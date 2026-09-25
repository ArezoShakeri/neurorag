"""CLI entrypoint for the offline ingestion pipeline. Run from the repo root:

    python -m rag.run_ingestion
    python -m rag.run_ingestion --max-results 50   # smaller/faster run for testing
"""

import argparse
from pathlib import Path

from rag.ingestion_pipeline import (
    EXTRA_JOURNALS_PATH,
    SEED_QUERIES_PATH,
    load_extra_journals,
    load_seed_queries,
    run_ingestion,
)


def main() -> None:
    parser = argparse.ArgumentParser(description="Populate the NeuroRAG ChromaDB corpus.")
    parser.add_argument("--max-results", type=int, default=100, help="Max records per seed query/journal.")
    parser.add_argument("--seed-queries", type=Path, default=SEED_QUERIES_PATH)
    parser.add_argument("--extra-journals", type=Path, default=EXTRA_JOURNALS_PATH)
    args = parser.parse_args()

    seed_queries = load_seed_queries(args.seed_queries)
    extra_journals = load_extra_journals(args.extra_journals)

    print(f"Starting ingestion: {len(seed_queries)} seed queries, {len(extra_journals)} extra journals, "
          f"max {args.max_results} results each.")

    summary = run_ingestion(seed_queries, extra_journals, max_results_per_query=args.max_results)

    print("\n--- Ingestion summary ---")
    print(f"Records fetched:          {summary.records_fetched}")
    print(f"Records after dedup:      {summary.records_after_dedup}")
    print(f"Open-access full text:    {summary.open_access_full_text}")
    print(f"Abstract-only:            {summary.abstract_only}")
    print(f"Chunks written to Chroma: {summary.chunks_written}")
    print(f"Skipped (no content):     {summary.skipped_no_content}")
    if summary.errors:
        print(f"\n{len(summary.errors)} errors (non-fatal, other records still processed):")
        for err in summary.errors[:20]:
            print(f"  - {err}")
        if len(summary.errors) > 20:
            print(f"  ... and {len(summary.errors) - 20} more")


if __name__ == "__main__":
    main()
