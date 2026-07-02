# AnnoABSA — Project Primer (give this at the start of every session)

You are helping modify **AnnoABSA**, a web-based annotation tool for Aspect-Based Sentiment
Analysis (ABSA), forked/customized for Turkish ABSA research (accepted to LREC 2026).

**You do not have filesystem or repo access.** I will paste you the exact current content of
any file you need to edit. Do not guess at file contents or assume a file looks like a typical
project of this kind — work only from what I paste you. If you need to see a file I haven't
shown you, ask for it by name instead of assuming its contents.

## Stack

- **Backend**: Python, FastAPI (`main.py` — all API endpoints, ~1178 lines), CLI entry point
  (`cli.py` — argparse-based launcher, ~684 lines, starts backend + frontend as subprocesses).
- **Frontend**: React + TypeScript, Vite, Tailwind (`frontend/src/`).
- Data is stored as CSV or JSON, loaded/saved via `main.py::load_data`/`save_data`, switching
  on a global `DATA_FILE_TYPE` ("csv" or "json") set from the file extension.
- LLM prediction (`predict_llm` for Ollama, `predict_openai` for OpenAI) uses BM25 retrieval
  (`rank_bm25`) to pick few-shot examples, then asks the model for structured
  `(aspect_term, aspect_category, sentiment_polarity, opinion_term)` output.

## Working style — follow this strictly

- **One task at a time.** I will give you a single, scoped task per session. Do not attempt to
  address other known issues or "while I'm here" improvements.
- **Minimum code that solves the problem.** No speculative flexibility, no abstractions for
  single-use code, no extra config options I didn't ask for.
- **Surgical changes.** Touch only what the task requires. Don't reformat, refactor, or
  "clean up" adjacent code. Match existing style even if you'd write it differently.
- **State assumptions explicitly.** If something in the task is ambiguous or you're missing
  information (e.g. you need to see a file I haven't pasted), stop and ask — don't guess and
  proceed.
- **Give me a plan before writing code**, in this form, then wait for me to confirm before
  producing the full implementation:
  ```
  1. [Step] → verify: [how I'll check this worked]
  2. [Step] → verify: [how I'll check this worked]
  ```
- **Output format**: give me complete, ready-to-paste file contents (or a clearly-marked diff)
  for each file you change — not partial snippets I have to merge by hand, since I'll be
  copying this into the actual files myself.

## Reference document

I'm working from a written implementation brief (`PHASE1_AGENT_BRIEF.md`) covering 5 tasks.
You will only ever see the one task relevant to the current session, with the actual current
source of the files it touches inlined below the task text — you don't need the whole brief.