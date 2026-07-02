# Phase 1, Task 4 — Completion Report

**Task:** Helper Agent Prompt Improvements (Turkish, configurable, consolidated)  
**Date:** 2026-07-02  
**Status:** ✅ Complete — 8/8 verification groups passed

---

## Summary

The ABSA labeling prompt and the helper agent chat prompt were both hardcoded as Python string literals — the labeling prompt in English inside `build_prediction_prompt()`, and the chat prompt as a Turkish f-string inside `agent_chat()`. This task made both prompts **user-configurable** via the existing JSON config system, shipped Turkish-language **defaults** for both, and consolidated the labeling prompt construction so it's driven entirely by a template rather than inline conditionals.

**Key result:** Users can now edit `labeling_prompt_template` and `helper_agent_prompt_template` in their config JSON to change the instruction text the LLM receives — no code changes needed. The shipped defaults are Turkish-language instruction prose while preserving English `aspect_category`/`sentiment_polarity` values, as required.

---

## Changes by file

### `main.py` — Template constants, refactored prompt builder, provider wiring

**Template constants (2 new module-level strings):**
- `DEFAULT_LABELING_TEMPLATE` — Full Turkish labeling prompt with 6 placeholders:
  - `{implicit_aspect_note}` — "Görünüş terimi örtük (implicit) ise 'NULL' olabilir." or empty
  - `{implicit_opinion_note}` — "Görüş terimi örtük (implicit) ise 'NULL' olabilir." or empty
  - `{aspect_categories}` — comma-joined list of categories (English values, untranslated)
  - `{polarities}` — comma-joined list of polarity options (English values, untranslated)
  - `{element_names}` — e.g. "aspect terms, opinion terms" (derived from config)
  - `{element_keys}` — e.g. "'aspect term', 'opinion term'" (derived from config)
- `DEFAULT_CHAT_TEMPLATE` — Turkish helper agent prompt with 5 placeholders:
  - `{review_text}`, `{model_a_name}`, `{model_a_triplets}`, `{model_b_name}`, `{model_b_triplets}`

**`load_config()`:** Added `labeling_prompt_template` and `helper_agent_prompt_template` to the defaults dict, referencing the constants above.

