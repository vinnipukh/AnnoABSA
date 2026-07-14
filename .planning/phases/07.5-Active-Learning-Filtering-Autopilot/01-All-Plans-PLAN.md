# PLAN.md — Phase 7.5: Active Learning, Filtering & Autopilot Rework

**Phase:** 7.5
**Goal:** Make active learning work in 4-Way Mode: train TF-IDF + LogisticRegression on user-annotated triplets, add an autopilot button that auto-predicts and saves for unlabeled reviews, iterate through the dataset. **The main purpose of this app is now 4-Way Comparison** — all features must default to 4-way mode. Write comprehensive integration tests for ALL 4-way toolbar elements. Rewrite tests when needed.

**Wave execution:** Sequential (Plan 1 → Plan 2 → Plan 3 → Plan 4)

---

## Plan 1: Backend — ML Predict-and-Save Autopilot Endpoint

**Files to read first:**
- `services/active_learning.py` — existing TF-IDF + LogisticRegression pipeline
- `app/routes/learning.py` — existing `/learning/suggestions` and `/learning/predict` endpoints
- `app/routes/reviews.py` — existing save endpoint
- `app/data.py` — `load_data()`, `save_data()`
- `models/schemas.py`

**Files to modify:**
- `services/active_learning.py` — add `predict_texts()` function
- `app/routes/learning.py` — add `POST /learning/autopilot` endpoint
- `models/schemas.py` — add `AutopilotRequest` model

**Objective:** Create a `POST /learning/autopilot` endpoint that:
1. Trains TF-IDF + LogisticRegression on all user-annotated reviews (reviews with non-empty `label` column)
2. For each unlabeled review, predicts triplets, saves them, reports progress
3. Returns a summary of how many reviews were auto-annotated

### Design Principles (applied)

- **Separation of Concerns**: Business logic (predict + format) goes in `services/active_learning.py`, HTTP concerns (parse request, call service, return response) go in the route handler — same layering as existing `train_labeled_data` / `get_uncertainty_scores`.
- **Single Responsibility**: The new `predict_texts()` service function predicts + formats only. The endpoint loads data, orchestrates the loop, saves, returns. Each has one reason to change.
- **KISS**: No factory, no strategy pattern, no abstract base. A new function + a new endpoint using the same patterns as `GET /learning/predict/{idx}`.
- **Inject dependencies**: `train_labeled_data` already takes `texts, labels` as plain parameters (no global state). `predict_texts` follows the same pattern — takes `model_data + texts`, returns formatted predictions.
- **Don't mix I/O with business logic**: `load_data()` / `save_data()` calls are in the endpoint, not the service function.

### Changes

1. **Add `predict_texts()` to `services/active_learning.py`**:
   - `predict_texts(model_data: dict, texts: list, confidence_threshold: float = 0.5) -> list[list[dict]]`
   - For each text, calls `model.predict_proba([text])`, filters by `confidence_threshold`, formats as triplet dicts `{aspect_category, sentiment_polarity, label, confidence}`
   - Returns `[[{...}, ...], ...]` — one list of triplets per input text
   - Pure function (no I/O), easily testable

2. **Add `AutopilotRequest` to `models/schemas.py`**:
   - `count: int = 10` — how many reviews to auto-annotate
   - `confidence_threshold: float = 0.5` — minimum confidence to accept a prediction
   - `start_index: int | None = None` — where to start (None = first unlabeled)

3. **Add `POST /learning/autopilot` endpoint to `app/routes/learning.py`**:
   - Thin handler — loads data, calls service functions, saves, returns
   - Error response if < 2 labeled reviews exist (400)
   - Error response if 0 unlabeled reviews remain (200 with `annotated: 0, message: "..."`)
   - Uses `df.at[idx, "label"] = json.dumps(triplets)` for CSV — same save pattern as `POST /review/{idx}/save`

4. **Handle the 4-way CSV label column**:
   - Uses universal `label` column — same as `POST /review/{idx}/save`
   - `labeled_texts_from_data` already reads `label` column (or `original_label` fallback)
   - Predictions saved to `label` column — no special 4-way handling needed
   - `GET /data/{idx}` automatically picks up saved labels

