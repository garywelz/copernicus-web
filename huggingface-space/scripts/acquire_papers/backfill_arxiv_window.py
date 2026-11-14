#!/usr/bin/env python3
"""One-off arXiv backfill for a fixed window of submission dates (governance/BULLETIN.md entry 045).

WHY: the arXiv scout acquired nothing from 2026-10-18 until its date range was fixed. The scout only ever takes the
newest papers of each session (150, shared between its queries), so after a gap of weeks the regular runs keep
fetching the same newest papers and never reach the older ones. This script fetches EVERYTHING the scout's own
queries match in a window, once.

IT REUSES THE SCOUT, it does not reimplement it: the queries come from the scout's config (`arxiv_queries` in
daily_scout_config.json), and the query string, the search, the paging, the parsing and the saving are the scout's own
functions in acquire_arxiv_batch.py (build_arxiv_query, search_arxiv, fetch_arxiv_papers, parse_arxiv_entry through
fetch, save_papers). Only the window is different: --from and --to instead of "the last N days".

RUN ATTENDED, ONLY ON GARY'S APPROVAL. It must be told what to do; with no mode it refuses:
  --count-only   one request per query: how many papers arXiv has in the window. Writes nothing.
  --dry-run      fetches every page and reports, per query and in total, how many papers there are, how many are
                 already on disk and how many would be new. Writes nothing.
  --write        the same, then saves the NEW papers as JSON files in the scout's papers directory. A paper already on
                 disk is never rewritten. Nothing here touches Firestore: the next scheduled ingest reads the new files
                 (through its stub gate) exactly as it reads the scout's.

NO CAP ON THE NUMBER OF PAPERS (Gary, 2026-11-14: decide after the dry run shows the real count). The one limit is a
safety ceiling per query (--ceiling, default 10000): a query that matches more than that is REFUSED, never cut short.

EXIT CODES: 0 done; 1 a query failed, came back incomplete, or was over the ceiling (what was fetched is reported, and
in --write mode the new papers that were fetched are saved: a re-run skips them); 2 usage.

Usage:
  python3 backfill_arxiv_window.py --from 2026-10-18 --to 2026-11-14 --dry-run
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import sys
import time
from datetime import date, datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

HERE = Path(__file__).resolve().parent
DEFAULT_CONFIG = HERE / "daily_scout_config.json"
DEFAULT_CEILING = 10000


def load_scout():
    """The scout module itself (acquire_arxiv_batch.py, next to this file)."""
    spec = importlib.util.spec_from_file_location("acquire_arxiv_batch", HERE / "acquire_arxiv_batch.py")
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    sys.modules.setdefault("acquire_arxiv_batch", mod)
    spec.loader.exec_module(mod)
    return mod


def parse_day(text: str) -> date:
    return datetime.strptime(text, "%Y-%m-%d").date()


def load_queries(config_path: Path) -> List[Dict[str, Any]]:
    """The scout's own `arxiv_queries` (name, categories, optional keyword_filter). Its days_back and share are not used here."""
    data = json.loads(config_path.read_text(encoding="utf-8"))
    queries = data.get("arxiv_queries") if isinstance(data, dict) else data
    if not isinstance(queries, list) or not queries or not all(isinstance(q, dict) and q.get("categories") for q in queries):
        raise ValueError(f"{config_path}: no usable arxiv_queries")
    return queries


def window_query(scout, qdef: Dict[str, Any], start: date, end: date) -> str:
    """The scout's query for this definition, with the window [start 00:00, end 23:59] in place of 'the last N days'."""
    return scout.build_arxiv_query(list(qdef["categories"]), (end - start).days, qdef.get("keyword_filter"), today=end)


def on_disk(output_dir: Path, arxiv_id: str) -> bool:
    """True if the scout (or an earlier run of this script) already saved this paper, under any discipline directory."""
    name = f"arxiv_{arxiv_id}.json"
    return any((d / name).exists() for d in output_dir.iterdir() if d.is_dir()) if output_dir.exists() else False


