"""Renders one retrieved paper: metadata, individually linked identifiers, and an
Open Access / Abstract-only badge (per the locked OA-handling design decision)."""

import streamlit as st


def render_paper_card(paper: dict) -> None:
    with st.container(border=True):
        st.markdown(f"**[{paper['title']}]({paper['url']})**")

        authors = paper.get("authors") or []
        author_line = ", ".join(authors[:3]) + (" et al." if len(authors) > 3 else "")
        journal = paper.get("journal") or "Unknown journal"
        year = paper.get("publication_year") or "n.d."
        st.caption(f"{author_line} — *{journal}* ({year})")

        if paper.get("is_open_access"):
            st.badge("Open Access — full text used", color="green")
        else:
            st.badge("Abstract only — not used for full-text retrieval", color="orange")

        links = []
        if paper.get("pmid"):
            links.append(f"[PMID: {paper['pmid']}](https://pubmed.ncbi.nlm.nih.gov/{paper['pmid']}/)")
        if paper.get("pmcid"):
            links.append(f"[PMCID: {paper['pmcid']}](https://www.ncbi.nlm.nih.gov/pmc/articles/{paper['pmcid']}/)")
        if paper.get("doi"):
            links.append(f"[DOI: {paper['doi']}](https://doi.org/{paper['doi']})")
        if links:
            st.markdown(" · ".join(links))

        if paper.get("excerpt"):
            with st.expander("Excerpt"):
                st.write(paper["excerpt"])
