"""Thin route layer — parses the request, delegates to backend.services.agent_service, and
translates exceptions to HTTP errors. No graph invocation logic lives here."""

from fastapi import APIRouter, HTTPException

from backend.schemas import QueryRequest, QueryResponse
from backend.services.agent_service import handle_query

router = APIRouter()


@router.post("/query", response_model=QueryResponse)
def query(request: QueryRequest) -> QueryResponse:
    try:
        return handle_query(request)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to process query: {exc}") from exc
