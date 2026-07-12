# Phase 4 — Live Compare Mode: Per-Model Prompts, Temperature, and Provider Selection

> **Status:** 🟡 Tasks 1–2 complete — see `task1_completion_report.md` and `task2_completion_report.md`
> **Date:** 2026-07-12
> **Scope:** Add a Live Compare mode alongside the existing CSV-based Compare mode, where Model A and Model B each have independently configurable provider, model, prompt, and temperature. The Helper Agent also gets its own config. A mode selector (CSV vs Live) controls which data populates the comparison columns.

---

## Table of Contents

1. [Motivation](#1-motivation)
2. [Architecture Overview](#2-architecture-overview)
3. [Data Model & Config Keys](#3-data-model--config-keys)
4. [Backend Changes](#4-backend-changes)
   - 4.1 Add `temperature` to provider `predict()` interface
   - 4.2 New config defaults in `load_config()`
   - 4.3 Expose new fields in `GET /settings`
   - 4.4 New endpoint: `GET /live_prediction/{data_idx}`
   - 4.5 Modify `agent_chat()` for per-agent config
   - 4.6 Per-model config validation
5. [Frontend Changes](#5-frontend-changes)
   - 5.1 Extend `Settings` interface (`types.ts`)
   - 5.2 Settings Panel: 3 new collapsible sections
   - 5.3 App.tsx: Live mode state & fetching
   - 5.4 ModelTripletColumn: "Run" button
6. [Test Strategy](#6-test-strategy)
7. [Design Decisions & Rationale](#7-design-decisions--rationale)
8. [Extension Guide](#8-extension-guide)

---

## 1. Motivation

The original Compare mode loads pre-computed triplets from CSV files. This is useful for comparing two static model outputs side-by-side, but it doesn't let the user:

- Change the prompt and observe how it affects predictions
- Compare two different models live (e.g., deepseek-v4-flash vs deepseek-v4-pro)
- Adjust temperature per model
- Iterate quickly on prompt engineering without re-running external scripts

Phase 4 adds a **Live Compare mode** where Model A and Model B columns are populated on-demand via LLM API calls, each using their own independent configuration. The Helper Agent also gets independent config.

The two modes (CSV and Live) are mutually exclusive — toggling between them changes what the comparison columns show.

---

## 2. Architecture Overview

```
┌──────────────────────────────────────────────────────────────────┐
│                        Settings Panel                            │
│  ┌─ Compare Mode ────────────────────────────────────────────┐  │
│  │  ○ CSV  ● Live                                            │  │
│  └───────────────────────────────────────────────────────────┘  │
│  ┌─ Model A (Live) ──────────────────────────────────────────┐  │
│  │  Provider: [ollama ▼]  Model: [deepseek-v4-flash]         │  │
│  │  Prompt: [textarea with DEFAULT_LABELING_TEMPLATE]        │  │
│  │  Temperature: [═══════●═══════] 0.7                       │  │
│  └───────────────────────────────────────────────────────────┘  │
│  ┌─ Model B (Live) ──────────────────────────────────────────┐  │
│  │  Provider: [openai ▼]  Model: [deepseek-v4-pro]            │  │
│  │  Prompt: [textarea with DEFAULT_LABELING_TEMPLATE]        │  │
│  │  Temperature: [═══════●═══════] 0.7                       │  │
│  └───────────────────────────────────────────────────────────┘  │
│  ┌─ Helper Agent (Live) ─────────────────────────────────────┐  │
│  │  Provider: [anthropic ▼]  Model: [claude-sonnet-4]         │  │
│  │  Prompt: [textarea with DEFAULT_CHAT_TEMPLATE]            │  │
│  │  Temperature: [═══════●═══════] 0.7                       │  │
│  └───────────────────────────────────────────────────────────┘  │
└──────────────────────────────────────────────────────────────────┘

          │ compare_mode = "live"
          ▼
┌──────────────────────────────────────────────────────────┐
│  App.tsx (Compare mode rendering)                         │
│                                                           │
│  ┌─ Model A Column ───┐  ┌─ Center ──┐  ┌─ Model B ────┐ │
│  │ [▶ Model A'yı      │  │ Review    │  │ [▶ Model B'yi│ │
│  │   Çalıştır]        │  │ text      │  │   Çalıştır]  │ │
│  │                    │  │ Manual    │  │              │ │
│  │ (after click)      │  │ triplets  │  │ (after click)│ │
│  │ triplets appear    │  │           │  │ triplets     │ │
│  └────────────────────┘  └───────────┘  └──────────────┘ │
└──────────────────────────────────────────────────────────┘
          │
          │ onClick "Çalıştır"
          ▼
┌──────────────────────────────────────────────────────────┐
│  GET /live_prediction/{idx}?role=model_a                  │
│  ┌──────────────────────────────────────────────────────┐ │
│  │  1. Read role-specific config from CONFIG_DATA       │ │
│  │  2. Validate per-model provider has required keys    │ │
│  │  3. get_provider(model_a_provider, CONFIG_DATA)      │ │
│  │  4. provider.predict(..., prompt=model_a_prompt,     │ │
│  │                          temperature=model_a_temp)   │ │
│  │  5. Add position data if enabled                     │ │
│  │  6. Return predictions                               │ │
│  └──────────────────────────────────────────────────────┘ │
└──────────────────────────────────────────────────────────┘
```

---

## 3. Data Model & Config Keys

### New config keys (stored in `CONFIG_DATA` and persisted to JSON config file)

| Key | Type | Default | Purpose |
|---|---|---|---|
| `compare_mode` | `"csv" \| "live"` | `"csv"` | Controls which mode the Compare view uses |
| `model_a_provider` | `str \| None` | `None` | Provider for Model A live predictions |
| `model_a_model` | `str \| None` | `None` | Model name for Model A |
| `model_a_prompt` | `str \| None` | `None` → `DEFAULT_LABELING_TEMPLATE` | Labeling prompt for Model A |
| `model_a_temperature` | `float` | `0.7` | Temperature for Model A |
| `model_b_provider` | `str \| None` | `None` | Provider for Model B live predictions |
| `model_b_model` | `str \| None` | `None` | Model name for Model B |
| `model_b_prompt` | `str \| None` | `None` → `DEFAULT_LABELING_TEMPLATE` | Labeling prompt for Model B |
| `model_b_temperature` | `float` | `0.7` | Temperature for Model B |
| `helper_agent_provider` | `str \| None` | `None` | Provider for Helper Agent |
| `helper_agent_model` | `str \| None` | `None` | Model name for Helper Agent |
| `helper_agent_prompt` | `str \| None` | `None` → `DEFAULT_CHAT_TEMPLATE` | Chat prompt for Helper Agent |
| `helper_agent_temperature` | `float` | `0.7` | Temperature for Helper Agent |

### Frontend `Settings` type additions

```typescript
// In frontend/src/types.ts, add to Settings interface:
compare_mode: 'csv' | 'live';
model_a_provider: string | null;
model_a_model: string | null;
model_a_prompt: string | null;
model_a_temperature: number;
model_b_provider: string | null;
model_b_model: string | null;
model_b_prompt: string | null;
model_b_temperature: number;
helper_agent_provider: string | null;
helper_agent_model: string | null;
helper_agent_prompt: string | null;
helper_agent_temperature: number;
```

---

## 4. Backend Changes

### 4.1 Add `temperature` parameter to provider `predict()`

**File:** `services/llm_providers.py`

**Why:** The existing `predict()` method hardcodes `temperature=0.0` inside each provider. To support per-model temperature, we need to accept it as a parameter and pass it to the LLM API call.

**Protocol update:**

```python
@runtime_checkable
class LLMProviderPort(Protocol):
    def predict(self, text, considered_sentiment_elements, examples,
                aspect_categories, polarities, allow_implicit_aspect_terms,
                allow_implicit_opinion_terms, n_few_shot, llm_model,
                prompt_template=None, temperature=0.7):  # ← new param
        ...
```

**Each provider change (Ollama, OpenAI, Anthropic, VLLM):** Add `temperature=0.7` to the signature and replace the hardcoded temperature in the API call:

```python
# OllamaProvider.predict() — before:
response = generate(
    prompt=prompt, model=llm_model, raw=True,
    options={"temperature": 0.0, "max_tokens": 1024},  # ← hardcoded
    format=Aspects.model_json_schema()
)

# After:
def predict(self, ..., temperature=0.7):
    ...
    response = generate(
        prompt=prompt, model=llm_model, raw=True,
        options={"temperature": temperature, "max_tokens": 1024},  # ← parameter
        format=Aspects.model_json_schema()
    )
```

The same pattern applies to OpenAIProvider (replace `temperature=0.0` on line 184), AnthropicProvider (line 277), and VLLMProvider (line 383).

**`predict_llm()` backward-compat wrapper:** Also needs the `temperature` param added, defaulting to `0.7`, and passed through to `OllamaProvider.predict()`.

### 4.2 New config defaults in `load_config()`

**File:** `main.py`

Add the following keys to the default config dict in `load_config()`:

```python
def load_config():
    """Load configuration from JSON file."""
    if CONFIG_PATH and os.path.exists(CONFIG_PATH):
        with open(CONFIG_PATH, 'r', encoding='utf-8') as f:
            return json.load(f)
    # Return default configuration if no config file
    return {
        # ... existing defaults ...

        # Phase 4: Live Compare Mode
        "compare_mode": "csv",
        "model_a_provider": None,
        "model_a_model": None,
        "model_a_prompt": DEFAULT_LABELING_TEMPLATE,
        "model_a_temperature": 0.7,
        "model_b_provider": None,
        "model_b_model": None,
        "model_b_prompt": DEFAULT_LABELING_TEMPLATE,
        "model_b_temperature": 0.7,
        "helper_agent_provider": None,
        "helper_agent_model": None,
        "helper_agent_prompt": DEFAULT_CHAT_TEMPLATE,
        "helper_agent_temperature": 0.7,
    }
```

**Why pre-fill prompts with defaults:** So the Settings Panel textareas show the current prompt template when first opened. The user modifies from there; blank means use the default behavior.

### 4.3 Expose new fields in `GET /settings`

**File:** `main.py`, `get_settings()` endpoint

Add the 12 new keys to the returned settings dict. This is what the frontend reads on page load to populate the Settings Panel.

### 4.4 New endpoint: `GET /live_prediction/{data_idx}`

**File:** `main.py`

This is the core of the feature. It is a near-copy of `get_ai_prediction()` but reads per-model config instead of global config.

```python
@app.get("/live_prediction/{data_idx}")
def get_live_prediction(data_idx: int, role: str = "model_a"):
    """Generate AI predictions using per-model config.

    Args:
        data_idx: 0-based row index.
        role: 'model_a' or 'model_b' — determines which config keys to use.

    Returns:
        List of predicted aspect dicts (same shape as get_ai_prediction).
    """
    if role not in ("model_a", "model_b"):
        raise HTTPException(status_code=400, detail=f"Unknown role: {role}")

    try:
        data = load_data()
        config = load_config()
        default_aspects = config.get('aspect_categories', [])
        examples = []

        # Read per-model config keys
        provider_name = config.get(f"{role}_provider")
        llm_model = config.get(f"{role}_model")
        prompt_template = config.get(f"{role}_prompt")
        temperature = config.get(f"{role}_temperature", 0.7)

        # Validate that per-model config is complete
        if not provider_name:
            raise HTTPException(
                status_code=400,
                detail=f"{role} has no provider configured. Set it in Settings."
            )
        if not llm_model:
            raise HTTPException(
                status_code=400,
                detail=f"{role} has no model configured. Set it in Settings."
            )

        # Load the review text (same logic as get_ai_prediction)
        # ... (collect text, examples, aspect_categories same as existing endpoint) ...

        # Validate provider config (checks global keys like openai_key)
        from services.llm_providers import validate_provider_config
        val_errors = validate_provider_config(provider_name, CONFIG_DATA)
        if val_errors:
            raise HTTPException(status_code=400, detail=val_errors[0])

        # Dispatch to provider with per-model config
        provider = get_provider(provider_name, CONFIG_DATA)
        predictions = provider.predict(
            text,
            config.get('sentiment_elements', [...existing defaults...]),
            examples,
            aspect_categories,
            config.get('sentiment_polarity_options', [...existing defaults...]),
            allow_implicit_aspect_terms=config.get('implicit_aspect_term_allowed', True),
            allow_implicit_opinion_terms=config.get('implicit_opinion_term_allowed', False),
            n_few_shot=config.get('n_few_shot', 10),
            llm_model=llm_model,
            prompt_template=prompt_template,
            temperature=temperature       # ← new parameter
        )[0]
        predictions = predictions["aspects"]

        # Add position data (same as existing endpoint)
        if config.get('save_phrase_positions', True):
            for aspect in predictions:
                if 'aspect_term' in aspect and aspect['aspect_term'] != 'NULL':
                    start, end = find_phrase_positions(text, aspect['aspect_term'])
                    aspect['at_start'] = start
                    aspect['at_end'] = end
                if 'opinion_term' in aspect and aspect['opinion_term'] != 'NULL':
                    start, end = find_phrase_positions(text, aspect['opinion_term'])
                    aspect['ot_start'] = start
                    aspect['ot_end'] = end

        return predictions

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Error in live prediction: {str(e)}"
        )
```

**Key differences from `get_ai_prediction()`:**
1. Reads `{role}_provider`, `{role}_model`, `{role}_prompt`, `{role}_temperature` instead of global `llm_provider`, `llm_model`, `labeling_prompt_template`
2. Validates per-model config is non-blank before proceeding (no fallback)
3. Passes `temperature` to `provider.predict()`
4. Takes a `role` query parameter to distinguish Model A vs Model B

### 4.5 Modify `agent_chat()` for per-agent config

**File:** `main.py`, `agent_chat()` endpoint

Replace the global config reads with per-agent reads:

```python
# Before:
provider_name = _derive_provider(CONFIG_DATA)
...
provider = get_provider(provider_name, CONFIG_DATA)
reply = provider.chat(
    messages=messages,
    model=config.get("llm_model", "gemma3:4b"),
    temperature=0.7,
    max_tokens=300
)

# After:
provider_name = CONFIG_DATA.get("helper_agent_provider") or _derive_provider(CONFIG_DATA)
llm_model = CONFIG_DATA.get("helper_agent_model") or config.get("llm_model", "gemma3:4b")
chat_template = CONFIG_DATA.get("helper_agent_prompt", DEFAULT_CHAT_TEMPLATE)
temperature = CONFIG_DATA.get("helper_agent_temperature", 0.7)

# Validate per-agent config
if not CONFIG_DATA.get("helper_agent_provider"):
    # Fall back to rule-based responses
    ...existing fallback...

# Use helper-agent-specific prompt
system_content = chat_template.format(...)

provider = get_provider(provider_name, CONFIG_DATA)
reply = provider.chat(
    messages=messages,
    model=llm_model,
    temperature=temperature,
    max_tokens=300
)
```

**Important:** The Helper Agent's prompt is the chat template (uses `review_text`, `model_a_name`, etc. as format placeholders), not the labeling template. The `helper_agent_prompt` should default to `DEFAULT_CHAT_TEMPLATE`.

### 4.6 Per-model config validation (utility function)

**File:** `services/llm_providers.py`

Add a new validation function that checks a per-model config is complete:

```python
def validate_per_model_config(role: str, config: dict) -> list[str]:
    """Validate that a per-model config has its required fields.

    Checks:
    - Provider must be set
    - Model must be set
    - Provider-specific global keys must be present (via validate_provider_config)

    Args:
        role: 'model_a', 'model_b', or 'helper_agent'
        config: CONFIG_DATA dict.

    Returns:
        List of error messages (empty = valid).
    """
    errors = []
    provider_name = config.get(f"{role}_provider")
    model_name = config.get(f"{role}_model")

    if not provider_name:
        errors.append(f"{role}: No provider configured.")
    if not model_name:
        errors.append(f"{role}: No model configured.")

    if provider_name:
        # Check global keys required by the chosen provider
        prov_errors = validate_provider_config(provider_name, config)
        errors.extend(prov_errors)

    return errors
```

---

## 5. Frontend Changes

### 5.1 Extend `Settings` interface

**File:** `frontend/src/types.ts`

Add 12 new fields plus `compare_mode` to the `Settings` interface. See [Section 3](#data-model--config-keys) above for the full field list.

Also update `DEFAULT_SETTINGS` in `App.tsx` to include defaults for all new fields.

Also update the settings fetch in the `useEffect` in `App.tsx` to capture the new fields from the `/settings` response.

### 5.2 Settings Panel: 3 new collapsible sections

**File:** `frontend/src/components/SettingsPanel.tsx`

#### Compare Mode selector

Add a radio/select control between the existing "0. Görünüm" and "1. Ek Açıklama" sections:

```tsx
<section>
  <SectionTitle title="Karşılaştırma Modu" />
  <div className="flex gap-2 py-1.5 px-1">
    <button
      onClick={() => setForm(p => ({ ...p, compare_mode: 'csv' }))}
      className={`flex-1 py-2 px-3 rounded-lg text-xs font-bold transition-all border ${
        form.compare_mode === 'csv'
          ? 'bg-primary text-primary-content border-primary shadow-sm'
          : 'bg-base-200 text-base-content/60 border-base-300 hover:text-base-content'
      }`}
    >
      📁 CSV Karşılaştırma
    </button>
    <button
      onClick={() => setForm(p => ({ ...p, compare_mode: 'live' }))}
      className={`flex-1 py-2 px-3 rounded-lg text-xs font-bold transition-all border ${
        form.compare_mode === 'live'
          ? 'bg-primary text-primary-content border-primary shadow-sm'
          : 'bg-base-200 text-base-content/60 border-base-300 hover:text-base-content'
      }`}
    >
      ⚡ Canlı Karşılaştırma
    </button>
  </div>
</section>
```

#### Per-model collapsible sections (DaisyUI collapse)

Each section (Model A, Model B, Helper Agent) uses a DaisyUI collapse with the same sub-controls:

```tsx
const PROVIDER_OPTIONS = [
  { value: 'ollama', label: 'Ollama (yerel)' },
  { value: 'openai', label: 'OpenAI' },
  { value: 'anthropic', label: 'Anthropic' },
  { value: 'vllm', label: 'vLLM' },
];

function ModelConfigSection({ title, prefix, form, setForm }: {
  title: string; prefix: string;
  form: FormState; setForm: React.Dispatch<React.SetStateAction<FormState>>;
}) {
  const isConfigured = !!form[`${prefix}_provider`] && !!form[`${prefix}_model`];
  return (
    <div className="collapse collapse-arrow bg-base-200/50 rounded-xl border border-base-300">
      <input type="checkbox" defaultChecked={false} />
      <div className="collapse-title text-xs font-bold text-base-content flex items-center gap-2">
        {isConfigured ? '🟢' : '⚪'} {title}
      </div>
      <div className="collapse-content space-y-1">
        <SelectRow label="Sağlayıcı" key_={`${prefix}_provider`}
          form={form} setForm={setForm} options={PROVIDER_OPTIONS} />
        <TextRow label="Model" key_={`${prefix}_model`}
          form={form} setForm={setForm} placeholder="deepseek-v4-flash" />
        <div className="py-1.5 px-1">
          <label className="text-xs text-base-content/60 block mb-1">Sıcaklık (Temperature)</label>
          <div className="flex items-center gap-3">
            <input
              type="range" min="0" max="2" step="0.1"
              value={(form[`${prefix}_temperature`] as number) ?? 0.7}
              onChange={(e) => setForm(p => ({ ...p, [`${prefix}_temperature`]: parseFloat(e.target.value) }))}
              className="range range-primary range-xs flex-1"
            />
            <span className="text-xs font-mono text-base-content/70 w-8 text-right">
              {(form[`${prefix}_temperature`] as number)?.toFixed(1) ?? '0.7'}
            </span>
          </div>
        </div>
        <div className="py-1.5 px-1">
          <label className="text-xs text-base-content/60 block mb-1">Prompt</label>
          <textarea
            value={(form[`${prefix}_prompt`] as string) ?? ''}
            onChange={(e) => setForm(p => ({ ...p, [`${prefix}_prompt`]: e.target.value }))}
            rows={6}
            className="w-full bg-base-200 border border-base-300 rounded-lg px-2.5 py-1.5 text-xs font-mono text-base-content placeholder-base-content/40 focus:outline-none focus:border-primary focus:ring-1 focus:ring-primary transition-all resize-y"
            placeholder="Prompt template..."
          />
        </div>
      </div>
    </div>
  );
}
```

Then instantiate three times in the settings panel body:

```tsx
<section className="space-y-2">
  <SectionTitle title="3a. Model A (Canlı)" />
  <ModelConfigSection title="Model A" prefix="model_a" form={form} setForm={setForm} />
</section>
<section className="space-y-2">
  <SectionTitle title="3b. Model B (Canlı)" />
  <ModelConfigSection title="Model B" prefix="model_b" form={form} setForm={setForm} />
</section>
<section className="space-y-2">
  <SectionTitle title="3c. Yardımcı Asistan (Canlı)" />
  <ModelConfigSection title="Helper Agent" prefix="helper_agent" form={form} setForm={setForm} />
</section>
```

### 5.3 App.tsx: Live mode state & fetching

**File:** `frontend/src/App.tsx`

#### State additions

```typescript
// New state for live prediction results
const [liveModelATriplets, setLiveModelATriplets] = useState<TripletItem[]>([]);
const [liveModelBTriplets, setLiveModelBTriplets] = useState<TripletItem[]>([]);
const [isModelAPredicting, setIsModelAPredicting] = useState(false);
const [isModelBPredicting, setIsModelBPredicting] = useState(false);
```

#### Live prediction fetch function

```typescript
const fetchLivePrediction = async (role: 'model_a' | 'model_b') => {
  const setter = role === 'model_a' ? setLiveModelATriplets : setLiveModelBTriplets;
  const loader = role === 'model_a' ? setIsModelAPredicting : setIsModelBPredicting;

  loader(true);
  try {
    const res = await fetch(`${backendUrl}/live_prediction/${currentIndex}?role=${role}`);
    if (!res.ok) {
      const err = await res.json();
      setSaveToast(`❌ ${role}: ${err.detail || 'Hata'}`);
      setTimeout(() => setSaveToast(null), 3000);
      return;
    }
    const predictions: TripletItem[] = await res.json();
    setter(predictions);
    setSaveToast(`✅ ${role} tamamlandı (${predictions.length} etiket)`);
    setTimeout(() => setSaveToast(null), 2500);
  } catch (e) {
    setSaveToast(`❌ ${role}: Sunucu hatası`);
    setTimeout(() => setSaveToast(null), 3000);
  } finally {
    loader(false);
  }
};
```

#### Updated render for Compare mode

In the Compare mode section, check `compare_mode` to decide which data to show:

```tsx
const isLiveMode = settings.compare_mode === 'live';

// In the three-column grid
<ModelTripletColumn
  title={currentData.model_a_name ? `Model A - ${currentData.model_a_name}` : "Model A"}
  subtitle="" badgeText={currentData.model_a_name || "MODEL A"}
  badgeColor="bg-secondary/10 text-secondary border-secondary/30"
  triplets={isLiveMode ? liveModelATriplets : currentData.model_a_triplets}
  selectedIds={selectedModelAIds}
  onToggleSelect={toggleModelA}
  onSelectAll={selectAllModelA}
  onClearAll={clearAllModelA}
  // New props for live mode
  onRunPrediction={isLiveMode ? () => fetchLivePrediction('model_a') : undefined}
  isPredicting={isModelAPredicting}
/>
```

#### Clear live state on row navigation

```typescript
// In loadReviewRow, add:
setLiveModelATriplets([]);
setLiveModelBTriplets([]);
```

### 5.4 ModelTripletColumn: "Run" button

**File:** `frontend/src/components/ModelTripletColumn.tsx`

Add optional props and a "Run" button in the empty state:

```typescript
interface ModelTripletColumnProps {
  // ... existing props ...
  onRunPrediction?: () => void;       // Live mode: run button callback
  isPredicting?: boolean;              // Live mode: loading state
}

// In the empty state section, replace the static message:
{triplets.length === 0 ? (
  <div className="h-full flex flex-col items-center justify-center text-base-content/50 py-8">
    {onRunPrediction ? (
      <>
        <button
          onClick={onRunPrediction}
          disabled={isPredicting}
          className="px-6 py-3 rounded-xl bg-primary hover:bg-primary/90 text-primary-content font-bold text-sm transition-all shadow-lg flex items-center gap-2 disabled:opacity-50"
        >
          {isPredicting ? (
            <>
              <div className="w-4 h-4 border-2 border-primary-content border-t-transparent rounded-full animate-spin" />
              Tahmin ediliyor...
            </>
          ) : (
            <>
              <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M14.752 11.168l-3.197-2.132A1 1 0 0010 9.87v4.263a1 1 0 001.555.832l3.197-2.132a1 1 0 000-1.664z" />
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
              </svg>
              {title} Çalıştır
            </>
          )}
        </button>
        <p className="text-xs text-base-content/40 mt-3">
          {isPredicting ? 'Lütfen bekleyin...' : 'Canlı tahmin için tıklayın'}
        </p>
      </>
    ) : (
      <>
        {/* Existing CSV-mode empty state */}
        <svg className="w-8 h-8 mb-2 opacity-40" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M20 13V6a2 2 0 00-2-2H6a2 2 0 00-2 2v7m16 0v5a2 2 0 01-2 2H6a2 2 0 01-2-2v-5m16 0h-2.586a1 1 0 00-.707.293l-2.414 2.414a1 1 0 01-.707.293h-3.172a1 1 0 01-.707-.293l-2.414-2.414A1 1 0 006.586 13H4" />
        </svg>
        <p className="text-sm font-medium">Bu model çıktı üretmedi</p>
        <p className="text-xs text-base-content/40 mt-1">Eksikleri manuel girebilirsiniz</p>
      </>
    )}
  </div>
) : (
  // ... existing triplet rendering ...
)}
```

**Note:** In Live mode, the "Tümünü Seç" / "Tümünü Kaldır" buttons only appear when triplets have been loaded (they already do — the existing `{triplets.length > 0 && (...)}` guard handles this).

---

## 6. Test Strategy

Following the [python-testing-patterns](../python-testing-patterns/SKILL.md) skill conventions:

### 6.1 New tests for `live_prediction` endpoint

**File:** `tests/test_live_prediction.py`

| Test name | What it covers |
|---|---|
| `test_live_prediction_model_a_returns_predictions` | Happy path: Model A configured → returns triplet list |
| `test_live_prediction_model_b_returns_predictions` | Happy path: Model B configured → returns triplet list |
| `test_live_prediction_unknown_role_returns_400` | Invalid role query param → 400 |
| `test_live_prediction_no_provider_returns_400` | `model_a_provider` is None → 400 with clear message |
| `test_live_prediction_no_model_returns_400` | `model_a_model` is None → 400 |
| `test_live_prediction_calls_provider_with_temperature` | Verifies `provider.predict(temperature=X)` is called with the configured temperature |
| `test_live_prediction_calls_provider_with_custom_prompt` | Verifies the per-model prompt is passed through |
| `test_live_prediction_inherits_global_api_keys` | Uses global `openai_key` when model_a_provider=openai |
| `test_live_prediction_adds_position_data` | `save_phrase_positions=true` → predictions have at_start/at_end |

### 6.2 Updated tests for temperature in `predict()`

**File:** `tests/test_llm_providers.py`

Update existing tests that call `provider.predict()` to include `temperature` parameter. Add new tests:

| Test name | What it covers |
|---|---|
| `test_ollama_predict_accepts_temperature_parameter` | Verifies signature accepts temperature |
| `test_all_providers_accept_temperature` | Tests all 4 providers accept the temperature kwarg |
| `test_temperature_default_is_07` | Default value is 0.7 |

### 6.3 New tests for `validate_per_model_config()`

**File:** `tests/test_llm_providers.py` (added to existing file)

| Test name | What it covers |
|---|---|
| `test_validate_per_model_config_returns_empty_when_valid` | All fields set → no errors |
| `test_validate_per_model_config_missing_provider` | No provider → error |
| `test_validate_per_model_config_missing_model` | No model → error |
| `test_validate_per_model_config_missing_api_key` | Provider=openai but no openai_key → error |

### 6.4 Vitest frontend tests

**File:** `frontend/src/components/SettingsPanel.test.tsx` (new)

| Test name | What it covers |
|---|---|
| `renders_compare_mode_selector` | CSV/Live toggle renders |
| `renders_model_a_section_expandable` | Model A collapse opens/closes |
| `renders_temperature_slider_with_default` | Temperature slider shows 0.7 |
| `renders_prompt_textarea` | Textarea shows default prompt |

**File:** `frontend/src/components/ModelTripletColumn.test.tsx` (new or appended)

| Test name | What it covers |
|---|---|
| `shows_run_button_when_onRunPrediction_provided` | Live mode: button renders |
| `shows_loading_state_when_isPredicting` | Spinner shown during prediction |
| `shows_static_empty_state_in_csv_mode` | No `onRunPrediction` → old empty state |

---

## 7. Design Decisions & Rationale

### 7.1 Why a new endpoint instead of modifying `get_ai_prediction`

The existing `GET /ai_prediction/{data_idx}` is used by the AI Suggestions feature and reads from global config. Modifying it would risk breaking existing functionality. A separate `GET /live_prediction/{data_idx}?role=model_a` is:

- **Cleaner separation** — each endpoint has one job
- **Backward compatible** — AI Suggestions unchanged
- **Easier to test** — isolated test surface
- **Easier to extend** — adding `role=model_c` or `model_d` is trivial

### 7.2 Why per-model config keys instead of reusing global keys

The user explicitly ruled out fallback behavior ("if it's blank, it should not work"). Each model stands independently:

- Model A could use `openai` with `deepseek-v4-flash`
- Model B could use `anthropic` with `claude-sonnet-4`
- Helper Agent could use `ollama` with `gemma3:4b`

This flexibility requires separate keys. The global `llm_provider` and `llm_model` still exist solely for AI Suggestions backward compat.

### 7.3 Why collapsible (DaisyUI collapse) sections instead of always-visible

The Settings Panel already has 5 sections. Adding 3 more with 4 fields each would make the panel scroll excessively. Collapsible sections:

- Keep the panel manageable at default size
- Let the user focus on what they're configuring
- Follow the DaisyUI collapse pattern already familiar to users

### 7.4 Why a mode selector instead of merging CSV + Live

Merging would mean the compare view shows 4 columns (CSV A, CSV B, Live A, Live B) or tries to overlay them. This is confusing and the user confirmed they want one mode at a time. The mode selector:

- Clear UX: what you see is what's active
- Simple state management: either `currentData.model_a_triplets` or `liveModelATriplets`
- No merge logic needed

### 7.5 Why no fallback/global default for per-model config

Design principle from the user: "There should be no 'global model' for the user. If it's blank, it should not work. As simple as that."

This follows **KISS** (Keep It Simple) — no implicit merging logic, no cascading defaults, no surprising behavior. The user explicitly chooses what each model should use.

### 7.6 Why the existing `predict()` needed a `temperature` parameter added

The `predict()` method on all 4 providers hardcoded `temperature=0.0` internally. To support per-model temperature, we had two options:

1. **Add `temperature` parameter** to `predict()` — changes the interface, but is explicit
2. **Read temperature from config inside `predict()`** — implicit, hides the dependency

Option 1 was chosen because it's **explicit** (the parameter is visible in the call site) and **testable** (can assert the correct value is passed). It follows the **dependency injection** principle from [python-design-patterns](../python-design-patterns/SKILL.md).

### 7.7 Why validation checks both per-model AND global provider keys

The per-model config only stores `provider`, `model`, `prompt`, and `temperature`. The API keys (`openai_key`, `anthropic_key`, `vllm_url`) remain global because they are deployment-level secrets, not model-level settings. The validation:

1. Checks per-model provider is set → clear error: "Model A: No provider configured"
2. Checks per-model model is set → clear error: "Model A: No model configured"
3. Delegates to `validate_provider_config()` to check global API keys → reuses existing logic

This avoids duplicating key validation logic while still giving precise error messages for per-model issues.

---

## 8. Extension Guide

This section is for future coding agents and maintainers.

### 8.1 Adding a new provider (e.g., Google Gemini)

1. Create the adapter class in `services/llm_providers.py` implementing `predict()` and `chat()`
2. Add it to `PROVIDER_REGISTRY`
3. Add the config key (e.g., `gemini_key`) to `load_config()` defaults
4. Add validation in `validate_provider_config()`
5. Add the provider option to `PROVIDER_OPTIONS` in `SettingsPanel.tsx`
6. No changes needed to the live prediction endpoint — it already reads `{role}_provider` from config

### 8.2 Adding a Model C (third comparison column)

1. Add config keys: `model_c_provider`, `model_c_model`, `model_c_prompt`, `model_c_temperature`
2. Add a fourth collapsible section in SettingsPanel.tsx
3. Add `liveModelCTriplets` state in App.tsx
4. Add `fetchLivePrediction('model_c')` call
5. Add a third ModelTripletColumn in the grid (change `grid-cols-1 md:grid-cols-3` to `md:grid-cols-4`)
6. The backend endpoint already supports any role via the `role` query parameter — no backend change needed

### 8.3 Adding per-model API keys (if needed in the future)

Currently API keys are global. To make them per-model:

1. Add `model_a_openai_key`, `model_b_openai_key`, etc. to config
2. Modify `get_live_prediction()` to build a config subset with the per-model key before calling `get_provider()`
3. Modify `validate_per_model_config()` to check the per-model key instead of global

### 8.4 Adding keyboard shortcuts for "Run" buttons

Per the user's earlier mention of "configurable shortcut". The `ModelTripletColumn` already accepts `onRunPrediction` as a prop. To add keyboard shortcuts:

1. Add `onKeyDown` handler in `App.tsx` (or a custom hook)
2. Map keys (e.g., `Ctrl+1` for Model A, `Ctrl+2` for Model B)
3. Call `fetchLivePrediction` when the shortcut is pressed
4. The per-model config is already stored in settings — no backend change needed

### 8.5 Files to touch for this feature

| File | Change type | What to do |
|---|---|---|
| `services/llm_providers.py` | Modify | Add `temperature` to predict(), add `validate_per_model_config()` |
| `main.py` | Modify | Add config keys, expose in settings, add `live_prediction` endpoint, update `agent_chat` |
| `cli.py` | Modify | Add template constant defaults for `model_a_prompt` etc. (keep in sync with prediction.py) |
| `frontend/src/types.ts` | Modify | Extend Settings interface |
| `frontend/src/App.tsx` | Modify | Add live state, fetch function, conditional rendering |
| `frontend/src/components/SettingsPanel.tsx` | Modify | Add mode selector + 3 collapsible config sections |
| `frontend/src/components/ModelTripletColumn.tsx` | Modify | Add optional `onRunPrediction` + `isPredicting` props |
| `tests/test_llm_providers.py` | Modify | Add per-model config validation tests, temperature tests |
| `tests/test_live_prediction.py` | New | 10+ tests for the live prediction endpoint |
| `agentdocs/session_reports/backend_reference.md` | Modify | Add live_prediction endpoint entry |
| `docs/architecture_map.md` | Modify | Add new endpoint, module changes |
| `agentdocs/ProjectPrimer.md` | Modify | Note config keys, live mode |
| `tests/testcases.md` | Modify | Add Tier 9 for live compare mode |

---

## 9. Verification Plan

After implementation, run these checks in order:

```
1. py_compile all changed Python files
2. pytest tests/          → all existing + new tests pass
3. npx vitest run          → all frontend tests pass
4. npm run build           → frontend compiles
5. Start backend + frontend
6. Open browser → app loads without console errors
7. Verify CSV mode still works (no regression):
   - Switch to Compare mode (CSV) → existing columns render from CSV
   - Add triplets, save → works as before
8. Verify Live mode:
   - Open Settings → switch to "Canlı Karşılaştırma"
   - Configure Model A: provider=ollama, model=gemma3:4b
   - Configure Model B: provider=ollama, model=gemma3:4b
   - Close settings
   - Click "Model A Çalıştır" → loading spinner → triplets appear
   - Click "Model B Çalıştır" → loading spinner → triplets appear
   - Select triplets, save → works
9. Verify blank config:
   - Clear Model A provider → back to Compare → "Model A Çalıştır" shows error
10. Verify Helper Agent uses its own prompt:
    - Change helper_agent_prompt → ask a question → response reflects new prompt
```
