# 01 — Product Vision

> **Document status:** Draft v1
> **Owner:** Product
> **Related docs:** `02_System_Architecture.md`, `07_AI_Food_Recognition.md`, `08_AI_Nutrition_Coach.md`

---

## 1. One-liner

**BetterBite** is a mobile nutrition app that turns a single photo of a meal into a complete, editable nutritional log — and then acts as a personal AI nutrition coach that learns the user's habits over time instead of just counting calories.

## 2. The problem

Manual calorie logging is the single biggest reason people abandon nutrition apps. Searching a database, picking the right entry, and guessing portions for every item of every meal is slow and tedious. Most apps that solve the *speed* problem stop at a number on a screen ("You ate 650 calories") and give the user no guidance about whether that was good, why, or what to do next.

Two unmet needs:

1. **Logging is too much work.** Users want to record a meal in seconds, not minutes.
2. **Numbers without coaching are not behavior change.** A calorie count is data, not advice. Users want to know *what to do differently*.

## 3. Our solution

BetterBite attacks both:

- **Photo-first logging.** The user photographs a meal; an AI vision model detects the food items, estimates portions, and produces per-item nutrition. The user confirms or edits, then logs. Target: **a logged meal in under 15 seconds.**
- **An AI coach, not a calculator.** After each meal — and across days and weeks — an AI coach gives short, specific, encouraging guidance grounded in the user's actual eating patterns and goals.

## 4. Target audience

Primary: health-conscious adults (≈ 22–45) who want to eat better or hit a body-composition goal but find traditional trackers too tedious to sustain.

Secondary: people advised by a professional (trainer, dietitian, doctor) to track intake, who need an effortless way to do so.

### Personas

**Michal — "I keep quitting trackers"**
32, works full-time, wants to lose ~6 kg. Has tried two calorie apps and quit both within a week because logging took too long. Will stick with an app only if logging feels effortless and the feedback feels human.

**Daniel — "I'm trying to build muscle"**
27, trains 4×/week, wants to hit a protein target and a slight surplus. Cares about macros (especially protein), not just total calories. Wants to know if a meal helped or hurt the goal.

**Noa — "My dietitian told me to track"**
41, managing blood sugar. Needs accurate-enough logging without friction and values trustworthy, non-judgmental guidance.

## 5. Core value proposition

| For users who… | BetterBite gives them… | Unlike… |
|---|---|---|
| Find logging too slow | One-photo meal logging in seconds | Manual-search trackers |
| Want guidance, not data | A coach that explains and recommends | Apps that only show calorie counts |
| Lose motivation | Streaks, scores, and habit-based encouragement | Static dashboards |

## 6. The differentiator — AI Nutrition Coach

This is the feature that sets BetterBite apart and the one to protect.

Most apps say: *"You ate 650 calories."* BetterBite coaches across time:

- **Sunday:** "I noticed your breakfasts are usually low in protein."
- **Tuesday:** "Your fiber has been low for three days — try adding a fruit or salad at lunch."
- **A week later:** "Nice work — you raised your protein by 20% and stayed on your calorie goal five days running."

The system does not just analyze a single photo. It **learns the user's habits over time and delivers personalized recommendations**, creating the feeling of a personal coach rather than a calorie calculator. Detailed behavior lives in `08_AI_Nutrition_Coach.md`.

## 7. Feature map

Grouped by the modules in the original brief. Priority: **P0** = MVP, **P1** = fast-follow, **P2** = later.

| # | Module | Priority | Notes |
|---|---|---|---|
| 1 | Authentication (Google / Apple / Email) | P0 | Firebase Auth |
| 2 | Profile + goal setup (BMR / TDEE / daily kcal) | P0 | Onboarding |
| 3 | Home screen (remaining kcal, progress ring, today's meals) | P0 | Core daily surface |
| 4 | Photo upload (camera / gallery) | P0 | |
| 5 | AI Vision food recognition | P0 | Heart of the app |
| 6 | User confirmation / edit of detected items | P0 | Accuracy guardrail |
| 7 | Nutrition calculation (totals & macros) | P0 | |
| 8 | AI Nutrition Coach | P0 | Differentiator — ship a basic version in MVP |
| 9 | Health Score (0–100) | P1 | |
| 10 | Gamification (tasks, XP) | P1 | |
| 11 | Achievements / badges | P1 | |
| 12 | Statistics (weight, BMI, kcal, protein, steps, water) | P1 | |
| 13 | Weigh-in + Google Fit / Samsung Health sync | P1 | |
| 14 | Notifications | P1 | |
| 15 | AI recipe generation | P2 | |
| 16 | Shopping list (from recipes) | P2 | |
| 17 | AI dietitian chat | P2 | |
| 18 | Settings (language, dark mode, units, notifications) | P0 | Lightweight |

> **MVP definition:** Modules 1–8 + 18. A user can sign up, set a goal, photograph a meal, confirm it, see their day, and get coached. Everything else builds on that loop.

## 8. The core loop

The product succeeds or fails on one loop being fast and rewarding:

```
Open app  →  Tap 📷  →  Photograph meal  →  AI detects items
        →  Confirm / edit  →  Meal logged  →  Coach responds
        →  Home updates (remaining kcal, ring)
```

Everything else (scores, badges, stats, recipes, chat) exists to bring the user back to this loop and keep them in it.

## 9. Success metrics

**North Star:** number of meals logged per active user per week (proxy for the habit forming).

Supporting metrics:

- **Activation:** % of new users who log ≥ 3 meals in their first 3 days.
- **Time-to-log:** median seconds from opening the camera to a confirmed meal (target < 15s).
- **Recognition acceptance:** % of detected items the user keeps without editing (proxy for AI accuracy).
- **Retention:** D1 / D7 / D30 retention.
- **Coach engagement:** % of users who read/act on coach messages.

## 10. Scope & non-goals

**In scope:** nutrition tracking via photo, coaching, goals, gamification, basic stats, recipes, AI chat.

**Non-goals (for now):**

- Not a medical/clinical product; no diagnosis or medical claims.
- Not a social network (no feeds/following in v1).
- Not a workout-programming app (we read steps/activity, we don't prescribe training).
- Lab-grade nutritional precision is not promised — estimates are "good enough to guide behavior," and the UI is honest about that.

## 11. Guiding principles

1. **Effort is the enemy.** Every tap removed from logging is a feature.
2. **Coach, don't scold.** Guidance is specific, kind, and actionable.
3. **Honest about uncertainty.** AI estimates are presented as editable, not as gospel.
4. **Fast first, complete second.** A quick approximate log beats an abandoned perfect one.
