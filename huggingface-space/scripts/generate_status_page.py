#!/usr/bin/env python3
"""
Generate Knowledge Engine status JSON (and print summary).

Modes:
  --source api (default)  Use Cloud Run content API totals (matches papers-database-table / live KE).
  --source local          Count JSON files under huggingface-space (offline; can diverge from Firestore).

Videos: prefer /api/content/browse?content_type=videos, then videos-metadata.json
`totalVideos`. Override with KSTATUS_VIDEO_COUNT or --videos N.
"""

from __future__ import annotations

import argparse
import json
import os
import ssl
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

DEFAULT_API = "https://copernicus-podcast-api-phzp4ie2sq-uc.a.run.app"
# Public `metadata.json` for each programming-framework process family (GCS; same as database HTML tables).
GCS_STATUS_BASE = "https://storage.googleapis.com/regal-scholar-453620-r7-podcast-storage"
VIDEOS_METADATA_URL = f"{GCS_STATUS_BASE}/videos-metadata.json"
# Last-known-good value, used only if the live fetch fails AND no override is
# set. This is a fallback of last resort, not a source of truth -- it will go
# stale again if left here long enough, same as the "753" it replaces did.
VIDEOS_COUNT_FALLBACK = 582
# Last-known-good discipline paper counts (public browse API,
# verified 2026-08-14), used only if both the API and a direct Firestore
# query fail. 29,184/17,153 were the 2026-08-03 figures; leaving those
# in place would republish the exact stale number the glmp Space page
# currently falls back to.
DISCIPLINE_PAPERS_FALLBACK = {
    "biology": 80138,
    "mathematics": 18321,
}
PROCESS_DATABASE_METADATA: tuple[tuple[str, str], ...] = (
    ("glmp_v2", f"{GCS_STATUS_BASE}/glmp-v2/metadata.json"),
    ("mathematics", f"{GCS_STATUS_BASE}/mathematics-processes-database/metadata.json"),
    ("biology", f"{GCS_STATUS_BASE}/biology-processes-database/metadata.json"),
    ("chemistry", f"{GCS_STATUS_BASE}/chemistry-processes-database/metadata.json"),
    ("physics", f"{GCS_STATUS_BASE}/physics-processes-database/metadata.json"),
    ("computer_science", f"{GCS_STATUS_BASE}/computer-science-processes-database/metadata.json"),
)
BASE_DIR = Path(__file__).resolve().parent.parent
DEFAULT_OUT = BASE_DIR / "knowledge-engine-status.json"

TARGETS = {
    "papers": 100_000,
    "processes": 1_000,  # PF process charts (GCS sum); ramp over coming months
    "videos": 2_000,
    "podcasts": 500,
}


def _fetch_browse_total(
    api_base: str, content_type: str, discipline: Optional[str] = None
) -> int:
    url = (
        f"{api_base.rstrip('/')}/api/content/browse"
        f"?content_type={content_type}&page=1&limit=1"
    )
    if discipline:
        url += f"&discipline={discipline}"
    req = Request(url, headers={"Accept": "application/json"})
    ctx = ssl.create_default_context()
    with urlopen(req, timeout=60, context=ctx) as resp:
        data = json.loads(resp.read().decode("utf-8"))
    pag = data.get("pagination") or {}
    return int(pag.get("total") or 0)


def _fetch_json_url(url: str) -> Any:
    req = Request(url, headers={"Accept": "application/json"})
    ctx = ssl.create_default_context()
    with urlopen(req, timeout=90, context=ctx) as resp:
        return json.loads(resp.read().decode("utf-8"))


def _count_from_process_metadata(data: Any) -> Optional[int]:
    """
    Public metadata.json files use `totalProcesses` and/or a `processes` array
    (shape varies slightly by family).
    """
    if not isinstance(data, dict):
        return None
    if "totalProcesses" in data and data["totalProcesses"] is not None:
        try:
            return int(data["totalProcesses"])
        except (TypeError, ValueError):
            pass
    proc = data.get("processes")
    if isinstance(proc, list):
        return len(proc)
    return None


