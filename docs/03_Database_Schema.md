# 03 — Database Schema

> **Document status:** Draft v1
> **Owner:** Engineering
> **DB:** PostgreSQL 15+ · **ORM:** SQLAlchemy 2.x · **Migrations:** Alembic
> **Related docs:** `02_System_Architecture.md`, `04_API_Spec.md`

---

## 1. Conventions

- Table names: `snake_case`, plural (`meals`, `meal_items`).
- Primary keys: `id UUID` (default `gen_random_uuid()`), unless noted.
- Every table has `created_at` and (where mutable) `updated_at` — `TIMESTAMPTZ`, UTC.
- Foreign keys are indexed. Money-free app, so all nutrition values are numeric grams/kcal.
- Soft references to the user always via `user_id` for row-level scoping.
- Enancurated value sets use Postgres `ENUM` types (listed in §3).
- Units stored in **metric**: grams (g), kilocalories (kcal), millilitres (ml), kilograms (kg), centimetres (cm).

## 2. Entity overview

```
users ──1:1── goals
  │
  ├──1:N── meals ──1:N── meal_items ──N:1── foods
  │                          
  ├──1:N── weight_history
  ├──1:N── water_logs
  ├──1:N── daily_summaries        (one row per user per day; rollups)
  ├──1:N── user_achievements ──N:1── achievements
  ├──1:N── user_tasks ──N:1── tasks
  ├──1:N── coach_insights
  ├──1:N── chat_messages
  ├──1:N── recipes (saved/generated)
  ├──1:N── shopping_list_items
  ├──1:N── notifications
  └──1:N── devices                (FCM tokens)

recipes ──1:N── recipe_ingredients ──N:1── foods (optional link)
```

## 3. Enum types

```sql
CREATE TYPE sex_enum            AS ENUM ('male', 'female', 'other');
CREATE TYPE activity_level_enum AS ENUM ('sedentary','light','moderate','active','very_active');
CREATE TYPE goal_type_enum      AS ENUM ('lose_weight','gain_muscle','maintain');
CREATE TYPE meal_type_enum      AS ENUM ('breakfast','lunch','dinner','snack');
CREATE TYPE meal_source_enum    AS ENUM ('photo','manual','barcode','recipe');
CREATE TYPE item_source_enum    AS ENUM ('ai','catalog','manual');
CREATE TYPE insight_scope_enum  AS ENUM ('meal','daily','weekly');
CREATE TYPE chat_role_enum      AS ENUM ('user','assistant');
CREATE TYPE notif_type_enum     AS ENUM ('meal_reminder','water_reminder','coach','achievement','custom');
CREATE TYPE weight_source_enum  AS ENUM ('manual','google_fit','samsung_health','healthkit');
```

---

## 4. Tables

### 4.1 `users`

The application user. One row per Firebase identity.

| Column | Type | Notes |
|---|---|---|
| `id` | UUID PK | |
| `firebase_uid` | TEXT UNIQUE NOT NULL | from Firebase Auth; the join key for auth |
| `email` | TEXT | nullable (Apple private relay etc.) |
| `display_name` | TEXT | |
| `photo_url` | TEXT | avatar |
| `sex` | `sex_enum` | |
| `birth_date` | DATE | used to derive age (store DOB, not age) |
| `height_cm` | NUMERIC(5,1) | |
| `activity_level` | `activity_level_enum` | |
| `locale` | TEXT | e.g. `he`, `en` (default `he`) |
| `units_metric` | BOOLEAN | display units; storage stays metric (default `true`) |
| `dark_mode` | BOOLEAN | |
| `xp` | INTEGER | total experience points (default 0) |
| `streak_days` | INTEGER | current logging streak (default 0) |
| `onboarded_at` | TIMESTAMPTZ | null until profile setup complete |
| `created_at` / `updated_at` | TIMESTAMPTZ | |

> Age is **derived** from `birth_date`, not stored, so it never goes stale.

### 4.2 `goals`

Current goal + computed energy targets. One active row per user (history optional via `is_active`).

