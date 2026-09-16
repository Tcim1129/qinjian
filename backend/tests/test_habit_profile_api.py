import asyncio
import uuid
from datetime import datetime, timezone

from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.api.deps import get_current_user
from app.api.v1 import auth
from app.core.database import Base, get_db
from app.models import User


def test_habits_save_reload_and_omitted_update_preserves_them():
    engine = create_async_engine('sqlite+aiosqlite:///:memory:')
    sessions = async_sessionmaker(engine, expire_on_commit=False)
    user_id = uuid.uuid4()

    async def setup():
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        async with sessions() as db:
            db.add(User(id=user_id, email='habits@test.local', nickname='测试', password_hash='unused', created_at=datetime.now(timezone.utc)))
            await db.commit()
    asyncio.run(setup())

    async def db_override():
        async with sessions() as db:
            yield db
            await db.commit()

    # Use the same dependency session for the authenticated ORM object.
    from fastapi import Depends
    async def authenticated(db=Depends(get_db)):
        return await db.get(User, user_id)

    app = FastAPI()
    app.include_router(auth.router)
    app.dependency_overrides[get_db] = db_override
    app.dependency_overrides[get_current_user] = authenticated
    try:
        with TestClient(app) as client:
            habits = {'taboos': [' 不要催促 ', '不要催促'], 'comfort_preferences': ['先听我说'], 'custom_notes': '晚点再聊'}
            response = client.put('/auth/me', json={'habit_profile': habits, 'tone_preference': 'direct'})
            assert response.status_code == 200, response.text
            assert response.json()['habit_profile']['taboos'] == ['不要催促']
            assert client.get('/auth/me').json()['habit_profile']['custom_notes'] == '晚点再聊'
            response = client.put('/auth/me', json={'response_length': 'short'})
            assert response.json()['habit_profile']['comfort_preferences'] == ['先听我说']
            assert client.put('/auth/me', json={'habit_profile': {'custom_notes': 'x' * 201}}).status_code == 422
            assert client.put('/auth/me', json={'habit_profile': {}}).json()['habit_profile']['taboos'] == []
    finally:
        asyncio.run(engine.dispose())
