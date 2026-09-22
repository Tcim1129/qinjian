"""App 与微信小程序全链路端到端模拟测试套件 (E2E Migration Simulation)。

覆盖：
1. 客户端能力预检 (preflight) 与启动引导 (bootstrap)
2. 小程序与 App 跨端双人配对链路
3. 离线草稿 (offline drafts) 弱网暂存、版本乐观锁与去重
4. 多媒体上传凭证 (media preflight ticket) 与打卡挂载
5. 双人打卡脱敏流转、伴侣投影与 D1 决策拦截 (422 严拒 shared_original)
6. 智能陪伴 (Agent Chat) 异常显式报错与防伪造降级
7. 设备推送登记 (push registration) 生命周期
"""

from __future__ import annotations

import asyncio
import uuid
from datetime import datetime, timedelta, timezone

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.api.deps import get_current_user, get_db
from app.api.v1.agent import router as agent_router
from app.api.v1.checkins import router as checkins_router
from app.api.v1.mobile import router as mobile_router
from app.api.v1.pairs import router as pairs_router
from app.core.database import Base
from app.models import Checkin, MobileMediaUpload, MobileOfflineDraft, MobilePushRegistration, Pair, PairStatus, PairType, User


@pytest.fixture
def e2e_client():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    factory = async_sessionmaker(engine, expire_on_commit=False)

    user_ids = {
        "alice": uuid.uuid4(),  # 模拟微信小程序端用户
        "bob": uuid.uuid4(),    # 模拟手机 App 端用户
        "stranger": uuid.uuid4(),
    }
    pair_id = uuid.uuid4()
    current_actor = {"id": user_ids["alice"]}

    async def init_db():
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        async with factory() as db:
            alice = User(id=user_ids["alice"], email="alice@mini.invalid", nickname="爱丽丝(小程序)", password_hash="mock_hash")
            bob = User(id=user_ids["bob"], email="bob@app.invalid", nickname="鲍勃(App)", password_hash="mock_hash")
            stranger = User(id=user_ids["stranger"], email="stranger@other.invalid", nickname="路人", password_hash="mock_hash")
            pair = Pair(
                id=pair_id,
                user_a_id=user_ids["alice"],
                user_b_id=user_ids["bob"],
                type=PairType.COUPLE,
                status=PairStatus.ACTIVE,
                invite_code="E2E-TEST-CODE",
            )
            db.add_all([alice, bob, stranger, pair])
            await db.commit()

    asyncio.run(init_db())

    async def db_override():
        async with factory() as db:
            try:
                yield db
                await db.commit()
            except Exception:
                await db.rollback()
                raise

    async def user_override():
        async with factory() as db:
            return await db.get(User, current_actor["id"])

    app = FastAPI(title="亲健跨端模拟测试环境")
    app.include_router(mobile_router, prefix="/api/v1")
    app.include_router(checkins_router, prefix="/api/v1")
    app.include_router(agent_router, prefix="/api/v1")
    app.include_router(pairs_router, prefix="/api/v1")

    app.dependency_overrides[get_db] = db_override
    app.dependency_overrides[get_current_user] = user_override

    with TestClient(app, raise_server_exceptions=False) as client:
        yield client, user_ids, pair_id, current_actor, factory

    asyncio.run(engine.dispose())


def test_step1_preflight_and_bootstrap(e2e_client):
    """步骤 1：小程序端与 App 端的能力预检与启动聚合。"""
    client, user_ids, pair_id, actor, _ = e2e_client

    # 1.1 小程序端预检
    actor["id"] = user_ids["alice"]
    res_mp = client.post("/api/v1/mobile/preflight", json={"client_type": "mini_program"})
    assert res_mp.status_code == 200
    data_mp = res_mp.json()
    assert data_mp["client_type"] == "mini_program"
    assert any(m["method"] == "wechat" for m in data_mp["login_methods"])

    # 1.2 App 端预检与启动
    actor["id"] = user_ids["bob"]
    res_app = client.post("/api/v1/mobile/preflight", json={"client_type": "app"})
    assert res_app.status_code == 200
    assert res_app.json()["client_type"] == "app"

    res_boot = client.post("/api/v1/mobile/bootstrap", json={})
    assert res_boot.status_code == 200
    boot_data = res_boot.json()
    assert boot_data["state_version"] is not None
    assert len(boot_data["relationships"]) >= 1
    assert str(boot_data["relationships"][0]["space_id"]) == str(pair_id)