def fetch_process_databases_gcs() -> tuple[Optional[Dict[str, int]], Optional[str]]:
    """
    Sum of process counts from each public metadata.json (GLMP v2 + five discipline DBs).
    Independent of Firestore `glmp_processes` (which can include dupes and non-catalog docs).
    """
    per: Dict[str, int] = {}
    errors: list[str] = []
    for key, url in PROCESS_DATABASE_METADATA:
        try:
            data = _fetch_json_url(url)
            n = _count_from_process_metadata(data)
            if n is None:
                errors.append(f"{key}: unparseable shape")
                continue
            per[key] = n
        except (HTTPError, URLError, json.JSONDecodeError, TimeoutError, OSError, TypeError) as e:
            errors.append(f"{key}: {e!s}")
    if not per:
        return None, "; ".join(errors) if errors else "no data"
    per["sum"] = sum(v for k, v in per.items() if k != "sum")
    if errors:
        return per, "partial: " + "; ".join(errors)
    return per, None


def _resolve_video_count(api_base: Optional[str] = None) -> tuple[int, Optional[str]]:
    """
    Video count, in priority order: explicit override (env/--videos) >
    live browse API total > videos-metadata.json totalVideos > fallback.
    """
    override = os.environ.get("KSTATUS_VIDEO_COUNT")
    if override is not None:
        return int(override), f"KSTATUS_VIDEO_COUNT override ({override}), live fetch not attempted."
    if api_base:
        try:
            total = _fetch_browse_total(api_base, "videos")
            if total > 0:
                return total, None
        except (HTTPError, URLError, TimeoutError, ValueError, OSError, json.JSONDecodeError) as exc:
            browse_err = f"browse videos failed ({exc})"
        else:
            browse_err = "browse videos returned 0"
    else:
        browse_err = None
    try:
        data = _fetch_json_url(VIDEOS_METADATA_URL)
        total = data.get("totalVideos")
        if isinstance(total, int):
            note = f"{browse_err}; used videos-metadata.json." if browse_err else None
            return total, note
        return VIDEOS_COUNT_FALLBACK, (
            f"{browse_err + '; ' if browse_err else ''}"
            "videos-metadata.json fetched but had no totalVideos field; used fallback."
        )
    except (HTTPError, URLError, TimeoutError, ValueError, OSError) as exc:
        return VIDEOS_COUNT_FALLBACK, (
            f"{browse_err + '; ' if browse_err else ''}"
            f"videos-metadata.json fetch failed ({exc}); used fallback."
        )


def fetch_papers_by_discipline(
    api_base: str,
    disciplines: tuple[str, ...] = ("biology", "mathematics"),
) -> tuple[Dict[str, int], Optional[str]]:
    """
    Live count of research_papers per discipline.

    Prefer the public browse API (same path as paper totals) so this works
    from a cron venv that has no google-cloud-firestore. Fall back to a
    direct Firestore count, then to last-known-good values. Always returns
    a complete dict so the published JSON cannot silently omit the field
    the glmp Space page reads.
    """
    counts: Dict[str, int] = {}
    api_errors: list[str] = []
    for disc in disciplines:
        try:
            counts[disc] = _fetch_browse_total(api_base, "papers", discipline=disc)
        except (HTTPError, URLError, json.JSONDecodeError, TimeoutError, OSError, TypeError, ValueError) as e:
            api_errors.append(f"{disc}: {e!s}")
    if len(counts) == len(disciplines):
        return counts, None

    firestore_note: Optional[str] = None
    missing = [d for d in disciplines if d not in counts]
    try:
        from google.cloud import firestore
        from google.cloud.firestore_v1.base_query import FieldFilter
    except ImportError as e:
        firestore_note = f"google-cloud-firestore not importable ({e})"
    else:
        try:
            gcp_project_id = os.environ.get("GCP_PROJECT_ID", "regal-scholar-453620-r7")
            db = firestore.Client(project=gcp_project_id, database="copernicusai")
            for disc in missing:
                q = db.collection("research_papers").where(filter=FieldFilter("discipline", "==", disc))
                counts[disc] = int(q.count().get()[0][0].value)
            missing = [d for d in disciplines if d not in counts]
        except Exception as e:
            firestore_note = f"Firestore discipline count failed ({e})"

    used_fallback = []
    for disc in missing:
        counts[disc] = DISCIPLINE_PAPERS_FALLBACK[disc]
        used_fallback.append(disc)
    parts = []
    if api_errors:
        parts.append("browse API failed (" + "; ".join(api_errors) + ")")
    if firestore_note:
        parts.append(firestore_note)
    if used_fallback:
        parts.append(f"used fallback for {', '.join(used_fallback)}")
    return counts, "; ".join(parts) if parts else None


