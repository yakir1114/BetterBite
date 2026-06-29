# CLAUDE.md — BetterBite

This file is the source of truth for how this repository works. Read it fully before doing anything. When in doubt, follow the spec docs in `docs/` over your own assumptions.

---

## What we're building

**BetterBite** — a mobile nutrition app. A user photographs a meal, an AI vision model detects the food items and portions, the user confirms/edits, the meal is logged, and an AI coach gives short, specific guidance that learns the user's habits over time.

- **North star:** meals logged per active user per week.
- **The core loop (keep it fast):** open → 📷 → detect → confirm/edit → logged → coach responds → home updates.
- **The differentiator:** the AI Nutrition Coach (longitudinal, not a single-photo calculator). Protect it.

Full vision: `docs/01_Product_Vision.md`.

---

## Stack (locked — flag before changing)

| Layer | Choice |
|---|---|
| Mobile | Flutter (Dart), Android first, iOS after |
| Flutter state mgmt | **Riverpod** — *decision; switch to Bloc here if preferred* |
| Backend | Python 3.12 + FastAPI (async) |
| ORM / migrations | SQLAlchemy 2.x + Alembic |
| Database | PostgreSQL 15+ |
| Validation | Pydantic v2 |
| Auth | Firebase Authentication (backend verifies ID tokens) |
| Image storage | Firebase Storage / GCS |
| Push | Firebase Cloud Messaging |
| AI vision + text | LLM providers behind internal adapters (`app/ai/...`) |
| Backend package mgr | **uv** — *decision; plain venv+pip is fine too* |

---

## Repo layout

```
BetterBite/
  CLAUDE.md                 # this file
  docs/                     # the 12 spec docs — the real source of truth
  backend/
    app/
      main.py               # FastAPI app + router registration
      config.py             # settings from env vars only
      deps.py               # shared deps (db session, current_user)
      auth/ users/ meals/ foods/ nutrition/
      ai/ { vision/ text/ coach/ recipes/ chat/ }
      gamification/ stats/ weight/ water/ notifications/
      db/                   # SQLAlchemy models, session, Alembic
    tests/
    pyproject.toml
  app/                      # Flutter project
    lib/ { core/ features/ shared/ }
    test/
    pubspec.yaml
```

Each backend module follows the same shape: `router.py` (HTTP), `service.py` (logic), `schemas.py` (Pydantic), models live in `db/models.py`.

---

## The spec docs are the source of truth

Before implementing any module, **read its spec doc first.**

| Area | Doc |
|---|---|
| Vision / scope | `01_Product_Vision.md` |
| Architecture / flows | `02_System_Architecture.md` |
| DB schema | `03_Database_Schema.md` |
| API contract | `04_API_Spec.md` |
| Screens | `05_UI_Design.md` *(pending)* |
| Design system | `06_Design_System.md` *(pending)* |
| Food recognition | `07_AI_Food_Recognition.md` *(pending)* |
| Nutrition coach | `08_AI_Nutrition_Coach.md` *(pending)* |
| Recipes | `09_Recipes_Module.md` *(pending)* |
| Gamification | `10_Gamification.md` *(pending)* |
| Notifications | `11_Notifications.md` *(pending)* |
| Testing | `12_Testing_Plan.md` *(pending)* |

If a spec is ambiguous or contradicts this file, stop and ask rather than guessing.

---

## Backend conventions

- **Auth on every route** except `/health`: verify the Firebase ID token, resolve the `users` row by `firebase_uid`.
- **Scope every query by `user_id`.** A user can only read/write their own rows.
- **Storage is metric** (g, kcal, ml, kg, cm). Convert for display at the client edge, never in the DB.
- **Error envelope** (always): `{ "error": { "code", "message", "details" } }`. Codes per `04_API_Spec.md`.
- **Timestamps:** ISO-8601 UTC.
- **AI provider isolation:** never import a provider SDK outside `app/ai/*/`. Everything else calls the `AIVisionProvider` / `AITextProvider` adapter interfaces. Keys live in env only — never in the repo or the app.
- **Schema changes always ship an Alembic migration.** Don't hand-edit the DB.
- **Denormalized totals** (`meals.total_*`, `daily_summaries`) are caches — recompute them in the nutrition service whenever items change; `meal_items` is the source of truth.

## Frontend conventions

- **Feature-first** folders under `lib/features/<feature>/`.
- The app talks **only to our backend** — never to AI providers directly.
- Keep the logging flow fast: camera/gallery → `POST /meals/analyze` (draft) → review/edit → `POST /meals` (save).
- Respect user settings: locale (he/en), units, dark mode.

## API

- Base path `/api/v1`; JSON, `snake_case`; `Authorization: Bearer <firebase_id_token>`.
- AI-backed endpoints (`/meals/analyze`, `/chat/messages`, `/recipes/generate`) are rate-limited.

---

## Testing (required, not optional)

- Write tests alongside features. Backend: **pytest**. Flutter: **flutter test**.
- Prefer writing the test first for anything with real logic (nutrition math, score, auth scoping).
- **Run the tests and confirm they pass before claiming a task is done.** Don't assert success without evidence.

---

## Commands

> Valid once the scaffold exists; create the scaffold to match these.

```bash
# Backend
cd backend
uv sync                       # install deps
uv run uvicorn app.main:app --reload
uv run alembic upgrade head   # apply migrations
uv run alembic revision --autogenerate -m "msg"
uv run pytest

# Frontend
cd app
flutter pub get
flutter run
flutter test
```

---

## Working with subagents

- Use the built-in **Explore** agent to navigate the codebase and **a verify agent** to run tests and report only failures — keep that noise out of the main context.
- **Do not parallelize the foundation** (DB schema, auth, core models, shared scaffolding) — build it single-threaded to avoid drift.
- **Parallelize only independent feature modules**, and only after the API contract exists as code. Good candidates: water, weight, water/stats, notifications.
- When delegating an implementation task, hand the subagent the relevant `docs/NN_*.md` and require it to write tests.
- Don't pre-build a rigid pipeline of custom agents. Start with built-ins; add a custom one only when you keep repeating the same specialized task.

## Definition of done (per task)

1. Behavior matches the relevant spec doc.
2. Tests written and passing.
3. Lint clean.
4. Alembic migration included if the schema changed.
5. No AI provider SDK imported outside `app/ai/`.
6. No secrets committed.

## Guardrails

- No secrets in the repo (env / secret manager only).
- No medical claims or diagnoses — this is a guidance app, not a clinical tool.
- We store no passwords; Firebase owns credentials.
- Never silently rewrite historical nutrition values when a `foods` row changes — items store resolved values at log time.
- AI estimates are presented as editable, never as final truth.
