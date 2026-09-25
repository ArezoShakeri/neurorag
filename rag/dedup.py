"""Merge RawRecords for the same paper across sources before any OA/full-text work happens."""

from rapidfuzz import fuzz

from retrieval.models import RawRecord

TITLE_MATCH_THRESHOLD = 92


def dedup(records: list[RawRecord]) -> list[RawRecord]:
    """Merge by identity key (DOI / PMID / PMCID, any one match counts) first, then fuzzy
    title+year for the remainder. Every key ever seen for a merged group is repointed to the
    same merged record — a record with both a DOI and PMID that bridges two previously
    separate groups (e.g. one source only gave a DOI, another only a PMID) must fold both
    groups together, not just the single key it matched on first."""
    key_to_record: dict[str, RawRecord] = {}
    keys_for_record: dict[int, set[str]] = {}
    unmatched: list[RawRecord] = []

    for record in records:
        keys = set(record.merge_key_candidates())
        if not keys:
            unmatched.append(record)
            continue

        existing = {id(key_to_record[k]): key_to_record[k] for k in keys if k in key_to_record}
        if existing:
            merged_record = record
            union_keys = set(keys)
            for existing_record in existing.values():
                merged_record = _backfill(existing_record, merged_record)
                union_keys |= keys_for_record.get(id(existing_record), set())
            for k in union_keys:
                key_to_record[k] = merged_record
            keys_for_record[id(merged_record)] = union_keys
        else:
            for k in keys:
                key_to_record[k] = record
            keys_for_record[id(record)] = set(keys)

    merged = list({id(v): v for v in key_to_record.values()}.values())

    for record in unmatched:
        match = _find_fuzzy_match(record, merged)
        if match:
            merged[merged.index(match)] = _backfill(match, record)
        else:
            merged.append(record)

    return merged


def _backfill(primary: RawRecord, secondary: RawRecord) -> RawRecord:
    data = primary.model_dump()
    for field, value in secondary.model_dump().items():
        if not data.get(field) and value:
            data[field] = value
    return RawRecord(**data)


def _find_fuzzy_match(record: RawRecord, candidates: list[RawRecord]) -> RawRecord | None:
    for candidate in candidates:
        if candidate.publication_year != record.publication_year:
            continue
        if fuzz.token_sort_ratio(candidate.title.lower(), record.title.lower()) >= TITLE_MATCH_THRESHOLD:
            return candidate
    return None
