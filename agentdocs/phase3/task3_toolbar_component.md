# Task 3: Frontend — NLP Helper Toolbar Component

## What this is

A collapsible floating toolbar (`NlpHelperToolbar.tsx`) that appears when text is selected in either Manuel or Karşılaştır mode. Collapsed state: a small SVG bag icon. Clicking it expands a 4-segment bar:

| Segment | Trigger | Action |
|---|---|---|
| 📖 Sözlük (Lexicon) | Auto on expand | `GET /nlp/lexicon-polarity?text=...` |
| 🤖 Duygu (Sentiment) | On click | `GET /nlp/sentiment?text=...` |
| 🔧 Yapı (Morphology) | On click | `GET /nlp/morphology?word=...` |
| 📊 Benzerlik (Similarity) | On click | `GET /nlp/embedding-similarity?selection=...&sentence=...` |

---

## Auto-vs-on-demand policy (confirmed)

- **Lexicon polarity** (SentiNet) — cheap, local dict lookup → **auto-fetches** when toolbar expands
- **Sentence sentiment** (BERT) — heavy model → **fetches on segment click**
- **Morphology** (NlpToolkit) — local, fast → **fetches on segment click** (consistent)
- **Embedding similarity** (e5-small) — heavy model → **fetches on segment click**

---

## Implementation steps

### Step 1 — Create `frontend/src/components/NlpHelperToolbar.tsx`

#### Component interface

```typescript
interface NlpHelperToolbarProps {
  selectedText: string;
  sentenceText?: string;
  anchorRect?: DOMRect | null;       // position anchor near selection
  onClose?: () => void;
}
```

#### State

```typescript
// Visual state
const [expanded, setExpanded] = useState(false);

// Per-segment state (indexed by segment id)
interface SegmentResult { loading: boolean; data: any; error: string | null }

const [lexiconResult, setLexiconResult] = useState<SegmentResult>({ loading: false, data: null, error: null });
const [sentimentResult, setSentimentResult] = useState<SegmentResult>({ loading: false, data: null, error: null });
const [morphologyResult, setMorphologyResult] = useState<SegmentResult>({ loading: false, data: null, error: null });
const [similarityResult, setSimilarityResult] = useState<SegmentResult>({ loading: false, data: null, error: null });
```

#### Keyboard & event handling

- `Escape` key → collapse toolbar
- Click outside → collapse toolbar (use `useEffect` with document-level `mousedown`)
- Abort in-flight requests on collapse via `AbortController` ref

#### Position logic

```typescript
// Anchor toolbar below the selection
const toolbarStyle: React.CSSProperties = useMemo(() => {
  if (!anchorRect) return { position: 'fixed', bottom: '60px', left: '16px' };  // fallback
  return {
    position: 'fixed',
    top: `${anchorRect.bottom + 8}px`,
    left: `${Math.min(anchorRect.left, window.innerWidth - 380)}px`,
    zIndex: 45,
  };
}, [anchorRect]);
```

#### API call helpers

```typescript
const backendUrl = import.meta.env?.VITE_BACKEND_URL || 'http://localhost:8000';
const abortRef = useRef<AbortController | null>(null);

async function fetchSegment(endpoint: string, params: Record<string, string>,
  setResult: (r: SegmentResult) => void) {
  // Abort any previous in-flight request for this segment
  if (abortRef.current) abortRef.current.abort();
  const controller = new AbortController();
  abortRef.current = controller;

  setResult({ loading: true, data: null, error: null });
  try {
    const query = new URLSearchParams(params).toString();
    const res = await fetch(`${backendUrl}${endpoint}?${query}`, {
      signal: controller.signal,
    });
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const data = await res.json();
    if (!controller.signal.aborted) {
      setResult({ loading: false, data, error: null });
    }
  } catch (e: any) {
    if (e.name === 'AbortError') return;
    if (!controller.signal.aborted) {
      setResult({ loading: false, data: null, error: e.message });
    }
  }
}
```

#### Auto-fetch lexicon on expand

