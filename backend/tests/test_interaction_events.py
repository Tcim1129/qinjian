import pytest
from pydantic import ValidationError

from app.models import UserInteractionEvent
from app.schemas import InteractionEventBatchRequest


def test_user_interaction_event_model_exposes_expected_columns():
    columns = set(UserInteractionEvent.__table__.c.keys())

    assert {
        "user_id",
        "pair_id",
        "session_id",
        "source",
        "event_type",
        "page",
        "path",
        "http_method",
        "http_status",
        "target_type",
        "target_id",
        "payload",
        "occurred_at",
    }.issubset(columns)


def test_interaction_batch_request_caps_batch_size():
    payload = {
        "events": [{"event_type": "page.view"} for _ in range(50)]
    }

    request = InteractionEventBatchRequest(**payload)

    assert len(request.events) == 50

    with pytest.raises(ValidationError):
        InteractionEventBatchRequest(
            events=[{"event_type": "page.view"} for _ in range(51)]
        )
