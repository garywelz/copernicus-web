#!/usr/bin/env python3
"""
Untitled-husk cleanup for Firestore research_papers.

Final plan (2026-07-21): freeze → export JSONL → READY_TO_DELETE → staged delete.
Embeddings live on the doc (Vector + embedding_model); live find_nearest needs no
separate index rebuild. This script does NOT run deletes unless --delete is passed
AND a READY_TO_DELETE marker exists (local and/or GCS) AND --i-understand-delete.

Resumability: if a --delete run dies mid-sweep, a rerun is safe. Already-deleted
IDs appear in missing_at_start on the next run and are skipped; remaining pinned
IDs continue through pilot/batches with the same checkpoints.

Modes (mutually exclusive primary actions):
  --export-only       Freeze Untitled set, write docs.jsonl + manifest + README
  --probe-retrieval   Pre/post hygiene probes (Untitled in top-k?)
  --dry-run-delete    Walk delete path; print would-delete / would-skip; no writes
  --delete            Staged delete from pinned manifest (requires gates)

Env:
  GOOGLE_CLOUD_PROJECT   default regal-scholar-453620-r7
  FIRESTORE_DATABASE     default copernicusai

Usage (Yoga, ADC) — run the *tracked* commit after push/pull, not an untracked draft:
  cd cloud-run-backend
  python3 scripts/sweep_untitled_husks.py --export-only --out-dir /tmp/untitled_sweep_20260721
  python3 scripts/sweep_untitled_husks.py --probe-retrieval --out-dir /tmp/untitled_sweep_20260721
  # after Gary export-go + upload + READY_TO_DELETE:
  python3 scripts/sweep_untitled_husks.py --dry-run-delete --out-dir ...
  python3 scripts/sweep_untitled_husks.py --delete --i-understand-delete --out-dir ...

Vector export policy: Firestore Vector → JSON list of floats (complete restore).
Delete-time predicate is identifiers-only because every ID already passed the full
husk predicate at freeze; see is_husk_full vs is_husk_delete_safe.

Probe distance_measure defaults to COSINE to match production
mcp_server/tools/vector_search.py find_nearest calls. Override with --distance if needed.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

from google.cloud import firestore
from google.cloud.firestore_v1.base_query import FieldFilter
from google.cloud.firestore_v1.base_vector_query import DistanceMeasure
from google.cloud.firestore_v1.vector import Vector

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

DEFAULT_PROJECT = "regal-scholar-453620-r7"
DEFAULT_DATABASE = "copernicusai"
COLLECTION = "research_papers"
ENFORCE_CUTOFF = "2026-07-19T14:30:00"  # ISO prefix; matches string created_at
EXPECTED_CENSUS_N = 1543
READY_MARKER_NAME = "READY_TO_DELETE"
DEFAULT_GCS_PREFIX = (
    "gs://regal-scholar-453620-r7-podcast-storage/"
    "research_data/corpus_hygiene"
)
DEFAULT_PROBE_QUERIES = [
    "lac operon regulation",
    "CRISPR gene editing",
    "DNA methylation epigenetics",
]

# Freeze-time: full husk predicate (identifiers + abstract + URL + sources).
# Delete-time: identifiers only — every ID already passed full predicate at freeze;
# re-check title + identifiers so a repaired doc mid-sweep is skipped, without
# re-litigating empty abstract/URL (same as plan Amendment / Claude Chat note).


def _utcnow() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _client() -> firestore.Client:
    project = os.environ.get("GOOGLE_CLOUD_PROJECT", DEFAULT_PROJECT)
    database = os.environ.get("FIRESTORE_DATABASE", DEFAULT_DATABASE)
    return firestore.Client(project=project, database=database)


def created_at_iso(data: Dict[str, Any]) -> Optional[str]:
    """
    Normalize created_at for prefix compare against ENFORCE_CUTOFF.

    Pre-flight samples store ISO *strings* with a T separator. If ingest ever
    writes a Firestore timestamp, str() uses a space and same-day post-cutoff
    leaks can sort as pre-cutoff. isoformat() always uses T.

    Returns None if created_at is missing/empty — caller must hard-abort (do not
    treat blank as pre-cutoff).
    """
    ca_raw = data.get("created_at")
    if ca_raw is None:
        return None
    if hasattr(ca_raw, "isoformat"):
        s = ca_raw.isoformat()
    else:
        s = str(ca_raw).strip()
    return s or None


def _truthy_str(v: Any) -> bool:
    if v is None:
        return False
    if isinstance(v, (list, dict)):
        return len(v) > 0
    return str(v).strip() != ""


def has_identifier(data: Dict[str, Any]) -> bool:
    return any(
        _truthy_str(data.get(k))
        for k in ("doi", "pmid", "arxiv_id", "bibcode", "arxiv")
    )


def has_abstract_url_or_sources(data: Dict[str, Any]) -> bool:
    if _truthy_str(data.get("abstract")):
        return True
    if any(_truthy_str(data.get(k)) for k in ("url", "source_url", "pdf_url", "html_url")):
        return True
    if _truthy_str(data.get("sources")):
        return True
    return False


def is_husk_full(data: Dict[str, Any]) -> bool:
    """Freeze-time predicate: Untitled + no identifiers + no abstract/URL/sources."""
    title = str(data.get("title") or "").strip()
    if title != "Untitled":
        return False
    if has_identifier(data):
        return False
    if has_abstract_url_or_sources(data):
        return False
    return True


def is_husk_delete_safe(data: Dict[str, Any]) -> bool:
    """
    Delete-time predicate (lighter): Untitled + no identifiers.

    Asymmetry vs is_husk_full is intentional and accepted by the final plan
    (Claude Chat / Core): freeze already required empty abstract/URL/sources.
    Residual risk: a doc that gains only abstract/URL (no identifier) between
    freeze and delete would still be deleted. Window is short (export→GCS→Gary
    go→delete); we accept that residual rather than re-litigate the full husk
    predicate. Identifier gain is re-checked and causes skip.
    """
    title = str(data.get("title") or "").strip()
    if title != "Untitled":
        return False
    if has_identifier(data):
        return False
    return True


def vector_to_floats(raw: Any) -> Optional[List[float]]:
    """Serialize Firestore Vector (or list) to JSON-safe floats. Never silent-drop."""
    if raw is None:
        return None
    if isinstance(raw, Vector):
        return [float(x) for x in list(raw)]
    if isinstance(raw, (list, tuple)):
        return [float(x) for x in raw]
    if isinstance(raw, dict) and "values" in raw:
        vals = raw.get("values")
        if isinstance(vals, (list, tuple)):
            return [float(x) for x in vals]
    raise TypeError(f"Cannot serialize embedding type {type(raw)!r}")


def doc_to_export_dict(doc_id: str, data: Dict[str, Any]) -> Dict[str, Any]:
    out = dict(data)
    if "embedding" in out:
        out["embedding"] = vector_to_floats(out.get("embedding"))
        out["_embedding_export"] = "float_list"
    out["_firestore_id"] = doc_id
    return out


def stream_untitled(col) -> Iterable[Tuple[str, Dict[str, Any]]]:
    for snap in col.where(filter=FieldFilter("title", "==", "Untitled")).stream():
        yield snap.id, (snap.to_dict() or {})


def freeze_untitled(col) -> Tuple[List[str], List[Dict[str, Any]], Dict[str, Any]]:
    """
    Returns (ids, export_rows, freeze_report).
    Hard-aborts via SystemExit on unsafe conditions.
    """
    rows: List[Dict[str, Any]] = []
    ids: List[str] = []
    leak: List[str] = []
    failed_husk: List[str] = []
    missing_created_at: List[str] = []

    for doc_id, data in stream_untitled(col):
        ca = created_at_iso(data)
        if ca is None:
            missing_created_at.append(doc_id)
            continue
        if ca >= ENFORCE_CUTOFF:
            leak.append(doc_id)
        if not is_husk_full(data):
            failed_husk.append(doc_id)
            continue
        ids.append(doc_id)
        rows.append(doc_to_export_dict(doc_id, data))

    n = len(ids)
    report = {
        "frozen_at_utc": _utcnow(),
        "n": n,
        "expected_census_n": EXPECTED_CENSUS_N,
        "leak_since_enforce_count": len(leak),
        "leak_ids": leak,
        "missing_created_at_count": len(missing_created_at),
        "missing_created_at_ids_sample": missing_created_at[:20],
        "failed_husk_predicate_count": len(failed_husk),
        "failed_husk_ids_sample": failed_husk[:20],
    }

    if missing_created_at:
        print(
            "HARD ABORT: Untitled docs with missing/empty created_at:",
            len(missing_created_at),
        )
        for i in missing_created_at[:20]:
            print(" ", i)
        raise SystemExit(2)
    if leak:
        print("HARD ABORT: Untitled docs with created_at >= enforce cutoff:", len(leak))
        for i in leak[:20]:
            print(" ", i)
        raise SystemExit(2)
    if failed_husk:
        print("HARD ABORT: Untitled docs failing full husk predicate:", len(failed_husk))
        for i in failed_husk[:20]:
            print(" ", i)
        raise SystemExit(2)
    if n > EXPECTED_CENSUS_N:
        print(f"HARD ABORT: frozen n={n} > expected {EXPECTED_CENSUS_N}")
        raise SystemExit(2)
    if n < EXPECTED_CENSUS_N:
        print(
            f"SOFT PATH: frozen n={n} < expected {EXPECTED_CENSUS_N}; "
            "continuing with actual n (record drift in README)."
        )
    if n == 0:
        print("HARD ABORT: nothing to freeze")
        raise SystemExit(2)

    ids.sort()
    rows.sort(key=lambda r: r["_firestore_id"])
    return ids, rows, report


def write_export(out_dir: Path, ids: List[str], rows: List[Dict[str, Any]], report: Dict[str, Any]) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    jsonl_path = out_dir / "docs.jsonl"
    manifest_path = out_dir / "manifest.json"
    readme_path = out_dir / "README.md"
    sweep_day = datetime.now(timezone.utc).strftime("%Y%m%d")
    gcs_archive = f"{DEFAULT_GCS_PREFIX}/untitled_sweep_{sweep_day}/"

    with jsonl_path.open("w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False, default=str) + "\n")

    line_count = sum(1 for _ in jsonl_path.open(encoding="utf-8"))
    if line_count != len(ids):
        print(f"HARD ABORT: jsonl lines {line_count} != id count {len(ids)}")
        raise SystemExit(2)

    manifest = {
        **report,
        "collection": COLLECTION,
        "selector": 'title == "Untitled" AND full husk predicate',
        "enforce_cutoff": ENFORCE_CUTOFF,
        "ids": ids,
        "docs_jsonl": "docs.jsonl",
        "vector_export_policy": "embedding stored as float list; _embedding_export=float_list",
        "gcs_archive": gcs_archive,
        "ready_to_delete_marker": READY_MARKER_NAME,
    }
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")

    readme = f"""# Untitled husk sweep export

