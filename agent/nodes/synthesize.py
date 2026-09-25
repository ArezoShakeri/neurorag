"""LLM call grounded strictly in graded_chunks, with structured output so citations are parsed
deterministically rather than regex-scraped from prose."""

import re

from database.chroma_client import RetrievedChunk
from agent.llm_factory import get_chat_model
from agent.schemas import SynthesisOutput
from agent.state import AgentState
from prompts.loader import render_prompt

# Matches our internal doc_id/chunk_id shapes (see rag/ingestion_pipeline.py::_derive_doc_id),
# optionally wrapped in brackets/parens, e.g. "(pmid_42338648)" or "[pmcid_PMC123::chunk_2]".
# The prompt already tells the model never to write these, but that instruction isn't 100%
# reliable — this is the same "don't trust the model, enforce in code" principle as
# validate_citations.py, just applied to ID leakage in prose instead of citation grounding.
_INTERNAL_ID_RE = re.compile(
    r"[\(\[]?\s*(?:pmid_\d+|pmcid_PMC\d+|doi_[0-9a-f]{12}|title_[0-9a-f]{12})(?:::chunk_\d+)?\s*[\)\]]?"
)
_WHITESPACE_RE = re.compile(r"[ \t]{2,}")
_SPACE_BEFORE_PUNCT_RE = re.compile(r"\s+([.,;:!?])")

# Caps how many chunks reach the LLM prompt, independent of how many papers are ultimately
# shown to the user (format_response.py still aggregates from the full graded_chunks set).
# Local models pay for prompt length in prefill time — this is the single biggest speed lever
# without touching accuracy, since grade_relevance already ranked chunks by similarity, so the
# ones cut are the least relevant.
SYNTHESIS_CHUNK_LIMIT = 8


def synthesize_answer(state: AgentState) -> dict:
    model = get_chat_model().with_structured_output(SynthesisOutput)
    top_chunks = sorted(state["graded_chunks"], key=lambda c: c.distance)[:SYNTHESIS_CHUNK_LIMIT]
    chunks_block = _format_chunks(top_chunks)
    prompt = render_prompt("synthesize_answer", question=state["original_question"], chunks_block=chunks_block)

    feedback = state.get("citation_feedback")
    if feedback:
        prompt = f"{prompt}\n\n{feedback}"

    result: SynthesisOutput = model.invoke(prompt)
    return {
        "draft_summary": _strip_internal_ids(result.evidence_summary),
        "draft_interpretation": result.interpretation,
        "citation_ids": result.citations,
        "suggested_questions": result.suggested_questions,
    }


def _strip_internal_ids(text: str) -> str:
    cleaned = _INTERNAL_ID_RE.sub("", text)
    cleaned = _WHITESPACE_RE.sub(" ", cleaned)
    return _SPACE_BEFORE_PUNCT_RE.sub(r"\1", cleaned).strip()


def _format_chunks(chunks: list[RetrievedChunk]) -> str:
    blocks = []
    for chunk in chunks:
        meta = chunk.metadata
        blocks.append(
            f"[chunk_id: {meta.chunk_id}] ({meta.section}, \"{meta.title}\", {meta.publication_year})\n{chunk.text}"
        )
    return "\n\n---\n\n".join(blocks)