| Column | Type | Notes |
|---|---|---|
| `id` | UUID PK | |
| `user_id` | UUID FK → users | |
| `goal_type` | `goal_type_enum` | lose / gain / maintain |
| `start_weight_kg` | NUMERIC(5,1) | snapshot at goal creation |
| `target_weight_kg` | NUMERIC(5,1) | |
| `bmr_kcal` | NUMERIC(7,1) | computed (Mifflin–St Jeor) |
| `tdee_kcal` | NUMERIC(7,1) | computed (BMR × activity factor) |
| `daily_kcal_target` | NUMERIC(7,1) | TDEE adjusted for goal |
| `protein_g_target` | NUMERIC(6,1) | |
| `carbs_g_target` | NUMERIC(6,1) | |
| `fat_g_target` | NUMERIC(6,1) | |
| `water_ml_target` | INTEGER | default e.g. 2000 |
| `is_active` | BOOLEAN | default `true`; only one active per user |
| `created_at` / `updated_at` | TIMESTAMPTZ | |

> **Computation reference (see `02`/`07` for where it runs):**
> - BMR (Mifflin–St Jeor): male `10·kg + 6.25·cm − 5·age + 5`; female `… − 161`.
> - TDEE = BMR × {sedentary 1.2, light 1.375, moderate 1.55, active 1.725, very_active 1.9}.
> - Daily target = TDEE − 15–20% (lose) / + 10–15% (gain) / TDEE (maintain). Exact % is a tunable constant.

### 4.3 `foods`

Reusable nutrition catalog. Values are **per 100 g** (or per 100 ml for liquids) so any portion scales.

| Column | Type | Notes |
|---|---|---|
| `id` | UUID PK | |
| `name` | TEXT NOT NULL | canonical English/Hebrew name |
| `name_he` | TEXT | localized name |
| `aliases` | TEXT[] | alternate names for matching |
| `barcode` | TEXT | nullable; indexed for scans |
| `is_liquid` | BOOLEAN | per-100-ml vs per-100-g |
| `kcal_per_100` | NUMERIC(7,2) | |
| `protein_per_100` | NUMERIC(6,2) | |
| `carbs_per_100` | NUMERIC(6,2) | |
| `fat_per_100` | NUMERIC(6,2) | |
| `fiber_per_100` | NUMERIC(6,2) | |
| `sugar_per_100` | NUMERIC(6,2) | |
| `sodium_mg_per_100` | NUMERIC(7,2) | |
| `is_processed` | BOOLEAN | feeds Health Score |
| `saturated_fat_per_100` | NUMERIC(6,2) | feeds Health Score |
| `source` | TEXT | e.g. `seed`, `usda`, `ai_generated` |
| `created_at` | TIMESTAMPTZ | |

> **Hybrid nutrition source:** when the AI detects an item we try to match it to a `foods` row (by name/alias/barcode). On a match we use catalog values × grams. On no match we store the AI's per-item values directly on the `meal_item` and may create a new `foods` row (`source='ai_generated'`). See `07`.

### 4.4 `meals`

A logged eating event.

| Column | Type | Notes |
|---|---|---|
| `id` | UUID PK | |
| `user_id` | UUID FK → users | |
| `meal_type` | `meal_type_enum` | breakfast/lunch/dinner/snack |
| `eaten_at` | TIMESTAMPTZ | when eaten (user-editable) |
| `logged_date` | DATE | denormalized local date for daily rollups & queries |
| `source` | `meal_source_enum` | photo/manual/barcode/recipe |
| `image_url` | TEXT | Firebase Storage path (nullable) |
| `note` | TEXT | optional user note |
| `total_kcal` | NUMERIC(8,2) | denormalized sum of items |
| `total_protein_g` | NUMERIC(7,2) | denormalized |
| `total_carbs_g` | NUMERIC(7,2) | denormalized |
| `total_fat_g` | NUMERIC(7,2) | denormalized |
| `total_fiber_g` | NUMERIC(7,2) | denormalized |
| `total_sugar_g` | NUMERIC(7,2) | denormalized |
| `total_sodium_mg` | NUMERIC(8,2) | denormalized |
| `health_score` | SMALLINT | 0–100 for this meal (nullable) |
| `created_at` / `updated_at` | TIMESTAMPTZ | |

