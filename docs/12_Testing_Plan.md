# 12 — Testing Plan

> **Document status:** Draft v1
> **Owner:** Engineering
> **Related docs:** all module docs · `CLAUDE.md` (testing is required, not optional)

---

## 1. Principles

- **Tests ship with features.** A module isn't done until its tests are written and **passing with evidence** (`CLAUDE.md` Definition of Done).
- **Test-first for real logic.** Nutrition math, BMR/TDEE, Health Score, streaks, auth scoping — write the test before the code.
- **Mock the outside world.** AI providers, Firebase, and FCM are mocked in tests; we never hit a paid API or external service in CI.
- **The core loop is sacred.** The photo→analyze→confirm→save→coach→home path has the highest coverage bar.

## 2. Backend — pytest

### 2.1 Layers

| Layer | What | Notes |
|---|---|---|
| **Unit** | Pure logic, no DB/network | nutrition engine, BMR/TDEE, Health Score components, streak math, coach `signals.py`, recipe nutrition recompute. |
| **Integration** | API endpoints against a test DB | real FastAPI app, real Postgres (test schema), mocked AI/Firebase. |
| **Contract** | Request/response shapes match `04` | validate Pydantic schemas + error envelope. |

### 2.2 Setup

- **Test DB:** spin up Postgres (Docker / a disposable schema); run Alembic migrations at session start; truncate between tests or use transactional rollback per test.
- **Async:** `pytest-asyncio`; use FastAPI's `httpx.AsyncClient` against the app.
- **Auth:** a fixture that injects a fake authenticated user (override the `current_user` dependency) so tests don't need real Firebase tokens. A separate test verifies the real verifier rejects bad/expired tokens (with Firebase mocked).
- **Fakes:** `FakeVisionProvider`, `FakeTextProvider` (fixtures for recognition/coach/recipes); a fake FCM client; a fake Storage that returns predictable URLs.

### 2.3 Must-have test cases

**Auth & scoping (critical):**
- Every protected route rejects requests with no/invalid token (401).
- A user **cannot** read or write another user's rows — meals, weight, water, chat, etc. all scoped by `user_id` (403/404). Add a test per resource.

**Nutrition & goals:**
- BMR/TDEE for known inputs (male/female, each activity level) → expected values.
- Daily target adjustment for lose/gain/maintain.
- `resolve_items` for the three paths (catalog hit / AI fallback / unknown) — `07`.
- Meal totals = sum of items; daily totals recompute correctly when items change/are deleted (denormalized caches stay consistent with `meal_items`).

**Health Score & gamification — `10`:**
- Each score component on crafted meals (high protein, high sugar, all-processed, high variety).
- Streak increment/reset across day boundaries and timezones.
- Task auto-completion thresholds; achievement evaluation is idempotent (no double award).
- Wellbeing guardrail: implausibly low intake does **not** earn the "within calories" reward.

**Core meal flow — `07`:**
- `POST /meals/analyze` returns a draft (nothing persisted) using `FakeVisionProvider`; covers single/multi-item, liquid, low-confidence, empty/non-food, invalid-JSON-then-repair.
- `POST /meals` persists meal + items, recomputes the day, returns a coach insight; `eaten_at`/`logged_date` handled correctly.
- `DELETE /meals/{id}` recomputes the day.

**Coach — `08`:**
- `signals.py` on crafted histories: low-fiber streak, protein improvement, calorie streak, cold start (no false trends).
- Full pipeline with `FakeTextProvider` attaches correct `scope`/`tags`.
- Fail-soft: text-provider error still saves the meal.
- Guardrail: medical-type input yields only a safe redirect, no advice.

**Recipes — `09`:** parsing valid/invalid JSON, nutrition recompute from catalog, constraint filtering, shopping-list merge.

**Notifications — `11`:** quiet-hours suppression, per-type toggles, frequency caps, timezone correctness, "meal already logged → no reminder", invalid-token pruning, fan-out to multiple devices.

**Error envelope:** representative failures return `{ "error": { code, message, details } }` with the right code (`04`).

## 3. Frontend — flutter test

| Layer | What |
|---|---|
| **Unit** | converters (metric↔display units), formatters, view-model/Riverpod providers, gendered-string resolution. |
| **Widget** | key screens render and react: Home (ring/remaining from a fake response), Image Review (edit/add/remove items updates totals), Meal Result (coach card), Onboarding steps. |
| **Integration (golden path)** | the logging loop with a mocked API client: Home → Camera → Image Review → Save → Home updates. |

- **Mock the API client** (the app talks only to our backend — `CLAUDE.md`); no real network in tests.
- Test **RTL + LTR** rendering and dark/light for a couple of representative screens.
- Golden tests (optional) for the design-system components.

## 4. Coverage targets

- **Critical paths** (auth scoping, nutrition math, score, meal save/analyze): aim high (~90%+).
- Overall backend: a reasonable floor (e.g. 80%) — don't chase 100% on glue code.
- Coverage is a guide, not the goal; a passing meaningful test beats a covered trivial line.

## 5. CI

- On every PR: install deps, run lint (`ruff` backend / `flutter analyze`), run `pytest` and `flutter test`. Red = not mergeable.
- Backend integration tests get a Postgres service container in CI.
- No external AI/Firebase calls in CI (fakes only) → fast, deterministic, free.
- (Later) report coverage on the PR.

## 6. Definition of done (testing slice)

A task is done only when:
1. Tests exist for the new logic (and were written first where it's real logic).
2. `pytest` / `flutter test` were **run** and pass — paste the evidence.
3. Lint is clean.

No "should pass" — show the green run.