def fetch_focus_fallback_metric() -> Optional[Dict[str, Any]]:
    """
    RAG focus_id silent-fallback counter (item 42, GLMP_MASTER_TODO.md).
    rag_service.py writes system_metrics/rag_focus_fallback every time a
    Knowledge Map node click's focus_id fails to resolve against any known
    collection (item 34's fallback path). No public-API equivalent exists
    for this (it's an operational counter, not content), so this goes
    straight to Firestore -- lazy-imported so a cron venv without
    google-cloud-firestore degrades to omitting the field entirely rather
    than failing the whole status build.

    Unlike papers_by_discipline, there is no honest last-known-good
    fallback for an ever-incrementing counter -- a stale count would
    actively mislead about whether this is currently firing. On any
    failure this returns None and the field is simply omitted, same as
    content_stats' existing optional-field pattern in build_status().
    """
    try:
        from google.cloud import firestore
    except ImportError:
        return None
    try:
        gcp_project_id = os.environ.get("GCP_PROJECT_ID", "regal-scholar-453620-r7")
        db = firestore.Client(project=gcp_project_id, database="copernicusai")
        snap = db.collection("system_metrics").document("rag_focus_fallback").get()
        if not snap.exists:
            return {"count": 0, "last_fired_at": None, "last_focus_id": None}
        data = snap.to_dict() or {}
        last_fired = data.get("last_fired_at")
        return {
            "count": int(data.get("count", 0)),
            "last_fired_at": last_fired.isoformat() if hasattr(last_fired, "isoformat") else last_fired,
            "last_focus_id": data.get("last_focus_id"),
        }
    except Exception:
        return None


def _fetch_content_stats(api_base: str) -> Optional[Dict[str, Any]]:
    """
    /api/content/stats: papers with embedding (embedding_model set in Firestore).
    """
    url = f"{api_base.rstrip('/')}/api/content/stats"
    req = Request(url, headers={"Accept": "application/json"})
    ctx = ssl.create_default_context()
    with urlopen(req, timeout=90, context=ctx) as resp:
        return json.loads(resp.read().decode("utf-8"))


def count_local() -> tuple[Dict[str, int], Optional[str]]:
    papers = len(list((BASE_DIR / "metadata-database" / "papers").rglob("*.json")))
    processes = len(
        [
            f
            for f in BASE_DIR.glob("*-processes-database/processes/**/*.json")
            if not f.name.endswith(".backup")
        ]
    )
    videos, videos_note = _resolve_video_count()
    return {
        "papers": papers,
        "processes": processes,
        "videos": videos,
        "podcasts": int(os.environ.get("KSTATUS_PODCAST_COUNT", "79")),
    }, videos_note


def count_api(api_base: str) -> tuple[Dict[str, int], Optional[str]]:
    papers = _fetch_browse_total(api_base, "papers")
    podcasts = _fetch_browse_total(api_base, "podcasts")
    processes = _fetch_browse_total(api_base, "processes")
    videos, videos_note = _resolve_video_count(api_base)
    return {
        "papers": papers,
        "processes": processes,
        "videos": videos,
        "podcasts": podcasts,
    }, videos_note


