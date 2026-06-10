#!/usr/bin/env python3
"""
Export Firestore `research_papers` to JSONL for frozen corpora / OpenAI embedding jobs.

Aligned with ingest writer (scripts/ingest_papers_from_metadata_json.py):
  - database: env FIRESTORE_DATABASE (default copernicusai)
  - collection: research_papers
  - top-level fields: title, abstract, doi, pmid, arxiv_id, embedding, embedding_model, ...

Canon ID for joins: Firestore document id (matches ingest doc ids such as pubmed_* / arxiv_*).

Firestore pagination (recommended for ~60k docs):
  - Each page uses .order_by("__name__").limit(N).stream() — a server-side page, not get() on the
    whole collection (avoids loading 60k into memory at once).
  - Cursors: .start_after(last_snapshot) on the last DocumentSnapshot from the previous page.
  - Optional --checkpoint-file + --resume after timeouts (see below).

Usage:
  export GOOGLE_APPLICATION_CREDENTIALS=...   # or gcloud auth application-default login
  export GOOGLE_CLOUD_PROJECT=regal-scholar-453620-r7
  export FIRESTORE_DATABASE=copernicusai
  python3 scripts/export_research_papers_jsonl.py \\
    --out /tmp/research_papers_export_2026-05-26.jsonl \\
    --batch-size 500

Resume after failure (append to same JSONL, continue after last written id):
  python3 scripts/export_research_papers_jsonl.py \\
    --out /tmp/research_papers_export.jsonl --batch-size 500 \\
    --checkpoint-file /tmp/research_papers_export.cp \\
    --resume

Then:
  gzip -k /tmp/research_papers_export_2026-05-26.jsonl
  shasum -a 256 research_papers_export_2026-05-26.jsonl.gz >> SHA256SUMS.txt
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterator, List, Optional, Union

from google.cloud import firestore


def _env(name: str, default: str) -> str:
    v = os.getenv(name)
    return v.strip() if isinstance(v, str) and v.strip() else default


def _as_text(v: Any) -> str:
    if v is None:
        return ""
    return str(v).strip()


def _combined_text(title: str, abstract: str) -> str:
    t = title.strip()
    a = abstract.strip()
    if t and a:
        return f"{t}\n\n{a}"
    return t or a


def _serialize_embedding(val: Any) -> Any:
    """Avoid dumping huge vectors unless requested; handle VectorValue-like objects."""
    if val is None:
        return None
    if isinstance(val, list):
        return val
    try:
        return [float(x) for x in list(val)]
    except Exception:
        return None


def _export_row(doc_id: str, data: Dict[str, Any], include_embedding: bool) -> Dict[str, Any]:
    title = _as_text(data.get("title"))
    abstract = _as_text(data.get("abstract"))
    row: Dict[str, Any] = {
        "doc_id": doc_id,
        "firestore_id": doc_id,
        "doi": data.get("doi"),
        "pmid": data.get("pmid"),
        "arxiv_id": data.get("arxiv_id"),
        "title": title,
        "abstract": abstract,
        "combined_text": _combined_text(title, abstract),
        "discipline": data.get("discipline"),
        "sources": data.get("sources"),
        "embedding_model": data.get("embedding_model") or "",
        "has_vertex_embedding_marker": bool(
            _as_text(data.get("embedding_model", ""))
        ),
    }
    if include_embedding and data.get("embedding") is not None:
        row["embedding"] = _serialize_embedding(data.get("embedding"))
    return row


def _stream_page_with_retry(
    query: firestore.Query,
    max_retries: int,
    retry_sleep_seconds: float,
) -> List[firestore.DocumentSnapshot]:
    """Materialize one page via stream(); retry on transient errors."""
    last_err: Optional[BaseException] = None
    for attempt in range(max_retries):
        try:
            # stream() is the recommended API — pages are capped by .limit(batch_size).
            return list(query.stream())
        except BaseException as e:
            last_err = e
            wait = retry_sleep_seconds * (attempt + 1)
            print(f"⚠️  stream page failed ({e!r}); retry {attempt + 1}/{max_retries} in {wait}s", file=sys.stderr)
            time.sleep(wait)
    assert last_err is not None
    raise last_err


def _selected_collection(
    coll: firestore.CollectionReference,
    projection: str,
    include_embedding: bool,
) -> Union[firestore.CollectionReference, firestore.Query]:
    """
    Optionally restrict fields (.select()) to cut payload size on ~60k reads.
    `--projection minimal` pulls only rows needed for default JSONL (plus embedding blob if flagged).
    """
    if projection == "full":
        return coll
    fields = [
        "title",
        "abstract",
        "doi",
        "pmid",
        "arxiv_id",
        "discipline",
        "sources",
        "embedding_model",
    ]
    if include_embedding:
        fields.append("embedding")
    # Firestore requires at least one field; __name__ is implicit for ordering
    return coll.select(fields)


def _paginate_collection(
    coll_or_query_base: Any,
    batch_size: int,
    limit: int,
    start_after_snap: Optional[firestore.DocumentSnapshot],
    max_retries: int,
    retry_sleep_seconds: float,
) -> Iterator[List[firestore.DocumentSnapshot]]:
    """Stable key order pagination using document id + start_after(DocumentSnapshot cursor)."""
    emitted = 0
    last: Optional[firestore.DocumentSnapshot] = start_after_snap
    while True:
        q = coll_or_query_base.order_by("__name__").limit(batch_size)
        # Pass full snapshot (not bare id) — recommended for Named DB routing in start_after().
        if last is not None:
            q = q.start_after(last)
        batch = _stream_page_with_retry(q, max_retries, retry_sleep_seconds)
        if not batch:
            break
        if limit:
            remaining = limit - emitted
            if remaining <= 0:
                break
            if len(batch) > remaining:
                batch = batch[:remaining]
        yield batch
        emitted += len(batch)
        last = batch[-1]
        if limit and emitted >= limit:
            break


def _read_checkpoint(cp: Path) -> Optional[str]:
    if not cp.exists():
        return None
    raw = cp.read_text(encoding="utf-8").strip().splitlines()
    if not raw:
        return None
    # last non-empty line wins
    return raw[-1].strip() or None


def _write_checkpoint(cp: Path, last_doc_id: str) -> None:
    cp.write_text(last_doc_id + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="Export research_papers to JSONL.")
    parser.add_argument("--out", required=True, help="Output JSONL path")
    parser.add_argument("--batch-size", type=int, default=500, help="Firestore page size (try 500–5000)")
    parser.add_argument("--limit", type=int, default=0, help="Max documents (0 = all)")
    parser.add_argument(
        "--include-embedding-vectors",
        action="store_true",
        help="Include full embedding arrays (large JSONL; default omit)",
    )
    parser.add_argument(
        "--collection",
        default="research_papers",
        help="Firestore collection id",
    )
    parser.add_argument(
        "--checkpoint-file",
        default="",
        help="Write last exported firestore doc id after each page (resume aid)",
    )
    parser.add_argument(
        "--resume",
        action="store_true",
        help="Append to --out; continue after doc id stored in checkpoint (requires --checkpoint-file)",
    )
    parser.add_argument("--max-retries", type=int, default=8, help="Retries per streamed page")
    parser.add_argument(
        "--retry-sleep-seconds",
        type=float,
        default=3.0,
        help="Base sleep; multiplied by attempt number between retries",
    )
    parser.add_argument(
        "--projection",
        choices=("full", "minimal"),
        default="full",
        help="minimal = .select() title/abstract/ids metadata only (smaller payloads for ~60k reads)",
    )
    args = parser.parse_args()

    if args.resume and not args.checkpoint_file:
        print("--resume requires --checkpoint-file", file=sys.stderr)
        return 2

    project = _env("GOOGLE_CLOUD_PROJECT", _env("GCP_PROJECT_ID", "regal-scholar-453620-r7"))
    database = _env("FIRESTORE_DATABASE", "copernicusai")

    out_path = Path(args.out).expanduser().resolve()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    cp_path = Path(args.checkpoint_file).expanduser().resolve() if args.checkpoint_file else None

    db = firestore.Client(project=project, database=database)
    coll = db.collection(args.collection)
    query_base = _selected_collection(
        coll, args.projection, bool(args.include_embedding_vectors)
    )

    start_after_snap: Optional[firestore.DocumentSnapshot] = None
    if args.resume and cp_path:
        last_id = _read_checkpoint(cp_path)
        if last_id:
            # Rehydrate a DocumentSnapshot for start_after(); do not pass a raw string here.
            snap = coll.document(last_id).get()
            if not snap.exists:
                print(f"❌ Checkpoint doc id not found: {last_id!r}", file=sys.stderr)
                return 2
            start_after_snap = snap

    meta = {
        "export_utc": datetime.now(timezone.utc).isoformat(),
        "project": project,
        "firestore_database": database,
        "collection": args.collection,
        "batch_size": args.batch_size,
        "limit": args.limit or None,
        "include_embedding_vectors": bool(args.include_embedding_vectors),
        "projection": args.projection,
        "resume": bool(args.resume),
        "checkpoint_file": str(cp_path) if cp_path else None,
        "start_after_firestore_id": start_after_snap.id if start_after_snap else None,
    }
    print(json.dumps({"export_meta": meta}, indent=2), file=sys.stderr)

    file_mode = "a" if (args.resume and out_path.exists()) else "w"
    count = 0
    with out_path.open(file_mode, encoding="utf-8") as fh:
        for batch in _paginate_collection(
            query_base,
            args.batch_size,
            args.limit,
            start_after_snap,
            args.max_retries,
            args.retry_sleep_seconds,
        ):
            for snap in batch:
                data = snap.to_dict() or {}
                row = _export_row(snap.id, data, include_embedding=bool(args.include_embedding_vectors))
                fh.write(json.dumps(row, ensure_ascii=False) + "\n")
                count += 1
            fh.flush()
            if cp_path and batch:
                _write_checkpoint(cp_path, batch[-1].id)
            print(f"... {count} documents (checkpoint {batch[-1].id if batch else 'n/a'})", file=sys.stderr)

    print(json.dumps({"wrote": str(out_path), "documents_this_run": count, "mode": file_mode}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