```typescript
useEffect(() => {
  if (expanded && selectedText) {
    fetchSegment('/nlp/lexicon-polarity', { text: selectedText }, setLexiconResult);
  }
}, [expanded, selectedText]);
```

#### Segment rendering

Each segment is a clickable row/button:
```tsx
function SegmentButton({ emoji, label, loading, data, error, onClick }: SegmentButtonProps) {
  return (
    <button onClick={onClick} disabled={loading}
      className="flex items-center gap-2 w-full px-3 py-2 rounded-lg
        hover:bg-base-200 cursor-pointer transition-colors text-left
        disabled:opacity-60 disabled:cursor-wait"
    >
      <span className="text-base">{emoji}</span>
      <div className="flex-1 min-w-0">
        <div className="text-xs font-medium text-base-content">{label}</div>
        <div className="text-[10px] text-base-content/50 truncate">
          {loading && 'Yükleniyor…'}
          {error && `❌ ${error}`}
          {data && !loading && !error && <ResultDisplay data={data} />}
        </div>
      </div>
    </button>
  );
}
```

#### Layout markup

```tsx
return (
  <div style={toolbarStyle} ref={toolbarRef}
    className="bg-base-100/95 backdrop-blur-md border border-base-300 rounded-xl shadow-2xl
      min-w-[280px] max-w-[360px] overflow-hidden"
  >
    {!expanded ? (
      <button onClick={() => setExpanded(true)}
        className="p-2 hover:bg-base-200 rounded-xl transition-colors" title="NLP Araçları">
        {/* Bag SVG icon */}
        <svg className="w-5 h-5 text-base-content/70" ...>...</svg>
      </button>
    ) : (
      <div className="p-2 space-y-1">
        {/* Lexicon (auto-loaded) */}
        <SegmentButton emoji="📖" label="Sözlük"
          loading={lexiconResult.loading} data={lexiconResult.data} error={lexiconResult.error}
          onClick={() => {}}  /* already loaded */ />
        <div className="border-t border-base-300 my-1" />
        {/* Sentiment (on click) */}
        <SegmentButton emoji="🤖" label="Duygu Analizi"
          loading={sentimentResult.loading} data={sentimentResult.data} error={sentimentResult.error}
          onClick={() => fetchSegment('/nlp/sentiment', { text: selectedText }, setSentimentResult)} />
        {/* Morphology (on click) */}
        <SegmentButton emoji="🔧" label="Yapı Çözümleme"
          loading={morphologyResult.loading} data={morphologyResult.data} error={morphologyResult.error}
          onClick={() => fetchSegment('/nlp/morphology',
            { word: selectedText.split(/\s+/)[0] }, setMorphologyResult)} />
        {/* Similarity (on click) */}
        <SegmentButton emoji="📊" label="Benzerlik Karşılaştırması"
          loading={similarityResult.loading} data={similarityResult.data} error={similarityResult.error}
          onClick={() => {
            if (!sentenceText) return;
            fetchSegment('/nlp/embedding-similarity',
              { selection: selectedText, sentence: sentenceText }, setSimilarityResult);
          }} />
      </div>
    )}
  </div>
);
```

**→ verify: `npx tsc --noEmit` type-checks without errors**

### Step 2 — Result display renderer

Create a function to render each segment's response data:

```typescript
function ResultDisplay({ data }: { data: any }) {
  // Polarity lexicon
  if (data?.aggregate) {
    const pol = data.aggregate;
    const color = pol === 'positive' ? 'text-success'
      : pol === 'negative' ? 'text-error' : 'text-warning';
    return (
      <span className={color + ' font-bold'}>
        {pol === 'positive' ? '😊 Olumlu' : pol === 'negative' ? '😞 Olumsuz' : '😐 Nötr'}
        {' · '}
        {data.words?.filter((w: any) => w.polarity !== 'unknown').length || 0} kelime bulundu
      </span>
    );
  }
  // Sentiment
  if (data?.label) {
    const col = data.label === 'positive' ? 'text-success'
      : data.label === 'negative' ? 'text-error' : 'text-warning';
    return <span className={col + ' font-bold'}>{data.label} ({(data.score * 100).toFixed(0)}%)</span>;
  }
  // Morphology
  if (data?.parses) {
    return (
      <span>
        {data.parses.length} çözümleme · kök: {data.parses[0]?.root || '?'}
      </span>
    );
  }
  // Similarity
  if (data?.similarity !== undefined) {
    const pct = (data.similarity * 100).toFixed(0);
    return <span>Benzerlik: <strong>{pct}%</strong></span>;
  }
  return <span>Yanıt alındı</span>;
}
```

