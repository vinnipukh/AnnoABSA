# Phase 7.2: Testing & TypeScript Fixes — Plan

**Phase:** 7.2-Testing-and-TSFixes
**Planned:** 2026-07-13
**Execution mode:** Parallel (all plans independent)
**Status:** Not started

---

## Plan 1: Tests for `services/active_learning.py`

**Goal:** Add comprehensive unit tests for the active learning service module.
**Est. effort:** Easy
**Files:** `tests/test_active_learning.py`
**Target:** `services/active_learning.py` (190 lines)

### Implementation Steps

1. Create `tests/test_active_learning.py` with three test classes mirroring the module's three public functions:

   **`TestLabeledTextsFromData`:**
   - `test_json_format_returns_texts_and_labels` — Valid JSON records with `label` array of dicts (aspect_category, sentiment_polarity)
   - `test_csv_format_returns_texts_and_labels` — DataFrame rows with JSON-string `label` column
   - `test_empty_labels_returns_empty_sets` — Reviews with `""` or `"[]"` label value → empty label_sets
   - `test_missing_category_or_polarity_skips_label` — Label dict missing key → skipped
   - `test_malformed_json_falls_back_to_ast_literal_eval` — JSONDecodeError triggers ast.literal_eval fallback
   - `test_both_fallback_fails_returns_empty` — Unparseable string → empty list
   - `test_none_label_handling` — `pd.isna(raw_label)` path for `None`/`NaN` values

   **`TestTrainLabeledData`:**
   - `test_returns_model_with_label_columns` — 2+ labeled reviews returns dict with 'model' and 'label_columns'
   - `test_returns_none_when_no_labels` — No labels found → None
   - `test_returns_none_when_fewer_than_2_labeled` — Single labeled review → None
   - `test_multilabel_binary_matrix_shape` — 3 reviews with labels in 2 categories → y.shape=(3,2)
   - `test_model_is_fitted_pipeline` — returned model has `predict_proba` and `predict`

   **`TestGetUncertaintyScores`:**
   - `test_returns_array_matching_input_length` — N texts → array of length N
   - `test_higher_score_for_ambiguous_input` — Predict_proba near 0.5 → higher entropy
   - `test_zero_score_for_certain_prediction` — Perfectly confident → near-zero entropy
   - `test_all_positive_gives_zero_entropy` — All p=1.0 → entropy=0 per label
   - `test_values_are_non_negative` — All scores ≥ 0

2. Use parametrize decorators (pytest.mark.parametrize) for edge cases
3. No mocking needed — sklearn pipeline is pure computation

### UAT Criteria
- [ ] 12+ tests pass
- [ ] All edge cases covered: empty data, single label, mixed polarity
- [ ] 100% line coverage of the three public functions

---

## Plan 2: Tests for `app/routes/learning.py`

**Goal:** Add FastAPI TestClient tests for the learning route endpoints.
**Est. effort:** Easy
**Files:** `tests/test_learning_routes.py`
**Target:** `app/routes/learning.py` (169 lines)

### Implementation Steps

1. Create `tests/conftest.py` with shared fixtures that all backend test files can reuse:
   - `csv_path` fixture: `tempfile.NamedTemporaryFile` with `TEST_REVIEWS_CSV` constant (reproduces pattern from `test_live_prediction.py`)
   - `app` fixture (module scope): Set `ABSA_DATA_PATH` env var, import main, mutate `CONFIG_DATA` in-place, return `TestClient(main.app)`
   - `reset_config` fixture (autouse): Reset per-test config state

2. Create `tests/test_learning_routes.py`:

   **`TestGetLearningSuggestions`:**
   - `test_returns_suggestions_with_ranked_indices` — Unlabeled reviews get sorted by uncertainty desc
   - `test_empty_suggestions_when_all_labeled` — All reviews have labels → `{"suggestions": [], "message": "..."}`
   - `test_default_n_is_5` — No `n` param → 5 suggestions
   - `test_custom_n_returns_requested_count` — `?n=3` → 3 suggestions
   - `test_returns_uncertainty_1_when_not_enough_labels` — <2 labeled reviews → uncertainty=1.0 uniform
   - `test_error_handling_on_data_load_failure` — Corrupted data path → 500

   **`TestGetLearningPredict`:**
   - `test_returns_predictions_for_valid_index` — 2+ labeled reviews → list of predictions
   - `test_predictions_contain_all_required_keys` — Each prediction has aspect_category, sentiment_polarity, confidence, label
   - `test_out_of_range_index_returns_404` — Index beyond data length → 404
   - `test_400_when_not_enough_labeled_data` — <2 labeled reviews → 400
   - `test_negative_index_returns_404` — Negative index → 404

