---
wave: 2
depends_on:
  - PLAN-01-Backend-Data-Loading
files_modified:
  - frontend/src/components/FourWayGrid.tsx (NEW)
  - frontend/src/components/CompactTripletChip.tsx (NEW)
  - frontend/src/components/ReviewHeader.tsx (NEW — extracted from ManualInputForm)
  - frontend/src/types.ts (extend ReviewComparisonData)
autonomous: false
requirements:
  - NEWUI-01: 2x2 grid + resolution panel layout
  - NEWUI-03: 2x2 Grid cards: GT, Gemma, Qwen, GPT in fixed positions
  - NEWUI-04: Consensus diamond at center intersection, color-coded by majority_vote
  - D-01: Narrow/compact triplet chips, all 4 columns visible at 1280px+
  - D-04: Review header unchanged at top
---

# Plan 2: Frontend — 2x2 Grid Component

**Phase:** 07.1-Compare-Mode-UI-Rework  
**Plan:** 2/5 — 2x2 grid with compact triplet chips, consensus diamond, and review header  
**Status:** Planned

---

## Overview

Create the core visual layout for 4-way Compare mode: a 2x2 grid of model columns (GT/Gemma/Qwen/GPT) with compact triplet chips instead of full cards, a consensus diamond at the center intersection, and an extracted ReviewHeader component reused from the top section of `ManualInputForm`.

**Layout (left ~70% of the page):**
```
┌──────────────────────────────────────────────┐
│           ReviewHeader (top bar)              │
├──────────────┬───────────────────────────────┤
│  GT (top-L)  │  Gemma (top-R)               │
│  ┌──────────┐│  ┌──────────┐                │
│  │ chip     ││  │ chip     │                │
│  │ chip     ││  │ chip     │                │
│  └──────────┘│  └──────────┘                │
│              │         ◆ (diamond at center) │
│  Qwen (bot-L)│  GPT   (bot-R)               │
│  ┌──────────┐│  ┌──────────┐                │
│  │ chip     ││  │ chip     │                │
│  └──────────┘│  └──────────┘                │
└──────────────┴───────────────────────────────┘
```

---

## must_haves

1. `FourWayGrid` component — renders 2x2 grid with 4 CompactTripletChip columns + consensus diamond
2. `CompactTripletChip` component — single-line triplet chip (~28-36px tall), inherits sentiment color scheme from existing `getSentimentStyle()`
3. `ReviewHeader` component — extracted review text display from ManualInputForm, standalone and reusable
4. Consensus diamond — colored border/fill by `majority_vote` value (3=green, 2=yellow, 1=red), shows integer value
5. All 4 columns visible at 1280px+ minimum (D-01)
6. Selection state pass-through: each column receives `selectedIds`, `onToggleSelect`, `onSelectAll`, `onClearAll`
7. Sentiment color badges on each chip using existing sentiment style pattern

---

## Tasks

### Task 2.1: Extend `ReviewComparisonData` interface in `types.ts`

<read_first>
Read `frontend/src/types.ts` lines 32-44 (ReviewComparisonData interface). Must add NEWUI fields as optional (`undefined` when not in 4-way mode).
</read_first>

<acceptance_criteria>
- [ ] Add the following optional fields to `ReviewComparisonData`:
  ```typescript
  gt_triplets?: TripletItem[];
  gemma_triplets?: TripletItem[];
  qwen_triplets?: TripletItem[];
  gpt_triplets?: TripletItem[];
  majority_vote?: number;    // 3, 2, or 1
  majority_label?: TripletItem[];
  consensus_intersection?: TripletItem[];
  original_llm_diff?: string;
  ```
- [ ] All fields optional — existing code referencing `.model_a_triplets` still compiles
- [ ] `majority_vote` type is `number` to allow `===` comparison for tier logic
- [ ] Update `Settings.compare_mode` to accept `'4way'`:
  ```typescript
  compare_mode: 'csv' | 'live' | '4way';
  ```
- [ ] Update `AppActions` interface:
  - `switchMode` signature unchanged (still `'compare' | 'manual'`)
  - `selectTriplet` needs `role` union extended: `'model_a' | 'model_b' | 'gt' | 'gemma' | 'qwen' | 'gpt'`
  - Same for `selectAllTriplets`, `clearAllTriplets`
  - `triggerLivePrediction` role union extended similarly
</acceptance_criteria>