> Totals are **denormalized** for fast Home/History rendering and recomputed whenever items change. `logged_date` is the user's local calendar date (important for "today" across timezones).

### 4.5 `meal_items`

One detected/confirmed food within a meal.

| Column | Type | Notes |
|---|---|---|
| `id` | UUID PK | |
| `meal_id` | UUID FK → meals (ON DELETE CASCADE) | |
| `food_id` | UUID FK → foods | nullable (AI-only items) |
| `name` | TEXT NOT NULL | snapshot name shown to user |
| `quantity_g` | NUMERIC(7,2) | portion in grams (or ml if liquid) |
| `source` | `item_source_enum` | ai / catalog / manual |
| `confidence` | NUMERIC(4,3) | AI confidence 0–1 (nullable) |
| `kcal` | NUMERIC(7,2) | resolved value for this portion |
| `protein_g` | NUMERIC(6,2) | |
| `carbs_g` | NUMERIC(6,2) | |
| `fat_g` | NUMERIC(6,2) | |
| `fiber_g` | NUMERIC(6,2) | |
| `sugar_g` | NUMERIC(6,2) | |
| `sodium_mg` | NUMERIC(7,2) | |
| `edited_by_user` | BOOLEAN | true if user changed AI output (accuracy metric) |
| `created_at` | TIMESTAMPTZ | |

> Per-item nutrition is stored resolved (already scaled to the portion) so a later change to a `foods` row doesn't silently rewrite history.

### 4.6 `daily_summaries`

One row per user per local date. Rollup for Home, stats, streaks, and the coach.

| Column | Type | Notes |
|---|---|---|
| `id` | UUID PK | |
| `user_id` | UUID FK → users | |
| `date` | DATE NOT NULL | |
| `kcal_total` / `kcal_target` | NUMERIC | |
| `protein_g` / `carbs_g` / `fat_g` | NUMERIC | sums |
| `fiber_g` / `sugar_g` / `sodium_mg` | NUMERIC | sums |
| `water_ml` | INTEGER | |
| `meals_count` | SMALLINT | |
| `health_score` | SMALLINT | day score 0–100 |
| `goal_met` | BOOLEAN | within calorie target |
| `created_at` / `updated_at` | TIMESTAMPTZ | |
| | | **UNIQUE(user_id, date)** |

### 4.7 `weight_history`

| Column | Type | Notes |
|---|---|---|
| `id` | UUID PK | |
| `user_id` | UUID FK → users | |
| `weight_kg` | NUMERIC(5,1) NOT NULL | |
| `bmi` | NUMERIC(4,1) | computed from current height |
| `measured_at` | TIMESTAMPTZ | |
| `source` | `weight_source_enum` | manual / fit / samsung / healthkit |
| `created_at` | TIMESTAMPTZ | |

### 4.8 `water_logs`

| Column | Type | Notes |
|---|---|---|
| `id` | UUID PK | |
| `user_id` | UUID FK → users | |
| `amount_ml` | INTEGER NOT NULL | |
| `logged_date` | DATE | |
| `logged_at` | TIMESTAMPTZ | |

### 4.9 `achievements` (catalog) & `user_achievements` (earned)

`achievements` — the defined badges:

| Column | Type | Notes |
|---|---|---|
| `id` | UUID PK | |
| `code` | TEXT UNIQUE | e.g. `streak_7`, `healthy_30`, `streak_100` |
| `title` | TEXT | "7 days in a row" |
| `title_he` | TEXT | |
| `description` | TEXT | |
| `icon` | TEXT | emoji/asset id (🥇, 🥗, 🔥) |
| `xp_reward` | INTEGER | |
| `criteria` | JSONB | machine-checkable rule, e.g. `{"streak_days":7}` |

