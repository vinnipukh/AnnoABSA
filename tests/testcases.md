# AnnoABSA — Regression Test Cases

**Status:** Baseline captured 2026-07-11 (updated for Phase 3: drag selection + NLP toolbox).
**Test dataset:** `examples/semeval_reviews.csv` (5 Turkish restaurant reviews).
**Backend:** `uvicorn main:app --port=8000 --host=localhost` with `ABSA_DATA_PATH=examples/semeval_reviews.csv`
**Frontend:** `npm run dev -- --port 3000` in `frontend/`

Covers automated (pytest + vitest) and manual (browser) test cases.

---

## Quick-Reference Tables

### Tier 1 — Smoke

| ID | Test | Expected | Verdict |
|---|---|---|---|
| S1 | App loads at `localhost:3000` | Header + main area + Helper Agent panel visible, no console errors | ✓ run |
| S2 | Click mode toggle (`Karşılaştır` / `Manuel`) | Swaps cleanly between two-column comparison and single-column manual annotator | ✓ run |
| S3 | Row counter in header | Shows `#N/total` format (e.g. `#1/4`) | ✓ code |
| S4 | No UI overlap at default window size | Footer `Kaydet & Geç` doesn't cover chat input; popup backdrop covers full screen | ✓ run |
| S5 | Backend reachable | `GET /settings` returns 200 | ✓ code + run |

### Tier 2A — Manuel mode (PhraseAnnotator)

| ID | Test | Expected | Verdict |
|---|---|---|---|
| MA1 | Drag-select on review text (mousedown → drag → mouseup) | Native browser blue highlight, token snapping via `getTokenBounds()` | ✓ code |
| MA2 | Form opens after span selection | Popup with aspect term pre-filled from selected text | ✓ code + run |
| MA3 | Save a triplet | Counter increments, annotation listed, text highlighted | ✓ code + run |
| MA4 | Add multiple triplets | Each gets distinct color, all remain listed and highlighted; duplicate (same span + same category) silently skipped | ✓ code + run |
| MA5 | Delete a triplet | Removed from list, highlight removed, count decremented | ✓ code |
| MA6 | Save with no category/polarity | **No blocked state** — form always has defaults (`categories[0]`, `'positive'`) | ✓ code |

### Tier 2B — Karşılaştır mode (Compare)

| ID | Test | Expected | Verdict |
|---|---|---|---|
| KA1 | Model A / B triplets render with checkboxes | Columns populated from API; empty state when no comparison CSVs | ✓ code + run |
| KA2 | Click `Tümünü Seç` on Model A | Only Model A items selected — Model B untouched (separate `Set` state) | ✓ code |
| KA3 | Click `Tümünü Seç` on Model B | Reversed | ✓ code |
| KA4 | Individual checkbox toggle | Toggles id in respective `Set` | ✓ code |
| KA5 | Deselect a checked item | Removed from `Set` | ✓ code |
| KA6 | Add manual triplet while in Compare mode | Appears under "Eklenen Özel Tripletler", NOT in Model A/B columns | ✓ code |
| KA7 | Triplet with `"NULL"` aspect term | Renders as `"NULL"` (quoted), still selectable | ✓ code |
| KA8 | Footer count (`X etiket seçildi`) | Compare: `A.size + B.size + manual.length`; Manual: `manual.length` | ✓ code |

### Tier 2C — Text Selection (native drag)

| ID | Test | Expected | Verdict |
|---|---|---|---|
| TS1 | Karşılaştır mode: drag-select on review text | Native blue highlight follows cursor | — |
| TS2 | Karşılaştır mode: release mouse after drag | Selection finalized, NLP toolbox red icon appears at bottom-center | — |
| TS3 | Single click (no drag) on a word | Selects the full token (token snapping) | — |
| TS4 | Selection clears on row navigation | New row has no active selection | — |
| TS5 | Drag selection in Karşılaştır mode does NOT toggle model checkboxes | Checkbox state unchanged | — |
| TS6 | Select text, switch mode to Manuel, switch back | Selection resets (expected — mode change re-renders) | — |

### Tier 3 — Persistence (in-memory frontend state, not DB)

| ID | Test | Expected | Verdict |
|---|---|---|---|
| P1 | Add triplets in Manuel, switch to Karşılaştır | Triplets survive — mode toggle doesn't clear state | ✓ code |
| P2 | Select in Karşılaştır, switch to Manuel | Survives — same state shared across renders | ✓ code |
| P3 | Round-trip Manuel → Karşılaştır → Manuel | No duplication, no loss | ✓ code |
| P4 | Send chat message, switch modes | Chat history persists | ✓ code |
| P5 | Navigate row #1 → #2 → back to #1 | Triplets restored from backend `label` field (P5 bugfix) | ✓ code (10/10) |

