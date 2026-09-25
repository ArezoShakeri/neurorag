"""Shared text sanitization for raw API responses. Europe PMC and Crossref both embed
inline HTML/JATS markup (e.g. <i>...</i> for italicized species/gene names) directly in
title and abstract strings — this must be stripped before the text reaches the corpus,
the API response, or the LLM prompt."""

import html
import re

_TAG_RE = re.compile(r"<[^>]+>")
_WHITESPACE_RE = re.compile(r"\s+")


def strip_html_tags(text: str | None) -> str | None:
    if not text:
        return text
    # Europe PMC returns markup as HTML-entity-escaped tags (e.g. "&lt;i&gt;"), not literal
    # "<i>" — unescape first so the tag regex actually matches, then strip real tags too.
    unescaped = html.unescape(text)
    # Replace with a space (not empty string) so tags directly abutting words don't merge them,
    # then collapse the resulting extra whitespace.
    return _WHITESPACE_RE.sub(" ", _TAG_RE.sub(" ", unescaped)).strip()
