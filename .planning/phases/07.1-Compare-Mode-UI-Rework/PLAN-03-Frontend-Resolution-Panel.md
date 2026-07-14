---
wave: 2
depends_on:
  - PLAN-02-Frontend-2x2-Grid
files_modified:
  - frontend/src/components/ResolutionPanel.tsx (NEW)
  - frontend/src/components/ResolutionPanel.test.tsx (NEW)
autonomous: false
requirements:
  - NEWUI-05: Resolution panel with Primary Suggestion Box and Diff Tracker Box
  - NEWUI-06: Tier 1 Auto-Accept logic (green, majority_vote ≥ 2 AND majority_label == original_label)
  - NEWUI-07: Tier 2 Quick Diff logic (yellow, majority_vote ≥ 2 AND majority_label != original_label)
  - NEWUI-08: Tier 3 High-Confusion manual review logic (red, majority_vote == 1)
  - NEWUI-09: Action buttons (accept, edit, manual)
  - D-02: Resolution panel fixed right side, grid ~70%, panel ~30%
  - D-09: Tier 1 pre-selects GT triplets
  - D-10: Tier 2 Diff Tracker, user picks
  - D-11: Tier 3 shows all 4 models, manual review
---

# Plan 3: Frontend — Resolution Panel

**Phase:** 07.1-Compare-Mode-UI-Rework  
**Plan:** 3/5 — Resolution panel with 3-tier curation logic, Primary Suggestion Box, Diff Tracker, action buttons  
**Status:** Planned

---

## Overview

Create the Resolution Panel component that sits on the right ~30% of the 4-way Compare layout. It contains:

1. **Primary Suggestion Box** — Shows the recommended action based on tier (Auto-Accept, Quick Diff, Manual Review)
2. **Diff Tracker Box** — Shows comparison data (side-by-side diff for Tier 2, "all 4 models displayed" for Tier 3)
3. **Action buttons** — Accept suggestion, Edit manually, Manual triplet entry form (Tier 3 only)
4. **3-tier logic** — Color-coded state machine driven by `majority_vote` and `majority_label == original_label`

---

## must_haves

1. Resolution Panel is fixed right side, ~30% width (D-02)
2. Three distinct visual states matching 3 curation tiers
3. Primary Suggestion Box shows recommendation with tier-appropriate messaging
4. Diff Tracker Box shows majority_label (Tier 1/2) or "all 4 models visible" (Tier 3)
5. Action buttons: [Accept] [Edit] [Manual] with tier-appropriate defaults
6. Manual triplet entry form embedded in panel (for when user needs to add/correct triplets)
7. Color-coded header bar matching consensus diamond (green/yellow/red)
8. No overlap with NLP toolbar or floating chat (NEWUI-10)

---

## Tasks

### Task 3.1: Create `ResolutionPanel` component with tier logic

<read_first>
Read `frontend/src/components/ManualInputForm.tsx` lines 145-224 (form section with aspect term input, category dropdown, sentiment buttons, and manual triplet list). This form will be reused in the resolution panel for manual entry.
</read_first>

<acceptance_criteria>
- [ ] New file `frontend/src/components/ResolutionPanel.tsx`
- [ ] Props:
  ```typescript
  interface ResolutionPanelProps {
    majorityVote: number;           // 3, 2, or 1
    majorityLabel: TripletItem[];   // majority triplets to suggest
    gtTriplets: TripletItem[];      // Ground Truth triplets (for Tier 1 auto-accept)
    consensusIntersection: TripletItem[];
    originalLlmDiff: string;        // Diff description text
    categories: string[];
    polarities: string[];
    manualTriplets: TripletItem[];
    onAddTriplet: (triplet: TripletItem) => void;
    onRemoveTriplet: (id: string) => void;
    onAcceptSuggestion: (triplets: TripletItem[]) => void;
    onEditTriplets: () => void;
  }
  ```
- [ ] **Tier detection logic** (internal derived state):
  ```typescript
  const tier = majorityVote >= 2
    ? (gtTripletsEq ? 1 : 2)  // Tier 1 if majority_label matches GT, else Tier 2
    : 3;                       // Tier 3 if majorityVote == 1
  ```
  Where `gtTripletsEq` is a deep-equality check of `majorityLabel` vs `gtTriplets`
- [ ] **Panel layout** (≈30% width, full height card):
  ```
  ┌─────────────────────────────┐
  │  Resolution Panel           │
  │  ┌───────────────────────┐  │
  │  │ Primary Suggestion    │  │  ← tier header + recommendation
  │  └───────────────────────┘  │
  │  ┌───────────────────────┐  │
  │  │ Diff Tracker          │  │  ← side-by-side or text
  │  └───────────────────────┘  │
  │  ┌───────────────────────┐  │
  │  │ Action Buttons        │  │  ← accept / edit / manual
  │  └───────────────────────┘  │
  │  ┌───────────────────────┐  │
  │  │ Manual Form (cond.)   │  │  ← entry form + manual triplets
  │  └───────────────────────┘  │
  └─────────────────────────────┘
  ```
