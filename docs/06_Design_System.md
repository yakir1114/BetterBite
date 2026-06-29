# 06 — Design System

> **Document status:** Draft v1
> **Owner:** Design / Frontend
> **Related docs:** `05_UI_Design.md`
> **Target:** Flutter `ThemeData` + a small token layer (`lib/core/theme/`).

---

## 1. Design language

Fresh, clean, trustworthy — a health app, not a clinical one. Lots of whitespace, soft cards, one confident accent color, friendly rounded shapes. The food photo is usually the most colorful thing on screen; the UI stays calm around it.

## 2. Color palette

Defined as tokens; both light and dark themes provided. Hex values are a starting point — tune in implementation.

| Token | Light | Dark | Use |
|---|---|---|---|
| `primary` | `#2E7D5B` (fresh green) | `#4CAF82` | brand, primary buttons, ring |
| `primary_container` | `#D7F0E2` | `#1E4536` | selected chips, highlights |
| `accent` | `#FF8A4C` (warm orange) | `#FF9E66` | CTAs, the 📷 button, energy |
| `background` | `#F7F9F8` | `#101513` | app background |
| `surface` | `#FFFFFF` | `#1A211E` | cards, sheets |
| `on_surface` | `#1B211F` | `#E7EDEA` | primary text |
| `muted` | `#6B7670` | `#9AA8A1` | secondary text |
| `outline` | `#E1E7E4` | `#2C3531` | borders, dividers |
| `success` | `#3BA55C` | `#5BC47C` | goal met, positive |
| `warning` | `#E0A100` | `#F2C14E` | low confidence, over-target soon |
| `danger` | `#D14343` | `#E66A6A` | over target, destructive |

**Macro colors** (consistent everywhere — bars, charts, rings):
`protein #3E7BFA` · `carbs #F2A93B` · `fat #E0607E` · `fiber #4CAF82`.

**Health Score bands:** 0–39 danger · 40–69 warning · 70–100 success.

## 3. Typography

Must render Hebrew and Latin cleanly.

- **Font:** a variable family with strong Hebrew support — e.g. **Heebo** or **Rubik** (both cover Hebrew + Latin). One family across the app.
- **Numbers** (calories, macros) use tabular figures so they don't jump as they change.

| Style | Size / weight | Use |
|---|---|---|
| `display` | 34 / 700 | the big remaining-kcal number |
| `h1` | 24 / 700 | screen titles |
| `h2` | 20 / 600 | section headers |
| `title` | 16 / 600 | card titles, list items |
| `body` | 15 / 400 | body text |
| `caption` | 13 / 400 | secondary, units |
| `button` | 15 / 600 | button labels |

## 4. Spacing & shape

- **Spacing scale (dp):** 4, 8, 12, 16, 24, 32. Default screen padding 16; section gap 24.
- **Radius:** cards 16, buttons 12, chips/pills full (999), bottom sheets 24 (top corners).
- **Elevation:** mostly flat; cards use a soft shadow (y2, blur 8, 8% black) rather than hard Material elevation.

## 5. Core components

| Component | Notes |
|---|---|
| **Primary button** | filled `primary`, radius 12, full-width on forms, 48dp min height. |
| **Accent CTA** | the 📷 "Log a meal" button — `accent`, large, prominent on Home; mirrors as the center nav item. |
| **Card** | `surface`, radius 16, soft shadow, 16 padding. The base container for meals, recipes, stats. |
| **Progress ring** | circular indicator for calories (consumed/target); color shifts toward `warning`/`danger` as the user approaches/exceeds target. |
| **Macro bar** | thin horizontal bar, macro color, with `consumed/target` label. |
| **Meal row** | thumbnail + name + kcal; chevron to details. |
| **Detected item row** | ✓ icon, name, editable quantity stepper, kcal; low-confidence shows a small `warning` dot. |
| **Coach card** | distinct soft `primary_container` background, coach avatar/emoji, short message; the visual "voice" of the app. |
| **Badge / achievement** | circular, earned = full color, locked = greyed `muted`. |
| **Chip** | filters/tags (recipes), tasks; pill shape, selectable. |
| **Bottom nav** | 5 items with the center 📷 raised. |
| **Empty state** | icon + one line + a clear action. |
| **Snackbar / toast** | for confirmations and recoverable errors. |

## 6. Iconography

- A single consistent icon set (e.g. Lucide / Material Symbols, outlined).
- Emoji are used intentionally for warmth in copy and meal types (🌞 morning, 🥗, 🔥 streak) — not as functional icons.

## 7. Dark mode

First-class, driven by the user's `dark_mode` setting (and optionally system). All tokens above have dark values. Test the food-photo contrast and the ring/score colors specifically in dark.

## 8. RTL & localization

- Full **RTL** support for Hebrew. Use Flutter's directionality; never hard-code `EdgeInsets.only(left:)` — use `start`/`end`.
- Icons that imply direction (back/forward, progress) mirror in RTL.
- **Gendered Hebrew strings:** the localization layer resolves masculine/feminine variants from `users.sex`. Keys carry both forms; a fallback (neutral/masculine) is used when sex is `other`/unset. English keys are single-form.
- Numbers/dates/units format per `locale` and the `units_metric` display setting (storage stays metric — see `03`).

## 9. Accessibility

- Tap targets ≥ 48dp. Text scales with system font size.
- Color is never the only signal (pair score color with the number; pair low-confidence color with an icon).
- Contrast meets WCAG AA for text.
- All interactive elements have semantic labels for screen readers.

## 10. Implementation notes

- Centralize tokens in `lib/core/theme/` (`colors.dart`, `typography.dart`, `spacing.dart`, `app_theme.dart`).
- Expose light + dark `ThemeData`; components read from theme, never literal hex.
- Build a tiny widget gallery screen (debug-only) to eyeball every component in both themes and both directions.
