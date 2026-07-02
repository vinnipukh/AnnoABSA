# AnnoABSA — Phase 1 Implementation Brief

Audience: a coding agent picking up this repo cold. Read this fully before writing code.
Repo: AnnoABSA (FastAPI backend `main.py`/`cli.py`, React+TS frontend in `frontend/`).

Phase 1 has five tasks. They are mostly independent — do them in the order below, but don't
block one on another unless noted.

1. STD format dataset support
2. Generalize the two-LLM comparison feature
3. New provider support (Anthropic, vLLM)
4. Prompt improvements
5. Restore original-AnnoABSA manual annotation screen + mode toggle

**Note on scope:** an earlier version of this brief listed a "Settings menu" as a Phase 2 item.
That's still Phase 2 — Task 5 below does **not** include exposing the ~28 CLI flags in-app. It
only concerns the annotation screen itself.

For each task: read "Current state" before touching anything — don't assume, verify against
the actual file/line. Each task ends with a "Definition of done" — treat that as the test to
pass, not a suggestion.

---

## Task 1 — STD format dataset integration

### What STD format is

Two-column CSV used by the user's research group: `review,triplet`. Example
(`coursera_train.csv`):

```csv
review,triplet
"Çok az araştırma temeli olan harika ""amatör tavsiyeler"" sunuyordu.","[['NULL', 'presentation quality', 'negative']]"
Böylesine harika materyal için tüm yazarlara teşekkürler.,"[['materyal', 'material quality', 'positive']]"
Bu alana ilgi duyan herkese tavsiye ederim.,"[['NULL', 'course general', 'positive']]"
```

Rules:
- `review` = the text to annotate.
- `triplet` = a **Python list-literal string** (not JSON — note the single quotes) of
  3-element lists: `[aspect_term, aspect_category, sentiment_polarity]`.
- `aspect_term` is the literal string `'NULL'` when the aspect is implicit (not a span in the
  text). There is no fourth element — **STD has no `opinion_term` and no character positions**.
- A review can have zero, one, or multiple triplets in the list.

### Current state (verify before coding)

The internal annotation schema (used everywhere else in the app — `get_data`, `post_annotations`,
the frontend annotation form) is a list of dicts per item:

```json
{"aspect_term": "materyal", "aspect_category": "material quality", "sentiment_polarity": "positive", "opinion_term": "", "at_start": 0, "at_end": 0, "ot_start": 0, "ot_end": 0}
```

— stored under a `label` column (CSV, JSON-encoded string) or `label` key (JSON file).
See `main.py::get_data` (~L241) and `main.py::post_annotations` (~L400).

There is **already** a parser for the STD triplet-list syntax: `main.py::parse_triplet_column`
(~L176), using `ast.literal_eval`. It currently only feeds the **comparison** columns
(`deepseek_triplets`/`qwen_triplets` — see Task 2) and outputs a *different*, comparison-only
shape (`{id, aspect_term, aspect_category, sentiment_polarity}` — no `opinion_term`/positions).
Don't reuse it as-is for the main `label` field; write a sibling converter with the correct
output shape, and consider whether `parse_triplet_column`'s core parsing logic should be
factored out so both call the same `ast.literal_eval` parsing step.

### What to build

1. A converter function, e.g. `std_triplets_to_label(raw_triplet_str: str) -> list[dict]`,
   producing the internal `label` shape:
   - `'NULL'` (case as given, plus reasonably handle `None`/empty string defensively) →
     `aspect_term: ""` (this is how implicit aspects are represented elsewhere — check
     `auto_add_missing_positions`, ~L485, for confirmation before assuming).
   - `opinion_term: ""`, and omit/zero positions (`at_start`/`at_end`/`ot_start`/`ot_end`) —
     do **not** invent positions for the aspect term here. If you want positions filled in
     automatically, that's what the existing `--auto-positions` flag / `auto_add_missing_positions`
     is for — wire into that rather than duplicating position-finding logic.
   - Empty list `[]` → `[]`.
