"""Async SQLAlchemy engine + session factory.

The engine is created lazily at import time but does not open a connection until
first use, so importing the app (e.g. to serve ``/health``) never requires a
live database.
"""

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.config import get_settings

settings = get_settings()

engine = create_async_engine(
    settings.database_url,
    echo=False,
    pool_pre_ping=True,
)

async_session = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)
