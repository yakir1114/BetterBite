# 11 — Notifications

> **Document status:** Draft v1
> **Owner:** Engineering
> **Related docs:** `03_Database_Schema.md` (`notifications`, `devices`), `04_API_Spec.md`
> **Code home:** `backend/app/notifications/`

---

## 1. Goal

Bring users back to the loop at the right moments — without being annoying. Notifications are reminders and encouragement, delivered via **Firebase Cloud Messaging (FCM)**, scheduled server-side, respectful of quiet hours and frequency caps.

## 2. Types

| `type` | Trigger | Example |
|---|---|---|
| `meal_reminder` | No meal logged by a usual mealtime | "Time to log lunch? 🍽" |
| `water_reminder` | Behind on water target during the day | "You're a bit behind on water today." |
| `coach` | Weekly coach insight / notable trend (`08`) | "Nice — protein up 20% this week!" |
| `achievement` | A badge was earned (`10`) | "🔥 100-day streak unlocked!" |
| `custom` | Ops / announcements | — |

All map to `notif_type_enum` in `03`.

## 3. Architecture

```
Scheduler (per-minute/per-hour job)         Event-driven
  → finds due reminders per user      vs.     → on achievement earned / coach weekly
  → respects settings + quiet hours          → enqueue notification row
  → writes notifications row (scheduled_for)
            │
            ▼
   dispatcher → FCM send to user's devices (fan-out over devices.fcm_token)
            → set notifications.sent_at
```

- **Device registry:** the app registers its FCM token via `POST /devices` on login and removes it via `DELETE /devices/{token}` on logout. A user may have several devices; dispatch fans out to all and prunes tokens FCM reports as invalid.
- **In-app inbox:** `GET /notifications` lists recent notifications (read/unread); `POST /notifications/{id}/read` marks read. Tapping deep-links via the `data` payload.

## 4. Scheduling logic

- **Meal reminders:** based on the user's typical meal times (start with sensible defaults — e.g. breakfast 08:00, lunch 13:00, dinner 19:00 local — refine from their logging history). Fire only if that meal type isn't logged yet today and the time has passed by a grace window.
- **Water reminders:** if, partway through the day, `water_ml` is well below the pro-rated `water_ml_target`, send at most one nudge in the afternoon.
- **Coach (weekly):** fired by the weekly coach job (`08`) when there's a worthwhile insight.
- **Achievement:** immediately on unlock (event-driven), bypassing the schedule but still respecting quiet hours (defer if within quiet hours).
- All times computed in the **user's timezone** using their local date.

## 5. User settings & frequency caps

- Settings via `PUT /me/notification-settings`: per-type toggles (`meal`, `water`, `coach`) + **quiet hours** (e.g. 22:00–07:00).
- **Caps:** at most ~3 notifications/day total per user; **one `coach` notification/day** max; never two of the same type within a few hours; suppress a type the user disabled.
- Quiet hours: nothing is delivered during the window; time-sensitive ones are dropped, not stacked up to fire at 07:00.
- Respect OS-level permission: if the user denied push, fall back to in-app inbox only.

## 6. Payload & deep links

FCM message carries a `data` payload so taps land on the right screen:

```json
{ "type": "coach", "insight_id": "…", "route": "/coach" }
{ "type": "achievement", "achievement_code": "streak_100", "route": "/achievements" }
{ "type": "meal_reminder", "meal_type": "lunch", "route": "/camera" }
```

The client routes from `route`/ids; unknown types open the inbox.

## 7. Content & tone

- Short, warm, specific (same voice as the coach, `08`). No guilt ("you failed"), no medical claims.
- Localized (he/en) and gendered for Hebrew.
- A reminder is a gentle invitation, never a scold.

## 8. Reliability

- Dispatch is idempotent (a notification row is sent once; `sent_at` guards re-sends).
- FCM failures: retry transient errors; on `UNREGISTERED`/invalid token, delete that `devices` row.
- The whole system fails soft — a missed reminder never blocks app usage.

## 9. Testing hooks

- Mock the FCM client; assert the dispatcher fans out to all of a user's devices and sets `sent_at`.
- Unit-test scheduling decisions: quiet-hours suppression, per-type toggles, frequency caps, timezone correctness, "meal already logged → no reminder."
- Test invalid-token pruning.
- See `12_Testing_Plan.md`.