### Tier 4 — Navigation

| ID | Test | Expected | Verdict |
|---|---|---|---|
| N1 | `Kaydet & Geç` on non-last row | Saves to `POST /review/{idx}/save`, advances | ✓ code |
| N2 | `Kaydet & Geç` on last row | Saves, wraps to row #1 | ✓ code |
| N3 | ▶ arrow button | Simple nav, no save, wraps | ✓ code |
| N4 | ◀ arrow button | Simple nav, no save, wraps | ✓ code |
| N5 | `Kaydet & Geç` with zero triplets | Saves empty `[]` — no warning, no block | ✓ code |
| N6 | `Temizle` button | Clears state, no navigation, no save | ✓ run |

### Tier 5 — Helper Agent

| ID | Test | Expected | Verdict |
|---|---|---|---|
| H1 | `İlk Analiz` on row load | Auto-renders with initial analysis referencing current review | ✓ code + run |
| H2 | Send message via `Asistana sor...` | User + agent bubbles appear | ✓ code |
| H3 | Multi-turn on same row | Context maintained — backend trims to last 4 turns | ✓ code |
| H4 | Navigate to different row | Chat resets (new `İlk Analiz`, old conversation gone) | ✓ code |
| H5 | Empty message input | `Gönder` disabled | ✓ code |
| H6 | Long conversation | Auto-scroll to latest message | ✓ code |

### Tier 6 — UI Polish

| ID | Test | Expected | Verdict |
|---|---|---|---|
| U1 | Text span highlight | Continuous runs, no per-character gaps | ✓ code + run |
| U2 | Default window width | Main area `max-w-[1700px]`, fluid layout | ✓ run |
| U3 | Header icons (💬 ⬆ ◀ ▶) | All present and clickable | ✓ code |
| U4 | Footer status text | `{N} etiket seçildi · {mod} modu` | ✓ code |

---

### Tier 7 — NLP Helper Toolbar Backend

| ID | Test | Expected | Verdict |
|---|---|---|---|
| NLB1 | `GET /nlp/lexicon-polarity?text=güzel` returns known word | Polarity for "güzel" is "positive" | ✓ |
| NLB2 | `GET /nlp/lexicon-polarity?text=xyzzy` returns unknown word | polarity="unknown", aggregate="neutral" | ✓ (test) |
| NLB3 | `GET /nlp/sentiment?text=Harika` with positive text | label="positive", score > 0.7 | — (needs model download) |
| NLB4 | `GET /nlp/sentiment?text=Berbat` with negative text | label="negative", score > 0.7 | — (needs model download) |
| NLB5 | `GET /nlp/morphology?word=güzel` | Returns at least 1 parse with root + POS | ✓ |
| NLB6 | `GET /nlp/embedding-similarity` with identical selection+sentence | similarity=1.0 | ✓ (test) |
| NLB7 | Lazy loading: no model import at startup | Server logs contain none of: "SentiNet", "pipeline", "FsmMorphological", "SentenceTransformer" | ✓ |
| NLB8 | All 4 endpoints return HTTP 500 on internal error | Each wraps exceptions properly | ✓ (test) |
| NLB9 | Router registration in main.py | `from app.routes.nlp import router` + `app.include_router(nlp_router)` | ✓ |

### Tier 7B — NLP Helper Toolbar Frontend

| ID | Test | Expected | Verdict |
|---|---|---|---|
| NF1 | Red toolbox icon visible after text selection in Manuel mode | Red toolbox SVG appears at bottom-center of screen | — (browser) |
| NF2 | Red toolbox icon visible after text selection in Karşılaştır mode | Red toolbox SVG appears at bottom-center of screen | — (browser) |
| NF3 | Click toolbox icon → toolbar expands | 4 segments visible; Sözlük shows lexicon result immediately | — (browser) |
| NF4 | Click "Duygu Analizi" segment | Loading spinner → positive/negative label + confidence | — (browser, needs model) |
| NF5 | Click "Yapı Çözümleme" segment | Root word + POS + inflectional groups shown | — (browser) |
| NF6 | Click "Benzerlik Karşılaştırması" segment | Similarity score shown as percentage | — (browser, needs model) |
| NF7 | Escape key collapses toolbar | Toolbar disappears, text selection preserved | — (browser) |
| NF8 | Click outside toolbar collapses it | Same as Escape | — (browser) |

