#!/usr/bin/env python3
"""
Backfill embeddings for glmp_processes documents missing them.
Written June 30, 2026 — replaces lost backfill_embeddings.py.

Generates embeddings from process metadata (name, description, keywords, mermaid, etc.)
Uses OpenAI text-embedding-3-small (1536-d) to match existing 108 docs.
"""

from __future__ import annotations

import argparse
import os
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
sys.path.insert(0, str(Path(__file__).parent.parent))

from google.cloud import firestore

try:
    from openai import OpenAI
except ImportError:
    print("ERROR: openai package not installed. Run: pip install openai")
    sys.exit(1)

from process_sync_common import create_text_for_process

try:
    from google.cloud import secretmanager
except ImportError:
    secretmanager = None

PROJECT_ID = "regal-scholar-453620-r7"
DATABASE_ID = "copernicusai"
COLLECTION = "glmp_processes"
EMBEDDING_MODEL = "text-embedding-3-small"
EMBEDDING_DIMENSIONS = 1536


def get_openai_api_key() -> str | None:
    key = os.getenv("OPENAI_API_KEY", "").strip()
    if key:
        return key
    if not secretmanager:
        return None
    try:
        client = secretmanager.SecretManagerServiceClient()
        name = f"projects/{PROJECT_ID}/secrets/openai-api-key/versions/latest"
        return client.access_secret_version(request={"name": name}).payload.data.decode("UTF-8").strip()
    except Exception:
        return None


def get_embedding_text(data: dict) -> str:
    """Build embedding text from a Firestore glmp_processes document."""
    payload = dict(data)
    if not payload.get("mermaid") and payload.get("mermaid_code"):
        payload["mermaid"] = payload["mermaid_code"]
    return create_text_for_process(payload)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--yes", action="store_true", help="Skip confirmation prompt")
    parser.add_argument("--limit", type=int, default=None, help="Max documents to backfill")
    parser.add_argument("--dry-run", action="store_true", help="Print plan only, no writes")
    args = parser.parse_args()

    api_key = get_openai_api_key()
    if not api_key and not args.dry_run:
        print("ERROR: OPENAI_API_KEY not found in environment or Secret Manager (openai-api-key)")
        return 1
    if api_key:
        os.environ["OPENAI_API_KEY"] = api_key
        print("OpenAI API key: found via env or Secret Manager")
    else:
        print("Dry-run: skipping OpenAI key check")

    print("Connecting to Firestore...")
    db = firestore.Client(project=PROJECT_ID, database=DATABASE_ID)
    client = OpenAI() if api_key else None

    docs = list(db.collection(COLLECTION).stream())
    missing = [(doc.id, doc.to_dict()) for doc in docs if not doc.to_dict().get("embedding")]
    if args.limit:
        missing = missing[: args.limit]

    print(f"Total documents: {len(docs)}")
    print(f"Documents missing embeddings: {len(missing)}")

    if not missing:
        print("Nothing to do — all documents already have embeddings.")
        return 0

    if args.dry_run:
        doc_id, data = missing[0]
        text = get_embedding_text(data)
        print(f"\nSample ({doc_id}), {len(text)} chars:")
        print("-" * 50)
        print(text[:1500])
        if len(text) > 1500:
            print("...")
        print("-" * 50)
        return 0

    if not args.yes:
        confirm = input(f"\nProceed to generate {len(missing)} embeddings? (yes/no): ")
        if confirm.lower() != "yes":
            print("Aborted.")
            return 1

    success_count = 0
    fail_count = 0
    failed_ids: list[str] = []

    for i, (doc_id, data) in enumerate(missing, 1):
        try:
            text = get_embedding_text(data)
            if not text.strip():
                print(f"  [{i}/{len(missing)}] SKIP {doc_id} — no text content to embed")
                fail_count += 1
                failed_ids.append(doc_id)
                continue

            response = client.embeddings.create(model=EMBEDDING_MODEL, input=text)
            embedding_vector = response.data[0].embedding

            if len(embedding_vector) != EMBEDDING_DIMENSIONS:
                raise ValueError(f"unexpected dimension {len(embedding_vector)}")

            from google.cloud.firestore_v1.vector import Vector

            db.collection(COLLECTION).document(doc_id).update(
                {
                    "embedding": Vector(embedding_vector),
                    "embedding_model": EMBEDDING_MODEL,
                    "embedding_updated_at": firestore.SERVER_TIMESTAMP,
                }
            )

            success_count += 1
            if i % 10 == 0 or i == len(missing):
                print(f"  [{i}/{len(missing)}] OK {doc_id} ({len(embedding_vector)}-d)")

            time.sleep(0.1)
        except Exception as exc:
            fail_count += 1
            failed_ids.append(doc_id)
            print(f"  [{i}/{len(missing)}] FAIL {doc_id} — {exc}")

    print(f"\n{'=' * 50}")
    print("BACKFILL COMPLETE")
    print(f"{'=' * 50}")
    print(f"Success: {success_count}")
    print(f"Failed: {fail_count}")
    if failed_ids:
        print("\nFailed document IDs:")
        for fid in failed_ids:
            print(f"  {fid}")

    return 1 if fail_count else 0


if __name__ == "__main__":
    raise SystemExit(main())