- Frozen at (UTC): {report["frozen_at_utc"]}
- Selector: title == "Untitled" + full husk predicate (no DOI/PMID/arXiv/bibcode; empty abstract/URL/sources)
- Enforce cutoff: `{ENFORCE_CUTOFF}`
- Frozen n: **{len(ids)}** (census expectation was {EXPECTED_CENSUS_N})
- Leak since enforce: {report["leak_since_enforce_count"]}
- Vector policy: Firestore `Vector` exported as JSON float lists (complete restore possible; these vectors are junk for retrieval)

## Files

- `docs.jsonl` — one full document per line (`_firestore_id` set)
- `manifest.json` — pinned ID list + census
- `{READY_MARKER_NAME}` — **create last**, only after the export-go sequence below succeeds; `--delete` requires this file

## Export-go sequence (marker is last)

1. Run `--export-only` into this directory (from the **tracked** script commit on Yoga).
2. Verify locally: `docs.jsonl` line count == manifest `n`; spot-check a few JSONL lines.
3. `gsutil cp` `docs.jsonl`, `manifest.json`, and `README.md` to
   `{gcs_archive}`
4. **Verify the GCS copy** (`gsutil ls -l` sizes match local, or hash compare — plain fetch, no cache-buster).
5. Only then create `{READY_MARKER_NAME}` **locally and in GCS** (empty file or short JSON note).
   The marker means: everything before it succeeded. Never create it earlier.

