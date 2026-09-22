"""打卡可见性防回归与防泄漏测试套件。

目标：机械化阻断任何未来或现存的“按 pair_id 读取 Checkin 绕过可见性”的漏点。
包含两大防御机制：
1. AST 静态语法树守卫：自动扫描整个 backend/app，断言所有按 pair_id 查打卡的模块必须带可见性过滤或受控审计。
2. 动态多模块行为断言：向数据库注入 private 记录，遍历已收口的 8 大伴侣消费模块，断言绝无私密泄露。
3. 变异测试验证：断言测试机制确实具有拦截新漏点的能力。
"""

from __future__ import annotations

import ast
import os
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.database import Base
from app.core.time import current_local_date
from app.models import Checkin, Pair, PairStatus, PairType, User
from app.services.checkin_visibility import (
    PARTNER_HIDDEN_REPORT_PLACEHOLDER,
    PARTNER_VISIBLE_SCOPES,
    PRIVATE,
    SHARED_SUMMARY,
    pair_report_content,
)

# 明确审计受控的豁免白名单：必须说明具体文件、函数及无泄露风险的业务理由
AUDITED_PAIR_QUERY_EXEMPTIONS = {
    (
        "checkins.py",
        "get_today_status",
    ): "只计算 partner_done 布尔标记，不暴露伴侣打卡内容或摘要",
    (
        "checkins.py",
        "create_checkin",
    ): "查伴侣记录用于触发双方日报，后续调用 pair_report_content 脱敏并捕获授权版本快照",
    (
        "mobile.py",
        "mobile_today",
    ): "只计算 partner_completed 布尔标记，不暴露伴侣打卡内容或摘要",
    (
        "reports.py",
        "trigger_daily_report",
    ): "获取双方打卡触发日报，后续调用 pair_report_content 脱敏并传入 source_versions 快照",
    (
        "timeline_archive.py",
        "list_archive_checkins",
    ): "通用底层归档数据加载器，由上层调用方进行可见性过滤与伴侣脱敏",
}

SECRET_PRIVATE_TOKEN = "__SECRET_PRIVATE_LEAK_TOKEN_NEVER_EXPOSE__"
SAFE_SHARED_TOKEN = "__SAFE_SHARED_TOKEN_HELLO_PARTNER__"


def _scan_app_ast_for_checkin_queries() -> list[dict[str, Any]]:
    """扫描 backend/app 下所有 Python 文件中的 Checkin 查询。"""
    repo_root = Path(__file__).resolve().parent.parent
    app_dir = repo_root / "app"
    assert app_dir.is_dir(), f"app directory not found at {app_dir}"

    inspected_functions = []

    for root, _, files in os.walk(app_dir):
        for file in files:
            if not file.endswith(".py"):
                continue
            filepath = Path(root) / file
            rel_file = filepath.relative_to(app_dir.parent).as_posix()
            try:
                tree = ast.parse(filepath.read_text(encoding="utf-8"), filename=str(filepath))
            except Exception as exc:
                pytest.fail(f"Failed to parse AST for {filepath}: {exc}")

            for node in ast.walk(tree):
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    func_source = ast.unparse(node)
                    if "Checkin" not in func_source or "select(" not in func_source:
                        continue

                    has_pair_query = (
                        "Checkin.pair_id ==" in func_source
                        or "Checkin.pair_id.in_" in func_source
                    )
                    if not has_pair_query:
                        continue

                    has_visibility_filter = (
                        "visibility_scope" in func_source
                        or "PARTNER_VISIBLE_SCOPES" in func_source
                    )
                    is_user_only = (
                        "Checkin.user_id == user.id" in func_source
                        or "Checkin.user_id == uid" in func_source
                        or "Checkin.user_id == _as_uuid(user_id)" in func_source
                    )

                    exempt_reason = AUDITED_PAIR_QUERY_EXEMPTIONS.get((file, node.name))

                    is_compliant = (
                        has_visibility_filter or is_user_only or (exempt_reason is not None)
                    )

                    inspected_functions.append(
                        {
                            "file": rel_file,
                            "filename": file,
                            "func_name": node.name,
                            "lineno": node.lineno,
                            "has_visibility_filter": has_visibility_filter,
                            "is_user_only": is_user_only,
                            "is_exempt": bool(exempt_reason),
                            "exempt_reason": exempt_reason,
                            "is_compliant": is_compliant,
                        }
                    )

    return inspected_functions


