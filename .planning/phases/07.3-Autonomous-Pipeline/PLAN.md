# Phase 7.3: Autonomous Annotation Pipeline — Plan

**Phase:** 7.3-Autonomous-Pipeline
**Planned:** 2026-07-14
**Execution mode:** Sequential by wave
**Status:** Not started

---

## Plan 1: Backend prompt — autopilot action instructions

**Goal:** Add 3 missing `[[action:...]]` directives (`selectTriplet`, `addTriplet`, `annotateAll`) to `DEFAULT_CHAT_TEMPLATE`. No full rewrite — the existing 11 actions with Turkish descriptions and examples are correct. Append the new ones.

**Est. effort:** Easy
**Files:** `services/prediction.py:37-65`

### Implementation Steps
1. Read current `DEFAULT_CHAT_TEMPLATE` to understand format
2. Add `selectTriplet(role, id)` entry — "Belirtilen role ve ID'ye sahip tripleti seç/kaldır"
3. Add `addTriplet(term, category, polarity)` entry — "Elle yeni bir triplet ekle (terim, kategori, kutup)"
4. Add `annotateAll()` entry — "Tüm incelemeleri oto-etiketle (tahmin et → seç → kaydet → ilerle)"

### UAT Criteria
- [ ] 3 new action entries present in `DEFAULT_CHAT_TEMPLATE` with Turkish descriptions
- [ ] Existing 11 actions unchanged
- [ ] Format consistent (same `\\n` line breaks, same `- actionName(args) — description` pattern)
- [ ] All existing backend tests still pass (209)

---

## Plan 2: Keyboard shortcut Ctrl+Shift+L

**Goal:** Wire `Ctrl+Shift+L` to toggle the Active Learning suggestions panel.

**Est. effort:** Easy
**Files:** `frontend/src/App.tsx:247-259`

### Implementation Steps
1. Read existing keyboard shortcut handler at App.tsx (around line 247)
2. The handler already has a generic pattern: `if (e.ctrlKey && e.shiftKey && e.key.toLowerCase() === shortcutKey)`
3. The existing handler toggles `fetchAIPrediction`. Add a new `else if` branch:
   - `if (e.ctrlKey && e.shiftKey && e.key.toLowerCase() === 'l')`
   - Toggle the `showALSuggestions` state (or equivalent state that shows/hides the Active Learning panel)
4. Add a `keyboard_shortcut` entry to settings or handle as a hardcoded shortcut

### UI/UX Constraints
- **Stale closure avoidance** (ref-forwarded callbacks): The keydown handler callback references `showALSuggestions` setter which changes independently of the effect's dependency array. Use the ref-forwarded pattern:
  ```ts
  const toggleALRef = useRef(toggleAL);
  toggleALRef.current = toggleAL;
  ```
  Then call `toggleALRef.current()` inside the registered `keydown` listener. This prevents stale closures without re-registering the listener on every render.
- **No emoji**: No icons needed for a keyboard shortcut.
- **Screen reader support**: The AL panel should have an `aria-label="Active Learning Suggestions"` so screen reader users know what Ctrl+Shift+L toggled.

### UAT Criteria
- [ ] Ctrl+Shift+L toggles Active Learning suggestions panel visibility
- [ ] Existing Ctrl+Shift+(other key) shortcuts still work
- [ ] No conflicting shortcuts
- [ ] All 87 frontend tests still pass
- [ ] 0 TS errors

---

## Plan 3: Auto-suggest banner on uncertain reviews

**Goal:** Show an inline banner above the review header when the current review has high active-learning uncertainty, plus a toast notification as secondary cue.

**Est. effort:** Medium
**Files:**
- `frontend/src/components/ActiveLearningSuggestions.tsx` or new banner component
- `frontend/src/components/AutoSuggestBanner.tsx` (new)

### Implementation Steps
1. Create `frontend/src/components/AutoSuggestBanner.tsx`:
   - Props: `text: string` (review text), `uncertainty: number`, `hasLabels: boolean`, `onDismiss: () => void`, `onAnnotate: () => void`
   - Renders a DaisyUI `alert alert-info` banner with:
     - Icon: Heroicons information circle SVG (`w-5 h-5 text-info`) — copy the exact SVG from `svg-icon-replacements.md` (info circle), do NOT use emoji
     - Text: "Bu inceleme yüksek belirsizlik taşıyor — etiketlemek ister misiniz?"
     - "Etiketle" button (calls `onAnnotate`) — must be ≥44×44px touch target
     - Dismiss (X) button (calls `onDismiss`) — use Heroicons close SVG (X mark), not emoji ✕; must be ≥44×44px touch target
   - CSS: `position: relative`, full width, above review header
   - Condition: `hasLabels` is false AND `uncertainty > threshold` (e.g. 0.7)

