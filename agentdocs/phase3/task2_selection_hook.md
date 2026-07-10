# Task 2: Frontend — Shared Text Selection Hook

## What this is

Extract the character-level text selection logic from `PhraseAnnotator.tsx` into a shared React hook (`useTextSelection`), then use it in **both**:
- `PhraseAnnotator.tsx` (Manuel mode) — already has selection, adapt to use the hook
- `ManualInputForm.tsx` (Karşılaştır / Compare mode) — currently read-only plain `<p>`, needs clickable selection

---

## Current state

### `PhraseAnnotator.tsx` (lines 48-136)

Has inline selection state + handlers:
- `selStart`, `selEnd` — character index state (lines 53-54)
- `handleCharClick(charIndex)` — first click = start, second = end, third = reset (lines 63-78)
- `pending`, `pendingFromSelection` — computed annotation from selection (lines 80-88)
- Token boundary detection via `getTokenBounds(text, charIndex)` (lines 27-34)
- Phrase cleaning via `getCleanedPositions(start, end, text, clean)` (lines 40-46)
- Visual rendering: character-level `<span>` elements with highlighting (lines 138-187)

### `ManualInputForm.tsx` (lines 82-84)

Review text is rendered as a plain `<p>`:
```tsx
<p className="text-lg md:text-xl font-medium ...">
  {showTranslation && translation ? translation : reviewText || "Metin bulunamadı."}
</p>
```
No click/selection handling at all. The compare mode has no selection mechanism.

---

## Implementation steps

### Step 1 — Create `frontend/src/hooks/useTextSelection.ts`

```typescript
interface PendingSelection {
  start: number;
  end: number;
  text: string;
}

interface TextSelectionState {
  selStart: number | null;
  selEnd: number | null;
  selectedText: string;
  pendingSelection: PendingSelection | null;
}

interface TextSelectionActions {
  handleCharClick: (charIndex: number) => void;
  clearSelection: () => void;
}

/**
 * Character-level text selection hook.
 *
 * Click cycle: first click sets start, second click sets end,
 * third click resets. Supports token snapping and phrase cleaning.
 *
 * @param reviewText - The full text being selected from
 * @param options.clickOnToken - Snap to word boundaries (default: true)
 * @param options.autoCleanPhrases - Strip punctuation from selection (default: true)
 */
function useTextSelection(
  reviewText: string,
  options?: { clickOnToken?: boolean; autoCleanPhrases?: boolean }
): [TextSelectionState, TextSelectionActions]
```

**Implementation details:**

The hook should contain:
- `getTokenBounds(text, charIndex)` — snap char index to nearest word boundary
- `getCleanedPositions(start, end, text, clean)` — strip leading/trailing punctuation
- `cleanPhrase(p)` — punctuation cleanup helper
- Internal state: `selStart`, `selEnd`, `prevEndRef` (for change detection)
- `handleCharClick(charIndex)` — 3-state click machine
- `pendingSelection` — computed via `useMemo` from selStart/selEnd

**→ verify:** Extract these pure functions with no React dependencies, then test them standalone:

```typescript
// Pure functions (can test without React)
export function getTokenBounds(text: string, ci: number): { start: number; end: number }
export function cleanPhrase(p: string): string
export function getCleanedPositions(os: number, oe: number, txt: string, clean: boolean): { start: number; end: number }
```

### Step 2 — Create `frontend/src/hooks/useTextSelection.test.ts`

New test file using Vitest (matching the Vite-based project setup).

```typescript
import { describe, it, expect } from 'vitest';
import { getTokenBounds, cleanPhrase, getCleanedPositions } from './useTextSelection';

describe('getTokenBounds', () => {
  it('returns full word boundaries for middle of word', () => {
    const { start, end } = getTokenBounds('güzel yemek', 3);
    expect(start).toBe(0);
    expect(end).toBe(4);
  });

  it('returns single char for punctuation', () => {
    const { start, end } = getTokenBounds('güzel,', 5);  // comma
    expect(start).toBe(5);
    expect(end).toBe(5);
  });

  it('handles first char of text', () => {
    const { start, end } = getTokenBounds('Merhaba dünya', 0);
    expect(start).toBe(0);
    expect(end).toBe(6);
  });

  it('handles last char of text', () => {
    const { start, end } = getTokenBounds('hello world', 10);
    expect(start).toBe(6);
    expect(end).toBe(10);
  });

  it('handles empty text gracefully', () => {
    const r = getTokenBounds('', 0);
    expect(r.start).toBe(0);
    expect(r.end).toBe(0);
  });
});

describe('cleanPhrase', () => {
  it('strips leading punctuation', () => {
    expect(cleanPhrase('"güzel"')).toBe('güzel');
  });

  it('strips trailing punctuation', () => {
    expect(cleanPhrase('güzel!')).toBe('güzel');
  });

  it('strips both sides', () => {
    expect(cleanPhrase('(güzel)')).toBe('güzel');
  });

  it('leaves clean text unchanged', () => {
    expect(cleanPhrase('güzel')).toBe('güzel');
  });

  it('handles Turkish characters', () => {
    expect(cleanPhrase('«şahane»')).toBe('şahane');
  });
});

describe('getCleanedPositions', () => {
  it('returns original positions when no cleaning needed', () => {
    const r = getCleanedPositions(0, 5, 'güzel yemek', true);
    expect(r.start).toBe(0);
    expect(r.end).toBe(5);
  });

  it('adjusts positions when leading punctuation stripped', () => {
    // text: '"güzel" yemek', positions 0-6 → '"güzel"'
    // cleaned: 'güzel' → positions 1-5
    const r = getCleanedPositions(0, 6, '"güzel" yemek', true);
    expect(r.start).toBe(1);
    expect(r.end).toBe(5);
  });

  it('returns original when autoCleanPhrases is false', () => {
    const r = getCleanedPositions(0, 6, '"güzel" yemek', false);
    expect(r.start).toBe(0);
    expect(r.end).toBe(6);
  });
});
```

