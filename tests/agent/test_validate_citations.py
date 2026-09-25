from agent.nodes.validate_citations import validate_citations
from database.chroma_client import RetrievedChunk
from database.schema import ChunkMetadata


def _chunk(chunk_id: str) -> RetrievedChunk:
    meta = ChunkMetadata(
        chunk_id=chunk_id,
        doc_id="doc1",
        title="Some paper",
        authors="A",
        journal="J",
        publication_year=2023,
        url="u",
        source="pubmed",
        is_open_access=True,
        full_text_available=True,
        section="abstract",
        chunk_index=0,
        ingestion_date="2026-01-01",
    )
    return RetrievedChunk(metadata=meta, text="some text", distance=0.1)


def test_all_citations_valid_passes_immediately():
    state = {"graded_chunks": [_chunk("doc1::chunk_0")], "citation_ids": ["doc1::chunk_0"], "retry_count": 0}
    result = validate_citations(state)
    assert result["citation_validation_passed"] is True
    assert result["citation_feedback"] is None


def test_hallucinated_citation_triggers_retry():
    state = {"graded_chunks": [_chunk("doc1::chunk_0")], "citation_ids": ["doc1::chunk_0", "fabricated::chunk_9"], "retry_count": 0}
    result = validate_citations(state)
    assert result["citation_validation_passed"] is False
    assert result["retry_count"] == 1
    assert "fabricated::chunk_9" in result["citation_feedback"]


def test_invalid_citation_stripped_after_retries_exhausted():
    state = {
        "graded_chunks": [_chunk("doc1::chunk_0")],
        "citation_ids": ["doc1::chunk_0", "fabricated::chunk_9"],
        "retry_count": 1,  # MAX_RETRIES already reached
    }
    result = validate_citations(state)
    assert result["citation_validation_passed"] is True
    assert result["citation_ids"] == ["doc1::chunk_0"]
    assert "fabricated::chunk_9" not in result["citation_ids"]


def test_no_citations_at_all_passes_trivially():
    state = {"graded_chunks": [_chunk("doc1::chunk_0")], "citation_ids": [], "retry_count": 0}
    result = validate_citations(state)
    assert result["citation_validation_passed"] is True