**→ verify:** Each segment type renders correctly when the component receives mock data

### Step 3 — Create `frontend/src/components/NlpHelperToolbar.test.tsx`

Component tests using Vitest + React Testing Library:

```typescript
import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { NlpHelperToolbar } from './NlpHelperToolbar';

// Mock fetch globally
const mockFetch = vi.fn();
global.fetch = mockFetch;

beforeEach(() => {
  mockFetch.mockReset();
});

describe('NlpHelperToolbar — collapsed state', () => {
  it('renders bag icon when collapsed', () => {
    render(<NlpHelperToolbar selectedText="güzel" />);
    // Should show a button (bag icon) — text shouldn't be visible
    const button = screen.getByRole('button');
    expect(button).toBeTruthy();
  });

  it('does not fetch anything on mount', () => {
    render(<NlpHelperToolbar selectedText="güzel" />);
    expect(mockFetch).not.toHaveBeenCalled();
  });
});

describe('NlpHelperToolbar — expanded state', () => {
  it('expands and auto-fetches lexicon on click', async () => {
    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: async () => ({
        words: [{ word: 'güzel', polarity: 'positive', score: 1.0 }],
        aggregate: 'positive',
      }),
    });
    render(<NlpHelperToolbar selectedText="güzel" />);
    // Click the collapsed button
    fireEvent.click(screen.getByRole('button'));
    // Wait for lexicon fetch
    await waitFor(() => {
      expect(screen.getByText(/Olumlu/)).toBeTruthy();
    });
    expect(mockFetch).toHaveBeenCalledWith(
      expect.stringContaining('/nlp/lexicon-polarity')
    );
  });

  it('fetches sentiment on click', async () => {
    mockFetch
      .mockResolvedValueOnce({ ok: true, json: async () => ({ aggregate: 'neutral' }) }) // lexicon
      .mockResolvedValueOnce({
        ok: true,
        json: async () => ({ label: 'positive', score: 0.95 }),
      }); // sentiment
    render(<NlpHelperToolbar selectedText="harika" />);
    fireEvent.click(screen.getByRole('button')); // expand
    await waitFor(() => expect(mockFetch).toHaveBeenCalledTimes(1)); // lexicon done
    // Click sentiment button
    fireEvent.click(screen.getByText('Duygu Analizi'));
    await waitFor(() => {
      expect(screen.getByText(/positive/)).toBeTruthy();
    });
    expect(mockFetch).toHaveBeenCalledWith(
      expect.stringContaining('/nlp/sentiment')
    );
  });
});

describe('NlpHelperToolbar — error handling', () => {
  it('shows error when lexicon fetch fails', async () => {
    mockFetch.mockRejectedValueOnce(new Error('Network error'));
    render(<NlpHelperToolbar selectedText="test" />);
    fireEvent.click(screen.getByRole('button'));
    await waitFor(() => {
      expect(screen.getByText(/Hata/)).toBeTruthy();
    });
  });

  it('collapses on Escape key', () => {
    render(<NlpHelperToolbar selectedText="test" />);
    fireEvent.click(screen.getByRole('button'));
    fireEvent.keyDown(document, { key: 'Escape' });
    // Should be collapsed again — only the icon button visible
    expect(screen.getByRole('button')).toBeTruthy();
  });
});
```

**→ verify: `npx vitest run frontend/src/components/NlpHelperToolbar.test.tsx` passes all tests**

