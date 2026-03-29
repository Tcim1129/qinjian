from app.api.v1.pairs import (
    INVITE_CODE_ALPHABET,
    INVITE_CODE_LENGTH,
    _generate_invite_code,
)


def test_generate_invite_code_uses_high_entropy_safe_charset():
    invite_code = _generate_invite_code()

    assert len(invite_code) == INVITE_CODE_LENGTH
    assert set(invite_code).issubset(set(INVITE_CODE_ALPHABET))
