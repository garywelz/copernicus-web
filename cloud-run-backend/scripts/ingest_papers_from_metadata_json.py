#!/usr/bin/env python3
"""
Ingest acquired paper JSON files into Firestore (CopernicusAI).

This script reads paper metadata JSON files produced by the Ralph Wiggum
acquisition pipeline under:
  copernicus-web-public/huggingface-space/metadata-database/papers/**.json

and writes them to Firestore:
  database: copernicusai
  collection: research_papers

Design goals:
- Vertex-free (no embeddings, no Gemini calls)
- Batch writes (up to 500 ops per commit)
- Safe to re-run (skip-existing by default)
"""

from __future__ import annotations

import argparse
import json
import os
import re
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple

from google.cloud import firestore
from google.api_core.exceptions import AlreadyExists


def _now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _env(name: str, default: str) -> str:
    v = os.getenv(name)
    return v.strip() if isinstance(v, str) and v.strip() else default


def _normalize_doi(doi: Optional[str]) -> Optional[str]:
    if not doi:
        return None
    d = doi.strip().lower()
    d = re.sub(r"^(doi:|https?://(dx\.)?doi\.org/)", "", d).strip()
    return d or None


def _parse_acquired_date(paper: Dict[str, Any]) -> Optional[str]:
    """
    Acquisition JSON has acquired_date like: 2026-01-10T17:01:28.110000
    Store as ISO string; don't require it.
    """
    v = paper.get("acquired_date") or paper.get("acquiredAt") or paper.get("ingested_at")
    if not v:
        return None
    try:
        # normalize to ISO
        # allow fractional seconds
        dt = datetime.fromisoformat(str(v))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.replace(microsecond=0).isoformat()
    except Exception:
        return str(v)


def _infer_discipline(paper: Dict[str, Any], filepath: Path) -> str:
    # Prefer explicit category/discipline
    cat = (paper.get("category") or paper.get("discipline") or "").strip().lower()
    if cat:
        return cat
    # Fall back to directory name
    parts = [p.lower() for p in filepath.parts]
    for d in ("biology", "chemistry", "physics", "mathematics", "computer_science", "interdisciplinary"):
        if d in parts:
            return d
    return "other"


def _infer_sources(paper: Dict[str, Any]) -> List[str]:
    # acquisition JSON uses singular "source"
    source = (paper.get("source") or "").strip().lower()
    sources = paper.get("sources")
    if isinstance(sources, list) and sources:
        out = [str(s).strip().lower() for s in sources if str(s).strip()]
        return out or ([source] if source else [])
    if source:
        return [source]
    # fallback from ids
    if paper.get("pmid"):
        return ["pubmed"]
    if paper.get("arxiv_id") or paper.get("arxivId"):
        return ["arxiv"]
    return []


def _doc_id_for_paper(paper: Dict[str, Any]) -> str:
    """
    Create a stable, URL-safe doc id.
    Prefer source IDs; don't use DOI as doc id because it can contain '/'.
    """
    if paper.get("pmid"):
        return f"pubmed_{paper.get('pmid')}"
    arxiv_id = paper.get("arxiv_id") or paper.get("arxivId")
    if arxiv_id:
        return f"arxiv_{str(arxiv_id).replace('/', '_')}"
    bibcode = paper.get("bibcode")
    if bibcode:
        return f"nasa_ads_{bibcode}"
    # fallback to provided id if safe
    pid = str(paper.get("id") or "").strip()
    if pid and "/" not in pid:
        return pid
    # last resort
    return f"paper_{abs(hash(json.dumps(paper, sort_keys=True, default=str)))}"


