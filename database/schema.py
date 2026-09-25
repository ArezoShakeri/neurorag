"""Shared metadata models — the single source of truth used by ingestion, retrieval, and API responses."""

from datetime import date
from typing import Literal

from pydantic import BaseModel, Field

Source = Literal["pubmed", "pmc", "europepmc", "crossref_extra"]
Section = Literal["abstract", "introduction", "methods", "results", "discussion", "full_text"]


class ChunkMetadata(BaseModel):
    """One retrievable unit stored in Chroma. Metadata values must stay flat scalars."""

    chunk_id: str
    doc_id: str
    title: str
    authors: str  # "; "-joined — Chroma metadata values must be flat scalars, not lists
    journal: str
    publication_year: int | None = None
    pmid: str | None = None
    pmcid: str | None = None
    doi: str | None = None
    url: str
    source: Source
    is_open_access: bool
    full_text_available: bool
    section: Section
    chunk_index: int
    ingestion_date: str  # ISO date string

    def to_chroma_metadata(self) -> dict:
        """Chroma rejects None values, so omit unset optional fields instead of sending null.
        chunk_id is duplicated into metadata (in addition to being the Chroma-level id) so
        retrieval doesn't depend on the langchain Document.id field being populated."""
        data = self.model_dump()
        return {k: v for k, v in data.items() if v is not None}

    @classmethod
    def from_chroma_result(cls, chunk_id: str | None, metadata: dict) -> "ChunkMetadata":
        resolved_id = chunk_id or metadata["chunk_id"]
        return cls(**{**metadata, "chunk_id": resolved_id})


class PaperMetadata(BaseModel):
    """Paper-level view returned to API clients — aggregated from one or more chunks of the same doc_id."""

    doc_id: str
    title: str
    authors: list[str]
    journal: str
    publication_year: int | None = None
    pmid: str | None = None
    pmcid: str | None = None
    doi: str | None = None
    url: str
    source: Source
    is_open_access: bool
    full_text_available: bool
    excerpt: str | None = Field(default=None, description="Representative snippet from the most relevant chunk")
    relevance_score: float | None = Field(default=None, description="Lower is more relevant (embedding distance)")


def paper_from_chunk(chunk: ChunkMetadata, excerpt: str | None = None, relevance_score: float | None = None) -> PaperMetadata:
    """Build the API-facing PaperMetadata from a stored ChunkMetadata. Single mapping point to avoid drift."""
    return PaperMetadata(
        doc_id=chunk.doc_id,
        title=chunk.title,
        authors=[a.strip() for a in chunk.authors.split(";") if a.strip()],
        journal=chunk.journal,
        publication_year=chunk.publication_year,
        pmid=chunk.pmid,
        pmcid=chunk.pmcid,
        doi=chunk.doi,
        url=chunk.url,
        source=chunk.source,
        is_open_access=chunk.is_open_access,
        full_text_available=chunk.full_text_available,
        excerpt=excerpt,
        relevance_score=relevance_score,
    )


def today_iso() -> str:
    return date.today().isoformat()
