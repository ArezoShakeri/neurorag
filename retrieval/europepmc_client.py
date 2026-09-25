"""Europe PMC REST API client — the primary source: one call surfaces PMID/PMCID/DOI,
open-access status, and a full-text URL when available.
Docs: https://europepmc.org/RestfulWebService"""

import httpx
from tenacity import retry, stop_after_attempt, wait_exponential

from retrieval.models import RawRecord
from retrieval.text_cleaning import strip_html_tags

BASE_URL = "https://www.ebi.ac.uk/europepmc/webservices/rest/search"


@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
def _fetch_page(client: httpx.Client, query: str, cursor_mark: str, page_size: int) -> dict:
    response = client.get(
        BASE_URL,
        params={
            "query": query,
            "format": "json",
            "resultType": "core",
            "pageSize": page_size,
            "cursorMark": cursor_mark,
        },
    )
    response.raise_for_status()
    return response.json()


def search(query: str, max_results: int = 200, page_size: int = 100) -> list[RawRecord]:
    """Search Europe PMC and return normalized records, following cursorMark pagination."""
    records: list[RawRecord] = []
    cursor_mark = "*"
    with httpx.Client(timeout=30) as client:
        while len(records) < max_results:
            data = _fetch_page(client, query, cursor_mark, min(page_size, max_results - len(records)))
            results = data.get("resultList", {}).get("result", [])
            if not results:
                break
            records.extend(_to_raw_record(item) for item in results)
            next_cursor = data.get("nextCursorMark")
            if not next_cursor or next_cursor == cursor_mark:
                break
            cursor_mark = next_cursor
    return records


def _journal_title(item: dict) -> str:
    """resultType=core nests the journal under journalInfo; the flat journalTitle field only
    exists in the lite format, so check both."""
    journal = item.get("journalInfo", {}).get("journal", {})
    title = journal.get("title") or journal.get("isoabbreviation") or item.get("journalTitle") or ""
    return strip_html_tags(title) or ""


def _to_raw_record(item: dict) -> RawRecord:
    pmid = item.get("pmid")
    pmcid = item.get("pmcid")
    doi = item.get("doi")
    is_oa = item.get("isOpenAccess") == "Y"

    full_text_url = None
    for link in item.get("fullTextUrlList", {}).get("fullTextUrl", []):
        if link.get("availability", "").lower().startswith("open access"):
            full_text_url = link.get("url")
            break

    landing_url = (
        f"https://europepmc.org/article/{item['source']}/{item['id']}"
        if item.get("source") and item.get("id")
        else f"https://doi.org/{doi}" if doi else ""
    )

    year = None
    if item.get("pubYear"):
        try:
            year = int(item["pubYear"])
        except ValueError:
            year = None

    return RawRecord(
        title=strip_html_tags(item.get("title", "")) or "",
        authors=[a.strip() for a in item.get("authorString", "").split(",") if a.strip()],
        journal=_journal_title(item),
        publication_year=year,
        abstract=strip_html_tags(item.get("abstractText")),
        pmid=pmid,
        pmcid=pmcid,
        doi=doi,
        source="europepmc",
        landing_url=landing_url,
        is_open_access=is_oa,
        full_text_url=full_text_url,
    )
