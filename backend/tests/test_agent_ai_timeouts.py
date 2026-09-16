from app.api.v1 import agent


def test_agent_chat_timeout_stays_within_user_facing_minute_limit():
    assert 55 <= agent.AGENT_COMPLETION_TIMEOUT_SECONDS <= 60
