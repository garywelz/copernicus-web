"""Shared GCS → Firestore sync for JSON-canonical process databases."""

from __future__ import annotations

import json
import os
import re
from datetime import datetime, timezone
from typing import Any

from google.cloud import firestore
from google.cloud import storage

GCS_BUCKET_NAME = os.getenv("GCS_BUCKET_NAME", "regal-scholar-453620-r7-podcast-storage")
SKIP_JSON_NAMES = {"metadata.json", "process-index.json", "catalog_config.json", "index.json"}


def create_text_for_process(process_data: dict[str, Any]) -> str:
    parts = []
    for field in ("name", "title", "description"):
        val = process_data.get(field, "")
        if val:
            parts.append(str(val))
    for field in ("category", "subcategory", "subcategory_name"):
        val = process_data.get(field, "")
        if val:
            parts.append(f"{field}: {val}")
    keywords = process_data.get("keywords") or []
    if keywords:
        parts.append("Keywords: " + ", ".join(keywords[:20]))
    mermaid = process_data.get("mermaid") or process_data.get("mermaid_code") or ""
    if mermaid:
        nodes = re.findall(r'[A-Za-z0-9_]+[\[\(\{]([^\]\)\}]+)[\]\)\}]', mermaid)
        if nodes:
            parts.append("Process steps: " + ", ".join(nodes[:30]))
    return "\n".join(parts)


def convert_to_firestore(
    process_data: dict[str, Any],
    process_id: str,
    file_path: str,
    *,
    default_category: str,
) -> dict[str, Any]:
    name = process_data.get("name") or process_data.get("title") or process_id
    complexity = process_data.get("complexity") or {}
    level = complexity.get("level", "medium") if isinstance(complexity, dict) else str(complexity)
    return {
        "process_id": process_id,
        "id": process_data.get("id", process_id),
        "name": name,
        "title": name,
        "description": process_data.get("description", ""),
        "category": process_data.get("category", default_category),
        "subcategory": process_data.get("subcategory", "general"),
        "subcategory_name": process_data.get("subcategory_name", ""),
        "processType": process_data.get("processType", "algorithm"),
        "mermaid": process_data.get("mermaid", ""),
        "mermaid_code": process_data.get("mermaid", ""),
        "keywords": process_data.get("keywords", []),
        "sources": process_data.get("sources", []),
        "metadata": {
            "source": "json_canonical",
            "file_path": file_path,
            "gcs_url": f"gs://{GCS_BUCKET_NAME}/{file_path}",
            "complexity": level,
            "verified": process_data.get("verified", True),
        },
        "created_at": process_data.get("created", datetime.now(timezone.utc).isoformat()),
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }


def list_process_json_files(bucket_path: str) -> list[str]:
    client = storage.Client()
    bucket = client.bucket(GCS_BUCKET_NAME)
    prefix = f"{bucket_path.rstrip('/')}/processes/"
    files = []
    for blob in bucket.list_blobs(prefix=prefix):
        if not blob.name.endswith(".json"):
            continue
        if blob.name.rsplit("/", 1)[-1] in SKIP_JSON_NAMES:
            continue
        files.append(blob.name)
    return sorted(files)


def load_process_json(file_path: str) -> dict[str, Any] | None:
    client = storage.Client()
    bucket = client.bucket(GCS_BUCKET_NAME)
    blob = bucket.blob(file_path)
    if not blob.exists():
        return None
    return json.loads(blob.download_as_text())


def process_id_from_blob(file_path: str, bucket_path: str, process_data: dict[str, Any]) -> str:
    if process_data.get("id"):
        return process_data["id"]
    processes_prefix = f"{bucket_path.rstrip('/')}/processes/"
    rel = file_path.replace(processes_prefix, "").replace(".json", "")
    return rel.replace("/", "-")


def sync_process_collection(
    *,
    collection_name: str,
    bucket_path: str,
    default_category: str,
    dry_run: bool = False,
    limit: int | None = None,
    skip_existing: bool = True,
) -> dict[str, Any]:
    stats = {
        "total_in_gcs": 0,
        "already_in_firestore": 0,
        "synced": 0,
        "failed": 0,
        "errors": [],
    }

    gcp_project_id = os.getenv("GCP_PROJECT_ID", "regal-scholar-453620-r7")
    firestore_db = firestore.Client(project=gcp_project_id, database="copernicusai")
    coll_ref = firestore_db.collection(collection_name)

    all_files = list_process_json_files(bucket_path)
    if limit:
        all_files = all_files[:limit]
    stats["total_in_gcs"] = len(all_files)

    existing: set[str] = set()
    if skip_existing:
        for doc in coll_ref.stream():
            existing.add(doc.id)

    for i, file_path in enumerate(all_files, 1):
        try:
            process_data = load_process_json(file_path)
            if not process_data:
                stats["failed"] += 1
                stats["errors"].append(f"Could not load {file_path}")
                continue

            process_id = process_id_from_blob(file_path, bucket_path, process_data)
            if skip_existing and process_id in existing:
                stats["already_in_firestore"] += 1
                continue

            doc = convert_to_firestore(
                process_data, process_id, file_path, default_category=default_category
            )
            if not dry_run:
                coll_ref.document(process_id).set(doc, merge=True)
            stats["synced"] += 1

            if i % 25 == 0 or i == len(all_files):
                print(f"   ✅ {collection_name}: {i}/{len(all_files)} synced={stats['synced']}")

        except Exception as exc:
            stats["failed"] += 1
            stats["errors"].append(f"{file_path}: {exc}")

    return stats
