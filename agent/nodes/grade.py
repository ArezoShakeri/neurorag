"""Filters retrieved chunks for diversity (caps chunks per paper) and ranks by similarity.
Deliberately not an LLM call in milestone 1 — pure scoring keeps latency low on a local model.
Isolated in its own node so swapping in an LLM-based corrective grader later touches only this file."""

from agent.state import AgentState

MAX_CHUNKS_PER_DOC = 3


def grade_relevance(state: AgentState) -> dict:
    chunks = sorted(state.get("retrieved_chunks", []), key=lambda c: c.distance)

    seen_per_doc: dict[str, int] = {}
    graded = []
    for chunk in chunks:
        count = seen_per_doc.get(chunk.metadata.doc_id, 0)
        if count >= MAX_CHUNKS_PER_DOC:
            continue
        seen_per_doc[chunk.metadata.doc_id] = count + 1
        graded.append(chunk)

    return {"graded_chunks": graded}
