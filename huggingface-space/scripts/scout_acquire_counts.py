"""Per-source, per-session scout counts for the status file and the alarm.

The daily logs already print `SCOUT_STATS fetched=N new_json=M`. This module
reads those lines. It does not look at exit codes. A session with no log counts
as fetched 0 and new 0: that is how a scout that never started stays visible.

Times are America/New_York. Morning sessions count once the clock is at or
after 10:30 (the arXiv morning scout starts at 10:25). Evening sessions count
once the clock is at or after 20:15 (the arXiv evening scout starts at 20:10).
"""

from __future__ import annotations

import re
from datetime import date, datetime, time, timedelta
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple
from zoneinfo import ZoneInfo

NEW_YORK = ZoneInfo("America/New_York")
SOURCES: Tuple[str, ...] = ("pubmed", "biorxiv", "arxiv")
SOURCE_LABEL = {"pubmed": "PubMed", "biorxiv": "bioRxiv", "arxiv": "arXiv"}
AM_DUE = time(10, 30)
PM_DUE = time(20, 15)
FETCH_ZERO_STREAK = 3
NEW_ZERO_SESSIONS = 14  # 7 days, morning and evening
STATUS_STALE_HOURS = 18
STATUS_URL = (
    "https://storage.googleapis.com/regal-scholar-453620-r7-podcast-storage/"
    "knowledge-engine-status.json"
)
STATS_RE = re.compile(r"SCOUT_STATS fetched=(\d+) new_json=(\d+)")
Slot = Tuple[date, str]


def now_eastern(now: Optional[datetime] = None) -> datetime:
    if now is None:
        return datetime.now(NEW_YORK)
    if now.tzinfo is None:
        return now.replace(tzinfo=NEW_YORK)
    return now.astimezone(NEW_YORK)


def recent_completed(now: datetime, n: int) -> List[Slot]:
    """The n most recently due sessions, newest first."""
    if n <= 0:
        return []
    local = now_eastern(now)
    ordered: List[Slot] = []
    day = local.date()
    if local.time() >= PM_DUE:
        ordered.append((day, "pm"))
    if local.time() >= AM_DUE:
        ordered.append((day, "am"))
    day = day - timedelta(days=1)
    while len(ordered) < n:
        ordered.append((day, "pm"))
        if len(ordered) >= n:
            break
        ordered.append((day, "am"))
        day = day - timedelta(days=1)
    return ordered[:n]


def parse_session_log(path: Path) -> Tuple[int, int, bool]:
    """Return (fetched, new, had_stats). Several SCOUT_STATS lines are summed."""
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return 0, 0, False
    matches = STATS_RE.findall(text)
    if not matches:
        return 0, 0, False
    fetched = sum(int(item[0]) for item in matches)
    new = sum(int(item[1]) for item in matches)
    return fetched, new, True


def collect_sessions(log_dir: Path, now: Optional[datetime] = None, sessions: int = NEW_ZERO_SESSIONS) -> List[Dict[str, Any]]:
    """One record per source per due session, oldest first."""
    when = now_eastern(now)
    slots = list(reversed(recent_completed(when, sessions)))
    records: List[Dict[str, Any]] = []
    for day, slot in slots:
        for source in SOURCES:
            path = log_dir / f"{source}_{slot}_{day.strftime('%Y%m%d')}.log"
            if not path.is_file():
                records.append({
                    "source": source,
                    "date": day.isoformat(),
                    "slot": slot,
                    "fetched": 0,
                    "new": 0,
                    "missing": True,
                })
                continue
            fetched, new, had_stats = parse_session_log(path)
            records.append({
                "source": source,
                "date": day.isoformat(),
                "slot": slot,
                "fetched": fetched,
                "new": new,
                "missing": not had_stats,
            })
    return records


