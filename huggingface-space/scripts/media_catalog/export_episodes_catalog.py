#!/usr/bin/env python3
"""Export Firestore episodes to JSON-canonical episodes-catalog.json."""

from __future__ import annotations

import argparse
import json
import subprocess
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
HF_ROOT = SCRIPT_DIR.parent.parent
DEFAULT_BUCKET = "regal-scholar-453620-r7-podcast-storage"
OUTPUT_NAME = "episodes-catalog.json"


def now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def fetch_episodes(limit: int = 0) -> list[dict]:
    from google.cloud import firestore

    db = firestore.Client(project="regal-scholar-453620-r7", database="copernicusai")
    episodes = []
    for doc in db.collection("episodes").stream():
        data = doc.to_dict() or {}
        row = {
            "id": doc.id,
            "title": data.get("title") or data.get("episode_title") or doc.id,
            "description": data.get("description") or data.get("summary") or "",
            "category": data.get("category") or data.get("discipline") or "interdisciplinary",
            "subcategory": data.get("subcategory") or "",
            "audio_url": data.get("audio_url") or data.get("gcs_audio_url") or "",
            "published_date": data.get("published_date") or data.get("created_at") or "",
            "duration_seconds": data.get("duration_seconds") or data.get("duration"),
            "tags": data.get("tags") or [],
            "keywords": data.get("keywords") or [],
            "transcript_available": bool(data.get("transcript") or data.get("transcript_available")),
            "related_papers": data.get("related_papers") or [],
            "related_processes": data.get("related_processes") or [],
            "verified": True,
            "source": "firestore_episodes",
        }
        episodes.append(row)
        if limit and len(episodes) >= limit:
            break
    episodes.sort(key=lambda e: (e.get("published_date") or "", e["title"]), reverse=True)
    return episodes


def build_catalog(episodes: list[dict]) -> dict:
    by_category = Counter(e.get("category") or "unknown" for e in episodes)
    return {
        "name": "CopernicusAI Podcast Episodes Catalog",
        "version": "1.0.0",
        "lastUpdated": now_iso(),
        "category": "podcasts",
        "totalEpisodes": len(episodes),
        "statistics": {
            "by_category": dict(by_category),
            "with_transcripts": sum(1 for e in episodes if e.get("transcript_available")),
        },
        "episodes": episodes,
    }


def upload(path: Path, bucket: str) -> None:
    dest = f"gs://{bucket}/{OUTPUT_NAME}"
    subprocess.run(
        ["gsutil", "-h", "Cache-Control:no-cache, max-age=0", "cp", str(path), dest],
        check=True,
    )
    print(f"✅ Uploaded {dest}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=HF_ROOT / OUTPUT_NAME)
    parser.add_argument("--bucket", default=DEFAULT_BUCKET)
    parser.add_argument("--upload", action="store_true")
    parser.add_argument("--limit", type=int, default=0)
    args = parser.parse_args()

    episodes = fetch_episodes(limit=args.limit)
    catalog = build_catalog(episodes)
    args.output.write_text(json.dumps(catalog, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"✅ Wrote {len(episodes)} episodes → {args.output}")
    if args.upload:
        upload(args.output, args.bucket)


if __name__ == "__main__":
    main()