`user_achievements` — which user earned what:

| Column | Type | Notes |
|---|---|---|
| `id` | UUID PK | |
| `user_id` | UUID FK → users | |
| `achievement_id` | UUID FK → achievements | |
| `earned_at` | TIMESTAMPTZ | |
| | | **UNIQUE(user_id, achievement_id)** |

### 4.10 `tasks` (catalog) & `user_tasks` (progress)

`tasks` — repeatable daily/period challenges:

| Column | Type | Notes |
|---|---|---|
| `id` | UUID PK | |
| `code` | TEXT UNIQUE | e.g. `water_2l`, `ate_veggies`, `hit_protein`, `under_kcal` |
| `title` / `title_he` | TEXT | |
| `xp_reward` | INTEGER | |
| `criteria` | JSONB | e.g. `{"water_ml":2000}` |
| `cadence` | TEXT | `daily` (default) / `weekly` |

`user_tasks` — per-user per-day completion:

| Column | Type | Notes |
|---|---|---|
| `id` | UUID PK | |
| `user_id` | UUID FK → users | |
| `task_id` | UUID FK → tasks | |
| `date` | DATE | |
| `completed` | BOOLEAN | |
| `completed_at` | TIMESTAMPTZ | |
| | | **UNIQUE(user_id, task_id, date)** |

### 4.11 `coach_insights`

Messages produced by the AI Nutrition Coach (`08`).

| Column | Type | Notes |
|---|---|---|
| `id` | UUID PK | |
| `user_id` | UUID FK → users | |
| `scope` | `insight_scope_enum` | meal / daily / weekly |
| `meal_id` | UUID FK → meals | nullable (set for meal-scope) |
| `message` | TEXT NOT NULL | the coach text shown to the user |
| `tags` | TEXT[] | e.g. `{low_fiber, high_protein}` for analytics |
| `context` | JSONB | inputs used to generate (for debugging/audit) |
| `read_at` | TIMESTAMPTZ | nullable |
| `created_at` | TIMESTAMPTZ | |

### 4.12 `chat_messages`

AI dietitian chat history (`module 17`).

| Column | Type | Notes |
|---|---|---|
| `id` | UUID PK | |
| `user_id` | UUID FK → users | |
| `role` | `chat_role_enum` | user / assistant |
| `content` | TEXT NOT NULL | |
| `created_at` | TIMESTAMPTZ | |

### 4.13 `recipes` & `recipe_ingredients`

`recipes` — saved or AI-generated:

| Column | Type | Notes |
|---|---|---|
| `id` | UUID PK | |
| `user_id` | UUID FK → users | nullable (null = global/seed recipe) |
| `title` / `title_he` | TEXT | |
| `instructions` | TEXT | steps (markdown allowed) |
| `prep_minutes` | SMALLINT | |
| `servings` | SMALLINT | |
| `kcal_per_serving` | NUMERIC(7,2) | |
| `protein_g_per_serving` | NUMERIC(6,2) | |
| `carbs_g_per_serving` | NUMERIC(6,2) | |
| `fat_g_per_serving` | NUMERIC(6,2) | |
| `is_ai_generated` | BOOLEAN | |
| `tags` | TEXT[] | e.g. `{keto, high_protein, quick}` |
| `created_at` | TIMESTAMPTZ | |

`recipe_ingredients`:

| Column | Type | Notes |
|---|---|---|
| `id` | UUID PK | |
| `recipe_id` | UUID FK → recipes (CASCADE) | |
| `food_id` | UUID FK → foods | nullable |
| `name` | TEXT NOT NULL | free-text ingredient |
| `quantity_g` | NUMERIC(7,2) | nullable |
| `display_amount` | TEXT | e.g. "2 tbsp", "1 cup" |

### 4.14 `shopping_list_items`

Derived from recipes (`module 16`).

