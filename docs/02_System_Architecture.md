# 02 — System Architecture

> **Document status:** Draft v1
> **Owner:** Engineering
> **Related docs:** `03_Database_Schema.md`, `04_API_Spec.md`, `07_AI_Food_Recognition.md`

---

## 1. Overview

BetterBite is a **client–server** application:

- A **Flutter** mobile client (Android first, iOS to follow with minimal changes).
- A **FastAPI** backend exposing a REST API.
- A **PostgreSQL** database.
- **Firebase** for authentication, image storage, and push notifications.
- External **AI model providers** for food-image recognition and for coaching / recipe text generation.

The backend is the single source of truth for nutrition data and business logic. The client never talks to AI providers directly — all AI calls are proxied through the backend so we control prompts, cost, keys, and data handling.

## 2. High-level diagram

```
┌──────────────────────────────────────────────────────────────┐
│                       Flutter App (mobile)                     │
│   UI · local cache · camera/gallery · Firebase Auth SDK · FCM  │
└───────────────┬───────────────────────────────┬───────────────┘
                │ HTTPS (REST + Firebase ID JWT) │ direct upload
                ▼                                 ▼
┌───────────────────────────────┐      ┌────────────────────────┐
│        FastAPI Backend        │      │   Firebase Storage      │
│  · Auth verify (JWT)          │◄─────│   (meal images)         │
│  · Profile / goals / meals    │ URL  └────────────────────────┘
│  · Nutrition engine           │
│  · AI orchestration layer ────┼───────────┐
│  · Coach engine               │           ▼
│  · Recipes / chat             │   ┌────────────────────────┐
└───────┬───────────────┬───────┘   │   AI Providers          │
        │               │           │   · Vision (food)       │
        ▼               ▼           │   · LLM (coach/recipes) │
┌──────────────┐ ┌──────────────┐   └────────────────────────┘
│ PostgreSQL   │ │ Firebase     │
│ (app data)   │ │ Cloud Msg.   │──► Push notifications to device
└──────────────┘ └──────────────┘
```

## 3. Technology stack & rationale

| Layer | Choice | Why |
|---|---|---|
| Mobile client | **Flutter (Dart)** | One codebase for Android + iOS; fast iteration; strong with Claude Code. |
| Backend | **Python + FastAPI** | Async, typed (Pydantic), auto OpenAPI docs, ideal glue for AI providers. |
| Database | **PostgreSQL** | Relational integrity for meals/items/foods; JSONB where flexibility helps. |
| ORM / migrations | **SQLAlchemy 2.x + Alembic** | Mature, typed models, versioned schema changes. |
| Auth | **Firebase Authentication** | Google/Apple/Email out of the box; backend verifies ID tokens. |
| Image storage | **Firebase Storage / GCS** | Cheap, scalable blob storage; signed URLs. |
| Push | **Firebase Cloud Messaging** | Cross-platform push. |
| Vision AI | **Vision LLM** (e.g. GPT-4.x Vision / Gemini Vision) behind an adapter | Recognizes thousands of foods without us training a model. Swappable. |
| Text AI | **LLM** (coach, recipes, chat) behind an adapter | Generates explanations, tips, recipes. Swappable. |
| Cache / jobs (later) | **Redis + a task queue** | Background coach summaries, async recognition, rate limiting. |

> **Provider independence:** Vision and text AI both sit behind an internal **adapter interface** (`AIVisionProvider`, `AITextProvider`). The rest of the system never imports a provider SDK directly. Swapping or A/B-testing models is a config change. See `07_AI_Food_Recognition.md`.

## 4. Backend module layout

A modular monolith — one deployable, clear internal boundaries. Split into services later only if needed.

```
backend/
  app/
    main.py                 # FastAPI app, router registration
    config.py               # settings (env vars)
    deps.py                 # shared dependencies (db session, current user)
    auth/                   # Firebase token verification, current-user dependency
    users/                  # profile, goals, BMR/TDEE
    meals/                  # meals, meal items, photo→log flow
    foods/                  # food catalog / lookup
    nutrition/              # nutrition engine (totals, macros, health score)
    ai/
      vision/               # AIVisionProvider adapter + impls
      text/                 # AITextProvider adapter + impls
      coach/                # coach engine (per-meal + longitudinal)
      recipes/              # recipe generation
      chat/                 # dietitian chat
    gamification/           # tasks, XP, achievements
    stats/                  # statistics aggregation
    weight/ water/          # weigh-ins, hydration
    notifications/          # scheduling + FCM dispatch
    db/                     # SQLAlchemy models, session, Alembic
  tests/
```

Each module exposes a `router.py` (HTTP), `service.py` (logic), `schemas.py` (Pydantic), and uses shared `db/models.py`.

## 5. Key data flows

