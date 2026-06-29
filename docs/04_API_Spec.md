# 04 — API Specification

> **Document status:** Draft v1
> **Owner:** Engineering
> **Base URL:** `https://api.betterbite.app/api/v1`
> **Related docs:** `02_System_Architecture.md`, `03_Database_Schema.md`

---

## 1. Conventions

- **Auth:** all endpoints (except `/health`) require `Authorization: Bearer <firebase_id_token>`. The backend verifies the token, resolves the `users` row by `firebase_uid`, and scopes every query to that user.
- **Content type:** `application/json`; fields are `snake_case`.
- **Units:** request/response bodies are **metric** (g, kcal, ml, kg, cm). Client converts for display.
- **Timestamps:** ISO-8601 UTC (e.g. `2026-06-29T08:15:00Z`).
- **IDs:** UUID strings.
- **Pagination:** list endpoints accept `?limit=` (default 20, max 100) and `?cursor=` (opaque) or `?offset=`.

### Standard error envelope

```json
{
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "quantity_g must be positive",
    "details": { "field": "quantity_g" }
  }
}
```

| HTTP | `code` examples |
|---|---|
| 400 | `VALIDATION_ERROR`, `BAD_REQUEST` |
| 401 | `UNAUTHENTICATED`, `TOKEN_EXPIRED` |
| 403 | `FORBIDDEN` |
| 404 | `NOT_FOUND` |
| 409 | `CONFLICT` |
| 429 | `RATE_LIMITED` (AI endpoints) |
| 500 | `INTERNAL_ERROR` |
| 502 | `AI_PROVIDER_ERROR` |

---

## 2. Auth & user

### `POST /auth/session`
Called after Firebase sign-in. Verifies the token and lazily creates the `users` row on first call. Returns the user profile and whether onboarding is needed.

**Response 200**
```json
{
  "user": { "id": "…", "email": "michal@example.com", "display_name": "Michal", "onboarded": false },
  "needs_onboarding": true
}
```

### `GET /me`
Current user profile (joins active goal).

**Response 200**
```json
{
  "id": "…",
  "email": "michal@example.com",
  "display_name": "Michal",
  "sex": "female",
  "birth_date": "1994-03-02",
  "height_cm": 168,
  "activity_level": "moderate",
  "locale": "he",
  "units_metric": true,
  "dark_mode": false,
  "xp": 340,
  "streak_days": 5,
  "goal": {
    "goal_type": "lose_weight",
    "target_weight_kg": 62,
    "daily_kcal_target": 1800,
    "protein_g_target": 120,
    "carbs_g_target": 180,
    "fat_g_target": 60,
    "water_ml_target": 2000
  }
}
```

### `PATCH /me`
Update profile fields (name, sex, birth_date, height, activity_level, locale, units, dark_mode). Returns the updated user. If fields affecting BMR/TDEE change, targets are recomputed if a goal is active.

### `DELETE /me`
Delete the account and all owned data (per privacy policy).

---

## 3. Onboarding, goals & targets

### `POST /onboarding`
Completes profile creation in one call: demographics + initial weight + goal. Computes BMR/TDEE/targets and creates the active `goals` row.

**Request**
```json
{
  "sex": "female",
  "birth_date": "1994-03-02",
  "height_cm": 168,
  "current_weight_kg": 70,
  "target_weight_kg": 62,
  "activity_level": "moderate",
  "goal_type": "lose_weight"
}
```

**Response 201**
```json
{
  "goal": {
    "id": "…",
    "bmr_kcal": 1452,
    "tdee_kcal": 2251,
    "daily_kcal_target": 1800,
    "protein_g_target": 120,
    "carbs_g_target": 180,
    "fat_g_target": 60,
    "water_ml_target": 2000
  }
}
```

### `GET /goals/active` — current active goal.
### `PUT /goals/active` — update goal (type, target weight, activity); recomputes targets.
### `POST /goals/recalculate` — force recompute of BMR/TDEE/targets from latest profile + weight.

