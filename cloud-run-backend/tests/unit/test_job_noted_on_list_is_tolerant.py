"""A curated run must not be thrown away because a breadcrumb could not be written.

On 2026-11-22 a run of 017 was refused with HTTP 500 after every check had passed. The job document had already been written; the next line
appended the job id to its source list inside a Firestore transaction, and that transaction came back "The referenced transaction has expired
or is no longer valid". Generation had not started, so nothing was voiced, and the job was left at `pending` with no owner — an orphan that
had to be marked failed by hand.

The list's `jobs` array is a convenience. The link of record lives on the job (`curated_list_id`, `curated_list_hash`), nothing in the
service reads the array, and it can be rebuilt from the jobs collection. So the append retries once and then gives up loudly, and the run
goes on.
"""
import re
from pathlib import Path

import pytest
from fastapi import HTTPException

import endpoints.curated.routes as routes

BACKEND = Path(__file__).resolve().parents[2]


@pytest.fixture
def calls(monkeypatch):
    """Record every _mutate attempt, and the log lines, without touching Firestore."""
    seen = {"mutate": 0, "warning": [], "error": []}
    monkeypatch.setattr(routes, "_require_db", lambda: None)
    monkeypatch.setattr(routes.structured_logger, "warning", lambda msg, **kw: seen["warning"].append((msg, kw)))
    monkeypatch.setattr(routes.structured_logger, "error", lambda msg, **kw: seen["error"].append((msg, kw)))
    return seen


def _mutate_that(calls, fail_times, exc=RuntimeError("The referenced transaction has expired or is no longer valid")):
    def fake(list_id, mutator):
        calls["mutate"] += 1
        if calls["mutate"] <= fail_times:
            raise exc
        return True
    return fake


def test_a_working_append_is_made_once(calls, monkeypatch):
    monkeypatch.setattr(routes, "_mutate", _mutate_that(calls, 0))
    assert routes._note_job_on_list("L1", "J1") is True
    assert calls["mutate"] == 1
    assert calls["warning"] == [] and calls["error"] == []


def test_a_transient_failure_is_retried_once_and_succeeds(calls, monkeypatch):
    monkeypatch.setattr(routes, "_mutate", _mutate_that(calls, 1))
    assert routes._note_job_on_list("L1", "J1") is True
    assert calls["mutate"] == 2, "exactly one retry"
    assert len(calls["warning"]) == 1 and calls["warning"][0][1]["job_id"] == "J1"
    assert calls["error"] == [], "a retry that works is not an error"


def test_two_failures_log_an_error_with_both_ids_and_the_run_continues(calls, monkeypatch):
    monkeypatch.setattr(routes, "_mutate", _mutate_that(calls, 2))
    assert routes._note_job_on_list("L1", "J1") is False, "it reports the failure, it does not raise"
    assert calls["mutate"] == 2, "it does not keep retrying"
    assert len(calls["error"]) == 1
    message, fields = calls["error"][0]
    assert fields["job_id"] == "J1" and fields["list_id"] == "L1", "both ids are named"
    assert "podcast_jobs" in message, "the log says how to rebuild the array"


def test_a_missing_list_or_a_status_refusal_still_reaches_the_caller(calls, monkeypatch):
    """Only infrastructure failures are tolerated. A 404 for a list that does not exist is the caller's answer."""
    def fake(list_id, mutator):
        calls["mutate"] += 1
        raise HTTPException(status_code=404, detail="No such source list")
    monkeypatch.setattr(routes, "_mutate", fake)
    with pytest.raises(HTTPException) as got:
        routes._note_job_on_list("L1", "J1")
    assert got.value.status_code == 404
    assert calls["mutate"] == 1, "an HTTPException is not retried"


def test_both_generation_routes_use_the_tolerant_append():
    """Neither route may append inside the request-failing transaction again."""
    source = (BACKEND / "endpoints" / "curated" / "routes.py").read_text(encoding="utf-8")
    assert source.count("_note_job_on_list(body.list_id, job_id)") == 2
    assert not re.search(r'^\s*_mutate\(body\.list_id, lambda d: d\.setdefault\("jobs"', source, re.M), \
        "the fragile form is gone from both call sites"


def test_the_job_still_records_which_list_it_came_from():
    """The tolerance is only safe because the link of record is on the job itself."""
    source = (BACKEND / "endpoints" / "curated" / "routes.py").read_text(encoding="utf-8")
    assert source.count("'curated_list_id': run.list_id, 'curated_list_hash': run.list_hash") == 2
