# Task 3 Kickoff — New Helper Agent Providers (Anthropic & vLLM)

This is the only task for this session. Full context is below. Read carefully before proposing a plan.

## Task

The current helper agent implementation is effectively hardcoded or narrowly focused on a few providers (e.g., OpenAI, Ollama). Your job is to refactor the AI prediction pipeline to support Anthropic and vLLM, making the provider selection configurable via CLI/config.

### Current state (Verify before coding)

This feature is modular but not yet unified:
- The backend contains functions (likely named `predict_openai`, `predict_ollama`, etc.) in `main.py` that handle specific API request structures.
- Provider selection is likely determined by rigid logic or limited command-line arguments.
- The `AgentChatRequest` model in `main.py` needs to support passing provider-specific parameters.
- **Grep for `openai` and `ollama`** across `main.py` and `cli.py` to identify the existing entry points and configuration handling.

### What to build

1. **CLI & Config Expansion:**
   - Add new flags in `cli.py` to support configuring Anthropic (`--anthropic-key`) and vLLM (`--vllm-url`, `--vllm-model`).
   - Update the configuration loader to ingest these new parameters.
2. **Provider Abstraction/Dispatch:**
   - Implement a dispatch mechanism (or expand the existing one) in `main.py` that routes requests based on the selected provider.
   - Ensure the prediction function interface is unified: `get_ai_prediction(text, provider, **kwargs)`.
3. **New Client Implementation:**
   - Implement `predict_anthropic` (using the Anthropic SDK or standard API calls).
   - Implement `predict_vllm` (using the `openai` SDK pointing to the custom vLLM `base_url`).
4. **Environment/Configuration:**
   - Ensure API keys and URLs are handled securely (do not hardcode keys).
   - If a provider is selected but the necessary key/URL is missing, raise a clear user-friendly error immediately.

### Definition of done

- The tool can successfully switch between "openai", "ollama", "anthropic", and "vllm" via CLI flags.
- Anthropic and vLLM providers produce valid ABSA output (aspect_term, aspect_category, sentiment_polarity, opinion_term).
- The existing functionality for OpenAI and Ollama remains completely intact and bug-free.
- No hardcoded API keys; all sensitive configuration is passed via CLI or env.

---

## What I need from you

1. A step-by-step execution plan in the `[Step] → verify: [how I'll check this worked]` format. 
2. A brief note on how you intend to refactor the `get_ai_prediction` dispatcher to keep the code clean as we add future providers (e.g., Factory pattern vs. simple dictionary dispatch).
3. Wait for my go-ahead.
4. Once approved, provide the full file contents (or clearly marked diffs) for every file you change.

If you need to see the exact current contents of `main.py` (specifically the existing `predict_*` functions) or `cli.py` before formulating your plan, explicitly ask for them now.