3. Use `labeled_reviews_csv` fixture with pre-labeled data rows (set `label` column to JSON strings)

### UAT Criteria
- [ ] 12+ tests pass via TestClient
- [ ] Both endpoints tested: suggestions and predict
- [ ] Edge cases: empty data, insufficient labels, out-of-range indices

---

## Plan 3: Tests for `cli/` package

**Goal:** Add unit tests for `cli/config.py`, `cli/convert.py`, and smoke tests for `cli/runner.py`.
**Est. effort:** Easy
**Files:** `tests/test_cli.py`
**Target:** `cli/config.py` (258 lines), `cli/convert.py` (33 lines), `cli/runner.py` (180 lines)

### Implementation Steps

1. Create `tests/test_cli.py` with three classes:

   **`TestAbsaAnnotatorConfig`:**
   - `test_initial_config_has_defaults` — Constructor sets all expected keys
   - `test_set_sentiment_elements_valid` — Valid elements pass validation
   - `test_set_sentiment_elements_invalid_raises` — Invalid element → ValueError
   - `test_set_sentiment_polarities` — Custom polarities stored correctly
   - `test_set_aspect_categories` — Custom categories stored correctly
   - `test_set_implicit_aspect_allowed` — Toggle True/False
   - `test_set_llm_provider_valid` — Valid providers accepted
   - `test_set_llm_provider_invalid_raises` — Invalid provider → ValueError
   - `test_set_n_few_shot_negative_raises` — Negative value → ValueError
   - `test_set_annotation_guideline_missing_raises` — Non-existent path → ValueError
   - `test_get_config_returns_copy` — Mutations don't affect internal state
   - `test_save_and_load_roundtrip` — `save_config()` → `load_config()` preserves all keys
   - `test_load_config_file_not_found_exits` — Missing file → sys.exit(1) (use pytest.raises(SystemExit))
   - `test_load_config_invalid_json_exits` — Malformed JSON → sys.exit(1)

   **`TestStdTripletsToLabel`:**
   - `test_valid_triplet_string` — `"[['NULL', 'course general', 'positive']]"` → list of dicts
   - `test_empty_string_returns_empty` — `""` → `[]`
   - `test_nan_string_returns_empty` — `"nan"` → `[]`
   - `test_none_returns_empty` — `None` → `[]`
   - `test_multi_triplet_parsing` — Multiple triplets all parsed
   - `test_short_triplet_skipped` — `<3 elements` → skipped
   - `test_invalid_input_returns_empty` — Unparseable → `[]`

   **`TestRunnerUtils`** (pure functions, no process spawning):
   - `test_is_port_in_use_free_port` — Random port → False
   - `test_is_port_in_use_bound_port` — Bind then check → True
   - `test_update_vite_port_config` — Regex substitution works (use `tmp_path`)

2. Use `tmp_path` fixture for file operations (config save/load, vite config update)
3. Mock `subprocess.Popen` for runner tests that would start actual servers
4. Use `pytest.raises(SystemExit)` for config error paths

### UAT Criteria
- [ ] 18+ tests pass
- [ ] Config roundtrip (save → load) verified
- [ ] STD format conversion edge cases covered
- [ ] Runner utility functions tested (port checks, config update)

---

## Plan 4: Endpoint tests for settings, timing, upload routes

**Goal:** Add TestClient tests for the remaining untested route files.
**Est. effort:** Medium
**Files:** `tests/test_routes_misc.py`
**Target:** `app/routes/settings.py` (97 lines), `app/routes/timing.py` (83 lines), `app/routes/upload.py` (54 lines)

### Implementation Steps

