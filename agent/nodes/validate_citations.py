"""Hard, code-level enforcement of 'never fabricate references': every cited chunk_id must
exist in graded_chunks. Model honesty is not trusted — this check is what actually prevents
a hallucinated citation from reaching the user."""

from agent.state import AgentState

MAX_RETRIES = 1


def validate_citations(state: AgentState) -> dict:
    valid_ids = {chunk.metadata.chunk_id for chunk in state["graded_chunks"]}
    cited = state.get("citation_ids", [])
    invalid = [c for c in cited if c not in valid_ids]

    if not invalid:
        return {"citation_validation_passed": True, "citation_feedback": None}

    retry_count = state.get("retry_count", 0)
    if retry_count < MAX_RETRIES:
        feedback = (
            f"Your previous answer cited chunk_id(s) that were not in the provided evidence: "
            f"{', '.join(invalid)}. Only cite chunk_ids explicitly listed above."
        )
        return {"citation_validation_passed": False, "retry_count": retry_count + 1, "citation_feedback": feedback}

    # Retries exhausted: strip invalid citations rather than ever show a fabricated one.
    return {
        "citation_validation_passed": True,
        "citation_ids": [c for c in cited if c in valid_ids],
        "citation_feedback": None,
    }