**→ verify: `npx vitest run frontend/src/hooks/useTextSelection.test.ts` passes all tests**

### Step 3 — Refactor `PhraseAnnotator.tsx`

Replace inline selection state + handlers with the hook:

**Change checklist:**
- [ ] Remove: `selStart` state (line 53)
- [ ] Remove: `selEnd` state (line 54)
- [ ] Remove: `handleCharClick` function (lines 63-78)
- [ ] Remove: `pendingFromSelection` useMemo (lines 80-88)
- [ ] Remove: `getTokenBounds` function (lines 27-34)
- [ ] Remove: `cleanPhrase` function (lines 36-38)
- [ ] Remove: `getCleanedPositions` function (lines 40-46)
- [ ] Remove: imported `useMemo` if no longer used elsewhere
- [ ] Add: `import { useTextSelection } from '../hooks/useTextSelection';`
- [ ] Add: `const [{ selStart, selEnd, pendingSelection }, { handleCharClick, clearSelection }] = useTextSelection(reviewText, { clickOnToken, autoCleanPhrases });`
- [ ] Keep: `pending` state — derive from `pendingSelection` (hook signals, component manages form)
- [ ] Keep: annotation form popup, handleAdd, handleCancel, triplet rendering, color highlighting
- [ ] Keep: `renderedRuns` useMemo — still uses `selStart`/`selEnd` from hook

**The `pending` state bridge:**
```typescript
const [pendingFormState, setPendingFormState] = useState<PendingAnnotation | null>(null);

// Bridge: hook's pendingSelection → component's form state
const prevSelectionRef = useRef<PendingSelection | null>(null);
useEffect(() => {
  if (pendingSelection && pendingSelection !== prevSelectionRef.current) {
    setPendingFormState({
      start: pendingSelection.start,
      end: pendingSelection.end,
      text: pendingSelection.text,
    });
    // Reset form fields
    setFormAspectTerm(pendingSelection.text);
    // ...
    prevSelectionRef.current = pendingSelection;
  }
}, [pendingSelection]);
```

**→ verify:** Click a character → first click shows "Başlangıç:N", second click shows "[N-M]" range and opens popup. Third click resets. **Same behavior as before the refactor.**

### Step 4 — Update `ManualInputForm.tsx` (read-only selection)

Replace the plain `<p>` with character-level clickable spans. **No popup, no form, no save.**

**Props to add to `ManualInputFormProps`:**
```typescript
interface ManualInputFormProps {
  // ... existing props ...
  clickOnToken?: boolean;          // for selection snapping
  onSelectionChange?: (text: string, rect?: DOMRect) => void;  // for NLP toolbar (Task 3)
}
```

**Rendered text implementation:**
```tsx
const [{ selStart, selEnd }, { handleCharClick, clearSelection }] = useTextSelection(
  reviewText,
  { clickOnToken: true, autoCleanPhrases: true }
);

// Build character-level runs (same pattern as PhraseAnnotator lines 138-187)
const renderedRuns = useMemo(() => {
  if (!reviewText) return null;
  const n = reviewText.length;
  // Build bg/class arrays for selection highlight
  const bg: (string | null)[] = new Array(n).fill(null);
  const cls: string[] = new Array(n).fill('');
  if (selStart !== null) {
    const effE = selEnd ?? selStart;
    for (let i = selStart; i <= effE && i < n; i++) {
      bg[i] = 'rgba(59,130,246,0.4)';
      cls[i] = 'ring-1 ring-primary/60';
    }
  }
  // Merge into runs
  const runs: { start: number; end: number; bg: string | null; cls: string }[] = [];
  let i = 0;
  while (i < n) {
    const curBg = bg[i];
    const curCls = cls[i];
    const start = i;
    while (i < n && bg[i] === curBg && cls[i] === curCls) i++;
    runs.push({ start, end: i - 1, bg: curBg, cls: curCls });
  }
  return runs.map((r) => (
    <span
      key={r.start}
      onClick={() => handleCharClick(r.start)}
      className={`cursor-pointer select-none rounded-sm ${r.bg ? r.cls : 'hover:bg-primary/20'}`}
      style={r.bg ? { backgroundColor: r.bg } : undefined}
    >
      {reviewText.slice(r.start, r.end + 1)}
    </span>
  ));
}, [reviewText, selStart, selEnd, handleCharClick]);
```

