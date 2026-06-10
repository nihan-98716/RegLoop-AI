"""Database engine and session configuration.

Supports SQLite (default/dev) and PostgreSQL (Docker/production-like).
The active database is chosen by the DATABASE_URL environment variable.
"""

from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from app.config import settings
from app.logging_config import get_logger

log = get_logger(__name__)

# ---------------------------------------------------------------------------
# Engine
# ---------------------------------------------------------------------------

_connect_args: dict = {}

if settings.database_url.startswith("sqlite"):
    # SQLite requires check_same_thread=False for async use
    _connect_args = {"check_same_thread": False}

engine = create_async_engine(
    settings.database_url,
    echo=settings.app_env == "development",
    connect_args=_connect_args,
)

AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


# ---------------------------------------------------------------------------
# Declarative base
# ---------------------------------------------------------------------------


class Base(DeclarativeBase):
    """Shared declarative base for all ORM models."""


# ---------------------------------------------------------------------------
# Dependency
# ---------------------------------------------------------------------------


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency that yields a database session."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def init_db() -> None:
    """Create all tables. Used for SQLite dev startup and tests."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    log.info("database.initialized", url=settings.database_url)
