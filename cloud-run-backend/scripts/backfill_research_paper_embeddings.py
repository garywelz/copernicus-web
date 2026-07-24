#!/usr/bin/env python3
"""
Backfill OpenAI embeddings for Firestore collections missing embedding_model.

Amended plan 2026-07-22 (Core GO) + episodes parameterization 2026-07-23:
  model  text-embedding-3-small
  dims   1536
  field  embedding (Firestore Vector) + embedding_model

Collections (``--collection``):
  research_papers  — empty embedding_model AND title != Untitled
                     (Untitled clause is husk-sweep residue; papers only)
  episodes         — empty embedding_model alone; text via create_text_for_podcast
                     (accepts description OR description_markdown)

Modes (exactly one):
  --pin           Predicate census → write manifest.json (+ README) under --out-dir
  --dry-run       Walk pinned IDs; report would-embed / would-skip; no API, no writes
  --pilot N       Embed first N still-pending IDs from manifest (writes)
  --run           Embed all remaining pending IDs from manifest (writes)
  --auto          Unattended gap fill: live census (no manifest/pin/checkpoint),
                  embed via shared process_one_doc. Cap with --max-docs
                  (default 500). Append dated JSONL under --log-dir
                  (default /media/sdcard/logs). Exit 0 success/idle, 2 hard-stop,
                  3 refuse over cap (no writes).

Idempotency: per-doc re-check of embedding_model at write time (skip if set).
Hard-stop (StructuralError) if returned vector length != 1536 or response model
does not match text-embedding-3-small. Do NOT pass dimensions= to the API
(match corpus request). Structural errors bypass the transient retry loop.

Reuse create_text_for_* only — not add_embedding_to_* helpers (those are
non-blocking write-path wrappers; this tool owns API gates + checkpointing).
Per-doc embed+write is shared (process_one_doc) by process_ids and --auto
so safety gates cannot drift.

Operator notes:
  - Mid-run abort on structural errors (dim/model/empty response) is expected
    fail-fast; rerun is safe (per-doc skip). Transient API errors get a few
    bounded retries with backoff, then hard-stop.
  - Re-pin after a checkpoint: if pinned_at_utc changes, delete/move
    checkpoint.json or use a fresh --out-dir (hard-stop otherwise).
  - Episodes pilot: prefer ``--pilot 5`` then a live find_nearest proof before
    remainder — count coverage alone is not enough.
  - Cron: pin ``--collection research_papers --auto`` explicitly. Hook is
    non-blocking (status_publish still runs if embed fails).

Env:
  GOOGLE_CLOUD_PROJECT   default regal-scholar-453620-r7
  FIRESTORE_DATABASE     default copernicusai
  OPENAI_API_KEY         optional; else Secret Manager secret openai-api-key

Usage (Yoga, system Python 3.12 + ADC; tracked commit after Gary go):
  cd cloud-run-backend
  python scripts/backfill_research_paper_embeddings.py --collection episodes \\
    --pin --out-dir ../_sweep_work/embed_episodes_20260723
  python scripts/backfill_research_paper_embeddings.py --collection episodes \\
    --dry-run --out-dir ...
  python scripts/backfill_research_paper_embeddings.py --collection episodes \\
    --pilot 5 --out-dir ...
  python scripts/backfill_research_paper_embeddings.py --collection episodes \\
    --run --out-dir ... --batch-size 50
  python scripts/backfill_research_paper_embeddings.py \\
    --collection research_papers --auto --max-docs 500
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Sequence, Tuple

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

# cloud-run-backend on sys.path for create_text_for_*
_BACKEND_ROOT = Path(__file__).resolve().parent.parent
if str(_BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(_BACKEND_ROOT))

from utils.auto_embedding import (  # noqa: E402
    create_text_for_paper,
    create_text_for_podcast,
)

DEFAULT_PROJECT = "regal-scholar-453620-r7"
DEFAULT_DATABASE = "copernicusai"
DEFAULT_COLLECTION = "research_papers"
EMBEDDING_MODEL = "text-embedding-3-small"
EMBEDDING_DIMENSIONS = 1536
MANIFEST_NAME = "manifest.json"
CHECKPOINT_NAME = "checkpoint.json"
README_NAME = "README.md"
TRANSIENT_RETRIES = 3
TRANSIENT_BACKOFF_S = 2.0
DEFAULT_LOG_DIR = "/media/sdcard/logs"
DEFAULT_MAX_DOCS = 500

TextBuilder = Callable[[Dict[str, Any]], str]
SelectFn = Callable[[Dict[str, Any], str], bool]


@dataclass(frozen=True)
class DocEmbedResult:
    """Outcome of process_one_doc (gates shared by process_ids and --auto)."""

    outcome: str  # skipped_* | would_embed | completed
    tokens: int = 0
    est_tokens: int = 0
    detail: str = ""


class StructuralError(RuntimeError):
    """
    Fail-fast structural fault: wrong dim/model, empty API payload, pin mismatch.

    Must bypass the transient-API retry loop and terminate the run. Do not wrap
    rate-limits / 5xx / timeouts in this type.
    """


@dataclass(frozen=True)
class CollectionProfile:
    name: str
    text_builder: TextBuilder
    select: SelectFn
    predicate_label: str
    # Fields needed by select() for --auto live census. Projection avoids
    # shipping 1536-float vectors (~GB/scan) to the Jetson for a two-field gate.
    census_fields: Tuple[str, ...]


def _select_papers(data: Dict[str, Any], _doc_id: str) -> bool:
    # Works on projected dicts: missing embedding_model → empty; missing title → "".
    if not _model_empty(data):
        return False
    title = str(data.get("title") or "").strip()
    if title.lower() == "untitled":
        return False
    return True


def _select_episodes(data: Dict[str, Any], _doc_id: str) -> bool:
    # Episodes: no Untitled husk clause — that guard is papers/husk-sweep residue.
    return _model_empty(data)


PROFILES: Dict[str, CollectionProfile] = {
    "research_papers": CollectionProfile(
        name="research_papers",
        text_builder=create_text_for_paper,
        select=_select_papers,
        predicate_label="embedding_model empty/missing AND title != Untitled",
        census_fields=("embedding_model", "title"),
    ),
    "episodes": CollectionProfile(
        name="episodes",
        text_builder=create_text_for_podcast,
        select=_select_episodes,
        predicate_label="embedding_model empty/missing",
        census_fields=("embedding_model",),
    ),
}


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


def _id_prefix(doc_id: str) -> str:
    if "_" in doc_id:
        return doc_id.split("_", 1)[0]
    if "-" in doc_id:
        return doc_id.split("-", 1)[0]
    return "other"


def _build_provenance(
    profile: CollectionProfile,
    *,
    ids: Sequence[str],
    scanned: List[Tuple[str, Dict[str, Any]]],
    total_scanned: int,
    untitled_skipped: int,
) -> Dict[str, Any]:
    """Collection-specific pin metadata — no paper-only fields on episodes."""
    created_min: Optional[str] = None
    created_max: Optional[str] = None
    for _doc_id, data in scanned:
        ca = _created_at_iso(data.get("created_at") or data.get("generated_at"))
        if ca:
            if created_min is None or ca < created_min:
                created_min = ca
            if created_max is None or ca > created_max:
                created_max = ca

    prefix_counts: Dict[str, int] = {}
    for doc_id in ids:
        p = _id_prefix(doc_id)
        prefix_counts[p] = prefix_counts.get(p, 0) + 1

    base: Dict[str, Any] = {
        "id_prefix_counts": dict(sorted(prefix_counts.items())),
        "corpus_scanned": total_scanned,
        "created_at_min": created_min,
        "created_at_max": created_max,
    }

    if profile.name == "research_papers":
        with_abstract = sum(
            1 for _i, d in scanned if str(d.get("abstract") or "").strip()
        )
        base.update(
            {
                "with_abstract": with_abstract,
                "untitled_skipped": untitled_skipped,
                "note": (
                    "Scout biology ingest without embed pass (measured 2026-07-22); "
                    "not GLMP flowchart hand-delivery."
                ),
            }
        )
    elif profile.name == "episodes":
        with_script = sum(1 for _i, d in scanned if str(d.get("script") or "").strip())
        with_desc_md = sum(
            1 for _i, d in scanned if str(d.get("description_markdown") or "").strip()
        )
        with_job_id = sum(1 for _i, d in scanned if str(d.get("job_id") or "").strip())
        base.update(
            {
                "with_script": with_script,
                "with_description_markdown": with_desc_md,
                "with_job_id": with_job_id,
                "note": (
                    "Episodes catalog had 0 embeddings while find_nearest targets "
                    "episodes; podcast_jobs held stranded vectors (2026-07-23)."
                ),
            }
        )
    return base


def pin_unembedded(
    db: firestore.Client,
    out_dir: Path,
    profile: CollectionProfile,
) -> int:
    """Predicate census for the selected collection. Write manifest.

    Reads full documents (not a field projection) so provenance can count
    abstracts/scripts/etc. Paginated, so it will not hit the unbounded-stream
    timeout — but each page still ships vectors. Run from the Yoga 9i (ADC),
    not the Jetson; for Jetson gap-fill use --auto (projected census).
    """
    out_dir.mkdir(parents=True, exist_ok=True)
    col = db.collection(profile.name)
    ids: List[str] = []
    scanned_hits: List[Tuple[str, Dict[str, Any]]] = []
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
            # Track Untitled skips only for papers (predicate residue accounting).
            if profile.name == "research_papers":
                if _model_empty(data):
                    title = str(data.get("title") or "").strip()
                    if title.lower() == "untitled":
                        untitled_skipped += 1
            if not profile.select(data, snap.id):
                continue
            ids.append(snap.id)
            scanned_hits.append((snap.id, data))
        last = docs[-1]

    ids.sort()
    pinned_at = _utcnow()
    provenance = _build_provenance(
        profile,
        ids=ids,
        scanned=scanned_hits,
        total_scanned=total_scanned,
        untitled_skipped=untitled_skipped,
    )
    manifest = {
        "pinned_at_utc": pinned_at,
        "collection": profile.name,
        "project": os.environ.get("GOOGLE_CLOUD_PROJECT", DEFAULT_PROJECT),
        "database": os.environ.get("FIRESTORE_DATABASE", DEFAULT_DATABASE),
        "predicate": profile.predicate_label,
        "n": len(ids),
        "ids": ids,
        "provenance": provenance,
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

    prov_lines = "\n".join(f"- {k}: {v}" for k, v in provenance.items())
    readme = f"""# Embedding backfill pin — `{profile.name}`