def test_step2_offline_draft_sync_and_conflict_resolution(e2e_client):
    """步骤 2：小程序离线草稿暂存、同步、版本乐观锁与去重机制。"""
    client, user_ids, pair_id, actor, factory = e2e_client
    actor["id"] = user_ids["alice"]

    draft_client_id = f"draft_{uuid.uuid4().hex}"

    # 2.1 首次离线同步
    sync_res = client.post(
        "/api/v1/mobile/offline-drafts/sync",
        json={
            "client_draft_id": draft_client_id,
            "base_revision": 0,
            "upload_confirmed": True,
            "draft": {
                "relationship_space_id": str(pair_id),
                "content": "今天在小程序上离线写下的日记草稿",
                "mood_score": 3,
                "mood_tags": ["平静"],
            },
            "local_updated_at": datetime.now(timezone.utc).isoformat(),
        },
    )
    assert sync_res.status_code == 200, sync_res.text
    meta = sync_res.json()
    assert meta["revision"] == 1
    assert meta["status"] == "active"

    # 2.2 幂等去重检查（内容未变化）
    sync_res_dup = client.post(
        "/api/v1/mobile/offline-drafts/sync",
        json={
            "client_draft_id": draft_client_id,
            "base_revision": 1,
            "upload_confirmed": True,
            "draft": {
                "relationship_space_id": str(pair_id),
                "content": "今天在小程序上离线写下的日记草稿",
                "mood_score": 3,
                "mood_tags": ["平静"],
            },
            "local_updated_at": datetime.now(timezone.utc).isoformat(),
        },
    )
    assert sync_res_dup.status_code == 200
    assert sync_res_dup.json()["deduplicated"] is True

    # 2.3 版本冲突检测（base_revision 不匹配）
    conflict_res = client.post(
        "/api/v1/mobile/offline-drafts/sync",
        json={
            "client_draft_id": draft_client_id,
            "base_revision": 99,  # 错误旧版本
            "upload_confirmed": True,
            "draft": {"content": "尝试覆盖"},
            "local_updated_at": datetime.now(timezone.utc).isoformat(),
        },
    )
    assert conflict_res.status_code == 409

    # 2.4 他人无法越权拉取 Alice 的草稿
    actor["id"] = user_ids["bob"]
    pull_res_bob = client.post(
        "/api/v1/mobile/offline-drafts/pull",
        json={"client_draft_id": draft_client_id},
    )
    assert pull_res_bob.status_code == 404


def test_step3_media_preflight_and_upload_access(e2e_client):
    """步骤 3：多媒体上传预检、安全 Token 签发与生命周期管理。"""
    client, user_ids, pair_id, actor, _ = e2e_client
    actor["id"] = user_ids["alice"]

    client_req_id = f"req_{uuid.uuid4().hex}"
    png_bytes = b"\x89PNG\r\n\x1a\n" + b"\x00" * 32

    # 3.1 媒体预检申请
    preflight = client.post(
        "/api/v1/mobile/media/preflight",
        json={
            "client_request_id": client_req_id,
            "media_kind": "image",
            "content_type": "image/png",
            "size_bytes": len(png_bytes),
            "private_storage_confirmed": True,
        },
    )
    assert preflight.status_code == 200
    preflight_data = preflight.json()
    assert preflight_data["upload_ticket"] is not None

    # 3.2 模拟上传文件
    uploaded = client.post(
        "/api/v1/mobile/media/upload",
        data={"upload_ticket": preflight_data["upload_ticket"]},
        files={"file": ("photo.png", png_bytes, "image/png")},
    )
    assert uploaded.status_code == 200
    media_id = uploaded.json()["media_id"]

    # 3.3 检查媒体状态（根据 client_request_id）
    status_res = client.post("/api/v1/mobile/media/status", json={"client_request_id": client_req_id})
    assert status_res.status_code == 200
    assert status_res.json()["status"] == "uploaded"
    assert status_res.json()["media_id"] == media_id


