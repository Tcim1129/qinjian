from __future__ import annotations

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.v1.admin_routes import decision_replay as decision_replay_api
from app.api.v1.admin_routes import shared as admin_shared


def test_decision_replay_route_returns_fixed_cases(monkeypatch):
    app = FastAPI()
    app.include_router(decision_replay_api.router)

    async def override_get_db():
        yield None

    class FakeUser:
        id = "user-1"

    async def override_current_user():
        return FakeUser()

    async def override_admin_user():
        return FakeUser()

    app.dependency_overrides[decision_replay_api.get_db] = override_get_db
    app.dependency_overrides[decision_replay_api.get_admin_user] = override_admin_user

    with TestClient(app, raise_server_exceptions=False) as client:
        response = client.get("/decision-replay")

    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload["cases"]
    assert {case["task"] for case in payload["cases"]} >= {"message_simulation", "alignment"}


def test_decision_evaluation_uses_scope_resolution(monkeypatch):
    app = FastAPI()
    app.include_router(decision_replay_api.router)

    async def override_get_db():
        yield None

    class FakeUser:
        id = "user-1"

    async def override_current_user():
        return FakeUser()

    async def override_admin_user():
        return FakeUser()

    captured = {}

    async def fake_build_intervention_evaluation(db, *, pair_id=None, user_id=None):
        captured["pair_id"] = pair_id
        captured["user_id"] = user_id
        return {"plan_id": "plan-1"}

    async def fake_resolve_scope(*, pair_id, mode, user, db):
        captured["resolved_pair_id"] = pair_id
        captured["resolved_mode"] = mode
        captured["resolved_user_id"] = user.id
        return None, user.id

    app.dependency_overrides[decision_replay_api.get_db] = override_get_db
    app.dependency_overrides[decision_replay_api.get_admin_user] = override_admin_user
    monkeypatch.setattr(decision_replay_api, "build_intervention_evaluation", fake_build_intervention_evaluation)
    monkeypatch.setattr(decision_replay_api, "resolve_scope", fake_resolve_scope)

    with TestClient(app, raise_server_exceptions=False) as client:
        response = client.get("/decision-evaluation", params={"mode": "solo"})

    assert response.status_code == 200, response.text
    assert captured["resolved_mode"] == "solo"
    assert captured["user_id"] == "user-1"
    assert captured["pair_id"] is None
    assert captured["user_id"] == "user-1"


def test_decision_replay_route_rejects_non_admin(monkeypatch):
    app = FastAPI()
    app.include_router(decision_replay_api.router)

    async def override_get_db():
        yield None

    class FakeUser:
        id = "user-1"
        email = "ordinary@example.com"

    async def override_current_user():
        return FakeUser()

    app.dependency_overrides[decision_replay_api.get_db] = override_get_db
    app.dependency_overrides[admin_shared.get_current_user] = override_current_user
    monkeypatch.setattr(admin_shared.settings, "ADMIN_EMAILS", "admin@example.com")

    with TestClient(app, raise_server_exceptions=False) as client:
        response = client.get("/decision-replay")

    assert response.status_code == 403
