from datetime import datetime, timezone
from types import SimpleNamespace
import uuid

from app.api.v1.pairs import (
    INVITE_CODE_ALPHABET,
    INVITE_CODE_LENGTH,
    _build_pair_response,
    _generate_invite_code,
)


def test_generate_invite_code_uses_high_entropy_safe_charset():
    invite_code = _generate_invite_code()

    assert len(invite_code) == INVITE_CODE_LENGTH
    assert set(invite_code).issubset(set(INVITE_CODE_ALPHABET))


def test_build_pair_response_redacts_partner_contact_channels():
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    user_a_id = uuid.uuid4()
    user_b_id = uuid.uuid4()

    pair = SimpleNamespace(
        id=uuid.uuid4(),
        user_a_id=user_a_id,
        user_b_id=user_b_id,
        type="couple",
        status="active",
        invite_code="SAFEINV123",
        unbind_requested_by=None,
        unbind_requested_at=None,
        created_at=now,
        custom_partner_nickname_a="小林",
        custom_partner_nickname_b=None,
    )
    me = SimpleNamespace(id=user_a_id)
    partner = SimpleNamespace(
        id=user_b_id,
        nickname="林夏",
        email="partner@example.com",
        phone="13800138000",
        avatar_url=None,
        wechat_avatar=None,
    )

    payload = _build_pair_response(pair, me, partner).model_dump()

    assert payload["partner_nickname"] == "林夏"
    assert payload["partner_email"] is None
    assert payload["partner_phone"] is None
