"""Chat loop: question input (typed or spoken), and the 'show more papers' / suggested-
follow-up controls that appear after each answer. The agent always answers directly — there
is no pre-answer clarification round-trip; instead every answer ends with a confirmation
check and suggested next questions (agent/nodes/suggest_followups.py), which render here as
clickable buttons."""

import hashlib

import streamlit as st

from frontend.api_client import BackendUnavailableError, post_query, transcribe_audio
from frontend.components.answer_display import render_answer

SHOW_MORE_INCREMENT = 5


def _init_state(default_num_papers: int) -> None:
    st.session_state.setdefault("messages", [])
    st.session_state.setdefault("session_id", None)
    st.session_state.setdefault("last_question", None)
    st.session_state.setdefault("num_papers", default_num_papers)
    st.session_state.setdefault("can_show_more", False)
    st.session_state.setdefault("suggested_questions", [])
    st.session_state.setdefault("last_audio_hash", None)


def render_chat(default_num_papers: int) -> None:
    _init_state(default_num_papers)

    for i, message in enumerate(st.session_state.messages):
        with st.chat_message(message["role"]):
            if message.get("answer"):
                render_answer(message["answer"], key_prefix=f"msg_{i}")
            else:
                st.write(message["content"])

    if st.session_state.can_show_more:
        if st.button("Show more papers"):
            st.session_state.num_papers += SHOW_MORE_INCREMENT
            _ask(st.session_state.last_question)

    if st.session_state.suggested_questions:
        st.caption("You might also ask:")
        for i, suggestion in enumerate(st.session_state.suggested_questions):
            if st.button(suggestion, key=f"suggestion_{i}_{suggestion[:20]}"):
                _ask(suggestion)

    _handle_voice_input()

    prompt = st.chat_input("Ask a question about Alzheimer's disease research...")
    if prompt:
        _ask(prompt)


def _handle_voice_input() -> None:
    audio = st.audio_input("Or ask by voice", key="voice_recorder")
    if audio is None:
        return

    audio_bytes = audio.getvalue()
    audio_hash = hashlib.md5(audio_bytes).hexdigest()
    if audio_hash == st.session_state.last_audio_hash:
        return  # same recording as last run — already processed, avoid re-transcribing on rerun
    st.session_state.last_audio_hash = audio_hash

    with st.spinner("Transcribing..."):
        try:
            text = transcribe_audio(audio_bytes)
        except BackendUnavailableError as exc:
            st.error(str(exc))
            return

    if text.strip():
        _ask(text.strip())
    else:
        st.warning("Didn't catch that — please try recording again.")


def _ask(question: str) -> None:
    st.session_state.messages.append({"role": "user", "content": question})
    _run_query(question)


def _run_query(question: str) -> None:
    st.session_state.last_question = question

    with st.spinner("Searching literature and synthesizing an answer..."):
        try:
            result = post_query(
                question=question,
                session_id=st.session_state.session_id,
                num_papers=st.session_state.num_papers,
                sources=st.session_state.get("allowed_sources"),
                year_from=st.session_state.get("year_from"),
                year_to=st.session_state.get("year_to"),
            )
        except BackendUnavailableError as exc:
            st.session_state.messages.append({"role": "assistant", "content": str(exc)})
            st.session_state.can_show_more = False
            st.session_state.suggested_questions = []
            st.rerun()
            return

    st.session_state.session_id = result["session_id"]
    answer = dict(result["answer"])
    answer["corpus_refreshed"] = result.get("corpus_refreshed", False)
    st.session_state.can_show_more = answer["total_papers_found"] > answer["papers_shown"]
    st.session_state.suggested_questions = answer.get("suggested_questions", [])
    st.session_state.messages.append({"role": "assistant", "content": "", "answer": answer})
    # Rerun so the "show more" / suggested-question buttons (driven by the state just set
    # above) render in this same turn — Streamlit won't retroactively draw them into a
    # position in the script that already executed earlier in this run.
    st.rerun()
