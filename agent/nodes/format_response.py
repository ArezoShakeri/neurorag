"""Aggregates graded_chunks to the paper level and assembles the final three-part answer:
evidence-based summary, retrieved papers (the 'N most relevant papers' requirement), and an
optional personal interpretation, kept visibly separate per the response-requirements rule."""

from database.chroma_client import RetrievedChunk
from database.schema import paper_from_chunk
from agent.constants import CONFIRMATION_PROMPT
from agent.state import AgentAnswer, AgentState

EXCERPT_MAX_CHARS = 300


def format_response(state: AgentState) -> dict:
    best_by_doc: dict[str, RetrievedChunk] = {}
    for chunk in state["graded_chunks"]:
        existing = best_by_doc.get(chunk.metadata.doc_id)
        if existing is None or chunk.distance < existing.distance:
            best_by_doc[chunk.metadata.doc_id] = chunk

    ranked = sorted(best_by_doc.values(), key=lambda c: c.distance)
    requested = state.get("requested_paper_count", 5)
    shown = ranked[:requested]

    papers = [
        paper_from_chunk(chunk.metadata, excerpt=_excerpt(chunk.text), relevance_score=chunk.distance)
        for chunk in shown
    ]

    answer: AgentAnswer = {
        "ai_summary": state.get("draft_summary", ""),
        "retrieved_evidence": papers,
        "personal_interpretation": state.get("draft_interpretation"),
        "total_papers_found": len(ranked),
        "papers_shown": len(shown),
        # suggested_questions come bundled with synthesize_answer's output (one LLM call,
        # not two) — this path never touches agent/nodes/suggest_followups.py.
        "confirmation_prompt": CONFIRMATION_PROMPT,
        "suggested_questions": state.get("suggested_questions", []),
    }
    return {"final_response": answer}


def respond_no_evidence(state: AgentState) -> dict:
    answer: AgentAnswer = {
        "ai_summary": (
            "No relevant papers were found in the current corpus for this question. "
            "Try rephrasing it, or note that this topic may not be covered by the ingested literature yet."
        ),
        "retrieved_evidence": [],
        "personal_interpretation": None,
        "total_papers_found": 0,
        "papers_shown": 0,
        # filled in by agent/nodes/suggest_followups.py, which runs next
        "confirmation_prompt": "",
        "suggested_questions": [],
    }
    return {"final_response": answer}


def _excerpt(text: str, max_chars: int = EXCERPT_MAX_CHARS) -> str:
    text = text.strip()
    if len(text) <= max_chars:
        return text
    return text[:max_chars].rsplit(" ", 1)[0] + "…"