**Acceptance criteria:**
- `POST /learning/autopilot` returns 400 if < 2 labeled reviews exist
- For a CSV with 100 reviews, 5 labeled: autopilot trains on 5, predicts for next N unlabeled, saves them
- Predicted triplets are saved in same format as manual annotations (JSON in `label` column)
- Works identically on 4-way NEWUI CSV and standard CSV
- Returns correct count of annotated reviews

**Tests:**
- `tests/test_active_learning.py` — add `test_predict_texts_empty`, `test_predict_texts_filtered`
- `tests/test_learning_routes.py` — add 5-8 integration tests:
  - Test autopilot with 2+ labeled reviews → predictions saved
  - Test autopilot with < 2 labeled → 400 error
  - Test autopilot confidence_threshold filters low-confidence predictions
  - Test autopilot count parameter limits annotations
  - Test autopilot saves are readable and in valid JSON

---

## Plan 2: Frontend — Autopilot Button in 4-Way Toolbar

**Files to read first:**
- `frontend/src/App.tsx` — main app component, mode management
- `frontend/src/components/FourWayGrid.tsx` — existing 4-way toolbar
- `frontend/src/hooks/useReviewNavigation.ts` — saveReview, loadReviewRow
- `frontend/src/types.ts` — AppActions, settings types

**Files to modify:**
- `frontend/src/App.tsx` — add autopilot handler
- `frontend/src/types.ts` — add autopilot to AppActions
- `frontend/src/components/FourWayGrid.tsx` — add autopilot button in toolbar

**Objective:** Add an "Otomatik Etiketle" (Auto-Annotate) button to the 4-way mode toolbar that calls the autopilot endpoint and shows progress.

### UI/UX Constraints

- **No emoji icons** (Priority 4): The autopilot button must use a Heroicons SVG icon, not ⚡ emoji. Use the Lightning bolt SVG from `svg-icon-replacements.md`:
  ```tsx
  <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 10V3L4 14h7v7l9-11h-7z" />
  </svg>
  ```
- **Touch targets ≥44×44px** (Priority 2): The autopilot button must be at least 44×44px hit area. Use the same button pattern as the existing toolbar (inline Tailwind `px-2 py-1 text-[10px] font-bold rounded-md` + `min-h-[36px]`).
- **Button style consistency** (Priority 4): The autopilot button must use the SAME class pattern as the existing toolbar buttons in `FourWayGrid.tsx`. Do NOT use DaisyUI `btn` classes if the toolbar uses inline Tailwind, and vice versa. Read the existing button patterns from the file first.
- **Loading state** (Priority 2): Button must show loading spinner + disabled state during autopilot execution. Use the inline spinner from `svg-icon-replacements.md`:
  ```tsx
  <div className="w-4 h-4 border-2 border-primary border-t-transparent rounded-full animate-spin" />
  ```
- **Color not sole indicator** (Priority 1): The loading/disabled state must use opacity change + spinner + text change, not just color.
- **Accessibility** (Priority 1): Icon-only elements must have `aria-label`. The button text "Otomatik Etiketle" serves as visible label, so no separate aria-label needed on the button itself. The loading spinner is decorative and has `aria-hidden="true"`.
- **Toast feedback** (Priority 8): Success/error toasts must use the existing `setSaveToast` pattern, auto-dismiss in ~3s. Use Turkish text: `"{N} inceleme etiketlendi"` for success, `"Hata: {error}"` for failure. **No emoji in toast messages** (scan `setSaveToast` calls for emoji regression).
- **Modified-file emoji scanning**: Both `FourWayGrid.tsx` and `App.tsx` must be scanned for existing emoji in toast messages, button text, and labels. Fix any found.
- **React 19 test workaround**: All new tests must use `createRoot` + `flushSync` from `react19-testing-workaround.md`, not `@testing-library/react`.
- **Async data null-safety**: `App.tsx` render-time accesses to async-loaded data (`currentData?.field`, `navState?.currentIndex`) must use optional chaining.

### Changes

1. **Add `runAutopilot` to `AppActions` interface** in `types.ts`:
   - `runAutopilot: (count: number) => Promise<{annotated: number, total_unlabeled: number}>`

2. **Add autopilot handler in `App.tsx`**:
   - Function `handleRunAutopilot(count: number = 10)`:
     - Set loading state, disable button
     - `POST /learning/autopilot` with `{count, confidence_threshold: 0.5}`
     - On success: `setSaveToast(\`${data.annotated} inceleme etiketlendi (${data.total_unlabeled} kaldı)\`)`
     - On error: `setSaveToast(\`Hata: ${error.message}\`)`
     - Reload current review data via `loadReviewRow(currentIndex)`
     - Clear loading state
   - Wire into AppActions ref and pass to FourWayGrid

