# 07 — AI Food Recognition

> **Document status:** Draft v1
> **Owner:** Engineering / AI
> **Related docs:** `02_System_Architecture.md`, `03_Database_Schema.md`, `04_API_Spec.md`
> **Code home:** `backend/app/ai/vision/`

---

## 1. Goal

Turn one meal photo into a **draft list of food items** with estimated portions and nutrition, accurate enough to be a great starting point — never presented as final. The user always confirms/edits before anything is saved (`05` §Image Review).

## 2. Where it sits

```
POST /meals/analyze
   → meals.service.analyze()
       → AIVisionProvider.recognize(image)         # app/ai/vision/
           → returns detected items (name, grams, confidence, raw nutrition?)
       → nutrition.resolve_items(detected)         # hybrid match to foods catalog
       → returns DRAFT (items + totals)            # NOT persisted
```

The provider SDK is imported **only** inside `app/ai/vision/`. Everything else depends on the adapter interface below (`CLAUDE.md` rule).

## 3. Adapter interface

```python
# app/ai/vision/base.py
class DetectedItem(BaseModel):
    name: str
    name_he: str | None = None
    quantity_g: float                 # estimated portion (or ml if liquid)
    confidence: float                 # 0..1
    # optional per-100 nutrition the model is fairly sure about:
    kcal_per_100: float | None = None
    protein_per_100: float | None = None
    carbs_per_100: float | None = None
    fat_per_100: float | None = None
    is_liquid: bool = False

class AIVisionProvider(Protocol):
    async def recognize(self, *, image_url: str, locale: str) -> list[DetectedItem]: ...
```

Concrete impls (e.g. `OpenAIVisionProvider`, `GeminiVisionProvider`) live beside it and are selected by the `AI_VISION_PROVIDER` env var. A `FakeVisionProvider` returns fixtures for tests (no network).

## 4. Prompt design (vision LLM)

System prompt, in spirit:

> You are a nutrition vision assistant. Identify each distinct food/drink in the image. For each, give a short name (English + Hebrew if locale is he), estimate the portion in grams (or ml for liquids) using visual cues (plate size, utensils, common serving sizes), and your confidence 0–1. If you recognize a standard food, you may include approximate per-100g macros. Do not invent items you cannot see. Return **only** JSON matching the schema.

Rules baked in:
- **Structured JSON only** (we parse it; no prose). Validate against the schema; on parse failure, one repair retry, then error.
- **Per-item, not per-meal** — a plate of chicken + rice + salad is three items.
- **Portion estimation** uses visual anchors; when unsure, prefer common serving sizes and lower the confidence.
- **Locale-aware names** so Hebrew users see Hebrew item names.

## 5. Hybrid nutrition resolution

For each `DetectedItem` we produce final per-portion nutrition (`nutrition.resolve_items`):

1. **Catalog match first.** Look up `foods` by exact/alias/trigram name (and `barcode` for scans). On a confident match → use catalog per-100 values × `quantity_g / 100`. Set `meal_item.food_id`, `source='catalog'`.
2. **AI values fallback.** No catalog match but the model returned per-100 macros → use those, set `source='ai'`, leave `food_id` null. Optionally create a `foods` row with `source='ai_generated'` for reuse.
3. **Unknown.** No match, no macros → keep the item with `quantity_g` and zeros, flag low confidence, and prompt the user to set it (the edit UI makes this easy).

Fiber/sugar/sodium come from the catalog when matched; if only AI macros exist, those secondary fields may be null until the user or a later catalog match fills them.

> **Why hybrid:** the catalog gives consistency and the secondary nutrients (fiber, sodium) that drive the Health Score; the AI gives coverage for the long tail of dishes the catalog doesn't have.

## 6. Confidence handling

- `confidence ≥ 0.75` → shown normally, checked ✓.
- `0.5 ≤ confidence < 0.75` → shown with a subtle `warning` marker ("double-check this").
- `confidence < 0.5` → still shown but visually de-emphasized and easy to remove.

Confidence never blocks logging — it only guides the user's attention. The user's edits are the ground truth (`meal_items.edited_by_user`), and the **acceptance rate** (items kept unedited) is our headline accuracy metric (`01` §metrics).

## 7. Barcode path

`POST /meals/barcode` skips vision entirely: look up `foods.barcode`; if found, return a single draft item scaled to a default/asked portion; if not found, return "unknown barcode" so the user can add it manually.

## 8. Caching, latency, cost

- **Cache by image hash.** Identical image (re-submitted) returns the cached recognition — saves cost and time.
- **Latency:** MVP runs synchronously (request blocks on the model). If p95 latency is poor, move to **async**: `POST /meals/analyze` returns a `job_id`, the client polls or gets a push when ready (`02` §10, P1).
- **Cost controls:** rate-limit `/meals/analyze` per user (`04`); choose a model tier appropriate to quality needs; downscale/compress images client-side before upload (long edge ~1024px is plenty).

## 9. Failure & edge cases

| Case | Handling |
|---|---|
| Model returns invalid JSON | one repair retry → else `AI_PROVIDER_ERROR` (502) with a friendly client message. |
| No food detected | return empty draft + "couldn't spot a meal — try another photo or add manually." |
| Non-food image | empty draft; never fabricate items. |
| Mixed/complex dish (e.g. stew) | allow a single combined item; user can split. |
| Multiple plates / large spread | detect all; user prunes. |
| Provider timeout / outage | surface retry; allow manual entry as the fallback path. |

Manual entry (`POST /meals/manual`) always exists so a vision failure never blocks logging.

## 10. Privacy

- Meal images are private (signed URLs, `02` §7).
- Only the image (and locale) is sent to the provider; no user identity or health history is attached to a recognition call.
- Image retention policy is configurable; users deleting a meal/account removes associated images (`03` §6).

## 11. Testing hooks

- `FakeVisionProvider` fixtures cover: single item, multi-item plate, liquid, low-confidence, empty/non-food, invalid-JSON-then-repair.
- Unit-test `nutrition.resolve_items` for all three resolution paths (catalog hit, AI fallback, unknown).
- See `12_Testing_Plan.md`.
