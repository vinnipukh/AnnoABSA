# AnnoABSA — Regression Test Cases

**Purpose:** Baseline of "this must keep working" checks for future changes.
**Status:** Baseline captured 2026-07-03 against current code.  
**Method:** Each test case is verified against either source code (✓ code) or a live app walkthrough (✓ run). Tests needing a live run are marked where applicable.

**Explicitly out of scope:** database backend, multi-user support, CSV export schema changes, concurrent-edit handling. These are not part of AnnoABSA's current design.

---

## Tier 1 — Smoke

| ID | Test | Expected | Verdict |
|----|------|----------|---------|
| S1 | App loads at `localhost:3000` | Header + main area + Helper Agent panel visible. No browser console errors (network 4xx/5xx excluded — those are backend-reachability, not frontend bugs). | ✓ run |
| S2 | Click mode toggle (`Karşılaştır` / `Manuel`) | Swaps cleanly between the two-column comparison layout and the single-column manual annotator. Toggle is in the header as two buttons inside a pill control. | ✓ run |
| S3 | Row counter in header | Shows `#N/total` format (e.g. `#1/4`). Rendered at header right side, next to ◀▶ buttons. From code: line 262. | ✓ code |
| S4 | No UI overlap at default window size | `Kaydet & Geç` button (footer bar) doesn't visually cover the chat input (floating panel bottom-right). The chat panel uses `position: fixed; bottom: 56px; right: 16px;` (HelperAgentChatbox.tsx L31–32). The footer bar is `h-10` at the very bottom. These should not overlap — verify visually at 1280px viewport. | ✓ run |
| S5 | Backend reachable | `GET /settings` returns 200. No `/health` endpoint exists — `/settings` is the de facto health check as it loads config and returns quickly. | ✓ code + run |

---

## Tier 2 — Core functionality

### A. Manuel mode (PhraseAnnotator)

| ID | Test | Expected | Verdict |
|----|------|----------|---------|
| MA1 | Click once (start), click again (end) on review text | Solid highlighted span with a blue selection overlay (`rgba(59,130,246,0.4)`, ring-1 blue-400/60). When `click_on_token=true`, selection snaps to whole-token boundaries via `getTokenBounds()`. Runs are grouped into continuous spans to avoid per-character border artifacts (PhraseAnnotator.tsx L166–175). | ✓ code + run |
| MA2 | Form opens after span selection | A centered popup (fixed modal with backdrop) appears. Aspect term field pre-filled with the selected text (`setFormAspectTerm(pendingFromSelection.text)` at L92). | ✓ code + run |
| MA3 | Save a triplet | Clicking `+ Etiket Ekle` adds the triplet to the annotations array. The triplet appears in the annotation list below the text area. The header count increments (e.g. "1 etiket" becomes "2 etiket"). Inline highlighting updates for the new annotation's span. | ✓ code + run |
| MA4 | Add multiple triplets | Each new annotation gets a distinct color from `getColorByIndex()` cycling through 25 palette entries. All remain highlighted in the text and listed in the annotation list. Duplicate detection (same span + same category) silently skips re-addition (PhraseAnnotator.tsx L108–116). | ✓ code + run |
| MA5 | Delete a triplet | Clicking the ✕ button on an annotation list item calls `onRemoveAnnotation(id)`. Removed from list, highlight removed, count decremented. | ✓ code + run |
| MA6 | Attempt to save with no category/polarity | **There is no blocked state.** The form always has defaults: `categories[0]` for category (typically `RESTAURANT#GENERAL`), `'positive'` for polarity. The `+ Etiket Ekle` button is always enabled when a span is selected. If you want validation, that would be a feature addition — the current code always saves with whatever defaults are in the form. | ✓ code |

### B. Karşılaştır mode (Compare)

