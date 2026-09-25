# Ingestion workflow

Plain-English recipe for how `python -m rag.run_ingestion` populates the corpus.

1. **Fetch** — for each seed query in `database/config/seed_queries.yaml`, search Europe PMC
   and PubMed. For each journal in `database/config/extra_journals.yaml`, search Crossref
   scoped to that exact journal title.
2. **Dedup** — merge records that are the same paper across sources, matched by DOI, then PMID,
   then PMCID, then (if none of those are present) fuzzy title+year matching. Fields missing on
   one duplicate are backfilled from another (e.g. one source has the abstract, another has the
   PMCID).
3. **Resolve open access** — trust a source-provided OA flag (Europe PMC, PMC). For records
   with no OA flag (mainly Crossref discoveries), look up the DOI in Unpaywall.
4. **Fetch full text — open access only** — PMC's structured XML (section-labeled) preferred;
   otherwise the best OA location's PDF, extracted with pypdf. Paywalled records stop here with
   only their abstract/metadata kept — never scraped.
5. **Chunk** — section-aware (~450 words, ~70-word overlap) when full text sections are known;
   otherwise a single abstract-only chunk.
6. **Embed and write** — chunks are embedded (local sentence-transformers model) and written to
   ChromaDB in batches, tagged with the full paper metadata (title, authors, journal, year,
   PMID, PMCID, DOI, URL, source, OA status).

A summary prints at the end: records fetched, records after dedup, open-access vs
abstract-only counts, chunks written, and any per-record errors (non-fatal — one bad record
never aborts the run).
