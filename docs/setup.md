# Setup

## Prerequisites

- Python 3.11+
- [Ollama](https://ollama.com) running locally (`ollama serve`, or the desktop app)

## 1. Install dependencies

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

## 2. Configure

```bash
cp .env.example .env
```

Edit `.env` and set `UNPAYWALL_EMAIL` / `CONTACT_EMAIL` to a real email address — Unpaywall
rejects placeholder domains like `example.com`. An `NCBI_API_KEY` is optional but raises PubMed
rate limits from 3 to 10 req/sec (free, from your NCBI account settings).

## 3. Pull the local LLM

```bash
ollama pull qwen3:8b
```

Needs ~6 GB RAM/VRAM, runs comfortably on a 16 GB laptop. Chosen over `qwen2.5:7b-instruct`
and `gemma3:12b` in a side-by-side test on the same questions: faster than both (~20s per answer
on an M2 Pro vs ~33s and ~70s), and its first drafts had no figure-attribution errors caught by
`agent/claim_checks.py`. Thinking mode is disabled in `agent/llm_factory.py`. Any Ollama model
works — change `OLLAMA_MODEL` in `.env`, no code change needed.

## 4. Populate the vector store

```bash
python -m rag.run_ingestion
```

Fetches from PubMed, Europe PMC, and the extra journals in
`database/config/extra_journals.yaml`, then chunks, embeds, and writes to
`database/chroma_store/`. Takes roughly 10-20 minutes for the default seed query set
(`database/config/seed_queries.yaml`). Use `--max-results 20` for a quick smoke-test run.

## 5. Run the app

Two terminals:

```bash
uvicorn backend.main:app --reload
```

```bash
streamlit run frontend/app.py
```

Open http://localhost:8501. API docs (Swagger UI) are at http://localhost:8000/docs.

The backend's first startup also downloads the local Whisper speech-to-text model
(`WHISPER_MODEL_SIZE`, default `base`, ~75 MB) — no manual step needed, it's a normal Python
dependency (`faster-whisper`), just a one-time model download on first run.

Heads up: the first message of every new conversation kicks off a live corpus refresh in the
background (fetches current literature on that question's topic) if the question is Alzheimer's/
dementia-related. It doesn't block that first answer — you'll get a normal-speed response using
the existing corpus — but newly-fetched papers only become searchable a little later, once the
background fetch finishes. See `docs/architecture.md` for why it's backgrounded rather than
blocking (short version: blocking made the app appear broken when shared through a tunnel with a
short edge timeout).

## Switching to the Anthropic API later

Set in `.env`:

```
LLM_PROVIDER=anthropic
ANTHROPIC_API_KEY=sk-...
```

No code changes — `agent/llm_factory.py` picks it up automatically.

## Running tests

```bash
pytest
```

This runs the offline unit tests only (no network calls, no running Ollama required). Tests
that need a live corpus or Ollama are documented but not included in the default `pytest` run
for milestone 1 — see `docs/architecture.md` for the manual end-to-end verification steps.
