import asyncio
import shutil
from types import SimpleNamespace
from pathlib import Path

from app.ai import reporter
from app.core.config import settings


def test_default_multimodal_model_targets_qwen_flash():
    assert settings.AI_MULTIMODAL_MODEL == "qwen3.8-flash"
    assert settings.AI_MULTIMODAL_FALLBACK_MODEL == "qwen3.8-flash"


def test_analyze_image_uses_configured_multimodal_model_and_png_data_url(monkeypatch):
    upload_dir = Path("tmp/test-reporter-multimodal/uploads")
    if upload_dir.parent.exists():
        shutil.rmtree(upload_dir.parent)
    image_dir = upload_dir / "images"
    image_dir.mkdir(parents=True)
    image_file = image_dir / "scene.png"
    image_file.write_bytes(b"\x89PNG\r\n\x1a\n" + (b"\x00" * 16))

    captured = {}

    async def fake_create_chat_completion(**kwargs):
        captured.update(kwargs)
        return SimpleNamespace(
            choices=[
                SimpleNamespace(
                    message=SimpleNamespace(
                        content='{"scene_summary":"一对情侣在聊天截图里慢慢修复误会","mood":"温柔里带着疲惫","mood_tags":["疲惫","委屈","修复"],"relationship_stage":"修复中","interaction_signal":"双方都在把误会往说开推进","social_signal":"能看到明显的安抚与靠近信号","risk_level":"watch","risk_flags":["双方都比较脆弱"],"care_points":["适合记录对方回应中的安抚动作"],"privacy_sensitivity":"high","privacy_reasons":["这是一张聊天截图"],"retention_recommendation":"analysis_only","retention_reason":"更适合保留分析结果，不长期保存原图","score":8}'
                    )
                )
            ]
        )

    monkeypatch.setattr(reporter.settings, "UPLOAD_DIR", str(upload_dir))
    monkeypatch.setattr(
        reporter.settings,
        "AI_MULTIMODAL_MODEL",
        "qwen3.7-plus-2026-05-26",
    )
    monkeypatch.setattr(reporter, "create_chat_completion", fake_create_chat_completion)

    result = asyncio.run(
        reporter.analyze_image("/uploads/images/scene.png", context="聊天截图")
    )

    assert captured["model"] == "qwen3.7-plus-2026-05-26"
    assert captured["temperature"] == 0.4
    assert (
        captured["messages"][1]["content"][1]["image_url"]["url"].startswith(
            "data:image/png;base64,"
        )
        is True
    )
    assert "背景信息：聊天截图" in captured["messages"][1]["content"][0]["text"]
    assert "display_mood_tags" in captured["messages"][1]["content"][0]["text"]
    assert "emotion_weights" in captured["messages"][1]["content"][0]["text"]
    assert "emotion_blend_summary" in captured["messages"][1]["content"][0]["text"]
    assert result == {
        "scene_summary": "一对情侣在聊天截图里慢慢修复误会",
        "mood": "温柔里带着疲惫",
        "mood_tags": ["疲惫", "委屈", "修复"],
        "relationship_stage": "修复中",
        "interaction_signal": "双方都在把误会往说开推进",
        "social_signal": "能看到明显的安抚与靠近信号",
        "risk_level": "watch",
        "risk_flags": ["双方都比较脆弱"],
        "care_points": ["适合记录对方回应中的安抚动作"],
        "privacy_sensitivity": "high",
        "privacy_reasons": ["这是一张聊天截图"],
        "retention_recommendation": "analysis_only",
        "retention_reason": "更适合保留分析结果，不长期保存原图",
        "score": 8,
    }
