"""Scout alarm: counts from what was acquired, and one open issue per problem."""

from __future__ import annotations

import importlib.util
import sys
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

SCRIPTS = Path(__file__).resolve().parents[1]
NY = ZoneInfo("America/New_York")


def _load(name: str, filename: str):
    spec = importlib.util.spec_from_file_location(name, SCRIPTS / filename)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


counts = _load("scout_acquire_counts_test", "scout_acquire_counts.py")
alarm = _load("scout_alarm_test", "scout_alarm.py")


def _at(hour: int, minute: int, day: int = 17) -> datetime:
    return datetime(2026, 11, day, hour, minute, tzinfo=NY)


def _sessions(slots, fetched=10, new=1):
    """A full grid: every source, every slot. Tests then edit one source."""
    rows = []
    for source in counts.SOURCES:
        for day, slot in slots:
            rows.append({
                "source": source,
                "date": day.isoformat(),
                "slot": slot,
                "fetched": fetched,
                "new": new,
                "missing": False,
            })
    return rows


def _pubmed(rows):
    return [row for row in rows if row["source"] == "pubmed"]


def _status(sessions, last_updated="2026-11-17T12:40:00"):
    return {"last_updated": last_updated, "scout": {"sessions": sessions}}


def test_morning_check_expects_todays_am_and_not_todays_pm():
    slots = counts.recent_completed(_at(12, 45), 3)
    assert [(day.isoformat(), slot) for day, slot in slots] == [
        ("2026-11-17", "am"),
        ("2026-11-16", "pm"),
        ("2026-11-16", "am"),
    ]
    evening = counts.recent_completed(_at(22, 45), 2)
    assert [(day.isoformat(), slot) for day, slot in evening] == [
        ("2026-11-17", "pm"),
        ("2026-11-17", "am"),
    ]
    before_scout = counts.recent_completed(_at(10, 0), 1)
    assert before_scout == [(datetime(2026, 11, 16).date(), "pm")]


def test_a_log_with_two_stats_lines_sums_the_main_job_and_the_supplement(tmp_path):
    path = tmp_path / "pubmed_am_20261117.log"
    path.write_text(
        "SCOUT_STATS fetched=500 new_json=40 updated_json=460\n"
        "SCOUT_STATS fetched=12 new_json=2 updated_json=10\n",
        encoding="utf-8",
    )
    assert counts.parse_session_log(path) == (512, 42, True)
    missing = counts.parse_session_log(tmp_path / "nope.log")
    assert missing == (0, 0, False)


def test_three_zero_fetches_alarm_and_a_recovery_clears_it():
    now = _at(12, 45)
    slots = counts.recent_completed(now, 14)
    rows = _sessions(slots, fetched=10, new=1)
    pubmed = _pubmed(rows)
    # Newest session fetched nothing. The two before it did not. No streak yet.
    pubmed[0]["fetched"] = 0
    assert counts.scout_problems(_status(rows), now) == []
    for row in pubmed[:3]:
        row["fetched"] = 0
    problems = counts.scout_problems(_status(rows), now)
    assert [item["key"] for item in problems] == ["pubmed-fetched-zero"]
    assert problems[0]["sentence"] == "PubMed fetched no papers for 3 sessions in a row."


def test_seven_days_with_no_new_papers_alarms_and_one_new_paper_clears_it():
    now = _at(22, 45)
    slots = counts.recent_completed(now, 14)
    assert len(slots) == 14
    rows = _sessions(slots, fetched=20, new=0)
    for row in rows:
        if row["source"] != "pubmed":
            row["new"] = 1
    problems = counts.scout_problems(_status(rows), now)
    assert [item["key"] for item in problems] == ["pubmed-no-new-7d"]
    _pubmed(rows)[0]["new"] = 1
    assert counts.scout_problems(_status(rows), now) == []


def test_a_missing_log_counts_as_fetched_zero(tmp_path):
    now = _at(12, 45)
    slots = list(reversed(counts.recent_completed(now, 14)))
    # Write every session except pubmed's three newest.
    newest = {(day, slot) for day, slot in counts.recent_completed(now, 3)}
    for day, slot in slots:
        for source in counts.SOURCES:
            if source == "pubmed" and (day, slot) in newest:
                continue
            path = tmp_path / f"{source}_{slot}_{day.strftime('%Y%m%d')}.log"
            path.write_text("SCOUT_STATS fetched=4 new_json=1 updated_json=3\n", encoding="utf-8")
    sessions = counts.collect_sessions(tmp_path, now=now)
    problems = counts.scout_problems(_status(sessions), now)
    assert [item["key"] for item in problems] == ["pubmed-fetched-zero"]


def test_stale_status_and_a_missing_scout_block():
    now = _at(12, 45)
    fresh = {"last_updated": "2026-11-17T12:40:00"}
    assert counts.stale_problem(fresh, now) is None
    old = {"last_updated": "2026-11-16T12:00:00"}
    stale = counts.stale_problem(old, now)
    assert stale is not None and stale["key"] == "status-stale"
    assert "18 hours" in stale["sentence"]
    # No scout block: do not invent a per-source alarm from a file that predates the counts.
    assert counts.scout_problems(old, now) == []
    assert [item["key"] for item in counts.alarm_problems(old, now)] == ["status-stale"]
    assert counts.stale_problem({}, now)["key"] == "status-stale"


def test_an_open_issue_for_the_same_key_is_not_opened_again():
    problems = [
        {"key": "arxiv-fetched-zero", "sentence": "arXiv fetched no papers for 3 sessions in a row."},
        {"key": "status-stale", "sentence": "The knowledge-engine status is more than 18 hours old."},
    ]
    pending = alarm.pending_problems(problems, ["arxiv-fetched-zero"])
    assert [item["key"] for item in pending] == ["status-stale"]
    body = alarm.issue_body(problems[1])
    assert "alarm-key: status-stale" in body
    assert "knowledge-engine-status.json" in body


def test_the_workflow_runs_after_each_scout_window_in_winter():
    text = Path(__file__).resolve().parents[3].joinpath(".github/workflows/scout-alarm.yml").read_text(encoding="utf-8")
    assert '- cron: "45 17 * * *"' in text
    assert '- cron: "45 3 * * *"' in text
    assert "issues: write" in text