<action>
1. Edit `frontend/src/types.ts`:
   - Add 8 new optional fields to `ReviewComparisonData` (lines 32-44)
   - Modify line 80: `compare_mode: 'csv' | 'live' | '4way'`
   - Modify lines 116-118: extend role union types to include `'gt' | 'gemma' | 'qwen' | 'gpt'`
   - Modify line 123: extend `triggerLivePrediction` role
</action>

---

### Task 2.2: Create `CompactTripletChip` component

<read_first>
Read `frontend/src/components/ModelTripletColumn.tsx` lines 130-176 (triplet rendering). The existing card is ~80-100px tall with aspect_term, sentiment badge, category label, and checkbox. The compact chip must be a single-line ~28-36px tall.
</read_first>

<acceptance_criteria>
- [ ] New file `frontend/src/components/CompactTripletChip.tsx`
- [ ] Props:
  ```typescript
  interface CompactTripletChipProps {
    triplet: TripletItem;
    isSelected: boolean;
    onToggle: (id: string) => void;
  }
  ```
- [ ] Renders as a single-line chip, ~28-36px tall:
  ```
  ◆ "aspect_term"   [SENTIMENT]   CATEGORY
  ```
- [ ] Uses existing `getSentimentStyle()` color scheme for the sentiment badge
- [ ] Clicking the chip toggles selection (same `Set<string>` pattern)
- [ ] Selected state: subtle colored left border + background tint
- [ ] Unselected state: transparent bg with muted border
- [ ] Diamond (◆) indicates selected state — filled with primary color when selected, outlined/border when not
- [ ] Tailwind classes: `flex items-center h-8 px-2 rounded-lg text-xs border transition-all cursor-pointer select-none gap-2 min-w-0`
- [ ] Aspect term truncates with `truncate` if too long
- [ ] Sentiment badge: `text-[10px] px-1.5 py-0.5 rounded-md border uppercase tracking-wider flex-shrink-0`
- [ ] Category: `text-[10px] text-base-content/50 font-mono truncate flex-shrink`
</acceptance_criteria>

<action>
1. Create `frontend/src/components/CompactTripletChip.tsx`:
```tsx
import React from 'react';
import { TripletItem } from '../types';

interface CompactTripletChipProps {
  triplet: TripletItem;
  isSelected: boolean;
  onToggle: (id: string) => void;
}

const getSentimentStyle = (polarity: string) => {
  const pol = polarity.toLowerCase();
  if (pol === 'positive' || pol === 'pos' || pol === 'olumlu') {
    return { text: 'text-success font-medium', badge: 'bg-success/10 text-success border-success/30' };
  } else if (pol === 'negative' || pol === 'neg' || pol === 'olumsuz') {
    return { text: 'text-error font-medium', badge: 'bg-error/10 text-error border-error/30' };
  }
  return { text: 'text-warning font-medium', badge: 'bg-warning/10 text-warning border-warning/30' };
};

export const CompactTripletChip: React.FC<CompactTripletChipProps> = ({ triplet, isSelected, onToggle }) => {
  const style = getSentimentStyle(triplet.sentiment_polarity);
  return (
    <div
      onClick={() => onToggle(triplet.id)}
      className={`flex items-center h-8 px-2 rounded-lg text-xs border transition-all cursor-pointer select-none gap-2 min-w-0 ${
        isSelected
          ? 'bg-primary/5 border-primary/40 shadow-sm'
          : 'bg-base-100/40 border-base-300/60 hover:border-base-200'
      }`}
    >
      <span className={`text-xs leading-none flex-shrink-0 ${isSelected ? 'text-primary' : 'text-base-content/30'}`}>◆</span>
      <span className="text-base-content font-medium truncate">"{triplet.aspect_term || 'NULL'}"</span>
      <span className={`text-[10px] px-1.5 py-0.5 rounded-md border uppercase tracking-wider flex-shrink-0 ${style.badge}`}>
        {triplet.sentiment_polarity}
      </span>
      <span className="text-[10px] text-base-content/40 font-mono truncate flex-shrink hidden sm:inline">
        {triplet.aspect_category}
      </span>
    </div>
  );
};
```
</action>

---

### Task 2.3: Create `ReviewHeader` component (extracted from ManualInputForm)

<read_first>
Read `frontend/src/components/ManualInputForm.tsx` lines 112-142 (review text display block). This is the top section with the "İnceleme Metni" label, edit button, translation toggle, and the review text content.
</read_first>

