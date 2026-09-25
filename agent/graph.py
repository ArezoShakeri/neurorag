"""Wires the LangGraph nodes into the agent's control flow:

classify_intent -> [about_agent]      -> answer_about_agent -> END
                 -> [off_topic]       -> answer_off_topic -> END   (no LLM call — fastest path)
                 -> [disease_relevant]-> refresh_corpus (only on first message of a new conversation)
                                             -> retrieve -> grade_relevance -> [no evidence] -> respond_no_evidence -> suggest_followups -> END
                                                                             -> [has evidence] -> synthesize_answer (bundles suggested_questions)
                                                                                                      -> validate_citations
                                                                                                             -> [invalid, retries left] -> synthesize_answer
                                                                                                             -> [valid] -> format_response -> END

The agent always answers directly (no pre-answer clarification gate). classify_intent routes
to a different answering strategy depending on what kind of question this is, rather than
blocking with a clarifying question.
"""

from functools import lru_cache

from langgraph.graph import END, StateGraph

from agent.nodes.answer_about_agent import answer_about_agent
from agent.nodes.answer_off_topic import answer_off_topic
from agent.nodes.classify_intent import classify_intent
from agent.nodes.format_response import format_response, respond_no_evidence
from agent.nodes.grade import grade_relevance
from agent.nodes.refresh_corpus import refresh_corpus
from agent.nodes.retrieve import retrieve
from agent.nodes.suggest_followups import suggest_followups
from agent.nodes.synthesize import synthesize_answer
from agent.nodes.validate_citations import validate_citations
from agent.state import AgentState


def _route_after_intent(state: AgentState) -> str:
    return state.get("intent", "disease_relevant")


def _route_after_grade(state: AgentState) -> str:
    return "has_evidence" if state.get("graded_chunks") else "no_evidence"


def _route_after_validate(state: AgentState) -> str:
    return "valid" if state.get("citation_validation_passed") else "retry"


def build_graph():
    graph = StateGraph(AgentState)

    graph.add_node("classify_intent", classify_intent)
    graph.add_node("answer_about_agent", answer_about_agent)
    graph.add_node("answer_off_topic", answer_off_topic)
    graph.add_node("refresh_corpus", refresh_corpus)
    graph.add_node("retrieve", retrieve)
    graph.add_node("grade_relevance", grade_relevance)
    graph.add_node("synthesize_answer", synthesize_answer)
    graph.add_node("validate_citations", validate_citations)
    graph.add_node("format_response", format_response)
    graph.add_node("respond_no_evidence", respond_no_evidence)
    graph.add_node("suggest_followups", suggest_followups)

    graph.set_entry_point("classify_intent")
    graph.add_conditional_edges(
        "classify_intent",
        _route_after_intent,
        {
            "about_agent": "answer_about_agent",
            "off_topic": "answer_off_topic",
            "disease_relevant": "refresh_corpus",
        },
    )
    graph.add_edge("answer_about_agent", END)
    graph.add_edge("answer_off_topic", END)

    graph.add_edge("refresh_corpus", "retrieve")
    graph.add_edge("retrieve", "grade_relevance")
    graph.add_conditional_edges(
        "grade_relevance", _route_after_grade, {"has_evidence": "synthesize_answer", "no_evidence": "respond_no_evidence"}
    )
    graph.add_edge("respond_no_evidence", "suggest_followups")
    graph.add_edge("suggest_followups", END)
    graph.add_edge("synthesize_answer", "validate_citations")
    graph.add_conditional_edges(
        "validate_citations", _route_after_validate, {"valid": "format_response", "retry": "synthesize_answer"}
    )
    graph.add_edge("format_response", END)

    return graph.compile()


@lru_cache
def get_agent_graph():
    return build_graph()