2. Wire banner into `App.tsx`:
   - Compute `uncertainty` from `currentData` (may need backend to pass uncertainty in data response, or compute from active learning service)
   - Show banner conditionally above `<ReviewHeader>`
   - Dismiss: hide banner for current review (don't persist)
   - Annotate: toggle Active Learning panel open, or trigger `fetchAIPrediction`

3. Toast notification:
   - When banner first appears, also show a toast: "Bu inceleme yüksek belirsizlik taşıyor"
   - Auto-dismiss after 4 seconds
   - Uses existing `setSaveToast` pattern

### UI/UX Constraints
- **No emoji icons** (Priority 4): Every visual indicator in the banner must use Heroicons SVG. Reference file: `svg-icon-replacements.md` has all needed paths. Specifically:
  - Information circle → Heroicons info SVG (not ℹ️ or ⚠️)
  - Dismiss → Heroicons X mark SVG (not ✕ or ❌)
- **Touch targets ≥44×44px** (Priority 2): 
  - "Etiketle" button: add `min-h-[44px] min-w-[44px]` or use DaisyUI `btn` class which has native touch sizing
  - Dismiss button: add `p-3` or explicit `min-w-[44px] min-h-[44px]`
  - 8px minimum gap between banner buttons
- **Color not sole indicator** (Priority 1): The banner text must be readable without color cues. The info icon provides visual context in addition to the `alert-info` blue tint. This is sufficient — icon + text, not just blue.
- **Reduced motion** (Priority 7): If the banner uses a slide-in animation:
  ```css
  @media (prefers-reduced-motion: reduce) {
    .auto-suggest-banner { animation: none; }
  }
  ```
- **Accessible dismiss** (Priority 1): Dismiss button must have `aria-label="Kapat"` for screen readers since it's icon-only.
- **Component extraction checklist** (from `component-extraction-pitfalls.md`):
  - [ ] List every prop the parent passes to the new component
  - [ ] Verify `onDismiss` and `onAnnotate` callbacks are wired correctly in App.tsx
  - [ ] Verify the banner's conditional rendering doesn't break other layout (no CLS when banner appears/disappears)

### UAT Criteria
- [ ] Banner appears when review has high uncertainty AND no labels
- [ ] Banner does NOT appear when review already has labels
- [ ] Banner does NOT appear when uncertainty is below threshold
- [ ] Dismiss (X) hides banner for current review
- [ ] "Etiketle" button triggers relevant action
- [ ] Toast appears as secondary notification on banner first show
- [ ] No emoji in banner UI (use Heroicons SVG)
- [ ] All 87 frontend tests still pass
- [ ] 0 TS errors

---

## Plan 4: selectTriplet + addTriplet actions + AppActions wiring

**Goal:** Register `selectTriplet(role, id)` and `addTriplet(aspect_term, aspect_category, polarity)` in `AppActions` and wire them. `selectTriplet` already exists as an action — needs prompt entry (Plan 1) and verification. `addTriplet` is new and needs a 3-arg wrapper.

**Est. effort:** Medium
**Files:**
- `frontend/src/types.ts:119-135` — AppActions interface
- `frontend/src/App.tsx:264-280` — AppActions wiring
- `frontend/src/hooks/useAnnotationState.ts:25` — addTriplet action target

### Implementation Steps

#### 4a. selectTriplet verification
1. Verify `selectTriplet(role, id)` is in `AppActions` interface ✅ (already at line 125)
2. Verify it's wired in `App.tsx` ✅ (line 270: `selectTriplet: (role, id) => toggleTriplet(role, id)`)
3. Verify `toggleTriplet` works correctly for 4-way column roles ('gt', 'gemma', 'qwen', 'gpt')
4. Already covered by existing frontend tests

#### 4b. addTriplet 3-arg wrapper
1. Add `addTriplet: (aspect_term: string, aspect_category: string, polarity: string) => void` to `AppActions` interface in `types.ts`
2. In `App.tsx` AppActions wiring, add:
   ```ts
   addTriplet: (term, category, polarity) => {
     const triplet: TripletItem = { id: `manual_${Date.now()}`, aspect_term: term, aspect_category: category, sentiment_polarity: polarity };
     addManualTriplet(triplet);
   }
   ```
3. Add hook test in `useAnnotationState.test.tsx` for the new wrapper

### UI/UX Constraints
- **React 19 test workaround** (from `react19-testing-workaround.md`): The hook test file `useAnnotationState.test.tsx` already uses `createRoot` + `flushSync` instead of `@testing-library/react`. Any new test cases added must follow the same pattern — do NOT import from `@testing-library/react`.
- **File extension**: `.tsx`, not `.ts` — the test file uses generic angle brackets in JSX context.

### UAT Criteria
- [ ] `selectTriplet(role, id)` callable from agent through existing infrastructure
- [ ] `selectTriplet` works for all 6 roles ('model_a', 'model_b', 'gt', 'gemma', 'qwen', 'gpt')
- [ ] `addTriplet(term, category, polarity)` creates a valid `TripletItem` and calls `addManualTriplet`
- [ ] `addTriplet` with `'NULL'` as term works (implicit aspect sentinel)
- [ ] All 87 frontend tests still pass
- [ ] 0 TS errors

---

## Plan 5: Chat predictions endpoint

**Goal:** Create `GET /chat/predictions/{data_idx}` endpoint returning ML predictions formatted as natural Turkish text for the Helper Agent to read and act on.

**Est. effort:** Hard
**Files:**
- `app/routes/learning.py` or new `app/routes/chat_predictions.py`
- `services/active_learning.py` (reuse existing pipeline)

### Implementation Steps
1. Add new route file or new endpoint in `app/routes/learning.py`:
   - `GET /chat/predictions/{data_idx}`
   - Accepts `data_idx: int` path parameter
   - Returns `{"text": "...", "predictions": [...]}`

2. Implementation:
   - Reuses the existing ML pipeline from `services/active_learning.py`:
     - `labeled_texts_from_data()` — extract texts/labels
     - `train_labeled_data()` — train model on labeled reviews
     - `get_uncertainty_scores()` — score review
     - Format output as Turkish text
   - If <2 labeled reviews available → return error message as text
   - If model cannot train → return fallback text

3. Response format:
   ```json
   {
     "text": "Modelin bu inceleme için tahminleri:\\n- Kategori: FOOD#QUALITY, Kutup: positive (güven: 0.92)\\n- Kategori: SERVICE#GENERAL, Kutup: negative (güven: 0.78)\\n\\nYüksek güvenli tahminleri seçip kaydedebilir veya manuel olarak düzenleyebilirsiniz.",
     "predictions": [
       {"aspect_category": "FOOD#QUALITY", "sentiment_polarity": "positive", "confidence": 0.92, "label": "FOOD#QUALITY__positive"},
       {"aspect_category": "SERVICE#GENERAL", "sentiment_polarity": "negative", "confidence": 0.78, "label": "SERVICE#GENERAL__negative"}
     ]
   }
   ```

4. Helper Agent integration:
   - The frontend fetches this endpoint when the Helper Agent needs prediction context
   - The `text` field is injected into the chat context (either as `initialReasoning` or appended to messages)

### UAT Criteria
- [ ] `GET /chat/predictions/{idx}` returns 200 with `text` and `predictions` fields
- [ ] `text` is valid Turkish text describing the predictions
- [ ] `predictions` array contains entries with `aspect_category`, `sentiment_polarity`, `confidence`, `label`
- [ ] Returns appropriate error for out-of-range index → 404
- [ ] Returns appropriate error for <2 labeled reviews → 400 with message
- [ ] Response is deterministic (same input → same output, no randomness)
- [ ] All 209 backend tests still pass
- [ ] 16+ new tests for the new endpoint

---

## Plan 6: annotateAll() pipeline action

**Goal:** Implement `annotateAll()` pipeline action in AppActions — predict → select → save → advance, repeated across N reviews.

**Est. effort:** Hard
**Files:**
- `frontend/src/types.ts:119-135` — AppActions interface
- `frontend/src/App.tsx:264-280` — AppActions wiring
- `frontend/src/hooks/useAnnotationState.ts` — triplet management
- `app/routes/learning.py` — existing predict endpoint

### Implementation Steps

#### 6a. Add annotateAll to AppActions interface
1. Add `annotateAll: (count?: number) => Promise<void>` to `AppActions` in `types.ts`
2. Parameter `count`: number of reviews to process (default 5)

#### 6b. Implement pipeline logic in App.tsx
1. Create async `handleAnnotateAll` function:
   ```ts
   const handleAnnotateAll = useCallback(async (count = 5) => {
     let processed = 0;
     while (processed < count) {
       // 1. Fetch predictions
       const res = await fetch(`${backendUrl}/learning/predict/${currentIndex}`);
       if (!res.ok) break;
       const predictions = await res.json();
       
       // 2. Filter by confidence threshold (>0.5)
       const highConf = predictions.filter(p => p.confidence > 0.5);
       if (highConf.length === 0) break;
       
       // 3. Add triplets via addTriplet wrapper
       for (const p of highConf) {
         addTriplet('NULL', p.aspect_category, p.sentiment_polarity);
       }
       
       // 4. Save and advance
       await saveReview(/* collect selected triplets */);
       goToNext();
       
       // 5. Debounce 500ms for UI
       await new Promise(r => setTimeout(r, 500));
       processed++;
     }
   }, [backendUrl, currentIndex, addTriplet, saveReview, goToNext]);
   ```

2. Wire into AppActions:
   ```ts
   annotateAll: handleAnnotateAll,
   ```

#### 6c. Confirmation model (TBD during planning)
- **Option A (silent):** `annotateAll()` runs immediately when called by agent
- **Option B (confirmed):** Agent calls `annotateAll()` → frontend shows confirmation dialog/chat message asking user — user approves → pipeline runs

Default to Option A (silent) for now. Make it easy to add confirmation later by wrapping the pipeline body.

### UI/UX Constraints
- **Loading state** (Priority 2): The button/action that triggers `annotateAll()` must show a disabled state with spinner during the pipeline run. Use the existing spinner SVG from `svg-icon-replacements.md` (inline spinner: `border-2 border-primary border-t-transparent rounded-full animate-spin`).
- **Progress feedback** (Priority 8): Show periodic toast updates during pipeline execution — "3/5 incelemeler etiketlendi" after each iteration. Use existing `setSaveToast` pattern with 4-second auto-dismiss.
- **Abort safety**: The pipeline must handle the case where the user navigates away mid-pipeline — check `currentIndex` hasn't changed between iterations and abort if it has.

### UAT Criteria
- [ ] `annotateAll()` fetches predictions for current review
- [ ] Filters by confidence >0.5 threshold
- [ ] Calls `addTriplet` for each high-confidence prediction
- [ ] Calls `saveAndNext()` after adding triplets
- [ ] Loops across N reviews (default 5)
- [ ] Stops early when no predictions available or no high-confidence predictions
- [ ] 500ms debounce between iterations
- [ ] All 87 frontend tests still pass
- [ ] 0 TS errors
- [ ] New hook/integration tests for pipeline behavior (4+ tests)

---

## Wave execution: Sequential

| Wave | Plans | Description | Dependencies |
|------|-------|-------------|--------------|
| **Wave 1** | Plan 2, Plan 3 | Frontend-only: keyboard shortcut + auto-suggest banner | None |
| **Wave 2** | Plan 1, Plan 4 | Template actions + AppActions wiring | None |
| **Wave 3** | Plan 5 | Backend: chat predictions endpoint | Plan 4 (action interface defined) |
| **Wave 4** | Plan 6 | Pipeline: annotateAll() | Plans 4, 5 (actions + endpoint) |

Each wave builds on the previous. Waves 1 and 2 could run in parallel if needed.

---

## Verification

After each wave, run:
```bash
# Backend tests
cd /path/to/AnnoABSA
python -m pytest tests/ -q --tb=short

# Frontend tests
cd frontend && NODE_ENV=development npx vitest run

# TypeScript check
NODE_ENV=development npx tsc --noEmit

# Build
NODE_ENV=development npx vite build
```

After full phase execution:
- **+16+ backend tests** (Plan 5 endpoint tests)
- **+4+ frontend tests** (Plan 4 + Plan 6 pipeline tests)
- All 209 existing backend tests still pass
- All 87 existing frontend tests still pass
- 0 TS errors
- Clean build