### Tier 8 — NLP Toolbar Unit Tests (vitest)

| ID | Test | Expected | Verdict |
|---|---|---|---|
| VT1 | 14 toolbar component tests | All pass: collapse/expand, auto-fetch, on-demand, errors, Escape, abort | ✓ (27 total) |

### Tier 9 — Live Compare Mode

| ID | Test | Expected | Verdict |
|---|---|---|---|
| LC1 | Open Settings → switch Compare Mode to ⚡ Canlı | Mode toggle shows "Canlı", CSV columns go empty | — |
| LC2 | Click "Model A Çalıştır" with unconfigured provider | Error toast: "model_a: No provider configured" | — |
| LC3 | Configure Model A (provider=ollama, model=gemma3:4b), click "Model A Çalıştır" | Loading spinner → triplet list appears in column | — |
| LC4 | Click "Model B Çalıştır" with unconfigured model_b | Error toast: "model_b: No model configured" | — |
| LC5 | Configure Model B, click "Model B Çalıştır" | Triplets appear, independent of Model A's output | — |
| LC6 | Select some triplets, save & advance | POST /review/{idx}/save called, row advances | — |
| LC7 | Navigate back to the saved row | Live state cleared, columns empty again | — |
| LC8 | Switch Compare Mode back to 📁 CSV | CSV data re-appears in columns (no regression) | — |
| LC9 | Configure custom Model A prompt → run | Different prompt produces different output | — |
| LC10 | Set temperature to 1.5 → run | Output may differ from temperature=0.0 run | — |

---

## Automated Tests

```bash
pytest tests/        # 124 backend tests
cd frontend && npx vitest run   # 27 frontend tests
```

### Backend (pytest — 124 tests)

| File | Tests | What it covers | Correlates to |
|---|---|---|---|
| `tests/test_prediction.py` | 38 | `find_phrase_positions`, `find_valid_phrases_list`, `generate_mock_reasoning`, `build_prediction_prompt`, `build_absa_models`, `get_most_similar_examples` | MA3/MA4 position math, H1 fallback, prompt templates |
| `tests/test_llm_providers.py` | 31 | `_derive_provider` (12 scenarios), `PROVIDER_REGISTRY`, `get_provider` factory, `predict_llm` importable, `validate_provider_config` (10 scenarios), `validate_per_model_config` | Provider derivation, key validation, per-model config |
| `tests/test_main_helpers.py` | 12 | `parse_triplet_column` (STD tuples, lists, dicts, empty/null) | KA7 NULL handling, data loading |
| `tests/test_nlp_helpers.py` | 12 | `lexicon_polarity`, `sentiment_classify`, `morphology`, `embedding_similarity` (all mocked) | NLB1–NLB8 handler logic |
| `tests/test_live_prediction.py` | 31 | `get_live_prediction` happy path, error cases (no provider, no model, unknown role), temperature propagation, per-model config validation | LC1–LC10 live compare mode |

### Frontend (vitest — 27 tests)

| File | Tests | What it covers |
|---|---|---|
| `frontend/src/hooks/useTextSelection.test.ts` | 13 | `getTokenBounds` (5), `cleanPhrase` (5), `getCleanedPositions` (3) |
| `frontend/src/components/NlpHelperToolbar.test.tsx` | 14 | Collapse/expand, auto-fetch lexicon, on-demand segments, error handling, Escape key, abort-on-unmount |

### What's NOT automated (needs live browser walkthrough)

- S1–S4: Page load, mode toggle, overlap, row counter rendering
- MA1–MA5: Drag selection, popup appearance, save, highlighting
- TS1–TS6: Native drag selection in Compare mode, token snapping, row reset
- KA1, KA6: Column rendering, manual form integration
- P1–P5: Mode-switch persistence, chat persistence, row re-navigation
- N1–N6: All navigation buttons
- H1–H6: Chat interactions, auto-scroll
- U1–U4: Visual polish
- NF1–NF8: NLP toolbox visual interaction (icon, expand, segments, collapse)

These require a running backend + frontend and a browser.

---

## Detailed Walkthroughs (Live-Verified)

### S1 — App loads

**Action:** Navigated to `http://localhost:3000` via `browser_navigate()`.
**Result:** Page loaded with title "AnnoABSA". Browser console showed zero errors or warnings.

