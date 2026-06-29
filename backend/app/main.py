"""FastAPI application entrypoint and router registration.

Feature routers (auth, users, meals, ...) get mounted under the ``/api/v1``
base path as they are built. ``GET /health`` is intentionally unauthenticated
and lives at the root (liveness probe) per docs/04_API_Spec.md §16.
"""

from fastapi import APIRouter, FastAPI

from app.config import get_settings
from app.errors import register_exception_handlers


def create_app() -> FastAPI:
    settings = get_settings()

    app = FastAPI(
        title="BetterBite API",
        version="0.1.0",
        description="Backend for BetterBite — AI nutrition tracking.",
    )

    register_exception_handlers(app)

    @app.get("/health", tags=["system"])
    async def health() -> dict[str, str]:
        return {"status": "ok"}

    # Versioned API surface. Feature module routers are included here as they
    # are implemented (see docs/04_API_Spec.md §17 for the full endpoint map).
    api_v1 = APIRouter(prefix=settings.api_base_path)
    app.include_router(api_v1)

    return app


app = create_app()