def _to_firestore_paper(paper: Dict[str, Any], filepath: Path) -> Dict[str, Any]:
    title = paper.get("title") or "Untitled"
    abstract = paper.get("abstract") or ""
    authors = paper.get("authors") or []
    if isinstance(authors, str):
        authors = [authors]
    keywords = paper.get("keywords") or []
    if isinstance(keywords, str):
        keywords = [keywords]

    out: Dict[str, Any] = {
        "title": title,
        "abstract": abstract,
        "authors": authors,
        "keywords": keywords,
        "doi": _normalize_doi(paper.get("doi") or paper.get("DOI")),
        "sources": _infer_sources(paper),
        "discipline": _infer_discipline(paper, filepath),
        "url": paper.get("url"),
        "pmid": paper.get("pmid"),
        "arxiv_id": paper.get("arxiv_id") or paper.get("arxivId"),
        "journal": paper.get("journal") or paper.get("journal_full"),
        "created_at": _now_iso(),
        "updated_at": _now_iso(),
    }

    acquired = _parse_acquired_date(paper)
    if acquired:
        out["ingested_at"] = acquired

    # categories/subcategories are used differently across sources; store both
    subcats = paper.get("subcategories") or []
    if isinstance(subcats, str):
        subcats = [subcats]
    out["categories"] = [c for c in subcats if c]  # for arXiv codes, etc.

    # Preserve raw fields for traceability
    out["raw_source_id"] = paper.get("id")

    return out


def _iter_json_files(root: Path, include_glob: str) -> Iterable[Path]:
    # Use rglob but allow filtering by glob
    for p in root.rglob("*.json"):
        if include_glob and not p.match(include_glob):
            continue
        yield p


def _batched(items: List[Tuple[str, Dict[str, Any]]], batch_size: int) -> Iterable[List[Tuple[str, Dict[str, Any]]]]:
    for i in range(0, len(items), batch_size):
        yield items[i:i + batch_size]