Elements present:
- Header: "A" logo, "AnnoABSA" heading
- Mode toggle: "Karşılaştır" and "Manuel" buttons
- Chat toggle "Sohbeti Kapat" with SVG icon
- Upload button "CSV/JSON Yükle"
- Row counter "Satır: #1/5" with ◀ and ▶ nav buttons
- Model A column: "Bu model çıktı üretmedi" empty state
- Center column with ManualInputForm and review text "Manzara şahane ama servis rezalet"
- Model B column: same empty state
- Floating Helper Agent panel at bottom-right with initial analysis
- Footer: "Temizle" and "Kaydet & Geç ▶"

### S2 — Mode toggle

**Action:** Clicked "Manuel" button, then clicked "Karşılaştır" to round-trip.
**Result:** Manual mode shows "Manuel Etiketleme" heading, "TOKEN" badge, "0 etiket" count, clickable text spans, instruction text. Compare mode returns to three-column layout.

### S3 — Row counter

**Result:** Shows `#N/total` format. Initially `#1/5`.

### S4 — No UI overlap

**Checked at ~1280px viewport:**
1. Compare mode + chat panel open: No overlap
2. Manual mode + chat panel open: No overlap
3. Manual mode + annotation popup open: Popup is `position: fixed; z-index: 50` centered with `bg-black/40` backdrop. Chat panel at `bottom: 56px; right: 16px;` — backdrop covers it (expected).

### S5 — Backend reachable

**Action:** `curl http://localhost:8000/settings`
**Result:** HTTP 200, JSON with `total_count: 5`.

### MA1 — Drag-to-select span

**Action sequence:**
1. Switch to Manual mode
2. **mousedown** at start of desired text, **drag** across words, **mouseup**
3. Snapshot shows selected range (e.g. "[0-6]")

**Result:** Range [0-6] = "Manzara". Native browser blue selection highlight visible. Token snapping via `getTokenBounds()` expands to word boundaries.

### MA2 — Form opens after span selection

**Result:** Popup with "YENI ETIKET" header, ✕ close button, selected text `"Manzara"`, aspect term pre-filled as "Manzara", "NULL" checkbox, opinion term field, category dropdown, polarity buttons (+P / -N / =N), "+ Etiket Ekle" button.

### MA3 — Save a triplet

**Action:** Set category via JS to "Ambience#general", clicked "+ Etiket Ekle".
**Result:** Popup closed, counter "1 etiket", annotation listed as `"Manzara" | Ambience#general | POSITIVE`. Text runs re-rendered with colored background.

### MA4 — Add multiple triplets

**Action:** Selected "şahane" (range [7-13]), set category, saved.
**Result:** Counter "2 etiket". Both annotations listed. Text split into 4 runs based on highlighted regions.

### MA5 — Delete a triplet

**Tag:** ✓ code
**Code path:** `PhraseAnnotator.tsx` `onRemoveAnnotation(ann.id)`, App.tsx filters by id.
**Live note:** ✕ buttons inside scrollable annotation lists may be inconsistent via CDP. Use Temizle button as proxy.

### MA6 — Save with no category/polarity

**Finding:** No blocked state. Form always defaults to `categories[0]` and `'positive'`. Button always enabled.

### KA1 — Model columns with comparison CSVs

**Result:** Without `--compare-model-*-csv` flags, both columns render empty state "Bu model çıktı üretmedi".

### KA2–KA5 — Select/Deselect mechanics

**Code path:** `selectAllModelA`/`B` sets `Set` with all IDs. `toggleModelA`/`B` toggles individual IDs. Independent state between models.

### KA6 — Manual triplet in Compare mode

**Observation:** "Eklenen Özel Tripletler" section visible in center column with count and listed triplets.

### KA7 — NULL aspect term

**Code path:** `{t.aspect_term || 'NULL'}` renders as `"NULL"` (quoted).

### KA8 — Footer count

**Code path:** `mode === 'compare' ? selectedModelAIds.size + selectedModelBIds.size + manualTriplets.length : manualTriplets.length`.

### P1–P4 — Mode-switch preserves state

**Action (P1):** Added "Manzara" in Manual, switched to Compare, confirmed triplet still listed.
**Code:** Mode toggle is conditional render, never clears state. Only `loadReviewRow` clears.

### P5 — Row navigation restores saved triplets

**Issue found:** `setManualTriplets([])` was called unconditionally — saved data never restored to UI.
**Fix:** `loadReviewRow` now parses `data.label` and restores triplets on re-navigation.

**Test results (10/10 logic verification):**

