"""Hard, code-level enforcement of 'never fabricate references': every cited chunk_id must
exist in graded_chunks, and every number in the summary must appear in the evidence and be tied
to the same treatment the evidence ties it to (agent/claim_checks.py). Model honesty is not
trusted — these checks are what actually prevent a hallucinated citation or figure from reaching
the user."""

from agent.claim_checks import check_numeric_claims, remove_sentences
from agent.state import AgentState

MAX_RETRIES = 1
_NO_VERIFIED_SUMMARY = (
    "I couldn't produce a summary whose figures could all be verified against the retrieved "
    "papers. Please see the papers below directly."
)


def validate_citations(state: AgentState) -> dict:
    valid_ids = {chunk.metadata.chunk_id for chunk in state["graded_chunks"]}
    cited = state.get("citation_ids", [])
    invalid = [c for c in cited if c not in valid_ids]
    claims = check_numeric_claims(state.get("draft_summary", ""), state["graded_chunks"])

    if not invalid and claims.passed:
        return _passed(cited, claims.supporting_chunk_ids)

    retry_count = state.get("retry_count", 0)
    if retry_count < MAX_RETRIES:
        return {
            "citation_validation_passed": False,
            "retry_count": retry_count + 1,
            "citation_feedback": _feedback(invalid, claims.ungrounded, claims.misattributed),
        }

    # Retries exhausted: strip invalid citations and unverifiable sentences rather than ever
    # show a fabricated reference or figure.
    summary = remove_sentences(state.get("draft_summary", ""), claims.bad_sentences) or _NO_VERIFIED_SUMMARY
    return {**_passed([c for c in cited if c in valid_ids], claims.supporting_chunk_ids), "draft_summary": summary}


def _passed(cited: list[str], supporting: set[str]) -> dict:
    # Credit every chunk a figure was taken from, even if the model forgot to cite it.
    extra = sorted(supporting - set(cited))
    return {"citation_validation_passed": True, "citation_ids": cited + extra, "citation_feedback": None}


def _feedback(invalid: list[str], ungrounded: list[str], misattributed: list[str]) -> str:
    problems = []
    if invalid:
        problems.append(
            f"You cited chunk_id(s) that were not in the provided evidence: {', '.join(invalid)}. "
            "Only cite chunk_ids explicitly listed above."
        )
    if ungrounded:
        problems.append(
            "These numbers do not appear anywhere in the evidence — remove them or copy the exact "
            "figure from the evidence: " + "; ".join(ungrounded)
        )
    if misattributed:
        problems.append(
            "These numbers are attributed to the wrong treatment — in the evidence they belong to a "
            "different drug. Re-read the evidence and attribute each figure correctly: " + "; ".join(misattributed)
        )
    return "Your previous answer had problems:\n- " + "\n- ".join(problems)