- Pinned at (UTC): {pinned_at}
- n: **{len(ids)}**
- Model/dims: `{EMBEDDING_MODEL}` / {EMBEDDING_DIMENSIONS}
- Predicate: {profile.predicate_label}
- Provenance:
{prov_lines}
{ck_note}
## Sequence

1. `--dry-run` (no writes)
2. `--pilot N` (episodes: start with 5, then live find_nearest proof)
3. `--run` after remainder-go
4. Re-census + findability probe (not count alone)

Rerun-safe: per-doc skip if `embedding_model` already set.

Abort behavior: StructuralError (wrong dim/model, empty API response) hard-stops
immediately and bypasses retries. Transient API errors (429/5xx/timeout) retry a
few times with backoff, then hard-stop. Rerun is safe either way.
"""
    (out_dir / README_NAME).write_text(readme, encoding="utf-8")
    print(f"Pinned n={len(ids)} collection={profile.name} → {manifest_path}")
    print(f"Predicate: {profile.predicate_label}")
    print(f"Corpus scanned: {total_scanned}")
    if profile.name == "research_papers":
        print(f"Untitled skipped: {untitled_skipped}")
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
            raise StructuralError(
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

    StructuralError bypasses the transient retry loop (isinstance check below).
    """
    last_exc: Optional[BaseException] = None
    for attempt in range(1, TRANSIENT_RETRIES + 1):
        try:
            # No dimensions= kwarg (see docstring).
            response = client.embeddings.create(model=EMBEDDING_MODEL, input=text)
            data = getattr(response, "data", None) or []
            if len(data) != 1:
                raise StructuralError(
                    f"HARD STOP: expected 1 embedding in response, got {len(data)}"
                )
            returned_model = str(getattr(response, "model", "") or "")
            # startswith: OpenAI may return dated variants; genuine mismatches still trip.
            if not returned_model.startswith(EMBEDDING_MODEL):
                raise StructuralError(
                    f"HARD STOP: response model {returned_model!r} does not match "
                    f"requested {EMBEDDING_MODEL!r}"
                )
            vec = list(data[0].embedding)
            # Dimension gate BEFORE any Firestore write (caller must not write on raise).
            if len(vec) != EMBEDDING_DIMENSIONS:
                raise StructuralError(
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
        except StructuralError:
            # Structural faults never retry — re-raise immediately.
            raise
        except Exception as exc:
            last_exc = exc
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


def process_one_doc(
    col: Any,
    client: Optional[Any],
    profile: CollectionProfile,
    doc_id: str,
    *,
    write: bool,
    sleep_s: float,
) -> DocEmbedResult:
    """
    Shared per-doc path for process_ids and --auto.

    Gates (must not drift between callers):
      - per-doc embedding_model re-check (skip if set)
      - empty text skip
      - embed_one: no dimensions=, single-input, response-model assert,
        1536 assert, StructuralError bypasses retry
      - pre-write 1536 re-assert
      - write embedding + embedding_model + embedding_updated

    Raises StructuralError / exhausted transient errors on hard-stop.
    """
    ref = col.document(doc_id)
    snap = ref.get()
    if not snap.exists:
        print(f"  SKIP missing doc {doc_id}")
        return DocEmbedResult(outcome="skipped_missing", detail="missing")

    data = snap.to_dict() or {}
    # Per-doc re-check (idempotency): skip if already embedded.
    if not _model_empty(data):
        existing = str(data.get("embedding_model") or "").strip()
        print(f"  SKIP already set embedding_model={existing!r} {doc_id}")
        return DocEmbedResult(
            outcome="skipped_already", detail=f"embedding_model={existing}"
        )

    text = profile.text_builder(data)
    if text is None or not str(text).strip():
        print(f"  SKIP empty embed text {doc_id}")
        return DocEmbedResult(outcome="skipped_empty_text", detail="empty_text")

    text = str(text)
    est = _estimate_tokens(text)

    if not write:
        print(f"  WOULD-EMBED {doc_id} chars={len(text)} est_tokens≈{est}")
        return DocEmbedResult(outcome="would_embed", est_tokens=est)

    assert client is not None
    vec, tokens = embed_one(client, text)
    # Re-assert immediately before write (per-vector, not post-batch).
    if len(vec) != EMBEDDING_DIMENSIONS:
        raise StructuralError(
            f"HARD STOP: pre-write dim {len(vec)} != {EMBEDDING_DIMENSIONS}"
        )
    ref.update(
        {
            "embedding": Vector(vec),
            "embedding_model": EMBEDDING_MODEL,
            "embedding_updated": _utcnow(),
        }
    )
    print(
        f"  OK {doc_id} dims={len(vec)} model={EMBEDDING_MODEL} tokens={tokens}"
    )
    if sleep_s > 0:
        time.sleep(sleep_s)
    return DocEmbedResult(outcome="completed", tokens=tokens, est_tokens=est)


def process_ids(
    db: firestore.Client,
    client: Optional[Any],
    out_dir: Path,
    work_ids: Sequence[str],
    queue_ids: Sequence[str],
    profile: CollectionProfile,
    *,
    manifest_pinned_at_utc: str,
    write: bool,
    batch_size: int,
    sleep_s: float,
) -> int:
    """
    Process work_ids (pilot slice or full run).

    queue_ids is the full pending queue used for checkpoint remainder so a
    --pilot N leaves the other IDs in remaining_ids.
    """
    col = db.collection(profile.name)
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
        f"Mode: {'WRITE' if write else 'DRY-RUN'} | collection={profile.name} | "
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
                result = process_one_doc(
                    col,
                    client,
                    profile,
                    doc_id,
                    write=write,
                    sleep_s=sleep_s if write else 0.0,
                )
                if result.outcome == "completed":
                    tokens_total += result.tokens
                    completed.append(doc_id)
                    if doc_id in failed:
                        failed.remove(doc_id)
                elif result.outcome == "would_embed":
                    est_tokens += result.est_tokens
                else:
                    skipped.append(doc_id)
                    est_tokens += result.est_tokens
                processed_this_run += 1
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
    print(f"collection={profile.name}")
    print(f"completed={len(completed)} skipped={len(skipped)} failed={len(failed)}")
    print(f"remaining={len(rem)} tokens_total={tokens_total}")
    print("=" * 60)
    # Remaining > 0 is normal after --pilot; only failures are errors.
    # Human-gated pilot/run keeps exit 1 for non-empty failed (historical).
    # --auto uses exit 2 via run_auto (see that path).
    return 1 if failed else 0


def census_unembedded(
    db: firestore.Client, profile: CollectionProfile
) -> Tuple[List[str], float]:
    """Live full-collection scan; returns (matching ids, scan_seconds).

    Uses a field projection (profile.census_fields) so vectors / large text
    are not pulled into RAM. select() must tolerate missing projected keys.
    Paginated like pin_unembedded — a single unbounded stream of full docs
    can hit Firestore query timeouts on this corpus.
    """
    t0 = time.monotonic()
    ids: List[str] = []
    col = db.collection(profile.name)
    fields = list(profile.census_fields)
    # Full scan intentional: Firestore cannot query "field missing".
    # Projection: only the fields the predicate needs (never the Vector).
    last = None
    while True:
        q = col.select(fields).order_by("__name__").limit(500)
        if last is not None:
            q = q.start_after(last)
        docs = list(q.stream())
        if not docs:
            break
        for snap in docs:
            data = snap.to_dict() or {}
            if profile.select(data, snap.id):
                ids.append(snap.id)
        last = docs[-1]
    return ids, time.monotonic() - t0


def _append_auto_run_log(log_dir: Path, record: Dict[str, Any]) -> Path:
    log_dir.mkdir(parents=True, exist_ok=True)
    day = datetime.now(timezone.utc).strftime("%Y%m%d")
    path = log_dir / f"embed_auto_{day}.jsonl"
    with path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(record, sort_keys=True) + "\n")
    return path


