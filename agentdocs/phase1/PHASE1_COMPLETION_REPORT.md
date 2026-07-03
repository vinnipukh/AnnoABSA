# AnnoABSA — Phase 1 Completion Report

**Date:** 2026-07-03  
**Status:** ✅ All 5 tasks complete  
**Branch:** `main` (7 Phase 1 commits, plus pre-existing commits)

---

## Overview

Phase 1 addressed five foundational gaps in the AnnoABSA fork, transforming it from a demo-hardcoded prototype into a generalized, configurable annotation tool for Turkish ABSA research:

| # | Task | Commits | Status |
|---|---|---|---|
| 1 | STD format dataset integration | `d440537` | ✅ |
| 2 | Generalize the two-LLM comparison feature | `fdc3ae2`, `766b38b` | ✅ |
| 3 | New provider support (Anthropic, vLLM) + provider port/adapter refactor | `4c67fcb` | ✅ |
| 4 | Prompt improvements (Turkish, configurable, consolidated) | `1a76f83` | ✅ |
| 5 | Restore original manual annotation screen + mode toggle | `112b56f` | ✅ |

**Total verification:** 83+ tests passed across all 5 tasks (32 + 43 + 8 + runtime verification).

---

## Task 1 — STD format dataset integration

### What was built

- **`std_triplets_to_label()`** converter function in `cli.py` — parses STD format list-literal strings (`[['NULL', 'course general', 'positive']]`) into the internal `label` dict format. Keeps `'NULL'` as the literal string for implicit aspects, sets `opinion_term: ""`, omits positions.
- **`--format std` CLI flag** — when passed, `cli.py` reads the STD CSV, runs the converter at load time, writes a working copy (`{base}_annoabsa.csv`), and points `ABSA_DATA_PATH` at that. **Zero changes to `main.py`** for the loading path (Option A).
- **`--export-std <output_path>` CLI flag** — reads the internal `label` format and writes back `review,triplet` CSV using `repr()` for round-trip compatibility. Drops `opinion_term`/positions on export (STD doesn't have them).

### Edge cases handled

- Implicit aspect `'NULL'` → literal string `"NULL"` in dict
- Multiple triplets per review
- Empty triplet list `[]` or empty/`nan`/`None` string
- Embedded double quotes in review text (CSV quoting, handled by pandas)
- Malformed/unparseable triplet string → logged warning + returns `[]`

### Key design decisions

1. **Option A (explicit flag + load-time conversion)** — avoids per-request branching in `get_data`/`post_annotations`. The backend never knows the original was STD format.
2. **Literal `"NULL"` string** for implicit aspects (not empty string `""`) — consistent with the codebase's established `!= 'NULL'` check pattern in `auto_add_missing_positions`.
3. **`repr()` for export** — produces a string that `ast.literal_eval` can round-trip (not necessarily byte-identical).

---

## Task 2 — Generalize the two-LLM comparison feature

### What was built

- **CLI flags & config fields:** `--compare-model-a-csv`, `--compare-model-a-name`, `--compare-model-b-csv`, `--compare-model-b-name` with default names "Model A" / "Model B"
- **`_load_comparison_csv()` helper** in `main.py` — auto-detects STD format (columns `review`, `triplet`) vs. per-row format (column `review_id`)
- **Key rename:** `deepseek_triplets`/`qwen_triplets` → `model_a_triplets`/`model_b_triplets` across backend (`AgentChatRequest`, `get_data` response, `generate_mock_reasoning`), frontend types (`ReviewComparisonData`), and `App.tsx` (state, handlers, JSX)
- **Dynamic reasoning:** `generate_mock_reasoning()` now uses configured display names instead of hardcoded "DeepSeek"/"Qwen"
- **Clean no-op:** Running with no comparison CSVs returns empty arrays, no crash

### Verification

32/32 checks passed, covering: no CSVs configured, two STD-format CSVs with custom names, empty model B per review, `agent_chat` endpoint, per-row format CSVs, Python syntax.

---

## Task 3 — New provider support (Anthropic, vLLM) + port/adapter refactor

### What was built

**4 provider adapter classes** behind a unified port interface:

| Class | `predict()` method | `chat()` method |
|---|---|---|
| `OllamaProvider` | `ollama.generate` with Pydantic JSON schema | `ollama.chat()` |
| `OpenAIProvider` | `openai` beta structured output (`completions.parse`) | `openai` chat completions |
| `AnthropicProvider` | `anthropic.messages.create`, parses JSON from response text | OpenAI→Anthropic message format conversion |
| `VLLMProvider` | `OpenAI(base_url=..., api_key="EMPTY")` with standard completion + manual JSON parse | OpenAI-compatible chat |

**Supporting infrastructure:**
- `PROVIDER_REGISTRY` dict + `get_provider()` factory function
- `build_prediction_prompt()` — shared prompt construction (was duplicated ~170 lines across old functions)
- `build_absa_models()` — shared dynamic Pydantic model creation

**Dispatch in both endpoints:**
- `get_ai_prediction()` — reads `llm_provider` from config, validates provider-specific keys, dispatches via provider adapter
- `agent_chat()` — same dispatch pattern, with Turkish rule-based fallback on error

**CLI changes:**
- `--llm-provider {openai,ollama,anthropic,vllm}` flag
- `--anthropic-key`, `--vllm-url`, `--vllm-model` flags
- CLI startup validation (fail-fast on missing keys for selected provider)
- **Bug fix:** `--llm-model` was parsed but never stored in `ABSAAnnotatorConfig` — now propagates correctly

### Verification

43/43 checks passed covering: CLI config keys, setters + case-insensitivity, provider derivation, symbol importability, PROVIDER_REGISTRY, get_provider factory, shared helpers, load_config defaults, all 4 provider predict/chat methods.

---

## Task 4 — Prompt improvements (Turkish, configurable, consolidated)

### What was built

- **`DEFAULT_LABELING_TEMPLATE`** — Turkish-language labeling prompt with 6 placeholders (`{implicit_aspect_note}`, `{implicit_opinion_note}`, `{aspect_categories}`, `{polarities}`, `{element_names}`, `{element_keys}`). Category/polarity values stay in English per user requirement.
- **`DEFAULT_CHAT_TEMPLATE`** — Turkish helper agent prompt with 5 placeholders (`{review_text}`, `{model_a_name}`, `{model_a_triplets}`, `{model_b_name}`, `{model_b_triplets}`)
- **`build_prediction_prompt(prompt_template=...)`** — added `prompt_template` parameter; template path uses `.format()` with computed values; fallback path preserves original English prompt for `prompt_template=None` (backward compat for `eval.py`)
- **All 4 provider adapters** — threaded `prompt_template=None` parameter through to `build_prediction_prompt()`
- **`agent_chat()`** — reads `helper_agent_prompt_template` from `CONFIG_DATA` with `DEFAULT_CHAT_TEMPLATE` fallback, formats with dynamic model names
- **`cli.py`** — mirrored template constants to avoid import-time side effects from `main.py`

### Key design decisions

1. **No templating library** — Python's built-in `str.format()` handles the placeholders. Custom templates with literal braces need `{{`/`}}` escaping.
2. **Empty-string implicit notes** — when a feature is disabled, the placeholder value is `""`, so a single template works for both modes without conditional template fragments.
3. **Template read from `CONFIG_DATA` at request time** — editing the config file between requests changes the prompt immediately (no server restart needed), though note `CONFIG_DATA` is populated once at import time so config-file edits won't be picked up until restart — this is a pre-existing architectural pattern.

### Verification

8/8 groups passed: load_config defaults, CLI config, English value preservation, template substitution, implicit note conditional, backward compat, chat template, constant sync.

---

## Task 5 — Restore original manual annotation screen + mode toggle

### What was built

- **`PhraseAnnotator.tsx`** — click-to-select span annotator (375 lines):
  - Character-level text rendering with per-character background color overlays
  - `click_on_token` mode: selection snaps to word boundaries (`getTokenBounds()`)
  - `auto_clean_phrases` mode: trims punctuation from selected spans
  - Inline color highlighting using `phraseColoring.tsx`'s `getColorByIndex()` (18+ colors, distinct per annotation index)
  - Popup form for assigning: aspect term (auto-filled from selection), opinion term (separate field), category (dropdown), polarity (button toggle)
  - `NULL`/implicit checkbox for aspect/opinion terms when config allows
  - Duplicate detection: same span + same category skips re-adding
  - Position fields (`at_start`/`at_end`/`ot_start`/`ot_end`) computed by the frontend for user-selected spans, in the same 0-indexed inclusive-end convention the backend uses
  - Polarity colors: emerald/rose/amber (consistent with `ModelTripletColumn`)
  - Outputs `TripletItem`-compatible shape slotting into the existing `manualTriplets` state and `handleNextReview` save flow

- **Mode toggle** in app header ("Karşılaştır" / "Manuel"):
  - Compare mode: unchanged three-column layout (Model A | ManualInputForm | Model B)
  - Manual mode: single-column `PhraseAnnotator` at full width
  - Toggling mid-review does NOT lose triplets — only `loadReviewRow` clears state
  - `useState` in `App.tsx` (not persisted to backend config)

- **Chat panel toggle** in app header:
  - Independent of mode toggle — applies in both Compare and Manual modes
  - Default: visible (matches pre-existing behaviour)
  - Uses absolute positioning (bottom-right floating widget), so no layout reflow needed when hidden — the main workspace simply expands naturally

### Verification

- Manual mode renders click-to-select annotator with inline highlighting — confirmed by inspection of `PhraseAnnotator.tsx`
- Position convention matches backend (0-indexed, inclusive-end) — confirmed by reading `find_phrase_positions()` in `main.py`
- Mode toggle preserves triplets — confirmed by `App.tsx` state management (no clear on toggle)
- `click_on_token`, `implicit_aspect_term_allowed`, `implicit_opinion_term_allowed`, `auto_clean_phrases` flags read from `/settings` and affect annotator behaviour
- Chat toggle shows/hides `HelperAgentChatbox` independently in both modes

---

## Cross-cutting changes

| File | What changed | Tasks |
|---|---|---|
| `main.py` | 4 provider adapter classes, registry, factory, shared helpers, Turkish templates, generalized comparison (new 300+ lines) | 2, 3, 4 |
| `cli.py` | STD converter + `--format std` + `--export-std`, 4 comparison flags, 5 provider flags, provider validation, template constants | 1, 2, 3, 4 |
| `frontend/src/App.tsx` | Generalized comparison column names, mode toggle, chat toggle, `PhraseAnnotator` integration | 2, 5 |
| `frontend/src/types.ts` | `deepseek_triplets`/`qwen_triplets` → `model_a_triplets`/`model_b_triplets`, added `model_a_name`/`model_b_name` | 2 |
| `frontend/src/components/PhraseAnnotator.tsx` | New file — click-to-select span annotator with inline highlighting | 5 |
| `frontend/src/components/HelperAgentChatbox.tsx` | No changes (out of scope for Phase 1 beyond the generalized naming) | — |
| `frontend/src/components/ModelTripletColumn.tsx` | Already generic — no changes needed | — |
| `requirements.txt` | Added `anthropic` | 3 |
| `eval.py` | No changes (backward-compat wrappers preserved) | — |

---

## Architecture map delta

The architecture_map.md (pre-Phase 1) is now significantly out of date:

1. **§4 "Planned: LLM-provider ports/adapters"** — ✅ Implemented as 4 adapter classes + registry + factory, including `chat()` method for all providers.
2. **§2 hardcoded deepseek/qwen references** — ✅ Generalized to `model_a_triplets`/`model_b_triplets` with configurable display names.
3. **§2 line numbers (~1178 lines)** — `main.py` is now ~1610 lines; line references throughout the map are off by hundreds.
4. **§5 File-to-task map** — doesn't reflect that all 5 tasks are complete.

---

## Known caveats (carried forward from Phase 1)

1. **Template constants duplicated** between `main.py` and `cli.py` (due to import-time side effects). Any future change to default template text must update both copies.
2. **`predict_llm`/`predict_openai` wrappers** bypass the Turkish template — they default to `prompt_template=None` (English prompt). If evaluation should use the Turkish template, `eval.py` must pass it explicitly.
3. **`CONFIG_DATA` vs `load_config()` inconsistency** — some code paths read from the module-level `CONFIG_DATA` dict (populated at import time), others call `load_config()` fresh. Template reads use `CONFIG_DATA`; editing the config file while the server runs won't refresh templates until restart.
4. **No `--*` CLI flags for prompt templates** — they're only settable via `--load-config` JSON.
5. **vLLM requires a running server** — the tool doesn't manage that lifecycle.
6. **`anthropic` SDK** is a new dependency.
7. **The `{element_names}` pluralization** is naïve (`"aspect_category" + "s"` → `"aspect categorys"`) — matches the original English prompt's identical behaviour, not a regression.
8. **BM25 tokenization has no Turkish stemming** — plain `\b\w+\b` regex. Not a Phase 1 task, but relevant for retrieval quality.
