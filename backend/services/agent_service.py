"""Owns the LangGraph invocation and state->response mapping. Routers never touch the graph
directly — this is the one place business logic for handling a query lives."""

import uuid

from agent.graph import get_agent_graph
from agent.state import AgentState
from backend.schemas import AgentAnswerResponse, QueryRequest, QueryResponse


def handle_query(request: QueryRequest) -> QueryResponse:
    is_new_conversation = request.session_id is None
    session_id = request.session_id or str(uuid.uuid4())

    initial_state: AgentState = {
        "original_question": request.question,
        "requested_paper_count": request.num_papers,
        "allowed_sources": request.sources,
        "year_from": request.year_from,
        "year_to": request.year_to,
        "is_new_conversation": is_new_conversation,
        "retry_count": 0,
    }

    graph = get_agent_graph()
    final_state: AgentState = graph.invoke(initial_state)

    return QueryResponse(
        session_id=session_id,
        answer=AgentAnswerResponse(**final_state["final_response"]),
        corpus_refreshed=final_state.get("corpus_refreshed", False),
    )
