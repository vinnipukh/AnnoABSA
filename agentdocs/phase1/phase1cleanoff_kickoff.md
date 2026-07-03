# Phase 1 Cleanup — Kickoff

Same working rules as the Phase 1 primer: one task at a time (there are 4 below, but treat
them as a sequence, not a batch — plan→verify→wait for go-ahead, per task), no filesystem
access on your end — **I do not have your current `main.py`/`cli.py`/`App.tsx` contents
either**, only the 5 completion reports. Where a task needs to see current code, ask for it by
name before proposing a plan. Don't guess at what the completion reports imply the code looks
like — confirm against the actual file.

This is a **cleanup pass**, not new feature work. Every change should trace directly to one of
the 4 items below. Do not refactor, "improve," or touch anything else you notice while in
these files — if you spot something unrelated, mention it, don't fix it.

---

## Task A (Critical) — Confirm which save endpoint the frontend actually uses

### Why this matters

Two competing endpoints exist in `main.py`:

```python
@app.post("/annotations/{data_idx}")
def post_annotations(data_idx: int, annotation_data: AnnotationData): ...

@app.post("/review/{data_idx}/save")
def save_review_triplets(data_idx: int, req: SaveTripletsRequest): ...
```

This was flagged during Task 1 planning and never resolved in writing. Every completion
report since then assumes annotations flow through "the existing save flow" without stating
which endpoint that is:
- Task 1's report: STD-loaded data "works through `post_annotations`" — stated, not verified
  against what the frontend calls.
- Task 5's report: `PhraseAnnotator` outputs feed into "the existing `manualTriplets` state and
  `handleNextReview` save flow" — doesn't name the endpoint `handleNextReview` hits.

If these two endpoints diverge in behavior (e.g. one validates differently, one is dead code
nobody removed), you need to know which one is load-bearing before either report's claims can
be trusted.

### What to do

1. Grep `frontend/src/App.tsx` for `fetch` calls containing `/annotations/` or `/review/` and
   `/save`. Paste me what you find.
2. State definitively: which endpoint does `handleNextReview` (or whatever the actual save
   handler is now called) call?
3. If the *other* endpoint (`post_annotations` or `save_review_triplets`, whichever is unused)
   has no callers anywhere in the frontend, say so explicitly — don't delete it (that's outside
   this task's scope), just confirm and report it as dead code for me to decide on separately.
4. If both are somehow called from different code paths (e.g. Compare mode uses one, Manual
   mode uses the other), state that clearly — that's a more important finding than either
   single-endpoint answer, and changes what "the save flow" means in every prior report.

### Verify

- You can point to the exact line in `App.tsx` showing which endpoint is called from the live
  save path, for both Compare mode and Manual mode.
- If a save-endpoint fetch call exists inside `PhraseAnnotator.tsx` itself (rather than
  `App.tsx`), check there too — don't assume `App.tsx` owns all save calls.

---

## Task B (Critical) — Provider auto-derivation silently falls back to Ollama

### Current state (per Task 3's completion report — confirm against actual code before fixing)

```
If --llm-provider is omitted, it auto-derives: openai if --openai-key is set, else ollama
```

This only accounts for two of the four providers. If a user sets `--anthropic-key` or
`--vllm-url` but forgets `--llm-provider`, the tool silently falls through to `ollama` — not
an error, not the provider they clearly intended to configure. This is worse than doing
nothing, because it fails silently with a plausible-looking but wrong provider instead of
failing loudly.

### What to do

1. Ask me for the actual current derivation logic in `cli.py` (function name, exact code) —
   the snippet above is a paraphrase from a report, not source.
2. Extend the derivation to check all four provider-identifying config values:
   `openai_key`, `anthropic_key`, `vllm_url` (Ollama has no identifying key — it's the
   fallback only when *nothing* else is set).