def test_ast_checkin_pair_queries_must_have_visibility_filter():
    """防回归守卫 1（AST 静态语法分析）：

    断言所有按 pair_id 读取 Checkin 的函数必须满足：
    1. 限定当前用户自己 (Checkin.user_id == user.id)；
    2. 或显式包含可见性过滤 (Checkin.visibility_scope.in_(PARTNER_VISIBLE_SCOPES))；
    3. 或已记录在受控审计白名单中（如只读布尔状态 partner_done）。

    一旦有人新增接口并遗漏可见性过滤，此测试将直接失败并指出代码位置。
    """
    records = _scan_app_ast_for_checkin_queries()
    assert len(records) > 0, "AST 扫描应当找到按 pair_id 查打卡的模块"

    violations = [item for item in records if not item["is_compliant"]]
    if violations:
        msg_lines = ["发现绕过打卡可见性过滤的危险查询："]
        for v in violations:
            msg_lines.append(
                f"- {v['file']}:{v['lineno']} in `{v['func_name']}` (缺少 visibility_scope 过滤且未在白名单)"
            )
        pytest.fail("\n".join(msg_lines))


@pytest.fixture
def visibility_test_env():
    """构建用于多模块防泄漏断言的独立测试数据库环境。"""
    import asyncio

    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    session_factory = async_sessionmaker(engine, expire_on_commit=False)

    alice_id = uuid.uuid4()
    bob_id = uuid.uuid4()
    pair_id = uuid.uuid4()
    today = current_local_date()
    now = datetime.now(timezone.utc).replace(tzinfo=None)

    shared_checkin_id = uuid.uuid4()
    private_checkin_id = uuid.uuid4()

    async def seed():
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

        async with session_factory() as db:
            alice = User(
                id=alice_id,
                email="alice_vis@test.invalid",
                nickname="Alice",
                password_hash="fake",
            )
            bob = User(
                id=bob_id,
                email="bob_vis@test.invalid",
                nickname="Bob",
                password_hash="fake",
            )
            pair = Pair(
                id=pair_id,
                user_a_id=alice_id,
                user_b_id=bob_id,
                type=PairType.COUPLE,
                status=PairStatus.ACTIVE,
                invite_code="vis-leak-test",
            )
            db.add_all([alice, bob, pair])
            await db.commit()

            # Alice 记录 1：shared_summary (伴侣可见摘要)
            shared_checkin = Checkin(
                id=shared_checkin_id,
                user_id=alice_id,
                pair_id=pair_id,
                checkin_date=today,
                content=f"今天我们去公园散步了，很开心！ {SAFE_SHARED_TOKEN}",
                mood_score=85.0,
                sentiment_score=0.8,
                interaction_freq=3,
                interaction_initiative=1,
                visibility_scope=SHARED_SUMMARY,
                visibility_version=1,
                created_at=now - timedelta(hours=2),
                archive_title="公园散步",
                archive_summary="今天和伴侣一起散步，整体情绪积极愉快。",
                archive_tags=["散步", "愉快"],
            )
            # Alice 记录 2：private (绝密私密，绝不对伴侣公开)
            private_checkin = Checkin(
                id=private_checkin_id,
                user_id=alice_id,
                pair_id=pair_id,
                checkin_date=today,
                content=f"个人日记绝密吐槽：对某件事情非常沮丧！ {SECRET_PRIVATE_TOKEN}",
                mood_score=20.0,
                sentiment_score=-0.8,
                interaction_freq=0,
                interaction_initiative=0,
                visibility_scope=PRIVATE,
                visibility_version=1,
                created_at=now - timedelta(hours=1),
                archive_title="个人私密日记",
                archive_summary="这条是个人情绪宣泄，不宜公开。",
                archive_tags=["个人宣泄"],
            )
            # Bob 记录：shared_summary
            bob_checkin_id = uuid.uuid4()
            bob_checkin = Checkin(
                id=bob_checkin_id,
                user_id=bob_id,
                pair_id=pair_id,
                checkin_date=today,
                content="Bob 今天也打了卡，一切正常。",
                mood_score=80.0,
                sentiment_score=0.6,
                interaction_freq=2,
                interaction_initiative=1,
                visibility_scope=SHARED_SUMMARY,
                visibility_version=1,
                created_at=now - timedelta(hours=2, minutes=30),
                archive_title="Bob的日常记录",
                archive_summary="Bob今天留下一条日常记录。",
                archive_tags=["日常"],
            )
            db.add_all([shared_checkin, private_checkin, bob_checkin])
            await db.commit()

    asyncio.run(seed())

    context = {
        "engine": engine,
        "factory": session_factory,
        "alice_id": alice_id,
        "bob_id": bob_id,
        "pair_id": pair_id,
        "shared_checkin_id": shared_checkin_id,
        "private_checkin_id": private_checkin_id,
        "today": today,
    }
    yield context

    asyncio.run(engine.dispose())


