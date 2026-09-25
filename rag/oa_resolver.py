"""Fill in open-access status for records the source API didn't already flag
(mainly retrieval.crossref_client records, which have no OA info of their own)."""

from retrieval import unpaywall_client
from retrieval.models import RawRecord


def resolve_open_access(record: RawRecord) -> RawRecord:
    """Trust a source-provided OA flag (Europe PMC, PMC OA subset) as-is. Otherwise, resolve
    via Unpaywall when a DOI is available. Records with no DOI and no source OA flag are
    conservatively treated as not open-access (metadata-only, per the locked scoping decision)."""
    if record.is_open_access is not None:
        return record

    if not record.doi:
        return record.model_copy(update={"is_open_access": False})

    status = unpaywall_client.resolve(record.doi)
    if status is None:
        return record.model_copy(update={"is_open_access": False})

    return record.model_copy(
        update={
            "is_open_access": status.is_open_access,
            "full_text_url": status.best_oa_url or record.full_text_url,
        }
    )


def resolve_all(records: list[RawRecord]) -> list[RawRecord]:
    return [resolve_open_access(r) for r in records]
