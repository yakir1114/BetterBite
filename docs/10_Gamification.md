# 10 — Gamification

> **Document status:** Draft v1
> **Owner:** Engineering / Product
> **Related docs:** `03_Database_Schema.md` (`achievements`, `user_achievements`, `tasks`, `user_tasks`), `04_API_Spec.md`
> **Code home:** `backend/app/gamification/` (+ Health Score in `app/nutrition/`)

---

## 1. Goal

Make healthy logging feel rewarding and bring the user back to the core loop. Three mechanics: a **Health Score** (quality, not just quantity), **XP + streaks** (momentum), and **tasks + achievements** (goals to chase). None of these should encourage unhealthy behavior — see §7.

## 2. Health Score (0–100)

A per-meal and per-day quality score, so the app rewards *what* you eat, not only the calorie count. Six weighted components (from the brief): **protein, fiber, sugar, processed food, saturated fat, variety.**

Suggested weights (tunable constants in `nutrition/health_score.py`):

| Component | Weight | Scores high when… |
|---|---:|---|
| Protein | 20 | protein meets/approaches target (per meal: a fair share of it) |
| Fiber | 20 | adequate fiber (ref ~14 g / 1000 kcal) |
| Sugar | 15 | added/total sugar is low relative to kcal |
| Processed food | 15 | items are mostly whole foods (`foods.is_processed=false`) |
| Saturated fat | 15 | saturated fat is a small share of fat/kcal |
| Variety | 15 | multiple distinct food groups / items |
| **Total** | **100** | |

Rules:
- Each component returns 0..1 of its weight; sum, round to 0–100.
- **Per-meal** score uses that meal's items. **Per-day** score uses the day's totals + variety across the day (stored on `daily_summaries.health_score`; meal score on `meals.health_score`).
- Bands for display (`06`): 0–39 danger · 40–69 warning · 70–100 success.
- Keep the formula in one place; it's referenced by the coach (`08`) to name weak components.

> The exact sub-formulas (how each component maps to 0..1) are implementation constants — start simple and document them inline so they can be tuned with real data.

## 3. XP & levels

- Users earn **XP** for actions (logging meals, completing tasks, earning achievements). XP accumulates on `users.xp`.
- **Levels** are derived from XP (e.g. simple curve: level n needs `100 * n*(n+1)/2` XP — tune later). `GET /me/xp` returns `xp`, `level`, `next_level_xp`, `streak_days`.
- Suggested awards (tunable): log a meal +10 · complete a daily task +15 · earn an achievement = its `xp_reward` · hit all daily tasks +bonus.

## 4. Streaks

- `users.streak_days` = consecutive days with ≥1 logged meal (the habit we care about, tied to the North Star).
- Computed/updated server-side when a meal is saved and via the daily job: if yesterday had a meal and today does, increment; if a day was missed, reset to today's 1.
- Timezone-aware (use the user's local date / `logged_date`).
- Streaks power achievements (7 / 100 days) and can drive a gentle reminder if a streak is about to break (`11`).

## 5. Tasks (daily challenges)

Defined in the `tasks` catalog with a machine-checkable `criteria` (JSONB). Examples from the brief:

| code | title | criteria | XP |
|---|---|---|---:|
| `water_2l` | Drink 2 L of water | `{"water_ml": 2000}` | 15 |
| `ate_veggies` | Eat vegetables | `{"has_food_group":"vegetable"}` | 10 |
| `hit_protein` | Reach your protein goal | `{"protein_pct_of_target": 1.0}` | 20 |
| `under_kcal` | Stay within calories | `{"kcal_within_target": true}` | 15 |

- `GET /tasks/today` returns today's tasks + completion (joins `user_tasks` for `date=today`).
- **Auto-completion:** where criteria are measurable from logged data (water, protein, calories), the server marks them complete when logging crosses the threshold — no manual tap.
- **Manual completion:** self-reported tasks (e.g. "ate veggies" if not inferable) use `POST /tasks/{code}/complete`, which validates what it can and awards XP. One completion per task per day (`UNIQUE(user_id, task_id, date)`).

## 6. Achievements (badges)

Defined in `achievements` with `criteria` + `xp_reward`. Examples:

| code | title | icon | criteria |
|---|---|---|---|
| `streak_7` | 7 days in a row | 🥇 | `{"streak_days": 7}` |
| `healthy_30` | 30 healthy meals | 🥗 | `{"healthy_meals": 30}` (meal health_score ≥ 70) |
| `streak_100` | 100 days | 🔥 | `{"streak_days": 100}` |
| `protein_week` | Protein goal 7 days | 💪 | `{"protein_goal_days": 7}` |
| `first_meal` | First meal logged | ✨ | `{"meals_logged": 1}` |

- Awarding is **server-side and event-driven:** after a meal/water/weight log and in the daily job, an `achievements.evaluate(user)` step checks unearned achievements against current stats and inserts `user_achievements` (idempotent via the UNIQUE constraint), awarding `xp_reward`.
- `GET /achievements` returns the catalog with each user's `earned_at` (null if locked).
- Newly earned achievements can trigger an `achievement` notification (`11`) and a celebratory UI moment.

## 7. Anti-gaming & wellbeing guardrails

- **Never reward restriction or under-eating.** "Stay within calories" rewards *being within a healthy target band*, not eating as little as possible. Do not award points for very low intake; if intake is implausibly low, suppress the reward.
- No streak pressure that encourages logging fake meals — streak = days with a meal, and quality is separate (Health Score).
- Tasks/achievements focus on **adding good habits** (protein, veggies, water) more than cutting.
- Keep it positive: locked badges are aspirational, not shaming.
- These rules align with the app's no-medical-claims, wellbeing-first stance (`CLAUDE.md`).

## 8. Testing hooks

- Unit-test `health_score` per component with crafted meals (high protein, high sugar, all-processed, high variety).
- Unit-test streak increment/reset across day boundaries and timezones.
- Unit-test task auto-completion thresholds and achievement evaluation idempotency.
- See `12_Testing_Plan.md`.
