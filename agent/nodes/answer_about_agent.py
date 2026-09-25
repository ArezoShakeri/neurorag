"""Answers questions about the assistant itself (goal, sources, limitations) from static
context — no retrieval, no citations, no suggested papers, per the locked design decision
that meta-questions about the agent shouldn't trigger a literature search."""

from agent.constants import ABOUT_AGENT_SUGGESTIONS, AGENT_CONTEXT, CONFIRMATION_PROMPT
from agent.llm_factory import get_chat_model
from agent.state import AgentAnswer, AgentState
from prompts.loader import render_prompt


def answer_about_agent(state: AgentState) -> dict:
    model = get_chat_model()
    prompt = render_prompt("answer_about_agent", agent_context=AGENT_CONTEXT, question=state["original_question"])
    response = model.invoke(prompt)

    answer: AgentAnswer = {
        "ai_summary": response.content,
        "retrieved_evidence": [],
        "personal_interpretation": None,
        "total_papers_found": 0,
        "papers_shown": 0,
        "confirmation_prompt": CONFIRMATION_PROMPT,
        "suggested_questions": ABOUT_AGENT_SUGGESTIONS,
    }
    return {"final_response": answer}