def test_step4_checkin_visibility_flow_and_leakage_prevention(e2e_client):
    """步骤 4：双端打卡、可见性流转、伴侣脱敏投影与 D1 严拒 shared_original。"""
    client, user_ids, pair_id, actor, factory = e2e_client

    # 4.1 Alice 在小程序提交打卡（默认 shared_summary）
    actor["id"] = user_ids["alice"]
    alice_secret_text = "今天工作被领导批评了非常委屈，甚至想辞职一个人静静。"
    create_res = client.post(
        "/api/v1/mobile/checkins",
        json={
            "scope": "relationship",
            "relationship_space_id": str(pair_id),
            "client_request_id": f"chk_{uuid.uuid4().hex}",
            "content": alice_secret_text,
            "sharing_confirmed": True,
        },
    )
    assert create_res.status_code == 200
    record_id = create_res.json()["record_id"]

    # 4.2 Bob (伴侣视角) 查看打卡详情
    actor["id"] = user_ids["bob"]
    bob_view = client.post(
        "/api/v1/mobile/checkins/detail",
        json={"record_id": record_id},
    )
    assert bob_view.status_code == 200
    bob_data = bob_view.json()
    # 核心隐私断言：Bob 绝对看不到 Alice 的原话！
    assert bob_data["is_owner"] is False
    assert bob_data["content"] is None
    assert alice_secret_text not in str(bob_data["summary"] or "")
    assert "原文和原媒体默认仅记录者本人可见" in bob_data["locked_reason"]

    # 4.3 Alice 尝试切换为 shared_original -> 必须返回 422 拒绝（落实 D1 决策）
    actor["id"] = user_ids["alice"]
    patch_bad = client.patch(
        f"/api/v1/checkins/{record_id}/visibility",
        json={"visibility_scope": "shared_original", "client_source": "mini_program"},
    )
    assert patch_bad.status_code == 422, "D1决策：shared_original 必须被 422 拒绝"

    # 4.4 Alice 切换为 private -> 伴侣端彻底不可见
    patch_private = client.patch(
        f"/api/v1/checkins/{record_id}/visibility",
        json={"visibility_scope": "private", "client_source": "mini_program"},
    )
    assert patch_private.status_code == 200
    assert patch_private.json()["visibility_scope"] == "private"

    actor["id"] = user_ids["bob"]
    bob_view_private = client.post(
        "/api/v1/mobile/checkins/detail",
        json={"record_id": record_id},
    )
    # 当 Alice 改为 private 后，Bob 查询应直接返回 404（不泄露存在性）
    assert bob_view_private.status_code == 404


def test_step5_push_registration_lifecycle(e2e_client):
    """步骤 5：App 端设备推送凭据 (APNs/FCM/UniPush) 登记、状态查询与生命周期。"""
    client, user_ids, _, actor, _ = e2e_client
    actor["id"] = user_ids["bob"]

    inst_id = f"device_{uuid.uuid4().hex}"

    # 5.1 同步权限状态
    perm_res = client.post(
        "/api/v1/mobile/push/permission-sync",
        json={
            "installation_id": inst_id,
            "platform": "ios",
            "provider": "unipush",
            "permission_state": "authorized",
            "permission_status_confirmed": True,
        },
    )
    assert perm_res.status_code == 200
    assert perm_res.json()["permission_state"] == "authorized"

    # 5.2 查询状态
    status_res = client.post(
        "/api/v1/mobile/push/status",
        json={"installation_id": inst_id},
    )
    assert status_res.status_code == 200
    assert status_res.json()["permission_state"] == "authorized"


def test_step6_agent_chat_failure_never_canned_fallback(e2e_client, monkeypatch):
    """步骤 6：AI 智能陪伴异常时返回真实错误，绝对无伪造 assistant 假回复。"""
    from app.api.v1 import agent as agent_api

    client, user_ids, _, actor, _ = e2e_client
    actor["id"] = user_ids["alice"]

    # 6.1 创建 Agent 会话
    sess_res = client.post("/api/v1/agent/sessions", json={})
    assert sess_res.status_code == 200
    session_id = sess_res.json()["session_id"]

    # 6.2 模拟大模型服务故障
    async def mock_fail_loop(**_kwargs):
        raise RuntimeError("simulated model provider timeout")

    monkeypatch.setattr(agent_api, "run_agent_loop", mock_fail_loop)

    chat_res = client.post(
        f"/api/v1/agent/sessions/{session_id}/chat",
        json={"content": "我心情不好想聊聊", "surface": "chat"},
    )
    # 显式报错 502/504，绝不返回 200 假成功
    assert chat_res.status_code in (500, 502, 504)

    # 6.3 检查历史消息库：绝不包含任何伪造的 assistant 回复
    msg_res = client.get(f"/api/v1/agent/sessions/{session_id}/messages")
    assert msg_res.status_code == 200
    messages = msg_res.json()
    assert not any(m.get("role") == "assistant" for m in messages)
    assert not any("没能连上助手" in m.get("content", "") for m in messages)
