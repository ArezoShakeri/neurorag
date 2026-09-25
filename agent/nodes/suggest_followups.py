"""Closes out the no-evidence path with a confirmation check and suggested next questions.
The has-evidence path (agent/nodes/format_response.py) gets its suggestions bundled into
synthesize_answer's own structured output instead — one LLM call, not two — so this node
only runs for respond_no_evidence, where there's no summary yet to bundle it with."""

from agent.constants import CONFIRMATION_PROMPT
from agent.llm_factory import get_chat_model
from agent.schemas import FollowUpOutput
from agent.state import AgentState
from prompts.loader import render_prompt


def suggest_followups(state: AgentState) -> dict:
    model = get_chat_model().with_structured_output(FollowUpOutput)
    prompt = render_prompt(
        "suggest_followups",
        question=state["original_question"],
        summary=state["final_response"]["ai_summary"],
    )
    result: FollowUpOutput = model.invoke(prompt)

    answer = dict(state["final_response"])
    answer["confirmation_prompt"] = CONFIRMATION_PROMPT
    answer["suggested_questions"] = result.suggested_questions
    return {"final_response": answer}