| Input | Result | Expected |
|---|---|---|
| `'[{"aspect_term":"pasta"}]'` | 1 item | 1 item |
| `'[]'` | 0 items | 0 items |
| `''` | 0 items | 0 items |
| `undefined` | 0 items | 0 items |
| `null` | 0 items | 0 items |
| `'NaN'` | 0 items | 0 items |
| `'None'` | 0 items | 0 items |
| `'[{},{}]'` | 2 items | 2 items |
| `[]` (FALLBACK_DATA) | 0 items | 0 items |
| `'   '` (whitespace) | 0 items | 0 items |

### N1–N2 — Kaydet & Geç

**Code path:** Collects approved triplets from selected model IDs + manual triplets, calls `POST /review/{idx}/save`, then advances via `(p + 1) % totalCount`. Wraps on last row.

### N3–N4 — Arrow buttons

**Code path:** ▶: `onClick={() => setCurrentIndex(p => (p + 1) % totalCount)}` — no save.
◀: wraps from index 0 to last. No save.

**Live run:** ▶ from row 1 → `#2/5`. ◀ → back to `#1/5`.

### N5 — Kaydet & Geç with zero triplets

**Code path:** Saves `{ triplets: [] }`. Backend writes `[]`. No validation.

### N6 — Temizle button

**Action:** Clicked "Temizle" after adding 2 triplets.
**Result:** Counter "0 etiket", list empty, single unhighlighted run. No navigation, no save.

### H1 — Initial analysis on row load

**Result:** Styled box "İlk Analiz" with reference to current review text and model names.

### H2 — Send a message

**Tag:** ✓ code
**Code path:** `POST /agent/chat` with `{review_text, model_a/b_triplets, user_message, chat_history}`. On failure → Turkish rule-based fallback.

### H3 — Multi-turn conversation

**Code path:** Full `chatHistory` sent. Backend trims to last 4: `req.chat_history[-4:]`.

### H4 — Chat resets on row change

**Action:** Navigated row 1 → row 2. Chat panel showed new initial analysis. Old conversation gone (expected baseline).

### H5 — Empty message disabled

**Code path:** `disabled={!inputText.trim() || isLoading}`.

### H6 — Auto-scroll

**Code path:** `messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })`.

### U1 — Text span highlight

**Code path:** Continuous runs via merged background colors, `rounded-sm`. No per-character borders.

### U2 — Window width

**Code path:** Main area `max-w-[1700px]`. No explicit 1280px target. Compare mode uses `grid-cols-1 md:grid-cols-3`.

### U3 — Header icons

| Icon | Action | Code |
|---|---|---|
| 💬 | Toggle chat panel | `setShowFloatingChat(p => !p)` |
| ⬆ | File upload | `fileInputRef.current?.click()` |
| ◀ | Previous row | `setCurrentIndex(p => ...)` |
| ▶ | Next row | Same, forward |

### U4 — Footer status

**Code path:** `{tripletCount} etiket seçildi · {mode === 'manual' ? 'Manuel' : 'Karşılaştırma'} modu`.

---

## Backend endpoints verified

| Endpoint | Method | Status | Notes |
|---|---|---|---|
| `/settings` | GET | 200 | Returns config, total_count=5 |
| `/data/{idx}` | GET | 200 | Review data with label, model triplets |
| `/review/{idx}/save` | POST | 200 | **Only live save endpoint** |
| `/agent/chat` | POST | 200 | Provider dispatch + rule-based fallback |

---

## Browser tool interaction notes

1. **Native drag selection works naturally** — mousedown, drag, mouseup. The `useTextSelection` hook reads `window.getSelection()` on mouseup and computes character offsets via `Range.toString().length` walking. Token snapping still applies.

2. **Single click selects one token** — mousedown + mouseup without drag selects the word at the click position (token-snapped).

3. **✕ delete buttons inside scrollable annotation lists** are not consistently reachable via CDP. The Temizle button (same state management) is a reliable proxy.

4. **Multi-line JavaScript expressions in `browser_console`** fail with `SyntaxError: Unexpected end of input` — use single-line JS only.

---

## Coverage summary

| Suite | Command | Count |
|---|---|---|
| Backend pure logic | `pytest tests/` | 124 |
| Frontend pure functions | `npx vitest run` | 13 (hook) |
| Frontend component tests | `npx vitest run` | 14 (toolbox) |
| **Total automated** | | **151** |
| Manual browser walkthrough | `tests/testcases.md` tiers 1–9 | ~60 cases |
