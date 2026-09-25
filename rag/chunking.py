"""Splits a record's text into retrievable chunks. Independent of ChunkMetadata/doc identity —
rag/ingestion_pipeline.py combines this output with record-level fields to build ChunkMetadata."""

from dataclasses import dataclass

WORDS_PER_CHUNK = 450
OVERLAP_WORDS = 70


@dataclass
class Chunk:
    section: str
    chunk_index: int
    text: str


def chunk_record(sections: dict[str, str] | None, abstract: str | None) -> list[Chunk]:
    """Section-aware chunking when full-text sections are available (from rag.fulltext_fetcher);
    a single abstract-only chunk otherwise. Never both — full text supersedes the abstract."""
    if sections:
        chunks = []
        index = 0
        for section_label, text in sections.items():
            for piece in _split_words(text):
                chunks.append(Chunk(section=section_label, chunk_index=index, text=piece))
                index += 1
        return chunks

    if abstract:
        return [Chunk(section="abstract", chunk_index=0, text=abstract)]

    return []


def _split_words(text: str, chunk_size: int = WORDS_PER_CHUNK, overlap: int = OVERLAP_WORDS) -> list[str]:
    words = text.split()
    if len(words) <= chunk_size:
        return [text] if words else []

    pieces = []
    step = chunk_size - overlap
    for start in range(0, len(words), step):
        piece_words = words[start : start + chunk_size]
        if not piece_words:
            break
        pieces.append(" ".join(piece_words))
        if start + chunk_size >= len(words):
            break
    return pieces