**`build_prediction_prompt()`:** Added `prompt_template=None` parameter.
- **Template path** (when `prompt_template` is provided): uses `.format()` with computed values for all 6 placeholders. Implicit notes are empty strings when disabled (no double-spaces or stray punctuation — verified).
- **Fallback path** (when `prompt_template` is `None`): original hardcoded English prompt preserved for backward compatibility (used by `eval.py`'s direct imports of `predict_llm`).
- Few-shot examples block and `Text: ...\nSentiment elements:` suffix remain structurally identical.

**Provider adapter threading:** Added `prompt_template=None` parameter to all 4 provider `predict()` methods (`OllamaProvider`, `OpenAIProvider`, `AnthropicProvider`, `VLLMProvider`) and both backward-compat wrappers (`predict_llm`, `predict_openai`). Each passes it through to `build_prediction_prompt()`.

**`get_ai_prediction()`:** Reads `labeling_prompt_template` from `CONFIG_DATA` (with `DEFAULT_LABELING_TEMPLATE` fallback) and passes it as `prompt_template=` to `provider.predict()`.

**`agent_chat()`:** Replaced the hardcoded f-string system message with:
```python
chat_template = CONFIG_DATA.get('helper_agent_prompt_template', DEFAULT_CHAT_TEMPLATE)
system_content = chat_template.format(
    review_text=..., model_a_name=..., model_a_triplets=...,
    model_b_name=..., model_b_triplets=...,
)
```
The model names (`model_a_name`/`model_b_name`) were already generic from Task 2 — no DeepSeek/Qwen strings remain.

### `cli.py` — Config defaults

- Added `CLI_DEFAULT_LABELING_TEMPLATE` and `CLI_DEFAULT_CHAT_TEMPLATE` as module-level constants (mirrored from `main.py` to avoid import-time side effects from `main.py`'s FastAPI app creation).
- Added both keys to `ABSAAnnotatorConfig.__init__()` config defaults.

---

## Verification (8/8 groups passed)

| # | Check | Result |
|---|-------|--------|
| 1 | `load_config()` has both template keys with Turkish text | ✓ |
| 2 | CLI `ABSAAnnotatorConfig` has both keys | ✓ |
| 3 | Template preserves English category/polarity values (not translated) | ✓ |
| 4 | `build_prediction_prompt(template=...)` produces Turkish text with correct category/polarity/placeholder substitution, no double-spaces from empty implicit notes | ✓ |
| 5 | Implicit notes appear when `allow_implicit_aspect_terms=True`, absent when `False` | ✓ |
| 6 | `prompt_template=None` still produces English prompt (backward compat) | ✓ |
| 7 | Chat template formats correctly with all dynamic values | ✓ |
| 8 | CLI template constants match `main.py` constants (no drift) | ✓ |

---

## Usage

The templates ship as defaults — no user action needed. To customize:

```json
{
  "labeling_prompt_template": "Aşağıdaki duygu unsuru tanımlarına göre:\n...",
  "helper_agent_prompt_template": "Sen ABSA veri etiketleme asistanısın..."
}
```

The templates support standard Python `.format()` placeholders:

**Labeling template placeholders:**
| Placeholder | Description |
|---|---|
| `{implicit_aspect_note}` | "Görünüş terimi örtük (implicit) ise 'NULL' olabilir." or empty |
| `{implicit_opinion_note}` | "Görüş terimi örtük (implicit) ise 'NULL' olabilir." or empty |
| `{aspect_categories}` | Comma-joined category list (English values) |
| `{polarities}` | Comma-joined polarity list (English values) |
| `{element_names}` | Plural display names from `considered_sentiment_elements` |
| `{element_keys}` | Quoted key names from `considered_sentiment_elements` |

**Chat template placeholders:**
| Placeholder | Description |
|---|---|
| `{review_text}` | The review text being annotated |
| `{model_a_name}` | Configurable display name for Model A |
| `{model_a_triplets}` | Model A's triplet list |
| `{model_b_name}` | Configurable display name for Model B |
| `{model_b_triplets}` | Model B's triplet list |

---

## Design decisions

1. **Template as default (not fallback-only):** Rather than making the config key optional with the old English prompt as fallback, the default shipped value IS the new Turkish template. This ensures all users get the improved prompt out of the box. The old English prompt is only preserved in the `prompt_template=None` path used by backward-compat wrappers (`eval.py`).

2. **Empty-string implicit notes (no conditional template branches):** When `allow_implicit_aspect_terms=False`, the `{implicit_aspect_note}` value is `""`. The template has `...öbeğidir. {implicit_aspect_note}` — this renders as `...öbeğidir. ` (period + space before newline). No double-spaces, no stray punctuation. A single template works for both modes without conditional template fragments.

3. **No templating library dependency:** Python's built-in `str.format()` handles the 6-5 placeholders without any additional dependencies. Custom templates with literal braces would need `{{`/`}}` escaping, but this is an unlikely edge case and the standard Python behavior is documented.

4. **Constants duplicated in `cli.py` (not imported from `main.py`):** `main.py` creates a FastAPI app at import time and reads environment variables. Importing it from `cli.py` would trigger these side effects at CLI-parsing time. Mirroring the string constants avoids this without adding a shared module.

5. **Template read from `CONFIG_DATA` at request time:** Both `get_ai_prediction` and `agent_chat` read the template from the module-level `CONFIG_DATA` dict on every request (via `.get(key, DEFAULT)`). This means editing the config file between requests immediately changes the prompt — no server restart needed.

---

## Known caveats

- Custom templates with unmatched `.format()` placeholders will raise a `KeyError` at runtime — this is intentional fail-fast behavior rather than silent corruption
- The `{element_names}` pluralization is naïve (`"aspect_category" + "s"` → `"aspect categorys"` rather than `"aspect categories"`) — this matches the original English prompt's identical behavior and is not a regression
- The default labeling template assumes Turkish text (the agglutinative-language paragraph); users annotating in other languages should provide their own template
- The optional `labeling_prompt_template` and `helper_agent_prompt_template` config keys have no corresponding `--*` CLI flags — they're only settable via `--load-config` JSON; a future task could add inline flags if needed

---

## Notes for future agents

### Template constants are duplicated between `main.py` and `cli.py`

`DEFAULT_LABELING_TEMPLATE` / `DEFAULT_CHAT_TEMPLATE` live in **both** files. This is intentional — `cli.py` cannot import from `main.py` without triggering import-time side effects (FastAPI app creation, environment variable reads). Any future change to the default template text **must update both copies** or the CLI-generated configs will silently use the stale version.

If someone later refactors `main.py` to be safely importable (e.g., deferring `app = FastAPI()` behind a guard), the `CLI_DEFAULT_*` constants in `cli.py` can be replaced with a clean `from main import DEFAULT_LABELING_TEMPLATE`.

### Template read from `CONFIG_DATA`, not `load_config()`

Both `get_ai_prediction()` and `agent_chat()` read the template from the module-level **`CONFIG_DATA`** dict (populated once at import time from `ABSA_CONFIG_PATH`), **not** from the fresh `config = load_config()` call that coexists in the same function. This means:
- Startup-time config file → templates work
- Editing the config file while the server is running → `CONFIG_DATA` is **not** refreshed; templates won't change until restart

This is a pre-existing architectural pattern (not introduced by Task 4) — `CONFIG_DATA` vs `load_config()` are used inconsistently throughout the codebase for different settings. A future cleanup could standardise on one source, but if you do, make sure all consumers (including `/settings` endpoint) agree.

### New providers must thread `prompt_template`

Any future provider adapter class added to `PROVIDER_REGISTRY` **must** accept `prompt_template=None` in its `predict()` signature and pass it through to `build_prediction_prompt()`. The 4 existing providers all do this. Forgetting means the new provider silently gets the `prompt_template=None` fallback (English prompt) instead of the configured Turkish template.

### `predict_llm` / `predict_openai` wrappers bypass the template

These backward-compat functions (imported by `eval.py`) default to `prompt_template=None` — they use the old English prompt unless explicitly given a template. If evaluation should use the Turkish template, `eval.py` must be updated to pass `prompt_template=DEFAULT_LABELING_TEMPLATE` explicitly.
