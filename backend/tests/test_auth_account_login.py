import pytest
from fastapi import HTTPException
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from types import SimpleNamespace

from app.api.v1 import auth
from app.api.v1.auth import (
    MIN_PASSWORD_LENGTH,
    _build_phone_account_email,
    _serialize_user_response,
    confirm_profile_update_code,
    login,
    register,
    send_profile_update_code,
    send_profile_update_code_demo,
    update_me,
)
from app.core.database import Base
from app.core.security import hash_password, verify_password
from app.models import UploadAsset, User
from app.schemas import (
    LoginRequest,
    ProfileUpdateCodeConfirmRequest,
    ProfileUpdateCodeSendRequest,
    RegisterRequest,
    UserUpdateRequest,
    WechatLoginRequest,
)
from app.services import login_attempts, phone_code_store


def _fake_request():
    return SimpleNamespace(client=SimpleNamespace(host="127.0.0.1"), headers={})


@pytest.fixture
async def db_session():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", future=True)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    async with session_factory() as session:
        yield session

    await engine.dispose()


@pytest.fixture(autouse=True)
def debug_verification_environment(monkeypatch):
    monkeypatch.setattr(auth.settings, "DEBUG", True)
    monkeypatch.setattr(auth.settings, "PHONE_CODE_STORE", "memory")
    monkeypatch.setattr(auth.settings, "REDIS_URL", "")
    monkeypatch.setattr(login_attempts, "_LOGIN_ATTEMPT_STORE", None)
    monkeypatch.setattr(phone_code_store, "_PHONE_CODE_STORE", None)


@pytest.mark.anyio
async def test_register_accepts_phone_account_and_allows_phone_password_login(
    db_session,
):
    response = await register(
        RegisterRequest(
            account="13800138000",
            nickname="手机用户",
            password="123456",
        ),
        _fake_request(),
        db=db_session,
    )

    assert response["user"].phone == "13800138000"
    assert response["user"].email == _build_phone_account_email("13800138000")

    login_response = await login(
        LoginRequest(account="13800138000", password="123456"),
        _fake_request(),
        db=db_session,
    )

    assert login_response["user"].id == response["user"].id


@pytest.mark.anyio
async def test_login_accepts_both_email_and_phone_for_same_account(db_session):
    user = User(
        email="tester@example.com",
        phone="13800138001",
        nickname="tester",
        password_hash=hash_password("123456"),
    )
    db_session.add(user)
    await db_session.flush()

    email_login = await login(
        LoginRequest(account="tester@example.com", password="123456"),
        _fake_request(),
        db=db_session,
    )
    phone_login = await login(
        LoginRequest(account="13800138001", password="123456"),
        _fake_request(),
        db=db_session,
    )

    assert email_login["user"].id == user.id
    assert phone_login["user"].id == user.id


@pytest.mark.anyio
async def test_user_response_marks_relaxed_test_account(db_session, monkeypatch):
    monkeypatch.setattr(
        auth.settings,
        "RELAXED_TEST_ACCOUNT_EMAILS",
        "relaxed-user@example.com",
        raising=False,
    )
    user = User(
        email="Relaxed-User@Example.com",
        nickname="relaxed",
        password_hash=hash_password("123456"),
    )
    db_session.add(user)
    await db_session.flush()

    response = _serialize_user_response(user)

    assert response.testing_unrestricted is True


@pytest.mark.anyio
async def test_wechat_login_rejects_local_upload_avatar_url(db_session, monkeypatch):
    class _FakeWechatResponse:
        def json(self):
            return {"openid": "wx-local-upload-avatar"}

    class _FakeAsyncClient:
        def __init__(self, *args, **kwargs):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return False

        async def get(self, *_args, **_kwargs):
            return _FakeWechatResponse()

    monkeypatch.setattr(auth.settings, "WECHAT_APPID", "appid")
    monkeypatch.setattr(auth.settings, "WECHAT_SECRET", "secret")

    import httpx

    monkeypatch.setattr(httpx, "AsyncClient", _FakeAsyncClient)

    with pytest.raises(HTTPException) as exc:
        await auth.wechat_login(
            WechatLoginRequest(
                code="code",
                nickname="微信用户",
                avatar_url="/uploads/images/stolen.png",
            ),
            db=db_session,
        )

    assert exc.value.status_code == 400


@pytest.mark.anyio
async def test_register_keeps_legacy_email_field_compatible(db_session):
    response = await register(
        RegisterRequest(
            email="Legacy@Example.com",
            nickname="legacy",
            password="123456",
        ),
        _fake_request(),
        db=db_session,
    )

    assert response["user"].email == "legacy@example.com"

    login_response = await login(
        LoginRequest(email="Legacy@Example.com", password="123456"),
        _fake_request(),
        db=db_session,
    )

    assert login_response["user"].id == response["user"].id


