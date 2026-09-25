"""Thin HTTP client for the backend API. The only module in frontend/ that knows the API shape."""

import httpx

from settings import get_settings

# The per-conversation live corpus refresh (rag/conversation_refresh.py) now runs in the
# background rather than blocking the response (agent/nodes/refresh_corpus.py), so a normal
# query should always return well within this — kept comfortably under free tunnel services'
# (e.g. Cloudflare quick tunnels) ~100s edge timeout, so a genuine hang fails fast and clearly
# instead of the tunnel silently dropping the connection.
REQUEST_TIMEOUT_SECONDS = 90


class BackendUnavailableError(Exception):
    pass


def post_query(
    question: str,
    session_id: str | None,
    num_papers: int,
    sources: list[str] | None = None,
    year_from: int | None = None,
    year_to: int | None = None,
) -> dict:
    settings = get_settings()
    payload = {
        "question": question,
        "session_id": session_id,
        "num_papers": num_papers,
        "sources": sources,
        "year_from": year_from,
        "year_to": year_to,
    }
    try:
        response = httpx.post(f"{settings.backend_url}/api/v1/query", json=payload, timeout=REQUEST_TIMEOUT_SECONDS)
        response.raise_for_status()
        return response.json()
    except httpx.HTTPError as exc:
        raise BackendUnavailableError(f"Could not reach the backend at {settings.backend_url}: {exc}") from exc


def transcribe_audio(audio_bytes: bytes, content_type: str = "audio/wav") -> str:
    settings = get_settings()
    try:
        response = httpx.post(
            f"{settings.backend_url}/api/v1/transcribe",
            files={"audio": ("recording.wav", audio_bytes, content_type)},
            timeout=60,
        )
        response.raise_for_status()
        return response.json()["text"]
    except httpx.HTTPError as exc:
        raise BackendUnavailableError(f"Could not reach the backend at {settings.backend_url}: {exc}") from exc