### 5.1 Photo → logged meal (the core flow)

```
1. App captures/picks an image.
2. App uploads the image to Firebase Storage → gets a storage path/URL.
   (Alternatively, App POSTs the image to the backend, which stores it. Pick ONE —
    default below is client-direct upload to keep the backend light.)
3. App POSTs { image_url } to  POST /meals/analyze.
4. Backend:
     a. Verifies the user (JWT).
     b. Calls AIVisionProvider.recognize(image_url) → list of detected items
        (name, estimated grams, confidence).
     c. Maps each detected item to nutrition (Foods catalog or AI-provided values).
     d. Returns a DRAFT meal: items + per-item + totals (NOT yet saved).
5. User confirms/edits (add, remove, change quantities).
6. App POSTs the confirmed meal to  POST /meals  → persisted as Meal + MealItems.
7. Backend recomputes daily totals; Coach engine produces a per-meal insight.
8. App refreshes Home (remaining kcal, ring) and shows the coach message.
```

**Why a draft step:** the AI is not always right (`06_User_Confirmation` in the brief). Nothing is saved until the user confirms, which keeps the data clean and the user in control.

### 5.2 Authentication

```
1. User signs in via Firebase (Google / Apple / Email) in the app.
2. Firebase returns an ID token (JWT).
3. App sends every API request with  Authorization: Bearer <ID token>.
4. Backend verifies the token against Firebase public keys, extracts the uid,
   and resolves (or lazily creates) the matching Users row.
```

The backend stores no passwords — credentials are Firebase's responsibility.

### 5.3 Coaching (longitudinal)

```
Per-meal:   on each saved meal, generate a short insight from the meal + day context.
Daily:      a scheduled job summarizes the day and updates habit signals.
Periodic:   a job scans recent days for trends (e.g. "low fiber 3 days running")
            and queues a coach message / notification.
```

Detail in `08_AI_Nutrition_Coach.md`.

## 6. API conventions

- **Base path:** `/api/v1`
- **Format:** JSON request/response, `snake_case` fields.
- **Auth:** `Authorization: Bearer <firebase_id_token>` on all endpoints except health checks.
- **Errors:** consistent envelope (see `04_API_Spec.md`):
  ```json
  { "error": { "code": "VALIDATION_ERROR", "message": "…", "details": {…} } }
  ```
- **Timestamps:** ISO-8601 UTC.
- **Units:** stored in metric (grams, kcal, ml, kg, cm); the client converts for display per user settings.
- **Pagination:** cursor or `limit`/`offset` for list endpoints.

## 7. Security

- All traffic over **HTTPS/TLS**.
- **Firebase ID-token verification** on every protected route; reject expired/invalid tokens.
- **Authorization:** users may only read/write their own rows; enforced in the service layer (every query is scoped by `user_id`).
- **AI keys** live only on the backend (env/secret manager), never in the app.
- **Image access** via short-lived signed URLs; images are private by default.
- **PII minimization:** store only what's needed (age, sex, height, weight, goals). No medical diagnoses.
- **Input validation** via Pydantic on every endpoint.
- **Rate limiting** on AI-backed endpoints (recognition, chat, recipes) to control cost and abuse.

## 8. Environments & deployment

| Env | Purpose |
|---|---|
| **local** | Docker Compose: FastAPI + PostgreSQL + Firebase emulator. |
| **staging** | Pre-prod with test data; uses cheaper AI model tier. |
| **production** | Live. |

- Backend containerized (Docker) and deployed to a managed container host (Cloud Run / similar).
- DB managed PostgreSQL with automated backups.
- Config via environment variables only (12-factor). No secrets in the repo.
- CI runs lint + tests on every PR (see `12_Testing_Plan.md`).

## 9. Scalability & cost notes

- **AI cost is the main variable cost.** Mitigations: cache recognition results per image hash; batch/queue non-urgent coach work; cap free-tier AI calls; use a cheaper model tier where quality allows.
- **Stateless backend** → scale horizontally behind a load balancer.
- **Heavy reads** (stats) → add read replicas / caching later if needed.
- **Async recognition (P1):** if vision latency is high, return a job id and push the result, instead of blocking the request.

## 10. Open decisions

| Decision | Options | Default for now |
|---|---|---|
| Image upload path | Client→Storage direct vs Client→Backend→Storage | **Client→Storage direct** (lighter backend); revisit if we need server-side preprocessing. |
| Nutrition source of truth | Own `Foods` catalog vs trust AI per-item values vs hybrid | **Hybrid**: prefer catalog match, fall back to AI values. See `03` & `07`. |
| Recognition latency | Sync request vs async job+push | **Sync** for MVP; async as P1. |
| Steps/activity source | Google Fit / Samsung Health / HealthKit | Integrate in P1 (`13` module). |
