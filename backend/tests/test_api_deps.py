import uuid

import pytest
from fastapi import HTTPException, status

from app.api.deps import _parse_uuid_or_raise


def test_parse_uuid_or_raise_accepts_uuid_string():
    value = str(uuid.uuid4())

    parsed = _parse_uuid_or_raise(
        value,
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="invalid",
    )

    assert isinstance(parsed, uuid.UUID)
    assert str(parsed) == value


def test_parse_uuid_or_raise_rejects_invalid_value():
    with pytest.raises(HTTPException) as exc_info:
        _parse_uuid_or_raise(
            "not-a-uuid",
            status_code=status.HTTP_404_NOT_FOUND,
            detail="missing",
        )

    assert exc_info.value.status_code == status.HTTP_404_NOT_FOUND
    assert exc_info.value.detail == "missing"