3. **Add autopilot button in `FourWayGrid.tsx` toolbar**:
   - Add a button in the toolbar row: Lightning SVG + "Otomatik Etiketle" text
   - Must match the existing toolbar button pattern (check the file — if inline Tailwind, use same classes; if DaisyUI `btn`, use `btn btn-sm btn-ghost`)
   - Tooltip (DaisyUI tooltip or `title` attribute): "Etiketlenmemiş incelemeleri ML ile otomatik etiketle"
   - On click: `props.runAutopilot(10)`
   - Disabled + spinner when loading
   - `aria-label` not needed (visible text label present)

4. **No toggle button needed** — autopilot is a one-shot action, not a persistent mode

**Acceptance criteria:**
- Autopilot button visible in 4-Way mode toolbar
- Clicking starts autopilot, shows loading state
- On success: toast with annotation count, data refreshes
- Button disabled during execution
- Works without crashing on empty/edge datasets
- 0 emoji in modified files (FourWayGrid.tsx, App.tsx)

**Tests:**
- `frontend/src/components/FourWayGrid.test.tsx` — add 2-3 tests:
  - Test autopilot button renders in 4-way mode
  - Test button becomes disabled during execution
  - Test success toast appears after completion

|---

## Plan 3: Integration & Test Rewrites

**Files to read first:**
- `tests/test_learning_routes.py` — existing learning route tests
- `tests/test_active_learning.py` — existing active learning tests
- `tests/conftest.py` — shared test fixtures

**Files to modify:**
- `tests/test_learning_routes.py` — add autopilot tests, fix any broken tests
- `tests/test_active_learning.py` — verify still pass

**Objective:** Ensure all existing tests still pass, add new tests for autopilot, verify everything works end-to-end in 4-way mode.

**Changes:**

1. **Add autopilot tests to `tests/test_learning_routes.py`**:
   - Create a NEWUI CSV fixture with `majority_vote`, `original_label`, `gemma4_31b_label`, `qwen3.6_35b_label`, `gpt_oss_120b_label` columns
   - Set first few rows to have `label` (user-annotated)
   - Test autopilot trains and predicts
   - Test autopilot respects confidence threshold

2. **Verify existing tests still pass**:
   - Run full pytest suite
   - Run full vitest suite
   - Fix any broken tests

3. **Manual verification in 4-way mode**:
   - Start app with NEWUI CSV
   - Manually annotate 3 reviews
   - Click autopilot → verify predictions appear on subsequent reviews
   - Verify saved data is readable in export

**Acceptance criteria:**
- All existing backend tests still pass (237+)
- All existing frontend tests still pass (88+)
- New autopilot tests pass (5-8 backend, 2-3 frontend)
- End-to-end: annotate 3 → autopilot → verify labels saved
- 0 TypeScript errors

|---

## Plan 4: 4-Way Mode Default, Hardening & Comprehensive Integration Tests

**Files to read first:**
- `frontend/src/App.tsx` — mode initialization, mode toggle logic
- `frontend/src/components/FourWayGrid.tsx` — all toolbar buttons (mode toggle, demo, export, filter, save, autopilot)
- `frontend/src/hooks/useCompareMode.ts` — compare mode state
- `frontend/src/types.ts` — Settings interface (compare_mode default)
- `app/config.py` — default config values
- `tests/conftest.py` — test fixtures for backend
- `frontend/src/components/SettingsPanel.test.tsx` — existing settings/frontend tests

**Files to modify:**
- `frontend/src/App.tsx` — default mode → `'4way'`, null-safety hardening
- `frontend/src/components/FourWayGrid.tsx` — null-safety on all button handlers
- `frontend/src/types.ts` — change default `compare_mode` if applicable
- `app/config.py` — change default `compare_mode` to `'4way'`
- `tests/test_learning_routes.py` — add autopilot edge case tests
- `frontend/src/components/FourWayGrid.test.tsx` — comprehensive 4-way integration tests

**Objective:** Make 4-Way Comparison the default mode and ensure clicking ANY button in 4-way mode never crashes — with data, without data, or during autopilot.