> Computation formulas (Mifflin–St Jeor + activity factors + goal adjustment) are defined in `03_Database_Schema.md §4.2`.

---

## 4. Meals — the core flow

### `POST /meals/analyze`  🔒 rate-limited
Send a meal image; get a **draft** (unsaved) analysis from the vision AI. Nothing is persisted except optional caching.

**Request**
```json
{ "image_url": "gs://betterbite/meals/uid/abc.jpg", "meal_type": "lunch" }
```

**Response 200**
```json
{
  "draft_id": "…",
  "items": [
    {
      "temp_id": "1",
      "name": "Chicken breast",
      "name_he": "חזה עוף",
      "quantity_g": 180,
      "source": "ai",
      "confidence": 0.91,
      "food_id": "…",
      "kcal": 298, "protein_g": 54, "carbs_g": 0, "fat_g": 7,
      "fiber_g": 0, "sugar_g": 0, "sodium_mg": 130
    },
    { "temp_id": "2", "name": "Rice", "name_he": "אורז", "quantity_g": 150, "confidence": 0.84, "kcal": 195, "protein_g": 4, "carbs_g": 42, "fat_g": 0.5 }
  ],
  "totals": { "kcal": 690, "protein_g": 60, "carbs_g": 47, "fat_g": 12 }
}
```

The client renders this as the **Image Review** screen (`module 6`), letting the user edit/add/remove before saving.

### `POST /meals`
Persist a confirmed meal (after user edits). Creates `meals` + `meal_items`, recomputes daily totals, and triggers a per-meal coach insight.

**Request**
```json
{
  "meal_type": "lunch",
  "eaten_at": "2026-06-29T12:30:00Z",
  "source": "photo",
  "image_url": "gs://betterbite/meals/uid/abc.jpg",
  "items": [
    { "name": "Chicken breast", "food_id": "…", "quantity_g": 180, "source": "ai", "confidence": 0.91, "edited_by_user": false,
      "kcal": 298, "protein_g": 54, "carbs_g": 0, "fat_g": 7, "fiber_g": 0, "sugar_g": 0, "sodium_mg": 130 },
    { "name": "Salad", "quantity_g": 120, "source": "manual", "edited_by_user": true, "kcal": 60, "protein_g": 2, "carbs_g": 6, "fat_g": 3, "fiber_g": 3 }
  ]
}
```

**Response 201**
```json
{
  "meal": {
    "id": "…", "meal_type": "lunch", "eaten_at": "2026-06-29T12:30:00Z",
    "total_kcal": 358, "total_protein_g": 56, "total_carbs_g": 6, "total_fat_g": 10,
    "health_score": 82, "image_url": "…",
    "items": [ … ]
  },
  "coach_insight": {
    "id": "…",
    "message": "Great — lots of protein here. I'd add more veggies for extra fiber.",
    "tags": ["high_protein", "low_fiber"]
  },
  "day": { "date": "2026-06-29", "kcal_total": 1180, "kcal_target": 1800, "remaining_kcal": 620 }
}
```

### `GET /meals?date=YYYY-MM-DD`
Meals for a day (defaults to today). Powers Home's "today's meals" and History.

### `GET /meals/{id}` — full meal with items (Meal Details screen).
### `PATCH /meals/{id}` — edit meal type / time / note; recomputes totals.
### `DELETE /meals/{id}` — remove a meal; recomputes daily totals.
### `POST /meals/manual` — create a meal without a photo (manual entry / `module` fallback).
### `POST /meals/barcode` — `{ "barcode": "729000…", "meal_type":"snack", "quantity_g":40 }` → looks up `foods`, returns a draft item.

---

## 5. Home / dashboard

### `GET /home?date=YYYY-MM-DD`
Single call that powers the Home screen: greeting data, remaining calories, ring progress, macro progress, today's meals grouped by type, today's tasks.

