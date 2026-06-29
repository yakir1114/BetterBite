# 05 — UI Design (Screens)

> **Document status:** Draft v1
> **Owner:** Product / Design
> **Related docs:** `04_API_Spec.md`, `06_Design_System.md`

---

## 1. Principles

- **Speed over completeness.** The logging loop must feel instant. Every screen on that path is optimized for the fewest taps.
- **One primary action per screen.** Each screen makes the obvious next step obvious.
- **Honest AI.** Anything the AI produced is visibly editable and never presented as final truth.
- **RTL + LTR.** The app ships Hebrew (RTL) and English (LTR). Layouts mirror correctly; never hard-code left/right — use start/end.
- **Gendered Hebrew copy.** Hebrew is grammatically gendered. UI strings have masculine/feminine variants selected from the user's `sex` setting (e.g. *"צלמי"* vs *"צלם"*, *"נשארו לך"* identical, *"תקטיני"* vs *"תקטין"*). English is gender-neutral. See `06` §localization.

## 2. Navigation map

```
Splash
 ├─(not authed)→ Login ⇄ Register ⇄ Forgot Password
 └─(authed)→
      ├─(no profile)→ Onboarding (multi-step) → Home
      └─(profile)→ Home

Bottom navigation (authed):
 [ Home ] [ History ] [ 📷 Log ] [ Stats ] [ More ]

Home ──────────► Camera ► Image Review ► Meal Result ► Home
History ───────► Meal Details (edit/delete)
Stats ─────────► Weight · Achievements
More (menu) ───► Recipes ► Recipe Details ► Shopping List
              ├► AI Chat
              ├► Profile
              └► Settings
```

The center **📷 Log** button is the app's hero action and is always one tap from Home.

## 3. Screens

Each screen lists: **purpose · key elements · data (API) · primary action**.

### 3.1 Splash
- **Purpose:** brand moment + decide route (authed? onboarded?).
- **Elements:** logo, subtle loader.
- **Data:** `POST /auth/session` (if a Firebase session exists) → `needs_onboarding`.
- **Action:** auto-route to Login / Onboarding / Home.

### 3.2 Login
- **Purpose:** sign in.
- **Elements:** Google button, Apple button, email + password, "Forgot password?", link to Register.
- **Data:** Firebase Auth SDK (client). On success → `POST /auth/session`.
- **Action:** authenticate → route.

### 3.3 Register
- **Purpose:** create an account.
- **Elements:** Google / Apple / email+password, link to Login.
- **Data:** Firebase Auth (client) → `POST /auth/session` (creates `users` row).
- **Action:** create account → Onboarding.

### 3.4 Forgot Password
- **Purpose:** reset email-based password.
- **Elements:** email field, send button, confirmation state.
- **Data:** Firebase Auth password reset (client).

### 3.5 Onboarding (multi-step)
The profile + goal wizard. One question per step keeps it light. Steps:
1. Sex
2. Birth date (→ age)
3. Height (cm; display per units)
4. Current weight (kg)
5. Target weight
6. Activity level (sedentary → very active)
7. Goal (lose / gain / maintain)
8. **Result screen:** computed BMR, TDEE, **daily calorie target** + macro targets.

- **Data:** `POST /onboarding` (sends all answers, returns computed targets).
- **Action:** "Start" → Home.
- **Notes:** progress indicator across steps; back navigation allowed; values validated client-side, recomputed server-side.

### 3.6 Home  ⭐ core surface
- **Purpose:** today at a glance + entry to logging.
- **Elements (top→bottom):**
  - Greeting: *"Good morning, Michal 🌞"* (time-of-day + name; gendered copy).
  - **Remaining calories**: large number — *"1,320 kcal left"*.
  - **Progress ring** + bar: `680 / 2000`.
  - Macro mini-bars: protein / carbs / fat vs target.
  - Big **📷 "Log a meal"** button.
  - **Today's meals** grouped: Breakfast · Lunch · Dinner · Snacks (each row: thumbnail, name, kcal).
  - Today's tasks chip row (optional).
- **Data:** `GET /home?date=today`.
- **Action:** tap 📷 → Camera.

### 3.7 Camera
- **Purpose:** capture or pick a meal photo.
- **Elements:** live camera, shutter, gallery 🖼 toggle, meal-type selector (auto-guessed by time, editable).
- **Data:** uploads image to Firebase Storage → gets `image_url`.
- **Action:** capture → Image Review (calls `POST /meals/analyze`).

### 3.8 Image Review  ⭐ accuracy guardrail
- **Purpose:** confirm/edit what the AI detected before saving.
- **Elements:**
  - The photo.
  - Detected items list — *"I found:"* with ✓ rows (name, quantity, kcal). Low-confidence items flagged subtly.
  - Per item: edit quantity, delete, change food.
  - **+ Add item** (search `foods` or manual).
  - Running totals update live.
