# BetterBite — Backend

Python 3.12 · FastAPI · SQLAlchemy 2.x (async) · Alembic · PostgreSQL 15+.

See `../CLAUDE.md` and `../docs/` for conventions and the spec (the source of truth).

## Setup

```bash
cd backend
uv sync                                   # install deps (creates .venv)
cp ../.env.example .env                    # fill in real values; never commit .env
```

## Run

```bash
uv run uvicorn app.main:app --reload      # http://127.0.0.1:8000  (GET /health)
```

## Database / migrations

```bash
uv run alembic upgrade head                       # apply migrations
uv run alembic revision --autogenerate -m "msg"   # create a migration from model changes
```

`DATABASE_URL` must point at a reachable Postgres (async driver), e.g.
`postgresql+asyncpg://postgres:postgres@localhost:5432/betterbite`.
The initial migration enables the `pgcrypto` and `pg_trgm` extensions.

## Tests

```bash
uv run pytest                              # the /health test needs no database
```

## Layout

```
app/
  main.py        # FastAPI app + router registration; GET /health
  config.py      # settings from env (pydantic-settings)
  deps.py        # shared deps: get_db, get_current_user (auth: TODO)
  errors.py      # standard error envelope + handlers
  db/            # Base, async engine/session, models.py (full schema)
  ai/            # AIVisionProvider / AITextProvider adapter interfaces
  auth/ users/ meals/ foods/ nutrition/ gamification/ stats/ weight/ water/ notifications/
alembic/         # migration env + versions
tests/
```

> AI provider SDKs may only be imported under `app/ai/`. Storage is metric.
> Every protected route resolves the user via Firebase token and scopes queries by `user_id`.
