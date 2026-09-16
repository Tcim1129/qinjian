from datetime import datetime, timedelta, timezone

import pytest
from fastapi import HTTPException
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.api.v1.auth import reset_password_by_phone
from app.api.v1 import auth
from app.core.database import Base
from app.core.security import hash_password, verify_password
from app.models import User
from app.schemas import PasswordResetByPhoneRequest
from app.schemas import PhoneSendCodeRequest
from app.services.phone_code_store import PhoneCodeEntry, get_phone_code_store


@pytest.fixture
async def db_session():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", future=True)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    async with session_factory() as session:
        yield session

    await engine.dispose()


@pytest.mark.anyio
async def test_send_phone_code_hides_test_code_when_popup_disabled(monkeypatch):
    monkeypatch.setattr(auth.settings, "DEBUG", True)
    monkeypatch.setattr(auth.settings, "PHONE_CODE_TEST_POPUP_ENABLED", False)
    monkeypatch.setattr(auth.settings, "PHONE_CODE_DEBUG_RETURN", False)
    monkeypatch.setattr(auth, "_generate_phone_code", lambda: "1357")
    store = get_phone_code_store()
    await store.delete("13800138102")

    response = await auth.send_phone_code(PhoneSendCodeRequest(phone="13800138102"))

    assert response == {"message": "验证码已发送"}
    assert "test_code" not in response
    assert "debug_code" not in response
    assert await store.get("13800138102") is not None


@pytest.mark.anyio
async def test_send_phone_code_never_leaks_test_code_on_formal_route(monkeypatch):
    monkeypatch.setattr(auth.settings, "DEBUG", True)
    monkeypatch.setattr(auth.settings, "PHONE_CODE_TEST_POPUP_ENABLED", True)
    monkeypatch.setattr(auth.settings, "PHONE_CODE_DEBUG_RETURN", True)
    monkeypatch.setattr(auth, "_generate_phone_code", lambda: "2468")
    store = get_phone_code_store()
    await store.delete("13800138112")

    response = await auth.send_phone_code(PhoneSendCodeRequest(phone="13800138112"))

    assert response == {"message": "验证码已发送"}
    assert "test_code" not in response
    assert "debug_code" not in response
    assert await store.get("13800138112") is not None


@pytest.mark.anyio
async def test_send_phone_code_demo_returns_test_code_when_enabled(monkeypatch):
    monkeypatch.setattr(auth.settings, "DEBUG", True)
    monkeypatch.setattr(auth.settings, "PHONE_CODE_TEST_POPUP_ENABLED", True)
    monkeypatch.setattr(auth, "_generate_phone_code", lambda: "9753")
    store = get_phone_code_store()
    await store.delete("13800138113")

    response = await auth.send_phone_code_demo(PhoneSendCodeRequest(phone="13800138113"))

    assert response == {
        "message": "测试验证码已生成",
        "delivery_mode": "test_popup",
        "test_code": "9753",
    }
    assert await store.get("13800138113") is not None


@pytest.mark.anyio
async def test_phone_code_can_reset_existing_user_password(db_session):
    phone = "13800138100"
    user = User(
        email="reset@example.com",
        phone=phone,
        nickname="reset",
        password_hash=hash_password("old-password"),
    )
    db_session.add(user)
    await db_session.flush()

    now = datetime.now(timezone.utc)
    store = get_phone_code_store()
    await store.set(
        phone,
        PhoneCodeEntry(
            code_hash=hash_password("246810"),
            requested_at=now,
            expires_at=now + timedelta(minutes=5),
            attempts_left=3,
        ),
    )

    response = await reset_password_by_phone(
        PasswordResetByPhoneRequest(
            phone=phone,
            code="246810",
            new_password="new-password",
        ),
        db=db_session,
    )

    assert response == {"message": "密码已重置，请用新密码登录"}
    assert verify_password("new-password", user.password_hash) is True
    assert await store.get(phone) is None


@pytest.mark.anyio
async def test_phone_password_reset_rejects_unknown_phone(db_session):
    phone = "13800138101"
    now = datetime.now(timezone.utc)
    store = get_phone_code_store()
    await store.set(
        phone,
        PhoneCodeEntry(
            code_hash=hash_password("246810"),
            requested_at=now,
            expires_at=now + timedelta(minutes=5),
            attempts_left=3,
        ),
    )

    with pytest.raises(HTTPException) as exc_info:
        await reset_password_by_phone(
            PasswordResetByPhoneRequest(
                phone=phone,
                code="246810",
                new_password="new-password",
            ),
            db=db_session,
        )

    assert exc_info.value.status_code == 404
    assert exc_info.value.detail == "该手机号尚未注册"