def build_status(
    counts: Dict[str, int],
    source: str,
    content_stats: Optional[Dict[str, Any]] = None,
    process_databases: Optional[Dict[str, int]] = None,
    process_databases_error: Optional[str] = None,
    videos_note: Optional[str] = None,
    papers_by_discipline: Optional[Dict[str, int]] = None,
    papers_by_discipline_note: Optional[str] = None,
    focus_fallback: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    videos_doc = (
        "Live from Cloud Run /api/content/browse?content_type=videos, "
        f"then {VIDEOS_METADATA_URL} (`totalVideos`); override with "
        "KSTATUS_VIDEO_COUNT or --videos."
    )
    out: Dict[str, Any] = {
        "last_updated": datetime.now().isoformat(),
        "papers": counts["papers"],
        "processes": counts["processes"],
        "videos": counts["videos"],
        "podcasts": counts["podcasts"],
        "targets": TARGETS.copy(),
        "count_source": source,
        "notes": {
            "papers_processes_podcasts": "From Cloud Run /api/content/browse when count_source is api (Firestore-backed).",
            "videos": videos_doc if not videos_note else f"{videos_doc} {videos_note}",
        },
    }
    if papers_by_discipline is not None:
        out["papers_by_discipline"] = papers_by_discipline
        disc_doc = (
            "From Cloud Run /api/content/browse?discipline=… (same count "
            "aggregation as papers); Firestore count is the fallback."
        )
        out["notes"]["papers_by_discipline"] = (
            disc_doc if not papers_by_discipline_note else f"{disc_doc} {papers_by_discipline_note}"
        )
    if content_stats:
        pwe = content_stats.get("papers_with_embedding")
        if pwe is not None:
            out["papers_with_embedding"] = int(pwe)
        pct = content_stats.get("papers_embedding_coverage_percent")
        if pct is not None:
            out["papers_embedding_coverage_percent"] = float(pct)
        cm = content_stats.get("count_method")
        if cm:
            out["notes"]["papers_embeddings"] = str(cm)
        if content_stats.get("note"):
            out["notes"]["papers_embeddings_error"] = str(content_stats["note"])
    if process_databases is not None:
        out["process_databases"] = process_databases
        out["notes"]["process_databases"] = (
            "Per-family counts from public GCS metadata.json (GLMP v2 + math, bio, chem, physics, CS). "
            "Field `sum` is the total across families (no double-count; each family is separate). "
            "Counts exclude graph_type_pilots (JSON-canonical publish). "
            "This differs from `processes` from /api/content/browse, which is Firestore `glmp_processes` only."
        )
        out["notes"]["media_catalogs"] = (
            "JSON-canonical media: episodes-catalog.json (Firestore episodes) and "
            "videos-catalog.json (ScienceVideoDB / GCS videos-metadata.json)."
        )
        out["notes"]["firestore_process_collections"] = (
            "Vector search process collections: glmp_processes, math_processes, chemistry_processes, "
            "physics_processes, computer_science_processes, biology_processes."
        )
    if process_databases_error:
        out["notes"]["process_databases_error"] = process_databases_error
    if focus_fallback is not None:
        out["rag_focus_fallback"] = focus_fallback
        out["notes"]["rag_focus_fallback"] = (
            "Count of Knowledge Map node-explanation requests where focus_id "
            "did not resolve to any known document (rag_service.py "
            "_record_focus_fallback, item 42). A rising rate points at a "
            "frontend sending malformed IDs, a renamed process ID, or a new "
            "content collection not yet in _FOCUS_ID_COLLECTIONS."
        )
    out["notes"]["firestore_glmp_vs_glmp_v2_table"] = (
        "`processes` = Firestore collection glmp_processes (document count). The GLMP summary table at "
        "glmp-database-table.html uses glmp-v2/metadata.json (`totalProcesses`, typically 108). The gap to "
        "115 is not extra biology charts in math/CS DBs: it is duplicate Bacillus document IDs, two E. coli "
        "variant IDs, and a stray `metadata` document. Normalize IDs by stripping a leading "
        "ecoli-/yeast-/bacillus- prefix to compare to metadata."
    )
    return out


def main() -> int:
    p = argparse.ArgumentParser(description="Generate knowledge-engine-status.json")
    p.add_argument(
        "--source",
        choices=("api", "local"),
        default="api",
        help="api = live Firestore totals via public API (default). local = count files on disk.",
    )
    p.add_argument(
        "--api-base",
        default=os.environ.get("COPERNICUS_API_BASE", DEFAULT_API),
        help="Cloud Run API base URL",
    )
    p.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_OUT,
        help="Output JSON path",
    )
    p.add_argument(
        "--videos",
        type=int,
        default=None,
        help="Override video count in output (stored in env for child logic if we pass)",
    )
    p.add_argument(
        "--no-process-metadata",
        action="store_true",
        help="Do not fetch GCS metadata.json for per-family process database sums.",
    )
    args = p.parse_args()

    if args.videos is not None:
        os.environ["KSTATUS_VIDEO_COUNT"] = str(args.videos)

    source_label = args.source
    content_stats: Optional[Dict[str, Any]] = None
    if args.source == "local":
        counts, videos_note = count_local()
    else:
        try:
            counts, videos_note = count_api(args.api_base)
        except (HTTPError, URLError, json.JSONDecodeError, TimeoutError, OSError) as e:
            print(f"❌ API mode failed ({e}); falling back to local file counts.")
            counts, videos_note = count_local()
            source_label = "local_fallback"
    if videos_note:
        print(f"⚠️  videos count: {videos_note}")
    if args.source == "api":
        try:
            content_stats = _fetch_content_stats(args.api_base)
        except (HTTPError, URLError, json.JSONDecodeError, TimeoutError, OSError) as e:
            print(f"⚠️  /api/content/stats failed ({e}); status JSON will omit embedding counts until available.")

    process_databases: Optional[Dict[str, int]] = None
    process_databases_error: Optional[str] = None
    if not args.no_process_metadata:
        try:
            process_databases, process_databases_error = fetch_process_databases_gcs()
        except Exception as e:  # defensive; fetch_process_databases_gcs should not throw
            process_databases_error = str(e)
        if process_databases_error:
            print(f"⚠️  GCS process metadata: {process_databases_error}")

    papers_by_discipline, papers_by_discipline_note = fetch_papers_by_discipline(args.api_base)
    if papers_by_discipline_note:
        print(f"⚠️  papers_by_discipline: {papers_by_discipline_note}")

    focus_fallback = fetch_focus_fallback_metric()
    if focus_fallback is None:
        print("⚠️  rag_focus_fallback: Firestore read failed or unavailable; status JSON will omit it.")

    status = build_status(
        counts,
        source_label,
        content_stats=content_stats,
        process_databases=process_databases,
        process_databases_error=process_databases_error,
        videos_note=videos_note,
        papers_by_discipline=papers_by_discipline,
        papers_by_discipline_note=papers_by_discipline_note,
        focus_fallback=focus_fallback,
    )
    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    with open(out, "w", encoding="utf-8") as f:
        json.dump(status, f, indent=2)

    print(f"✅ {out}")
    print(f"   source: {source_label}")
    for k in ("papers", "processes", "videos", "podcasts"):
        print(f"   {k}: {counts[k]:,}")
    if content_stats and content_stats.get("papers_with_embedding") is not None:
        print(
            f"   papers_with_embedding: {int(content_stats['papers_with_embedding']):,} "
            f"({content_stats.get('papers_embedding_coverage_percent', '?')}% of total)"
        )
    if process_databases and "sum" in process_databases:
        print(f"   process_databases (GCS sum): {process_databases['sum']:,} " f"(see JSON for per-family breakdown)")
    if papers_by_discipline:
        parts = ", ".join(f"{k}={v:,}" for k, v in papers_by_discipline.items())
        print(f"   papers_by_discipline: {parts}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
