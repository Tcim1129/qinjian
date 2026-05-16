from app.main import app


def test_admin_router_keeps_policy_paths():
    schema = app.openapi()
    paths = schema["paths"]

    assert "/api/v1/admin/policies" in paths
    assert "/api/v1/admin/policies/{policy_id}/audit" in paths
