from rag.chunking import chunk_record


def test_abstract_only_when_no_sections():
    chunks = chunk_record(sections=None, abstract="Short abstract text.")
    assert len(chunks) == 1
    assert chunks[0].section == "abstract"
    assert chunks[0].chunk_index == 0


def test_no_content_returns_empty_list():
    assert chunk_record(sections=None, abstract=None) == []


def test_sections_supersede_abstract():
    sections = {"methods": "word " * 10}
    chunks = chunk_record(sections=sections, abstract="Should be ignored")
    assert all(c.section == "methods" for c in chunks)


def test_long_section_splits_into_overlapping_chunks():
    long_text = " ".join(f"word{i}" for i in range(1000))
    chunks = chunk_record(sections={"results": long_text}, abstract=None)
    assert len(chunks) > 1
    assert [c.chunk_index for c in chunks] == list(range(len(chunks)))


def test_short_section_is_a_single_chunk():
    chunks = chunk_record(sections={"discussion": "A short discussion section."}, abstract=None)
    assert len(chunks) == 1
    assert chunks[0].text == "A short discussion section."