- [ ] **Tier 1 — Auto-Accept (green)**:
  - Header: `bg-success/10 border-success/30` with ✅ icon
  - Primary Suggestion: "Auto-Accept: GT triplets match majority consensus"
  - Diff Tracker: Shows `majority_label` with green badge "Tüm modeller uyumlu"
  - Pre-selected action: Accept suggestion (pre-selects GT triplets — D-09)
  - Action buttons: [Accept ✅] (primary) [Edit ✏️] (secondary)
- [ ] **Tier 2 — Quick Diff (yellow)**:
  - Header: `bg-warning/10 border-warning/30` with ⚠️ icon
  - Primary Suggestion: "Consensus found but differs from GT — verify"
  - Diff Tracker: Shows side-by-side comparison of `majority_label` vs `gt_triplets`
    - `original_llm_diff` string displayed in a styled text block
    - List majority_label triplets on left, gt triplets on right
  - Action buttons: [Accept Majority ⬡] (warning) [Keep GT 🛡] (secondary) [Edit ✏️] (secondary)
- [ ] **Tier 3 — High-Confusion (red)**:
  - Header: `bg-error/10 border-error/30` with ✋ icon
  - Primary Suggestion: "No consensus — manual review required"
  - Diff Tracker: Shows message "Tüm 4 model çıktısı yukarıdaki ızgarada görünüyor. Lütfen doğru tripletleri seçin."
  - Action buttons: [Manual Entry ✏️] (primary) — opens inline manual form
  - Manual form appears inline (reusing ManualInputForm's form pattern with aspect_term, category, sentiment)
</acceptance_criteria>

<action>
1. Create `frontend/src/components/ResolutionPanel.tsx`:
```tsx
import React, { useState, useMemo } from 'react';
import { TripletItem } from '../types';

interface ResolutionPanelProps {
  majorityVote: number;
  majorityLabel: TripletItem[];
  gtTriplets: TripletItem[];
  consensusIntersection: TripletItem[];
  originalLlmDiff: string;
  categories: string[];
  polarities: string[];
  manualTriplets: TripletItem[];
  onAddTriplet: (triplet: TripletItem) => void;
  onRemoveTriplet: (id: string) => void;
  onAcceptSuggestion: (triplets: TripletItem[]) => void;
  onEditTriplets: () => void;
}

type Tier = 1 | 2 | 3;

export const ResolutionPanel: React.FC<ResolutionPanelProps> = ({
  majorityVote, majorityLabel, gtTriplets, consensusIntersection,
  originalLlmDiff, categories, polarities,
  manualTriplets, onAddTriplet, onRemoveTriplet,
  onAcceptSuggestion, onEditTriplets,
}) => {
  const [showManualForm, setShowManualForm] = useState(false);
  const [aspectTerm, setAspectTerm] = useState('');
  const [category, setCategory] = useState(categories[0] || 'RESTAURANT#GENERAL');
  const [sentiment, setSentiment] = useState('positive');

  // Deep compare majority_label vs gt_triplets
  const gtMatchesMajority = useMemo(() => {
    if (majorityLabel.length !== gtTriplets.length) return false;
    const normalize = (t: TripletItem) => `${t.aspect_term}|${t.aspect_category}|${t.sentiment_polarity}`;
    const mlSet = new Set(majorityLabel.map(normalize));
    return gtTriplets.every(t => mlSet.has(normalize(t)));
  }, [majorityLabel, gtTriplets]);

  const tier: Tier = majorityVote >= 2 ? (gtMatchesMajority ? 1 : 2) : 3;

  const tierConfig = {
    1: { border: 'border-success/30', bg: 'bg-success/5', header: 'bg-success/10 border-success/30', icon: '✅', title: 'Auto-Accept', text: 'GT triplets match majority consensus' },
    2: { border: 'border-warning/30', bg: 'bg-warning/5', header: 'bg-warning/10 border-warning/30', icon: '⚠️', title: 'Quick Diff', text: 'Consensus found but differs from GT — verify' },
    3: { border: 'border-error/30', bg: 'bg-error/5', header: 'bg-error/10 border-error/30', icon: '✋', title: 'Manual Review', text: 'No consensus — manual review required' },
  };

  const tc = tierConfig[tier];

  const handleManualSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    const term = aspectTerm.trim() || 'NULL';
    onAddTriplet({
      id: `res_${Date.now()}_${Math.random().toString(36).substring(2, 6)}`,
      aspect_term: term,
      aspect_category: category,
      sentiment_polarity: sentiment,
      isSelected: true,
    });
    setAspectTerm('');
  };

  return (
    <div className={`flex flex-col h-full rounded-2xl border ${tc.border} ${tc.bg} p-3 shadow-xl backdrop-blur-sm overflow-hidden`}>
      {/* Tier header */}
      <div className={`flex items-center gap-2 px-3 py-2 rounded-xl border ${tc.header} mb-2`}>
        <span className="text-sm">{tc.icon}</span>
        <div>
          <div className="text-xs font-bold">{tc.title}</div>
          <div className="text-[10px] text-base-content/70">{tc.text}</div>
        </div>
      </div>

      {/* Primary Suggestion Box */}
      <div className="bg-base-200/80 border border-base-300/80 rounded-xl p-3 mb-2">
        <div className="text-[10px] font-bold text-base-content/60 uppercase tracking-wider mb-1">Primary Suggestion</div>
        {tier === 1 && (
          <div className="text-xs text-success font-medium">✅ GT triplets pre-selected — save to accept</div>
        )}
        {tier === 2 && (
          <div className="text-xs text-warning font-medium">⚠️ Majority differs from GT — review diff</div>
        )}
        {tier === 3 && (
          <div className="text-xs text-error font-medium">✋ Review all 4 models in grid, select correct triplets</div>
        )}
      </div>

      {/* Diff Tracker Box */}
      <div className="bg-base-200/80 border border-base-300/80 rounded-xl p-3 mb-2 flex-1 overflow-y-auto">
        <div className="text-[10px] font-bold text-base-content/60 uppercase tracking-wider mb-1.5">Diff Tracker</div>
        {tier === 1 && (
          <div className="text-xs text-success space-y-1">
            <span className="text-[10px] bg-success/10 px-1.5 py-0.5 rounded border border-success/30">Tüm modeller uyumlu</span>
            {majorityLabel.map(t => (
              <div key={t.id} className="flex items-center gap-1 text-[11px]">
                <span>◆</span> "{t.aspect_term}" <span className="text-[10px] opacity-60">{t.sentiment_polarity}</span>
              </div>
            ))}
          </div>
        )}
        {tier === 2 && (
          <div className="text-xs space-y-1.5">
            {originalLlmDiff && (
              <div className="text-[10px] bg-base-300/50 p-2 rounded border border-base-300 font-mono text-base-content/70 leading-relaxed">
                {originalLlmDiff}
              </div>
            )}
            <div className="grid grid-cols-2 gap-2 mt-1.5">
              <div>
                <div className="text-[9px] text-warning font-bold uppercase mb-0.5">Majority</div>
                {majorityLabel.map(t => (
                  <div key={t.id} className="text-[10px] text-base-content/80 truncate">◆ {t.aspect_term}</div>
                ))}
              </div>
              <div>
                <div className="text-[9px] text-primary font-bold uppercase mb-0.5">GT (Original)</div>
                {gtTriplets.map(t => (
                  <div key={t.id} className="text-[10px] text-base-content/80 truncate">◆ {t.aspect_term}</div>
                ))}
              </div>
            </div>
          </div>
        )}
        {tier === 3 && (
          <div className="text-[11px] text-base-content/60 leading-relaxed">
            Tüm 4 model çıktısı yukarıdaki ızgarada görünüyor. Lütfen doğru tripletleri seçin.
          </div>
        )}
      </div>

      {/* Action Buttons */}
      <div className="flex flex-col gap-1.5 mb-2">
        {tier === 1 && (
          <>
            <button onClick={() => onAcceptSuggestion(gtTriplets)} className="w-full py-2 px-3 bg-success hover:bg-success/90 text-success-content font-bold rounded-lg text-xs transition-all shadow-sm">✅ Kabul Et (Auto-Accept)</button>
            <button onClick={onEditTriplets} className="w-full py-1.5 px-3 bg-base-200 hover:bg-base-300 text-base-content/70 rounded-lg text-[10px] transition-all border border-base-300">✏️ Düzenle</button>
          </>
        )}
        {tier === 2 && (
          <>
            <button onClick={() => onAcceptSuggestion(majorityLabel)} className="w-full py-2 px-3 bg-warning hover:bg-warning/90 text-warning-content font-bold rounded-lg text-xs transition-all shadow-sm">⚠️ Majority Kabul Et</button>
            <button onClick={() => onAcceptSuggestion(gtTriplets)} className="w-full py-1.5 px-3 bg-primary hover:bg-primary/90 text-primary-content font-bold rounded-lg text-xs transition-all shadow-sm">🛡 GT'yi Koru</button>
            <button onClick={onEditTriplets} className="w-full py-1.5 px-3 bg-base-200 hover:bg-base-300 text-base-content/70 rounded-lg text-[10px] transition-all border border-base-300">✏️ Düzenle</button>
          </>
        )}
        {tier === 3 && (
          <>
            <button onClick={() => setShowManualForm(!showManualForm)} className="w-full py-2 px-3 bg-error hover:bg-error/90 text-error-content font-bold rounded-lg text-xs transition-all shadow-sm">
              {showManualForm ? '📋 Formu Gizle' : '✏️ Manuel Giriş'}
            </button>
          </>
        )}
      </div>

      {/* Manual Entry Form (Tier 3 or toggled) */}
      {((tier === 3) || showManualForm) && (
        <div className="border-t border-base-300 pt-2">
          <form onSubmit={handleManualSubmit} className="space-y-2 bg-base-300/50 p-2.5 rounded-xl border border-base-300/80">
            <input type="text" value={aspectTerm} onChange={e => setAspectTerm(e.target.value)}
              placeholder="Aspect term" className="w-full bg-base-200 border border-base-300 rounded-lg px-2 py-1 text-xs focus:outline-none focus:border-primary" />
            <div className="grid grid-cols-2 gap-1.5">
              <select value={category} onChange={e => setCategory(e.target.value)}
                className="bg-base-200 border border-base-300 rounded-lg px-1.5 py-1 text-[10px] focus:outline-none focus:border-primary">
                {categories.map(c => <option key={c} value={c}>{c}</option>)}
              </select>
              <div className="flex gap-1">
                {polarities.map(p => (
                  <button key={p} type="button" onClick={() => setSentiment(p.toLowerCase())}
                    className={`flex-1 py-1 rounded-lg text-[10px] font-bold border ${sentiment === p.toLowerCase() ? 'bg-primary/20 text-primary border-primary/30' : 'border-base-300 text-base-content/50'}`}>
                    {p === 'positive' ? '+P' : p === 'negative' ? '-N' : '=N'}
                  </button>
                ))}
              </div>
            </div>
            <button type="submit" className="w-full py-1.5 bg-primary hover:bg-primary/90 text-primary-content font-bold rounded-lg text-[10px] transition-all">+ Triplet Ekle</button>
          </form>
          {manualTriplets.length > 0 && (
            <div className="mt-2 space-y-1 max-h-[120px] overflow-y-auto">
              {manualTriplets.map(t => (
                <div key={t.id} className="flex items-center justify-between bg-base-300 p-1.5 rounded-lg border border-base-300/80 text-[10px]">
                  <span>"{(t.aspect_term || 'NULL')}"</span>
                  <button onClick={() => onRemoveTriplet(t.id)} className="text-base-content/40 hover:text-error">✕</button>
                </div>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
};
```
</action>

---

### Task 3.2: Create `ResolutionPanel.test.tsx`

<read_first>
Read `frontend/src/components/ModelTripletColumn.test.tsx` (vitest test pattern — render with `createRoot` + `flushSync`, `findByText`, `click()` — React 19 CJS compat pattern).
</read_first>

<acceptance_criteria>
- [ ] New file `frontend/src/components/ResolutionPanel.test.tsx`
- [ ] 6+ tests covering:
  - `renders Tier 1 Auto-Accept with green header` — majorityVote=3, gtMatchesMajority=true
  - `renders Tier 2 Quick Diff with yellow header` — majorityVote=2, majority_label differs from GT
  - `renders Tier 3 Manual Review with red header` — majorityVote=1
  - `Accept button triggers onAcceptSuggestion` — click Accept, verify callback with correct triplets
  - `Manual form can add triplet` — fill form, submit, verify onAddTriplet called
  - `Diff Tracker shows original_llm_diff text` — Tier 2, verify diff text visible
- [ ] Follows existing test pattern (createRoot + flushSync, no testing-library)
</acceptance_criteria>

<action>
1. Create `frontend/src/components/ResolutionPanel.test.tsx` with the test cases above
2. Import `CompactTripletChip` if needed for helper rendering
</action>

---

## Artifacts This Plan Produces

1. **`frontend/src/components/ResolutionPanel.tsx`** — New resolution panel with full tier logic
2. **`frontend/src/components/ResolutionPanel.test.tsx`** — 6+ vitest tests

---

## Verification

1. ✅ Tier 1 (majorityVote=3, matches GT): green header, auto-accept message, Accept button
2. ✅ Tier 2 (majorityVote=2, differs from GT): yellow header, diff tracker, Accept Majority/Keep GT buttons
3. ✅ Tier 3 (majorityVote=1): red header, manual review message, Manual Entry button
4. ✅ Accept button fires callback with correct triplets
5. ✅ Manual form adds triplets to parent state
6. ✅ Diff Tracker shows original_llm_diff text when present
7. ✅ Panel fits within ~30% width, no overflow

---

## PLANNING COMPLETE