def status_age_hours(status: Dict[str, Any], now: datetime) -> Optional[float]:
    """Hours since last_updated. None when the timestamp is missing or unreadable.

    A naive timestamp is Eastern local time, which is how the publisher writes it.
    """
    raw = status.get("last_updated") if isinstance(status, dict) else None
    if not isinstance(raw, str) or not raw.strip():
        return None
    try:
        stamp = datetime.fromisoformat(raw)
    except ValueError:
        return None
    if stamp.tzinfo is None:
        stamp = stamp.replace(tzinfo=NEW_YORK)
    delta = now_eastern(now) - stamp.astimezone(NEW_YORK)
    return delta.total_seconds() / 3600.0


def _index(sessions: Iterable[Dict[str, Any]]) -> Dict[Tuple[str, str, str], Dict[str, Any]]:
    out = {}
    for row in sessions:
        if not isinstance(row, dict):
            continue
        key = (str(row.get("source")), str(row.get("date")), str(row.get("slot")))
        out[key] = row
    return out


def _count(row: Optional[Dict[str, Any]], field: str) -> int:
    if not row:
        return 0
    try:
        return int(row.get(field) or 0)
    except (TypeError, ValueError):
        return 0


def scout_problems(status: Dict[str, Any], now: datetime) -> List[Dict[str, str]]:
    """Problems worth one GitHub issue each. Empty when the scout block is absent.

    (a) newest 3 due sessions fetched 0.
    (b) newest 14 due sessions (7 days) saved 0 new.
    (c) is not decided here; the status file cannot call itself stale at the
    moment it is written. The alarm script adds (c) from the file's age.
    """
    scout = status.get("scout") if isinstance(status, dict) else None
    rows = scout.get("sessions") if isinstance(scout, dict) else None
    if not isinstance(rows, list):
        return []
    index = _index(rows)
    expected = recent_completed(now, NEW_ZERO_SESSIONS)
    found: List[Dict[str, str]] = []
    for source in SOURCES:
        label = SOURCE_LABEL[source]
        newest = expected[:FETCH_ZERO_STREAK]
        if len(newest) >= FETCH_ZERO_STREAK and all(
            _count(index.get((source, day.isoformat(), slot)), "fetched") == 0
            for day, slot in newest
        ):
            found.append({
                "key": f"{source}-fetched-zero",
                "sentence": f"{label} fetched no papers for 3 sessions in a row.",
                "detail": _session_lines(index, source, newest),
            })
        if len(expected) >= NEW_ZERO_SESSIONS and all(
            _count(index.get((source, day.isoformat(), slot)), "new") == 0
            for day, slot in expected
        ):
            found.append({
                "key": f"{source}-no-new-7d",
                "sentence": f"{label} saved no new papers for 7 days.",
                "detail": _session_lines(index, source, expected),
            })
    return found


def stale_problem(status: Dict[str, Any], now: datetime) -> Optional[Dict[str, str]]:
    age = status_age_hours(status, now)
    if age is not None and age <= STATUS_STALE_HOURS:
        return None
    if age is None:
        sentence = "The knowledge-engine status has no readable timestamp."
        detail = "last_updated was missing or not a time."
    else:
        sentence = "The knowledge-engine status is more than 18 hours old."
        detail = f"Age at check: {age:.1f} hours."
    return {"key": "status-stale", "sentence": sentence, "detail": detail}


def alarm_problems(status: Dict[str, Any], now: datetime) -> List[Dict[str, str]]:
    found = list(scout_problems(status, now))
    stale = stale_problem(status, now)
    if stale:
        found.append(stale)
    return found


def notice_text(problems: Sequence[Dict[str, str]]) -> str:
    return " ".join(item["sentence"] for item in problems if item.get("sentence"))


def _session_lines(index: Dict[Tuple[str, str, str], Dict[str, Any]], source: str, slots: Sequence[Slot]) -> str:
    lines = []
    for day, slot in slots:
        row = index.get((source, day.isoformat(), slot))
        if row is None:
            lines.append(f"- {day.isoformat()} {slot}: no record (counted as fetched 0, new 0)")
            continue
        missing = " missing-log" if row.get("missing") else ""
        lines.append(
            f"- {day.isoformat()} {slot}: fetched={_count(row, 'fetched')} "
            f"new={_count(row, 'new')}{missing}"
        )
    return "\n".join(lines)
