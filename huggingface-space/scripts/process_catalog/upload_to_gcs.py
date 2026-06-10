#!/usr/bin/env python3
"""Upload JSON-canonical process database artifacts to GCS."""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
HF_ROOT = SCRIPT_DIR.parent.parent
DEFAULT_BUCKET = "regal-scholar-453620-r7-podcast-storage"


def gsutil(args: list[str], *, cwd: Path | None = None) -> None:
    cmd = ["gsutil", *args]
    print("$", " ".join(cmd))
    result = subprocess.run(cmd, cwd=cwd)
    if result.returncode != 0:
        raise SystemExit(result.returncode)


def upload_database(db_name: str, bucket: str, *, processes_only: bool = False) -> None:
    db_root = HF_ROOT / db_name
    if not db_root.is_dir():
        raise SystemExit(f"Database not found: {db_root}")

    gcs_prefix = f"gs://{bucket}/{db_name}"

    discipline = db_name.replace("-processes-database", "")
    table_html = f"{discipline}-database-table.html"
    catalog_files = [
        "metadata.json",
        "process-index.json",
        "catalog_config.json",
        table_html,
    ]

    if not processes_only:
        for name in catalog_files:
            path = db_root / name
            if path.exists():
                gsutil(
                    [
                        "-h",
                        "Cache-Control:no-cache, max-age=0",
                        "cp",
                        str(path),
                        f"{gcs_prefix}/{name}",
                    ]
                )

    processes_dir = db_root / "processes"
    if processes_dir.is_dir():
        gsutil(["-m", "cp", "-r", "processes", gcs_prefix + "/"], cwd=db_root)

    proof_dir = db_root / "proof-graphs"
    if proof_dir.is_dir() and not processes_only:
        gsutil(["-m", "cp", "-r", "proof-graphs", gcs_prefix + "/"], cwd=db_root)

    print(f"\n✅ Uploaded {db_name} to {gcs_prefix}/")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--database", default="mathematics-processes-database")
    parser.add_argument("--bucket", default=DEFAULT_BUCKET)
    parser.add_argument(
        "--processes-only",
        action="store_true",
        help="Upload only processes/ tree (skip table HTML)",
    )
    args = parser.parse_args()
    upload_database(args.database, args.bucket, processes_only=args.processes_only)


if __name__ == "__main__":
    main()