1. Create `tests/test_routes_misc.py` with three classes. Reuse `conftest.py` fixtures from Plan 2.

   **`TestSettings`:**
   - `test_get_settings_returns_all_keys` — GET /settings returns 25+ config keys
   - `test_get_settings_includes_current_index` — Response has current_index, max_number_of_idxs
   - `test_get_settings_includes_session_id_when_set` — CONFIG_DATA has session_id → returned
   - `test_patch_settings_updates_config` — PATCH /settings with `{"theme": "light"}` → CONFIG_DATA updated
   - `test_patch_settings_persists_to_file` — CONFIG_PATH set → file contains updated value
   - `test_patch_settings_returns_ok` — Response `{"status": "ok"}`
   - `test_multiple_keys_can_be_updated_at_once` — PATCH with 3 keys → all applied
   - `test_get_settings_after_patch_reflects_changes` — GET after PATCH shows new values (order-dependent test)

   **`TestTiming`:**
   - `test_post_timing_adds_entry` — POST /timing/0 with `{"duration": 5.0, "change": true}` → entry persisted
   - `test_get_avg_annotation_time_empty` — No timing data → avg_time=0.0, total_entries=0
   - `test_get_avg_annotation_time_with_data` — Multiple timing entries → correct average
   - `test_post_timing_out_of_range_404` — Index beyond data → 404

   **`TestUpload`:**
   - `test_upload_csv_file` — POST /upload-data with multipart CSV file → 200 with total_count
   - `test_upload_json_file` — POST /upload-data with JSON file → 200
   - `test_upload_unsupported_format_400` — .txt file → 400
   - `test_auto_add_positions` — POST /auto-add-positions → 200
   - `test_upload_no_file_400` — Missing file → 400

2. For upload tests, use `client.post("/upload-data", files={"file": ...})` with `io.BytesIO` for in-memory file data
3. For settings persistence, set `main.CONFIG_PATH` to a tmp_path location

### UAT Criteria
- [ ] 12+ tests pass
- [ ] Settings GET/PATCH roundtrip verified
- [ ] Timing POST/GET endpoints tested with various states
- [ ] Upload endpoint with CSV, JSON, and unsupported format
- [ ] Auto-add-positions endpoint reachable

---

## Plan 5: Frontend hardening — tsconfig, Vite upgrade, App.tsx split, TS fixes

**Goal:** Fix 3 pre-existing TS errors, tighten tsconfig, upgrade Vite, and split App.tsx into custom hooks.
**Est. effort:** Medium
**Files:** `frontend/tsconfig.json`, `frontend/vite.config.js`, `frontend/package.json`, `frontend/src/App.tsx`, `frontend/src/components/NlpHelperToolbar.test.tsx`, `frontend/src/hooks/useReviewNavigation.ts`, `frontend/src/hooks/useAnnotationState.ts`, `frontend/src/hooks/useAIPrediction.ts`, `frontend/src/hooks/useSettings.ts`, `frontend/src/hooks/useCompareMode.ts`, and their `.test.ts` files.

### Implementation Steps

#### 5a. tsconfig tightening (TSFIX-03)

1. Change `"target": "es5"` → `"es2016"` in `tsconfig.json` (fixes `includes` error)
2. Change `"lib": ["dom", "dom.iterable", "es6"]` → `["dom", "dom.iterable", "es2016"]` (matches new target)
3. Keep `strict: false, noImplicitAny: false` — full strict mode deferred per discussion

#### 5b. Vite upgrade from 4.x to 5.x

1. Update `frontend/package.json`: `"vite": "^4.5.14"` → `"^5.4.19"` (latest v5.x)
2. Update `frontend/vite.config.js`:
   - Remove deprecated `esbuild` block (lines 26-29)
   - Remove deprecated `optimizeDeps.esbuildOptions` block (lines 30-38)
   - Keep all other config: `plugins: [react(...)]`, `test`, `server`, `build`
3. Run `npm install` in frontend directory to update lockfile

#### 5c. TSFIX-01 — Fix `rect` error in App.tsx

1. Locate `nlpToolbarSelection` state type definition (~line 447 in App.tsx)
2. Add `rect?: DOMRect` to the state type
3. This resolves `Property 'rect' does not exist on type '[text, sentence]'`

#### 5d. TSFIX-02 — Fix `global` error in NlpHelperToolbar.test.tsx

1. In `NlpHelperToolbar.test.tsx:46`, replace `global.fetch = mockFetch` with `vi.stubGlobal('fetch', mockFetch)`
2. `global` is deprecated in newer ESLint/TypeScript; `vi.stubGlobal` is the vitest-native equivalent