@pytest.mark.anyio
async def test_register_can_upgrade_existing_phone_code_account(db_session):
    phone = "13800138002"
    user = User(
        email=_build_phone_account_email(phone),
        phone=phone,
        nickname="手机用户8002",
        password_hash=hash_password("temporary-secret"),
    )
    db_session.add(user)
    await db_session.flush()

    response = await register(
        RegisterRequest(account=phone, nickname="正式账号", password="123456"),
        _fake_request(),
        db=db_session,
    )

    assert response["user"].id == user.id
    assert user.nickname == "正式账号"
    assert verify_password("123456", user.password_hash) is True


@pytest.mark.anyio
async def test_register_rejects_passwords_shorter_than_six_chars(db_session):
    with pytest.raises(HTTPException) as exc_info:
        await register(
            RegisterRequest(
                account="tester@example.com",
                nickname="tester",
                password="12345",
            ),
            _fake_request(),
            db=db_session,
        )

    assert exc_info.value.status_code == 400
    assert exc_info.value.detail == f"密码至少需要 {MIN_PASSWORD_LENGTH} 位"


@pytest.mark.anyio
async def test_update_me_accepts_nickname_and_avatar(db_session):
    user = User(
        email="before@example.com",
        phone="13800138003",
        nickname="before",
        password_hash=hash_password("123456"),
    )
    db_session.add(user)
    await db_session.flush()
    db_session.add(
        UploadAsset(
            storage_path="/uploads/images/avatar.png",
            subdir="images",
            filename="avatar.png",
            owner_user_id=user.id,
            scope="user",
        )
    )
    await db_session.flush()

    response = await update_me(
        UserUpdateRequest(
            nickname="after",
            avatar_url="/uploads/images/avatar.png",
            avatar_presentation={
                "focus_x": 38,
                "focus_y": 62,
                "scale": 1.24,
            },
            selected_pair_id="pair-123",
        ),
        user=user,
        db=db_session,
    )

    assert response.nickname == "after"
    assert response.email == "before@example.com"
    assert response.phone == "13800138003"
    assert "/upload/access/images/avatar.png" in str(response.avatar_url or "")
    assert response.avatar_presentation.focus_x == pytest.approx(38.0)
    assert response.avatar_presentation.focus_y == pytest.approx(62.0)
    assert response.avatar_presentation.scale == pytest.approx(1.24)
    assert response.selected_pair_id == "pair-123"
    assert user.product_prefs["selected_pair_id"] == "pair-123"
    assert user.product_prefs["avatar_presentation"]["focus_x"] == pytest.approx(38.0)


@pytest.mark.anyio
async def test_update_me_normalizes_signed_avatar_access_url(db_session):
    user = User(
        email="avatar-signed@example.com",
        phone="13800138013",
        nickname="before",
        password_hash=hash_password("123456"),
    )
    db_session.add(user)
    await db_session.flush()
    db_session.add(
        UploadAsset(
            storage_path="/uploads/images/avatar.png",
            subdir="images",
            filename="avatar.png",
            owner_user_id=user.id,
            scope="user",
        )
    )
    await db_session.flush()

    response = await update_me(
        UserUpdateRequest(
            avatar_url="/api/v1/upload/access/images/avatar.png?expires=1&sig=test",
        ),
        user=user,
        db=db_session,
    )

    assert user.avatar_url == "/uploads/images/avatar.png"
    assert "/upload/access/images/avatar.png" in str(response.avatar_url or "")


@pytest.mark.anyio
async def test_update_me_rejects_avatar_upload_owned_by_another_user(db_session):
    user = User(
        email="avatar-owner@example.com",
        nickname="owner",
        password_hash=hash_password("123456"),
    )
    other = User(
        email="avatar-other@example.com",
        nickname="other",
        password_hash=hash_password("123456"),
        avatar_url="/uploads/images/other-avatar.png",
    )
    db_session.add_all([user, other])
    await db_session.flush()

    with pytest.raises(HTTPException) as exc_info:
        await update_me(
            UserUpdateRequest(avatar_url="/uploads/images/other-avatar.png"),
            user=user,
            db=db_session,
        )

    assert exc_info.value.status_code == 403


@pytest.mark.anyio
async def test_update_me_persists_spiritual_support_opt_in(db_session):
    user = User(
        email="prefs@example.com",
        phone="13800138103",
        nickname="prefs",
        password_hash=hash_password("123456"),
    )
    db_session.add(user)
    await db_session.flush()

    response = await update_me(
        UserUpdateRequest(
            preferred_language="zh",
            tone_preference="gentle",
            relationship_space_theme="engine",
            spiritual_support_enabled=True,
        ),
        user=user,
        db=db_session,
    )

    assert response.preferred_language == "zh"
    assert response.tone_preference == "gentle"
    assert response.relationship_space_theme == "engine"
    assert response.spiritual_support_enabled is True
    assert user.product_prefs["relationship_space_theme"] == "engine"
    assert user.product_prefs["spiritual_support_enabled"] is True


