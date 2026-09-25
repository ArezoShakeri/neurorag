"""Gates the live per-conversation corpus refresh (rag/conversation_refresh.py) behind two
conditions: it must be the first message of a new conversation, AND the question must be
disease-relevant (this node only sits on that branch of the graph) — no point spending the
refresh cost on an "about the agent" or off-topic first message.

Runs the refresh in a background thread rather than blocking the request on it. The full
ingestion pipeline can take 1-3+ minutes (network calls to Europe PMC/PubMed/Unpaywall, full-text
fetching), which — beyond just being a slow first message — exceeded the ~100s edge timeout of
free tunnel services (e.g. Cloudflare quick tunnels) when this app was shared externally, making
the whole first turn appear broken for anyone but the person running it locally. Backgrounding it
means retrieve/synthesize proceed immediately against the existing corpus; newly-fetched papers
land a little later, benefiting the next message in this conversation or other conversations,
rather than necessarily this exact answer. That's a reasonable trade for the answer actually
returning."""

import threading

from agent.state import AgentState
from rag.conversation_refresh import refresh_corpus_for_question


def refresh_corpus(state: AgentState) -> dict:
    if not state.get("is_new_conversation"):
        return {"corpus_refreshed": False}

    question = state["original_question"]
    threading.Thread(target=refresh_corpus_for_question, args=(question,), daemon=True).start()
    return {"corpus_refreshed": True}  # a refresh was *started*, not necessarily finished yet
