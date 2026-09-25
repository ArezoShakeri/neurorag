"""Orchestrates the offline ingestion pipeline: fetch -> dedup -> OA resolution -> full text
-> chunk -> embed -> write. Each step is a standalone function from another rag/ or retrieval/
module; this file only sequences them, so a future "hybrid" live-retrieval mode can reuse the
same fetch->write steps from a different trigger."""

import hashlib
from dataclasses import dataclass, field
from pathlib import Path

import yaml

from database.chroma_client import add_chunks
from database.schema import ChunkMetadata, today_iso
from rag import chunking
from rag.dedup import dedup
from rag.fulltext_fetcher import fetch_full_text
from rag.oa_resolver import resolve_all
from retrieval import crossref_client, europepmc_client, pubmed_client
from retrieval.models import RawRecord
from settings import REPO_ROOT

WRITE_BATCH_SIZE = 64
EXTRA_JOURNALS_PATH = REPO_ROOT / "database" / "config" / "extra_journals.yaml"
SEED_QUERIES_PATH = REPO_ROOT / "database" / "config" / "seed_queries.yaml"


def load_extra_journals(path: Path = EXTRA_JOURNALS_PATH) -> list[dict]:
    """Shared by the CLI (rag/run_ingestion.py) and the per-conversation live refresh
    (backend/services/corpus_refresh.py) so the journal allow-list is defined once."""
    with open(path) as f:
        return yaml.safe_load(f)["extra_journals"]


def load_seed_queries(path: Path = SEED_QUERIES_PATH) -> list[str]:
    with open(path) as f:
        return yaml.safe_load(f)["seed_queries"]


@dataclass
class IngestionSummary:
    records_fetched: int = 0
    records_after_dedup: int = 0
    open_access_full_text: int = 0
    abstract_only: int = 0
    chunks_written: int = 0
    skipped_no_content: int = 0
    errors: list[str] = field(default_factory=list)


def run_ingestion(
    seed_queries: list[str],
    extra_journals: list[dict],
    max_results_per_query: int = 100,
) -> IngestionSummary:
    summary = IngestionSummary()

    records = _fetch_all(seed_queries, extra_journals, max_results_per_query, summary)
    summary.records_fetched = len(records)

    merged = dedup(records)
    summary.records_after_dedup = len(merged)

    resolved = resolve_all(merged)

    chunk_metadatas: list[ChunkMetadata] = []
    texts: list[str] = []

    for record in resolved:
        try:
            metas, record_texts = _process_record(record, summary)
            chunk_metadatas.extend(metas)
            texts.extend(record_texts)
        except Exception as exc:  # one bad record must not abort the whole ingestion run
            summary.errors.append(f"{record.title[:80]!r}: {exc}")

        if len(chunk_metadatas) >= WRITE_BATCH_SIZE:
            summary.chunks_written += len(add_chunks(chunk_metadatas, texts))
            chunk_metadatas, texts = [], []

    if chunk_metadatas:
        summary.chunks_written += len(add_chunks(chunk_metadatas, texts))

    return summary


def _fetch_all(
    seed_queries: list[str], extra_journals: list[dict], max_results: int, summary: IngestionSummary
) -> list[RawRecord]:
    records: list[RawRecord] = []
    for query in seed_queries:
        try:
            records.extend(europepmc_client.search(query, max_results=max_results))
        except Exception as exc:
            summary.errors.append(f"europepmc query {query!r}: {exc}")
        try:
            records.extend(pubmed_client.search(query, max_results=max_results))
        except Exception as exc:
            summary.errors.append(f"pubmed query {query!r}: {exc}")

    for journal in extra_journals:
        try:
            records.extend(
                crossref_client.search_journal(
                    journal["name"], journal.get("query", "Alzheimer"), max_results=max_results
                )
            )
        except Exception as exc:
            summary.errors.append(f"crossref journal {journal.get('name')!r}: {exc}")

    return records


def _process_record(record: RawRecord, summary: IngestionSummary) -> tuple[list[ChunkMetadata], list[str]]:
    doc_id = _derive_doc_id(record)
    sections = None

    if record.is_open_access:
        sections = fetch_full_text(record)

    if sections:
        summary.open_access_full_text += 1
    elif record.abstract:
        summary.abstract_only += 1

    chunks = chunking.chunk_record(sections, record.abstract)
    if not chunks:
        summary.skipped_no_content += 1
        return [], []

    ingestion_date = today_iso()
    metas = [
        ChunkMetadata(
            chunk_id=f"{doc_id}::chunk_{chunk.chunk_index}",
            doc_id=doc_id,
            title=record.title,
            authors="; ".join(record.authors),
            journal=record.journal,
            publication_year=record.publication_year,
            pmid=record.pmid,
            pmcid=record.pmcid,
            doi=record.doi,
            url=_resolve_url(record),
            source=record.source,
            is_open_access=bool(record.is_open_access),
            full_text_available=bool(sections),
            section=chunk.section,
            chunk_index=chunk.chunk_index,
            ingestion_date=ingestion_date,
        )
        for chunk in chunks
    ]
    texts = [chunk.text for chunk in chunks]
    return metas, texts


def _resolve_url(record: RawRecord) -> str:
    if record.pmcid:
        return f"https://www.ncbi.nlm.nih.gov/pmc/articles/{record.pmcid}/"
    if record.doi:
        return f"https://doi.org/{record.doi}"
    return record.landing_url


def _derive_doc_id(record: RawRecord) -> str:
    if record.pmid:
        return f"pmid_{record.pmid}"
    if record.doi:
        digest = hashlib.sha1(record.doi.lower().encode()).hexdigest()[:12]
        return f"doi_{digest}"
    if record.pmcid:
        return f"pmcid_{record.pmcid}"
    digest = hashlib.sha1(f"{record.title}|{record.publication_year}".encode()).hexdigest()[:12]
    return f"title_{digest}"
