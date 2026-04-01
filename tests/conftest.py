import os

import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.api.deps import get_db
from app.core.config import settings
from app.core.database import Base
from app.main import app


@pytest_asyncio.fixture
async def db_session(tmp_path, monkeypatch):
    db_path = tmp_path / "test.db"
    engine = create_async_engine(f"sqlite+aiosqlite:///{db_path}")
    session_factory = async_sessionmaker(engine, expire_on_commit=False)

    monkeypatch.setattr(settings, "UPLOAD_DIR", str(tmp_path / "uploads"), raising=False)
    monkeypatch.setattr(settings, "RESULT_DIR", str(tmp_path / "results"), raising=False)
    monkeypatch.setattr(settings, "API_TOKEN", "test-token", raising=False)
    monkeypatch.setattr(settings, "TASK_RUNNER", "worker", raising=False)
    os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
    os.makedirs(settings.RESULT_DIR, exist_ok=True)

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with session_factory() as session:
        yield session

    await engine.dispose()


@pytest_asyncio.fixture
async def client(db_session):
    async def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://testserver",
        headers={"Authorization": "Bearer test-token"},
    ) as async_client:
        yield async_client

    app.dependency_overrides.clear()
