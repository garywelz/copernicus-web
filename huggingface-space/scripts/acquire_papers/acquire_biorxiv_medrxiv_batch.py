#!/usr/bin/env python3
"""
BioRxiv/MedRxiv Batch Paper Acquisition Script

Acquires recent preprint metadata from the public Cold Spring Harbor Laboratory
bioRxiv/medRxiv API. These records are metadata-only and are explicitly marked
as preprints so downstream tools do not imply peer review.
"""

import argparse
import json
import time
import urllib.parse
import urllib.request
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional


BASE_DIR = Path("/home/gdubs/copernicus-web-public/huggingface-space")
OUTPUT_DIR = BASE_DIR / "metadata-database" / "papers"
API_BASE_URL = "https://api.biorxiv.org/details"
PAGE_SIZE = 100
DELAY_BETWEEN_REQUESTS = 1.0

SERVER_WEIGHTS = {
    "biorxiv": 0.95,
    "medrxiv": 0.05,
}


def load_biorxiv_config(config_path: Optional[str]) -> Dict:
    defaults = {
        "biorxiv_share": 0.95,
        "medrxiv_share": 0.05,
        "lookback_days": 30,
        "subject_categories": [],
    }
    if not config_path:
        return defaults
    path = Path(config_path)
    if not path.exists():
        print(f"  ⚠️  Config file not found: {path}")
        return defaults
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    if isinstance(data, dict):
        defaults.update(data)
    return defaults


def _matches_subject_category(record: Dict, allowed: List[str]) -> bool:
    if not allowed:
        return True
    category = (record.get("category") or "").strip().lower()
    if not category:
        return True
    allowed_lower = [a.lower() for a in allowed]
    return any(a in category or category in a for a in allowed_lower)


def _safe_id(value: str) -> str:
    return (
        value.lower()
        .replace("https://doi.org/", "")
        .replace("http://doi.org/", "")
        .replace("doi:", "")
        .replace("/", "_")
        .replace(":", "_")
        .strip()
    )


def _split_authors(authors: Optional[str]) -> List[str]:
    if not authors:
        return []
    return [author.strip() for author in authors.split(";") if author.strip()]


def _fetch_json(url: str) -> Dict:
    with urllib.request.urlopen(url, timeout=45) as response:
        return json.loads(response.read().decode("utf-8"))


def fetch_server_records(server: str, target_count: int, lookback_days: int) -> List[Dict]:
    """Fetch up to target_count recent records for one server."""
    end_date = date.today()
    start_date = end_date - timedelta(days=lookback_days)
    interval = f"{start_date.isoformat()}/{end_date.isoformat()}"
    cursor = 0
    records: List[Dict] = []

    while len(records) < target_count:
        url = f"{API_BASE_URL}/{server}/{interval}/{cursor}/json"
        print(f"  Fetching {server}: cursor={cursor}, interval={interval}")
        try:
            data = _fetch_json(url)
        except Exception as exc:
            print(f"  WARNING: {server} request failed: {exc}")
            break

        batch = data.get("collection") or []
        if not batch:
            message = (data.get("messages") or [{}])[0]
            print(f"  No more {server} records: {message.get('status', 'empty response')}")
            break

        records.extend(batch)
        if len(batch) < PAGE_SIZE:
            break

        cursor += len(batch)
        time.sleep(DELAY_BETWEEN_REQUESTS)

    return records[:target_count]


