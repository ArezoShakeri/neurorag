"""Renders a completed answer with the three sections visibly separated — evidence-based
summary, retrieved evidence, and (optional) personal interpretation — per the response
requirement that these never blend together, for both general-audience and expert readers."""

import json

import streamlit as st
import streamlit.components.v1 as components

from frontend.components.paper_card import render_paper_card


def render_answer(answer: dict, key_prefix: str = "answer") -> None:
    if answer.get("corpus_refreshed"):
        st.caption(
            "🔄 Checking in the background for newly published research on this topic — "
            "this answer used the existing corpus; later messages may include what's found."
        )

    col1, col2 = st.columns([5, 1])
    with col1:
        st.markdown("#### AI-Generated Summary")
    with col2:
        if st.button("🔊 Listen", key=f"{key_prefix}_listen", help="Read the summary aloud"):
            _speak(answer["ai_summary"])
    st.write(answer["ai_summary"])

    st.markdown("#### Retrieved Scientific Evidence")
    papers = answer.get("retrieved_evidence") or []
    if not papers:
        st.info("No papers were retrieved for this question.")
    else:
        st.caption(f"Showing {answer['papers_shown']} of {answer['total_papers_found']} relevant papers found.")
        for paper in papers:
            render_paper_card(paper)

    if answer.get("personal_interpretation"):
        st.markdown("#### Personal Interpretation")
        st.caption("This section reflects an AI-generated opinion, not evidence-backed fact.")
        st.write(answer["personal_interpretation"])

    if answer.get("confirmation_prompt"):
        st.divider()
        st.caption(answer["confirmation_prompt"])


def _speak(text: str) -> None:
    """Reads text aloud via the browser's built-in speech synthesis — no backend TTS model,
    no API cost. Only renders (and only fires) when the Listen button was just pressed, since
    this component is freshly inserted into the DOM on that rerun and its script runs once."""
    js_text = json.dumps(text)
    components.html(
        f"""
        <script>
        window.speechSynthesis.cancel();
        const utterance = new SpeechSynthesisUtterance({js_text});
        window.speechSynthesis.speak(utterance);
        </script>
        """,
        height=0,
    )