@pytest.mark.anyio
async def test_update_me_persists_custom_mood_presets(db_session):
    user = User(
        email="moods@example.com",
        phone="13800138123",
        nickname="moods",
        password_hash=hash_password("123456"),
    )
    db_session.add(user)
    await db_session.flush()

    response = await update_me(
        UserUpdateRequest(
            custom_mood_presets=["失落", "释然", "失落", "心里堵堵的；"],
        ),
        user=user,
        db=db_session,
    )

    assert response.custom_mood_presets == ["失落", "释然", "心里堵堵的"]
    assert user.product_prefs["custom_mood_presets"] == ["失落", "释然", "心里堵堵的"]


@pytest.mark.anyio
async def test_update_me_persists_hidden_default_moods(db_session):
    user = User(
        email="mood-hidden@example.com",
        phone="13800138124",
        nickname="mood-hidden",
        password_hash=hash_password("123456"),
    )
    db_session.add(user)
    await db_session.flush()

    response = await update_me(
        UserUpdateRequest(
            hidden_default_moods=["焦虑", "生气", "释然", "焦虑"],
        ),
        user=user,
        db=db_session,
    )

    assert response.hidden_default_moods == ["焦虑", "生气"]
    assert user.product_prefs["hidden_default_moods"] == ["焦虑", "生气"]


@pytest.mark.anyio
async def test_update_me_rejects_direct_email_and_phone_change(db_session):
    user = User(
        email="before@example.com",
        phone="13800138003",
        nickname="before",
        password_hash=hash_password("123456"),
    )
    db_session.add(user)
    await db_session.flush()

    with pytest.raises(HTTPException) as email_exc:
        await update_me(
            UserUpdateRequest(email="after@example.com"),
            user=user,
            db=db_session,
        )

    with pytest.raises(HTTPException) as phone_exc:
        await update_me(
            UserUpdateRequest(phone="13800138009"),
            user=user,
            db=db_session,
        )

    assert email_exc.value.status_code == 400
    assert email_exc.value.detail == "请先通过验证码确认新的邮箱"
    assert phone_exc.value.status_code == 400
    assert phone_exc.value.detail == "请先通过验证码确认新的手机号"


@pytest.mark.anyio
async def test_send_profile_update_code_rejects_duplicate_email_and_phone(db_session):
    owner = User(
        email="owner@example.com",
        phone="13800138004",
        nickname="owner",
        password_hash=hash_password("123456"),
    )
    taken = User(
        email="taken@example.com",
        phone="13800138005",
        nickname="taken",
        password_hash=hash_password("123456"),
    )
    db_session.add_all([owner, taken])
    await db_session.flush()

    with pytest.raises(HTTPException) as email_exc:
        await send_profile_update_code(
            ProfileUpdateCodeSendRequest(field="email", value="TAKEN@example.com"),
            user=owner,
            db=db_session,
        )

    with pytest.raises(HTTPException) as phone_exc:
        await send_profile_update_code(
            ProfileUpdateCodeSendRequest(field="phone", value="13800138005"),
            user=owner,
            db=db_session,
        )

    assert email_exc.value.status_code == 400
    assert email_exc.value.detail == "该邮箱已被使用"
    assert phone_exc.value.status_code == 400
    assert phone_exc.value.detail == "该手机号已被使用"


@pytest.mark.anyio
async def test_confirm_profile_update_keeps_phone_placeholder_email_in_sync(
    db_session, monkeypatch
):
    user = User(
        email=_build_phone_account_email("13800138006"),
        phone="13800138006",
        nickname="手机用户8006",
        password_hash=hash_password("123456"),
    )
    db_session.add(user)
    await db_session.flush()
    monkeypatch.setattr(auth.settings, "DEBUG", True)
    monkeypatch.setattr(auth.settings, "PHONE_CODE_TEST_POPUP_ENABLED", True)

    send_payload = await send_profile_update_code_demo(
        ProfileUpdateCodeSendRequest(field="phone", value="13800138016"),
        user=user,
        db=db_session,
    )

    response = await confirm_profile_update_code(
        ProfileUpdateCodeConfirmRequest(
            field="phone",
            value="13800138016",
            code=str(send_payload["test_code"]),
        ),
        user=user,
        db=db_session,
    )

    assert response.phone == "13800138016"
    assert response.email == _build_phone_account_email("13800138016")