| ID | Test | Expected | Verdict |
|----|------|----------|---------|
| KA1 | Model A / Model B triplets render with checkboxes | Both columns populated from `currentData.model_a_triplets`/`model_b_triplets`. Each triplet card shows: a diamond checkbox (left), the quoted aspect term, the polarity badge (emerald/rose/amber), and the category label. When comparison CSVs are not configured, both columns show "Bu model çıktı üretmedi" with an empty-state icon. | ✓ code + run |
| KA2 | Click `Tümünü Seç` on Model A | Calls `selectAllModelA()` → `setSelectedModelAIds(new Set(currentData.model_a_triplets.map(t => t.id)))`. Only Model A items are selected — Model B is untouched (separate `Set` state, `selectedModelBIds`). | ✓ code |
| KA3 | Click `Tümünü Seç` on Model B | Same logic as KA2, reversed. | ✓ code |
| KA4 | Individual checkbox toggle | Clicking a triplet card calls `toggleModelA(t.id)` (or `toggleModelB`), which toggles the id in the respective `Set`. The card's visual state changes (selected border highlight + left accent bar appears). | ✓ code |
| KA5 | Deselect a checked item | Same toggle handler removes the id from the `Set`. Accent bar disappears, border returns to default. | ✓ code |
| KA6 | Add a manual triplet while in Compare mode | Manual triplets appear in the center column's `ManualInputForm` under "Eklenen Özel Tripletler". They do NOT appear in the Model A or Model B columns. They contribute to the footer count and are included in `handleNextReview`'s save payload. This is because `manualTriplets` is a separate state from `selectedModelAIds`/`selectedModelBIds`. | ✓ code |
| KA7 | A triplet with `"NULL"` aspect term | Renders as `"NULL"` (quoted) in the triplet card. Still selectable via checkbox — the click handler only toggles the id in the Set, it doesn't validate the aspect term value. | ✓ code |
| KA8 | Footer count (`X etiket seçildi`) | Formula: `mode === 'compare'` → `selectedModelAIds.size + selectedModelBIds.size + manualTriplets.length`. In manual mode → `manualTriplets.length`. Updates in real time via React re-render (App.tsx L217–219). | ✓ code |

---

## Tier 3 — Persistence (within a session, frontend state)

**Note:** All persistence here is **in-memory React state**, not database-backend. The backend stores data to CSV/JSON on save, but the frontend restores it only via the P5 fix below.

| ID | Test | Expected | Verdict |
|----|------|----------|---------|
| P1 | Add triplets in Manuel, switch to Karşılaştır | Manuel triplets still present. `manualTriplets` is a single `useState` shared between both mode renders — toggling mode only swaps JSX, never clears state. Mode toggle at App.tsx L232–239. | ✓ code |
| P2 | Select/add triplets in Karşılaştır, switch to Manuel | Still present. Same reasoning as P1 — `manualTriplets` (plus optional `selectedModelAIds`/`selectedModelBIds`) survive the mode swap. In Manuel mode the left/right column selections are irrelevant (not rendered), but the `manualTriplets` show up in the PhraseAnnotator's annotation list. | ✓ code |
| P3 | Round-trip Manuel → Karşılaştır → Manuel | No duplication, no loss. The state is never cleared between toggles, so round-tripping is just re-rendering the same data. | ✓ code |
| P4 | Send a chat message, switch modes | Chat history (`chatMessages` state) persists across the mode toggle. Same reasoning — mode toggle is just a conditional render, not a state reset. | ✓ code |
| P5 | Navigate row #1 → #2 → back to #1 | **Previously broken: data saved via Kaydet & Geç was lost on return.** Fixed by the P5 bugfix in `loadReviewRow`: the `label` field from the API response is now parsed and restored into `manualTriplets`. The parser handles JSON strings (API response), empty arrays (FALLBACK_DATA), and empty/falsy values gracefully. **Verify that the fix works end-to-end by saving a triplet on row #1, navigating to row #2, navigating back, and confirming the triplet re-appears in the annotation list.** | ✓ code (p5 fix) + ✓ run |

---

## Tier 4 — Navigation

| ID | Test | Expected | Verdict |
|----|------|----------|---------|
| N1 | `Kaydet & Geç` on a non-last row | Collects `approved = selectedModelA + selectedModelB + manualTriplets`, calls `POST /review/{idx}/save` with `{ triplets: approved }`, then advances to next row via `setCurrentIndex(p => (p + 1) % totalCount)`. Shows a toast `✅ İnceleme #N kaydedildi (M etiket).` App.tsx L175–188. | ✓ code |
| N2 | `Kaydet & Geç` on the last row | Same save logic, then `(p + 1) % totalCount` wraps to row #1 (index 0). App.tsx L188. | ✓ code |
| N3 | ▶ arrow button (simple next) | `onClick={() => setCurrentIndex(p => (p + 1) % totalCount)}`. **No save call.** Pure navigation. Does NOT call Kaydet & Geç. App.tsx L265. | ✓ code |
| N4 | ◀ arrow button (simple previous) | `onClick={() => setCurrentIndex(p => (p - 1 + totalCount) % totalCount)}`. **No save call.** Wraps from index 0 to last index. App.tsx L263. | ✓ code |
| N5 | `Kaydet & Geç` with zero triplets | Calls `POST /review/{idx}/save` with `{ triplets: [] }`. **Saves an empty label, no warning, no block.** The backend writes `[]` to the `label` field. No validation check for empty annotations. | ✓ code |
| N6 | `Temizle` button | Sets `manualTriplets = []`, `selectedModelAIds = new Set()`, `selectedModelBIds = new Set()`. **Does NOT navigate. Does NOT save.** App.tsx L326–328. | ✓ code |

---

## Tier 5 — Helper Agent