def parse_record(record: Dict) -> Optional[Dict]:
    doi = (record.get("doi") or "").strip()
    title = (record.get("title") or "").strip()
    server = (record.get("server") or "").strip().lower()
    if not doi or not title or server not in {"biorxiv", "medrxiv"}:
        return None

    authors = _split_authors(record.get("authors"))
    published = record.get("published")
    published_doi = None if not published or published == "NA" else published
    posted_date = record.get("date") or ""

    return {
        "id": f"{server}_{_safe_id(doi)}",
        "doi": doi,
        "title": title,
        "authors": authors,
        "author_string": ", ".join(authors[:5]) + (" et al." if len(authors) > 5 else ""),
        "journal": "bioRxiv" if server == "biorxiv" else "medRxiv",
        "journal_full": "bioRxiv" if server == "biorxiv" else "medRxiv",
        "year": posted_date[:4] if len(posted_date) >= 4 else "",
        "abstract": record.get("abstract") or "",
        "keywords": [],
        "categories": [record.get("category")] if record.get("category") else [],
        "citation_count": None,
        "url": f"https://doi.org/{doi}",
        "source": server,
        "sources": [server],
        "acquired_date": datetime.now().isoformat(),
        "category": "biology",
        "discipline": "biology",
        "subcategories": [record.get("category")] if record.get("category") else [],
        "published_date": posted_date or None,
        "updated_date": posted_date or None,
        "preprint": True,
        "peer_reviewed": False,
        "preprint_server": server,
        "preprint_version": record.get("version"),
        "preprint_type": record.get("type"),
        "license": record.get("license"),
        "jatsxml": record.get("jatsxml"),
        "published_doi": published_doi,
        "author_corresponding": record.get("author_corresponding"),
        "author_corresponding_institution": record.get("author_corresponding_institution"),
    }


def save_papers(papers: List[Dict]) -> None:
    by_server: Dict[str, List[Dict]] = {}
    for paper in papers:
        server = paper.get("preprint_server") or paper.get("source") or "preprint"
        by_server.setdefault(server, []).append(paper)

    for server, server_papers in by_server.items():
        output_dir = OUTPUT_DIR / server / "biology"
        output_dir.mkdir(parents=True, exist_ok=True)
        for paper in server_papers:
            filename = f"{paper['id']}.json"
            with open(output_dir / filename, "w", encoding="utf-8") as f:
                json.dump(paper, f, indent=2, ensure_ascii=False)


def acquire_recent_papers(
    target_count: int,
    lookback_days: int,
    server_weights: Optional[Dict[str, float]] = None,
    subject_categories: Optional[List[str]] = None,
) -> int:
    print("\n" + "=" * 60)
    print("BioRxiv/MedRxiv Preprint Acquisition")
    print("=" * 60)

    weights = server_weights or SERVER_WEIGHTS
    all_papers: List[Dict] = []
    seen_ids = set()
    total_weight = sum(weights.values())

    for server, weight in weights.items():
        server_target = max(1, round(target_count * weight / total_weight))
        remaining = target_count - len(all_papers)
        if remaining <= 0:
            break
        server_target = min(server_target, remaining)

        print(f"\nServer: {server} (target {server_target}, lookback {lookback_days}d)")
        records = fetch_server_records(server, server_target * 3, lookback_days)
        accepted = 0
        for record in records:
            if accepted >= server_target:
                break
            if not _matches_subject_category(record, subject_categories or []):
                continue
            paper = parse_record(record)
            if not paper or paper["id"] in seen_ids:
                continue
            seen_ids.add(paper["id"])
            all_papers.append(paper)
            accepted += 1
        print(f"  Acquired {accepted} filtered records; total parsed: {len(all_papers)}/{target_count}")

    print(f"\nSaving {len(all_papers)} BioRxiv/MedRxiv preprints...")
    save_papers(all_papers)
    return len(all_papers)


def main() -> int:
    parser = argparse.ArgumentParser(description="Acquire recent BioRxiv/MedRxiv preprints")
    parser.add_argument("--recent", type=int, default=250, help="Number of recent preprints")
    parser.add_argument("--lookback-days", type=int, default=30, help="Date-window lookback for API queries")
    parser.add_argument("--config-queries", type=str, default=None, help="JSON file with biorxiv_config object")
    args = parser.parse_args()

    bcfg = load_biorxiv_config(args.config_queries)
    lookback = int(bcfg.get("lookback_days", args.lookback_days))
    weights = {
        "biorxiv": float(bcfg.get("biorxiv_share", 0.95)),
        "medrxiv": float(bcfg.get("medrxiv_share", 0.05)),
    }
    subject_categories = bcfg.get("subject_categories") or []

    acquired = acquire_recent_papers(
        args.recent,
        lookback,
        server_weights=weights,
        subject_categories=subject_categories,
    )
    print("\n" + "=" * 60)
    print("Acquisition Complete")
    print("=" * 60)
    print(f"Total preprints acquired: {acquired}")
    print(f"Papers saved to: {OUTPUT_DIR}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