def main() -> int:
    parser = argparse.ArgumentParser(description="Ingest acquired paper JSON files into Firestore.")
    parser.add_argument(
        "--root",
        default="/home/gdubs/copernicus-web-public/huggingface-space/metadata-database/papers",
        help="Root directory containing acquired paper JSON files",
    )
    parser.add_argument(
        "--include-glob",
        default="**/*.json",
        help="Optional glob filter relative to --root (e.g. '**/biology/recent/*.json')",
    )
    parser.add_argument("--limit", type=int, default=0, help="Max number of JSON files to ingest (0 = all)")
    parser.add_argument(
        "--skip-first",
        type=int,
        default=0,
        help="Skip the first N matching files (useful for incremental runs without relying on doc existence checks)",
    )
    parser.add_argument("--dry-run", action="store_true", help="Do not write; just report what would happen")
    parser.add_argument("--skip-existing", action="store_true", default=True, help="Skip docs that already exist (default)")
    parser.add_argument("--no-skip-existing", action="store_true", help="Overwrite existing docs")
    parser.add_argument("--batch-size", type=int, default=400, help="Firestore batch size (<=500)")
    parser.add_argument(
        "--checkpoint-file",
        default="",
        help="If set, write the last successfully processed file path here after each commit (for resume).",
    )
    parser.add_argument(
        "--resume-from-checkpoint",
        action="store_true",
        help="If set, and --checkpoint-file exists, skip files up to and including the checkpoint path.",
    )
    args = parser.parse_args()

    root = Path(args.root).expanduser().resolve()
    if not root.exists():
        print(f"❌ Root directory not found: {root}")
        return 2

    skip_existing = args.skip_existing and (not args.no_skip_existing)
    batch_size = max(1, min(int(args.batch_size), 500))
    skip_first = max(0, int(args.skip_first))
    checkpoint_file = Path(args.checkpoint_file).expanduser().resolve() if args.checkpoint_file else None
    resume_from_checkpoint = bool(args.resume_from_checkpoint)

    project_id = _env("GCP_PROJECT_ID", _env("GOOGLE_CLOUD_PROJECT", "regal-scholar-453620-r7"))
    firestore_db_name = _env("FIRESTORE_DATABASE", "copernicusai")
    db = firestore.Client(project=project_id, database=firestore_db_name)
    col = db.collection("research_papers")

    files = list(_iter_json_files(root, args.include_glob or "**/*.json"))
    files.sort()
    if checkpoint_file and resume_from_checkpoint and checkpoint_file.exists():
        try:
            ck = checkpoint_file.read_text(encoding="utf-8").strip()
        except Exception:
            ck = ""
        if ck:
            # Skip up to and including the checkpoint file path
            try:
                idx = files.index(Path(ck))
                files = files[idx + 1 :]
                print(f"ℹ️  Resuming after checkpoint: {ck}")
            except ValueError:
                print(f"⚠️  Checkpoint path not found in file list; ignoring: {ck}")
    if skip_first:
        files = files[skip_first:]
    if args.limit and args.limit > 0:
        files = files[: args.limit]

    print("============================================================")
    print("Ingest Papers from JSON → Firestore")
    print("============================================================")
    print(f"Root:            {root}")
    print(f"Filter:          {args.include_glob}")
    print(f"Skip first:      {skip_first}")
    print(f"Files:           {len(files)}")
    print(f"Project:         {project_id}")
    print(f"Firestore DB:    {firestore_db_name}")
    print(f"Collection:      research_papers")
    print(f"Dry run:         {bool(args.dry_run)}")
    print(f"Skip existing:   {bool(skip_existing)}")
    print(f"Checkpoint file: {str(checkpoint_file) if checkpoint_file else '(none)'}")
    print(f"Batch size:      {batch_size}")
    print("============================================================")

    prepared: List[Tuple[str, Dict[str, Any], str]] = []
    load_failed = 0
    for fp in files:
        try:
            paper = json.loads(fp.read_text(encoding="utf-8"))
        except Exception as e:
            load_failed += 1
            if load_failed <= 5:
                print(f"⚠️  Failed to read {fp}: {e}")
            continue
        doc_id = _doc_id_for_paper(paper)
        prepared.append((doc_id, _to_firestore_paper(paper, fp), str(fp)))

    print(f"Prepared: {len(prepared)} docs (failed to load: {load_failed})")

    written = 0
    skipped = 0
    failed = 0
    attempted = 0
    started = time.time()
    last_checkpoint: Optional[str] = None

    for chunk in _batched(prepared, batch_size):
        batch = db.batch()
        staged_in_batch = 0
        for doc_id, doc, _fp in chunk:
            try:
                doc_ref = col.document(doc_id)
                attempted += 1
                if skip_existing:
                    # Avoid expensive per-doc reads: use create() with exists=False semantics.
                    # We stage it in the batch; if it already exists, commit will fail, so we
                    # fall back to per-doc create below (outside batch) for this chunk.
                    batch.create(doc_ref, doc)
                else:
                    batch.set(doc_ref, doc, merge=True)
                staged_in_batch += 1
            except Exception as e:
                failed += 1
                if failed <= 5:
                    print(f"❌ Failed preparing doc {doc_id}: {e}")

        if args.dry_run:
            written += staged_in_batch
            continue

        # Only commit if we actually staged any writes in this batch
        try:
            if staged_in_batch:
                batch.commit()
                written += staged_in_batch
                last_checkpoint = chunk[-1][2] if chunk else None
        except Exception as e:
            # Batch commit can fail if any doc already exists when using batch.create.
            # Fall back to per-doc create to count skips precisely.
            if skip_existing:
                for doc_id, doc, _fp in chunk:
                    try:
                        doc_ref = col.document(doc_id)
                        doc_ref.create(doc)
                        written += 1
                    except AlreadyExists:
                        skipped += 1
                    except Exception as e2:
                        failed += 1
                        if failed <= 5:
                            print(f"❌ Failed writing doc {doc_id}: {e2}")
                last_checkpoint = chunk[-1][2] if chunk else None
            else:
                failed += len(chunk)
                print(f"❌ Batch commit failed ({len(chunk)} items): {e}")

        # Persist checkpoint if requested
        if checkpoint_file and last_checkpoint:
            try:
                checkpoint_file.write_text(last_checkpoint + "\n", encoding="utf-8")
            except Exception as e:
                if failed <= 5:
                    print(f"⚠️  Failed writing checkpoint file {checkpoint_file}: {e}")

        elapsed = max(0.001, time.time() - started)
        rate = (attempted / elapsed) if attempted else 0.0
        print(f"Progress: attempted={attempted} wrote={written} skipped={skipped} failed={failed} rate={rate:.1f}/s")

    print("============================================================")
    print("Done")
    print("============================================================")
    print(f"Would write: {written}" if args.dry_run else f"Wrote:       {written}")
    print(f"Skipped:     {skipped}")
    print(f"Failed:      {failed}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