@pytest.mark.anyio
async def test_send_profile_update_code_hides_test_code_on_formal_route(
    db_session, monkeypatch
):
    user = User(
        email="before@example.com",
        phone="13800138007",
        nickname="before",
        password_hash=hash_password("123456"),
    )
    db_session.add(user)
    await db_session.flush()
    monkeypatch.setattr(auth.settings, "DEBUG", True)
    monkeypatch.setattr(auth.settings, "PHONE_CODE_TEST_POPUP_ENABLED", True)
    monkeypatch.setattr(auth.settings, "PHONE_CODE_DEBUG_RETURN", True)

    response = await send_profile_update_code(
        ProfileUpdateCodeSendRequest(field="email", value="next@example.com"),
        user=user,
        db=db_session,
    )

    assert response == {"message": "验证码已发送"}
    assert "test_code" not in response
    assert "debug_code" not in response


@pytest.mark.anyio
async def test_send_profile_update_code_demo_returns_test_code_for_email_change(
    db_session, monkeypatch
):
    user = User(
        email="before@example.com",
        phone="13800138017",
        nickname="before",
        password_hash=hash_password("123456"),
    )
    db_session.add(user)
    await db_session.flush()
    monkeypatch.setattr(auth.settings, "DEBUG", True)
    monkeypatch.setattr(auth.settings, "PHONE_CODE_TEST_POPUP_ENABLED", True)
    monkeypatch.setattr(auth, "_generate_phone_code", lambda: "4826")

    response = await send_profile_update_code_demo(
        ProfileUpdateCodeSendRequest(field="email", value="after-demo@example.com"),
        user=user,
        db=db_session,
    )

    assert response == {
        "message": "邮箱测试验证码已生成",
        "delivery_mode": "test_popup",
        "test_code": "4826",
    }


@pytest.mark.anyio
async def test_confirm_profile_update_code_updates_email(db_session, monkeypatch):
    user = User(
        email="before@example.com",
        phone="13800138008",
        nickname="before",
        password_hash=hash_password("123456"),
    )
    db_session.add(user)
    await db_session.flush()
    monkeypatch.setattr(auth.settings, "DEBUG", True)
    monkeypatch.setattr(auth.settings, "PHONE_CODE_TEST_POPUP_ENABLED", True)

    send_payload = await send_profile_update_code_demo(
        ProfileUpdateCodeSendRequest(field="email", value="after@example.com"),
        user=user,
        db=db_session,
    )

    response = await confirm_profile_update_code(
        ProfileUpdateCodeConfirmRequest(
            field="email",
            value="after@example.com",
            code=str(send_payload["test_code"]),
        ),
        user=user,
        db=db_session,
    )

    assert response.email == "after@example.com"


@pytest.mark.anyio
async def test_confirm_profile_update_code_updates_phone_and_placeholder_email(
    db_session, monkeypatch
):
    user = User(
        email=_build_phone_account_email("13800138011"),
        phone="13800138011",
        nickname="手机用户8011",
        password_hash=hash_password("123456"),
    )
    db_session.add(user)
    await db_session.flush()
    monkeypatch.setattr(auth.settings, "DEBUG", True)
    monkeypatch.setattr(auth.settings, "PHONE_CODE_TEST_POPUP_ENABLED", True)

    send_payload = await send_profile_update_code_demo(
        ProfileUpdateCodeSendRequest(field="phone", value="13800138021"),
        user=user,
        db=db_session,
    )

    response = await confirm_profile_update_code(
        ProfileUpdateCodeConfirmRequest(
            field="phone",
            value="13800138021",
            code=str(send_payload["test_code"]),
        ),
        user=user,
        db=db_session,
    )

    assert response.phone == "13800138021"
    assert response.email == _build_phone_account_email("13800138021")


@pytest.mark.anyio
async def test_confirm_profile_update_code_rejects_wrong_code(db_session, monkeypatch):
    user = User(
        email="before@example.com",
        phone="13800138012",
        nickname="before",
        password_hash=hash_password("123456"),
    )
    db_session.add(user)
    await db_session.flush()
    monkeypatch.setattr(auth.settings, "DEBUG", True)
    monkeypatch.setattr(auth.settings, "PHONE_CODE_TEST_POPUP_ENABLED", True)

    await send_profile_update_code_demo(
        ProfileUpdateCodeSendRequest(field="phone", value="13800138022"),
        user=user,
        db=db_session,
    )

    with pytest.raises(HTTPException) as exc_info:
        await confirm_profile_update_code(
            ProfileUpdateCodeConfirmRequest(
                field="phone",
                value="13800138022",
                code="0000",
            ),
            user=user,
            db=db_session,
        )

    assert exc_info.value.status_code == 400
    assert exc_info.value.detail == "验证码错误"