<acceptance_criteria>
- [ ] New file `frontend/src/components/ReviewHeader.tsx`
- [ ] Props:
  ```typescript
  interface ReviewHeaderProps {
    reviewText: string;
    translation?: string;
    onEditReview?: () => void;
  }
  ```
- [ ] Renders the review text display exactly as currently in ManualInputForm:
  - "İnceleme Metni (Raw Review)" label with animated dot
  - Review text in `text-lg md:text-xl` font
  - Translation toggle button (İngilizce Çeviri / Orijinali Göster)
  - Edit review button (SVG pencil icon)
- [ ] Does NOT include the form input controls (those move to resolution panel)
- [ ] Does NOT include the `renderedRuns` annotation overlay (not needed in compare mode)
- [ ] Uses same tailwind classes as current ManualInputForm header section
- [ ] Should be a thin bar, not full-card height — suitable for top-of-page placement
</acceptance_criteria>

<action>
1. Create `frontend/src/components/ReviewHeader.tsx`:
```tsx
import React, { useState } from 'react';

interface ReviewHeaderProps {
  reviewText: string;
  translation?: string;
  onEditReview?: () => void;
}

export const ReviewHeader: React.FC<ReviewHeaderProps> = ({ reviewText, translation, onEditReview }) => {
  const [showTranslation, setShowTranslation] = useState(false);
  return (
    <div className="bg-base-200/80 border border-base-300 rounded-xl p-3 mb-3 shadow-inner">
      <div className="flex items-center justify-between pb-1.5 mb-1.5 border-b border-base-300/80">
        <span className="text-xs font-bold text-base-content/60 uppercase tracking-wider flex items-center">
          <span className="w-2 h-2 rounded-full bg-primary mr-2 animate-pulse"></span>
          İnceleme Metni (Raw Review)
        </span>
        <div className="flex items-center gap-1">
          {onEditReview && (
            <button onClick={onEditReview}
              className="p-1 rounded-md bg-base-200 hover:bg-base-300 text-base-content/50 hover:text-primary transition-all border border-base-300"
              title="Metni Düzenle">
              <svg className="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z" />
              </svg>
            </button>
          )}
          {translation && (
            <button onClick={() => setShowTranslation(!showTranslation)}
              className="text-xs px-2 py-0.5 rounded bg-base-200 hover:bg-base-300 text-base-content/70 transition-colors border border-base-300">
              {showTranslation ? 'Orijinali Göster' : 'İngilizce Çeviri'}
            </button>
          )}
        </div>
      </div>
      <div className="text-base md:text-lg font-medium text-base-content leading-relaxed font-sans whitespace-pre-wrap">
        {showTranslation && translation ? translation : reviewText || "Metin bulunamadı."}
      </div>
    </div>
  );
};
```
</action>

---

### Task 2.4: Create `FourWayGrid` component

<read_first>
Read `frontend/src/components/ModelTripletColumn.tsx` lines 64-88 (column layout pattern — outer card, header with title+badge+select-all/clear-all). The FourWayGrid wraps 4 columns in a 2x2 grid with a consensus diamond at center intersection.
</read_first>

<acceptance_criteria>
- [ ] New file `frontend/src/components/FourWayGrid.tsx`
- [ ] Props:
  ```typescript
  interface FourWayGridProps {
    gtTriplets: TripletItem[];
    gemmaTriplets: TripletItem[];
    qwenTriplets: TripletItem[];
    gptTriplets: TripletItem[];
    majorityVote: number;  // 3, 2, or 1
    selectedIds: Record<string, Set<string>>;  // keyed by column id
    onToggleSelect: (column: string, id: string) => void;
    onSelectAll: (column: string) => void;
    onClearAll: (column: string) => void;
    modelNames: { gemma: string; qwen: string; gpt: string };
  }
  ```
- [ ] Layout: CSS grid `grid grid-cols-2 gap-2` with fixed positions:
  - Top-Left: GT (Ground Truth) column
  - Top-Right: Gemma column
  - Bottom-Left: Qwen column
  - Bottom-Right: GPT column
- [ ] Each column rendered very compactly:
  - Column header: title (small bold) + optional badge + select-all/clear-all
  - Triplet list: `CompactTripletChip` with `space-y-1` vertical gap
  - No full card borders per column — use `bg-base-200/50 rounded-lg p-2`