#### 5e. App.tsx split into custom hooks

1. Create `frontend/src/hooks/useReviewNavigation.ts`:
   - State: `currentIndex`, `currentData`, `totalCount`, `isLoading`
   - API: `fetchData()`, `saveReview()`, `goToNext()`, `goToPrev()`, `goToIndex()`
   - Return: `[state, actions]` tuple matching existing hook pattern

2. Create `frontend/src/hooks/useAnnotationState.ts`:
   - State: `manualTriplets`, `selectedModelAIds`, `selectedModelBIds`
   - API: `addTriplet()`, `removeTriplet()`, `selectAllModelA()`, `clearAllModelA()`, etc.
   - Preserves the `AppActions` interface that `HelperAgentChatbox` depends on via `useRef`

3. Create `frontend/src/hooks/useAIPrediction.ts`:
   - State: `aiSuggestions`, `liveModelATriplets`, `liveModelBTriplets`, `isAIPredicting`
   - API: `fetchAIPrediction()`, `fetchLivePrediction()`, `acceptSuggestion()`, `rejectSuggestion()`

4. Create `frontend/src/hooks/useSettings.ts`:
   - State: `settings`, `saveToast`
   - API: `fetchSettings()`, `updateSettings()` (PATCH /settings)

5. Create `frontend/src/hooks/useCompareMode.ts`:
   - State: `mode` (enum: "compare" | "manual"), `compareMode` (enum: "csv" | "live")
   - API: `toggleMode()`, `toggleCompareMode()`
   - No API calls — pure UI state

6. Each hook follows the `useTextSelection.ts` pattern:
   - `useState` for local state
   - `useCallback` for stable function references
   - `useMemo` for derived values
   - Returns `[state, actions]` tuple

7. Create hook test files (one per hook with non-trivial logic):
   - `frontend/src/hooks/useReviewNavigation.test.ts` — Test index navigation, data loading
   - `frontend/src/hooks/useAnnotationState.test.ts` — Test add/remove triplets, select/deselect
   - `frontend/src/hooks/useAIPrediction.test.ts` — Mock fetch, test prediction states
   - `frontend/src/hooks/useSettings.test.ts` — Mock fetch/PATCH, test settings update

8. Update `App.tsx`:
   - Replace inline state management with hook calls
   - Compose all 5 hooks at the top level
   - Wire hook actions into the existing JSX structure
   - Ensure `useImperativeHandle` / `forwardRef` still exposes the full `AppActions` interface

### UAT Criteria
- [ ] TSFIX-01: `rect` error resolved (0 TS errors in App.tsx)
- [ ] TSFIX-02: `global` deprecation fixed in NlpHelperToolbar.test.tsx
- [ ] TSFIX-03: `includes` error resolved by tsconfig target change
- [ ] tsconfig target is `es2016`, lib includes `es2016`
- [ ] Vite upgraded to v5.x, no deprecated esbuild config
- [ ] 5 hooks extracted from App.tsx with clean state/API separation
- [ ] 4+ hook unit tests pass
- [ ] Existing 51 frontend tests still pass
- [ ] AppActions interface preserved (HelperAgentChatbox still works)
- [ ] `npm run build` succeeds (frontend compiles cleanly)

---

## Wave execution: Parallel

| Plan | Dependencies |
|------|-------------|
| Plan 1 (active_learning tests) | None |
| Plan 2 (learning routes tests) | None (uses its own conftest.py) |
| Plan 3 (CLI tests) | None |
| Plan 4 (settings/timing/upload tests) | None (reuses Plan 2's conftest) |
| Plan 5 (frontend hardening) | None |

All plans are independent. Use `delegate_task` to parallelize wave execution.

---

## Verification

After execution, run:
```bash
# Backend tests
cd /path/to/AnnoABSA
python -m pytest tests/ -q --tb=short

# Frontend tests
cd frontend && npx vitest run

# Verify count
python -m pytest tests/ --collect-only -q

# Verify 0 TS errors
cd frontend && npx tsc --noEmit
```

**Milestone targets:**
- 16+ new backend tests (133 → 149+)
- 4+ new hook tests (51 → 55+)
- 0 pre-existing TS errors
