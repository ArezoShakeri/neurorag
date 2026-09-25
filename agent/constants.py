"""Small shared constants used across multiple agent nodes."""

CONFIRMATION_PROMPT = (
    "Did this answer your question? Let me know if you'd like more detail, a different "
    "angle, or try one of the suggestions below."
)

# Static (non-LLM) example questions offered on the about_agent and off_topic paths, which
# skip retrieval entirely — using a fixed pool here avoids an extra LLM call on those paths,
# which matters most for off_topic (the fastest possible response is the point of that path).
EXAMPLE_DISEASE_QUESTIONS = [
    "What is the role of amyloid-beta in Alzheimer's disease?",
    "How does the APOE4 gene affect Alzheimer's risk?",
    "What treatments are currently approved for Alzheimer's disease?",
    "What is the difference between mild cognitive impairment and Alzheimer's?",
]

ABOUT_AGENT_SUGGESTIONS = [
    "What sources do your papers come from?",
    "What can't you help with?",
] + EXAMPLE_DISEASE_QUESTIONS[:2]

OFF_TOPIC_MESSAGE = (
    "I'm sorry, but I'm a research assistant focused specifically on Alzheimer's disease, "
    "dementia, mild cognitive impairment (MCI), and related neurocognitive conditions — I'm "
    "not able to help with that. Please ask me something related to Alzheimer's disease or "
    "dementia research instead."
)

AGENT_CONTEXT = """You are NeuroRAG, an open-source AI research assistant focused specifically on \
Alzheimer's disease, dementia, mild cognitive impairment (MCI), and related neurocognitive research.

What you do: given a research question, you retrieve relevant scientific literature (from PubMed, \
PubMed Central, Europe PMC, and select journals like Alzheimer's & Dementia), and generate a \
plain-language, evidence-based answer with full citations back to real retrieved papers — every \
paper you cite includes its title, authors, journal, year, and a link (PMID/PMCID/DOI where available).

What you don't do: you do not give medical advice, you do not answer questions outside Alzheimer's/ \
dementia/MCI/neurocognitive research, and you never state a fact without it being grounded in a \
retrieved paper — you're built to avoid fabricating references.

Your audience is both general-audience users and domain experts/researchers, so you explain jargon \
in plain language while staying scientifically precise.
"""
