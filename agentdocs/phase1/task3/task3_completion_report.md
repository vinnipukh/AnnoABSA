# Phase 1, Task 3 — Completion Report

**Task:** New Helper Agent Providers (Anthropic & vLLM) + Provider Port/Adapter Refactor  
**Date:** 2026-07-02  
**Status:** ✅ Complete — 43/43 verification tests passed

---

## Summary

The AI prediction pipeline was hardcoded to two providers (OpenAI if a key was present, otherwise Ollama) with an implicit priority check. This task refactored the entire pipeline behind a **port/adapter pattern** with a dictionary-based dispatch — all 4 providers (Ollama, OpenAI, Anthropic, vLLM) are now first-class citizens selected via an explicit `--llm-provider` flag. The old `predict_llm` and `predict_openai` functions are retained as backward-compatible wrappers for `eval.py`.

**Bonus fix:** `--llm-model` was parsed by argparse but never stored in `ABSAAnnotatorConfig`, so it never reached the backend. This is now fixed — model names propagate correctly.

---

## Changes by file

### `cli.py` — Config fields, setters, CLI flags, wiring, validation

- **Config defaults** (5 new keys): `llm_provider: None`, `llm_model: "gemma3:4b"`, `anthropic_key: None`, `vllm_url: None`, `vllm_model: None` in `ABSAAnnotatorConfig.__init__`
- **Setter methods:** `set_llm_provider()` (case-insensitive, normalized to lowercase), `set_llm_model()`, `set_anthropic_key()`, `set_vllm_url()`, `set_vllm_model()`
- **Argparse flags:**
  - `--llm-provider {openai,ollama,anthropic,vllm}` — explicit provider selection
  - `--anthropic-key <API_KEY>` — Anthropic API key
  - `--vllm-url <URL>` — vLLM server base URL (e.g., `http://localhost:8001/v1`)
  - `--vllm-model <MODEL>` — vLLM model name (defaults to `--llm-model` value)
- **Provider derivation:** If `--llm-provider` is omitted, it auto-derives: `openai` if `--openai-key` is set, else `ollama` (backward compatible)
- **CLI startup validation** (fails fast with `sys.exit(1)`):
  - Provider `openai` without `--openai-key` → error
  - Provider `anthropic` without `--anthropic-key` → error
  - Provider `vllm` without `--vllm-url` → error
- **`print_config()`:** Shows `LLM Provider: {name} (model: {model})` with key/URL status line
- **Bug fix:** `--llm-model` now stored in `ABSAAnnotatorConfig.llm_model` so it propagates to the backend via the temp config file

### `main.py` — Shared helpers, 4 adapter classes, registry, dispatch

**Shared infrastructure:**
- **`build_prediction_prompt()`** (new): Extracted the prompt-building logic (instructions + few-shot examples) that was duplicated verbatim across `predict_llm` and `predict_openai`. Returns `(prompt_str, few_shot_examples)`. Called by all provider adapters.
- **`build_absa_models()`** (new): Extracted the dynamic Pydantic model / Enum construction (AspectEnum, PolarityEnum, CategoryEnum, OpinionEnum + Aspects model). Returns `(Aspects_model, field_types, enums_dict)`. Called by all provider adapters.

