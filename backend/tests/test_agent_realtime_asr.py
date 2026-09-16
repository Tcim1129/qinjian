import base64
import wave

import pytest

from app.api.v1 import agent as agent_api
from app.ai import asr as asr_module
from app.ai.asr import ASRTranscriptionResult, create_realtime_asr_client


class _FakeRealtimeProvider:
    def __init__(self, events):
        self._events = list(events)

    async def recv_event(self):
        if not self._events:
            raise RuntimeError("no more realtime events")
        return self._events.pop(0)


class _FakeWebSocket:
    def __init__(self):
        self.payloads = []

    async def send_json(self, payload):
        self.payloads.append(payload)


@pytest.mark.anyio
async def test_realtime_asr_final_payload_includes_chinese_labels_and_score():
    transcript = "今天我其实不是想吵架，我只是希望对方能先听懂我的委屈。"
    provider = _FakeRealtimeProvider(
        [
            {
                "type": "conversation.item.input_audio_transcription.completed",
                "transcript": transcript,
            },
            {
                "type": "session.finished",
                "transcript": transcript,
            },
        ]
    )
    websocket = _FakeWebSocket()

    result = await agent_api._pump_realtime_asr_events(provider, websocket)

    assert result["status"] == "completed"
    assert result["transcript"] == transcript
    final_payload = websocket.payloads[-1]
    assert final_payload["type"] == "final"
    assert final_payload["text"] == transcript
    assert final_payload["transcript_language"] == {
        "code": "zh",
        "label": "中文",
    }
    assert final_payload["voice_emotion"] == {
        "code": "",
        "label": "待识别",
    }
    assert final_payload["content_emotion"]["sentiment"] == "negative"
    assert final_payload["content_emotion"]["sentiment_label"] == "偏负向"
    assert final_payload["content_emotion"]["mood_label"] == "委屈"
    assert final_payload["content_emotion"]["score"] >= 5


def test_realtime_asr_session_max_seconds_is_clamped(monkeypatch):
    monkeypatch.setattr(agent_api.settings, "REALTIME_ASR_MAX_SESSION_SECONDS", 5)
    assert agent_api._realtime_asr_max_session_seconds() == 15

    monkeypatch.setattr(agent_api.settings, "REALTIME_ASR_MAX_SESSION_SECONDS", 120)
    assert agent_api._realtime_asr_max_session_seconds() == 120

    monkeypatch.setattr(agent_api.settings, "REALTIME_ASR_MAX_SESSION_SECONDS", 999)
    assert agent_api._realtime_asr_max_session_seconds() == 300


@pytest.mark.anyio
async def test_batch_realtime_asr_transcribes_buffered_pcm(monkeypatch):
    async def fake_transcribe_file(file_path, *, content_type=None):
        assert content_type == "audio/wav"
        with wave.open(file_path, "rb") as audio_file:
            assert audio_file.getnchannels() == 1
            assert audio_file.getsampwidth() == 2
            assert audio_file.getframerate() == 16000
            assert audio_file.getnframes() == 1600
        return ASRTranscriptionResult(
            text="你好，我今天有一点委屈，但是也想把事情说清楚。",
            provider="openai-compatible",
            model="FunAudioLLM/SenseVoiceSmall",
            audio_info={"language": "zh", "emotion": "neutral"},
        )

    monkeypatch.setattr(asr_module, "transcribe_file", fake_transcribe_file)

    provider = create_realtime_asr_client(provider="batch", sample_rate=16000)
    await provider.connect()
    await provider.start_session()
    await provider.send_audio_chunk(base64.b64encode(b"\x00\x00" * 1600).decode())
    await provider.stop_session()

    completed = await provider.recv_event()
    finished = await provider.recv_event()

    assert completed["type"] == "conversation.item.input_audio_transcription.completed"
    assert completed["transcript"] == "你好，我今天有一点委屈，但是也想把事情说清楚。"
    assert completed["audio_info"] == {"language": "zh", "emotion": "neutral"}
    assert finished["type"] == "session.finished"
