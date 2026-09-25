# Architecture

## Two pipelines, one vector store

```
frontend/ (Streamlit) --HTTP--> backend/ (FastAPI) --> agent/ (LangGraph) --> database/ (Chroma + embeddings)
                                                             ^
                                                         prompts/

retrieval/ (PubMed/PMC/EuropePMC/Crossref/Unpaywall) --> rag/ (dedup/OA/chunk) --> database/
```

- **Offline ingestion** (`retrieval/` → `rag/` → `database/`): a batch job (`python -m
  rag.run_ingestion`) that populates ChromaDB. Run it whenever you want to refresh or expand
  the corpus.
- **Per-conversation live refresh** (`rag/conversation_refresh.py`): on the first message of a
  new conversation, if the question is disease-relevant, kicks off the same full ingestion
  pipeline scoped to that question's topic in a **background thread**
  (`agent/nodes/refresh_corpus.py`), so answers reflect papers published up to today without
  blocking the response. Runs async rather than inline — the full pipeline can take 1-3+ minutes,
  which both makes for a slow first message and exceeds the ~100s edge timeout of free tunnel
  services (e.g. Cloudflare quick tunnels) when the app is shared externally, so blocking on it
  made the whole first turn look broken for anyone but the person running it locally. Backgrounding
  it means the current answer uses whatever's already in the corpus; newly-fetched papers land a
  little later, benefiting the next message in that conversation or other conversations.
- **Online query** (`frontend/` → `backend/` → `agent/` → `database/`): read-only against
  Chroma, plus one embedding call for the incoming question.

Fetch (`retrieval/`) and write-to-vector-store (`rag/` + `database/`) are kept as separate,
composable functions — the live refresh reuses the exact same `rag.ingestion_pipeline.run_ingestion`
used for batch ingestion, just scoped to one question instead of the seed query list.

## Query flow

1. Streamlit posts `{question, session_id, num_papers, sources, year_from, year_to}` to
   `POST /api/v1/query`.
2. `backend/services/agent_service.py` builds the initial agent state and invokes the compiled
   LangGraph (`agent/graph.py`).
3. `classify_intent` — LLM call routing the question into `about_agent`, `off_topic`, or
   `disease_relevant`. The agent always answers directly (no pre-answer clarification gate);
   this routes to a different answering strategy instead of blocking with a question:
   - `about_agent` → `answer_about_agent` answers from a static context block (project goal,
     sources, limitations) — no retrieval, no citations, no papers shown.
   - `off_topic` → `answer_off_topic` returns a fixed apology + redirect message. Deliberately
     makes **no LLM call at all** — nothing to ground, so a static response is both the fastest
     and the most reliable option.
   - `disease_relevant` → proceeds to `refresh_corpus` then the normal RAG flow below.
4. `refresh_corpus` — only starts the live per-conversation refresh (see above) if this is the
   first message of a new conversation; a no-op otherwise. Fires the refresh in a background
   thread and returns immediately — does not wait for it, and a refresh failure never blocks
   answering from whatever's already in the corpus.
5. `retrieve` — embeds the question, queries Chroma for the top-K candidate chunks, filtered by
   the sidebar's source/year selections if set. No LLM call.
6. `grade_relevance` — ranks by similarity and caps chunks per paper for diversity. No LLM call.
7. `synthesize_answer` — LLM call, grounded strictly in the graded chunks (capped to the top 8
   by relevance regardless of how many papers are shown — the single biggest speed lever, since
   local-model latency scales with prompt length). Returns structured output (`evidence_summary`,
   `citations: list[chunk_id]`, optional `interpretation`, **and** `suggested_questions` — bundled
   into this one call rather than a separate follow-up call).
8. `validate_citations` — **hard, code-level check**: every cited `chunk_id` must exist in the
   graded set. One corrective retry on failure; anything still invalid afterward is stripped,
   never shown. A second, regex-based safety net (`agent/nodes/synthesize.py::_strip_internal_ids`)
   also strips any raw `chunk_id`/`doc_id` the model might leak into the prose itself — belt and
   suspenders on "don't trust the model, enforce in code."
9. `format_response` (or `respond_no_evidence` + `suggest_followups` if nothing relevant was
   found — the no-evidence path is the only one still using a separate follow-up-suggestion call,
   since there's no summary yet to bundle it with) — assembles the final answer: summary,
   retrieved papers, confirmation prompt, suggested questions.

## Metadata schema

`database/schema.py` defines `ChunkMetadata` (stored in Chroma, one per retrievable chunk) and
`PaperMetadata` (paper-level, returned by the API). Both ingestion and the backend response
mapping use these same models — no duplicate field definitions.

Per-chunk fields: `chunk_id, doc_id, title, authors, journal, publication_year, pmid, pmcid,
doi, url, source, is_open_access, full_text_available, section, chunk_index, ingestion_date`.

`retrieve` can filter on `source` (`$in`) and `publication_year` (`$gte`/`$lte`) via a Chroma
`where` clause — see `database/chroma_client.py::_build_where_clause`.

## Open-access handling

Full text is only ingested for confirmed open-access articles (source-provided OA flag, or
resolved via Unpaywall for Crossref-discovered records). Paywalled articles are kept as
metadata/abstract-only records — never scraped — and surface in results tagged "Abstract only".

## LLM / embedding / speech provider abstraction

- `agent/llm_factory.py` returns a `BaseChatModel`; `LLM_PROVIDER=ollama` (default, local, free)
  or `LLM_PROVIDER=anthropic` (+ `ANTHROPIC_API_KEY`) — a config change, not a code change.
  `LLM_MAX_OUTPUT_TOKENS` bounds worst-case decode time.
- `database/embedding_factory.py` returns local sentence-transformers embeddings, model set via
  `EMBEDDING_MODEL_NAME`.
- `backend/services/transcription.py` returns a local `faster-whisper` model (`WHISPER_MODEL_SIZE`)
  for voice input — audio never leaves the machine. Text-to-speech (the "Listen" button) uses the
  browser's built-in `speechSynthesis` API instead of a backend model — zero cost, zero setup.

## Speed levers

In order of impact: (1) merging `suggested_questions` into `synthesize_answer`'s own structured
output instead of a second LLM call, (2) capping how many chunks reach the synthesis prompt
(`SYNTHESIS_CHUNK_LIMIT`, independent of how many papers are displayed), (3) `LLM_MAX_OUTPUT_TOKENS`
bounding decode length, (4) the `off_topic` path skipping the LLM entirely. None of these affect
citation grounding — `validate_citations` still runs against the full graded set either way.
