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
- Stub gate: observe (log-only) then enforce; every hit logged with full payload
- Stable last-resort ids via sha256(fingerprint of source payload), never Python hash()
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple

from google.cloud import firestore
from google.api_core.exceptions import AlreadyExists

# Minimal identity core for last-resort ids — fail CLOSED.
# Hash identity of the paper, not the record's current enrichment state.
# Mutable knowledge (abstract, categories, sources, urls, journal_*) must NOT
# enter the fingerprint or enrichment re-mints duplicates.
_DEFAULT_REJECT_GCS_PREFIX = (
    "gs://regal-scholar-453620-r7-podcast-storage/research_data/ingest_rejects"
)


def _now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _utc_date_stamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%d")


def _utc_run_stamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def _as_text(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return value
    return str(value)


def _count_jsonl_lines(path: Path) -> int:
    if not path.exists():
        return 0
    with path.open("r", encoding="utf-8") as fh:
        return sum(1 for line in fh if line.strip())


def _env(name: str, default: str) -> str:
    v = os.getenv(name)
    return v.strip() if isinstance(v, str) and v.strip() else default


def _normalize_doi(doi: Optional[str]) -> Optional[str]:
    if not doi:
        return None
    d = doi.strip().lower()
    d = re.sub(r"^(doi:|https?://(dx\.)?doi\.org/)", "", d).strip()
    return d or None


def _normalize_title(title: Optional[str]) -> str:
    """Collapse whitespace/case/trailing punctuation so source variants share an id."""
    if not title:
        return ""
    t = str(title).strip().lower()
    t = re.sub(r"\s+", " ", t)
    t = t.rstrip(".;:!,")
    # Strip common LaTeX wrappers that vary by source
    t = re.sub(r"[{}$\\]", "", t)
    return t.strip()


def _first_author_surname(paper: Dict[str, Any]) -> str:
    """First author surname only — not the full ordered authors list."""
    authors = paper.get("authors")
    if isinstance(authors, str) and authors.strip():
        authors = [authors]
    if isinstance(authors, list) and authors:
        first = str(authors[0] or "").strip()
        if first:
            # "Surname, Given" or "Given Surname"
            if "," in first:
                return first.split(",", 1)[0].strip().lower()
            parts = first.split()
            return (parts[-1] if parts else first).strip().lower()
    author_string = str(paper.get("author_string") or "").strip()
    if author_string:
        # "A, B et al." → first segment
        first = author_string.split(",")[0].strip()
        parts = first.split()
        return (parts[-1] if parts else first).lower()
    return ""


def _identity_year(paper: Dict[str, Any]) -> str:
    year = str(paper.get("year") or "").strip()
    if re.fullmatch(r"\d{4}", year):
        return year
    pub = str(paper.get("published_date") or "").strip()
    m = re.match(r"(\d{4})", pub)
    return m.group(1) if m else ""


def _fingerprint_paper(paper: Dict[str, Any]) -> Dict[str, Any]:
    """
    Minimal identity core (+ native ids when present).
    Enrichment fields (abstract, categories, sources, urls, journal_*) excluded.
    """
    out: Dict[str, Any] = {}
    title = _normalize_title(paper.get("title") if isinstance(paper.get("title"), str) else str(paper.get("title") or ""))
    if title:
        out["title"] = title
    surname = _first_author_surname(paper)
    if surname:
        out["first_author_surname"] = surname
    year = _identity_year(paper)
    if year:
        out["year"] = year
    doi = _normalize_doi(paper.get("doi") or paper.get("DOI"))
    if doi:
        out["doi"] = doi
    pmid = str(paper.get("pmid") or "").strip()
    if pmid:
        out["pmid"] = pmid
    arxiv = str(paper.get("arxiv_id") or paper.get("arxivId") or "").strip()
    if arxiv:
        out["arxiv_id"] = arxiv.replace("/", "_")
    bibcode = str(paper.get("bibcode") or "").strip()
    if bibcode:
        out["bibcode"] = bibcode
    return out


def _canonical_identity_payload(paper: Dict[str, Any]) -> bytes:
    """Deterministic bytes over the minimal identity core (no list-order traps)."""
    return json.dumps(
        _fingerprint_paper(paper),
        sort_keys=True,
        default=str,
        ensure_ascii=False,
        separators=(",", ":"),
    ).encode("utf-8")


def _payload_sha256_hex(paper: Dict[str, Any]) -> str:
    return hashlib.sha256(_canonical_identity_payload(paper)).hexdigest()


def _reject_stub_reason(paper: Dict[str, Any]) -> Optional[str]:
    """
    Conjunctive gate: (empty or Untitled title) AND (no DOI/PMID/arXiv/bibcode).
    Title-less but identifiable records survive. Titled experiment rows survive.
    """
    title = _as_text(paper.get("title")).strip()
    bad_title = (not title) or title.lower() == "untitled"
    has_doi = bool(_normalize_doi(paper.get("doi") or paper.get("DOI")))
    has_pmid = bool(_as_text(paper.get("pmid")).strip())
    has_arxiv = bool(
        _as_text(paper.get("arxiv_id") or paper.get("arxivId")).strip()
    )
    has_bibcode = bool(_as_text(paper.get("bibcode")).strip())
    if bad_title and not (has_doi or has_pmid or has_arxiv or has_bibcode):
        return "empty_or_untitled_title_and_no_identifier"
    return None


def _upload_reject_log_gcs(local_path: Path, gcs_uri: str) -> Optional[str]:
    """Best-effort upload so reject evidence is readable off-Jetson. Returns error or None."""
    if not local_path.exists() or local_path.stat().st_size == 0:
        return "empty_or_missing_local_reject_log"
    try:
        from google.cloud import storage  # type: ignore

        if not gcs_uri.startswith("gs://"):
            return f"invalid_gcs_uri:{gcs_uri}"
        _, _, rest = gcs_uri.partition("gs://")
        bucket_name, _, blob_name = rest.partition("/")
        client = storage.Client(project=_env("GOOGLE_CLOUD_PROJECT", "regal-scholar-453620-r7"))
        client.bucket(bucket_name).blob(blob_name).upload_from_filename(str(local_path))
        return None
    except Exception as e:
        return f"{type(e).__name__}: {e}"


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
    # fallback to provided id if safe (but not a prior unstable paper_<hash> id)
    pid = str(paper.get("id") or "").strip()
    if pid and "/" not in pid and not re.fullmatch(r"paper_\d+", pid):
        return pid
    # last resort: sha256 of minimal identity core (title/author/year + ids)
    return f"paper_{_payload_sha256_hex(paper)[:32]}"


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
    parser.add_argument(
        "--stub-gate-mode",
        choices=("observe", "enforce", "off"),
        default="observe",
        help=(
            "observe=log hits but still write (default; validate ~97/day via day reject log); "
            "enforce=block writes; off=disable gate"
        ),
    )
    parser.add_argument(
        "--reject-log",
        default="",
        help=(
            "Local JSONL for every gate hit (full payload; append across AM/PM). "
            "Prefer explicit path from ingest_metadata_to_firestore.sh. "
            "Fallback guess: <root>/../../paper_acquisition_logs/daily_scout/ingest_rejects_YYYYMMDD.jsonl"
        ),
    )
    parser.add_argument(
        "--reject-gcs-uri",
        default="",
        help=(
            "GCS object URI for THIS RUN's reject JSONL (append-only naming; readable off-Jetson). "
            f"Prefer explicit URI from ingest_metadata_to_firestore.sh. "
            f"Fallback: {_DEFAULT_REJECT_GCS_PREFIX}/YYYYMMDD/ingest_rejects_<runstamp>.jsonl"
        ),
    )
    parser.add_argument(
        "--no-reject-gcs",
        action="store_true",
        help="Skip GCS upload of reject log (local only; not recommended).",
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
    stub_gate_mode = str(args.stub_gate_mode)

    # Prefer explicit --reject-log / --reject-gcs-uri from ingest_metadata_to_firestore.sh.
    # Inferred defaults are a last resort and can land elsewhere if --root is not
    # exactly .../metadata-database/papers.
    stamp = _utc_date_stamp()
    run_stamp = _utc_run_stamp()
    reject_log_inferred = False
    if args.reject_log:
        reject_log_path = Path(args.reject_log).expanduser().resolve()
    else:
        reject_log_inferred = True
        # .../metadata-database/papers -> .../paper_acquisition_logs/daily_scout/
        hfs_guess = root.parent.parent
        reject_dir = hfs_guess / "paper_acquisition_logs" / "daily_scout"
        reject_log_path = reject_dir / f"ingest_rejects_{stamp}.jsonl"

    if args.reject_gcs_uri:
        reject_gcs_uri = args.reject_gcs_uri.strip()
    else:
        # Per-run object name: PM cannot overwrite AM evidence.
        reject_gcs_uri = (
            f"{_DEFAULT_REJECT_GCS_PREFIX}/{stamp}/ingest_rejects_{run_stamp}.jsonl"
        )

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
    print(f"Stub gate mode:  {stub_gate_mode}")
    print(f"Reject log:      {reject_log_path}")
    if reject_log_inferred:
        print(
            "⚠️  Reject log path was inferred from --root; pin --reject-log "
            "(and --reject-gcs-uri) in ingest_metadata_to_firestore.sh so AM/PM "
            "share one daily file."
        )
    print(f"Reject GCS:      {reject_gcs_uri if not args.no_reject_gcs else '(disabled)'}")
    print(f"Checkpoint file: {str(checkpoint_file) if checkpoint_file else '(none)'}")
    print(f"Batch size:      {batch_size}")
    print("============================================================")

    prepared: List[Tuple[str, Dict[str, Any], str]] = []
    load_failed = 0
    gate_hits = 0
    gate_enforced = 0
    reject_reasons: Dict[str, int] = {}
    run_reject_lines: List[str] = []
    reject_log_path.parent.mkdir(parents=True, exist_ok=True)
    reject_fh = reject_log_path.open("a", encoding="utf-8")

    try:
        for fp in files:
            try:
                paper = json.loads(fp.read_text(encoding="utf-8"))
            except Exception as e:
                load_failed += 1
                if load_failed <= 5:
                    print(f"⚠️  Failed to read {fp}: {e}")
                continue
            if not isinstance(paper, dict):
                load_failed += 1
                if load_failed <= 5:
                    print(f"⚠️  Skipping non-object JSON {fp}: {type(paper).__name__}")
                continue

            reason = None
            if stub_gate_mode != "off":
                reason = _reject_stub_reason(paper)
            if reason:
                gate_hits += 1
                reject_reasons[reason] = reject_reasons.get(reason, 0) + 1
                action = "observe_would_reject" if stub_gate_mode == "observe" else "rejected"
                line = (
                    json.dumps(
                        {
                            "ts_utc": _now_iso(),
                            "gate_mode": stub_gate_mode,
                            "action": action,
                            "reason": reason,
                            "path": str(fp),
                            "payload_sha256": _payload_sha256_hex(paper),
                            "doc_id_if_written": _doc_id_for_paper(paper),
                            "source": paper.get("source") or paper.get("sources"),
                            "title": paper.get("title"),
                            "keys": sorted(paper.keys()),
                            "paper": paper,
                        },
                        ensure_ascii=False,
                        default=str,
                    )
                    + "\n"
                )
                reject_fh.write(line)
                run_reject_lines.append(line)
                if stub_gate_mode == "enforce":
                    gate_enforced += 1
                    continue
                # observe: fall through and still write

            doc_id = _doc_id_for_paper(paper)
            prepared.append((doc_id, _to_firestore_paper(paper, fp), str(fp)))
    finally:
        reject_fh.close()

    day_log_lines = _count_jsonl_lines(reject_log_path)
    print(
        f"Prepared: {len(prepared)} docs "
        f"(failed to load: {load_failed}, gate_hits_this_run: {gate_hits}, "
        f"gate_hits_day_log: {day_log_lines}, gate_enforced: {gate_enforced})"
    )
    if reject_reasons:
        print(f"Gate hit reasons: {reject_reasons}")
    print(f"Reject log appended: {reject_log_path}")
    if not args.no_reject_gcs:
        if run_reject_lines:
            run_reject_path = reject_log_path.with_name(
                f"{reject_log_path.stem}_run_{run_stamp}{reject_log_path.suffix}"
            )
            run_reject_path.write_text("".join(run_reject_lines), encoding="utf-8")
            gcs_err = _upload_reject_log_gcs(run_reject_path, reject_gcs_uri)
            if gcs_err:
                print(
                    f"⚠️  Reject GCS upload failed ({gcs_err}); "
                    f"local day log retained at {reject_log_path}; "
                    f"run slice at {run_reject_path}"
                )
            else:
                print(f"Reject log uploaded (this run): {reject_gcs_uri}")
        else:
            print("Reject GCS: skipped (no gate hits this run)")

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
    print(
        f"Gate hits (this run): {gate_hits} "
        f"(enforced blocks: {gate_enforced}, mode={stub_gate_mode})"
    )
    print(f"Gate hits (day log lines, AM+PM): {day_log_lines}")
    print(f"Failed:      {failed}")
    if gate_hits or day_log_lines:
        print(f"Reject log:  {reject_log_path}")
        if not args.no_reject_gcs and run_reject_lines:
            print(f"Reject GCS:  {reject_gcs_uri}")
        print(
            "NOTE: Compare gate_hits_day_log (append across both 10:30 and 20:15 ET "
            "runs) to the remint clock (~97 tomorrow, ~101 next day if +4/day holds). "
            "This-run gate_hits resets each process and is often ~half the daily total. "
            "Persistently rising day-log hits after enforce → upstream still leaking."
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