**4 provider adapter classes:**
| Class | `predict()` | `chat()` |
|---|---|---|
| `OllamaProvider` | Wraps `ollama.generate` with structured JSON schema | Wraps `ollama.chat()` |
| `OpenAIProvider` | Wraps `openai` beta structured output (`completions.parse`) | Wraps `openai` chat completions |
| `AnthropicProvider` | Uses `anthropic.messages.create`, parses JSON from response text | Converts OpenAI-format messages to Anthropic format (system → `system` param, user/assistant → `messages`) |
| `VLLMProvider` | Uses `OpenAI(base_url=..., api_key="EMPTY")` with standard completion + manual JSON parse (vLLM doesn't support `beta.chat.completions.parse`) | Same OpenAI-compatible chat pattern |

- **`PROVIDER_REGISTRY`** dict: `{"ollama": OllamaProvider, "openai": OpenAIProvider, "anthropic": AnthropicProvider, "vllm": VLLMProvider}`
- **`get_provider(provider_name, config)`** factory: Looks up the registry, instantiates the adapter with the config dict. Raises `ValueError` for unknown providers.
- **`predict_llm()` / `predict_openai()`:** Refactored to thin wrappers calling the shared helpers, preserving their original signatures and return types for `eval.py` backward compat (~170 lines of duplicated code removed).

**Refactored endpoints:**
- **`get_ai_prediction()`:** Replaced the `if openai_key: predict_openai else: predict_llm` branch with:
  1. Read `llm_provider` from `CONFIG_DATA`
  2. Backward-compat derivation if not explicitly set
  3. Provider-config validation (400 HTTP error with explanation)
  4. `provider = get_provider(name, CONFIG_DATA)`
  5. `provider.predict(...)` call
- **`agent_chat()`:** Replaced the `if openai_key: ... else: hardcoded` branch with provider dispatch. Falls back to the original rule-based Turkish responses if the provider call fails.
- **`load_config()` defaults:** Added `llm_provider: "ollama"`, `llm_model: "gemma3:4b"`, `openai_key: None`, `anthropic_key: None`, `vllm_url: None`, `vllm_model: None`

### `requirements.txt`

- Added `anthropic` dependency

---

## Verification (43/43 tests passed)

| Area | Checks | Result |
|---|---|---|
| **CLI config keys** — all 5 new keys present with correct defaults | 5 | ✓ |
| **Setters + case-insensitivity** — ANTHROPIC→anthropic, OpenAI→openai, invalid→ValueError | 7 | ✓ |
| **Provider derivation** — openai_key → openai, no key → ollama | 2 | ✓ |
| **Symbol importability** — all main symbols importable cleanly | 1 | ✓ |
| **PROVIDER_REGISTRY** — 4 entries, all names present | 5 | ✓ |
| **get_provider factory** — returns correct class for each name, unknown→ValueError | 5 | ✓ |
| **build_prediction_prompt** — valid prompt, includes few-shot examples | 4 | ✓ |
| **build_absa_models** — valid Pydantic model with JSON schema | 2 | ✓ |
| **load_config defaults** — all 5 new keys present | 5 | ✓ |
| **Provider methods** — .predict() and .chat() callable on all 4 adapters | 8 | ✓ |

---

## Usage

```bash
# Default: Ollama (backward compatible)
annoabsa data.csv --ai-suggestions

# Explicit Ollama with custom model
annoabsa data.csv --ai-suggestions --llm-provider ollama --llm-model gemma3:12b

# OpenAI with explicit provider flag
annoabsa data.csv --ai-suggestions --llm-provider openai --openai-key sk-... --llm-model gpt-4o

# Anthropic (new)
annoabsa data.csv --ai-suggestions --llm-provider anthropic --anthropic-key sk-ant-... --llm-model claude-sonnet-4-20250514

# vLLM (new)
annoabsa data.csv --ai-suggestions --llm-provider vllm --vllm-url http://localhost:8001/v1 --llm-model my-model

# Via JSON config file:
annoabsa data.csv --load-config my_config.json
```

Where `my_config.json`:
```json
{
  "llm_provider": "anthropic",
  "llm_model": "claude-sonnet-4-20250514",
  "anthropic_key": "sk-ant-..."
}
```

---

## Design decisions

1. **Dictionary dispatch (not Factory pattern):** A simple `PROVIDER_REGISTRY` dict mapping provider name → class, with a thin `get_provider()` factory function. Adding a 5th provider means writing one adapter class and adding one entry to the dict — no new files, no registry mutations, no dependency injection framework.

2. **Shared prompt & model construction:** The prompt text and Pydantic model building were duplicated verbatim between `predict_llm` and `predict_openai` (~170 lines). Extracting them into `build_prediction_prompt()` and `build_absa_models()` eliminates that duplication and ensures all providers get identical instructions.

3. **vLLM uses raw `completions.create` (not `beta.completions.parse`):** vLLM's OpenAI-compatible endpoint doesn't support the `response_format` parameter for structured output. Using standard completion + `json.loads()` with a fallback to empty results is more robust and avoids silent failures.

4. **Anthropic message format conversion:** The `chat()` method converts OpenAI-style `system`/`user`/`assistant` messages to Anthropic's `system` param + `messages` array format. This keeps the calling code (`agent_chat`) provider-agnostic.

5. **Backward-compat wrappers:** `predict_llm()` and `predict_openai()` remain as thin wrappers calling the shared helpers, preserving their exact signatures and return types. This ensures `eval.py` (which imports `predict_llm`) continues to work without changes.

6. **Both CLI and endpoint validation:** Missing keys/URLs are caught at CLI startup (before spawning the backend) AND in the API endpoints (returning HTTP 400). The CLI check prevents confusing startup scenarios; the endpoint check protects against misconfigured config files.

---

## Known caveats

- The `anthropic` SDK must be installed (`pip install anthropic` or via `requirements.txt`) — it's a new dependency
- vLLM requires a running vLLM server; the tool doesn't manage that lifecycle
- `agent_chat`'s prompt content (Turkish system message, model comparison framing) is unchanged — Task 4 handles prompt cleanup
- `architecture_map.md` and kickoff docs still reference the old implicit-priority dispatch — these are documentation describing the pre-task state
