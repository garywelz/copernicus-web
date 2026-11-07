"""Onboarding PR 1 (design 7.3, Q6): the monthly generation quota, its 429 message, and the refund of a generation that failed before anything was spent.
Offline: an in-memory Firestore, a stub generation service, no network, no waits."""
import re
from pathlib import Path

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

import utils.generation_quota as gq
from tests.fakes_pr1 import FakeDB, Txn, passthrough_transactional, subscriber

SUB = "sub-q"
TOKEN = "token-q"
HS = {"X-Subscriber-Token": TOKEN}
ADMIN = {"X-Admin-API-Key": "test-key"}
BODY = {"topic": "a topic", "category": "Physics"}
MONTH = gq.current_month_key()


def fresh_db(quota=10, used=0, month=MONTH):
    return FakeDB(subscribers={SUB: subscriber(TOKEN, can_generate=True, monthly_quota=quota, generations_this_month=used, generation_month=month)}, podcast_jobs={})


class Service:
    """Stands in for the generation service. `outcome` decides what a run does to its job."""
    def __init__(self, db, outcome="ok"):
        self.db, self.outcome, self.calls = db, outcome, 0

    async def run_podcast_generation_job(self, job_id, request, subscriber_id=None, **kw):
        self.calls += 1
        ref = self.db.collection("podcast_jobs").document(job_id)
        if self.outcome == "ok":
            ref.update({"status": "completed", "result": {"canonical_filename": f"ep-{job_id[:6]}", "title": "t"}})
        elif self.outcome == "raise":
            raise RuntimeError("generation exploded before any audio")
        elif self.outcome == "raise_after_mark_only":
            ref.update({"tts_started_at": "2026-11-05T12:00:00"})            # the mark was written, then the usage record never was
            raise RuntimeError("audio step failed and the usage write was lost")
        elif self.outcome == "raise_after_tts":
            ref.update({"tts_characters": 1200, "tts_segments": 4})      # what the service stores when text-to-speech requests were sent
            raise RuntimeError("audio step failed after sending text")


@pytest.fixture
def env(monkeypatch):
    import config.database
    import utils.auth as auth
    from endpoints.podcast import routes as podcast_routes
    db = fresh_db()
    svc = Service(db)
    for mod in (podcast_routes, config.database):
        monkeypatch.setattr(mod, "db", db)
    monkeypatch.setattr(auth, "get_admin_api_key", lambda: "test-key")
    monkeypatch.setattr(gq.firestore, "transactional", passthrough_transactional)
    monkeypatch.setattr(podcast_routes, "_get_service", lambda: svc)
    app = FastAPI()
    app.include_router(podcast_routes.router)
    return type("Env", (), {"db": db, "svc": svc, "client": TestClient(app), "set_outcome": lambda self, o: setattr(svc, "outcome", o)})()


def generate(env, headers=HS):
    return env.client.post(f"/generate-podcast-with-subscriber?subscriber_id={SUB}", json=BODY, headers=headers)


def used(env):
    return env.db.data["subscribers"][SUB]["generations_this_month"]


# ---- the limit -----------------------------------------------------------------------------------------------------------------------------
def test_the_10th_generation_succeeds_and_the_11th_is_a_429_with_the_plain_message(env):
    for n in range(1, 11):
        r = generate(env)
        assert r.status_code == 200 and r.json()["status"] == "completed", (n, r.text)
        assert used(env) == n
    r = generate(env)
    assert r.status_code == 429 and r.json() == {"detail": "monthly limit reached"}      # nothing else: no count, no quota, no date
    assert env.svc.calls == 10 and used(env) == 10 and len(env.db.data["podcast_jobs"]) == 10    # the refused request made no job and ran nothing


def test_the_limit_applies_on_the_other_two_generate_routes_too(env, monkeypatch):
    env.db.data["subscribers"][SUB]["generations_this_month"] = 10
    assert env.client.post(f"/generate-podcast?subscriber_id={SUB}", json=BODY, headers=HS).json() == {"detail": "monthly limit reached"}
    assert env.client.post("/generate-podcast-from-paper", json={"subscriber_id": SUB, "paper_id": "p"}, headers=HS).status_code == 429


