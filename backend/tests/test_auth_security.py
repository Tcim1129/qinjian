from datetime import datetime, timezone
from types import SimpleNamespace
import uuid

from app.api.v1.auth import _serialize_user_response
from app.core.config import settings
from app.core.security import create_access_token, decode_access_token


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
