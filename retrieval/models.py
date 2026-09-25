"""Normalized record shape every source client returns, before dedup/OA resolution/chunking."""

from pydantic import BaseModel

from database.schema import Source


class RawRecord(BaseModel):
    title: str
    authors: list[str] = []
    journal: str = ""
    publication_year: int | None = None
    abstract: str | None = None
    pmid: str | None = None
    pmcid: str | None = None
    doi: str | None = None
    source: Source
    landing_url: str
    is_open_access: bool | None = None  # None = unknown, resolved later by rag/oa_resolver.py
    full_text_url: str | None = None  # known OA full-text location, if the source already provides one

    def merge_key_candidates(self) -> list[str]:
        """Ordered identity keys used for cross-source dedup: DOI > PMID > PMCID."""
        keys = []
        if self.doi:
            keys.append(f"doi:{self.doi.lower().strip()}")
        if self.pmid:
            keys.append(f"pmid:{self.pmid.strip()}")
        if self.pmcid:
            keys.append(f"pmcid:{self.pmcid.strip()}")
        return keys
