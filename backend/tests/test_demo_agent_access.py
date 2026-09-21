from __future__ import annotations

import asyncio
import uuid
from pathlib import Path
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.api.v1 import agent as agent_api
from app.core.database import Base, get_db
from app.core.config import settings
from app.api.deps import DEMO_MODE_TOKEN, DEMO_PERSONA_PAIRS


def test_demo_agent_sessions_for_all_personas():
    settings.ALLOW_DEMO_AGENT = True
    db_dir = Path(__file__).resolve().parents[1] / ".test-dbs"
    db_dir.mkdir(exist_ok=True)
    db_path = db_dir / f"demo-agent-{uuid.uuid4().hex}.db"
    engine = create_async_engine(f"sqlite+aiosqlite:///{db_path}")
    sessionmaker = async_sessionmaker(engine, expire_on_commit=False)

    async def setup_database():
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

    asyncio.run(setup_database())

    async def override_get_db():
        async with sessionmaker() as db:
            yield db

    app = FastAPI()
    # router has prefix="/agent", so including under /api/v1 yields /api/v1/agent/...
    app.include_router(agent_api.router, prefix="/api/v1")
    app.dependency_overrides[get_db] = override_get_db

    client = TestClient(app)
    headers = {"Authorization": f"Bearer {DEMO_MODE_TOKEN}"}

    # Test creating sessions for all 3 demo personas
    for persona_pair_id, _, _ in DEMO_PERSONA_PAIRS[:3]:
        resp = client.post(
            f"/api/v1/agent/sessions?pair_id={persona_pair_id}",
            headers=headers,
        )
        assert resp.status_code == 200, f"Failed for {persona_pair_id}: {resp.text}"
        data = resp.json()
        assert "session_id" in data
