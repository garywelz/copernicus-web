#!/usr/bin/env python3
"""
Backfill OpenAI embeddings for research_papers missing embedding_model.

Amended plan 2026-07-22 (Core GO): match production space —
  model  text-embedding-3-small
  dims   1536
  field  embedding (Firestore Vector) + embedding_model

Provenance (measured): scout biology pubmed_*/biorxiv_* that landed without
an ingest-time embed pass. Not GLMP hand-delivery.

Modes (primary actions; combine --pin with nothing else, or pin then run):
  --pin           Predicate census → write manifest.json (+ README) under --out-dir
  --dry-run       Walk pinned IDs; report would-embed / would-skip; no API, no writes
  --pilot N       Embed first N still-pending IDs from manifest (writes)
  --run           Embed all remaining pending IDs from manifest (writes)

Idempotency: per-doc re-check of embedding_model at write time (skip if set).
Hard-stop if returned vector length != 1536 or response model does not match
text-embedding-3-small. Do NOT pass dimensions= to the API (match corpus request).

DO NOT use utils.auto_embedding.add_embedding_to_paper_data — it hardcodes
embedding_model='text-embedding-004' even when the factory returns OpenAI.
Reuse create_text_for_paper only (same input text as production retrieval).

Operator notes:
  - Mid-run abort on structural errors (dim/model/empty response) is expected
    fail-fast; rerun is safe (per-doc skip). Transient API errors get a few
    bounded retries with backoff, then hard-stop.
  - Re-pin after a checkpoint: if pinned_at_utc changes, delete/move
    checkpoint.json or use a fresh --out-dir (hard-stop otherwise).

Env:
  GOOGLE_CLOUD_PROJECT   default regal-scholar-453620-r7
  FIRESTORE_DATABASE     default copernicusai
  OPENAI_API_KEY         optional; else Secret Manager secret openai-api-key

Usage (Yoga, backend venv, tracked commit after Gary go):
  cd cloud-run-backend
  python scripts/backfill_research_paper_embeddings.py --pin --out-dir ../_sweep_work/embed_backfill_20260722
  python scripts/backfill_research_paper_embeddings.py --dry-run --out-dir ...
  python scripts/backfill_research_paper_embeddings.py --pilot 20 --out-dir ...
  python scripts/backfill_research_paper_embeddings.py --run --out-dir ... --batch-size 100
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple

from google.cloud import firestore
from google.cloud.firestore_v1.vector import Vector

try:
    from openai import OpenAI
except ImportError:
    OpenAI = None  # type: ignore

try:
    from google.cloud import secretmanager
except ImportError:
    secretmanager = None

# cloud-run-backend on sys.path for create_text_for_paper
_BACKEND_ROOT = Path(__file__).resolve().parent.parent
if str(_BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(_BACKEND_ROOT))

# Text construction only — NEVER import/use add_embedding_to_paper_data here.
# That helper hardcodes embedding_model='text-embedding-004' even when OpenAI
# is the active factory provider; using it would mislabel 1536d vectors.
from utils.auto_embedding import create_text_for_paper  # noqa: E402

DEFAULT_PROJECT = "regal-scholar-453620-r7"
DEFAULT_DATABASE = "copernicusai"
COLLECTION = "research_papers"
EMBEDDING_MODEL = "text-embedding-3-small"
EMBEDDING_DIMENSIONS = 1536
MANIFEST_NAME = "manifest.json"
CHECKPOINT_NAME = "checkpoint.json"
README_NAME = "README.md"
TRANSIENT_RETRIES = 3
TRANSIENT_BACKOFF_S = 2.0


def _utcnow() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _client() -> firestore.Client:
    project = os.environ.get("GOOGLE_CLOUD_PROJECT", DEFAULT_PROJECT)
    database = os.environ.get("FIRESTORE_DATABASE", DEFAULT_DATABASE)
    return firestore.Client(project=project, database=database)


def get_openai_api_key() -> Optional[str]:
    key = (os.getenv("OPENAI_API_KEY") or "").strip()
    if key:
        return key
    if not secretmanager:
        return None
    try:
        sm = secretmanager.SecretManagerServiceClient()
        name = f"projects/{DEFAULT_PROJECT}/secrets/openai-api-key/versions/latest"
        return (
            sm.access_secret_version(request={"name": name})
            .payload.data.decode("UTF-8")
            .strip()
        )
    except Exception:
        return None


def _model_empty(data: Dict[str, Any]) -> bool:
    m = data.get("embedding_model")
    return m is None or str(m).strip() == ""


def _created_at_iso(raw: Any) -> str:
    """Normalize created_at for display range (not a safety gate)."""
    if raw is None:
        return ""
    if hasattr(raw, "isoformat"):
        try:
            return str(raw.isoformat())
        except Exception:
            pass
    return str(raw)


def _estimate_tokens(text: str) -> int:
    # Rough record-keeping estimate (~4 chars/token); API usage logged when available.
    return max(1, (len(text) + 3) // 4) if text.strip() else 0


def _safe_exc(exc: BaseException) -> str:
    """Exception text for logs — never include client/env repr (key leak risk)."""
    return f"{type(exc).__name__}: {str(exc)[:300]}"


def _is_transient_api_error(exc: BaseException) -> bool:
    name = type(exc).__name__.lower()
    msg = str(exc).lower()
    if any(t in name for t in ("ratelimit", "timeout", "apiconnection", "internalserver")):
        return True
    if any(t in msg for t in ("429", "rate limit", "timeout", "503", "502", "500", "temporarily")):
        return True
    status = getattr(exc, "status_code", None) or getattr(exc, "status", None)
    try:
        if status is not None and int(status) in (408, 429, 500, 502, 503, 504):
            return True
    except Exception:
        pass
    return False


def pin_unembedded(db: firestore.Client, out_dir: Path) -> int:
    """Predicate census: empty embedding_model, title != Untitled. Write manifest."""
    out_dir.mkdir(parents=True, exist_ok=True)
    col = db.collection(COLLECTION)
    ids: List[str] = []
    pubmed = 0
    biorxiv = 0
    other = 0
    created_min: Optional[str] = None
    created_max: Optional[str] = None
    with_abstract = 0
    untitled_skipped = 0

    # Full-collection scan is intentional: Firestore cannot query "field missing".
    # A where(embedding_model == "") would miss docs where the field is absent.
    last = None
    total_scanned = 0
    while True:
        q = col.order_by("__name__").limit(500)
        if last is not None:
            q = q.start_after(last)
        docs = list(q.stream())
        if not docs:
            break
        for snap in docs:
            total_scanned += 1
            data = snap.to_dict() or {}
            if not _model_empty(data):
                continue
            title = str(data.get("title") or "").strip()
            if title.lower() == "untitled":
                untitled_skipped += 1
                continue
            ids.append(snap.id)
            if snap.id.startswith("pubmed_"):
                pubmed += 1
            elif snap.id.startswith("biorxiv_"):
                biorxiv += 1
            else:
                other += 1
            if str(data.get("abstract") or "").strip():
                with_abstract += 1
            ca = _created_at_iso(data.get("created_at"))
            if ca:
                if created_min is None or ca < created_min:
                    created_min = ca
                if created_max is None or ca > created_max:
                    created_max = ca
        last = docs[-1]

    ids.sort()
    pinned_at = _utcnow()
    manifest = {
        "pinned_at_utc": pinned_at,
        "collection": COLLECTION,
        "project": os.environ.get("GOOGLE_CLOUD_PROJECT", DEFAULT_PROJECT),
        "database": os.environ.get("FIRESTORE_DATABASE", DEFAULT_DATABASE),
        "predicate": "embedding_model empty/missing AND title != Untitled",
        "n": len(ids),
        "ids": ids,
        "provenance": {
            "pubmed_prefix": pubmed,
            "biorxiv_prefix": biorxiv,
            "other_prefix": other,
            "with_abstract": with_abstract,
            "untitled_skipped": untitled_skipped,
            "created_at_min": created_min,
            "created_at_max": created_max,
            "corpus_scanned": total_scanned,
            "note": (
                "Scout biology ingest without embed pass (measured 2026-07-22); "
                "not GLMP flowchart hand-delivery."
            ),
        },
        "target_model": EMBEDDING_MODEL,
        "target_dimensions": EMBEDDING_DIMENSIONS,
    }
    manifest_path = out_dir / MANIFEST_NAME
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")

    ck_path = out_dir / CHECKPOINT_NAME
    ck_note = ""
    if ck_path.is_file():
        ck_note = (
            f"\n**Note:** `{CHECKPOINT_NAME}` already exists in this out-dir. "
            "A new pin does not delete it; `--dry-run`/`--pilot`/`--run` will "
            "HARD STOP if checkpoint.manifest_pinned_at_utc ≠ this pin. "
            "Move/delete the checkpoint or use a fresh --out-dir after re-pin.\n"
        )

    readme = f"""# Research-paper embedding backfill pin

