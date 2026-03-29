from fastapi.testclient import TestClient

from app.api.v1 import ws as ws_module
from app.core.config import settings
from app.core.security import create_realtime_ws_ticket
from app.main import app


class FakeRealtimeASRClient:
    def __init__(self):
        import asyncio

        self.events = asyncio.Queue()
        self.received_audio: list[str] = []

    async def connect(self):
        return None

    async def start_session(self):
        await self.events.put(
            {
                "type": "conversation.item.input_audio_transcription.text",
                "text": "今天有点累",
            }
        )

    async def send_audio_chunk(self, audio_base64: str):
        self.received_audio.append(audio_base64)

    async def stop_session(self):
        await self.events.put(
            {
                "type": "conversation.item.input_audio_transcription.completed",
                "text": "今天有点累，但已经缓过来了",
            }
        )

    async def recv_event(self):
        return await self.events.get()

    async def close(self):
        return None


def test_realtime_asr_websocket_bridges_partial_and_final_events(monkeypatch):
    original_secret_key = settings.SECRET_KEY
    settings.SECRET_KEY = "0123456789abcdef0123456789abcdef"
    fake_client = FakeRealtimeASRClient()
    monkeypatch.setattr(
        ws_module,
        "create_realtime_asr_client",
        lambda **kwargs: fake_client,
    )

    try:
        ticket = create_realtime_ws_ticket("user-789")
        with TestClient(app) as client:
            with client.websocket_connect(
                f"/api/v1/agent/asr/realtime?ticket={ticket}",
                headers={"host": "localhost"},
            ) as websocket:
                websocket.send_json(
                    {
                        "type": "session.start",
                        "format": "pcm",
                        "sample_rate": 16000,
                        "language": "zh",
                    }
                )
                partial = websocket.receive_json()
                assert partial == {"type": "partial", "text": "今天有点累"}

                websocket.send_json({"type": "audio.chunk", "audio": "Zm9v"})
                websocket.send_json({"type": "session.stop"})
                final = websocket.receive_json()

                assert final == {
                    "type": "final",
                    "text": "今天有点累，但已经缓过来了",
                }
                assert fake_client.received_audio == ["Zm9v"]
    finally:
        settings.SECRET_KEY = original_secret_key
