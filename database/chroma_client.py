"""Chroma vector store access. The only module that talks to Chroma directly — ingestion writes
and query-time retrieval both go through the functions here."""

from dataclasses import dataclass
from functools import lru_cache

from langchain_chroma import Chroma

from database.embedding_factory import get_embedding_model
from database.schema import ChunkMetadata
from settings import get_settings


@lru_cache
def get_chroma_store() -> Chroma:
    settings = get_settings()
    settings.chroma_persist_dir.mkdir(parents=True, exist_ok=True)
    return Chroma(
        collection_name=settings.chroma_collection_name,
        embedding_function=get_embedding_model(),
        persist_directory=str(settings.chroma_persist_dir),
    )


def add_chunks(chunks: list[ChunkMetadata], texts: list[str]) -> list[str]:
    """Embed and persist chunks. Used by the offline ingestion pipeline."""
    if len(chunks) != len(texts):
        raise ValueError("chunks and texts must be the same length")
    if not chunks:
        return []
    store = get_chroma_store()
    ids = [chunk.chunk_id for chunk in chunks]
    metadatas = [chunk.to_chroma_metadata() for chunk in chunks]
    return store.add_texts(texts=texts, metadatas=metadatas, ids=ids)


@dataclass
class RetrievedChunk:
    metadata: ChunkMetadata
    text: str
    distance: float  # lower is more similar


def similarity_search(
    query: str,
    k: int,
    sources: list[str] | None = None,
    year_from: int | None = None,
    year_to: int | None = None,
) -> list[RetrievedChunk]:
    """Query-time retrieval. Used by the agent's `retrieve` node. `sources`/`year_from`/
    `year_to` apply a metadata filter over the corpus (e.g. the sidebar resource filters) —
    None/unset means no restriction on that dimension."""
    store = get_chroma_store()
    where = _build_where_clause(sources, year_from, year_to)
    results = store.similarity_search_with_score(query, k=k, filter=where)
    retrieved = []
    for document, distance in results:
        metadata = ChunkMetadata.from_chroma_result(document.id, document.metadata)
        retrieved.append(RetrievedChunk(metadata=metadata, text=document.page_content, distance=distance))
    return retrieved


def _build_where_clause(sources: list[str] | None, year_from: int | None, year_to: int | None) -> dict | None:
    clauses = []
    if sources:
        clauses.append({"source": {"$in": sources}})
    if year_from is not None:
        clauses.append({"publication_year": {"$gte": year_from}})
    if year_to is not None:
        clauses.append({"publication_year": {"$lte": year_to}})

    if not clauses:
        return None
    if len(clauses) == 1:
        return clauses[0]
    return {"$and": clauses}
