from collections.abc import AsyncGenerator
from pathlib import Path

from sqlalchemy.engine import make_url
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from app.core.config import settings


class Base(DeclarativeBase):
    pass


_engine = None
_session_factory = None


def get_engine():
    global _engine
    if _engine is None:
        engine_kwargs = {
            "pool_pre_ping": not settings.IS_SQLITE,
        }
        if settings.IS_SQLITE:
            engine_kwargs["connect_args"] = {"check_same_thread": False}
        else:
            engine_kwargs["pool_recycle"] = 1800

        _engine = create_async_engine(
            settings.DATABASE_URL,
            **engine_kwargs,
        )
    return _engine


def get_session_factory():
    global _session_factory
    if _session_factory is None:
        _session_factory = async_sessionmaker(
            autocommit=False,
            autoflush=False,
            bind=get_engine(),
            class_=AsyncSession,
            expire_on_commit=False,
        )
    return _session_factory


class _SessionLocalProxy:
    def __call__(self, *args, **kwargs):
        return get_session_factory()(*args, **kwargs)


SessionLocal = _SessionLocalProxy()


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with SessionLocal() as session:
        yield session


async def init_database() -> None:
    """本地 SQLite 模式下自动初始化数据库，避免依赖 Alembic 和 PostgreSQL。"""
    if not settings.IS_SQLITE:
        return

    url = make_url(settings.DATABASE_URL)
    database_path = url.database
    if database_path and database_path != ":memory:":
        Path(database_path).parent.mkdir(parents=True, exist_ok=True)

    async with get_engine().begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