**Response 200**
```json
{
  "date": "2026-06-29",
  "kcal_target": 2000,
  "kcal_consumed": 680,
  "kcal_remaining": 1320,
  "macros": {
    "protein": { "consumed": 45, "target": 120 },
    "carbs":   { "consumed": 70, "target": 180 },
    "fat":     { "consumed": 22, "target": 60 }
  },
  "water_ml": 750,
  "water_target_ml": 2000,
  "health_score": 78,
  "meals": {
    "breakfast": [ … ], "lunch": [ … ], "dinner": [], "snack": [ … ]
  },
  "tasks": [ { "code": "water_2l", "title": "Drink 2 L water", "completed": false } ]
}
```

---

## 6. Foods catalog

### `GET /foods/search?q=chicken&limit=10` — fuzzy search (trigram + alias match).
### `GET /foods/{id}` — single food (per-100 values).
### `POST /foods` — create a custom food (advanced/manual). Used when AI returns an unknown item the user wants to save.

---

## 7. Nutrition & Health Score

### `GET /nutrition/day?date=YYYY-MM-DD`
Computed totals + macros + Health Score breakdown for a day (`module 7`, `module 9`).

**Response 200**
```json
{
  "date": "2026-06-29",
  "totals": { "kcal": 1180, "protein_g": 78, "carbs_g": 110, "fat_g": 40, "fiber_g": 22, "sugar_g": 35, "sodium_mg": 1900 },
  "health_score": 81,
  "score_breakdown": {
    "protein": 18, "fiber": 16, "sugar": 12, "processed": 14, "saturated_fat": 11, "variety": 10
  }
}
```

> Health Score components (protein, fiber, sugar, processed food, saturated fat, variety) and weights are defined in `09_Gamification.md` / `08_AI_Nutrition_Coach.md`.

---

## 8. AI Coach

### `GET /coach/insights?scope=meal|daily|weekly&limit=20`
List coach insights (history). `module 8`.

### `GET /coach/feed`
The "what should I notice today" feed: most recent unread daily/weekly insights for the home/coach surface.

### `POST /coach/insights/{id}/read` — mark an insight read.

> Insights are generated server-side (on meal save, and by scheduled daily/weekly jobs) — there is no client endpoint to *trigger* generation directly in MVP.

---

## 9. AI dietitian chat (`module 17`)

### `GET /chat/messages?limit=50` — conversation history.

### `POST /chat/messages`  🔒 rate-limited
Send a question; the backend builds context (recent nutrition + goals) and returns the assistant reply. Persists both messages.

**Request** `{ "content": "Is shawarma good for a diet?" }`

**Response 201**
```json
{
  "user_message": { "id": "…", "role": "user", "content": "Is shawarma good for a diet?" },
  "assistant_message": {
    "id": "…", "role": "assistant",
    "content": "Shawarma can fit a diet in moderation. Chicken over lamb and skipping the extra tahini/oil keeps it leaner — want a lighter version?"
  }
}
```

---

## 10. Recipes (`module 15`) & shopping list (`module 16`)

### `POST /recipes/generate`  🔒 rate-limited
AI generates recipes from constraints.

**Request**
```json
{ "max_kcal": 600, "min_protein_g": 35, "max_minutes": 20, "ingredients_on_hand": ["chicken","rice","tomato"], "tags": ["high_protein"] }
```

**Response 201** — list of generated `recipes` (saved with `is_ai_generated=true`).

### `GET /recipes?tag=&limit=` — list saved/seed recipes.
### `GET /recipes/{id}` — recipe + ingredients (Recipe Details screen).
### `POST /recipes/{id}/save` — save a generated recipe to the user's collection.

### `GET /shopping-list` — current items.
### `POST /shopping-list/from-recipe/{recipe_id}` — append a recipe's ingredients.
### `PATCH /shopping-list/{id}` — `{ "checked": true }`.
### `DELETE /shopping-list/{id}` — remove an item.

---

## 11. Weight, BMI & water

### `GET /weight?from=&to=` — weight history (for charts).
### `POST /weight` — `{ "weight_kg": 69.4, "measured_at":"…", "source":"manual" }` → stores + computes BMI; may update goal progress.
### `DELETE /weight/{id}`.

