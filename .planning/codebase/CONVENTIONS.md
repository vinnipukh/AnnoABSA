# AnnoABSA Coding Conventions

> Quality-focused code standards for the AnnoABSA project.
> Last updated: 2026-07-13

---

## 1. Python Backend

### General

- **Python version**: 3.11+ (`requires-python = ">=3.11"` in `pyproject.toml`)
- **Type hints**: All public functions and methods MUST have type hints on parameters and return values. Private helpers (`_`-prefixed) SHOULD have them.
- **Shebang**: Executable CLI scripts (`cli.py`) start with `#!/usr/bin/env python3`. Library modules do not.

### Docstrings

- Every module, class, and public function MUST have a module-level or function-level docstring.
- **Module docstrings**: Triple-quoted string immediately after the file header. Describe the module's purpose, exported symbols, and any architectural notes.
- **Function docstrings**: Describe what the function does, its args (with `Args:` block), return value (`Returns:`), and exceptions raised (`Raises:`).
- **Pattern** (Google-style):

```python
def find_phrase_positions(text: str, phrase: str) -> tuple[int | None, int | None]:
    """Find start and end positions of a phrase in text.

    Args:
        text: The review text to search in.
        phrase: The phrase to locate.

    Returns:
        Tuple (start, end) or (None, None) if not found.
    """
```

### Naming

| Construct | Convention | Example |
|---|---|---|
| Modules | `snake_case` | `nlp_helpers.py`, `llm_providers.py` |
| Classes | `PascalCase` | `OllamaProvider`, `ABSAAnnotatorConfig` |
| Functions | `snake_case` | `build_prediction_prompt()`, `validate_provider_config()` |
| Variables | `snake_case` | `few_shot_examples`, `aspect_categories` |
| Constants | `UPPER_SNAKE_CASE` | `DEFAULT_LABELING_TEMPLATE`, `CONFIG_DATA` |
| Private | `_`-prefixed | `_derive_provider()`, `_build_flattened_lexicon()` |
| Protocols | `PascalCase` ending with `Port` | `LLMProviderPort` |

### Error Handling

- **Services layer** (`services/`): Use `try/except` with specific exception types. Log errors with `print()`. Return safe defaults (empty dicts/lists) on failure rather than crashing.
- **Route layer** (`app/routes/`): Raise `HTTPException(status_code=4xx/5xx, detail=...)` for API errors. Catch `ValueError` from service calls and convert to 400. Catch `FileNotFoundError` → 404.
- **Data layer** (`app/data.py`): `get_total_count()`, `get_current_index()`, `max_number_of_idxs()` raise `HTTPException(404)` on missing file, `HTTPException(500)` on read errors.
- **Never** let a bare `Exception` propagate from a route handler — all routes are wrapped in `try/except` with `HTTPException`.

### Config System

- **Global state**: A single `CONFIG_DATA` dict in `app/config.py` holds all mutable configuration. Mutated in-place at startup by `cli.py` and at runtime by `PATCH /settings`.
- **Access pattern**: Modules import `from app.config import CONFIG_DATA` (or `from app import config` as `cfg`, then `cfg.CONFIG_DATA`).
- **Route modules**: Do NOT import directly from `main` — import from `app.config` and `app.data`.
- **Defaults**: `app/config.py` function `load_config()` provides default values for every config key.
- **CLI config**: `ABSAAnnotatorConfig` class in `cli/config.py` is the CLI-side config builder. Saved as JSON file, loaded into `CONFIG_DATA` on startup.

### Module Organization

```
main.py                    # Thin FastAPI launcher (~50 lines) — re-exports from app.*
cli.py                     # Thin CLI entrypoint (6 lines) — delegates to cli/
app/
  config.py                # Global CONFIG_DATA dict, load_config(), set_config()
  data.py                  # Data I/O: load/save CSV/JSON, parsing, comparison CSV loading
  positions.py             # Position auto-fill logic
  routes/                  # FastAPI routers
    nlp.py                 # 4 NLP endpoints
    settings.py            # GET/PATCH /settings
    reviews.py             # GET /data/{idx}, POST /save, POST /agent/chat
    ai.py                  # GET /ai_prediction, /live_prediction
    timing.py              # POST /timing, GET /avg-annotation-time
    upload.py              # POST /upload-data, /auto-add-positions
    learning.py            # Active learning endpoints
services/
  prediction.py            # Prompt building, BM25 retrieval, Pydantic model generation
  llm_providers.py         # 5 provider adapters + dispatch + PROTOCOL
  nlp_helpers.py           # Lazy-loaded NLP tools (SentiNet, BERT, morphology, embeddings)
  active_learning.py       # TF-IDF + LogisticRegression uncertainty sampling
models/
  schemas.py               # Pydantic request/response models
```

