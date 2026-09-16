from app.main import app


def test_split_insights_router_keeps_public_paths():
    schema = app.openapi()
    paths = schema["paths"]

    expected_paths = [
        "/api/v1/insights/safety/status",
        "/api/v1/insights/assessments/weekly-pack",
        "/api/v1/insights/assessments/latest",
        "/api/v1/insights/profile/latest",
        "/api/v1/insights/timeline",
        "/api/v1/insights/timeline/archive",
        "/api/v1/insights/timeline/archive/export",
        "/api/v1/insights/timeline/archive/items/{item_id}/export",
        "/api/v1/insights/plans/policy-audit",
        "/api/v1/insights/playbook/active",
        "/api/v1/insights/methodology",
        "/api/v1/insights/alignment/latest",
        "/api/v1/insights/alignment/generate",
    ]

    for path in expected_paths:
        assert path in paths