### Step 4 — Mount in `PhraseAnnotator.tsx` (Manual mode)

In `PhraseAnnotator.tsx`, after the `pendingSelection` state is computed:

```tsx
// NLP Toolbar state
const [toolbarSelection, setToolbarSelection] = useState<{text: string; rect: DOMRect} | null>(null);

// Derive toolbar visibility from pending selection
useEffect(() => {
  if (pendingSelection) {
    // Get screen position from the DOM
    // We use a range-based approach since we know character indices
    const el = textContainerRef.current;
    if (el) {
      // approximate position: find the span containing pendingSelection.start
      const range = document.createRange();
      const textNode = el.firstChild;
      if (textNode) {
        range.setStart(textNode, pendingSelection.start);
        range.setEnd(textNode, pendingSelection.end + 1);
        const rect = range.getBoundingClientRect();
        setToolbarSelection({ text: pendingSelection.text, rect });
      }
    }
  } else {
    setToolbarSelection(null);
  }
}, [pendingSelection]);
```

⚠️ **Note:** Getting exact position from character indices in React-rendered spans is fragile because React splits text into multiple `<span>` elements. A simpler approach: use `window.getSelection()` in the `handleCharClick` callback:

```typescript
// In handleCharClick, after updating selection:
const sel = window.getSelection();
if (sel && sel.rangeCount > 0) {
  const rect = sel.getRangeAt(0).getBoundingClientRect();
  onSelectionChange?.(text, rect);
}
```

Add ref to the text container:
```tsx
const textContainerRef = useRef<HTMLDivElement>(null);

// Render the text with ref
<div ref={textContainerRef} className="text-base md:text-lg ...">
  {renderedRuns || reviewText}
</div>

// Toolbar
{toolbarSelection && (
  <NlpHelperToolbar
    selectedText={toolbarSelection.text}
    sentenceText={reviewText}
    anchorRect={toolbarSelection.rect}
    onClose={clearSelection}
  />
)}
```

### Step 5 — Mount in `ManualInputForm.tsx` (Compare mode)

Same pattern. Pass `onSelectionChange` callback as a prop.

**Prop added (already in Task 2 Step 4):**
```typescript
onSelectionChange?: (text: string, rect?: DOMRect) => void;
```

**In `ManualInputForm`, when selection changes:**
```typescript
const textContainerRef = useRef<HTMLDivElement>(null);

useEffect(() => {
  if (selStart !== null && selEnd !== null && onSelectionChange) {
    const text = reviewText.substring(selStart, selEnd + 1);
    // Get position
    const sel = window.getSelection();
    let rect: DOMRect | undefined;
    if (sel && sel.rangeCount > 0) {
      rect = sel.getRangeAt(0).getBoundingClientRect();
    }
    onSelectionChange(text, rect);
  }
}, [selStart, selEnd, reviewText, onSelectionChange]);
```

**In `App.tsx` — shared toolbar state for both modes:**
```tsx
const [nlpToolbarSelection, setNlpToolbarSelection] = useState<{
  text: string; sentence: string; rect?: DOMRect
} | null>(null);

// Render toolbar when selection exists (in both modes)
{nlpToolbarSelection && (
  <NlpHelperToolbar
    selectedText={nlpToolbarSelection.text}
    sentenceText={nlpToolbarSelection.sentence}
    anchorRect={nlpToolbarSelection.rect}
    onClose={() => setNlpToolbarSelection(null)}
  />
)}
```

**→ verify:** Select text in either mode → toolbar appears near the selection

### Step 6 — Verify dependency: `setuptools<75`

The NlpToolkit packages depend on `pkg_resources` from setuptools. Ensure `pyproject.toml` pins:
```
setuptools<75
```

Without this, the import chain `SentiNet → pkg_resources` fails silently on newer setuptools (83+). This is a critical install-time dependency — see `task1_backend_nlp_helpers.md` for full dependency list.

---

## Step-by-step verification (run in order)

