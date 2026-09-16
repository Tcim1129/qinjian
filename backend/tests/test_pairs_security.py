import pytest
from pydantic import ValidationError

from app.api.v1.pairs import (
    INVITE_CODE_ALPHABET,
    INVITE_CODE_LENGTH,
    _generate_invite_code,
)
from app.models import PairType
from app.schemas import PairJoinRequest, PairJoinSubmitRequest


def test_generate_invite_code_uses_high_entropy_safe_charset():
    invite_code = _generate_invite_code()

    assert len(invite_code) == INVITE_CODE_LENGTH
    assert set(invite_code).issubset(set(INVITE_CODE_ALPHABET))


def test_pair_join_request_requires_current_invite_code_format():
    req = PairJoinRequest(invite_code=" a3h7k8m9q2 ")

    assert req.invite_code == "A3H7K8M9Q2"

    for invalid_code in ("123456", "A3H7K8M9Q2L", "A3H7K8M9O2"):
        with pytest.raises(ValidationError):
            PairJoinRequest(invite_code=invalid_code)


def test_pair_type_supports_regular_friend_relationship():
    assert PairType("friend") is PairType.FRIEND


def test_pair_join_submit_request_requires_supported_relationship_type():
    req = PairJoinSubmitRequest(invite_code=" a3h7k8m9q2 ", type="couple")

    assert req.invite_code == "A3H7K8M9Q2"
    assert req.type == "couple"

    with pytest.raises(ValidationError):
        PairJoinSubmitRequest(invite_code="A3H7K8M9Q2", type="unknown")
