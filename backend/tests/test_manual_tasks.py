from datetime import date
from types import SimpleNamespace
import uuid

import pytest
from fastapi import HTTPException

from app.api.v1.tasks import _resolve_manual_task_target_user_id, _task_to_dict
from app.models import TaskStatus
from app.services.task_adaptation import (
    build_daily_pack_label,
    build_daily_task_note,
    build_simple_daily_tasks,
)
from app.services.task_feedback import summarize_feedback_map


def test_resolve_manual_task_target_user_id_supports_self_and_both():
    user_a_id = uuid.uuid4()
    user_b_id = uuid.uuid4()
    pair = SimpleNamespace(user_a_id=user_a_id, user_b_id=user_b_id)
    current_user = SimpleNamespace(id=user_a_id)

    assert _resolve_manual_task_target_user_id("self", current_user, pair) == user_a_id
    assert _resolve_manual_task_target_user_id("both", current_user, pair) is None


def test_resolve_manual_task_target_user_id_rejects_partner_scope():
    user_a_id = uuid.uuid4()
    user_b_id = uuid.uuid4()
    pair = SimpleNamespace(user_a_id=user_a_id, user_b_id=user_b_id)
    current_user = SimpleNamespace(id=user_a_id)

    with pytest.raises(HTTPException) as exc_info:
        _resolve_manual_task_target_user_id("partner", current_user, pair)

    assert exc_info.value.status_code == 400
    assert exc_info.value.detail == "当前版本暂不支持直接给对方单独布置任务"


def test_task_to_dict_exposes_manual_task_metadata():
    task_id = uuid.uuid4()
    user_id = uuid.uuid4()
    parent_task_id = uuid.uuid4()

    task = SimpleNamespace(
        id=task_id,
        title="今晚先把下一步约出来",
        description="先约一个 10 分钟连接时间。",
        category="communication",
        status=TaskStatus.PENDING,
        user_id=user_id,
        due_date=date(2026, 4, 21),
        completed_at=None,
        source="manual",
        created_by_user_id=user_id,
        parent_task_id=parent_task_id,
    )

    payload = _task_to_dict(task)

    assert payload["source"] == "manual"
    assert payload["is_manual"] is True
    assert payload["target_scope"] == "self"
    assert payload["parent_task_id"] == str(parent_task_id)
    assert payload["created_by_user_id"] == str(user_id)


def test_summarize_feedback_map_tracks_relationship_shift_average():
    summary = summarize_feedback_map(
        {
            "task-1": {
                "usefulness_score": 4,
                "friction_score": 2,
                "relationship_shift_score": 2,
            },
            "task-2": {
                "usefulness_score": 3,
                "friction_score": 3,
                "relationship_shift_score": -1,
            },
        }
    )

    assert summary == {
        "feedback_count": 2,
        "usefulness_avg": 3.5,
        "friction_avg": 2.5,
        "relationship_shift_avg": 0.5,
    }


def test_build_simple_daily_tasks_returns_fixed_three_step_pack():
    tasks = build_simple_daily_tasks(
        {
            "plan_type": "conflict_repair_plan",
            "intensity": "light",
        }
    )

    assert len(tasks) == 3
    assert [task["category"] for task in tasks] == [
        "connection",
        "repair",
        "reflection",
    ]
    assert all(task["target"] == "both" for task in tasks)


def test_daily_task_copy_helpers_return_user_facing_short_text():
    strategy = {"plan_type": "low_connection_recovery", "intensity": "light"}

    assert build_daily_task_note(strategy) == "今天先把联系接回来，不用一次聊很多。"
    assert build_daily_pack_label(strategy) == "今天先轻一点"