### Imports

- **Standard library first**, then third-party, then local. Blank lines between groups.
- `from foo import bar` for specific symbols.
- In `main.py`: Use `from app.config import *` (with `# noqa: F401, F403`) for backward-compat re-exports.
- Otherwise, avoid star imports.

### Backend Testing Patterns

- **TestClient**: Use `fastapi.testclient.TestClient` for integration tests.
- **Mocking**: `unittest.mock.patch` and `MagicMock` for LLM provider calls, NLP model loading.
- **Test data**: Use `tempfile.NamedTemporaryFile` for temporary CSVs in integration tests.
- **Environment setup**: Set `os.environ["ABSA_DATA_PATH"]` BEFORE importing `main`.
- **CONFIG_DATA mutation**: Tests mutate `CONFIG_DATA` in-place via `import main; main.CONFIG_DATA.update(...)`.

---

## 2. Frontend (TypeScript / React)

### TypeScript

- **Target**: `es5` (compiled by Vite + esbuild, actual target is modern browsers)
- **Strict mode**: `"strict": false`, `"noImplicitAny": false` — NOT strict. TypeScript is used for type documentation, not rigorous type enforcement.
- **Module**: `esnext`, `moduleResolution: "node"`. JSX: `react-jsx`.
- **React 19**: `"^19.1.1"`. Uses `ReactDOM.createRoot` + `flushSync` in tests (not `@testing-library/react` — see Testing section).
- **Custom hooks**: Export as named functions from `hooks/` directory.

### Naming

| Construct | Convention | Example |
|---|---|---|
| Components | `PascalCase` | `SettingsPanel`, `ModelTripletColumn` |
| Files (components) | `PascalCase.tsx` | `NlpHelperToolbar.tsx` |
| Files (non-components) | `camelCase.ts` | `useTextSelection.ts`, `types.ts` |
| Interfaces | `PascalCase` | `TripletItem`, `ReviewComparisonData` |
| Types | `PascalCase` | `FormState`, `TextSelectionState` |
| Functions | `camelCase` | `handleMouseUp`, `cleanPhrase` |
| Constants | `UPPER_SNAKE_CASE` | `ALL_SENTIMENT_ELEMENTS`, `PROVIDER_OPTIONS` |

### React Conventions

- **No class components**: All components are function components with hooks.
- **One component per file**: Each `.tsx` file exports a single component plus its props interface. Helper sub-components can be in the same file.
- **Props interface**: Named `<ComponentName>Props`, defined above the component.
- **Exports**: Named exports (`export const SettingsPanel: React.FC<...> = ...`), not default exports.
- **Hooks at top level**: Follow the rules of hooks — no conditional `useState`/`useEffect`.
- **State**: `useState` for local state, `useCallback` for memoized handlers, `useMemo` for computed values.
- **Refs**: `useRef<HTMLDivElement>(null)` for DOM references and `AbortController` in NLP toolbar.

### Component Structure Pattern

```tsx
import React, { useState, useEffect, useRef, useCallback, useMemo } from 'react';

interface SettingsPanelProps {
  settings: Settings;
  onSave: (updates: Record<string, unknown>) => Promise<void>;
  onClose: () => void;
}

export const SettingsPanel: React.FC<SettingsPanelProps> = ({
  settings,
  onSave,
  onClose,
}) => {
  const [form, setForm] = useState<FormState>(/* ... */);
  // ... hooks and handlers

  return (
    <div>{/* JSX */}</div>
  );
};
```

### CSS / Styling

- **Tailwind CSS** (v3.4.17) with **DaisyUI** (v4.12.24) for components.
- **Utility classes**: All styling is done via Tailwind classes — no separate CSS files for individual components.
- **Colors**: Use DaisyUI theme tokens: `bg-base-100`, `text-base-content`, `bg-primary`, `text-error`, etc.
- **SVGs**: Inline SVGs (no external icon libraries except `@phosphor-icons/react`). Structural emojis replaced with inline SVGs.
- **Themes**: DaisyUI themes (`dark`, `light`, `coffee`, `forest`, `cupcake`, `aqua`, `lemonade`) — switchable via settings at runtime with `data-theme` attribute.

### Imports

- **React imports first**, then local files. No blank line between groups.
- Named imports from `'../types'` for type definitions.
- Component imports are path-based from `'./components/X'` or direct relative path.

### Frontend Testing Patterns

- **NOT using `@testing-library/react`**: Due to a React 19.2.7 CJS bug where `React.act` is undefined in the CJS bundle, which crashes testing-library's `render()`.
- **Alternative**: Mount components directly using `ReactDOMClient.createRoot` + `ReactDOM.flushSync`.
- **Render helper** (used in ALL test files):