def test_a_refund_counts_in_refunds_this_month_and_a_new_month_reads_zero(env):
    env.set_outcome("raise")
    for n in (1, 2, 3):
        generate(env)
        assert env.db.data["subscribers"][SUB]["refunds_this_month"] == n and used(env) == 0
        assert gq.read_quota(env.db, SUB)["refunds_this_month"] == n
    env.db.data["subscribers"][SUB]["refunds_month"] = "2000-01"                        # the stored refunds belong to an earlier month
    assert gq.read_quota(env.db, SUB)["refunds_this_month"] == 0
    generate(env)
    assert env.db.data["subscribers"][SUB]["refunds_this_month"] == 1                   # the new month starts again at one, not four
    assert env.db.data["subscribers"][SUB]["refunds_month"] == MONTH
    env.set_outcome("raise_after_tts")
    generate(env)
    assert env.db.data["subscribers"][SUB]["refunds_this_month"] == 1                   # a refused refund adds nothing


def test_the_refund_count_has_no_cap(env):
    env.db.data["subscribers"][SUB].update(refunds_this_month=500, refunds_month=MONTH, monthly_quota=1)
    env.set_outcome("raise")
    for _ in range(3):
        assert generate(env).status_code == 500                                         # quota 1: each failure is refunded, so each retry is allowed
    assert env.db.data["subscribers"][SUB]["refunds_this_month"] == 503


def test_a_new_month_resets_the_count_and_unlimited_never_stops(env):
    env.db.data["subscribers"][SUB].update(generations_this_month=10, generation_month="2000-01")
    assert generate(env).status_code == 200 and used(env) == 1
    env.db.data["subscribers"][SUB].update(monthly_quota=None, generations_this_month=5000)
    assert generate(env).status_code == 200


def test_the_message_constant_is_the_one_users_see():
    assert gq.QUOTA_MESSAGE == "monthly limit reached"
    with pytest.raises(gq.QuotaExceeded) as e:
        class R:
            def get(self, transaction=None):
                class S:
                    exists = True
                    def to_dict(self_s):
                        return {"can_generate": True, "monthly_quota": 1, "generations_this_month": 1, "generation_month": MONTH}
                return S()
        gq._check_and_increment(Txn(), R())
    assert str(e.value) == "monthly limit reached"


# ---- the refund (Q6) -----------------------------------------------------------------------------------------------------------------------
def test_a_failure_before_any_text_to_speech_is_refunded(env):
    env.set_outcome("raise")
    r = generate(env)
    assert r.status_code == 500 and used(env) == 0                                    # counted at the start, given back at the failure
    job = next(iter(env.db.data["podcast_jobs"].values()))
    assert job["status"] == "failed" and job["quota_refunded"] is True and job["quota_counted"] is True


def test_a_failure_after_text_to_speech_was_sent_is_not_refunded(env):
    env.set_outcome("raise_after_tts")
    assert generate(env).status_code == 500 and used(env) == 1                        # characters were paid for: the unit stays used
    job = next(iter(env.db.data["podcast_jobs"].values()))
    assert "quota_refunded" not in job


def test_a_job_with_the_tts_mark_but_no_usage_record_is_not_refunded(env):
    env.set_outcome("raise_after_mark_only")
    assert generate(env).status_code == 500 and used(env) == 1                        # the usage write failed, but the mark proves speech may have been requested
    job = next(iter(env.db.data["podcast_jobs"].values()))
    assert job["tts_started_at"] and "tts_characters" not in job and "quota_refunded" not in job
    assert gq.refund_failed_job(env.db, next(iter(env.db.data["podcast_jobs"]))) == (False, "tts_started")


def test_a_failure_before_the_mark_is_still_refunded(env):
    env.set_outcome("raise")
    assert generate(env).status_code == 500 and used(env) == 0
    assert "tts_started_at" not in next(iter(env.db.data["podcast_jobs"].values()))


def test_ten_failures_that_spent_nothing_never_use_up_the_quota(env):
    env.set_outcome("raise")
    for _ in range(12):
        assert generate(env).status_code == 500
    assert used(env) == 0
    env.set_outcome("ok")
    assert generate(env).status_code == 200


def test_job_creation_failure_gives_the_unit_back(env, monkeypatch):
    env.db.fail_set_on = {"podcast_jobs"}
    assert generate(env).status_code == 500 and used(env) == 0                        # counted, but no job was ever made


def test_a_refund_happens_once(env):
    env.set_outcome("raise")
    generate(env)
    job_id = next(iter(env.db.data["podcast_jobs"]))
    env.db.data["subscribers"][SUB]["generations_this_month"] = 4
    assert gq.refund_failed_job(env.db, job_id) == (False, "already_refunded") and used(env) == 4


