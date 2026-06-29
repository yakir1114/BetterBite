"""Database package: declarative base, engine/session, and ORM models.

Importing this package imports ``models`` so that ``Base.metadata`` is fully
populated (Alembic autogenerate and tests rely on this).
"""

from app.db import models  # noqa: F401  (populate Base.metadata)
from app.db.base import Base
from app.db.session import async_session, engine

__all__ = ["Base", "async_session", "engine", "models"]
