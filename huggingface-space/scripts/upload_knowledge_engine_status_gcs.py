#!/usr/bin/env python3
"""Upload knowledge-engine-status.json to public GCS (preserves allUsers read)."""
from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

from google.cloud import storage

DEFAULT_SA = "/home/gary/.config/copernicus/gcp-sa.json"
DEFAULT_BUCKET = "regal-scholar-453620-r7-podcast-storage"
DEFAULT_BLOB = "knowledge-engine-status.json"


def main() -> int:
    p = argparse.ArgumentParser(description="Upload knowledge-engine-status.json to GCS")
    p.add_argument(
        "--local",
        type=Path,
        default=Path(__file__).resolve().parent.parent / "knowledge-engine-status.json",
        help="Local JSON path",
    )
    p.add_argument("--bucket", default=os.environ.get("GCS_STATUS_BUCKET_NAME", DEFAULT_BUCKET))
    p.add_argument("--blob", default=DEFAULT_BLOB)
    p.add_argument(
        "--sa-key",
        default=os.environ.get("GOOGLE_APPLICATION_CREDENTIALS", DEFAULT_SA),
        help="Service account JSON path",
    )
    args = p.parse_args()

    if not args.local.is_file():
        print(f"❌ Local file not found: {args.local}", file=sys.stderr)
        return 1

    client = storage.Client.from_service_account_json(str(args.sa_key))
    blob = client.bucket(args.bucket).blob(args.blob)
    blob.upload_from_filename(str(args.local), content_type="application/json")
    blob.acl.all().grant_read()
    blob.acl.save()

    print(f"✅ Uploaded gs://{args.bucket}/{args.blob} (public read)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
