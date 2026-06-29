# 09 — Recipes Module

> **Document status:** Draft v1
> **Owner:** Engineering / AI
> **Related docs:** `03_Database_Schema.md` (`recipes`, `recipe_ingredients`, `shopping_list_items`), `04_API_Spec.md`
> **Code home:** `backend/app/ai/recipes/`

---

## 1. Goal

Generate recipes tailored to the user's constraints — calories, protein, time, ingredients on hand, and diet tags (keto / paleo / vegan / high-protein) — and let them save recipes and turn ingredients into a shopping list. This is a **P2** feature; it builds on the same `AITextProvider` adapter as the coach.

## 2. Flow

```
Recipes screen → user sets constraints → POST /recipes/generate
   → recipes.service.generate()
       → AITextProvider.generate(system, prompt)   # returns structured recipes
       → parse + validate + compute per-serving nutrition
       → persist recipes (is_ai_generated=true) + recipe_ingredients
   → return recipe list
User opens one → GET /recipes/{id}
   → Save: POST /recipes/{id}/save
   → Add to shopping list: POST /shopping-list/from-recipe/{id}
```

## 3. Generate request (recap from `04`)

```json
POST /recipes/generate
{
  "max_kcal": 600,
  "min_protein_g": 35,
  "max_minutes": 20,
  "ingredients_on_hand": ["chicken", "rice", "tomato"],
  "tags": ["high_protein"],
  "servings": 2,
  "count": 3
}
```

All constraints optional; sensible defaults applied. Rate-limited (AI endpoint).

## 4. Prompt & structured output

**System prompt (spirit):**
> You are a practical recipe generator for a nutrition app. Produce recipes that meet the given constraints (calorie ceiling, protein floor, time limit, diet tags) and prefer the listed on-hand ingredients. Keep steps short and realistic. For each recipe return: title (+ Hebrew if locale=he), servings, prep_minutes, ingredients (name, quantity_g or display amount), and per-serving macros (kcal, protein, carbs, fat). Return **only** JSON matching the schema.

**Output schema (per recipe):**
```json
{
  "title": "...", "title_he": "...",
  "prep_minutes": 18, "servings": 2,
  "kcal_per_serving": 520, "protein_g_per_serving": 42,
  "carbs_g_per_serving": 38, "fat_g_per_serving": 18,
  "tags": ["high_protein", "quick"],
  "instructions": "1. ... 2. ...",
  "ingredients": [
    { "name": "Chicken breast", "quantity_g": 300, "display_amount": "2 fillets" },
    { "name": "Rice", "quantity_g": 150, "display_amount": "3/4 cup dry" }
  ]
}
```

## 5. Nutrition validation

Don't blindly trust the model's macro numbers:
1. For each ingredient, try to match `foods` (name/alias) and recompute macros from catalog × quantity.
2. Sum, divide by servings → our **authoritative** per-serving macros.
3. If catalog coverage is partial, blend catalog values with the model's per-ingredient estimate; store the result.
4. Sanity-check against constraints (e.g. if `kcal_per_serving` blew past `max_kcal` significantly, drop or regenerate that recipe).

This keeps recipe nutrition consistent with how meals are computed elsewhere.

## 6. Saving & ownership

- Generated recipes are persisted immediately with `is_ai_generated=true` and `user_id` = requester (so they appear in history even before "save").
- `POST /recipes/{id}/save` marks/keeps it in the user's collection (e.g. a `saved` flag or simply that it belongs to them).
- Seed/global recipes may have `user_id=null` and be visible to everyone (`GET /recipes`).

## 7. Shopping list

- `POST /shopping-list/from-recipe/{recipe_id}` appends that recipe's ingredients to `shopping_list_items` (name + display amount + `recipe_id` origin).
- Merge logic (P2 nicety): if the same ingredient already exists unchecked, combine quantities where units allow; otherwise add a separate line.
- `PATCH /shopping-list/{id}` toggles `checked`; `DELETE` removes; a "clear checked" action removes all checked items.

## 8. Edge cases

| Case | Handling |
|---|---|
| Constraints impossible (e.g. 200 kcal & 60 g protein) | return best-effort recipes + a note that constraints were hard to meet; never fabricate impossible macros. |
| Invalid JSON from model | one repair retry → else `AI_PROVIDER_ERROR`. |
| Diet tag conflicts (vegan + chicken on-hand) | honor the tag (vegan wins); ignore conflicting on-hand items. |
| Allergens | out of scope for v1 beyond respecting diet tags; note as a future enhancement. |

## 9. Testing hooks

- `FakeTextProvider` returns fixture recipes (valid, invalid-JSON, over-budget) to test parsing, nutrition recompute, and constraint filtering.
- Unit-test the catalog-based nutrition recompute and the shopping-list merge.
- See `12_Testing_Plan.md`.
