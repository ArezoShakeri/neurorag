"""Fetch full text for confirmed open-access records only. Paywalled records never reach here —
callers must check `record.is_open_access` first (rag/ingestion_pipeline.py does this)."""

import httpx
from pypdf import PdfReader
from tenacity import retry, stop_after_attempt, wait_exponential

from retrieval.models import RawRecord

PMC_OA_FULLTEXT_URL = "https://www.ebi.ac.uk/europepmc/webservices/rest/{pmcid}/fullTextXML"

_SECTION_KEYWORDS = {
    "introduction": "introduction",
    "background": "introduction",
    "method": "methods",
    "material": "methods",
    "result": "results",
    "discussion": "discussion",
    "conclusion": "discussion",
}


@retry(stop=stop_after_attempt(2), wait=wait_exponential(multiplier=1, min=2, max=8))
def fetch_full_text(record: RawRecord) -> dict[str, str] | None:
    """Best-effort full-text fetch, returned as {section_label: text}. Returns None (falls
    back to abstract-only chunking) if no full text can be retrieved — not a hard failure
    for the ingestion run. PMC's structured XML yields real section labels; PDF/HTML
    fallbacks yield a single "full_text" section."""
    if not record.is_open_access:
        raise ValueError("fetch_full_text called on a non-open-access record")

    if record.pmcid:
        sections = _fetch_pmc_fulltext(record.pmcid)
        if sections:
            return sections

    if record.full_text_url:
        text = _fetch_generic_url(record.full_text_url)
        if text:
            return {"full_text": text}

    return None


def _classify_section(title: str) -> str:
    lowered = title.lower()
    for keyword, label in _SECTION_KEYWORDS.items():
        if keyword in lowered:
            return label
    return "full_text"


def _fetch_pmc_fulltext(pmcid: str) -> dict[str, str] | None:
    from xml.etree import ElementTree

    url = PMC_OA_FULLTEXT_URL.format(pmcid=pmcid)
    with httpx.Client(timeout=30) as client:
        response = client.get(url)
        if response.status_code != 200:
            return None
        try:
            root = ElementTree.fromstring(response.text)
        except ElementTree.ParseError:
            return None
        body = root.find(".//body")
        if body is None:
            return None

        sections: dict[str, list[str]] = {}
        top_level_secs = body.findall("./sec")
        if not top_level_secs:
            text = " ".join(t.strip() for t in body.itertext() if t.strip())
            return {"full_text": text} if text else None

        for sec in top_level_secs:
            title_el = sec.find("title")
            label = _classify_section(title_el.text) if title_el is not None and title_el.text else "full_text"
            text = " ".join(t.strip() for t in sec.itertext() if t.strip())
            if text:
                sections.setdefault(label, []).append(text)

        return {label: " ".join(parts) for label, parts in sections.items()} or None


def _fetch_generic_url(url: str) -> str | None:
    with httpx.Client(timeout=30, follow_redirects=True) as client:
        response = client.get(url)
        if response.status_code != 200:
            return None
        content_type = response.headers.get("content-type", "")
        if "pdf" in content_type or url.lower().endswith(".pdf"):
            return _extract_pdf_text(response.content)
        return None  # HTML full text is publisher-formatted and unreliable to parse generically


def _extract_pdf_text(pdf_bytes: bytes) -> str | None:
    import io

    try:
        reader = PdfReader(io.BytesIO(pdf_bytes))
        text = "\n".join(page.extract_text() or "" for page in reader.pages)
        return text.strip() or None
    except Exception:
        return None
