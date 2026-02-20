#!/usr/bin/env python3
"""
Export ScienceVideoDB videos to a single `videos-metadata.json` file and (optionally) upload to GCS.

This is meant to power the public static viewer:
  https://storage.googleapis.com/<bucket>/videos-database-table.html
which expects:
  https://storage.googleapis.com/<bucket>/videos-metadata.json

Notes:
- Vertex/embeddings are NOT required.
- Reads from the ScienceVideoDB PostgreSQL (via `SCIENCEVIDDB_DATABASE_URL` or Secret Manager).
"""

from __future__ import annotations

import argparse
import json
import os
from collections import Counter, defaultdict
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional


def _now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _get_database_url(secret_project: str, secret_name: str) -> str:
    # Env var first
    env_url = os.getenv("SCIENCEVIDDB_DATABASE_URL", "").strip()
    if env_url:
        return env_url

    # Secret Manager fallback
    from google.cloud import secretmanager  # type: ignore

    client = secretmanager.SecretManagerServiceClient()
    res_name = f"projects/{secret_project}/secrets/{secret_name}/versions/latest"
    resp = client.access_secret_version(request={"name": res_name})
    url = resp.payload.data.decode("utf-8").strip()
    if not url:
        raise ValueError("Secret Manager returned an empty database URL")
    return url


def _connect_pg(database_url: str):
    import psycopg2  # type: ignore
    return psycopg2.connect(database_url)


def _safe_list(v: Any) -> List[Any]:
    if v is None:
        return []
    if isinstance(v, list):
        return v
    return [v]


def fetch_videos(database_url: str, limit: int = 0) -> List[Dict[str, Any]]:
    """
    Fetch videos from ScienceVideoDB.

    We intentionally select a superset of fields; if a column is missing in your schema,
    adjust the query accordingly.
    """
    import psycopg2  # type: ignore
    from psycopg2.extras import RealDictCursor  # type: ignore

    conn = _connect_pg(database_url)
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            query = """
                SELECT
                    v.id,
                    v.source_id,
                    v.source,
                    v.title,
                    v.description,
                    v.published_at,
                    v.duration,
                    v.view_count,
                    v.thumbnail_url,
                    v.video_url,
                    v.disciplines,
                    v.tags,
                    v.transcript_available,
                    v.metadata,
                    c.channel_name,
                    c.channel_url,
                    c.channel_id
                FROM videos v
                JOIN channels c ON v.channel_id = c.id
                ORDER BY v.published_at DESC NULLS LAST
            """
            if limit and limit > 0:
                query += f" LIMIT {int(limit)}"

            cur.execute(query)
            rows = cur.fetchall()
            return [dict(r) for r in rows]
    finally:
        conn.close()


def to_public_video_row(row: Dict[str, Any]) -> Dict[str, Any]:
    published_at = row.get("published_at")
    published_iso = None
    year = None
    if published_at:
        try:
            published_iso = published_at.isoformat() if hasattr(published_at, "isoformat") else str(published_at)
            year = int(str(published_iso)[:4])
        except Exception:
            published_iso = str(published_at)

    disciplines = _safe_list(row.get("disciplines"))
    disciplines = [str(d).strip().lower() for d in disciplines if str(d).strip()]
    category = disciplines[0] if disciplines else None

    tags = _safe_list(row.get("tags"))
    tags = [str(t).strip() for t in tags if str(t).strip()]

    source = (row.get("source") or "youtube") if row.get("source") is not None else "youtube"
    source = str(source).strip().lower()

    out: Dict[str, Any] = {
        "id": str(row.get("id")),
        "title": row.get("title") or "",
        "description": row.get("description") or "",
        "url": row.get("video_url") or "",
        "source": source,
        "source_id": row.get("source_id"),
        "channel_id": row.get("channel_id"),
        "channel_name": row.get("channel_name") or "",
        "channel_url": row.get("channel_url") or "",
        "published_date": published_iso,
        "year": year,
        "duration": row.get("duration"),
        "view_count": row.get("view_count"),
        "thumbnail_url": row.get("thumbnail_url"),
        "disciplines": disciplines,
        "category": category or "interdisciplinary",
        "subcategories": [],
        "tags": tags,
        "keywords": [],
        "transcript_available": bool(row.get("transcript_available")),
        "related_papers": [],
        "related_processes": [],
        "quality_score": (row.get("metadata") or {}).get("quality_score") if isinstance(row.get("metadata"), dict) else None,
        "language": (row.get("metadata") or {}).get("language") if isinstance(row.get("metadata"), dict) else None,
        "acquired_date": _now_iso(),
    }
    return out


def build_statistics(videos: List[Dict[str, Any]]) -> Dict[str, Any]:
    by_source = Counter((v.get("source") or "unknown") for v in videos)
    by_category = Counter((v.get("category") or "unknown") for v in videos)

    by_discipline = Counter()
    with_transcripts = 0
    channels = set()
    for v in videos:
        if v.get("transcript_available"):
            with_transcripts += 1
        channels.add(v.get("channel_id"))
        for d in (v.get("disciplines") or []):
            by_discipline[str(d)] += 1

    return {
        "by_source": dict(by_source),
        "by_category": dict(by_category),
        "by_discipline": dict(by_discipline),
        "with_transcripts": with_transcripts,
        "channels": len([c for c in channels if c]),
    }


def upload_to_gcs(project: str, bucket: str, object_name: str, local_path: str) -> None:
    from google.cloud import storage  # type: ignore

    client = storage.Client(project=project)
    b = client.bucket(bucket)
    blob = b.blob(object_name)
    blob.cache_control = "no-cache"
    blob.content_type = "application/json; charset=utf-8"
    blob.upload_from_filename(local_path)


def main() -> int:
    parser = argparse.ArgumentParser(description="Export ScienceVideoDB videos to videos-metadata.json (and optionally upload to GCS).")
    parser.add_argument("--project", default=os.getenv("GOOGLE_CLOUD_PROJECT", "regal-scholar-453620-r7"), help="GCP project for GCS upload")
    parser.add_argument("--secret-project", default="regal-scholar-453620-r7", help="Project that holds the Secret Manager secret")
    parser.add_argument("--secret-name", default="scienceviddb-database-url", help="Secret name containing SCIENCEVIDDB_DATABASE_URL")
    parser.add_argument("--limit", type=int, default=0, help="Limit number of videos exported (0 = all)")
    parser.add_argument("--output", default="/tmp/videos-metadata.json", help="Local output path")
    parser.add_argument("--bucket", default="regal-scholar-453620-r7-podcast-storage", help="GCS bucket to upload to")
    parser.add_argument("--object", default="videos-metadata.json", help="GCS object name")
    parser.add_argument("--upload", action="store_true", help="Upload the generated JSON to GCS")
    args = parser.parse_args()

    db_url = _get_database_url(args.secret_project, args.secret_name)
    raw = fetch_videos(db_url, limit=args.limit)
    videos = [to_public_video_row(r) for r in raw]

    payload = {
        "last_updated": _now_iso(),
        "total_videos": len(videos),
        "videos": videos,
        "statistics": build_statistics(videos),
    }

    out_path = args.output
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False)

    print(f"✅ Exported {len(videos)} videos to {out_path}")
    if args.upload:
        upload_to_gcs(args.project, args.bucket, args.object, out_path)
        print(f"✅ Uploaded to gs://{args.bucket}/{args.object}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())