### Changes

1. **Default mode → 4-Way Comparison**:
   - In `app/config.py`'s `load_config()` default dict: change `"compare_mode": "csv"` → `"compare_mode": "4way"`
   - In `frontend/src/App.tsx`: change initial mode state from `'compare'` to `'4way'` (the default when no settings are loaded yet)
   - In `frontend/src/hooks/useCompareMode.ts`: verify default mode `'4way'` is handled
   - This ensures: fresh start → app loads in 4-way mode immediately

2. **Null-safety on ALL 4-way button handlers**:
   - For every button in `FourWayGrid.tsx`: wrap click handlers in try/catch with error toast fallback
   - Check `currentData` is non-null before accessing fields
   - Use optional chaining (`data?.field`) for all render-time accesses
   - Specific buttons to harden:
     - Mode toggle buttons (4-Way / Compare / Manual / Demo)
     - Export button (`handleExport4Way`)
     - Tier filter dropdown (`tierFilter` onChange)
     - Save button
     - **Autopilot button** (new — from Plan 2)
     - Any navigation controls rendered within FourWayGrid

3. **Comprehensive 4-way integration tests** — test ALL toolbar buttons:

   | Test | What it checks |
   |------|---------------|
   | **Default mode** | App loads in 4-way mode by default |
   | **Mode toggle to 4-way** | Clicking 4-Way button activates 4-way mode without crash |
   | **Mode toggle to Compare** | Clicking Compare button switches without crash |
   | **Mode toggle to Demo** | Clicking Demo loads demo data without crash |
   | **Mode toggle to Manual** | Clicking Manual switches without crash |
   | **Export button** | Clicking Export does not crash (may throw if no data — shows toast) |
   | **Tier filter** | Selecting each tier option (All/2/3) does not crash; Tier 1 option is removed |
   | **Save button** | Clicking Save does not crash (silent fail on no data) |
   | **Autopilot (no data)** | Clicking Autopilot when backend offline → error toast, no crash |
   | **Autopilot (with data)** | Clicking Autopilot with backend returning data → loading state, success toast |
   | **Multiple rapid clicks** | Rapidly clicking mode/Autopilot buttons → no race conditions |
   | **Navigation arrows** | Prev/Next buttons render without crash in 4-way mode |

4. **Remove Tier 1 from filter dropdown**:
   - Tier 1 = auto-resolved reviews where `majority_label == original_label` with high consensus — no human attention needed
   - Remove "Tier 1" option from the tier filter dropdown in `FourWayGrid.tsx`
   - Updated options: `All`, `Tier 2` (partial disagreement), `Tier 3` (low consensus)
   - Update `getReviewTier` logic: Tier 1 reviews are still identified internally (for autopilot/skip logic) but hidden from the filter UI
   - Users only need to focus on uncertain reviews (Tier 2 + Tier 3)

5. **Backend edge case hardening** (test level):
   - `POST /learning/autopilot` with 0 data items → graceful 400
   - `POST /learning/autopilot` with 1 labeled review → 400 (needs 2)
   - `POST /learning/autopilot` with all reviews already labeled → 200, `annotated: 0`
   - `GET /data/{idx}` in range for 4-way CSV → returns valid data
   - `GET /data/{idx}` out of range → 404, not 500

**Acceptance criteria:**
- Fresh app start loads in 4-way mode by default
- Every button in the 4-way toolbar can be clicked without crashing the app
- Missing/empty data shows Turkish error toast, not a blank white screen
- Autopilot with no labeled data shows helpful toast, not a crash
- All 4-way mode integration tests pass (15-20 frontend tests)
- All autopilot edge case tests pass (5-8 backend tests)
- 0 TypeScript errors

---

## Verification

| Check | Criteria |
|-------|----------|
| Backend tests | All existing + new autopilot tests pass |
| Frontend tests | All existing + new autopilot component tests pass |
| TypeScript | 0 errors |
| Autopilot (backend) | Trains on labeled data, predicts for unlabeled, saves correctly |
| Autopilot (frontend) | Button in 4-way toolbar, loading state, success toast, data refresh |
| Edge cases | < 2 labeled → graceful error; empty dataset → graceful error; 0 unlabeled → skip |
| 4-Way compatibility | All features work with NEWUI CSV format — uses universal `label` column |
