"""Deterministic checks on the numbers in a generated summary — the same "don't trust the
model, enforce in code" principle as validate_citations.py, applied to claim content.

For each percentage or decimal in the summary we find the evidence sentences that contain it:
- none   -> the number is ungrounded (the model invented or mis-copied it);
- some   -> those chunks are credited as citations, even if the model forgot to cite them;
- but the summary ties the number to a different named treatment than every evidence sentence
  containing it does (e.g. "lecanemab ... 85.1%" when the source says donanemab) -> misattributed.

Treatment names are matched by the international naming convention for antibodies ("-mab") plus
a short list of common Alzheimer's drugs; it's a targeted heuristic, not general entity linking.
"""

import re
from dataclasses import dataclass, field

from database.chroma_client import RetrievedChunk

# Percentages and decimals only: bare integers are too often years, trial phases, or cohort sizes.
# Lookarounds skip numbers glued to letters/identifiers, e.g. "p-tau217", "APOE ε4", "Aβ42".
_NUMBER_RE = re.compile(r"(?<![\w.\-])(\d+(?:\.\d+)?)\s?%|(?<![\w.\-])(\d+\.\d+)(?![\w.])")
_ANY_NUMBER_RE = re.compile(r"\d+(?:\.\d+)?")
_SENTENCE_SPLIT_RE = re.compile(r"(?<=[.!?])\s+(?=[A-Z(\"])")
# Clause boundaries: a number belongs to the named treatment nearest to it within its clause
# ("36.8% of donanemab-treated patients", "21.5% with lecanemab" — the name can come either side).
_CLAUSE_SPLIT_RE = re.compile(
    r"[;,]\s+|\s+(?:while|whereas|but|compared (?:with|to)|versus|vs\.?)\s+", re.IGNORECASE
)
_KNOWN_DRUGS = {
    "donepezil", "rivastigmine", "galantamine", "memantine", "semaglutide", "masitinib",
    "blarcamesine", "valiltramiprosate", "tramiprosate",
}
_TREATMENT_RE = re.compile(r"\b([a-z]+mab|" + "|".join(sorted(_KNOWN_DRUGS)) + r")\b", re.IGNORECASE)

# Integer claims may be rounded from the source ("85%" for 85.1%); decimals must match exactly.
_ROUNDING_TOLERANCE = 1.0


@dataclass
class ClaimCheckResult:
    supporting_chunk_ids: set[str] = field(default_factory=set)
    ungrounded: list[str] = field(default_factory=list)  # "number in: sentence"
    misattributed: list[str] = field(default_factory=list)
    bad_sentences: set[str] = field(default_factory=set)

    @property
    def passed(self) -> bool:
        return not self.ungrounded and not self.misattributed


def check_numeric_claims(summary: str, chunks: list[RetrievedChunk]) -> ClaimCheckResult:
    evidence = [(chunk.metadata.chunk_id, sentence) for chunk in chunks for sentence in split_sentences(chunk.text)]
    result = ClaimCheckResult()

    for sentence in split_sentences(summary):
        for clause in _CLAUSE_SPLIT_RE.split(sentence):
            for match in _NUMBER_RE.finditer(clause):
                raw = match.group(1) or match.group(2)
                sources = [(cid, s) for cid, s in evidence if _contains_number(s, raw)]
                if not sources:
                    result.ungrounded.append(f"{raw} in: {sentence}")
                    result.bad_sentences.add(sentence)
                    continue
                result.supporting_chunk_ids.update(cid for cid, _ in sources)

                claimed = _nearest_treatment(clause, match.start(), match.end()) or _last_treatment(
                    sentence[: sentence.find(clause)]
                )
                if claimed and _is_misattributed(claimed, [s for _, s in sources]):
                    result.misattributed.append(f"{raw} attributed to {claimed} in: {sentence}")
                    result.bad_sentences.add(sentence)

    return result


def remove_sentences(summary: str, bad_sentences: set[str]) -> str:
    return " ".join(s for s in split_sentences(summary) if s not in bad_sentences).strip()


def split_sentences(text: str) -> list[str]:
    return [s.strip() for s in _SENTENCE_SPLIT_RE.split(text.replace("\n", " ")) if s.strip()]


def _contains_number(text: str, raw: str) -> bool:
    target = float(raw)
    tolerance = 0.0 if "." in raw else _ROUNDING_TOLERANCE
    return any(abs(float(n) - target) < tolerance or float(n) == target for n in _ANY_NUMBER_RE.findall(text))


def _nearest_treatment(clause: str, start: int, end: int) -> str | None:
    mentions = [(min(abs(m.end() - start), abs(m.start() - end)), m.group(1)) for m in _TREATMENT_RE.finditer(clause)]
    return min(mentions)[1].lower() if mentions else None


def _last_treatment(text: str) -> str | None:
    found = _TREATMENT_RE.findall(text)
    return found[-1].lower() if found else None


def _is_misattributed(claimed: str, source_sentences: list[str]) -> bool:
    """Misattributed only if every source sentence names some treatment and none names this one —
    a source sentence naming no treatment at all is too ambiguous to contradict the claim."""
    for sentence in source_sentences:
        named = {t.lower() for t in _TREATMENT_RE.findall(sentence)}
        if not named or claimed in named:
            return False
    return True
