from app.main import app


def test_openapi_includes_product_description_and_tag_metadata():
    schema = app.openapi()

    assert schema["info"]["title"] == app.title
    assert "关系智能" in schema["info"]["description"]
    assert "/api/v1/agent/simulate-message" in schema["paths"]
    assert "/api/v1/interactions/events" in schema["paths"]

    tags = {tag["name"]: tag for tag in schema.get("tags", [])}
    assert tags["认证"]["description"] == "注册、登录、手机号验证码与账号资料维护。"
    assert tags["交互日志"]["description"] == "用户页面浏览、关键操作与 API 交互事件采集。"
    assert tags["关系智能"]["description"] == "关系画像、时间轴、干预计划、策略审计与叙事对齐接口。"
    assert "/api/v1/agent/asr/ws-ticket" in schema["paths"]


def test_app_registers_realtime_asr_websocket_route():
    websocket_paths = [
        getattr(route, "path", "")
        for route in app.routes
        if "websocket" in route.__class__.__name__.lower()
    ]

    assert "/api/v1/agent/asr/realtime" in websocket_paths
