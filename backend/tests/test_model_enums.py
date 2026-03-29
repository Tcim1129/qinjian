from app.models import (
    CrisisAlert,
    Pair,
    RelationshipTask,
    Report,
    RelationshipTree,
)


def test_model_enums_use_lowercase_database_values():
    assert Report.__table__.c.type.type.enums == ["daily", "weekly", "monthly", "solo"]
    assert Report.__table__.c.status.type.enums == ["pending", "completed", "failed"]
    assert Pair.__table__.c.type.type.enums == ["couple", "spouse", "bestfriend", "parent"]
    assert Pair.__table__.c.status.type.enums == ["pending", "active", "ended"]
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
