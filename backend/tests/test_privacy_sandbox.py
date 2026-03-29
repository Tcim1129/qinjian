import asyncio
from types import SimpleNamespace

import app.ai as ai_module
from app.api.v1 import auth
from app.schemas import PhoneSendCodeRequest
from app.services.privacy_audit import privacy_audit_scope
from app.services.privacy_sandbox import (
    mask_phone,
    redact_message_payload,
    redact_sensitive_text,
)


class _FakePhoneCodeStore:
    async def get(self, phone: str):
        return None

    async def set(self, phone: str, entry):
        self.phone = phone
        self.entry = entry


def test_redact_sensitive_text_masks_common_identifiers():
    text = (
        "联系我 13800138000，邮箱 tester@example.com，"
        "会话 123e4567-e89b-12d3-a456-426614174000，"
        "令牌 eyJhbGciOiJIUzI1NiJ9.payload.signature。"
    )

    redacted = redact_sensitive_text(text)

    assert "13800138000" not in redacted
    assert "tester@example.com" not in redacted
    assert "123e4567-e89b-12d3-a456-426614174000" not in redacted
    assert "eyJhbGciOiJIUzI1NiJ9.payload.signature" not in redacted
    assert "138****8000" in redacted
    assert "t***@example.com" in redacted
    assert "[UUID]" in redacted
    assert "[TOKEN]" in redacted


def test_redact_message_payload_preserves_image_url_and_masks_text():
    messages = [
        {
            "role": "user",
            "content": [
                {"type": "text", "text": "请联系 13800138000"},
                {
                    "type": "image_url",
                    "image_url": {"url": "data:image/png;base64,AAAA"},
                },
            ],
        }
    ]

    redacted = redact_message_payload(messages, enabled=True)

    assert redacted[0]["content"][0]["text"] == "请联系 138****8000"
    assert redacted[0]["content"][1]["image_url"]["url"] == "data:image/png;base64,AAAA"


def test_create_chat_completion_redacts_messages_before_provider(monkeypatch):
    captured = {}

    async def fake_create(**kwargs):
        captured.update(kwargs)
        return SimpleNamespace(
            choices=[SimpleNamespace(message=SimpleNamespace(content="ok"))]
        )

    monkeypatch.setattr(ai_module.client.chat.completions, "create", fake_create)
    monkeypatch.setattr(ai_module.settings, "PRIVACY_SANDBOX_ENABLED", True)
    monkeypatch.setattr(ai_module.settings, "PRIVACY_REDACT_LLM_INPUT", True)

    asyncio.run(
        ai_module.create_chat_completion(
            model="test-model",
            messages=[{"role": "user", "content": "手机号 13800138000"}],
            temperature=0.2,
        )
    )

    assert captured["messages"][0]["content"] == "手机号 138****8000"


def test_create_chat_completion_emits_metadata_only_privacy_audit(monkeypatch):
    provider_calls = {}
    audit_calls = {}

    async def fake_create(**kwargs):
        provider_calls.update(kwargs)
        return SimpleNamespace(
            choices=[SimpleNamespace(message=SimpleNamespace(content="请改成温和一点的说法"))]
        )

    async def fake_log_privacy_ai_chat(db, **kwargs):
        audit_calls.update(kwargs)
        return None

    monkeypatch.setattr(ai_module.client.chat.completions, "create", fake_create)
    monkeypatch.setattr(ai_module, "log_privacy_ai_chat", fake_log_privacy_ai_chat)
    monkeypatch.setattr(ai_module.settings, "PRIVACY_SANDBOX_ENABLED", True)
    monkeypatch.setattr(ai_module.settings, "PRIVACY_REDACT_LLM_INPUT", True)
    monkeypatch.setattr(ai_module.settings, "PRIVACY_AUDIT_ENABLED", True)

    async def _run():
        with privacy_audit_scope(
            db=object(),
            user_id="123e4567-e89b-12d3-a456-426614174000",
            scope="solo",
            run_type="unit_test",
        ):
            await ai_module.create_chat_completion(
                model="test-model",
                messages=[{"role": "user", "content": "联系我 13800138000"}],
                temperature=0.2,
            )

    asyncio.run(_run())

    assert provider_calls["messages"][0]["content"] == "联系我 138****8000"
    assert audit_calls["run_type"] == "unit_test"
    assert audit_calls["redacted_messages"][0]["content"] == "联系我 138****8000"
    assert audit_calls["raw_output"] == "请改成温和一点的说法"


def test_send_phone_code_logs_masked_phone_without_raw_code(monkeypatch, caplog):
    store = _FakePhoneCodeStore()
    monkeypatch.setattr(auth, "_resolve_phone_code_store", lambda: store)
    monkeypatch.setattr(auth, "_generate_phone_code", lambda: "123456")
    monkeypatch.setattr(auth.settings, "DEBUG", True)
    monkeypatch.setattr(auth.settings, "PHONE_CODE_DEBUG_RETURN", False)
    monkeypatch.setattr(auth.settings, "PRIVACY_SANDBOX_ENABLED", True)
    monkeypatch.setattr(auth.settings, "PRIVACY_MASK_LOGS", True)

    request = PhoneSendCodeRequest(phone="13800138000")

    with caplog.at_level("INFO"):
        payload = asyncio.run(auth.send_phone_code(request))

    assert payload == {"message": "验证码已发送"}
    assert "123456" not in caplog.text
    assert "13800138000" not in caplog.text
    assert mask_phone("13800138000") in caplog.text