- Pinned at (UTC): {pinned_at}
- n: **{len(ids)}**
- Model/dims: `{EMBEDDING_MODEL}` / {EMBEDDING_DIMENSIONS}
- Predicate: empty `embedding_model`, title ≠ Untitled
- Provenance: pubmed={pubmed}, biorxiv={biorxiv}, other={other}; abstracts={with_abstract}/{len(ids)}
- created_at range: {created_min} → {created_max}
{ck_note}
## Sequence

1. `--dry-run` (no writes)
2. `--pilot 20` after Gary pilot-go
3. `--run` after Gary remainder-go
4. Re-census + scientific_queries probe (separate / sweep script)

Rerun-safe: per-doc skip if `embedding_model` already set.

Abort behavior: structural errors (wrong dim/model, empty API response) hard-stop
immediately. Transient API errors (429/5xx/timeout) retry a few times with backoff,
then hard-stop. Rerun is safe either way.
"""
    (out_dir / README_NAME).write_text(readme, encoding="utf-8")
    print(f"Pinned n={len(ids)} → {manifest_path}")
    print(f"Provenance: pubmed={pubmed} biorxiv={biorxiv} other={other}")
    print(f"Corpus scanned: {total_scanned}; untitled skipped: {untitled_skipped}")
    if ck_path.is_file():
        print(
            f"WARNING: existing {CHECKPOINT_NAME} left in place — "
            "will hard-stop if pin timestamps differ"
        )
    return 0


def load_manifest(out_dir: Path) -> Dict[str, Any]:
    path = out_dir / MANIFEST_NAME
    if not path.is_file():
        raise FileNotFoundError(f"missing manifest: {path} (run --pin first)")
    manifest = json.loads(path.read_text(encoding="utf-8"))
    ids = list(manifest.get("ids") or [])
    n = manifest.get("n")
    if n != len(ids):
        raise ValueError(f"manifest n={n} != len(ids)={len(ids)}")
    return manifest


def load_checkpoint(out_dir: Path) -> Optional[Dict[str, Any]]:
    path = out_dir / CHECKPOINT_NAME
    if not path.is_file():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def write_checkpoint(
    out_dir: Path,
    *,
    manifest_pinned_at_utc: str,
    remaining_ids: Sequence[str],
    completed_ids: Sequence[str],
    skipped_ids: Sequence[str],
    failed_ids: Sequence[str],
    tokens_total: int,
) -> None:
    payload = {
        "updated_at_utc": _utcnow(),
        "manifest_pinned_at_utc": manifest_pinned_at_utc,
        "remaining_n": len(remaining_ids),
        "remaining_ids": list(remaining_ids),
        "completed_n": len(completed_ids),
        "completed_ids": list(completed_ids),
        "skipped_n": len(skipped_ids),
        "skipped_ids": list(skipped_ids),
        "failed_n": len(failed_ids),
        "failed_ids": list(failed_ids),
        "tokens_total": tokens_total,
        "model": EMBEDDING_MODEL,
        "dimensions": EMBEDDING_DIMENSIONS,
    }
    path = out_dir / CHECKPOINT_NAME
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    print(f"Checkpoint: remaining={len(remaining_ids)} → {path}")


def pending_ids(manifest: Dict[str, Any], out_dir: Path) -> List[str]:
    """IDs still to process: checkpoint remaining if present, else full manifest."""
    ck = load_checkpoint(out_dir)
    if ck and "remaining_ids" in ck:
        ck_pin = ck.get("manifest_pinned_at_utc")
        man_pin = manifest.get("pinned_at_utc")
        if ck_pin != man_pin:
            raise ValueError(
                "HARD STOP: checkpoint belongs to a different pin "
                f"({ck_pin!r} != {man_pin!r}). "
                "Move/delete checkpoint.json or use a fresh --out-dir."
            )
        return list(ck["remaining_ids"])
    return list(manifest["ids"])


def embed_one(
    client: Any,
    text: str,
) -> Tuple[List[float], int]:
    """
    One document → one embeddings.create(input=str) call.

    Intentionally NOT a multi-input batch: avoids index/order mismatch when
    zipping response.data back to doc IDs (silent wrong-vector assignment).

    Do not pass dimensions= — corpus vectors were requested without reduction;
    native 1536 must match that request path. Post-hoc len() assert catches surprises.
    """
    last_exc: Optional[BaseException] = None
    for attempt in range(1, TRANSIENT_RETRIES + 1):
        try:
            # No dimensions= kwarg (see docstring).
            response = client.embeddings.create(model=EMBEDDING_MODEL, input=text)
            data = getattr(response, "data", None) or []
            if len(data) != 1:
                raise RuntimeError(
                    f"HARD STOP: expected 1 embedding in response, got {len(data)}"
                )
            returned_model = str(getattr(response, "model", "") or "")
            # startswith: OpenAI may return dated variants; genuine mismatches still trip.
            if not returned_model.startswith(EMBEDDING_MODEL):
                raise RuntimeError(
                    f"HARD STOP: response model {returned_model!r} does not match "
                    f"requested {EMBEDDING_MODEL!r}"
                )
            vec = list(data[0].embedding)
            # Dimension gate BEFORE any Firestore write (caller must not write on raise).
            if len(vec) != EMBEDDING_DIMENSIONS:
                raise RuntimeError(
                    f"HARD STOP: unexpected dimension {len(vec)} "
                    f"(expected {EMBEDDING_DIMENSIONS})"
                )
            tokens = 0
            usage = getattr(response, "usage", None)
            if usage is not None:
                tokens = int(getattr(usage, "total_tokens", 0) or 0)
            if not tokens:
                tokens = _estimate_tokens(text)
            return vec, tokens
        except Exception as exc:
            last_exc = exc
            # Structural HARD STOP messages: never retry.
            if "HARD STOP" in str(exc):
                raise
            if _is_transient_api_error(exc) and attempt < TRANSIENT_RETRIES:
                wait = TRANSIENT_BACKOFF_S * attempt
                print(
                    f"  transient API error (attempt {attempt}/{TRANSIENT_RETRIES}): "
                    f"{_safe_exc(exc)}; sleep {wait:.1f}s"
                )
                time.sleep(wait)
                continue
            raise
    assert last_exc is not None
    raise last_exc


def process_ids(
    db: firestore.Client,
    client: Optional[Any],
    out_dir: Path,
    work_ids: Sequence[str],
    queue_ids: Sequence[str],
    *,
    manifest_pinned_at_utc: str,
    write: bool,
    batch_size: int,
    sleep_s: float,
) -> int:
    """
    Process work_ids (pilot slice or full run).

    queue_ids is the full pending queue used for checkpoint remainder so a
    --pilot 20 leaves the other ~385 IDs in remaining_ids.
    """
    col = db.collection(COLLECTION)
    work = list(work_ids)
    queue = list(queue_ids)
    completed: List[str] = []
    skipped: List[str] = []
    failed: List[str] = []
    tokens_total = 0
    est_tokens = 0

    ck = load_checkpoint(out_dir)
    if ck:
        # pending_ids already validated pin identity; restore accounting lists.
        completed = list(ck.get("completed_ids") or [])
        skipped = list(ck.get("skipped_ids") or [])
        failed = list(ck.get("failed_ids") or [])
        tokens_total = int(ck.get("tokens_total") or 0)

    print(
        f"Mode: {'WRITE' if write else 'DRY-RUN'} | "
        f"work={len(work)} queue={len(queue)} batch_size={batch_size}"
    )

    def _remainder() -> List[str]:
        done = set(completed) | set(skipped)
        # Failed IDs stay in remaining for inspect/rerun.
        return [i for i in queue if i not in done]

    def _checkpoint() -> None:
        if not write:
            return
        write_checkpoint(
            out_dir,
            manifest_pinned_at_utc=manifest_pinned_at_utc,
            remaining_ids=_remainder(),
            completed_ids=completed,
            skipped_ids=skipped,
            failed_ids=failed,
            tokens_total=tokens_total,
        )

    processed_this_run = 0
    idx = 0
    while idx < len(work):
        batch = work[idx : idx + max(1, batch_size)]
        idx += len(batch)

        for doc_id in batch:
            try:
                ref = col.document(doc_id)
                snap = ref.get()
                if not snap.exists:
                    print(f"  SKIP missing doc {doc_id}")
                    skipped.append(doc_id)
                    processed_this_run += 1
                    continue

                data = snap.to_dict() or {}
                # Per-doc re-check (husk-sweep idempotency): skip if already embedded.
                if not _model_empty(data):
                    existing = str(data.get("embedding_model") or "").strip()
                    print(f"  SKIP already set embedding_model={existing!r} {doc_id}")
                    skipped.append(doc_id)
                    processed_this_run += 1
                    continue

                text = create_text_for_paper(data)
                if text is None or not str(text).strip():
                    # Census said all 405 have abstracts; if this fires, skip + continue
                    # so the operator is not stuck hand-editing checkpoint JSON.
                    print(f"  SKIP empty embed text {doc_id}")
                    skipped.append(doc_id)
                    processed_this_run += 1
                    continue

                text = str(text)
                est = _estimate_tokens(text)
                est_tokens += est

                if not write:
                    print(f"  WOULD-EMBED {doc_id} chars={len(text)} est_tokens≈{est}")
                    processed_this_run += 1
                    continue

                assert client is not None
                vec, tokens = embed_one(client, text)
                # Re-assert immediately before write (per-vector, not post-batch).
                if len(vec) != EMBEDDING_DIMENSIONS:
                    raise RuntimeError(
                        f"HARD STOP: pre-write dim {len(vec)} != {EMBEDDING_DIMENSIONS}"
                    )
                ref.update(
                    {
                        "embedding": Vector(vec),
                        "embedding_model": EMBEDDING_MODEL,
                        "embedding_updated": _utcnow(),
                    }
                )
                tokens_total += tokens
                completed.append(doc_id)
                if doc_id in failed:
                    failed.remove(doc_id)
                processed_this_run += 1
                print(
                    f"  OK {doc_id} dims={len(vec)} model={EMBEDDING_MODEL} "
                    f"tokens={tokens}"
                )
                if sleep_s > 0:
                    time.sleep(sleep_s)
            except Exception as exc:
                if not write:
                    raise
                if doc_id not in failed:
                    failed.append(doc_id)
                print(f"  FAIL {doc_id} — {_safe_exc(exc)}")
                _checkpoint()
                print("HARD STOP after failure — fix/report before remainder-go.")
                return 2

        if write:
            _checkpoint()
            rem = _remainder()
            print(
                f"Batch checkpoint: completed={len(completed)} skipped={len(skipped)} "
                f"failed={len(failed)} remaining={len(rem)} "
                f"tokens_total={tokens_total}"
            )

    if not write:
        print(
            f"Dry-run done. would_consider={processed_this_run} "
            f"est_tokens≈{est_tokens} (no API calls, checkpoint unchanged)"
        )
        return 0

    rem = _remainder()
    print("=" * 60)
    print("BACKFILL RUN COMPLETE")
    print(f"completed={len(completed)} skipped={len(skipped)} failed={len(failed)}")
    print(f"remaining={len(rem)} tokens_total={tokens_total}")
    print("=" * 60)
    # Remaining > 0 is normal after --pilot; only failures are errors.
    return 1 if failed else 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--out-dir",
        required=True,
        help="Working dir for manifest.json / checkpoint.json (e.g. _sweep_work/embed_backfill_YYYYMMDD)",
    )
    parser.add_argument("--pin", action="store_true", help="Census + write pinned manifest")
    parser.add_argument("--dry-run", action="store_true", help="Plan only; no API, no writes")
    parser.add_argument(
        "--pilot",
        type=int,
        default=0,
        metavar="N",
        help="Embed first N pending IDs from manifest (writes)",
    )
    parser.add_argument("--run", action="store_true", help="Embed all remaining pending IDs")
    parser.add_argument(
        "--batch-size",
        type=int,
        default=100,
        help="Checkpoint cadence for --pilot / --run (default 100)",
    )
    parser.add_argument(
        "--sleep",
        type=float,
        default=0.05,
        help="Sleep seconds between successful embeds (rate-limit cushion)",
    )
    args = parser.parse_args()

    modes = sum(
        [
            bool(args.pin),
            bool(args.dry_run),
            bool(args.pilot and args.pilot > 0),
            bool(args.run),
        ]
    )
    if modes != 1:
        print(
            "ERROR: choose exactly one of --pin | --dry-run | --pilot N | --run",
            file=sys.stderr,
        )
        return 2

    out_dir = Path(args.out_dir).expanduser().resolve()
    db = _client()

    if args.pin:
        return pin_unembedded(db, out_dir)

    try:
        manifest = load_manifest(out_dir)
    except Exception as exc:
        print(f"HARD STOP: {_safe_exc(exc)}", file=sys.stderr)
        return 2

    print(
        f"Manifest n={manifest['n']} pinned_at={manifest.get('pinned_at_utc')} "
        f"target={manifest.get('target_model')}@{manifest.get('target_dimensions')}"
    )
    if manifest.get("target_model") != EMBEDDING_MODEL:
        print("HARD STOP: manifest target_model mismatch", file=sys.stderr)
        return 2
    if int(manifest.get("target_dimensions") or 0) != EMBEDDING_DIMENSIONS:
        print("HARD STOP: manifest target_dimensions mismatch", file=sys.stderr)
        return 2

    pin_at = str(manifest.get("pinned_at_utc") or "")
    if not pin_at:
        print("HARD STOP: manifest missing pinned_at_utc", file=sys.stderr)
        return 2

    try:
        queue = pending_ids(manifest, out_dir)
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        return 2

    work = queue
    if args.pilot and args.pilot > 0:
        work = queue[: args.pilot]
        print(f"Pilot slice: work={len(work)} of queue={len(queue)}")

    if args.dry_run:
        return process_ids(
            db,
            None,
            out_dir,
            work,
            queue,
            manifest_pinned_at_utc=pin_at,
            write=False,
            batch_size=max(1, int(args.batch_size)),
            sleep_s=0.0,
        )

    if OpenAI is None:
        print("ERROR: openai package not installed", file=sys.stderr)
        return 1
    api_key = get_openai_api_key()
    if not api_key:
        print(
            "ERROR: OPENAI_API_KEY not in env or Secret Manager (openai-api-key)",
            file=sys.stderr,
        )
        return 1
    # Pass key only into the client — do not mirror into os.environ (traceback leak risk).
    # Never print api_key, client, or response objects.
    print("OpenAI API key: found via env or Secret Manager")
    client = OpenAI(api_key=api_key)
    del api_key

    return process_ids(
        db,
        client,
        out_dir,
        work,
        queue,
        manifest_pinned_at_utc=pin_at,
        write=True,
        batch_size=max(1, int(args.batch_size)),
        sleep_s=max(0.0, float(args.sleep)),
    )


if __name__ == "__main__":
    raise SystemExit(main())
