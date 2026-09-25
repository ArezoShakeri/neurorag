"""Unpaywall API client — resolves open-access status/location for a DOI when the source
API didn't already provide it (mainly for retrieval.crossref_client records).
Docs: https://unpaywall.org/products/api"""

import httpx
from tenacity import retry, stop_after_attempt, wait_exponential

from settings import get_settings

BASE_URL = "https://api.unpaywall.org/v2"


class OpenAccessStatus:
    def __init__(self, is_open_access: bool, best_oa_url: str | None):
        self.is_open_access = is_open_access
        self.best_oa_url = best_oa_url


@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
def resolve(doi: str) -> OpenAccessStatus | None:
    """Returns None if the DOI isn't found in Unpaywall (e.g. not indexed, malformed)."""
    settings = get_settings()
    with httpx.Client(timeout=20) as client:
        response = client.get(f"{BASE_URL}/{doi}", params={"email": settings.unpaywall_email})
        if response.status_code == 404:
            return None
        response.raise_for_status()
        data = response.json()

    is_oa = bool(data.get("is_oa"))
    best_location = data.get("best_oa_location") or {}
    url = best_location.get("url_for_pdf") or best_location.get("url")
    return OpenAccessStatus(is_open_access=is_oa, best_oa_url=url if is_oa else None)
