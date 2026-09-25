"""Sidebar controls for which papers get searched: source toggles and a publication-year
range, each with an "All" option. Writes the resolved filter values into st.session_state
(year_from, year_to, allowed_sources) for frontend/api_client.py to send with the query.

Deliberately doesn't import database.schema — the frontend container doesn't ship that
package (see frontend/Dockerfile, which only copies frontend/ + settings.py), so the source
list is a small local constant instead."""

from datetime import date

import streamlit as st

# (value sent to the API, display label). Matches database.schema.Source values actually
# produced by retrieval/ clients — "pmc" is a defined Source literal but never populated by
# any client (Europe PMC already covers PMC content), so it's intentionally left out here.
SOURCE_OPTIONS = [
    ("europepmc", "Europe PMC"),
    ("pubmed", "PubMed"),
    ("crossref_extra", "Other journals (e.g. Alzheimer's & Dementia)"),
]

MIN_YEAR = 2000


def render_resource_filters() -> None:
    st.subheader("Time & Resources")
    st.caption("Control which papers are searched.")

    current_year = date.today().year

    all_years = st.checkbox("All years", value=True, key="filter_all_years")
    if all_years:
        st.session_state.year_from = None
        st.session_state.year_to = None
    else:
        year_from, year_to = st.slider(
            "Publication year range",
            min_value=MIN_YEAR,
            max_value=current_year,
            value=(current_year - 10, current_year),
            key="filter_year_range",
        )
        st.session_state.year_from = year_from
        st.session_state.year_to = year_to

    st.caption("Sources")
    all_sources = st.checkbox("All sources", value=True, key="filter_all_sources")
    if all_sources:
        st.session_state.allowed_sources = None
    else:
        selected = [value for value, label in SOURCE_OPTIONS if st.checkbox(label, value=True, key=f"filter_source_{value}")]
        if not selected:
            st.warning("No sources selected — no papers will be found. Select at least one.")
        st.session_state.allowed_sources = selected