## Delete gates

1. Archive integrity re-check inside `--delete` / `--dry-run-delete` (manifest parseable; JSONL lines == n; n == len(ids)).
2. `{READY_MARKER_NAME}` present (for `--delete` only).
3. Explicit `--delete --i-understand-delete` in session after Gary's delete-go.
"""
    readme_path.write_text(readme, encoding="utf-8")
    print(f"Wrote {jsonl_path} ({line_count} lines)")
    print(f"Wrote {manifest_path}")
    print(f"Wrote {readme_path}")
    print(f"Suggested GCS archive: {gcs_archive}")
    print(f"READY_TO_DELETE not written (export-only). Create after Gary go + GCS verify.")


def load_manifest(path: Path) -> Dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def ready_marker_present(out_dir: Path) -> bool:
    return (out_dir / READY_MARKER_NAME).is_file()


def verify_archive_integrity(out_dir: Path, manifest_path: Path) -> Tuple[List[str], Dict[str, Any]]:
    """
    Item 1 (Core): before any delete write, re-verify the archive next to READY_TO_DELETE.
    Returns (ids, manifest). Hard-aborts on mismatch.
    """
    if not manifest_path.is_file():
        print(f"HARD ABORT: missing manifest at {manifest_path}")
        raise SystemExit(2)
    try:
        manifest = load_manifest(manifest_path)
    except Exception as e:
        print(f"HARD ABORT: manifest not parseable: {e}")
        raise SystemExit(2)

    ids = list(manifest.get("ids") or [])
    n_field = manifest.get("n")
    if n_field is not None and int(n_field) != len(ids):
        print(
            f"HARD ABORT: manifest n={n_field} != len(ids)={len(ids)}"
        )
        raise SystemExit(2)

    jsonl_path = out_dir / "docs.jsonl"
    if not jsonl_path.is_file():
        # allow override if docs live beside manifest's declared name
        alt = out_dir / str(manifest.get("docs_jsonl") or "docs.jsonl")
        jsonl_path = alt if alt.is_file() else jsonl_path
    if not jsonl_path.is_file():
        print(f"HARD ABORT: missing docs.jsonl under {out_dir}")
        raise SystemExit(2)

    line_count = sum(1 for _ in jsonl_path.open(encoding="utf-8"))
    if line_count != len(ids):
        print(
            f"HARD ABORT: docs.jsonl lines={line_count} != len(manifest ids)={len(ids)}"
        )
        raise SystemExit(2)

    # Spot-check: every JSONL _firestore_id must be in the pinned set
    id_set = set(ids)
    with jsonl_path.open(encoding="utf-8") as f:
        for line in f:
            row = json.loads(line)
            fid = row.get("_firestore_id")
            if fid not in id_set:
                print(f"HARD ABORT: jsonl id {fid!r} not in manifest ids")
                raise SystemExit(2)

    print(
        f"Archive integrity OK: manifest n={len(ids)}, jsonl lines={line_count}, "
        f"ids list length matches"
    )
    return ids, manifest


def reconcile_missing_at_start(
    db: firestore.Client, col, ids: Sequence[str]
) -> List[str]:
    """IDs already absent before the sweep touches them (tolerated + logged)."""
    missing: List[str] = []
    for i in range(0, len(ids), 100):
        chunk = list(ids[i : i + 100])
        snaps = {s.id: s for s in db.get_all([col.document(x) for x in chunk])}
        for doc_id in chunk:
            snap = snaps.get(doc_id)
            if snap is None or not snap.exists:
                missing.append(doc_id)
    return missing


def count_manifest_remaining(db: firestore.Client, col, ids: Sequence[str]) -> int:
    """Between-batch checkpoint: how many pinned IDs still exist in Firestore."""
    n = 0
    for i in range(0, len(ids), 100):
        chunk = ids[i : i + 100]
        for snap in db.get_all([col.document(x) for x in chunk]):
            if snap.exists:
                n += 1
    return n


def staged_delete(
    db: firestore.Client,
    col,
    ids: List[str],
    *,
    apply: bool,
    pilot: int,
    batch_size: int,
) -> Dict[str, Any]:
    """
    Checkpoint (Amendment 1): gate on pinned-manifest remainder, not total corpus.

    Item 4 (Core): missing-at-start is reconciled once and frozen. Any *new* missing
    ID discovered mid-sweep (not in that set, not in deleted_set) hard-stops —
    concurrent modification signal.
    """
    missing_at_start = reconcile_missing_at_start(db, col, ids)
    missing_at_start_set = set(missing_at_start)
    print(
        f"Pre-delete reconciliation: missing_at_start={len(missing_at_start)} "
        f"(tolerated; will hard-stop if missing grows mid-sweep)"
    )
    if missing_at_start:
        print("  sample missing_at_start:", missing_at_start[:10])

    deleted: List[str] = []
    skipped: List[Dict[str, str]] = []
    missing_mid: List[str] = []
    deleted_set: set = set()

    def process_chunk(chunk: List[str]) -> None:
        snaps = {s.id: s for s in db.get_all([col.document(x) for x in chunk])}
        to_del: List[str] = []
        for doc_id in chunk:
            if doc_id in missing_at_start_set:
                continue  # already logged as absent before we touched anything
            if doc_id in deleted_set:
                continue
            snap = snaps.get(doc_id)
            if snap is None or not snap.exists:
                # Item 4: new absence mid-sweep → hard stop
                missing_mid.append(doc_id)
                print(
                    f"HARD STOP: id {doc_id} missing mid-sweep "
                    f"(not in missing_at_start; concurrent modification?)"
                )
                raise SystemExit(3)
            data = snap.to_dict() or {}
            if not is_husk_delete_safe(data):
                skipped.append({"id": doc_id, "reason": "delete_predicate_failed"})
                continue
            to_del.append(doc_id)

        if apply and to_del:
            step = min(batch_size, 500)
            for j in range(0, len(to_del), step):
                batch = db.batch()
                part = to_del[j : j + step]
                for doc_id in part:
                    batch.delete(col.document(doc_id))
                batch.commit()
                deleted.extend(part)
                deleted_set.update(part)
        elif not apply:
            deleted.extend(to_del)
            deleted_set.update(to_del)

    def checkpoint(label: str) -> None:
        if not apply:
            print(
                f"  [{label}] would_delete_so_far={len(deleted)} "
                f"skipped={len(skipped)} missing_at_start={len(missing_at_start)}"
            )
            return
        rem = count_manifest_remaining(db, col, ids)
        ghost = count_manifest_remaining(db, col, list(deleted_set))
        print(
            f"  [{label}] deleted={len(deleted_set)} skipped={len(skipped)} "
            f"missing_at_start={len(missing_at_start)} manifest_remaining={rem}"
        )
        if ghost != 0:
            print(f"HARD STOP: {ghost} supposedly-deleted IDs still present in Firestore")
            raise SystemExit(3)
        # rem = pinned IDs still present in Firestore.
        # Still-present set = not-yet-deleted ∪ skipped  (missing_at_start are absent).
        # So rem == n - deleted - missing_at_start.
        # Do NOT subtract len(skipped): skips remain present and are already inside rem.
        # (Subtracting skips would false-stop: rem would be expect + len(skipped).)
        expect = len(ids) - len(deleted_set) - len(missing_at_start_set)
        if rem != expect:
            print(
                f"HARD STOP: manifest_remaining={rem} != expect {expect} "
                f"(n - deleted - missing_at_start; skipped={len(skipped)} still counted in rem)"
            )
            raise SystemExit(3)

    pilot_ids = ids[: max(0, pilot)]
    rest = ids[len(pilot_ids) :]

    if pilot_ids:
        print(f"{'DELETE' if apply else 'DRY-RUN'} pilot n={len(pilot_ids)}")
        process_chunk(pilot_ids)
        checkpoint("after_pilot")

    if rest:
        print(f"{'DELETE' if apply else 'DRY-RUN'} remainder n={len(rest)} batch_size={batch_size}")
        for i in range(0, len(rest), batch_size):
            chunk = rest[i : i + batch_size]
            process_chunk(chunk)
            checkpoint(f"after_batch_{i // batch_size + 1}")

    return {
        "apply": apply,
        "deleted_or_would": deleted,
        "deleted_count": len(deleted),
        "skipped": skipped,
        "missing_at_start": missing_at_start,
        "missing_mid": missing_mid,
        "manifest_remaining": count_manifest_remaining(db, col, ids) if apply else None,
    }


def probe_retrieval(
    db: firestore.Client,
    col,
    *,
    out_dir: Optional[Path],
    top_k: int,
    queries: Sequence[str],
    distance_measure: DistanceMeasure,
) -> Dict[str, Any]:
    """
    Pre/post hygiene probe: for each query, embed (if service available) and
    find_nearest; count Untitled titles in top-k.

    If embedding service is unavailable: LIMIT — fall back to probing with a
    stored husk embedding (documents that) so the script still produces a record.
    """
    results: Dict[str, Any] = {
        "probed_at_utc": _utcnow(),
        "top_k": top_k,
        "distance_measure": distance_measure.name,
        "probe_mode": None,  # "scientific_queries" | "husk_own_vector" | "none"
        "queries": [],
        "limits": [],
    }

    embed_fn = None
    try:
        sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
        from services.embedding_service import get_embedding_service  # type: ignore

        svc = get_embedding_service()
        if svc and hasattr(svc, "embed_text"):
            embed_fn = svc.embed_text
    except Exception as e:
        results["limits"].append(f"embedding_service_unavailable: {e!s}"[:200])

    def run_vector(label: str, vec: List[float], *, mode: str) -> Dict[str, Any]:
        untitled_hits = []
        try:
            q = col.find_nearest(
                vector_field="embedding",
                query_vector=Vector(vec),
                limit=top_k,
                distance_measure=distance_measure,
            )
            for snap in q.stream():
                data = snap.to_dict() or {}
                title = str(data.get("title") or "")
                if title.strip() == "Untitled":
                    untitled_hits.append(snap.id)
        except Exception as e:
            return {
                "label": label,
                "probe_mode": mode,
                "error": str(e)[:300],
                "untitled_in_topk": None,
            }

        return {
            "label": label,
            "probe_mode": mode,
            "untitled_in_topk": len(untitled_hits),
            "untitled_ids_sample": untitled_hits[:10],
        }

    if embed_fn:
        results["probe_mode"] = "scientific_queries"
        for qtext in queries:
            try:
                vec = embed_fn(qtext)
                if not vec:
                    results["queries"].append(
                        {"label": qtext, "probe_mode": "scientific_queries", "error": "empty_embedding"}
                    )
                    continue
                results["queries"].append(
                    run_vector(qtext, list(vec), mode="scientific_queries")
                )
            except Exception as e:
                results["queries"].append(
                    {"label": qtext, "probe_mode": "scientific_queries", "error": str(e)[:300]}
                )
    else:
        results["limits"].append(
            "No text embedding; using one stored Untitled husk vector as query. "
            "Evidence strength: husk_own_vector (weaker claim than scientific_queries)."
        )
        husk_vec = None
        husk_id = None
        for snap in col.where(filter=FieldFilter("title", "==", "Untitled")).limit(50).stream():
            data = snap.to_dict() or {}
            if data.get("embedding") is not None and _truthy_str(data.get("embedding_model")):
                try:
                    husk_vec = vector_to_floats(data.get("embedding"))
                    husk_id = snap.id
                    break
                except Exception:
                    continue
        if husk_vec:
            results["probe_mode"] = "husk_own_vector"
            results["queries"].append(
                run_vector(f"husk_vector:{husk_id}", husk_vec, mode="husk_own_vector")
            )
        else:
            results["probe_mode"] = "none"
            results["limits"].append("No Untitled husk with embedding found for fallback probe.")

    if out_dir:
        out_dir.mkdir(parents=True, exist_ok=True)
        probe_path = out_dir / f"probe_retrieval_{_utcnow().replace(':', '')}.json"
        probe_path.write_text(json.dumps(results, indent=2) + "\n", encoding="utf-8")
        print(f"Wrote {probe_path}")

    print(json.dumps(results, indent=2))
    return results


def cmd_export(args: argparse.Namespace) -> int:
    db = _client()
    col = db.collection(COLLECTION)
    out_dir = Path(args.out_dir)
    ids, rows, report = freeze_untitled(col)
    write_export(out_dir, ids, rows, report)
    print(json.dumps({"ok": True, "n": len(ids), "out_dir": str(out_dir)}, indent=2))
    return 0


def cmd_probe(args: argparse.Namespace) -> int:
    db = _client()
    col = db.collection(COLLECTION)
    out_dir = Path(args.out_dir) if args.out_dir else None
    queries = args.query or DEFAULT_PROBE_QUERIES
    measure = _parse_distance(args.distance)
    probe_retrieval(
        db,
        col,
        out_dir=out_dir,
        top_k=args.top_k,
        queries=queries,
        distance_measure=measure,
    )
    return 0


def _parse_distance(name: str) -> DistanceMeasure:
    key = (name or "COSINE").strip().upper()
    try:
        return DistanceMeasure[key]
    except KeyError:
        print(f"Unknown --distance {name!r}; use one of {[m.name for m in DistanceMeasure]}")
        raise SystemExit(2)


def cmd_delete(args: argparse.Namespace, *, apply: bool) -> int:
    out_dir = Path(args.out_dir)
    manifest_path = Path(args.manifest) if args.manifest else out_dir / "manifest.json"

    if apply:
        if not args.i_understand_delete:
            print("Refusing --delete without --i-understand-delete")
            return 2
        if not ready_marker_present(out_dir):
            print(
                f"Refusing --delete: {READY_MARKER_NAME} not found in {out_dir}. "
                "Write that marker after Gary export-go + GCS verify."
            )
            return 2

    # Item 1: re-verify archive before any delete path work (dry-run too).
    ids, _manifest = verify_archive_integrity(out_dir, manifest_path)
    print(f"Loaded verified manifest n={len(ids)} from {manifest_path}")

    db = _client()
    col = db.collection(COLLECTION)
    report = staged_delete(
        db,
        col,
        ids,
        apply=apply,
        pilot=args.pilot,
        batch_size=args.batch_size,
    )
    summary = {
        "apply": apply,
        "deleted_count": report["deleted_count"],
        "skipped_count": len(report["skipped"]),
        "missing_at_start_count": len(report["missing_at_start"]),
        "missing_mid_count": len(report["missing_mid"]),
        "skipped_sample": report["skipped"][:10],
        "manifest_remaining": report["manifest_remaining"],
    }
    print(json.dumps(summary, indent=2))
    out_path = out_dir / ("delete_report.json" if apply else "dry_run_delete_report.json")
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path.write_text(
        json.dumps(
            {
                **summary,
                "deleted_or_would_ids": report["deleted_or_would"],
                "skipped": report["skipped"],
                "missing_at_start": report["missing_at_start"],
                "missing_mid": report["missing_mid"],
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    print(f"Wrote {out_path}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    g = p.add_mutually_exclusive_group(required=True)
    g.add_argument("--export-only", action="store_true", help="Freeze + write docs.jsonl/manifest/README")
    g.add_argument("--probe-retrieval", action="store_true", help="Pre/post Untitled-in-topk probes")
    g.add_argument("--dry-run-delete", action="store_true", help="Simulate delete; no Firestore writes")
    g.add_argument("--delete", action="store_true", help="Staged delete (requires READY_TO_DELETE + flag)")

    p.add_argument("--out-dir", type=str, default="", help="Working directory for export/reports")
    p.add_argument("--manifest", type=str, default="", help="Path to manifest.json (default: OUT_DIR/manifest.json)")
    p.add_argument("--pilot", type=int, default=50, help="Pilot delete size before remainder batches")
    p.add_argument("--batch-size", type=int, default=400, help="Delete batch size (max 500)")
    p.add_argument(
        "--i-understand-delete",
        action="store_true",
        help="Required with --delete (session acknowledgment)",
    )
    p.add_argument("--top-k", type=int, default=10, help="find_nearest limit for probes")
    p.add_argument("--query", action="append", default=[], help="Probe query text (repeatable)")
    p.add_argument(
        "--distance",
        type=str,
        default="COSINE",
        help="find_nearest DistanceMeasure name (default COSINE = production vector_search.py)",
    )
    return p


def main() -> int:
    args = build_parser().parse_args()
    if args.batch_size > 500:
        print("batch-size capped at 500 (Firestore limit)")
        args.batch_size = 500

    if args.export_only:
        if not args.out_dir:
            print("--out-dir is required for --export-only")
            return 2
        return cmd_export(args)

    if args.probe_retrieval:
        if not args.out_dir:
            # allow stdout-only
            args.out_dir = ""
        return cmd_probe(args)

    if args.dry_run_delete:
        if not args.out_dir:
            print("--out-dir is required for --dry-run-delete")
            return 2
        return cmd_delete(args, apply=False)

    if args.delete:
        if not args.out_dir:
            print("--out-dir is required for --delete")
            return 2
        return cmd_delete(args, apply=True)

    return 2


if __name__ == "__main__":
    raise SystemExit(main())