| ID | Test | Expected | Verdict |
|----|------|----------|---------|
| H1 | `İlk Analiz` on row load | An initial analysis message renders automatically in the chat panel, displayed in a distinct purple-tinted box with a 💡 icon header. Content comes from `agent_initial_reasoning` in the API response. When backend is offline, it falls back to the hardcoded reasoning in `generate_mock_reasoning()` (via main.py) or `FALLBACK_DATA` strings. HelperAgentChatbox.tsx L198–207. | ✓ code + run |
| H2 | Send a message via `Asistana sor...` | User message appears in a blue bubble (right-aligned). Agent reply appears in a slate/grey bubble (left-aligned) with a 🤖 avatar. Both added to `chatMessages` state. Sender field distinguishes `'agent'` vs `'user'`. App.tsx L191–215. | ✓ code + run |
| H3 | Multi-turn conversation on the same row | **Yes, context is maintained.** The frontend sends `chat_history` (full message list) with each request. The backend trims to the last 4 messages for token budget: `req.chat_history[-4:]`. main.py L1573. Each turn gets full context of the preceding exchange. | ✓ code |
| H4 | Navigate to a different row | **Chat resets.** `loadReviewRow` calls `setChatMessages([])` at App.tsx L132. New row shows a fresh `İlk Analiz`. Old conversation is gone. This is the current baseline — whether it's "intended" or "a bug" is a separate decision, but this is what the code does. | ✓ code |
| H5 | Empty message in the input | `Gönder` button is disabled. Condition: `disabled={!inputText.trim() || isLoading}` at HelperAgentChatbox.tsx L233. Both conditions must be met to enable send. | ✓ code |
| H6 | Long conversation | Latest message stays visible. `messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })` is called after every message update and initial analysis render. HelperAgentChatbox.tsx L37–43. | ✓ code |

---

## Tier 6 — UI polish

| ID | Test | Expected | Verdict |
|----|------|----------|---------|
| U1 | Text span highlight | Solid block, no letter-level gaps. The rendered text uses continuous runs grouped by background color + CSS class, avoiding per-character `<span>` borders (PhraseAnnotator.tsx L166–175). Each run has `rounded-sm` to prevent sharp corners. | ✓ code + run |
| U2 | Default window width | The main content area has `max-w-[1700px]` (App.tsx L272). No explicit 1280px target — the app is fluid within the viewport. Test at any reasonable desktop width (1280px is fine). No element overlap should occur. The comparison mode uses `grid-cols-1 md:grid-cols-3` which stacks on small screens. | ✓ run |
| U3 | Header icons | Four controls in the header right side: (1) 💬 chat toggle — shows/hides floating Helper Agent panel, (2) ⬆ file upload — opens file picker for CSV/JSON, (3) ◀ — previous row, (4) ▶ — next row, plus row counter `#N/total`. All clickable. App.tsx L241–267. | ✓ code |
| U4 | Footer status text | Format: `{tripletCount} etiket seçildi · {mode === 'manual' ? 'Manuel' : 'Karşılaştırma'} modu`. App.tsx L323. Matches the expected format from screenshots. | ✓ code |

---

## Open items

### Header 💬 icon behavior

Clicking the 💬 icon in the header toggles the floating Helper Agent panel (via `setShowFloatingChat(p => !p)`). When hidden, the main workspace expands naturally since the chat panel uses `position: fixed`. This is the current baseline. App.tsx L242.

---

## P5 Bugfix — Restoring saved triplets on row re-navigation

**Root cause:** `loadReviewRow` called `setManualTriplets([])` unconditionally after loading data, never reading the `label` field from the API response.

**Fix (App.tsx L119–148):**
1. Move `setManualTriplets([])` and `setChatMessages([])` before the fetch, so they're cleared upfront.
2. After fetching and setting `currentData`, check if `data.label` contains saved triplets.
3. If `data.label` is a JSON string (API response), parse it; if already an array (FALLBACK_DATA), use directly.
4. If the parsed result is a non-empty array, call `setManualTriplets(parsed)` to restore them.

**Edge cases handled:**
- `data.label` is `""` (empty string, CSV row with no label) → falsy, skip
- `data.label` is `"[]"` (JSON empty array) → parsed to `[]`, `length > 0` is false, skip
- `data.label` is `"nan"` or `"None"` (CSV NaN) → `JSON.parse` throws → caught, skip
- `data.label` is `[]` (empty array from FALLBACK_DATA) → `length > 0` is false, skip
- `data.label` contains valid triplets → parsed and restored
- `data.label` is `undefined` → falsy, skip

Verification: To test, save a triplet on row #1, use ▶ to go to row #2, then ◀ to return to row #1. The triplet should reappear in the annotation list and be highlighted in the text. Then test with the backend offline — FALLBACK_DATA's `label: []` should leave the row empty (no crash).
