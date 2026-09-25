"""Crossref REST API client — discovers records from journals outside PubMed/PMC/Europe PMC
(e.g. Alzheimer's Association journals), scoped to an explicit journal allow-list.
Docs: https://api.crossref.org/swagger-ui/index.html"""

import httpx
from tenacity import retry, stop_after_attempt, wait_exponential

from retrieval.models import RawRecord
from retrieval.text_cleaning import strip_html_tags
from settings import get_settings

BASE_URL = "https://api.crossref.org/works"


@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
def _fetch(client: httpx.Client, params: dict) -> dict:
    response = client.get(BASE_URL, params=params)
    response.raise_for_status()
    return response.json()


def search_journal(journal_name: str, query_terms: str, max_results: int = 100) -> list[RawRecord]:
    """Search a specific journal by exact container-title, filtered by bibliographic query terms."""
    settings = get_settings()
    records: list[RawRecord] = []
    rows = min(100, max_results)
    offset = 0
    with httpx.Client(timeout=30, headers={"User-Agent": f"neurorag (mailto:{settings.contact_email})"}) as client:
        while len(records) < max_results:
            data = _fetch(
                client,
                {
                    "query.container-title": journal_name,
                    "query.bibliographic": query_terms,
                    "rows": min(rows, max_results - len(records)),
                    "offset": offset,
                    "select": "DOI,title,author,container-title,published,abstract",
                },
            )
            items = data.get("message", {}).get("items", [])
            if not items:
                break
            records.extend(_to_raw_record(item) for item in items)
            offset += len(items)
            if len(items) < rows:
                break
    return records


def _to_raw_record(item: dict) -> RawRecord:
    doi = item.get("DOI")
    titles = item.get("title") or []
    title = strip_html_tags(titles[0]) if titles else ""

    authors = []
    for author in item.get("author", []):
        given, family = author.get("given"), author.get("family")
        if given and family:
            authors.append(f"{given} {family}")
        elif family:
            authors.append(family)

    journals = item.get("container-title") or []
    journal = strip_html_tags(journals[0]) if journals else ""

    year = None
    date_parts = item.get("published", {}).get("date-parts", [[None]])
    if date_parts and date_parts[0] and date_parts[0][0]:
        year = date_parts[0][0]

    # Crossref abstracts are JATS XML-tagged; strip tags for a plain-text fallback.
    abstract = strip_html_tags(item.get("abstract"))

    return RawRecord(
        title=title or "",
        authors=authors,
        journal=journal or "",
        publication_year=year,
        abstract=abstract or None,
        doi=doi,
        source="crossref_extra",
        landing_url=f"https://doi.org/{doi}" if doi else "",
        is_open_access=None,
        full_text_url=None,
    )
