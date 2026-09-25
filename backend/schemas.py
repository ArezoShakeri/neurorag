"""Request/response contracts for the API. Reuses database.schema.PaperMetadata as the
single source of truth for paper fields — no separate duplicate model here."""

from pydantic import BaseModel, Field

from database.schema import PaperMetadata, Source
from settings import get_settings


class QueryRequest(BaseModel):
    question: str = Field(min_length=1)
    session_id: str | None = None
    num_papers: int = Field(default_factory=lambda: get_settings().default_num_papers, ge=1, le=25)
    sources: list[Source] | None = Field(default=None, description="Restrict to these sources. None/empty = all.")
    year_from: int | None = Field(default=None, ge=1900)
    year_to: int | None = Field(default=None, ge=1900)


class AgentAnswerResponse(BaseModel):
    ai_summary: str
    retrieved_evidence: list[PaperMetadata]
    personal_interpretation: str | None
    total_papers_found: int
    papers_shown: int
    confirmation_prompt: str
    suggested_questions: list[str]


class QueryResponse(BaseModel):
    session_id: str
    answer: AgentAnswerResponse
    corpus_refreshed: bool = False


class TranscriptionResponse(BaseModel):
    text: str