```typescript
function render(el: React.ReactElement): { container: HTMLElement; root: ReactDOMClient.Root } {
  const container = document.createElement('div');
  document.body.appendChild(container);
  const root = ReactDOMClient.createRoot(container);
  ReactDOM.flushSync(() => { root.render(el); });
  return { container, root };
}
```

- **Query helper** — use `findByText()` with `document.createTreeWalker` instead of `screen.getByText()`:

```typescript
function findByText(container: HTMLElement, pattern: RegExp | string): Element | null {
  const walker = document.createTreeWalker(container, NodeFilter.SHOW_TEXT, null);
  let node: Text | null;
  while ((node = walker.nextNode() as Text | null)) {
    if (typeof pattern === 'string'
      ? node.textContent?.includes(pattern)
      : pattern.test(node.textContent || '')) {
      return node.parentElement;
    }
  }
  return null;
}
```

- **Click helper**: Use native `MouseEvent` dispatch wrapped in `flushSync`:

```typescript
function click(target: Element | null) {
  if (!target) throw new Error('Cannot click null element');
  ReactDOM.flushSync(() => {
    target.dispatchEvent(new MouseEvent('click', { bubbles: true, cancelable: true }));
  });
}
```

- **Polyfills**: `Element.prototype.scrollIntoView = vi.fn()` in HelperAgentChatbox tests (jsdom doesn't implement it).
- **Mock fetch**: `global.fetch = vi.fn()` for API-calling components.
- **Test framework**: `vitest` (v4.1.10) with `globals: true`, `environment: 'jsdom'`.

### File Organization

```
frontend/src/
  index.tsx                  # Entry point: createRoot + StrictMode
  App.tsx                    # Root component — all application state
  App.css                    # Global app styles
  index.css                  # Tailwind directives
  types.ts                   # Shared TypeScript interfaces
  phraseColoring.tsx          # Color assignment for inline annotation highlighting
  components/
    SettingsPanel.tsx         # Settings modal
    ModelTripletColumn.tsx   # Compare-mode column
    HelperAgentChatbox.tsx   # Chat panel
    NlpHelperToolbar.tsx     # NLP toolbox
    PhraseAnnotator.tsx      # Manual annotation form
    ManualInputForm.tsx      # Manual triplet input form
    AISuggestions.tsx        # AI suggestion list
    EditReviewTextModal.tsx  # Text editing modal
    CustomCheckbox.tsx       # Reusable checkbox
    ActiveLearningSuggestions.tsx  # Active learning panel
    WelcomeOverlay.tsx       # First-time welcome screen
  hooks/
    useTextSelection.ts      # Native drag-to-select hook
```

---

## 3. Git Conventions

- **Branch**: Active development on `experimental` branch.
- **Commits**: Descriptive messages. No enforced commit message format.
- **Commit types observed**: Feature additions, bug fixes, refactoring (e.g., "phase N feature", "fix X bug", "refactor: extract Y").

---

## 4. Lint / Tooling Configuration

| Tool | Config File | Key Settings |
|---|---|---|
| **Vite** | `frontend/vite.config.js` | React plugin, port 3000, build to `build/`, esbuild for TS/JSX |
| **Vitest** | `frontend/vite.config.js` (`test` block) | `globals: true`, `environment: 'jsdom'`, no setup files |
| **TypeScript** | `frontend/tsconfig.json` | `target: es5`, `strict: false`, `jsx: react-jsx`, `moduleResolution: node` |
| **Python** | No linter config file (no `.pylintrc`, `pyproject.toml` has no `[tool.*]` sections) | Follow conventions manually |
| **pytest** | No config file | Uses `tests/` directory, `__init__.py` for package |
| **Tailwind** | `frontend/tailwind.config.js` (not verified) | DaisyUI plugin, content paths |

---

## 5. Architecture Patterns

- **Hexagonal architecture** (ports & adapters): `LLMProviderPort` Protocol defines the port. `OllamaProvider`, `OpenAIProvider`, `AnthropicProvider`, `VLLMProvider`, `CustomOpenAIProvider` are the adapters. Dispatch happens through `PROVIDER_REGISTRY` dict.
- **Lazy loading**: NLP helper tools (SentiNet, BERT, morphology, embeddings) load on first use via module-level `_sentinet = None` pattern and `get_*()` accessors.
- **Dynamic model generation**: `build_absa_models()` creates Pydantic models and Enums at runtime based on review text content (allowed phrases become enum members).
- **Backend state**: Global mutable dict (`CONFIG_DATA`) shared by all route handlers via `app.config` import.
