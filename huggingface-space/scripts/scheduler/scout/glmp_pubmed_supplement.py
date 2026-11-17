#!/usr/bin/env python3.8
"""
Supplemental PubMed acquisition for GLMP query term clusters 1–3.

Runs from huggingface-space cwd; imports acquire_pubmed_batch helpers in-process.
Same rule as the main scout: publication date, a rolling window that ends today,
and the existing per-term cap so one term cannot crowd out the others.
"""

from __future__ import annotations

import sys
from datetime import datetime
from pathlib import Path

SCOUT_DIR = Path(__file__).resolve().parent
if str(SCOUT_DIR) not in sys.path:
    sys.path.insert(0, str(SCOUT_DIR))

from query_terms import ALL_CLUSTERS_1_3, GLMP_PUBMED_MAX_RESULTS_PER_TERM  # noqa: E402

ACQUIRE_DIR = Path("scripts/acquire_papers")
if not (ACQUIRE_DIR / "acquire_pubmed_batch.py").exists():
    print(f"ERROR: run from huggingface-space root; missing {ACQUIRE_DIR}", file=sys.stderr)
    sys.exit(2)

sys.path.insert(0, str(ACQUIRE_DIR.resolve()))

import acquire_pubmed_batch as pubmed  # noqa: E402


def main() -> int:
    pubmed.setup_entrez()
    output_dir = pubmed.OUTPUT_DIR / "glmp_scout"
    output_dir.mkdir(parents=True, exist_ok=True)

    mindate, maxdate = pubmed.rolling_pubmed_dates()
    print(f"GLMP PubMed supplement: {len(ALL_CLUSTERS_1_3)} terms")
    print(f"  window {mindate} to {maxdate}, sort=pub_date, cap={GLMP_PUBMED_MAX_RESULTS_PER_TERM}")

    all_papers = []
    for term in ALL_CLUSTERS_1_3:
        query = pubmed.supplement_term_query(term, mindate, maxdate)
        print(f"\nTerm: {term}")
        pmids = pubmed.search_pubmed(
            query,
            GLMP_PUBMED_MAX_RESULTS_PER_TERM,
            mindate=mindate,
            maxdate=maxdate,
            sort="pub_date",
            datetype="pdat",
        )
        if not pmids:
            continue
        papers = pubmed.fetch_pubmed_details(pmids)
        all_papers.extend(papers)
        print(f"  fetched {len(papers)} papers")

    if all_papers:
        stats = pubmed.save_papers(all_papers, output_dir, batch_num=int(datetime.now().strftime("%m%d%H")))
    else:
        stats = pubmed._empty_save_stats()

    print(f"\nTotal GLMP supplement papers: {len(all_papers)}")
    print(f"Saved under: {output_dir}")
    print(
        f"SCOUT_STATS fetched={stats['fetched']} "
        f"new_json={stats['new_files']} "
        f"updated_json={stats['updated_files']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