def run(scout, queries: List[Dict[str, Any]], start: date, end: date, mode: str, output_dir: Path, ceiling: int, out=print) -> Tuple[int, Dict[str, int]]:
    totals = {"queries": 0, "failed": 0, "incomplete": 0, "over_ceiling": 0, "matched": 0, "fetched": 0, "duplicates": 0, "on_disk": 0, "new": 0, "saved": 0}
    seen, to_save = set(), []
    out(f"arXiv backfill {start.isoformat()} to {end.isoformat()}  mode={mode}  papers dir={output_dir}")
    for n, qdef in enumerate(queries):
        if n:
            time.sleep(scout.DELAY_BETWEEN_QUERIES)
        name, query = qdef.get("name", f"query {n + 1}"), window_query(scout, qdef, start, end)
        totals["queries"] += 1
        out(f"\n[{name}]\n  {query}")
        first = scout.search_arxiv(query, 1, sort_by="submittedDate", sort_order="descending")
        if not first.get("ok"):
            totals["failed"] += 1
            out(f"  FAILED ({first.get('error_kind', 'other')}): the count could not be read; nothing is concluded about this query")
            continue
        matched = int(first.get("total") or 0)
        totals["matched"] += matched
        out(f"  arXiv has {matched} papers in the window")
        if mode == "count-only" or matched == 0:
            continue
        if matched > ceiling:
            totals["over_ceiling"] += 1
            out(f"  REFUSED: more than the safety ceiling of {ceiling}; nothing was fetched for this query (it is never cut short)")
            continue
        time.sleep(scout.DELAY_BETWEEN_QUERIES)
        papers, error = scout.fetch_arxiv_papers(query, matched, sort_by="submittedDate", sort_order="descending")
        if error is not None:
            totals["failed"] += 1
            out(f"  FAILED ({error.get('error_kind', 'other')}) while fetching; nothing is concluded about this query")
            continue
        fetched = [p for p in papers if p.get("arxiv_id")]
        totals["fetched"] += len(fetched)
        if len(fetched) < matched:
            totals["incomplete"] += 1
            out(f"  INCOMPLETE: fetched {len(fetched)} of {matched}; a re-run picks up the rest")
        dup = disk = new = 0
        for p in fetched:
            if p["arxiv_id"] in seen:
                dup += 1
            elif on_disk(output_dir, p["arxiv_id"]):
                seen.add(p["arxiv_id"])
                disk += 1
            else:
                seen.add(p["arxiv_id"])
                new += 1
                to_save.append(p)
        totals["duplicates"] += dup
        totals["on_disk"] += disk
        totals["new"] += new
        out(f"  fetched {len(fetched)}: {new} new, {disk} already on disk, {dup} already counted under an earlier query")
    if mode == "write" and to_save:
        stats = scout.save_papers(to_save, output_dir, "arxiv")
        totals["saved"] = int(stats.get("saved", 0))
        if stats.get("updated_files"):
            out(f"  WARNING: {stats['updated_files']} file(s) existed by the time of saving and were rewritten")
    out("\n" + ("WROTE" if mode == "write" else "DRY RUN: nothing was written" if mode == "dry-run" else "COUNT ONLY: nothing was fetched or written"))
    out("BACKFILL_STATS " + " ".join(f"{k}={v}" for k, v in totals.items()))
    problems = totals["failed"] + totals["incomplete"] + totals["over_ceiling"]
    if problems:
        out(f"NOT COMPLETE: {totals['failed']} failed, {totals['incomplete']} incomplete, {totals['over_ceiling']} over the ceiling")
    return (1 if problems else 0), totals


def main(argv: Optional[List[str]] = None, scout=None, today: Optional[date] = None, out=print) -> int:
    ap = argparse.ArgumentParser(description="One-off arXiv backfill for a window of submission dates (attended, on approval).")
    ap.add_argument("--from", dest="start", required=True, help="first day of the window, YYYY-MM-DD")
    ap.add_argument("--to", dest="end", required=True, help="last day of the window, YYYY-MM-DD")
    ap.add_argument("--count-only", action="store_true", help="one request per query: the number of papers; writes nothing")
    ap.add_argument("--dry-run", action="store_true", help="fetch and report what would be new; writes nothing")
    ap.add_argument("--write", action="store_true", help="save the new papers as JSON files (never rewrites a paper on disk)")
    ap.add_argument("--config", default=str(DEFAULT_CONFIG), help="the scout's config with arxiv_queries")
    ap.add_argument("--output-dir", default=None, help="papers directory (default: the scout's own)")
    ap.add_argument("--ceiling", type=int, default=DEFAULT_CEILING, help="safety ceiling per query; a query over it is refused, never cut")
    try:
        args = ap.parse_args(argv)
    except SystemExit as e:
        return 2 if e.code else 0
    modes = [m for m, on in (("count-only", args.count_only), ("dry-run", args.dry_run), ("write", args.write)) if on]
    if len(modes) != 1:
        print("ERROR: choose exactly one of --count-only, --dry-run, --write", file=sys.stderr)
        return 2
    try:
        start, end = parse_day(args.start), parse_day(args.end)
    except ValueError:
        print("ERROR: --from and --to are dates written YYYY-MM-DD", file=sys.stderr)
        return 2
    today = today or date.today()
    if start > end or end > today or args.ceiling < 1:
        print("ERROR: --from must not be after --to, --to must not be in the future, and --ceiling must be at least 1", file=sys.stderr)
        return 2
    try:
        queries = load_queries(Path(args.config))
    except (OSError, ValueError) as e:
        print(f"ERROR: {e}", file=sys.stderr)
        return 2
    scout = scout or load_scout()
    output_dir = Path(args.output_dir) if args.output_dir else Path(scout.OUTPUT_DIR)
    rc, _ = run(scout, queries, start, end, modes[0], output_dir, args.ceiling, out=out)
    return rc


if __name__ == "__main__":
    for _stream in (sys.stdout, sys.stderr):
        if hasattr(_stream, "reconfigure"):
            _stream.reconfigure(encoding="utf-8", errors="backslashreplace")
    sys.exit(main())
