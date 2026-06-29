# 08 — AI Nutrition Coach

> **Document status:** Draft v1
> **Owner:** Engineering / AI / Product
> **Related docs:** `03_Database_Schema.md` (`coach_insights`), `04_API_Spec.md` (`/coach/*`)
> **Code home:** `backend/app/ai/coach/`

---

## 1. Why this exists

This is the differentiator (`01`). Most apps say *"You ate 650 calories."* BetterBite **coaches over time** — it learns the user's habits and nudges them, like a personal coach rather than a calculator. Protect this feature; it's the reason to come back.

Three time horizons:

- **Per-meal** — an immediate, specific reaction right after logging.
- **Daily** — a wrap-up of the day vs goals.
- **Weekly** — trends and wins across days.

Example arc from the brief:
- *Sunday:* "I noticed your breakfasts are usually low in protein."
- *Tuesday:* "Your fiber's been low for three days — try a fruit or salad at lunch."
- *A week later:* "Nice — you raised protein by 20% and stayed on your calorie goal five days running."

## 2. Pipeline

```
Per-meal:   on POST /meals (after save) → coach.on_meal(meal, day_context) → insight(scope='meal', meal_id)
Daily:      scheduled job (evening, per user TZ) → coach.daily(user, summary) → insight(scope='daily')
Weekly:     scheduled job (weekly) → coach.weekly(user, trends) → insight(scope='weekly') + maybe a notification
```

All insights persist to `coach_insights` and surface via `GET /coach/insights` / `GET /coach/feed`. Provider SDK lives only in `app/ai/text/`; the coach calls the `AITextProvider` adapter.

## 3. Adapter interface

```python
# app/ai/text/base.py
class AITextProvider(Protocol):
    async def generate(self, *, system: str, prompt: str, max_tokens: int = 220) -> str: ...
```

`FakeTextProvider` returns canned text for tests. Provider chosen by `AI_TEXT_PROVIDER`.

## 4. Context building (the real work)

The model is only as good as the context. The coach service assembles a compact, structured context — **we compute the signals, the model phrases them.** Never dump raw rows; summarize first.

**Per-meal context:**
- This meal's totals + macros + Health Score and its weak/strong components.
- The user's goal + daily targets and **remaining** for today.
- A one-line habit hint if relevant (e.g. "breakfast protein typically low").

**Daily context:**
- `daily_summaries` for today: kcal vs target, macros vs targets, fiber/sugar/sodium, water, meals_count, health_score, goal_met.

**Weekly context (habit signals):**
Derived from the last 7–14 days of `daily_summaries` / `meal_items`:
- protein adherence (avg vs target, trend ↑/↓)
- fiber level (avg vs a reference, # low days in a row)
- sugar / sodium flags
- calorie-goal streak (days within target)
- meal-timing patterns (e.g. breakfasts skipped / low-protein)
- variety (distinct foods)

These signals are computed deterministically in `app/ai/coach/signals.py` and also stored as `coach_insights.tags` for analytics. The LLM turns chosen signals into one friendly message — it does not do the analysis itself.

## 5. Prompt & output

**System prompt (spirit):**
> You are BetterBite's nutrition coach. Be warm, specific, and brief (1–3 sentences). Encourage first, then give **one** concrete, actionable suggestion tied to the data provided. Use the user's language (he/en) and gender-appropriate phrasing for Hebrew. Never diagnose, never make medical claims, never shame. Don't restate raw numbers the user can already see — add insight or a next step.

**Input:** the structured context (JSON-ish) + chosen signals.
**Output:** plain text (the message). The service attaches `scope`, `meal_id?`, `tags`, and stores `context` for audit/debugging.

Guidelines enforced in code/prompt:
- **One suggestion, not five.** Pick the highest-value signal.
- **Specific beats generic.** "Add a fruit at lunch" > "eat healthier."
- **Praise real wins** (streaks, improvements) — not empty flattery.
- **Length cap** (~220 tokens) keeps it glanceable.

## 6. Tone rules (hard)

- Encouraging, never judgmental. No "bad" foods framing; no guilt.
- No medical claims, diagnoses, or treatment advice (`CLAUDE.md` guardrail). For medical-sounding questions, gently suggest a professional.
- Respect eating-sensitivity: avoid fixating on restriction; frame around adding good things more than removing.
- Honest: coaching is guidance, the user decides.

## 7. Triggering & frequency

- **Per-meal:** always generated on save, but kept short; shown on the Meal Result screen.
- **Daily:** once per day, evening, in the user's timezone; only if they logged ≥1 meal.
- **Weekly:** once per week; the weekly insight may also fire a `coach` notification (`11`).
- **Frequency cap:** never more than one coach *notification* per day; in-app insights can be more frequent but the feed de-dupes similar tags within a short window.

## 8. Cold start

New users have no history. Rules:
- First few meals: per-meal insights only, based on the meal + goal (no fake "trends").
- Daily/weekly trend messages unlock once there's enough data (e.g. ≥3 logged days).
- Avoid claiming patterns we can't yet see.

## 9. Endpoints (recap from `04`)

- `GET /coach/insights?scope=&limit=` — history.
- `GET /coach/feed` — recent unread daily/weekly insights for the home/coach surface.
- `POST /coach/insights/{id}/read` — mark read.
- No client endpoint *triggers* generation in MVP (server-driven).

## 10. Cost & reliability

- Per-meal calls are frequent → keep prompts tight; consider a cheaper model tier for per-meal and a stronger one for weekly.
- If the text provider fails, **fail soft**: save the meal anyway and either skip the insight or fall back to a templated, signal-based message (no blocking the core loop).
- Cache/skip if context is unchanged (e.g. duplicate triggers).

## 11. Testing hooks

- Deterministic `signals.py` is unit-tested with crafted day histories (low-fiber streak, protein improvement, calorie streak, cold start).
- `FakeTextProvider` lets us test the full pipeline without a network and assert that the right `tags`/`scope` are attached.
- Tone/guardrail checks: assert no insight is produced for medical questions beyond a safe redirect template.
- See `12_Testing_Plan.md`.
