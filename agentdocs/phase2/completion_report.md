# Phase 2 — Completion Report

**Date:** 2026-07-05
**Goal:** Frontend-only AI Suggestions wiring, Settings Panel with backend PATCH endpoint
**Status:** ✅ Complete

---

## Task 1: AI Suggestions — Frontend Wiring

### Problem

The backend had a fully functional `GET /ai_prediction/{data_idx}` endpoint and CLI flags (`--ai-suggestions`, `--disable-ai-automatic-prediction`), but the fork's entirely rewritten React frontend had **zero** AI suggestion UI. The original NilsHellwig/AnnoABSA repo had the feature in its `App.tsx` but it was lost during the fork's frontend re-architecture (Compare mode with `ModelTripletColumn`/`ManualInputForm`/`PhraseAnnotator`).

### What was built

| File | Lines | Purpose |
|---|---|---|
| `frontend/src/components/AISuggestions.tsx` | ~112 | Suggestion list component with accept (✓) / reject (✗) buttons |
| `frontend/src/App.tsx` | ~+100 | State, handlers, AI button, auto-trigger, abort logic, mounting |

### Key design decisions

1. **No backend changes** — The existing `GET /ai_prediction/{data_idx}` endpoint is consumed as-is. Its response shape (list of dicts with `aspect_term`, `aspect_category`, `sentiment_polarity`, `opinion_term`, `at_start`, `at_end`, `ot_start`, `ot_end`) maps directly to the `AiSuggestionItem` interface.

2. **Separate component** — `AISuggestions.tsx` is a self-contained list that receives suggestions, onAccept, and onReject props. It doesn't own the AI fetch logic or button — App.tsx handles those.

3. **Accept/reject flow** — Accepting adds the suggestion to `manualTriplets` state (same path as manually-entered triplets). Rejecting filters it from the local `aiSuggestions` array with no persistence.

4. **AbortController with ref** — Uses `useRef<AbortController | null>` instead of state to avoid re-render cycles during abort. The ref is aborted on row navigation (`useEffect` on `currentIndex`) and on manual save (`handleNextReview`).

5. **Auto-trigger gating** — Three conditions must all be true:
   - `enablePrePrediction === true`
   - `disableAiAutomaticPrediction === false`
   - Current row has no saved triplets (`manualTriplets.length === 0`)
   
   Plus a `aiTriggeredForIndex` flag prevents re-firing on the same index.

6. **Mode-agnostic mounting** — `AISuggestions` is mounted below the center column in Compare mode (wrapping `ManualInputForm`) and below the `PhraseAnnotator` in Manual mode. Same component, same props, just placed in different parts of the DOM tree.

### Files changed (Task 1 only)

```
frontend/src/App.tsx                    # +149 -16 (state, handlers, button, auto-trigger, mount)
frontend/src/components/AISuggestions.tsx  # new (112 lines)
```

---

## Task 2: Settings Panel

### Problem

All 35 CLI flags were only configurable via command-line arguments. Users had no GUI to change settings after launch. The Phase 2 audit classified flags into A (runtime-editable), B (startup-only, could be made live), C (actions), and D (infrastructure). This task covered categories A + B.

### What was built

| File | Lines | Purpose |
|---|---|---|
| `main.py` | +31 | `PATCH /settings` endpoint |
| `frontend/src/components/SettingsPanel.tsx` | ~363 | Modal with 5 sections, all Turkish UI |
| `frontend/src/types.ts` | +13 | Extended `Settings` interface |
| `frontend/src/App.tsx` | +92 | Gear button, save/rescan handlers, modal state |

### Endpoint: `PATCH /settings`

```
POST /settings { "key": value, ... }
→ { "status": "ok" }
```

- Accepts JSON body with one or more config key-value pairs
- Merges into `CONFIG_DATA` in-memory dict
- Writes updated config to `CONFIG_PATH` (the JSON file on disk)
- Returns HTTP 500 on error
- **Does NOT** re-instantiate provider classes
- **Does NOT** reload comparison CSVs
- Changes take effect immediately in-memory, and on next use for API keys / provider

### Settings Panel component

**5 sections:**

| Section | Settings | Control type |
|---|---|---|
| 1. Annotation | sentiment elements, polarities, categories, implicit aspect/opinion, click-on-token, save positions, clean phrases | Chip selectors, comma-separated input, toggles |
| 2. AI / LLM | enable predictions, disable auto-prediction, provider, model, vLLM model, API keys, vLLM URL, few-shot count | Toggles, dropdown, text inputs, password inputs, number input |
| 3. Timing | store time, display avg time | Toggles |
| 4. Data | Model A name, Model B name | Text inputs |
| 5. Utilities | Re-scan positions | Button (calls `POST /auto-add-positions`) |

### Key design decisions

1. **Dirty tracking** — `hasChanged()` compares current `settings` prop against local `form` state. Only changed fields are sent in the PATCH body. API keys and names that were cleared get sent as `null` instead of empty string.

2. **AI flag sync** — When `enable_pre_prediction` or `disable_ai_automatic_prediction` change via the panel, the separate state variables used by the AI button/auto-trigger logic are updated in `handleSaveSettings`.

3. **Password masking** — API key fields use `type="password"` to prevent shoulder-surfing.

4. **Scroll** — The body div has `flex-1 overflow-y-auto min-h-0` (the `min-h-0` is critical for flex shrinkage to enable scrolling).

5. **No new backend files** — The PATCH endpoint lives in `main.py`. No changes to `cli.py`, `services/`, or `models/`.

### Files changed (Task 2 only)

```
main.py                                        # +31 (PATCH /settings)
frontend/src/types.ts                          # +13 (extended Settings)
frontend/src/App.tsx                           # +92 (gear button, handlers, mount)
frontend/src/components/SettingsPanel.tsx      # new (363 lines)
agentdocs/backend_reference.md                 # +10 (PATCH endpoint entry)
architecture_map.md                            # +7 (13 endpoints, new files)
agentdocs/ProjectPrimer.md                     # +2 (~1053 lines, 13 endpoints)
```

---

## Verification

| Check | Result |
|---|---|
| Backend compilation | ✅ All 4 files pass `py_compile` |
| Tests | ✅ 71/71 pass in 0.22-0.30s |
| No backend regressions | ✅ `cli.py`, `services/` untouched |
| No debug prints / TODOs | ✅ Clean |
| Docs updated | ✅ `backend_reference.md`, `architecture_map.md`, `ProjectPrimer.md` |

---

## Files created

```
frontend/src/components/AISuggestions.tsx
frontend/src/components/SettingsPanel.tsx
agentdocs/phase2/completion_report.md     (this file)
```

## Files modified (Phase 2 total)

```
main.py                     # +31 (PATCH /settings)
frontend/src/App.tsx        # +241 (AI + settings integration)
frontend/src/types.ts       # +13 (extended Settings)
agentdocs/backend_reference.md   # +10
architecture_map.md              # +7
agentdocs/ProjectPrimer.md       # +2
```
