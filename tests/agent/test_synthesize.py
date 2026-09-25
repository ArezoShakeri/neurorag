from agent.nodes.synthesize import _strip_internal_ids


def test_strips_parenthetical_pmid():
    text = "Donanemab was approved by the FDA (pmid_42338648) for treating AD."
    assert "pmid_42338648" not in _strip_internal_ids(text)


def test_strips_bracketed_pmcid_with_chunk_suffix():
    text = "This is discussed in detail [pmcid_PMC12819041::chunk_2] in the trial data."
    result = _strip_internal_ids(text)
    assert "pmcid_PMC12819041" not in result
    assert "chunk_2" not in result


def test_strips_doi_and_title_hash_ids():
    text = "See doi_1a2b3c4d5e6f and title_9f8e7d6c5b4a for more."
    result = _strip_internal_ids(text)
    assert "doi_1a2b3c4d5e6f" not in result
    assert "title_9f8e7d6c5b4a" not in result


def test_leaves_normal_prose_untouched():
    text = "Amyloid-beta plaques are a hallmark feature of Alzheimer's disease pathology."
    assert _strip_internal_ids(text) == text


def test_collapses_leftover_whitespace():
    text = "A finding (pmid_123) followed by more text."
    result = _strip_internal_ids(text)
    assert "  " not in result


def test_no_stray_space_before_punctuation():
    text = "diverse populations (pmid_42338648). This approval marks progress."
    result = _strip_internal_ids(text)
    assert " ." not in result
    assert result == "diverse populations. This approval marks progress."
