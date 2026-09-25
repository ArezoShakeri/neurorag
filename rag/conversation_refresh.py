"""Per-conversation live corpus refresh: on the first message of a new session, runs the
full ingestion pipeline (PubMed + Europe PMC + Crossref/Unpaywall + full-text fetching)
scoped to that question's topic, so answers reflect papers published up to today — not just
whatever was in the corpus from the last batch `python -m rag.run_ingestion` run.

This trades speed for freshness on the first message only (by design — the user chose this
over a lightweight top-up or a static corpus, understanding it makes that one message slower).
Later messages in the same conversation, and all other conversations, benefit from what gets
added here without paying the cost again. A refresh failure must never block answering from
whatever is already in the corpus — this is a best-effort freshness improvement, not a
prerequisite for answering."""

import logging

from rag.ingestion_pipeline import load_extra_journals, run_ingestion
from settings import get_settings

logger = logging.getLogger(__name__)


def refresh_corpus_for_question(question: str) -> bool:
    """Returns True if the refresh completed (regardless of how many/few new chunks it found),
    False if it failed outright. Callers should treat both as non-fatal."""
    settings = get_settings()
    try:
        extra_journals = load_extra_journals()
        summary = run_ingestion(
            seed_queries=[question],
            extra_journals=extra_journals,
            max_results_per_query=settings.conversation_refresh_max_results,
        )
        logger.info(
            "Per-conversation corpus refresh for %r: %d chunks written (%d records after dedup, %d errors).",
            question,
            summary.chunks_written,
            summary.records_after_dedup,
            len(summary.errors),
        )
        return True
    except Exception:
        logger.exception("Per-conversation corpus refresh failed for %r; answering from existing corpus.", question)
        return False
