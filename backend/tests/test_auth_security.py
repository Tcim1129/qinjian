from datetime import datetime, timezone
from types import SimpleNamespace
import uuid

from app.api.v1.auth import (
    DUMMY_PASSWORD_HASH,
    INVALID_LOGIN_DETAIL,
    _normalize_email,
    _serialize_user_response,
)
from app.core.config import settings
from app.core.security import (
    create_access_token,
    create_realtime_ws_ticket,
    decode_access_token,
    decode_realtime_ws_ticket,
    verify_password,
)


def test_serialize_user_response_redacts_wechat_identifiers():
    user = SimpleNamespace(
        id=uuid.uuid4(),
        email="tester@example.com",
        phone=None,
        nickname="tester",
        avatar_url=None,
        wechat_openid="wx-openid",
        wechat_unionid="wx-unionid",
        wechat_avatar="https://example.com/avatar.png",
        product_prefs={
            "ai_assist_enabled": False,
            "privacy_mode": "local_first",
            "preferred_entry": "emergency",
        },
        created_at=datetime.now(timezone.utc).replace(tzinfo=None),
    )

    payload = _serialize_user_response(user).model_dump()

    assert payload["wechat_bound"] is True
    assert "wechat_openid" not in payload
    assert "wechat_unionid" not in payload
    assert payload["ai_assist_enabled"] is False
    assert payload["privacy_mode"] == "local_first"
    assert payload["preferred_entry"] == "emergency"


def test_decode_access_token_rejects_missing_required_claims():
    original_secret_key = settings.SECRET_KEY
    settings.SECRET_KEY = "0123456789abcdef0123456789abcdef"
    try:
        token = create_access_token("user-123")

        assert decode_access_token(token) == "user-123"
        assert decode_access_token("not-a-token") is None
    finally:
        settings.SECRET_KEY = original_secret_key


def test_login_security_helpers_normalize_email_and_use_dummy_hash():
    assert _normalize_email(" Tester@Example.COM ") == "tester@example.com"
    assert verify_password("wrong-password", DUMMY_PASSWORD_HASH) is False
    assert INVALID_LOGIN_DETAIL == "邮箱或密码错误"


def test_realtime_ws_ticket_is_short_lived_and_type_scoped():
    original_secret_key = settings.SECRET_KEY
    original_ttl = settings.REALTIME_ASR_TICKET_EXPIRE_SECONDS
    settings.SECRET_KEY = "0123456789abcdef0123456789abcdef"
    settings.REALTIME_ASR_TICKET_EXPIRE_SECONDS = 120
    try:
        ticket = create_realtime_ws_ticket("user-456")
        access_token = create_access_token("user-456")

        assert decode_realtime_ws_ticket(ticket) == "user-456"
        assert decode_access_token(ticket) is None
        assert decode_realtime_ws_ticket(access_token) is None
    finally:
        settings.SECRET_KEY = original_secret_key
        settings.REALTIME_ASR_TICKET_EXPIRE_SECONDS = original_ttl
