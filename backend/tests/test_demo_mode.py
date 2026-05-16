from fastapi.testclient import TestClient

from app.main import app


def test_demo_mode_allows_read_requests():
    client = TestClient(app, base_url="http://localhost")

    response = client.get("/api/health", headers={"X-QJ-Demo-Mode": "1"})

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_demo_mode_blocks_write_requests_before_business_logic():
    client = TestClient(app, base_url="http://localhost")

    response = client.post(
        "/api/v1/privacy/delete-request",
        headers={"X-QJ-Demo-Mode": "1"},
    )

    assert response.status_code == 403
    assert response.json() == {"detail": "Demo Mode is read-only."}
