from retrieval.europepmc_client import _to_raw_record


def _item(**overrides) -> dict:
    return {"title": "Amyloid paper", "pmid": "1", "source": "MED", "id": "1", **overrides}


def test_reads_journal_from_core_result_type():
    item = _item(journalInfo={"journal": {"title": "Glia", "isoabbreviation": "Glia"}})
    assert _to_raw_record(item).journal == "Glia"


def test_falls_back_to_lite_journal_title():
    assert _to_raw_record(_item(journalTitle="Neurology")).journal == "Neurology"


def test_missing_journal_is_empty_string():
    assert _to_raw_record(_item()).journal == ""
