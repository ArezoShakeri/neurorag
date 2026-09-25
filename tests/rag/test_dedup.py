from rag.dedup import dedup
from retrieval.models import RawRecord


def _record(**overrides) -> RawRecord:
    defaults = dict(
        title="Amyloid paper",
        authors=["A"],
        journal="J",
        publication_year=2023,
        source="pubmed",
        landing_url="u",
    )
    return RawRecord(**{**defaults, **overrides})


def test_no_duplicates_returns_all_records():
    records = [_record(pmid="1"), _record(pmid="2", title="Different paper")]
    result = dedup(records)
    assert len(result) == 2


def test_merges_by_shared_pmid():
    records = [_record(pmid="1", doi=None), _record(pmid="1", doi=None, abstract="abstract text")]
    result = dedup(records)
    assert len(result) == 1
    assert result[0].abstract == "abstract text"


def test_bridges_two_key_groups_when_a_record_links_them():
    # First source only gave a DOI, second only a PMID, third has both and bridges the two.
    a = _record(doi="10.1/x", pmid=None, source="europepmc")
    b = _record(doi=None, pmid="111", source="pubmed", abstract="has abstract")
    c = _record(doi="10.1/x", pmid="111", source="europepmc")

    result = dedup([a, b, c])

    assert len(result) == 1
    assert result[0].doi == "10.1/x"
    assert result[0].pmid == "111"
    assert result[0].abstract == "has abstract"


def test_fuzzy_matches_records_with_no_identity_keys():
    records = [
        _record(title="Amyloid Beta Pathology in AD", publication_year=2023, doi=None, pmid=None),
        _record(title="Amyloid Beta Pathology in AD.", publication_year=2023, doi=None, pmid=None, abstract="x"),
    ]
    result = dedup(records)
    assert len(result) == 1


def test_does_not_merge_different_papers_with_no_identity_keys():
    records = [
        _record(title="Amyloid Beta Pathology", publication_year=2023, doi=None, pmid=None),
        _record(title="Tau Tangle Formation", publication_year=2023, doi=None, pmid=None),
    ]
    result = dedup(records)
    assert len(result) == 2