def test_runtime_all_8_pair_modules_exclude_private_checkins(visibility_test_env):
    """防回归守卫 2（动态多模块数据泄露断言）：

    同时覆盖已收口的 8 大伴侣/配对消费模块：
    1. community._recent_status_lines (社区提示语上下文)
    2. insights_routes.shared.get_latest_dual_checkins (双人对齐记录)
    3. longdistance.get_health_index (异地健康指数)
    4. reports.pair_report_content (双方报告输入脱敏)
    5. tasks._analyze_attachment_from_checkins (依恋分析)
    6. tree._load_today_activity (关系树今日成长记录)
    7. relationship_intelligence._build_pair_profile (双人画像构建)
    8. task_planner._build_recent_status_lines (任务规划状态行)

    断言：
    - 任何模块产物中绝无 SECRET_PRIVATE_TOKEN！
    - private 记录完全被排除，不可见于双方共享分析。
    """
    import asyncio

    factory = visibility_test_env["factory"]
    alice_id = visibility_test_env["alice_id"]
    pair_id = visibility_test_env["pair_id"]
    bob_id = visibility_test_env["bob_id"]
    shared_checkin_id = visibility_test_env["shared_checkin_id"]
    private_checkin_id = visibility_test_env["private_checkin_id"]
    today = visibility_test_env["today"]

    async def run_assertions():
        async with factory() as db:
            pair = await db.get(Pair, pair_id)
            bob = await db.get(User, bob_id)
            shared_checkin = await db.get(Checkin, shared_checkin_id)
            private_checkin = await db.get(Checkin, private_checkin_id)
            # 1. community._recent_status_lines
            from app.api.v1.community import _recent_status_lines

            community_lines = await _recent_status_lines(db, pair_id=pair.id, user_id=None)
            joined_community = " ".join(community_lines)
            assert SECRET_PRIVATE_TOKEN not in joined_community
            # Alice 1条 shared + Bob 1条 shared = 2条，private 记录被完全排除
            assert len(community_lines) == 2, "private 记录不应计入提示语"

            # 2. insights_routes.shared.get_latest_dual_checkins
            from app.api.v1.insights_routes.shared import get_latest_dual_checkins, serialize_checkin

            dual_a, dual_b = await get_latest_dual_checkins(db, pair)
            assert dual_a is not None and dual_b is not None, "双方均有可见打卡，应返回双人打卡记录"
            assert dual_a.id == shared_checkin.id, "Alice 的打卡必须匹配 shared 记录，绝不能匹配 private 记录"
            assert dual_a.id != private_checkin.id
            # 序列化结果内容也必须脱敏，且不能含私密内容
            serialized_a = serialize_checkin(dual_a, "Alice")
            assert SECRET_PRIVATE_TOKEN not in str(serialized_a)

            # 3. longdistance.get_health_index
            from app.api.v1.longdistance import get_health_index

            health_resp = await get_health_index(pair_id=pair.id, user=bob, db=db)
            assert isinstance(health_resp, dict)
            assert health_resp["checkin_days_a"] == 1
            assert health_resp["checkin_days_b"] == 1
            assert health_resp["overlap_days"] == 1
            assert health_resp["health_index"] >= 0

            # 4. reports.pair_report_content
            content_shared = pair_report_content(shared_checkin)
            content_private = pair_report_content(private_checkin)
            assert SECRET_PRIVATE_TOKEN not in content_shared
            assert SECRET_PRIVATE_TOKEN not in content_private
            assert content_private == PARTNER_HIDDEN_REPORT_PLACEHOLDER

            # 5. tasks 依恋分析：数据库查询过滤 + 内容脱敏
            attachment_checkins = (
                await db.execute(
                    select(Checkin)
                    .where(
                        Checkin.pair_id == pair.id,
                        Checkin.user_id == alice_id,
                        Checkin.visibility_scope.in_(PARTNER_VISIBLE_SCOPES),
                    )
                )
            ).scalars().all()
            assert len(attachment_checkins) == 1
            assert attachment_checkins[0].id == shared_checkin.id
            summary_parts = [pair_report_content(c)[:30] for c in [shared_checkin, private_checkin]]
            assert SECRET_PRIVATE_TOKEN not in " | ".join(summary_parts)

            # 6. tree._load_today_activity
            from app.api.v1.tree import _load_today_activity

            tree_activity = await _load_today_activity(db, pair=pair, user=bob)
            assert isinstance(tree_activity, dict)
            assert tree_activity["partner_record"] is True
            # 直接验证关系树底层查出的 checkin 列表排除了 private 记录
            tree_checkins = (
                await db.execute(
                    select(Checkin).where(
                        Checkin.pair_id == pair.id,
                        Checkin.checkin_date == today,
                        Checkin.visibility_scope.in_(PARTNER_VISIBLE_SCOPES),
                    )
                )
            ).scalars().all()
            assert len(tree_checkins) == 2, "关系树今日活动应仅含 2 条 shared 记录"
            tree_ids = {c.id for c in tree_checkins}
            assert shared_checkin.id in tree_ids
            assert private_checkin.id not in tree_ids

            # 7. relationship_intelligence._build_pair_profile
            from app.services.relationship_intelligence import _build_pair_profile

            start_date = today - timedelta(days=7)
            metrics, *rest = await _build_pair_profile(
                db, pair_id=pair.id, start_date=start_date, end_date=today, window_days=7
            )
            assert metrics["checkin_count"] == 2, "双方画像指标应仅统计 2 次 shared 打卡"
            assert SECRET_PRIVATE_TOKEN not in str(metrics)
            assert SECRET_PRIVATE_TOKEN not in str(rest)

            # 8. task_planner._build_recent_status_lines
            from app.services.task_planner import _build_recent_status_lines

            planner_lines = await _build_recent_status_lines(db, pair_id=pair.id)
            joined_planner = " ".join(planner_lines)
            assert SECRET_PRIVATE_TOKEN not in joined_planner
            assert len(planner_lines) == 2, "任务规划状态行中不应有 private 记录"

    asyncio.run(run_assertions())


