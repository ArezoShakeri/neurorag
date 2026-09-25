"""LangGraph state schema — the data threaded through every node in agent/graph.py."""

from typing import TypedDict

from database.chroma_client import RetrievedChunk
from database.schema import PaperMetadata


class AgentAnswer(TypedDict):
    ai_summary: str
    retrieved_evidence: list[PaperMetadata]
    personal_interpretation: str | None
    total_papers_found: int
    papers_shown: int
    confirmation_prompt: str
    suggested_questions: list[str]


class AgentState(TypedDict, total=False):
    # Input
    original_question: str
    requested_paper_count: int
    allowed_sources: list[str] | None  # None = no source filter ("All")
    year_from: int | None
    year_to: int | None
    is_new_conversation: bool  # gates agent/nodes/refresh_corpus.py

    # classify_intent
    intent: str

    # refresh_corpus
    corpus_refreshed: bool

    # retrieve / grade_relevance
    retrieved_chunks: list[RetrievedChunk]
    graded_chunks: list[RetrievedChunk]

    # synthesize_answer / validate_citations
    draft_summary: str
    draft_interpretation: str | None
    citation_ids: list[str]
    citation_validation_passed: bool
    citation_feedback: str | None
    retry_count: int
    suggested_questions: list[str]

    # format_response / suggest_followups
    final_response: AgentAnswer | None
