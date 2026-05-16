import uuid
from types import SimpleNamespace

import pytest
from fastapi import HTTPException

from app.api.v1.tasks import _ensure_task_operator, _task_visible_to_user


def test_task_visible_to_user_allows_shared_and_owned_tasks():
    current_user_id = uuid.uuid4()
    current_user = SimpleNamespace(id=current_user_id)

    shared_task = SimpleNamespace(user_id=None)
    owned_task = SimpleNamespace(user_id=current_user_id)

    assert _task_visible_to_user(shared_task, current_user) is True
    assert _task_visible_to_user(owned_task, current_user) is True


def test_task_visible_to_user_hides_partner_only_task():
    current_user = SimpleNamespace(id=uuid.uuid4())
    partner_task = SimpleNamespace(user_id=uuid.uuid4())

    assert _task_visible_to_user(partner_task, current_user) is False


def test_ensure_task_operator_rejects_partner_only_task_completion():
    user_a_id = uuid.uuid4()
    user_b_id = uuid.uuid4()
    pair = SimpleNamespace(user_a_id=user_a_id, user_b_id=user_b_id)
    task = SimpleNamespace(user_id=user_b_id)
    current_user = SimpleNamespace(id=user_a_id)

    with pytest.raises(HTTPException) as exc_info:
        _ensure_task_operator(task, current_user, pair)

    assert exc_info.value.status_code == 403
    assert exc_info.value.detail == "该任务仅限指定用户操作"