Replace the old `<p>`:
```tsx
{/* OLD: <p className="text-lg ...">{reviewText}</p> */}
{/* NEW: */}
<div className="text-lg md:text-xl font-medium text-base-content leading-relaxed font-sans select-none whitespace-pre-wrap">
  {renderedRuns || reviewText}
</div>
```

**→ verify:** Compare mode text is now clickable — first click highlights start, second click highlights range with blue overlay.

### Step 5 — Wire `onSelectionChange` callback (for Task 3)

In `ManualInputForm.tsx`, notify parent component when selection changes:
```tsx
useEffect(() => {
  if (onSelectionChange) {
    if (selStart !== null && selEnd !== null) {
      const text = reviewText.substring(selStart, selEnd + 1);
      onSelectionChange(text);
    } else {
      onSelectionChange('');
    }
  }
}, [selStart, selEnd, reviewText, onSelectionChange]);
```

In `App.tsx`, pass the callback:
```tsx
<ManualInputForm
  reviewText={currentData.review_text}
  // ... existing props ...
  clickOnToken={settings.click_on_token}
  onSelectionChange={(text) => {
    if (text) {
      setNlpToolbarSelection({ text, sentence: currentData.review_text });
    } else {
      setNlpToolbarSelection(null);
    }
  }}
/>
```

---

## Step-by-step verification (run in order)

| Step | Action | Expected result |
|---|---|---|
| 1 | Create `frontend/src/hooks/useTextSelection.ts` with pure functions + hook | File compiles: `npx tsc --noEmit` passes |
| 2 | `npx vitest run frontend/src/hooks/useTextSelection.test.ts` | All unit tests pass (8 tests for getTokenBounds, 5 for cleanPhrase, 3 for getCleanedPositions) |
| 3 | Refactor `PhraseAnnotator.tsx` — replace inline selection with hook | No TypeScript errors |
| 4 | Build frontend: `cd frontend && npm run build` | Build succeeds without errors |
| 5 | Start backend + frontend; open `localhost:3000` in Manual mode | ✅ Same baseline behavior — browser console shows no errors |
| 6 | Manual mode: click two characters in review text | First click: "Başlangıç:N", second click: "[N-M]" range + popup appears (MA1, MA2 from testcases) |
| 7 | Manual mode: save a triplet, add another, delete one | MA3, MA4, MA5 all work as documented in testcases |
| 8 | Switch to Karşılaştır mode | Three-column layout renders, no TypeScript errors |
| 9 | Compare mode: click characters in center-column review text | Text highlights with blue overlay; no annotation popup appears |
| 10 | Compare mode: click a Model A / Model B triplet checkbox | Checkbox toggles independently — text selection above it unaffected |
| 11 | Compare mode: select text, switch mode to Manuel, switch back | Selection resets (expected — mode change re-renders components) |
| 12 | Row navigation: ◀ ▶ | Unchanged — same baseline behavior |
| 13 | `npm run build` (full production build) | Succeeds with no warnings |

---

## Test cases to add to `tests/testcases.md`

### Add to Tier 2A (Manuel mode)

| ID | Test | Expected | Verdict |
|---|---|---|---|
| MA7 | Selection via hook (refactored) | Same behavior as MA1–MA4 after hook extraction | — |

### Add to Tier 2C (Text Selection — new subtier)

| ID | Test | Expected | Verdict |
|---|---|---|---|
| TS1 | Karşılaştır mode: single click on review text | Character highlighted, no popup | — |
| TS2 | Karşılaştır mode: two clicks on review text | Range highlighted with blue overlay | — |
| TS3 | Karşılaştır mode: third click | Selection cleared | — |
| TS4 | Token snapping works in Karşılaştır mode | Clicking in middle of word selects full word | — |
| TS5 | Selection clears on row navigation | New row has no active selection | — |
| TS6 | Selection in Karşılaştır mode does NOT toggle model checkboxes | Checkbox state unchanged | — |

---

## Impact on existing test cases

**No existing test is expected to break.** The refactored `PhraseAnnotator` exposes the same click behavior through the hook. Run `pytest tests/` before and after — all 81 should pass. Run manual walkthrough (MA1–MA6) to confirm visual behavior is identical.