2. A loader path so the CLI can open a STD-format CSV directly. Two reasonable options — pick
   one and state your choice, don't silently do both:
   - **Option A (explicit):** new CLI flag `--format std`, used at load time to know to map
     `review`→`text` and `triplet`→`label` (via the converter) before the rest of the app sees it.
   - **Option B (auto-detect):** if the loaded CSV has exactly `review`/`triplet` columns and no
     `text`/`label` columns, treat it as STD format automatically.
   Recommendation: **Option A**, explicit flag. Auto-detection is a guess that fails silently
   when a colleague's CSV has slightly different column names — explicit is safer and matches
   how `--load-config` already works. Flag this choice to the user if you disagree.
3. Decide where conversion happens: convert once at load time into the existing internal
   CSV/JSON working format (simplest, matches current `load_data`/`save_data` architecture), vs.
   converting on the fly in `get_data`/`post_annotations` (more code, no benefit here). Use the
   load-time conversion — don't add per-request branching for this.
4. **Export back to STD format.** The user's research group needs files to stay compatible.
   Add a CLI flag (e.g. `--export-std <output_path>`) or a small standalone script that takes
   the internal `label` format and writes it back out as `review,triplet` with the same
   list-literal string syntax (use `repr()` of a list of 3-tuples — verify the round-trip
   produces a string `ast.literal_eval`-equivalent to the input, not necessarily byte-identical).
   This only needs to round-trip `aspect_term`/`aspect_category`/`sentiment_polarity` —
   `opinion_term` and positions are **dropped** on export (STD doesn't have them); confirm
   with the user that's acceptable before treating it as final.

### Edge cases to handle (write a test per case)

- Implicit aspect: `[['NULL', 'course general', 'positive']]`
- Multiple triplets in one review.
- Empty triplet list: `[]` or empty string.
- Embedded double quotes in the review text (see the `"amatör tavsiyeler"` example above — this
  is standard CSV quoting, `pandas.read_csv` should already handle it; just don't reprocess the
  text yourself).
- Malformed/unparseable triplet string — should not crash the app; log and treat as `[]`
  (mirrors `parse_triplet_column`'s existing `except` behavior).

### Definition of done

- Loading `coursera_train.csv` (the 9-row sample above) via the new flag produces correct
  `text`/`label` values for every row, verified by a script/test that checks each row's parsed
  `label` against the hand-written expected output.
- Annotating a STD-loaded item in the UI and saving works through the existing
  `post_annotations` endpoint unmodified.
- Export round-trips a small fixture file (triplets only — not testing opinion_term/positions,
  since those don't exist in STD).

---

## Task 2 — Generalize the LLM-comparison feature

### Current state (verify before coding)

This feature **already exists**, just hardcoded for a specific demo dataset. In
`main.py::get_data` (~L270–L300):
- It looks for columns `aspect_triplets`/`new_triplets` in the row, or
- Falls back to sibling files **hardcoded by filename**: `semeval_deepseek_labeled.csv` and
  `semeval_qwen_labeled.csv`, matched by `review_id`.
- Output keys are hardcoded as `deepseek_triplets`/`qwen_triplets` end-to-end: `main.py`
  (`AgentChatRequest`, `generate_mock_reasoning`, `get_data` response), `frontend/src/types.ts`
  (`ReviewComparisonData.deepseek_triplets`/`qwen_triplets`), and presumably `App.tsx` /
  `HelperAgentChatbox.tsx` (**grep for `deepseek`/`qwen` across `frontend/src` before starting
  — do not assume these are the only two files**).
- `ModelTripletColumn.tsx` itself is already generic (`title`, `badgeText` props) — it's the
  plumbing feeding it that's hardcoded, not the display component.

### What "compare labels of two LLMs from CSVs" should mean

User-supplied comparison: point the tool at two arbitrary labeled CSVs (not a fixed filename),
give each a display name, and see them side by side per review. The CSVs can use either the
existing per-row format (`review_id, aspect_term, aspect_category, sentiment_polarity`
columns) or STD triplet format (`review, triplet`) — reuse Task 1's parser for the latter so
there's one source of truth for STD parsing.

### What to build

1. Config fields (in the JSON config consumed by `load_config`, plus matching `--*` CLI flags
   in `cli.py`, following the existing pattern for e.g. `--annotation-guideline`):
   - `compare_model_a_csv`, `compare_model_a_name`
   - `compare_model_b_csv`, `compare_model_b_name`
2. Replace the hardcoded filenames/column names in `get_data` with reads from this config.
   Keep the generic dict shape (`{id, aspect_term, aspect_category, sentiment_polarity}`) that
   `ModelTripletColumn` already expects — don't change that contract.
3. Rename `deepseek_triplets`/`qwen_triplets` to generic names (e.g. `model_a_triplets`/
   `model_b_triplets`) across backend response, `types.ts`, and every frontend file that
   references them. This is a rename, not a redesign — **don't refactor `ModelTripletColumn`
   itself**, it already takes `title`/`badgeText` as props.
4. `generate_mock_reasoning` (~L209) currently hardcodes "DeepSeek"/"Qwen" in the Turkish
   reasoning text it generates — update to use the configured display names instead of
   literal strings.
5. If no comparison CSVs are configured, the feature should no-op cleanly (empty
   `model_a_triplets`/`model_b_triplets`, no errors) — this is closer to the current default
   behavior than something new, just confirm it still holds after the rename.

### Definition of done

- Two STD-format CSVs with different model labels, pointed to via config/CLI flags with custom
  names, render correctly in the existing two-column comparison UI with the configured names
  as headers — no `deepseek`/`qwen` string remains anywhere in code or config defaults.
- Running with no comparison CSVs configured behaves identically to today's default (no
  comparison columns shown / no crash).

---

## Task 3 — New Helper Agent providers (Anthropic, vLLM)

### Current state (verify before coding)

Two prediction functions exist side by side, same overall shape (build few-shot examples via
BM25 → call the model → parse structured aspects):
- `main.py::predict_llm` (~L640) — **Ollama**, uses `ollama.generate` with a Pydantic
  `Aspects` model passed as `format=`.
- `main.py::predict_openai` (~L734) — **OpenAI**, uses the `OpenAI` client's structured-output
  `.parse()` with a Pydantic `Aspects` model.

Dispatch is in `get_ai_prediction` (~L985): **implicit priority** — if `config['openai_key']`
is set, use OpenAI; otherwise fall through to Ollama. No explicit provider selection exists
today.

### What to build

1. **`predict_vllm`**: vLLM exposes an OpenAI-compatible HTTP API. Do **not** write a new
   client from scratch — instantiate `OpenAI(base_url=<vllm_base_url>, api_key="not-needed")`
   and reuse `predict_openai`'s logic (refactor `predict_openai` to accept an optional
   `base_url` parameter rather than duplicating the function). Add `--vllm-base-url` and reuse
   `--llm-model` for the model name.
2. **`predict_anthropic`**: new function, same input/output contract as `predict_llm`/
   `predict_openai` (same args: `text, considered_sentiment_elements, examples,
   aspect_categories, polarities, allow_implicit_*, n_few_shot, llm_model, anthropic_key`).
   Anthropic's API does **not** have OpenAI's `.parse()` structured-output helper — implement
   structured output via tool use (define a tool with a JSON schema matching the `Aspects`
   shape, force `tool_choice`, and parse the tool-call input from the response). Add a
   `--anthropic-key` CLI flag, mirroring `--openai-key`.
3. **Fix the dispatch ambiguity** in `get_ai_prediction`: with 4 providers, implicit
   "if key present, use it" priority is fragile (what if both Anthropic and OpenAI keys are
   set?). Add an explicit `--llm-provider {ollama,openai,anthropic,vllm}` flag. Recommended
   default: keep current behavior (auto-detect by which single key is set) only when exactly
   one of the three cloud keys is configured; require explicit `--llm-provider` if more than
   one cloud key is present, and error clearly rather than silently picking one. Flag this
   design decision to the user before implementing if you think auto-detect should be dropped
   entirely instead — it's a judgment call, not a clear-cut "right" answer.
4. Add `anthropic` to `requirements.txt`.

### What NOT to do

- Don't touch `predict_llm` (Ollama) or the BM25 retrieval (`get_most_similar_examples`) — out
  of scope for this task.
- Don't rewrite `predict_openai`'s prompt construction while you're in there "for consistency"
  — that's Task 4, and it should be a deliberate, scoped change, not a side effect of plumbing
  in vLLM.

### Definition of done

- `--llm-provider anthropic --anthropic-key <key>` produces a valid `Aspects` prediction on a
  sample review, in the same shape `predict_openai` currently returns.
- `--llm-provider vllm --vllm-base-url <url>` works against a locally running vLLM server with
  an OpenAI-compatible endpoint, no new HTTP client code beyond passing `base_url`.
- Existing Ollama/OpenAI behavior (CLI flags, default model names, response shape) is
  unchanged for users not using the new flags.

---

## Task 4 — Helper Agent prompt improvements

### Scope (confirmed with user, not a guess)

- Focus is **Turkish-language ABSA labeling quality**. English-labeling code paths don't need
  to be deleted (leave them working if removal risks breaking something), but they are not the
  priority — don't spend effort optimizing English prompt quality.
- `aspect_category` and `sentiment_polarity` **values stay in English** (e.g. `course general`,
  `positive`) — this is deliberate, confirmed with the user, not an oversight. Full Turkish
  translation of category/polarity naming is planned as separate future work, out of scope here.
  Do not translate category/polarity strings anywhere in this task.
- The prompt **instructions themselves** (the surrounding explanatory text the model reads,
  not the category/polarity values) should be rewritten in Turkish.
- The prompt must be **user-configurable** — the research group can edit it without a code
  change — but ship with a good Turkish default (given below), not an empty template.
- This applies to **all four providers** (Ollama, OpenAI, Anthropic, vLLM) uniformly, **and**
  to the separate Helper Agent chat prompt (see below) — not just the labeling prompt.

### Current state (two separate prompts — don't conflate them)

**1. Labeling prompt** — constructs the prompt sent to the model to produce structured
`(aspect_term, aspect_category, sentiment_polarity, opinion_term)` predictions. Currently
duplicated, in English, inside `predict_llm` (~L640-660) and `predict_openai` (equivalent
block). Task 3 already asked you to refactor `predict_openai` for `base_url` reuse — this task
adds a second reason to factor prompt construction into one shared function all four
`predict_*` functions call, rather than four copies drifting out of sync.

**2. Helper Agent chat prompt** — a *different* prompt, used by `main.py::agent_chat`
(~L1140), for the conversational chat panel (not structured labeling). Currently:
- Already Turkish-language, but hardcoded as an f-string literal in the function body.
- Only wired to OpenAI — no Ollama/Anthropic/vLLM branch. Task 3 built provider dispatch for
  `get_ai_prediction`; `agent_chat` needs the same dispatch, reusing that logic rather than
  duplicating it.
- Contains hardcoded `"DeepSeek tripletleri"` / `"Qwen tripletleri"` strings — this is a
  **second location** with the hardcoded model names Task 2 is meant to generalize; Task 2's
  audit was primarily backend-endpoint- and frontend-focused and may have missed this literal
  string inside `agent_chat`. Fix it here (use the Task 2 config's model display names) rather
  than assuming Task 2 already covers it — check, don't assume.

### What to build

1. **Config mechanism**: two new string fields in the config JSON (loaded via `load_config`,
   consistent with how other config fields work) — e.g. `labeling_prompt_template` and
   `helper_agent_prompt_template`. Support Python `.format()`-style or `{placeholder}` template
   substitution (match whatever templating convention is simplest given the existing codebase
   — don't add a templating library dependency for this). Placeholders needed for the labeling
   prompt: sentiment element definitions, aspect categories list, polarities list, few-shot
   examples block, target text. Placeholders needed for the chat prompt: review text, model A/B
   triplets (using Task 2's generic names, not `deepseek`/`qwen`).
2. **Ship the defaults below** as the out-of-the-box config values — don't leave the config
   field empty by default; that would break existing behavior for users who haven't set it.
3. **Refactor prompt construction into one shared function** used by all four `predict_*`
   functions (Task 3's Anthropic/vLLM additions should call it too — if Task 3 is done first,
   go back and point its two new functions at this shared function rather than writing
   provider-specific prompt text).
4. **Extend `agent_chat` to use the provider dispatch from Task 3** instead of being
   OpenAI-only, and to pull its system prompt from `helper_agent_prompt_template` instead of
   the hardcoded f-string.

### Default Turkish labeling prompt (ship this as the default)

Instructions in Turkish; category/polarity **values** are inserted verbatim in English and
must not be translated by the model. This replaces the English `prompt_head` construction in
`predict_llm`/`predict_openai` — adapt placeholders to whatever your shared prompt function
signature ends up being; the wording below is the actual content to ship, not just an example.

```
Aşağıdaki duygu unsuru tanımlarına göre:

- 'aspect term' (görünüş terimi), kullanıcının bir ürün veya hizmetin belirli bir özelliği
  hakkında görüş belirttiği, metindeki tam kelime veya kelime öbeğidir. {implicit_aspect_note}
- 'aspect category' (görünüş kategorisi), görünüşün ait olduğu kategoridir. Mevcut kategoriler
  (bu kategori adlarını İngilizce olduğu gibi bırakın, çevirmeyin): {aspect_categories}
- 'sentiment polarity' (duygu kutbu), ifade edilen görüşün olumluluk, olumsuzluk ya da nötrlük
  derecesidir. Mevcut kutuplar (İngilizce olduğu gibi bırakın, çevirmeyin): {polarities}
- 'opinion term' (görüş terimi), kullanıcının bir görünüşe yönelik tutumunu ifade eden,
  metindeki tam kelime veya kelime öbeğidir. {implicit_opinion_note}

Metin Türkçedir ve Türkçe sondan eklemeli (agglutinative) bir dildir: aynı kök farklı çekim
ekleriyle görünebilir (ör. "kitap", "kitabı", "kitaplarımdan"). Görünüş ve görüş terimlerini
ararken kelimenin metindeki tam, çekimli halini seçin — kökü ayırıp yeniden yazmayın.

Aşağıdaki metindeki tüm duygu unsurlarını, karşılık gelen {element_names} ile birlikte, her
biri {element_keys} anahtarlarına sahip nesnelerden oluşan bir liste biçiminde tanıyın.
```

Where:
- `{implicit_aspect_note}` = `"Görünüş terimi örtük (implicit) ise 'NULL' olabilir."` when
  `allow_implicit_aspect_terms` is true, else empty string.
- `{implicit_opinion_note}` = same pattern for opinion terms.
- `{aspect_categories}` / `{polarities}` = comma-joined lists, values untranslated.
- `{element_names}` / `{element_keys}` = derived from `considered_sentiment_elements`, same
  role as the current English version's equivalent loop.
- Few-shot examples block and final `Text: {text}\nSentiment elements:` suffix stay
  structurally the same as today (still English `Text:`/`Sentiment elements:` labels are fine
  to keep as-is — they're structural markers, not instructional prose — but ask the user if
  unsure rather than assuming).

### Default Turkish helper agent chat prompt (ship this as the default)

Close to the existing hardcoded string in `agent_chat`, but generalized off `deepseek`/`qwen`
and templated:

```
Sen ABSA (Aspect-Based Sentiment Analysis) veri etiketleme asistanısın. Şu incelemeyi
tartışıyorsunuz: "{review_text}". {model_a_name} tripletleri: {model_a_triplets},
{model_b_name} tripletleri: {model_b_triplets}. Kullanıcıya mantıklı, akıl yürüterek açıklama
yap.
```

### Test case (verifiable, per userPreferences goal-driven execution)

Use a review from the `coursera_train.csv` sample already in Task 1, e.g.:
`"Ayrıca son ödev talimatlarının biraz kafa karıştırıcı olduğunu düşündüm."` — expected
`[['ödev', 'assignments comprehensiveness', 'negative']]`. Before/after check: run this text
through the new Turkish prompt on at least one provider and confirm the returned
`aspect_term` is the correctly-inflected Turkish span (`"ödev"` or a valid inflected form found
in the text), `aspect_category`/`sentiment_polarity` are the correct **English** values, and no
category/polarity value has been translated into Turkish by the model.

---

## Task 5 — Restore original AnnoABSA manual screen + mode toggle

### Why this task exists (context, don't skip)

The current frontend (`App.tsx`) has **one fixed layout**: three columns always rendered
together — Model A comparison | `ManualInputForm` | Model B comparison — plus a chat panel.
This is a from-scratch redesign built for LLM comparison; it is not related to the upstream
[NilsHellwig/AnnoABSA](https://github.com/NilsHellwig/AnnoABSA) UI, which is a **single-column
click-to-select-phrase annotator**: the user selects a span of text directly in the review,
a popup lets them assign aspect term / opinion term / aspect category / sentiment polarity,
annotated phrases are color-highlighted inline, with a dark-mode toggle and a single (not
comparative) AI-suggestion button.

Confirmed by inspection: **this interaction does not exist anywhere in the current codebase.**
`ManualInputForm.tsx` (~164 lines) is a plain three-field dropdown/text form — it never reads
character positions and never sends `at_start`/`at_end`/`ot_start`/`ot_end`. However, the
*backend* already anticipates span-based annotation and has for a while:
- `main.py::load_config` defaults already include `click_on_token`, `auto_clean_phrases`,
  `save_phrase_positions` (~L67-69) — these are served via `/settings` (~L153-155) but currently
  unused by any frontend component.
- Position auto-fill already exists server-side: `get_ai_prediction` calls something that sets
  `aspect['at_start']`/`aspect['at_end']` etc. by string search (~L1023-1034), and there's
  similar logic elsewhere in the file (~L529-603) — **read this code before building the
  frontend piece**, since it tells you the exact position-finding convention (character
  offsets into `review_text`, 0-indexed, inclusive end) your new span-selector must match.

So this task is a **frontend rebuild** of a UI pattern the backend already supports, not new
backend work — verify that claim yourself by reading the position-handling code above before
assuming no backend changes are needed.

### What to build

**1. A new `PhraseAnnotator` component** (or similar name) implementing click/drag-select:
   - Render `review_text` as individual clickable/selectable tokens or characters (config
     flag `click_on_token` — when true, selection snaps to whole tokens; check its default
     and honor it, don't hardcode one behavior).
   - On selection, open a popup/inline form to assign: aspect term (auto-filled from the
     selected span, editable), opinion term (separate span selection, optional — respect
     `implicit_opinion_term_allowed`), aspect category (dropdown from `aspect_category_list`),
     sentiment polarity (dropdown from `sentiment_polarity_options`).
   - Support `NULL`/implicit aspect term (no span selected) when
     `implicit_aspect_term_allowed` is true — mirrors STD format's `NULL` convention from Task 1.
   - Color-highlight confirmed phrases inline in the review text, matching by
     `at_start`/`at_end` (aspect) and `ot_start`/`ot_end` (opinion), distinct colors per
     polarity — reuse whatever color convention already exists for polarity elsewhere in the
     app (check `ModelTripletColumn.tsx`'s polarity badge colors, e.g. emerald/rose/amber
     pattern visible in `ManualInputForm.tsx::getSentimentBadge`) rather than inventing new
     colors, so the "faithful to original design" requirement doesn't clash with "consistent
     with the rest of this fork."
   - Output triplets in the same `TripletItem`-compatible shape used elsewhere
     (`aspect_term`, `aspect_category`, `sentiment_polarity`, plus position fields), so they
     slot into the existing `manualTriplets` state and `handleNextReview` save flow in
     `App.tsx` without changing the save contract.
   - Respect `auto_clean_phrases` if it affects trimming of selected text (check what this
     flag currently does server-side, if anything, before assuming its frontend meaning).

**2. A mode toggle in the app header**, switchable per review (per your instruction — not a
   one-time startup choice):
   - Two modes: **"Compare 2 LLMs"** (existing three-column layout, Model A / (manual entry
     however it's currently embedded) / Model B) and **"Manual"** (new single-column
     `PhraseAnnotator`, full width, replacing the three-column section for that review).
   - Toggle state should be per-review-visit UI state (a `useState` in `App.tsx`), not
     persisted to backend config — this is a display preference, not an annotation setting.
   - Both modes write to the same `manualTriplets`/save flow — switching modes mid-review
     should not lose triplets already added in the other mode (don't clear `manualTriplets`
     on toggle; only clear it on `loadReviewRow`, as today).
   - Keep the "Compare 2 LLMs" mode exactly as it is today, functionally — this task adds an
     alternative, it does not modify the comparison layout itself (that's Task 2's job, and
     Task 2 already covers the `deepseek`/`qwen` renaming — don't duplicate that work here,
     but do rename any hardcoded "DeepSeek"/"Qwen" strings you encounter *inside JSX* in
     `App.tsx` if Task 2 missed them, since Task 2's audit was primarily backend-focused;
     flag to the user if you find such strings rather than silently deciding whose task it is).

**3. Make the Helper Agent chat panel optional**, confirmed by the user (not a guess):
   - Add a second header toggle (independent of the mode toggle above) to show/hide the
     `HelperAgentChatbox` panel. Applies in both "Compare 2 LLMs" and "Manual" modes — it's an
     orthogonal display preference, not tied to which mode is active.
   - Default: visible (matches current behavior for existing users).
   - This is client-side UI state only (no backend/config change needed) — don't add a
     `/settings` field for it unless you find a concrete reason the existing config mechanism
     is a better fit; a plain `useState` (optionally persisted via `localStorage` if you want
     it to survive a page reload — not required, keep it simple if unsure) is sufficient.
   - When hidden, the layout should reclaim the space sensibly (e.g. the "press for next
     review" action area can expand) rather than leaving a blank gap — use your judgment on
     the exact reflow, this isn't prescriptive.

### What NOT to do

- Don't restyle or reskin the existing three-column comparison layout to "look more like"
  original AnnoABSA — "faithful to the original design" applies to the **new manual mode**,
  not a retrofit of the comparison dashboard. The two modes are allowed to look different from
  each other; that's expected, since they're different tools for different tasks.
- Don't touch `HelperAgentChatbox` — out of scope, keep it attached to whichever layout it's
  currently in (confirm with the user whether the chat panel should appear in Manual mode too,
  or only in Compare mode, if that's not obvious after reading `App.tsx`'s current JSX
  structure — this brief doesn't have a firm answer for that specific sub-question either).
- Don't move `at_start`/`at_end` computation logic into the frontend — the backend already
  does this (Task 5's position-finding code references above); frontend only needs to *send*
  positions when the user did the selecting, and *read* them for highlighting when data comes
  pre-annotated (e.g. AI-suggested spans).

### Definition of done

- Toggling to "Manual" mode on any review shows a single-column click-to-select annotator with
  inline highlighted phrases, no comparison columns.
- Selecting a span, assigning category+polarity, and saving produces a triplet with correct
  `at_start`/`at_end` that matches the backend's own position-finding convention (verify by
  comparing against what `get_ai_prediction`'s auto-fill produces for the same span, on the
  same review, as a consistency check).
- Toggling back to "Compare 2 LLMs" mode mid-review does not lose triplets already entered in
  Manual mode for that review.
- `implicit_aspect_term_allowed`/`implicit_opinion_term_allowed`/`click_on_token` config flags
  are read from `/settings` and visibly change annotator behavior (test with each flag both
  true and false).
- The chat-panel toggle hides/shows `HelperAgentChatbox` correctly in both modes, defaults to
  visible, and doesn't affect the mode toggle's own state.

---

## Suggested execution order

1. Task 1 (STD format) — foundational, and Task 2 benefits from reusing its parser.
2. Task 3 (providers) — fully independent, parallelizable with Task 1/2.
3. Task 2 (comparison generalization) — touches more frontend surface area; do after Task 1
   so the STD parser already exists to reuse.
4. Task 4 (prompts) — now fully scoped (no longer blocked), but depends on Task 3's provider
   dispatch (`get_ai_prediction`, and the shared prediction function shape) and Task 2's
   generic model-name config — do after both.
5. Task 5 (manual screen + toggle) — independent of 1-4, but do after Task 2 so the toggle
   isn't wired against comparison-column names that Task 2 is about to rename.

## Cross-cutting notes

- This is a published research tool (AnnoABSA, accepted LREC 2026) with existing example data
  and an evaluation pipeline (`evaluation/`) — don't change existing default behavior (default
  CLI flags, restaurant-domain example config, current JSON/CSV schema) for users not opting
  into the new flags. Every task above is additive.
- `cli.py` already has ~28 flags; follow its existing patterns (`argparse` with sensible
  defaults, config save/load round-trip) rather than introducing a different config mechanism.