- [ ] **Consensus Diamond** (NEWUI-04):
  - Positioned at center intersection of the 4 columns (CSS: `absolute` centered at grid midpoint)
  - Diamond shape: use CSS transform `rotate(45deg)` on a square div, or SVG
  - Border/fill color by majority_vote:
    - 3 → `border-success` + `bg-success/20` (green — Tier 1)
    - 2 → `border-warning` + `bg-warning/20` (yellow — Tier 2)
    - 1 → `border-error` + `bg-error/20` (red — Tier 3)
  - Shows the `majority_vote` integer value centered in/on the diamond
  - Size: roughly 36x36px
  - z-index above grid columns but below interactive elements
  - CSS: `flex items-center justify-center` with the rotated container and counter-rotated text
- [ ] Column labels for each quadrant:
  - GT card: badge `bg-primary/10 text-primary border-primary/30`
  - Gemma card: badge `bg-secondary/10 text-secondary border-secondary/30`
  - Qwen card: badge `bg-accent/10 text-accent border-accent/30`
  - GPT card: badge `bg-info/10 text-info border-info/30`
- [ ] Empty state: when a column has 0 triplets, show "Bu model çıktı üretmedi" with tiny folder icon
- [ ] No overflow — scrollable per-column via `overflow-y-auto max-h-[300px] custom-scrollbar`
</acceptance_criteria>

<action>
1. Create `frontend/src/components/FourWayGrid.tsx` with the structure above
2. Key implementation details:
   - Use `relative` container with `grid grid-cols-2 gap-3` for the 4 columns
   - Wrap the entire grid in a relative div, position the consensus diamond with `absolute` at 50%/50%
   - Each column card:
     ```tsx
     <div className="bg-base-200/60 border border-base-300/80 rounded-xl p-2.5 shadow-sm flex flex-col min-h-0">
       <div className="flex items-center justify-between pb-1.5 border-b border-base-300/50 mb-1.5">
         <div className="flex items-center gap-1.5">
           <h4 className="text-xs font-bold">{title}</h4>
           <span className="text-[9px] px-1.5 py-0.5 rounded-full border {badgeColor}">{badgeText}</span>
         </div>
         {triplets.length > 0 && (
           <button onClick={allSelected ? clearAll : selectAll} className="text-[9px] px-1.5 py-0.5 rounded bg-base-200 hover:bg-base-300 text-base-content/60">
             {allSelected ? 'Temizle' : 'Hepsini Seç'}
           </button>
         )}
       </div>
       <div className="flex flex-col gap-1 overflow-y-auto max-h-[260px] custom-scrollbar pr-0.5">
         {triplets.map(t => (
           <CompactTripletChip key={t.id} triplet={t} isSelected={selectedIds[columnName]?.has(t.id) ?? false} onToggle={(id) => onToggleSelect(columnName, id)} />
         ))}
         {triplets.length === 0 && <div className="text-[10px] text-base-content/40 text-center py-4">Bu model çıktı üretmedi</div>}
       </div>
     </div>
     ```
   - Consensus diamond:
     ```tsx
     <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 z-10">
       <div className={`w-9 h-9 rotate-45 border-2 rounded-md flex items-center justify-center shadow-lg ${diamondColor}`}>
         <span className="-rotate-45 text-sm font-bold">{majorityVote}</span>
       </div>
     </div>
     ```
</action>

---

## Artifacts This Plan Produces

1. **`frontend/src/components/CompactTripletChip.tsx`** — New component for single-line chips
2. **`frontend/src/components/ReviewHeader.tsx`** — New standalone review header
3. **`frontend/src/components/FourWayGrid.tsx`** — New 2x2 grid panel
4. **`frontend/src/types.ts`** — Extended interfaces (ReviewComparisonData, Settings.compare_mode, AppActions roles)

---

## Verification

1. ✅ `FourWayGrid` renders 4 columns with correct GT/Gemma/Qwen/GPT labels
2. ✅ CompactTripletChip is ≤36px tall, shows term, sentiment badge, category
3. ✅ Consensus diamond visible at center, correct color for each majority_vote value
4. ✅ ReviewHeader displays current review text with translation toggle
5. ✅ All 4 columns visible at 1280px viewport width
6. ✅ Selection toggle works via click on any chip
7. ✅ Select-all/clear-all works per column

---

## PLANNING COMPLETE
