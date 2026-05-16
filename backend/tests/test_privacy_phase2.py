import asyncio
import uuid

from app.main import app
from app.services.privacy_audit import log_privacy_ai_chat
from app.services.relationship_intelligence import record_relationship_event


class _FakeSession:
    def __init__(self):
        self.items = []

    def add(self, item):
        self.items.append(item)

    async def flush(self):
        return None


def test_record_relationship_event_allows_global_privacy_events():
    db = _FakeSession()

    event = asyncio.run(
        record_relationship_event(
            db,
            event_type="privacy.retention.purged",
            entity_type="privacy_retention_sweep",
            payload={"counts": {"expired_privacy_events": 2}},
        )
    )

    assert event.event_type == "privacy.retention.purged"
    assert event.user_id is None
    assert event.pair_id is None
    assert len(db.items) == 1


def test_log_privacy_ai_chat_keeps_metadata_only(monkeypatch):
    captured = {}

    async def fake_record_relationship_event(db, **kwargs):
        captured.update(kwargs)
        return None

    monkeypatch.setattr(
        "app.services.privacy_audit.record_relationship_event",
        fake_record_relationship_event,
    )

    asyncio.run(
        log_privacy_ai_chat(
            object(),
            model="test-model",
            provider="compatible-gateway",
            run_type="daily_report",
            scope="solo",
            user_id=uuid.uuid4(),
            raw_messages=[{"role": "user", "content": "联系我 13800138000"}],
            redacted_messages=[{"role": "user", "content": "联系我 138****8000"}],
            raw_output="建议先放慢语气",
            latency_ms=123,
        )
    )

    payload = captured["payload"]
    assert captured["event_type"] == "privacy.ai.chat.logged"
    assert "13800138000" not in payload["input_summary_redacted"]
    assert payload["input_hash"]
    assert payload["output_hash"]
    assert "raw_prompt" not in payload
    assert "raw_output" not in payload
    assert payload["status"] == "completed"


def test_openapi_includes_privacy_phase2_routes():
    schema = app.openapi()
    paths = schema["paths"]

    assert "/api/v1/privacy/status" in paths
    assert "/api/v1/privacy/delete-request" in paths
    assert "/api/v1/admin/privacy/audits" in paths
    assert "/api/v1/admin/privacy/retention/sweep" in paths
    assert "/api/v1/admin/privacy/benchmarks" in paths
