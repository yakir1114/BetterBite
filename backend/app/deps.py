"""Shared FastAPI dependencies (DB session, current user).

``get_current_user`` is a placeholder until the auth module lands. Per
docs/02 §5.2 and CLAUDE.md, it will verify the Firebase ID token and resolve
the ``users`` row by ``firebase_uid``; every protected route depends on it so
queries can be scoped by ``user_id``.
"""

from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import async_session


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Yield a request-scoped async DB session."""
    async with async_session() as session:
        yield session


async def get_current_user() -> None:  # pragma: no cover - implemented in auth module
    """Resolve the authenticated user from the Firebase ID token.

    Not yet implemented — the ``auth`` module will replace this. It exists here
    so the dependency import path is stable for feature modules built later.
    """
    raise NotImplementedError("Auth module not yet implemented (see app/auth/).")
