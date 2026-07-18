# AnnoABSA Configuration Guide

<!-- GSD: configuration v1 -->

## Overview

AnnoABSA is a Turkish ABSA (Aspect-Based Sentiment Analysis) web annotation tool. Configuration flows through four layers, applied in order of precedence:

1. **CLI arguments** (highest priority — override everything)
2. **JSON config file** (loaded via `--load-config`)
3. **`PATCH /settings` API** (runtime updates from Settings UI)
4. **Environment variables** (read once at startup)

The backend reads `ABSA_DATA_PATH` and `ABSA_CONFIG_PATH` env vars set by the CLI runner (`cli/runner.py`). Configuration is stored in `app/config.py` as `CONFIG_DATA` and managed via the `ABSAAnnotatorConfig` class in `cli/config.py`.

---

## Table of Contents

- [Quick Start](#quick-start)
- [Configuration Sources](#configuration-sources)
- [CLI Reference](#cli-reference)
  - [Data & Session](#data--session)
  - [Annotation](#annotation)
  - [AI / LLM](#ai--llm)
  - [Live Compare Mode](#live-compare-mode)
  - [CSV Comparison](#csv-comparison)
  - [Server & Network](#server--network)
  - [Config File Management](#config-file-management)
- [Environment Variables](#environment-variables)
- [JSON Config File](#json-config-file)
- [Settings API](#settings-api)
- [Settings Panel UI](#settings-panel-ui)
- [Prompt Templates](#prompt-templates)
- [LLM Providers](#llm-providers)
- [Common Configuration Examples](#common-configuration-examples)

---

## Quick Start

```bash
# Basic — start with default settings
annoabsa my_data.csv

# Load a saved config
annoabsa my_data.csv --load-config my_config.json

# Custom ports
annoabsa my_data.csv --backend-port 8080 --frontend-port 5173

# Only backend (no frontend)
annoabsa my_data.csv --backend
```

---

## Configuration Sources

| Source | Mechanism | Persisted? | Priority |
|--------|-----------|------------|----------|
| CLI arguments | `argparse` in `cli/__init__.py` | No | Highest (overrides all others) |
| JSON config file | `--load-config <path>` / `--save-config` | Yes (to disk) | Middle (overridden by CLI) |
| Environment vars | `ABSA_DATA_PATH`, `ABSA_CONFIG_PATH` | No | Read once at backend startup |
| Settings API | `PATCH /settings` | Yes (to `ABSA_CONFIG_PATH` file) | Runtime |

---

## CLI Reference

### Data & Session

| Argument | Type | Default | Config Key | Description |
|----------|------|---------|------------|-------------|
| `data_path` (positional) | path | *required* | `csv_path` | CSV or JSON file to annotate |
| `--session-id` | string | `None` | `session_id` | Identifies this annotation session |
| `--format std` | flag | — | — | Convert two-column STD format (`review,triplet`) to internal format |
| `--export-std OUTPUT_PATH` | path | — | — | Export annotated data to STD format CSV, then exit |

### Annotation

| Argument | Type | Default | Config Key | Description |
|----------|------|---------|------------|-------------|
| `--elements` | list | all four | `sentiment_elements` | Elements to annotate: `aspect_term`, `aspect_category`, `sentiment_polarity`, `opinion_term` |
| `--polarities` | list | `positive negative neutral` | `sentiment_polarity_options` | Available sentiment polarities |
| `--categories` | list | 13 restaurant categories | `aspect_categories` | Available aspect categories |
| `--implicit-aspect` | flag | `true` | `implicit_aspect_term_allowed` | Allow implicit aspect terms |
| `--disable-implicit-aspect` | flag | — | — | Disable implicit aspect terms (overrides `--implicit-aspect`) |
| `--implicit-opinion` | flag | — | `implicit_opinion_term_allowed` | Allow implicit opinion terms |
| `--disable_implicit_opinion` | flag | `true` | — | Disable implicit opinion terms (default) |
| `--disable_clean_phrases` | flag | — | `auto_clean_phrases` | Disable auto-cleaning of punctuation from selected phrases |
| `--disable-save-positions` | flag | — | `save_phrase_positions` | Disable saving of phrase start/end character positions |
| `--disable-click-on-token` | flag | — | `click_on_token` | Disable token-boundary snapping (free character selection) |
| `--auto-positions` | flag | — | `auto_positions` | Auto-fill missing position data for existing phrases on startup |
| `--store-time` | flag | — | `store_time` | Store per-annotation timing data (duration + change status) |
| `--display-avg-annotation-time` | flag | — | `display_avg_annotation_time` | Display average annotation time |
| `--annotation-guidelines PDF_PATH` | path | — | `annotation_guideline` | PDF with annotation guidelines (base64-encoded in config) |

### AI / LLM

| Argument | Type | Default | Config Key | Description |
|----------|------|---------|------------|-------------|
| `--llm-provider` | choice | auto-derived | `llm_provider` | `openai`, `ollama`, `anthropic`, `vllm` |
| `--llm-model` | string | `gemma3:4b` | `llm_model` | Model name for AI predictions |
| `--openai-key` | string | `None` | `openai_key` | OpenAI API key |
| `--anthropic-key` | string | `None` | `anthropic_key` | Anthropic API key |
| `--vllm-url` | string | `None` | `vllm_url` | vLLM server base URL (e.g. `http://localhost:8001/v1`) |
| `--vllm-model` | string | `None` | `vllm_model` | vLLM model name (falls back to `--llm-model`) |
| `--n-few-shot` | int | `10` | `n_few_shot` | Max few-shot examples in LLM prompts (min: 0) |
| `--ai-suggestions` | flag | — | `enable_pre_prediction` | Enable AI pre-prediction feature |
| `--disable-ai-automatic-prediction` | flag | — | `disable_ai_automatic_prediction` | Disable automatic AI predictions (manual button still works) |

**Provider auto-detection:** If `--llm-provider` is not specified, the CLI derives it from which API keys/URLs are configured. If exactly one provider's credentials are set, it's used. If multiple are set, the CLI errors and asks you to pick one explicitly. If none are set, `ollama` is the fallback.

**Provider requirements:**

| Provider | Required Keys |
|----------|--------------|
| `ollama` | None (local, no validation) |
| `openai` | `openai_key` |
| `anthropic` | `anthropic_key` |
| `vllm` | `vllm_url` |
| `custom_openai` | `custom_openai_url` + `custom_openai_key` |

### Live Compare Mode (Phase 4)

Live Compare sends the same review to two models simultaneously and shows both predictions side-by-side. Each model has independent provider, model, temperature, and prompt configuration.

| Argument | Type | Default | Config Key | Description |
|----------|------|---------|------------|-------------|
| `--model-a-provider` | choice | `None` | `model_a_provider` | Provider for Model A: `openai`, `ollama`, `anthropic`, `vllm`, `custom_openai` |
| `--model-a-model` | string | `None` | `model_a_model` | Model name for Model A |
| `--model-a-temperature` | float | `0.7` | `model_a_temperature` | Temperature for Model A |
| `--model-a-prompt` | string | `None` | `model_a_prompt` | Custom prompt template for Model A |
| `--model-b-provider` | choice | `None` | `model_b_provider` | Provider for Model B |
| `--model-b-model` | string | `None` | `model_b_model` | Model name for Model B |
| `--model-b-temperature` | float | `0.7` | `model_b_temperature` | Temperature for Model B |
| `--model-b-prompt` | string | `None` | `model_b_prompt` | Custom prompt template for Model B |
| `--helper-agent-provider` | choice | `None` | `helper_agent_provider` | Provider for the Helper Agent |
| `--helper-agent-model` | string | `None` | `helper_agent_model` | Model name for the Helper Agent |
| `--helper-agent-temperature` | float | `0.7` | `helper_agent_temperature` | Temperature for the Helper Agent |
| `--helper-agent-prompt` | string | `None` | `helper_agent_prompt` | Custom prompt template for the Helper Agent |

**Compare mode** (`compare_mode`) has three values:
- `csv`: Compare against pre-computed CSV files
- `live`: Run both models live against the current review
- `4way`: Ground truth + Gemini + Qwen + GPT (4-column comparison)

### CSV Comparison

| Argument | Type | Default | Config Key | Description |
|----------|------|---------|------------|-------------|
| `--compare-model-a-csv` | path | `None` | `compare_model_a_csv` | CSV file with Model A's predictions |
| `--compare-model-a-name` | string | `Model A` | `compare_model_a_name` | Display name for Model A |
| `--compare-model-b-csv` | path | `None` | `compare_model_b_csv` | CSV file with Model B's predictions |
| `--compare-model-b-name` | string | `Model B` | `compare_model_b_name` | Display name for Model B |

### Server & Network

| Argument | Type | Default | Description |
|----------|------|---------|-------------|
| `--backend` | flag | — | Start only the FastAPI backend (skip frontend) |
| `--backend-port` | int | `8000` | Backend server port |
| `--backend-ip` | string | `localhost` | Backend server bind address |
| `--frontend-port` | int | `3000` | Frontend dev server port |
| `--frontend-ip` | string | `localhost` | Frontend dev server bind address |

The frontend communicates with the backend via `VITE_BACKEND_URL`, set automatically by the runner to `http://{backend_host}:{backend_port}`.

### Config File Management

| Argument | Type | Default | Description |
|----------|------|---------|-------------|
| `--save-config [PATH]` | path | `absa_config.json` | Save current configuration to a JSON file |
| `--load-config PATH` | path | — | Load configuration from a JSON file |
| `--show-config` | flag | — | Print the current configuration to stdout |

---

## Environment Variables

Set by the CLI runner (`cli/runner.py`) before launching the backend:

| Variable | Set By | Purpose |
|----------|--------|---------|
| `ABSA_DATA_PATH` | `start_backend()` | Path to the data file (CSV or JSON) |
| `ABSA_CONFIG_PATH` | `start_backend()` | Path to the temp config JSON file |

These are read once at module load time in `app/config.py`. The temp config file is written to `temp/temp_absa_config.json` then read by the backend process.

---

## JSON Config File

Saved/loaded via `--save-config` / `--load-config`. Format:

```json
{
  "csv_path": "my_data.csv",
  "session_id": "study_2024",
  "sentiment_elements": ["aspect_term", "aspect_category", "sentiment_polarity", "opinion_term"],
  "sentiment_polarity_options": ["positive", "negative", "neutral"],
  "aspect_categories": ["location general", "food quality", "..."],
  "implicit_aspect_term_allowed": true,
  "implicit_opinion_term_allowed": false,
  "auto_clean_phrases": true,
  "save_phrase_positions": true,
  "click_on_token": true,
  "auto_positions": false,
  "store_time": false,
  "display_avg_annotation_time": false,
  "enable_pre_prediction": false,
  "disable_ai_automatic_prediction": false,
  "enable_helper_agent": true,
  "annotation_guideline": null,
  "n_few_shot": 10,
  "llm_provider": "ollama",
  "llm_model": "gemma3:4b",
  "openai_key": null,
  "anthropic_key": null,
  "vllm_url": null,
  "vllm_model": null,
  "compare_model_a_csv": null,
  "compare_model_a_name": null,
  "compare_model_b_csv": null,
  "compare_model_b_name": null,
  "compare_mode": "csv",
  "model_a_provider": null,
  "model_a_model": null,
  "model_a_prompt": null,
  "model_a_temperature": 0.7,
  "model_b_provider": null,
  "model_b_model": null,
  "model_b_prompt": null,
  "model_b_temperature": 0.7,
  "helper_agent_provider": null,
  "helper_agent_model": null,
  "helper_agent_prompt": null,
  "helper_agent_temperature": 0.7,
  "ai_shortcut_key": "a",
  "arrow_key_navigation": true,
  "theme": "dark",
  "custom_openai_url": null,
  "custom_openai_key": null,
  "custom_openai_model": null,
  "labeling_prompt_template": "<default Turkish template>",
  "helper_agent_prompt_template": "<default Turkish template>"
}
```

See `examples/example_config.json` for a minimal example.

---

## Settings API

### `GET /settings`

Returns the full configuration + metadata. Called by the frontend on every page load.

Response includes: all config keys, `current_index`, `max_number_of_idxs`, `total_count`, `session_id`.

### `PATCH /settings`

Accepts a JSON body with one or more config key-value pairs. Changes are applied in-memory immediately and persisted to the `ABSA_CONFIG_PATH` file.

```bash
curl -X PATCH http://localhost:8000/settings \
  -H "Content-Type: application/json" \
  -d '{"llm_provider": "openai", "openai_key": "sk-...", "llm_model": "gpt-4o"}'
```

**Important notes:**
- `PATCH /settings` does NOT re-instantiate LLM provider adapters after changes. To apply new provider config, restart the backend or trigger a new prediction request which instantiates the provider on-demand.
- Empty-string values (`""`) in `openai_key`, `anthropic_key`, `vllm_url`, `vllm_model`, comparison names, and all Phase 4 model config fields are converted to `null` by the SettingsPanel.
- `aspect_categories` in the settings form is a comma-separated string; the SettingsPanel splits it into an array before submitting.
- `n_few_shot` from the form may arrive as a string; the SettingsPanel coerces it to `int`.

---

## Settings Panel UI

The frontend Settings panel (`frontend/src/components/SettingsPanel.tsx`) has 8 sections:

| Section | Title (Turkish) | Config Keys |
|---------|-----------------|-------------|
| 0 | Görünüm (Appearance) | `theme` |
| Compare | Karşılaştırma Modu (Compare Mode) | `compare_mode` (`csv` / `live`) |
| 1 | Ek Açıklama (Annotation) | `sentiment_elements`, `sentiment_polarity_options`, `aspect_categories`, `implicit_aspect_term_allowed`, `implicit_opinion_term_allowed`, `click_on_token`, `save_phrase_positions`, `auto_clean_phrases`, `arrow_key_navigation` |
| 2 | Yapay Zeka / Dil Modeli (AI / LLM) | `enable_pre_prediction`, `disable_ai_automatic_prediction`, `enable_helper_agent`, `ai_shortcut_key`, `llm_provider`, `llm_model`, `vllm_model`, `openai_key`, `anthropic_key`, `vllm_url`, `custom_openai_url`, `custom_openai_key`, `custom_openai_model`, `n_few_shot` |
| 3a | Model A (Canlı) | `model_a_provider`, `model_a_model`, `model_a_temperature`, `model_a_prompt` |
| 3b | Model B (Canlı) | `model_b_provider`, `model_b_model`, `model_b_temperature`, `model_b_prompt` |
| 3c | Yardımcı Asistan (Canlı) | `helper_agent_provider`, `helper_agent_model`, `helper_agent_temperature`, `helper_agent_prompt` |
| 4 | Veri (Data) | `compare_model_a_name`, `compare_model_b_name` |
| 5 | Araçlar (Tools) | Position re-scan button**\*** |

**\*Section 5 (Tools):** Contains a "Pozisyonları Yeniden Tara" (Rescan Positions) button that calls `onRescanPositions()` to recompute phrase character positions.

### Available Themes

| Value | Label |
|-------|-------|
| `light` | Açık |
| `dark` | Koyu |
| `coffee` | Kahve |
| `forest` | Orman |
| `cupcake` | Pastel |
| `aqua` | Su |
| `lemonade` | Limonata |

Themes are DaisyUI themes (`daisyui` ^4.12.24, Tailwind CSS ^3.4.17).

---

## Prompt Templates

AnnoABSA uses two Turkish-language prompt templates defined in `services/prediction.py`:

### `DEFAULT_LABELING_TEMPLATE`

Used for ABSA triplet extraction. Contains placeholder variables:
- `{implicit_aspect_note}` — whether implicit aspect terms are allowed
- `{implicit_opinion_note}` — whether implicit opinion terms are allowed
- `{aspect_categories}` — the configured category list
- `{polarities}` — the configured polarity list
- `{element_names}` / `{element_keys}` — the sentiment elements to extract

This template can be overridden per-model via `model_a_prompt`, `model_b_prompt`, or the global `labeling_prompt_template` config key.

### `DEFAULT_CHAT_TEMPLATE`

Used for the Helper Agent. Contains placeholder variables:
- `{review_text}` — the current review being discussed
- `{model_a_name}`, `{model_a_triplets}` — Model A's predictions
- `{model_b_name}`, `{model_b_triplets}` — Model B's predictions
- `{few_shot_examples}` — similar labeled examples

The template also defines the available actions the agent can invoke via `[[action:methodName(args)]]` syntax.

---

## LLM Providers

AnnoABSA supports five LLM providers, each with its own adapter class in `services/llm_providers.py`:

| Provider | Adapter Class | API | Structured Output |
|----------|--------------|-----|-------------------|
| `ollama` | `OllamaProvider` | `ollama` Python lib | Yes (Pydantic `format`) |
| `openai` | `OpenAIProvider` | `openai` Python lib | Yes (`beta.chat.completions.parse`) |
| `anthropic` | `AnthropicProvider` | `anthropic` Python lib | No (manual JSON parse) |
| `vllm` | `VLLMProvider` | OpenAPI-compatible | No (manual JSON parse) |
| `custom_openai` | `CustomOpenAIProvider` | OpenAPI-compatible | Yes (tries beta.parse, falls back to manual JSON) |

All providers implement the `LLMProviderPort` protocol with `predict()` and `chat()` methods. The `custom_openai` provider connects to any OpenAI-compatible endpoint (e.g., DeepSeek, Together AI, Groq) by setting a custom base URL and API key.

### Provider Dispatch

The `get_provider()` factory in `services/llm_providers.py` instantiates the correct adapter. Provider validation (`validate_provider_config`) checks that required credentials are present before use.

---

## Common Configuration Examples

### Example 1: Ollama (Local)

```bash
annoabsa reviews.csv --llm-provider ollama --llm-model gemma3:4b --n-few-shot 5
```

### Example 2: OpenAI

```bash
annoabsa reviews.csv \
  --llm-provider openai \
  --openai-key "sk-..." \
  --llm-model "gpt-4o-2024-08-06" \
  --n-few-shot 10
```

### Example 3: Anthropic (Claude)

```bash
annoabsa reviews.csv \
  --llm-provider anthropic \
  --anthropic-key "sk-ant-..." \
  --llm-model "claude-sonnet-4-20250514"
```

### Example 4: vLLM (Self-Hosted)

```bash
annoabsa reviews.csv \
  --llm-provider vllm \
  --vllm-url "http://gpu-server:8001/v1" \
  --vllm-model "meta-llama/Llama-3-70B"
```

### Example 5: Custom OpenAI-Compatible (DeepSeek)

```bash
# Custom OpenAI is configured via the Settings UI (Section 2) or config file, not CLI.
# In the Settings UI:
#   - Custom OpenAI URL: https://api.deepseek.com
#   - Custom OpenAI Key: sk-...
#   - Custom OpenAI Model: deepseek-v4-flash
# Then set llm_provider to custom_openai.
```

### Example 6: Live Compare Mode

```bash
annoabsa reviews.csv \
  --model-a-provider openai --model-a-model "gpt-4o" --model-a-temperature 0.5 \
  --model-b-provider anthropic --model-b-model "claude-sonnet-4-20250514" --model-b-temperature 0.7 \
  --helper-agent-provider ollama --helper-agent-model "gemma3:4b"
```

### Example 7: Custom Annotation Schema

```bash
annoabsa reviews.csv \
  --elements aspect_term sentiment_polarity \
  --polarities positive negative \
  --categories "food quality" "service general" "ambience general"
```

### Example 8: Session with Config File

```bash
# Step 1: Save config
annoabsa reviews.csv \
  --session-id "experiment_2024_round1" \
  --elements aspect_term aspect_category sentiment_polarity opinion_term \
  --save-config experiment_config.json

# Step 2: Reload later
annoabsa reviews.csv \
  --load-config experiment_config.json \
  --session-id "experiment_2024_round2"
```

### Example 9: STD Format Import

```bash
# Convert two-column STD format (review, triplet) to AnnoABSA internal format
annoabsa std_data.csv --format std
```

### Example 10: Export to STD Format

```bash
# Export annotated data to STD format, then exit
annoabsa annotated_data.csv --export-std exported_std.csv
```

### Example 11: Custom Ports & Remote Access

```bash
annoabsa reviews.csv \
  --backend-port 8080 \
  --backend-ip 0.0.0.0 \
  --frontend-port 5173
```

---

## Python Dependencies

AnnoABSA backend (from `pyproject.toml`):

```
fastapi, uvicorn, pandas, rank-bm25, openai, ollama, anthropic,
python-multipart, scikit-learn, sentence-transformers, transformers, torch,
nlptoolkit-sentinet, nlptoolkit-wordnet, nlptoolkit-dictionary,
nlptoolkit-morphologicalanalysis, setuptools<75, pytest<10
```

Python requirement: `>=3.11`

## Frontend Dependencies

AnnoABSA frontend (from `frontend/package.json`):

```
react ^19.1.1, react-dom ^19.1.1, @phosphor-icons/react ^2.1.10,
daisyui ^4.12.24, tailwindcss ^3.4.17, vite ^5.4.19,
typescript ^5.9.2, vitest ^4.1.10
```

---

## Default Aspect Categories

The 13 default restaurant-domain categories:

```
location general, food prices, food quality, food general,
ambience general, service general, restaurant prices,
drinks prices, restaurant miscellaneous, drinks quality,
drinks style_options, restaurant general, food style_options
```

Override with `--categories` or the Settings UI.

## Default Sentiment Elements

```
aspect_term, aspect_category, sentiment_polarity, opinion_term
```

Override with `--elements` or the Settings UI.

## Default Sentiment Polarities

```
positive, negative, neutral
```

Override with `--polarities` or the Settings UI.
