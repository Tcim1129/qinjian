from collections import Counter
from types import SimpleNamespace
import uuid

import pytest

from app.services.assessment_item_bank import (
    ASSESSMENT_ITEM_BANK,
    CORE_ITEMS,
    DIMENSION_LABELS,
    ROTATION_ITEMS,
    build_weekly_assessment_pack,
)
from app.models import PairType
from app.services.weekly_assessments import _normalize_answers


class DummyScalarResult:
    def all(self):
        return []


class DummyExecuteResult:
    def scalars(self):
        return DummyScalarResult()


class DummyAsyncSession:
    def __init__(self, pair=None):
        self.pair = pair

    async def execute(self, *_args, **_kwargs):
        return DummyExecuteResult()

    async def get(self, _model, _identity):
        return self.pair


@pytest.mark.anyio
async def test_build_weekly_assessment_pack_returns_fixed_ten_items():
    payload = await build_weekly_assessment_pack(
        DummyAsyncSession(),
        user_id=uuid.uuid4(),
    )

    assert payload["title"] == "自我诊断"
    assert "只看你自己" in payload["subtitle"]
    assert len(payload["items"]) == 10
    assert len([item for item in payload["items"] if item["track"] == "core"]) == 6
    assert len([item for item in payload["items"] if item["track"] == "rotation"]) == 4
    assert len({item["item_id"] for item in payload["items"]}) == 10
    assert all(len(item["options"]) == 5 for item in payload["items"])
    assert payload["items"][0]["prompt"].startswith("过去一周里，我还能")


def test_normalize_answers_keeps_item_and_option_ids():
    answers = _normalize_answers(
        [
            {
                "item_id": "anchor-connection-1",
                "dim": "沟通质量",
                "score": 75,
                "option_id": "opt_75",
            }
        ]
    )

    assert answers == [
        {
            "item_id": "anchor-connection-1",
            "dim": "沟通质量",
            "score": 75,
            "option_id": "opt_75",
        }
    ]


def test_assessment_item_bank_expands_rotation_pool_for_all_dimensions():
    assert len(ASSESSMENT_ITEM_BANK) >= 30
    assert len(CORE_ITEMS) == 6

    rotation_counts = Counter(item["dimension"] for item in ROTATION_ITEMS)
    assert all(rotation_counts[dimension] >= 6 for dimension in DIMENSION_LABELS)


@pytest.mark.anyio
async def test_build_weekly_assessment_pack_uses_friend_profile_copy():
    payload = await build_weekly_assessment_pack(
        DummyAsyncSession(pair=SimpleNamespace(type=PairType.FRIEND, is_long_distance=False)),
        pair_id=uuid.uuid4(),
    )

    assert payload["title"] == "友情体检"
    assert "友情" in payload["subtitle"]
    assert "友情" in payload["items"][0]["prompt"]


@pytest.mark.anyio
async def test_build_weekly_assessment_pack_uses_long_distance_profile_copy():
    payload = await build_weekly_assessment_pack(
        DummyAsyncSession(pair=SimpleNamespace(type=PairType.COUPLE, is_long_distance=True)),
        pair_id=uuid.uuid4(),
    )

    assert payload["title"] == "异地关系体检"
    assert "异地关系" in payload["subtitle"]
    assert "隔着距离" in payload["items"][0]["prompt"]


@pytest.mark.anyio
async def test_weekly_assessment_trend_handles_single_first_submission():
    from datetime import datetime
    from app.services.weekly_assessments import get_weekly_assessment_trend

    single_event = SimpleNamespace(
        id=uuid.uuid4(),
        pair_id=uuid.uuid4(),
        user_id=None,
        occurred_at=datetime(2026, 11, 25, 10, 0, 0),
        created_at=datetime(2026, 11, 25, 10, 0, 0),
        payload={
            "total_score": 82,
            "dimension_scores": [{"id": "connection", "label": "连接与表达", "score": 82, "status": "strong"}],
            "change_summary": "第一次评估",
        },
    )

    class OneEventSession:
        async def execute(self, *_args, **_kwargs):
            return SimpleNamespace(scalars=lambda: SimpleNamespace(all=lambda: [single_event]))

    trend = await get_weekly_assessment_trend(OneEventSession(), pair_id=single_event.pair_id, limit=4)
    assert trend["latest_score"] == 82
    assert len(trend["trend_points"]) == 1
    assert "第一次" in trend["change_summary"]
