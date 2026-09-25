"""Rejects off-topic questions with a fixed apology + redirect message. Deliberately makes
no LLM call at all — there is nothing to ground, so the fastest and most reliable answer is
a static one; an LLM call here would only add latency and a (small but nonzero) chance of the
model drifting off the "I can't help with that" message."""

from agent.constants import CONFIRMATION_PROMPT, EXAMPLE_DISEASE_QUESTIONS, OFF_TOPIC_MESSAGE
from agent.state import AgentAnswer, AgentState


def answer_off_topic(state: AgentState) -> dict:
    answer: AgentAnswer = {
        "ai_summary": OFF_TOPIC_MESSAGE,
        "retrieved_evidence": [],
        "personal_interpretation": None,
        "total_papers_found": 0,
        "papers_shown": 0,
        "confirmation_prompt": CONFIRMATION_PROMPT,
        "suggested_questions": EXAMPLE_DISEASE_QUESTIONS,
    }
    return {"final_response": answer}
