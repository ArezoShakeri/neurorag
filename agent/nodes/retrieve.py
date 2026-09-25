"""Embeds the question and queries Chroma. No LLM call."""

from database.chroma_client import similarity_search
from agent.state import AgentState
from settings import get_settings


def retrieve(state: AgentState) -> dict:
    settings = get_settings()
    chunks = similarity_search(
        state["original_question"],
        k=settings.retrieval_candidate_k,
        sources=state.get("allowed_sources"),
        year_from=state.get("year_from"),
        year_to=state.get("year_to"),
    )
    return {"retrieved_chunks": chunks}
