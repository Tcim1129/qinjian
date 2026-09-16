from app.api.v1.insights_routes.shared import serialize_timeline_event
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


def test_serialize_timeline_event_uses_privacy_labels_and_summary():
    event = RelationshipEvent(
        event_type="privacy.ai.transcription.logged",
        entity_type="privacy_ai_transcription",
        payload={
            "event_label": "记录了一次语音转写调用",
            "summary": "语音转录 completed",
            "status": "completed",
            "input_summary_redacted": "voice.wav",
            "audio_info": {"language_label": "中文"},
        },
    )

    serialized = serialize_timeline_event(event)

    assert serialized["label"] == "记录了一次语音转写调用"
    assert serialized["summary"] == "记录了一次语音转写调用"
    assert serialized["detail"] == "语言：中文，文件：voice.wav"
    assert serialized["category_label"] == "隐私"


def test_serialize_timeline_event_prefers_payload_text_for_unknown_events():
    event = RelationshipEvent(
        event_type="custom.audit.logged",
        entity_type="audit",
        payload={
            "event_label": "自定义审计事件",
            "summary": "这条自定义事件已经写入审计记录。",
        },
    )

    serialized = serialize_timeline_event(event)

    assert serialized["label"] == "自定义审计事件"
    assert serialized["summary"] == "这条自定义事件已经写入审计记录。"