### `GET /water?date=YYYY-MM-DD` — today's water total + entries.
### `POST /water` — `{ "amount_ml": 250 }`.

### `POST /integrations/health-sync`
Push a batch from Google Fit / Samsung Health / HealthKit (weight, steps, water).
```json
{ "source": "google_fit", "weights": [ { "weight_kg": 69.2, "measured_at": "…" } ], "steps": [ { "date":"2026-06-28", "count": 8400 } ] }
```

---

## 12. Statistics (`module 12`)

### `GET /stats?metric=weight|bmi|kcal|protein|steps|water&from=&to=&granularity=day|week`
Time-series for charts.

**Response 200**
```json
{
  "metric": "protein",
  "granularity": "day",
  "points": [ { "date": "2026-06-23", "value": 95 }, { "date": "2026-06-24", "value": 110 } ],
  "average": 102,
  "target": 120
}
```

---

## 13. Gamification (`module 10`) & achievements (`module 11`)

### `GET /tasks/today` — today's tasks with completion state.
### `POST /tasks/{code}/complete` — mark a task done (server validates criteria where possible); awards XP.
### `GET /achievements` — catalog + which the user has earned (with `earned_at`).
### `GET /me/xp` — `{ "xp": 340, "level": 4, "streak_days": 5, "next_level_xp": 500 }`.

> Most achievements/tasks are awarded **server-side** when meals/weights/water are logged (e.g. streaks, protein goal). The `complete` endpoint covers manual/self-reported tasks (e.g. "ate veggies").

---

## 14. Notifications (`module 14`)

### `POST /devices` — register an FCM token `{ "fcm_token":"…", "platform":"android" }`.
### `DELETE /devices/{token}` — unregister (logout).
### `GET /notifications?limit=` — in-app notification list.
### `POST /notifications/{id}/read` — mark read.
### `PUT /me/notification-settings` — toggle meal/water/coach reminders + quiet hours.

---

## 15. Settings (`module 18`)

Covered by `PATCH /me` (locale, units_metric, dark_mode) and `PUT /me/notification-settings`. No separate settings resource needed.

---

## 16. System

### `GET /health` — liveness (no auth). `{ "status": "ok" }`.

---

## 17. Endpoint summary

| Group | Endpoints |
|---|---|
| Auth/User | `POST /auth/session`, `GET/PATCH/DELETE /me` |
| Onboarding/Goals | `POST /onboarding`, `GET/PUT /goals/active`, `POST /goals/recalculate` |
| Meals | `POST /meals/analyze`, `POST /meals`, `GET /meals`, `GET/PATCH/DELETE /meals/{id}`, `POST /meals/manual`, `POST /meals/barcode` |
| Home | `GET /home` |
| Foods | `GET /foods/search`, `GET /foods/{id}`, `POST /foods` |
| Nutrition | `GET /nutrition/day` |
| Coach | `GET /coach/insights`, `GET /coach/feed`, `POST /coach/insights/{id}/read` |
| Chat | `GET /chat/messages`, `POST /chat/messages` |
| Recipes | `POST /recipes/generate`, `GET /recipes`, `GET /recipes/{id}`, `POST /recipes/{id}/save` |
| Shopping | `GET /shopping-list`, `POST /shopping-list/from-recipe/{id}`, `PATCH/DELETE /shopping-list/{id}` |
| Weight/Water | `GET/POST/DELETE /weight`, `GET/POST /water`, `POST /integrations/health-sync` |
| Stats | `GET /stats` |
| Gamification | `GET /tasks/today`, `POST /tasks/{code}/complete`, `GET /achievements`, `GET /me/xp` |
| Notifications | `POST/DELETE /devices`, `GET /notifications`, `POST /notifications/{id}/read`, `PUT /me/notification-settings` |
| System | `GET /health` |

🔒 = rate-limited (AI-backed): `/meals/analyze`, `/chat/messages`, `/recipes/generate`.
