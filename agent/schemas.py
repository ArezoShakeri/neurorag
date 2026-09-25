"""Structured LLM outputs. Using a Pydantic-bound structured call (rather than parsing free
text) makes citation extraction deterministic — see agent/nodes/synthesize.py."""

from typing import Literal

from pydantic import BaseModel, Field

Intent = Literal["about_agent", "disease_relevant", "off_topic"]


class IntentOutput(BaseModel):
    intent: Intent = Field(
        description="'about_agent' if the question is about the assistant itself (who/what it is, its "
        "purpose, capabilities, data sources, limitations). 'disease_relevant' if it's a research question "
        "about Alzheimer's disease, dementia, MCI, or related neurocognitive conditions. 'off_topic' for "
        "anything else."
    )


class SynthesisOutput(BaseModel):
    evidence_summary: str = Field(description="Plain-language, evidence-grounded answer with jargon briefly explained.")
    citations: list[str] = Field(description="chunk_id values from the provided evidence that this summary relies on.")
    interpretation: str | None = Field(
        default=None, description="Only set if the user explicitly asked for an opinion/recommendation."
    )
    suggested_questions: list[str] = Field(
        description="2-4 concise, specific follow-up questions the user might naturally ask next, "
        "building on this question and what the evidence covered."
    )


class FollowUpOutput(BaseModel):
    suggested_questions: list[str] = Field(
        description="2-4 concise, specific follow-up questions the user might naturally ask next, "
        "building on this question and what the evidence covered."
    )