- **Data:** draft from `POST /meals/analyze`; food search `GET /foods/search`.
- **Action:** **Save meal** → `POST /meals` → Meal Result.

### 3.9 Meal Result
- **Purpose:** confirmation + the coach moment.
- **Elements:**
  - Nutrition summary: kcal, protein, carbs, fat, fiber, sugar, sodium.
  - Meal **Health Score**.
  - **AI Coach card** — the short insight (e.g. *"Great — lots of protein. I'd add veggies for more fiber."*).
  - Updated "remaining today".
- **Data:** response of `POST /meals` (includes `coach_insight` + `day`).
- **Action:** Done → Home (refreshed).

### 3.10 History
- **Purpose:** browse past days/meals.
- **Elements:** date selector / scrollable day list; per day: total kcal, goal met badge, meals.
- **Data:** `GET /meals?date=…` (paged by day).
- **Action:** tap a meal → Meal Details.

### 3.11 Meal Details
- **Purpose:** view/edit a logged meal.
- **Elements:** photo, items + per-item nutrition, totals, score, note. Edit meal type/time, edit items, delete meal.
- **Data:** `GET /meals/{id}`; `PATCH /meals/{id}`; `DELETE /meals/{id}`.

### 3.12 Weight
- **Purpose:** log and view weight.
- **Elements:** current weight, target, trend sparkline; **+ add weigh-in**; "connect Google Fit / Samsung Health".
- **Data:** `GET /weight`, `POST /weight`, `POST /integrations/health-sync`.

### 3.13 Statistics
- **Purpose:** trends over time.
- **Elements:** metric switcher — Weight · BMI · Calories · Protein · Steps · Water; line/bar charts; range (week/month); average vs target.
- **Data:** `GET /stats?metric=…&from=&to=&granularity=`.

### 3.14 Achievements
- **Purpose:** badges + XP.
- **Elements:** XP/level header + streak; earned vs locked badges grid (🥇 7-day, 🥗 30 healthy meals, 🔥 100 days…).
- **Data:** `GET /achievements`, `GET /me/xp`.

### 3.15 Recipes
- **Purpose:** discover / generate recipes.
- **Elements:** generate form (max kcal, min protein, time, ingredients on hand, tags: keto/paleo/vegan/high-protein); result cards (title, kcal/serving, protein, time).
- **Data:** `POST /recipes/generate`, `GET /recipes`.
- **Action:** tap → Recipe Details.

### 3.16 Recipe Details
- **Purpose:** full recipe.
- **Elements:** title, per-serving macros, ingredients, steps, prep time, servings; **Save**, **Add ingredients to shopping list**.
- **Data:** `GET /recipes/{id}`, `POST /recipes/{id}/save`, `POST /shopping-list/from-recipe/{id}`.

### 3.17 Shopping List
- **Purpose:** consolidated ingredients to buy.
- **Elements:** checkable items (name, quantity), source recipe, clear-checked.
- **Data:** `GET /shopping-list`, `PATCH /shopping-list/{id}`, `DELETE /shopping-list/{id}`.

### 3.18 AI Chat
- **Purpose:** ask the AI dietitian.
- **Elements:** chat thread; suggested prompts (*"Is shawarma good for a diet?"*, *"What should I eat after a workout?"*, *"Am I getting enough protein?"*); input box.
- **Data:** `GET /chat/messages`, `POST /chat/messages`.
- **Note:** show a typing indicator while awaiting the assistant; rate-limited.

### 3.19 Settings
- **Purpose:** preferences.
- **Elements:** Language (he/en), Dark mode, Units (metric/imperial display), Notifications (meal/water/coach toggles + quiet hours), Account (sign out, delete account).
- **Data:** `PATCH /me`, `PUT /me/notification-settings`, `DELETE /me`.

### 3.20 Profile
- **Purpose:** view/edit personal data + goal.
- **Elements:** avatar, name, sex, age, height; current goal + targets; "recalculate".
- **Data:** `GET /me`, `PATCH /me`, `PUT /goals/active`, `POST /goals/recalculate`.

## 4. Cross-cutting UI rules

- **Loading:** the analyze step may take a few seconds — show an engaging "analyzing your meal…" state, never a frozen screen.
- **Empty states:** Home with no meals invites the first photo; History/Stats with no data explain what will appear.
- **Errors:** AI/network failures show a friendly retry; the error envelope `code` maps to a localized message.
- **Offline:** queued weigh-ins / water logs sync when back online (P1).
- **Accessibility:** min tap target 48dp, sufficient contrast, dynamic type, screen-reader labels. See `06`.