| Column | Type | Notes |
|---|---|---|
| `id` | UUID PK | |
| `user_id` | UUID FK → users | |
| `name` | TEXT NOT NULL | |
| `quantity` | TEXT | e.g. "500 g", "2 units" |
| `recipe_id` | UUID FK → recipes | nullable (origin) |
| `checked` | BOOLEAN | default false |
| `created_at` | TIMESTAMPTZ | |

### 4.15 `notifications`

Scheduled / sent notifications (`module 14`).

| Column | Type | Notes |
|---|---|---|
| `id` | UUID PK | |
| `user_id` | UUID FK → users | |
| `type` | `notif_type_enum` | meal/water/coach/achievement/custom |
| `title` / `body` | TEXT | |
| `scheduled_for` | TIMESTAMPTZ | nullable (immediate if null) |
| `sent_at` | TIMESTAMPTZ | nullable |
| `read_at` | TIMESTAMPTZ | nullable |
| `data` | JSONB | deep-link payload |
| `created_at` | TIMESTAMPTZ | |

### 4.16 `devices`

FCM tokens per user device (push targeting).

| Column | Type | Notes |
|---|---|---|
| `id` | UUID PK | |
| `user_id` | UUID FK → users | |
| `fcm_token` | TEXT UNIQUE NOT NULL | |
| `platform` | TEXT | `android` / `ios` |
| `last_seen_at` | TIMESTAMPTZ | |
| `created_at` | TIMESTAMPTZ | |

---

## 5. Indexes (beyond PK/FK)

```sql
CREATE INDEX idx_meals_user_date      ON meals (user_id, logged_date DESC);
CREATE INDEX idx_meal_items_meal      ON meal_items (meal_id);
CREATE INDEX idx_daily_user_date      ON daily_summaries (user_id, date DESC);
CREATE INDEX idx_weight_user_time     ON weight_history (user_id, measured_at DESC);
CREATE INDEX idx_water_user_date      ON water_logs (user_id, logged_date);
CREATE INDEX idx_foods_barcode        ON foods (barcode);
CREATE INDEX idx_foods_name_trgm      ON foods USING gin (name gin_trgm_ops);  -- fuzzy name match
CREATE INDEX idx_insights_user_time   ON coach_insights (user_id, created_at DESC);
CREATE INDEX idx_chat_user_time       ON chat_messages (user_id, created_at);
CREATE INDEX idx_notif_user_sched     ON notifications (user_id, scheduled_for);
```

> Requires the `pg_trgm` extension for fuzzy food-name matching: `CREATE EXTENSION IF NOT EXISTS pg_trgm;`
> Requires `pgcrypto` for `gen_random_uuid()`: `CREATE EXTENSION IF NOT EXISTS pgcrypto;`

## 6. Integrity & lifecycle rules

- Deleting a `meal` cascades to its `meal_items`; deleting a `recipe` cascades to `recipe_ingredients`.
- Deleting a `user` should cascade or soft-delete all owned rows (decide per privacy policy — default: hard cascade on account deletion request).
- `meals` denormalized totals and `daily_summaries` are recomputed by the nutrition service whenever items change — they are caches, not the source of truth (which is `meal_items`).
- Only one `goals` row per user has `is_active = true`.
- `daily_summaries`, `user_tasks`, `user_achievements` enforce one-row-per-period via UNIQUE constraints.

## 7. Mapping to the brief's table list

| Brief table | This schema |
|---|---|
| Users | `users` (+ `devices`) |
| Meals | `meals` |
| MealItems | `meal_items` |
| Foods | `foods` |
| Recipes | `recipes` (+ `recipe_ingredients`) |
| Achievements | `achievements` (+ `user_achievements`) |
| WeightHistory | `weight_history` |
| Water | `water_logs` |
| Goals | `goals` |
| Notifications | `notifications` |
| *(added)* | `daily_summaries`, `tasks`/`user_tasks`, `coach_insights`, `chat_messages`, `shopping_list_items` |

Added tables support features in the brief that have no obvious home in the original list (gamification tasks, the coach, AI chat, shopping list, daily rollups).
