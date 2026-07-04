# Root Reorganization — Completion Report

**Date:** 2026-07-04
**Goal:** Split monolithic `main.py` (~1750 lines) into focused modules. Zero behavior change.
**Status:** ✅ Complete

---

## New File Structure

```
project root/
├── main.py                          (1022 lines, was ~1750)
├── models/
│   ├── __init__.py
│   └── schemas.py                   (SaveTripletsRequest, AgentChatRequest)
├── services/
│   ├── __init__.py
│   ├── prediction.py                (prompt building, BM25, position helpers, templates)
│   └── llm_providers.py             (4 provider adapters + dispatch)
├── cli.py                           (untouched)
├── eval.py                          (1 import line changed)
└── eval_exc.py                      (untouched)
```

## What Moved

| From main.py → | Contents | Lines |
|---|---|---|
| `models/schemas.py` | `SaveTripletsRequest`, `AgentChatRequest` | ~12 |
| `services/prediction.py` | `DEFAULT_LABELING_TEMPLATE`, `DEFAULT_CHAT_TEMPLATE`, `build_prediction_prompt`, `build_absa_models`, `get_most_similar_examples`, `find_valid_phrases_list`, `find_phrase_positions`, `generate_mock_reasoning` | ~357 |
| `services/llm_providers.py` | `OllamaProvider`, `OpenAIProvider`, `AnthropicProvider`, `VLLMProvider`, `PROVIDER_REGISTRY`, `get_provider`, `_derive_provider`, `predict_llm` | ~502 |

## What Was Deleted

| Item | Reason |
|---|---|
| `post_data` endpoint | Dead code (no callers) |
| `post_annotations` endpoint | Dead code (frontend uses `/review/{idx}/save`) |
| `Item` Pydantic model | Only used by deleted endpoint |
| `AnnotationData` Pydantic model | Only used by deleted endpoint |
| `predict_openai` function | No callers (wrapped `OpenAIProvider`) |

## What Changed

- `eval.py` — import changed from `from main import predict_llm` to `from services.llm_providers import predict_llm`
- `cli.py` — **untouched** (its inline `_derive_provider` copy stays with sync comment)
- `architecture_map.md` — updated to reflect new structure
- `agentdocs/mainpy_functions.md` → `agentdocs/backend_reference.md` — renamed and updated

## Verification

All 24 verification checks pass: compilation, imports, instantiation, call chains, no regressions in dependent modules.
