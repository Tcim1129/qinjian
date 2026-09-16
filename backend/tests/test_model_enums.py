from app.models import (
    CrisisAlert,
    Pair,
    PairChangeRequest,
    RelationshipTask,
    Report,
    RelationshipTree,
)


def test_model_enums_use_lowercase_database_values():
    assert Report.__table__.c.type.type.enums == ["daily", "weekly", "monthly", "solo"]
    assert Report.__table__.c.status.type.enums == ["pending", "completed", "failed"]
    assert Pair.__table__.c.type.type.enums == [
        "couple",
        "friend",
        "spouse",
        "bestfriend",
        "parent",
    ]
    assert Pair.__table__.c.status.type.enums == ["pending", "active", "ended"]
    assert PairChangeRequest.__table__.c.kind.type.enums == [
        "join_request",
        "type_change",
        "break_request",
    ]
    assert PairChangeRequest.__table__.c.phase.type.enums == [
        "awaiting_timeout",
        "awaiting_retention_choice",
        "retaining",
    ]
    assert PairChangeRequest.__table__.c.resolution_reason.type.enums == [
        "no_retention_timeout",
        "partner_declined",
        "choice_timeout",
        "retention_rejected",
        "retention_timeout",
        "retention_accepted",
        "requester_cancelled",
    ]
    assert RelationshipTask.__table__.c.status.type.enums == [
        "pending",
        "completed",
        "skipped",
    ]
    assert RelationshipTree.__table__.c.level.type.enums == [
        "seed",
        "sprout",
        "sapling",
        "tree",
        "big_tree",
        "forest",
    ]
    assert CrisisAlert.__table__.c.level.type.enums == [
        "none",
        "mild",
        "moderate",
        "severe",
    ]