def _openai_client_or_exit() -> Tuple[Optional[Any], int]:
    """Build OpenAI client. Returns (client, 0) or (None, 2) on config hard-stop.

    Exit code 2 matches the --auto / suite hard-stop contract (not 1).
    """
    if OpenAI is None:
        print("ERROR: openai package not installed", file=sys.stderr)
        return None, 2
    api_key = get_openai_api_key()
    if not api_key:
        print(
            "ERROR: OPENAI_API_KEY not in env or Secret Manager (openai-api-key)",
            file=sys.stderr,
        )
        return None, 2
    # Pass key only into the client — do not mirror into os.environ (traceback leak risk).
    # Never print api_key, client, or response objects.
    print("OpenAI API key: found via env or Secret Manager")
    client = OpenAI(api_key=api_key)
    del api_key
    return client, 0


def run_auto(
    db: firestore.Client,
    profile: CollectionProfile,
    *,
    max_docs: int,
    log_dir: Path,
    sleep_s: float,
) -> int:
    """
    Unattended gap fill. No manifest, pin, or checkpoint — the gap is the state.

    Exit: 0 success/idle, 2 structural/transient-after-retry/config, 3 over cap.
    """
    t_run0 = time.monotonic()
    print(
        f"Mode: AUTO | collection={profile.name} | max_docs={max_docs} | "
        f"predicate={profile.predicate_label} | "
        f"census_fields={list(profile.census_fields)}"
    )
    ids, scan_s = census_unembedded(db, profile)
    n = len(ids)
    print(f"Auto census: n={n} scan_seconds={scan_s:.2f}")

    if n == 0:
        record = {
            "event": "nothing_to_do",
            "utc": _utcnow(),
            "collection": profile.name,
            "n": 0,
            "scan_seconds": round(scan_s, 3),
            "duration_seconds": round(time.monotonic() - t_run0, 3),
            "max_docs": max_docs,
        }
        path = _append_auto_run_log(log_dir, record)
        print(f"nothing_to_do → {path}")
        return 0

    if n > max_docs:
        record = {
            "event": "refuse_over_cap",
            "utc": _utcnow(),
            "collection": profile.name,
            "n": n,
            "max_docs": max_docs,
            "scan_seconds": round(scan_s, 3),
            "duration_seconds": round(time.monotonic() - t_run0, 3),
            "writes": False,
        }
        path = _append_auto_run_log(log_dir, record)
        print(
            f"REFUSE: n={n} > max_docs={max_docs}; no writes. log={path}",
            file=sys.stderr,
        )
        return 3

    client, key_rc = _openai_client_or_exit()
    if key_rc != 0:
        return key_rc

    col = db.collection(profile.name)
    completed: List[str] = []
    skipped_ids_by_outcome: Dict[str, List[str]] = {}
    failed: List[str] = []
    tokens_total = 0
    hard_stop_exc: Optional[str] = None

    for doc_id in ids:
        try:
            result = process_one_doc(
                col, client, profile, doc_id, write=True, sleep_s=sleep_s
            )
            if result.outcome == "completed":
                completed.append(doc_id)
                tokens_total += result.tokens
            else:
                skipped_ids_by_outcome.setdefault(result.outcome, []).append(doc_id)
        except Exception as exc:
            failed.append(doc_id)
            hard_stop_exc = _safe_exc(exc)
            print(f"  FAIL {doc_id} — {hard_stop_exc}")
            print("HARD STOP after failure (auto).", file=sys.stderr)
            break

    skipped_counts = {
        outcome: len(ids_) for outcome, ids_ in sorted(skipped_ids_by_outcome.items())
    }
    n_skipped = sum(skipped_counts.values())
    duration_s = time.monotonic() - t_run0
    record = {
        "event": "hard_stop" if failed else "complete",
        "utc": _utcnow(),
        "collection": profile.name,
        "n_selected": n,
        "max_docs": max_docs,
        "scan_seconds": round(scan_s, 3),
        "duration_seconds": round(duration_s, 3),
        "completed_ids": completed,
        "skipped_counts": skipped_counts,
        "skipped_ids_by_outcome": skipped_ids_by_outcome,
        "failed_ids": failed,
        "tokens_total": tokens_total,
        "error": hard_stop_exc,
    }
    path = _append_auto_run_log(log_dir, record)
    print("=" * 60)
    print("AUTO RUN COMPLETE" if not failed else "AUTO RUN HARD STOP")
    print(f"collection={profile.name}")
    print(
        f"completed={len(completed)} skipped={n_skipped} "
        f"skipped_counts={skipped_counts} failed={len(failed)} "
        f"tokens_total={tokens_total} duration_s={duration_s:.2f}"
    )
    print(f"log={path}")
    print("=" * 60)
    # Auto: structural, transient-after-retry, or config → 2 (not 1).
    return 2 if failed else 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--collection",
        default=DEFAULT_COLLECTION,
        choices=sorted(PROFILES.keys()),
        help=f"Firestore collection to backfill (default: {DEFAULT_COLLECTION})",
    )
    parser.add_argument(
        "--out-dir",
        default=None,
        help="Working dir for manifest.json / checkpoint.json (required except --auto)",
    )
    parser.add_argument("--pin", action="store_true", help="Census + write pinned manifest")
    parser.add_argument("--dry-run", action="store_true", help="Plan only; no API, no writes")
    parser.add_argument(
        "--pilot",
        type=int,
        default=0,
        metavar="N",
        help="Embed first N pending IDs from manifest (writes); episodes: prefer 5",
    )
    parser.add_argument("--run", action="store_true", help="Embed all remaining pending IDs")
    parser.add_argument(
        "--auto",
        action="store_true",
        help="Unattended gap fill (live census; no manifest/pin/checkpoint)",
    )
    parser.add_argument(
        "--max-docs",
        type=int,
        default=DEFAULT_MAX_DOCS,
        help=f"--auto refuse threshold (default {DEFAULT_MAX_DOCS}); exit 3 if over",
    )
    parser.add_argument(
        "--log-dir",
        default=DEFAULT_LOG_DIR,
        help=f"--auto dated JSONL directory (default {DEFAULT_LOG_DIR})",
    )
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
            bool(args.auto),
        ]
    )
    if modes != 1:
        print(
            "ERROR: choose exactly one of "
            "--pin | --dry-run | --pilot N | --run | --auto",
            file=sys.stderr,
        )
        return 2

    profile = PROFILES[args.collection]
    db = _client()

    if args.auto:
        log_dir = Path(args.log_dir).expanduser().resolve()
        return run_auto(
            db,
            profile,
            max_docs=max(1, int(args.max_docs)),
            log_dir=log_dir,
            sleep_s=max(0.0, float(args.sleep)),
        )

    if not args.out_dir:
        print(
            "ERROR: --out-dir is required for --pin | --dry-run | --pilot | --run",
            file=sys.stderr,
        )
        return 2

    out_dir = Path(args.out_dir).expanduser().resolve()

    if args.pin:
        return pin_unembedded(db, out_dir, profile)

    try:
        manifest = load_manifest(out_dir)
    except Exception as exc:
        print(f"HARD STOP: {_safe_exc(exc)}", file=sys.stderr)
        return 2

    man_coll = str(manifest.get("collection") or DEFAULT_COLLECTION)
    if man_coll != profile.name:
        print(
            f"HARD STOP: --collection={profile.name!r} but manifest collection="
            f"{man_coll!r} (re-pin or pass matching --collection)",
            file=sys.stderr,
        )
        return 2

    print(
        f"Manifest n={manifest['n']} collection={man_coll} "
        f"pinned_at={manifest.get('pinned_at_utc')} "
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
    except StructuralError as exc:
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
            profile,
            manifest_pinned_at_utc=pin_at,
            write=False,
            batch_size=max(1, int(args.batch_size)),
            sleep_s=0.0,
        )

    client, key_rc = _openai_client_or_exit()
    if key_rc != 0:
        return key_rc

    return process_ids(
        db,
        client,
        out_dir,
        work,
        queue,
        profile,
        manifest_pinned_at_utc=pin_at,
        write=True,
        batch_size=max(1, int(args.batch_size)),
        sleep_s=max(0.0, float(args.sleep)),
    )


if __name__ == "__main__":
    raise SystemExit(main())

