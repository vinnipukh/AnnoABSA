# Session Analysis — Phase 1 Completion & Root Reorganization

---

## SCHEMA/DATA MODEL
- [SCHEMA/DATA MODEL] Parse_triplet_column handles 3 triplet formats: STD tuples `[('term','CAT','pol')]`, STD lists `[['term','CAT','pol']]`, and dict format — `main.py:parse_triplet_column`, `tests/test_main_helpers.py:TestParseTripletColumn`
- [SCHEMA/DATA MODEL] Triple label JSON schema includes `at_start`/`at_end` (0-indexed inclusive) and `ot_start`/`ot_end` for phrase positions — `agentdocs/ProjectPrimer.md:Data format`
- [SCHEMA/DATA MODEL] `"NULL"` is a literal string sentinel for implicit aspects/opinions. Never convert to `""` — `architecture_map.md:Known landmines`
- [SCHEMA/DATA MODEL] SaveTripletsRequest and AgentChatRequest moved to `models/schemas.py` as the sole home for shared Pydantic models — `models/schemas.py`

## COMPARISON LOGIC
- [COMPARISON LOGIC] Backward-compat CSV columns (`aspect_triplets` → Model A, `new_triplets` → Model B) handled via ~10 lines of compat code in `get_data()` — `main.py:get_data` lines ~415-425
- [COMPARISON LOGIC] External `--compare-model-a-csv`/`--compare-model-b-csv` override inline column format when both present — `main.py:get_data`
- [COMPARISON LOGIC] `generate_mock_reasoning()` produces Turkish-language analysis comparing common/unique aspects between models — `services/prediction.py:generate_mock_reasoning`

## UI/UX DECISION
- [UI/UX DECISION] Two-click selection pattern for span annotation: first click sets `selStart`, second sets `selEnd`. Clicking same ref twice is reliable; different refs sometimes reset selection — `tests/testcases.md:Browser tool interaction notes`
- [UI/UX DECISION] Continuous text runs (merged by background color) avoid per-character span borders — `PhraseAnnotator.tsx:L166-175`
- [UI/UX DECISION] "No blocked state" for save button: defaults are `categories[0]` and `'positive'`, button always enabled — `MA6`

## BUG/ISSUE
- [BUG/ISSUE] `build_absa_models()` used `list[SentimentElement]` inside a nested class body where Python couldn't eagerly resolve the dynamically-created type. Fixed with forward reference `list['SentimentElement']` — `services/prediction.py:build_absa_models` (L354)
- [BUG/ISSUE] P5: saved triplets lost on row re-navigation because `loadReviewRow` called `setManualTriplets([])` unconditionally. Fixed by parsing `data.label` from API response and restoring triplets — `App.tsx:loadReviewRow` (L119-148)
- [BUG/ISSUE] Post_data and post_annotations endpoints were dead code (no frontend callers). POST `/review/{idx}/save` is the only live save endpoint — `main.py` (deleted), `App.tsx:handleNextReview`
- [BUG/ISSUE] Predict_openai had no callers (wrapped OpenAIProvider which exists directly) — `main.py` (deleted)
- [BUG/ISSUE] Item and AnnotationData Pydantic models were unused after endpoint deletions — `main.py` (deleted)
- [BUG/ISSUE] pyproject.toml had `requires-python = ">=3.14"` (wrong for 3.11 runtime) and empty dependencies. Fixed — `pyproject.toml`

## AGENT BEHAVIOR
- [AGENT BEHAVIOR] Route extraction (Steps 5-7) was attempted with build_routes.py using line ranges that shifted after earlier deletions, producing a broken `api/routes_reviews.py`. The agent aborted and deleted the broken file, keeping endpoints in main.py — recognizing the mechanical cost outweighed the benefit at this scale
- [AGENT BEHAVIOR] Multiple docstring-editing attempts via patch tool introduced double-quote escaping issues, resulting in `""""` (4 quotes) instead of `"""` (3) in the OllamaProvider class docstring. Fixed by direct hex byte manipulation
- [AGENT BEHAVIOR] Self-import bug in predict_llm rewrite: wrote `from services.llm_providers import OllamaProvider` inside `services/llm_providers.py`. Caught and corrected — `services/llm_providers.py:predict_llm`
- [AGENT BEHAVIOR] Agent was blocked by the system's tool-iteration limit (~30 calls) before completion on multiple occasions, leaving work partially done (predict_llm rewrite was at line 22 without the instantiation line at line 23)
- [AGENT BEHAVIOR] Browser JS console evaluations with multi-line expressions consistently failed with `SyntaxError: Unexpected end of input` — all JS must be single-line in this environment
- [AGENT BEHAVIOR] Terminal commands requiring user approval (`-e/-c` flags, recursive deletes) frequently blocked execution, requiring alternative approaches

## OPEN WORK
- [OPEN WORK] API route extraction (Steps 5-7) was abandoned due to line-shift issues. main.py is ~1022 lines with all 12 endpoints. Accepted as-is until/unless main.py reaches 1500+ lines — `agentdocs/phase2_prep.md:item 6`
- [OPEN WORK] Examples/user_dataset.csv uses old inline-column format (`aspect_triplets`, `new_triplets`). Kept as backward-compat fixture; compat code in main.py stays — `agentdocs/phase2_prep.md:item 8`
- [OPEN WORK] Evaluation data was already cleaned (1.9 MB remaining = source datasets, not regeneratable predictions). Closed as done — `agentdocs/phase2_prep.md:item 7`
- [OPEN WORK] Duplicated template constants and `_derive_provider` between services/ and cli.py resolved by shared imports (issue #4). cli.py now imports directly from `services.prediction` and `services.llm_providers`
- [OPEN WORK] eval.py import fragility resolved by stable compatibility shim (issue #5): `predict_llm` delegates to `OllamaProvider` via the adapter pattern, keeping the same API surface
- [OPEN WORK] No automated tests for frontend behavior (S1-S4, MA1-MA6, KA1, P1-P5 browser tests). Requires live backend + browser walkthrough via `tests/testcases.md`