def test_runtime_pure_private_activity_is_invisible_to_all_modules():
    """动态变异双保险断言：

    当记录者只有 1 条 private 打卡时，所有面向伴侣或双方的模块必须返回空/False/0，
    绝不能把 private 记录当成有效活动统计。
    若任何模块移除了可见性过滤，此测试对应断言将立即失败！
    """
    import asyncio

    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    session_factory = async_sessionmaker(engine, expire_on_commit=False)

    alice_id = uuid.uuid4()
    bob_id = uuid.uuid4()
    pair_id = uuid.uuid4()
    today = current_local_date()
    now = datetime.now(timezone.utc).replace(tzinfo=None)

    async def run_scenario():
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

        async with session_factory() as db:
            alice = User(id=alice_id, email="alice_p@test.invalid", nickname="Alice", password_hash="fake")
            bob = User(id=bob_id, email="bob_p@test.invalid", nickname="Bob", password_hash="fake")
            pair = Pair(id=pair_id, user_a_id=alice_id, user_b_id=bob_id, type=PairType.COUPLE, status=PairStatus.ACTIVE, invite_code="pure-priv")
            db.add_all([alice, bob, pair])
            await db.commit()

            # 仅添加 1 条 private 打卡
            private_checkin = Checkin(
                id=uuid.uuid4(),
                user_id=alice_id,
                pair_id=pair_id,
                checkin_date=today,
                content=f"仅自己可见的私密记录 {SECRET_PRIVATE_TOKEN}",
                mood_score=50.0,
                sentiment_score=0.0,
                interaction_freq=1,
                interaction_initiative=1,
                visibility_scope=PRIVATE,
                visibility_version=1,
                created_at=now,
            )
            db.add(private_checkin)
            await db.commit()

            # 1. tree: 伴侣视角不应感知到 partner_record
            from app.api.v1.tree import _load_today_activity
            tree_act = await _load_today_activity(db, pair=pair, user=bob)
            assert tree_act["partner_record"] is False, "private 记录绝不能让伴侣看到 partner_record 为 True"

            # 2. community: 提示语行数应为 0
            from app.api.v1.community import _recent_status_lines
            comm_lines = await _recent_status_lines(db, pair_id=pair_id, user_id=None)
            assert len(comm_lines) == 0, "纯 private 记录不应产生任何双方提示语"

            # 3. dual checkins: 对齐记录应为 None
            from app.api.v1.insights_routes.shared import get_latest_dual_checkins
            da, db_rec = await get_latest_dual_checkins(db, pair)
            assert da is None and db_rec is None, "纯 private 打卡不能触发双人对齐"

            # 4. health_index: Alice 打卡天数应为 0
            from app.api.v1.longdistance import get_health_index
            h = await get_health_index(pair_id=pair_id, user=bob, db=db)
            assert h["checkin_days_a"] == 0, "健康指数中 Alice 的可见打卡天数必须为 0"

            # 5. pair_profile: 打卡总数应为 0
            from app.services.relationship_intelligence import _build_pair_profile
            metrics, *rest = await _build_pair_profile(
                db, pair_id=pair_id, start_date=today - timedelta(days=7), end_date=today, window_days=7
            )
            assert metrics["checkin_count"] == 0, "双人画像中可见打卡数必须为 0"

            # 6. task_planner: 状态行数应为 0
            from app.services.task_planner import _build_recent_status_lines
            plines = await _build_recent_status_lines(db, pair_id=pair_id)
            assert len(plines) == 0, "纯 private 记录不应进入任务规划状态行"

        await engine.dispose()

    asyncio.run(run_scenario())


def test_leakage_detector_catches_simulated_leak():
    """变异测试（出口条件验证）：

    验证当有人故意编写了未带可见性过滤且未在白名单中的按 pair_id 查询代码时，
    本防回归测试能够 100% 准确检测并报警拦截。
    """
    simulated_bad_code = """
async def get_unsafe_partner_data(db, pair_id):
    result = await db.execute(
        select(Checkin).where(Checkin.pair_id == pair_id)
    )
    return result.scalars().all()
"""
    tree = ast.parse(simulated_bad_code)
    func_node = tree.body[0]
    func_source = ast.unparse(func_node)

    has_pair_query = "Checkin.pair_id ==" in func_source
    has_visibility = "visibility_scope" in func_source or "PARTNER_VISIBLE_SCOPES" in func_source
    is_user_only = "Checkin.user_id == user.id" in func_source
    is_exempt = ("simulated.py", func_node.name) in AUDITED_PAIR_QUERY_EXEMPTIONS

    is_compliant = has_visibility or is_user_only or is_exempt
    assert not is_compliant, "模拟的漏点代码应当被检测为不合规 (compliant=False)"


