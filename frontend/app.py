"""Streamlit entrypoint. Run with: streamlit run frontend/app.py"""

import streamlit as st

from frontend.components.chat import render_chat
from frontend.components.resource_filters import render_resource_filters
from settings import get_settings

st.set_page_config(page_title="NeuroRAG — Alzheimer's Research Assistant", page_icon="🧠", layout="centered")

settings = get_settings()

with st.sidebar:
    st.title("NeuroRAG")
    st.caption("AI Research Assistant for Alzheimer's disease literature")
    st.slider("Papers to show", min_value=1, max_value=25, value=settings.default_num_papers, key="num_papers")
    st.divider()
    render_resource_filters()
    st.divider()
    if st.button("New conversation"):
        st.session_state.clear()
        st.rerun()
    st.divider()
    st.caption(
        "Answers are grounded in retrieved scientific literature and always cite their sources. "
        "This assistant does not provide medical advice."
    )

st.title("Alzheimer's Disease Research Assistant")
st.caption("Ask a research question. Answers are evidence-based, cited, and explained in plain language.")

render_chat(default_num_papers=settings.default_num_papers)
