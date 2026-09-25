"""PubMed E-utilities client — supplements Europe PMC with any records it misses.
Docs: https://www.ncbi.nlm.nih.gov/books/NBK25501/"""

from xml.etree import ElementTree

import httpx
from tenacity import retry, stop_after_attempt, wait_exponential

from retrieval.models import RawRecord
from settings import get_settings

ESEARCH_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi"
EFETCH_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi"
BATCH_SIZE = 150


def _common_params() -> dict:
    settings = get_settings()
    params = {"tool": "neurorag", "email": settings.contact_email}
    if settings.ncbi_api_key:
        params["api_key"] = settings.ncbi_api_key
    return params


@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
def _esearch(client: httpx.Client, query: str, retmax: int) -> list[str]:
    response = client.get(
        ESEARCH_URL,
        params={**_common_params(), "db": "pubmed", "term": query, "retmax": retmax, "retmode": "json"},
    )
    response.raise_for_status()
    return response.json().get("esearchresult", {}).get("idlist", [])


@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
def _efetch(client: httpx.Client, pmids: list[str]) -> str:
    response = client.get(
        EFETCH_URL,
        params={**_common_params(), "db": "pubmed", "id": ",".join(pmids), "rettype": "abstract", "retmode": "xml"},
    )
    response.raise_for_status()
    return response.text


def search(query: str, max_results: int = 200) -> list[RawRecord]:
    """Search PubMed and return normalized records."""
    with httpx.Client(timeout=30) as client:
        pmids = _esearch(client, query, max_results)
        records: list[RawRecord] = []
        for i in range(0, len(pmids), BATCH_SIZE):
            batch = pmids[i : i + BATCH_SIZE]
            xml_text = _efetch(client, batch)
            records.extend(_parse_pubmed_xml(xml_text))
    return records


def _parse_pubmed_xml(xml_text: str) -> list[RawRecord]:
    root = ElementTree.fromstring(xml_text)
    records = []
    for article in root.findall(".//PubmedArticle"):
        record = _parse_article(article)
        if record:
            records.append(record)
    return records


def _parse_article(article: ElementTree.Element) -> RawRecord | None:
    pmid_el = article.find(".//PMID")
    pmid = pmid_el.text if pmid_el is not None else None
    title_el = article.find(".//ArticleTitle")
    title = "".join(title_el.itertext()).strip() if title_el is not None else None
    if not title:
        return None

    abstract_parts = [
        "".join(node.itertext()) for node in article.findall(".//Abstract/AbstractText")
    ]
    abstract = " ".join(part.strip() for part in abstract_parts if part.strip()) or None

    authors = []
    for author in article.findall(".//AuthorList/Author"):
        last = author.findtext("LastName")
        fore = author.findtext("ForeName")
        if last and fore:
            authors.append(f"{fore} {last}")
        elif last:
            authors.append(last)

    journal = article.findtext(".//Journal/Title") or article.findtext(".//Journal/ISOAbbreviation") or ""

    year = None
    year_text = article.findtext(".//JournalIssue/PubDate/Year") or article.findtext(
        ".//JournalIssue/PubDate/MedlineDate"
    )
    if year_text:
        digits = "".join(c for c in year_text[:4] if c.isdigit())
        year = int(digits) if len(digits) == 4 else None

    doi = None
    pmcid = None
    for article_id in article.findall(".//ArticleIdList/ArticleId"):
        id_type = article_id.get("IdType")
        if id_type == "doi":
            doi = article_id.text
        elif id_type == "pmc":
            pmcid = article_id.text

    return RawRecord(
        title=title,
        authors=authors,
        journal=journal,
        publication_year=year,
        abstract=abstract,
        pmid=pmid,
        pmcid=pmcid,
        doi=doi,
        source="pubmed",
        landing_url=f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/" if pmid else (f"https://doi.org/{doi}" if doi else ""),
        is_open_access=None,
        full_text_url=None,
    )