| Step | Action | Expected result |
|---|---|---|
| 1 | Create `frontend/src/components/NlpHelperToolbar.tsx` | No TypeScript errors |
| 2 | Create `frontend/src/components/NlpHelperToolbar.test.tsx` | File exists |
| 3 | `npx vitest run frontend/src/components/NlpHelperToolbar.test.tsx` | All tests pass (collapsed state, expand + lexicon fetch, sentiment on click, error handling, Escape collapse) |
| 4 | Mount toolbar in `PhraseAnnotator.tsx` | No TypeScript errors |
| 5 | Add `onSelectionChange` prop to `ManualInputForm.tsx` + wire in `App.tsx` | No TypeScript errors |
| 6 | `cd frontend && npm run build` | Build succeeds |
| 7 | Start backend + frontend; open `localhost:3000` | No console errors |
| 8 | **Manual mode:** select text (click-click) | Small bag icon appears near the selection |
| 9 | **Manual mode:** click bag icon | Toolbar expands. "Sözlük" segment shows polarity (auto-fetched). Other 3 segments show their labels. |
| 10 | **Manual mode:** click "Duygu Analizi" | Spinner → sentiment label + score appears |
| 11 | **Manual mode:** click "Yapı Çözümleme" | Root word + POS tag appears |
| 12 | **Manual mode:** click "Benzerlik Karşılaştırması" | Similarity percentage appears |
| 13 | **Switch to Karşılaştır mode:** select center-column text | Same toolbar behavior (bag icon → expand → segments) |
| 14 | **Escape key** while expanded | Toolbar collapses |
| 15 | **Click outside** while expanded | Toolbar collapses |
| 16 | Select a **different** text span | Old toolbar collapses, new one appears at the new selection |
| 17 | Select text in **Model A or B column** | No toolbar appears (those columns don't use useTextSelection) |
| 18 | **Backend not running:** toolbar shows | Segments show ❌ Hata on click instead of hanging |
| 19 | Full production build: `cd frontend && npm run build` | No errors |

---

## Test cases to add to `tests/testcases.md`

### Add to Tier 2C (Text Selection)

| ID | Test | Expected | Verdict |
|---|---|---|---|
| TS7 | Toolbar bag icon visible after text selection in Manual mode | Small icon appears near selection | — |
| TS8 | Toolbar bag icon visible after text selection in Karşılaştır mode | Small icon appears near selection | — |
| TS9 | Click bag icon → toolbar expands | 4 segments visible; lexicon shows result immediately | — |

### Add as Tier 7B — NLP Helper Toolbar Frontend

| ID | Test | Expected | Verdict |
|---|---|---|---|
| NF1 | Click "Duygu Analizi" segment | Loading spinner → positive/negative label + confidence | — |
| NF2 | Click "Yapı Çözümleme" segment | Root word + POS + inflectional groups shown | — |
| NF3 | Click "Benzerlik Karşılaştırması" segment | Similarity score shown as percentage | — |
| NF4 | Escape key collapses toolbar | Toolbar disappears, text selection preserved | — |
| NF5 | Click outside toolbar collapses it | Same as Escape | — |
| NF6 | Select new text while toolbar is expanded | Old toolbar replaced, new one at new selection | — |
| NF7 | Toolbar when backend is offline | Each segment shows error state on click (no hang) | — |
| NF8 | Token selection vs click outside in ModelTripletColumn | Toolbar does NOT appear when clicking checkboxes | — |

---

## CSS to add

No global CSS changes needed. The component uses existing DaisyUI utility classes. If the toolbar overlaps with the floating chat panel (`.HelperAgentChatbox` at `bottom-16 right-4`), the toolbar should have a higher z-index (`zIndex: 45`) but lower than modals (`zIndex: 50`).

---

## Impact on existing test cases

**No existing test is expected to break.** The toolbar is an additive component — it does not change any existing behavior of PhraseAnnotator, ManualInputForm, ModelTripletColumn, or any endpoint. Run `pytest tests/` before and after — all 81 should pass.
