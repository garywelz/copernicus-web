#!/usr/bin/env python3
"""Publish JSON-canonical videos catalog (wraps ScienceVideoDB export)."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parent.parent.parent
EXPORT_SCRIPT = REPO_ROOT / "cloud-run-backend/scripts/export_videos_metadata_to_gcs.py"
HF_ROOT = SCRIPT_DIR.parent.parent
OUTPUT_NAME = "videos-catalog.json"


def now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def normalize_export(payload: dict) -> dict:
    videos = []
    for v in payload.get("videos") or []:
        videos.append({
            "id": str(v.get("id")),
            "title": v.get("title") or "",
            "description": v.get("description") or "",
            "category": v.get("category") or "interdisciplinary",
            "subcategories": v.get("subcategories") or [],
            "url": v.get("url") or "",
            "source": v.get("source") or "youtube",
            "source_id": v.get("source_id"),
            "channel_name": v.get("channel_name") or "",
            "published_date": v.get("published_date"),
            "duration": v.get("duration"),
            "disciplines": v.get("disciplines") or [],
            "tags": v.get("tags") or [],
            "keywords": v.get("keywords") or [],
            "transcript_available": bool(v.get("transcript_available")),
            "thumbnail_url": v.get("thumbnail_url"),
            "related_papers": v.get("related_papers") or [],
            "related_processes": v.get("related_processes") or [],
            "verified": True,
        })
    return {
        "name": "Science Video Database Catalog",
        "version": "1.0.0",
        "lastUpdated": now_iso(),
        "category": "videos",
        "totalVideos": len(videos),
        "statistics": payload.get("statistics") or {},
        "videos": videos,
    }


def fetch_from_gcs(bucket: str) -> dict:
    from google.cloud import storage

    client = storage.Client()
    blob = client.bucket(bucket).blob("videos-metadata.json")
    return json.loads(blob.download_as_text())


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=HF_ROOT / OUTPUT_NAME)
    parser.add_argument("--bucket", default="regal-scholar-453620-r7-podcast-storage")
    parser.add_argument("--upload", action="store_true")
    parser.add_argument("--from-gcs", action="store_true", help="Normalize existing GCS videos-metadata.json")
    parser.add_argument("--limit", type=int, default=0)
    args = parser.parse_args()

    if args.from_gcs:
        raw = fetch_from_gcs(args.bucket)
    else:
        tmp = Path("/tmp/videos-metadata-raw.json")
        cmd = [sys.executable, str(EXPORT_SCRIPT), "--output", str(tmp)]
        if args.limit:
            cmd.extend(["--limit", str(args.limit)])
        subprocess.run(cmd, check=True, cwd=str(REPO_ROOT / "cloud-run-backend"))
        raw = json.loads(tmp.read_text(encoding="utf-8"))
    catalog = normalize_export(raw)
    args.output.write_text(json.dumps(catalog, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"✅ Wrote {catalog['totalVideos']} videos → {args.output}")

    if args.upload:
        for name in (OUTPUT_NAME, "videos-metadata.json"):
            dest = f"gs://{args.bucket}/{name}"
            subprocess.run(
                ["gsutil", "-h", "Cache-Control:no-cache, max-age=0", "cp", str(args.output), dest],
                check=True,
            )
            print(f"✅ Uploaded {dest}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
