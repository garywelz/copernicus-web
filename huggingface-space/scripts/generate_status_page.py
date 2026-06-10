#!/usr/bin/env python3
"""
Generate Knowledge Engine status JSON (and print summary).

Modes:
  --source api (default)  Use Cloud Run content API totals (matches papers-database-table / live KE).
  --source local          Count JSON files under huggingface-space (offline; can diverge from Firestore).

Videos: not in /api/content/browse. Set KSTATUS_VIDEO_COUNT or pass --videos N.
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


def _fetch_browse_total(api_base: str, content_type: str) -> int:
    url = f"{api_base.rstrip('/')}/api/content/browse?content_type={content_type}&page=1&limit=1"
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


def _fetch_content_stats(api_base: str) -> Optional[Dict[str, Any]]:
    """
    /api/content/stats: papers with embedding (embedding_model set in Firestore).
    """
    url = f"{api_base.rstrip('/')}/api/content/stats"
    req = Request(url, headers={"Accept": "application/json"})
    ctx = ssl.create_default_context()
    with urlopen(req, timeout=90, context=ctx) as resp:
        return json.loads(resp.read().decode("utf-8"))


def count_local() -> Dict[str, int]:
    papers = len(list((BASE_DIR / "metadata-database" / "papers").rglob("*.json")))
    processes = len(
        [
            f
            for f in BASE_DIR.glob("*-processes-database/processes/**/*.json")
            if not f.name.endswith(".backup")
        ]
    )
    return {
        "papers": papers,
        "processes": processes,
        "videos": int(os.environ.get("KSTATUS_VIDEO_COUNT", "753")),
        "podcasts": int(os.environ.get("KSTATUS_PODCAST_COUNT", "79")),
    }


def count_api(api_base: str) -> Dict[str, int]:
    papers = _fetch_browse_total(api_base, "papers")
    podcasts = _fetch_browse_total(api_base, "podcasts")
    processes = _fetch_browse_total(api_base, "processes")
    videos = int(os.environ.get("KSTATUS_VIDEO_COUNT", "753"))
    return {
        "papers": papers,
        "processes": processes,
        "videos": videos,
        "podcasts": podcasts,
    }


def build_status(
    counts: Dict[str, int],
    source: str,
    content_stats: Optional[Dict[str, Any]] = None,
    process_databases: Optional[Dict[str, int]] = None,
    process_databases_error: Optional[str] = None,
) -> Dict[str, Any]:
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
            "videos": "Not exposed on browse; use KSTATUS_VIDEO_COUNT or --videos until a videos count endpoint exists.",
        },
    }
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
        counts = count_local()
    else:
        try:
            counts = count_api(args.api_base)
        except (HTTPError, URLError, json.JSONDecodeError, TimeoutError, OSError) as e:
            print(f"❌ API mode failed ({e}); falling back to local file counts.")
            counts = count_local()
            source_label = "local_fallback"
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

    status = build_status(
        counts,
        source_label,
        content_stats=content_stats,
        process_databases=process_databases,
        process_databases_error=process_databases_error,
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
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
