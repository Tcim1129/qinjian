from app.api.v1.insights_routes.timeline import _timeline_impact_modules_for_event
from app.models import RelationshipEvent


def test_timeline_impact_modules_for_message_simulation():
    event = RelationshipEvent(
        event_type="message.simulated",
        entity_type="message_simulation",
        payload={"risk_level": "high"},
    )

    modules = _timeline_impact_modules_for_event(event)

    assert modules[0] == "时间轴证据"
    assert "消息预演" in modules
    assert "表达建议" in modules


def test_timeline_impact_modules_for_report_completed():
    event = RelationshipEvent(
        event_type="report.completed",
        entity_type="report",
        payload={"health_score": 78},
    )

    modules = _timeline_impact_modules_for_event(event)

    assert "关系简报" in modules
    assert "策略判断" in modules


def test_timeline_impact_modules_for_client_precheck():
    event = RelationshipEvent(
        event_type="client.precheck.completed",
        entity_type="checkin",
        payload={"risk_level": "watch"},
    )

    modules = _timeline_impact_modules_for_event(event)

    assert "端侧预检" in modules
    assert "隐私保护" in modules
    assert "风险拦截" in modules