3. If **more than one** of `openai_key`/`anthropic_key`/`vllm_url` is set and
   `--llm-provider` was not explicitly passed, **fail with a clear error** rather than picking
   one silently — the user configured something ambiguous and needs to resolve it themselves.
   Something in this shape (adapt to match the actual current code style/error-handling
   pattern in `cli.py`, don't introduce a new error-handling convention):

   ```python
   configured = [name for name, val in [
       ("openai", openai_key), ("anthropic", anthropic_key), ("vllm", vllm_url)
   ] if val]

   if not args.llm_provider:
       if len(configured) > 1:
           print(f"❌ Error: multiple providers configured ({', '.join(configured)}) but "
                 f"--llm-provider not specified. Pick one explicitly.")
           sys.exit(1)
       elif len(configured) == 1:
           args.llm_provider = configured[0]
       else:
           args.llm_provider = "ollama"
   ```

4. If exactly one of the three is set and `--llm-provider` is omitted, auto-derive to that one
   (this extends today's openai-only behavior to all three cloud providers, consistent with
   what a user would expect).
5. If none are set, fall back to `ollama` (unchanged from today).

### Verify

- `--anthropic-key sk-... ` alone (no `--llm-provider`) → derives to `anthropic`, not `ollama`.
- `--vllm-url http://... ` alone → derives to `vllm`.
- `--openai-key sk-...` alone → derives to `openai` (unchanged, confirm no regression).
- `--anthropic-key sk-... --openai-key sk-...` together, no `--llm-provider` → CLI exits with
  the ambiguity error, does not silently pick one.
- No keys/URLs at all, no `--llm-provider` → still derives to `ollama` (unchanged).
- Explicit `--llm-provider anthropic` with no `--anthropic-key` → still hits the existing
  fail-fast validation from Task 3 (don't touch that check, just confirm it still fires).

---

## Task C (Critical) — Task 5 has no executed tests, only static inspection

### Why this matters

Compare the verification sections across reports:

- Task 2: *"32/32 checks passed"* — executed.
- Task 3: *"43/43 tests passed"* — executed.
- Task 4: *"8/8 verification groups passed"* — executed.
- Task 5: *"confirmed by inspection of `PhraseAnnotator.tsx`,"* *"confirmed by reading
  `App.tsx` state management"* — **none of this was actually run.**

Task 5 is also the riskiest task in the batch: a new 375-line component doing character-level
DOM rendering, click/drag span selection, and position math that has to match the backend's
convention exactly. "I read the code and it looks right" is meaningfully weaker evidence here
than for the other four tasks, precisely because span-selection math is the kind of thing that
looks correct on read-through and is wrong by one character in practice.

### What to do

Actually run the app and manually exercise Manual mode, end to end:

1. Start the app with a small test dataset (reuse the STD sample from Task 1's kickoff if
   convenient, or any 2-3 row dataset).
2. Switch to Manual mode via the header toggle.
3. Select a span of text (test both `click_on_token: true` and `click_on_token: false`, since
   these use different selection logic per the report).
4. Assign a category + polarity, save.
5. **Compare the saved `at_start`/`at_end` against what the backend would independently
   compute for the same span** — e.g. call `GET /ai_prediction/{idx}` on the same review (which
   uses the backend's own position-finding) or manually check `text.find(selected_phrase)`
   against what got saved. They should agree.
6. Test the `NULL`/implicit checkbox path — save an implicit aspect, confirm no position fields
   get incorrectly populated (should mirror the `!= 'NULL'` skip behavior from
   `auto_add_missing_positions`).
7. Toggle back to Compare mode mid-review, confirm the triplet from step 4 is still present.
8. Toggle the chat panel off, confirm no visual overlap with other UI elements (see Task D).

### Verify

- Report actual before/after values for the position check in step 5 — not "it looked right,"
  the actual numbers.
- If anything in steps 1-8 fails or behaves unexpectedly, report it as a bug — don't quietly
  patch it as part of this task unless the fix is trivial (one line, obviously correct); if it
  needs real design thought, stop and report back rather than improvising a fix under this
  "cleanup" task's scope.

---

## Task D (Minor) — Confirm the floating chat panel doesn't overlap other UI

### Current state (per Task 5's report)

The chat toggle was implemented with absolute/floating positioning (bottom-right widget)
instead of the in-flow "reflow" the original kickoff asked for. That's a reasonable
simplification — floating avoids needing reflow logic entirely — but it wasn't the specified
approach, so it needs a visual check it wasn't given.

### What to do

With the chat panel visible, check it doesn't visually overlap: the mode toggle, the
`PhraseAnnotator`'s popup form (when a span is selected near the bottom-right of the screen),
and the "next review" action button/area. Check at a couple of screen widths if the app is
meant to be responsive; if it's desktop-only, one reasonable viewport size is enough.

### Verify

- Screenshot or explicit description of no-overlap at the review area's bottom-right, with the
  chat panel open and a `PhraseAnnotator` popup also open at the same time (the worst-case
  combination).
- If overlap exists, report it — don't redesign the positioning under this task unless the fix
  is a one-line CSS adjustment (e.g. z-index or margin), consistent with Task C's rule about
  not improvising larger fixes mid-cleanup.

---

## Order

A → B → C → D. A and B are independent of each other and could be done in either order or
in parallel sessions if you prefer, but both are prerequisites for trusting C's manual save-flow
walkthrough (you need to know which endpoint you're actually testing in step 5).

## What I need from you, per task

1. If you need current file contents beyond what's quoted/paraphrased above, ask by name.
2. A plan in the `[Step] → verify: [check]` format.
3. Wait for my go-ahead before implementing.
4. Full file contents or clearly marked diffs for anything you change — and for Task C, the
actual test output/values, not a summary claiming it passed./