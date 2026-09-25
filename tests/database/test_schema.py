from database.schema import ChunkMetadata, paper_from_chunk


def _chunk(**overrides) -> ChunkMetadata:
    defaults = dict(
        chunk_id="doc1::chunk_0",
        doc_id="doc1",
        title="Some paper",
        authors="Jane Doe; John Smith",
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
    return ChunkMetadata(**{**defaults, **overrides})


def test_to_chroma_metadata_omits_none_fields():
    meta = _chunk(pmid=None, pmcid=None, doi=None)
    data = meta.to_chroma_metadata()
    assert "pmid" not in data
    assert "pmcid" not in data
    assert "doi" not in data
    assert data["chunk_id"] == "doc1::chunk_0"


def test_chroma_round_trip_preserves_fields():
    meta = _chunk(pmid="123")
    data = meta.to_chroma_metadata()
    restored = ChunkMetadata.from_chroma_result(None, data)
    assert restored == meta


def test_paper_from_chunk_splits_joined_authors():
    meta = _chunk(authors="Jane Doe; John Smith")
    paper = paper_from_chunk(meta)
    assert paper.authors == ["Jane Doe", "John Smith"]
    assert paper.doc_id == meta.doc_id
