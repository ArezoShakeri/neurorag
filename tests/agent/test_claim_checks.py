from agent.claim_checks import check_numeric_claims, remove_sentences
from agent.nodes.validate_citations import validate_citations
from database.chroma_client import RetrievedChunk
from database.schema import ChunkMetadata

# Real passage (PMID 42180238) where a 7B model swapped the two drugs' figures.
ANTIBODY_EVIDENCE = (
    "For instance, lecanemab treatment resulted in a mean reduction of the standardized uptake value "
    "ratio (SUVR) for cerebral amyloid burden by 59.1% (95% CI: 56.3 to -61.9%) from baseline at 18 "
    "months. In the donanemab phase 3 trial, the mean reduction in amyloid plaque burden was 85.1% "
    "(95% CI: 83.4 to -86.8%) from baseline at 18 months. Cognitive benefits, however, were more "
    "modest: lecanemab treatment corresponded to an approximate 27% slowing of clinical decline."
)


def _chunk(chunk_id: str, text: str) -> RetrievedChunk:
    meta = ChunkMetadata(
        chunk_id=chunk_id, doc_id=chunk_id.split("::")[0], title="Some paper", authors="A", journal="J",
        publication_year=2026, url="u", source="pubmed", is_open_access=True, full_text_available=True,
        section="full_text", chunk_index=0, ingestion_date="2026-01-01",
    )
    return RetrievedChunk(metadata=meta, text=text, distance=0.1)


CHUNKS = [_chunk("pmid_1::chunk_3", ANTIBODY_EVIDENCE), _chunk("pmid_2::chunk_0", "Sleep matters.")]


def test_correct_attribution_passes_and_credits_source_chunk():
    summary = "Donanemab reduced amyloid plaque by 85.1%, while lecanemab reduced it by 59.1%."
    result = check_numeric_claims(summary, CHUNKS)
    assert result.passed
    assert result.supporting_chunk_ids == {"pmid_1::chunk_3"}


def test_swapped_drug_figure_is_flagged_as_misattributed():
    summary = "Lecanemab reduced amyloid plaque burden by 85.1% and slowed decline by 27%."
    result = check_numeric_claims(summary, CHUNKS)
    assert len(result.misattributed) == 1
    assert "85.1" in result.misattributed[0] and "lecanemab" in result.misattributed[0]


def test_treatment_named_after_the_number_is_used():
    summary = "Plaque fell by 85.1% in donanemab-treated patients compared to 59.1% with lecanemab."
    assert check_numeric_claims(summary, CHUNKS).passed


def test_number_absent_from_evidence_is_ungrounded():
    result = check_numeric_claims("Lecanemab slowed decline by 41.7%.", CHUNKS)
    assert len(result.ungrounded) == 1


def test_rounded_integer_percentage_is_accepted():
    assert check_numeric_claims("Donanemab cleared about 85% of plaque.", CHUNKS).passed


def test_identifiers_and_bare_integers_are_ignored():
    summary = "Plasma p-tau217 and APOE ε4 status were measured in 2024 across 3 phase trials."
    result = check_numeric_claims(summary, CHUNKS)
    assert result.passed and not result.supporting_chunk_ids


def test_remove_sentences_keeps_the_rest():
    summary = "First claim. Bad claim with 41.7%. Last claim."
    assert remove_sentences(summary, {"Bad claim with 41.7%."}) == "First claim. Last claim."


def test_validate_retries_on_misattribution_then_strips_sentence():
    state = {
        "graded_chunks": CHUNKS,
        "citation_ids": ["pmid_1::chunk_3"],
        "draft_summary": "Anti-amyloid antibodies modestly slow decline. Lecanemab reduced plaque by 85.1%.",
        "retry_count": 0,
    }
    first = validate_citations(state)
    assert first["citation_validation_passed"] is False
    assert "wrong treatment" in first["citation_feedback"]

    final = validate_citations({**state, "retry_count": 1})
    assert final["citation_validation_passed"] is True
    assert final["draft_summary"] == "Anti-amyloid antibodies modestly slow decline."


def test_validate_adds_uncited_supporting_chunks():
    state = {
        "graded_chunks": CHUNKS,
        "citation_ids": ["pmid_2::chunk_0"],
        "draft_summary": "Lecanemab slowed clinical decline by about 27%.",
        "retry_count": 0,
    }
    result = validate_citations(state)
    assert result["citation_validation_passed"] is True
    assert result["citation_ids"] == ["pmid_2::chunk_0", "pmid_1::chunk_3"]
