"""Entry node: routes the question before doing any retrieval. Replaces the old pre-answer
clarification gate with a routing decision instead of a blocking question — the agent always
answers, but answers differently depending on what kind of question this is."""

from agent.llm_factory import get_chat_model
from agent.schemas import IntentOutput
from agent.state import AgentState
from prompts.loader import render_prompt


def classify_intent(state: AgentState) -> dict:
    model = get_chat_model().with_structured_output(IntentOutput)
    prompt = render_prompt("classify_intent", question=state["original_question"])
    result: IntentOutput = model.invoke(prompt)
    return {"intent": result.intent}