@pytest.mark.parametrize("job,reason", [
    ({"status": "failed", "quota_counted": True, "quota_month": MONTH, "tts_segments": 3}, "tts_characters_spent"),
    ({"status": "failed", "quota_counted": True, "quota_month": MONTH, "tts_characters": 10}, "tts_characters_spent"),
    ({"status": "failed", "quota_counted": True, "quota_month": MONTH, "result": {"canonical_filename": "x"}}, "produced_a_result"),
    ({"status": "completed", "quota_counted": True, "quota_month": MONTH}, "not_failed"),
    ({"status": "pending", "quota_counted": True, "quota_month": MONTH}, "not_failed"),
    ({"status": "failed"}, "not_metered"),                                              # an admin-key or older job: never stamped
])
def test_refund_is_refused_unless_safe(env, job, reason):
    env.db.data["subscribers"][SUB]["generations_this_month"] = 3
    env.db.data["podcast_jobs"]["j"] = {"subscriber_id": SUB, **job}
    assert gq.refund_failed_job(env.db, "j") == (False, reason)
    assert used(env) == 3


def test_a_refund_never_reaches_into_another_month(env):
    env.db.data["subscribers"][SUB].update(generations_this_month=2, generation_month=MONTH)
    env.db.data["podcast_jobs"]["j"] = {"subscriber_id": SUB, "status": "failed", "quota_counted": True, "quota_month": "2000-01"}
    assert gq.refund_failed_job(env.db, "j") == (False, "count_already_reset") and used(env) == 2


def test_a_count_never_goes_below_zero(env):
    env.db.data["subscribers"][SUB]["generations_this_month"] = 0
    env.db.data["podcast_jobs"]["j"] = {"subscriber_id": SUB, "status": "failed", "quota_counted": True, "quota_month": MONTH}
    assert gq.refund_failed_job(env.db, "j")[0] is False and used(env) == 0


def test_a_refund_problem_never_hides_the_real_failure(env):
    assert gq.refund_failed_job(env.db, "no-such-job")[0] is False                    # missing job: reported, not raised
    broken = object()
    assert gq.refund_failed_job(broken, "j")[1].startswith("refund_error:")           # a broken database: reported, not raised


# ---- unaffected: admin-generated work ------------------------------------------------------------------------------------------------------
def test_admin_key_generation_is_unmetered_unstamped_and_never_refunded(env):
    env.db.data["subscribers"][SUB]["generations_this_month"] = 10                     # at the limit: an admin request is not blocked by it
    env.set_outcome("ok")
    assert generate(env, headers=ADMIN).status_code == 200
    job = next(iter(env.db.data["podcast_jobs"].values()))
    assert "quota_counted" not in job and used(env) == 10
    env.set_outcome("raise")
    assert generate(env, headers=ADMIN).status_code == 500
    assert used(env) == 10                                                             # no refund for a request that was never counted
    assert all("quota_counted" not in j and "quota_refunded" not in j for j in env.db.data["podcast_jobs"].values())


def test_quota_stamp_only_marks_subscriber_requests():
    assert gq.quota_stamp({"via": "admin"}) == {} and gq.quota_stamp(None) == {}
    assert gq.quota_stamp({"via": "subscriber"}) == {"quota_counted": True, "quota_month": MONTH}


# ---- wiring: the real service must call the refund where it marks a job failed --------------------------------------------------------------
def test_the_generation_service_refunds_at_both_places_it_marks_a_job_failed():
    """The service cannot be run offline here (it needs the speech, model and storage clients), so this checks the wiring in its source: every place it
    sets status 'failed' for a generation run is followed by the refund call."""
    src = Path(__file__).resolve().parent.parent.joinpath("services", "podcast_generation_service.py").read_text(encoding="utf-8").replace("\r\n", "\n")
    assert "from utils.generation_quota import refund_failed_job" in src
    run_start = src.index("async def run_podcast_generation_job")
    run_end = src.index("async def run_curated_generation_job")
    body = src[run_start:run_end]
    failed_updates = [m.end() for m in re.finditer(r"'status': 'failed',", body)]
    assert len(failed_updates) == 2
    for end in failed_updates:
        assert "refund_failed_job(db, job_id)" in body[end:end + 600]


def test_the_service_writes_the_tts_mark_before_the_first_speech_request_and_fails_closed():
    src = Path(__file__).resolve().parent.parent.joinpath("services", "podcast_generation_service.py").read_text(encoding="utf-8").replace("\r\n", "\n")
    mark = src.index("job_ref.update({'tts_started_at'")
    first_request = src.index("generate_multi_voice_audio_with_bumpers(")
    assert mark < first_request
    guard = src[mark - 40:first_request]
    assert "except Exception as mark_error:" in guard and "no speech was requested" in guard and "raise RuntimeError" in guard
    assert src.count("generate_multi_voice_audio_with_bumpers(") == 1                 # there is no other speech request in the generation run
