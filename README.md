# BetterBite 🍽️

AI nutrition tracking. Photograph a meal → an AI vision model detects the foods and portions → you confirm or edit → it's logged → an AI coach gives short, specific guidance that learns your habits over time.

Not just a calorie calculator: the differentiator is a longitudinal **AI Nutrition Coach** that actually coaches you across days and weeks.

## Status

🚧 Early development — specification phase. Foundation specs are in `docs/`; code scaffold is next.

## Stack

| Layer | Choice |
|---|---|
| Mobile | Flutter (Dart) — Android first, iOS to follow |
| Backend | Python 3.12 + FastAPI |
| Database | PostgreSQL 15+ (SQLAlchemy 2.x + Alembic) |
| Auth | Firebase Authentication |
| Storage / Push | Firebase Storage · Firebase Cloud Messaging |
| AI | Vision + text LLMs behind internal adapters |

## Repository layout

```
BetterBite/
  CLAUDE.md        # how this repo works — read first (constitution for Claude Code)
  docs/            # the spec documents — the real source of truth
  backend/         # FastAPI service          (coming next)
  app/             # Flutter app              (coming next)
```

## Specs

| # | Doc | Status |
|---|---|---|
| 01 | [Product Vision](docs/01_Product_Vision.md) | ✅ |
| 02 | [System Architecture](docs/02_System_Architecture.md) | ✅ |
| 03 | [Database Schema](docs/03_Database_Schema.md) | ✅ |
| 04 | [API Spec](docs/04_API_Spec.md) | ✅ |
| 05–12 | UI, Design System, AI modules, Recipes, Gamification, Notifications, Testing | ⏳ |

## Working in this repo

Open it with Claude Code from the repo root. `CLAUDE.md` defines the stack, conventions, layout, and how to use subagents. Before implementing any module, read its spec in `docs/`.
