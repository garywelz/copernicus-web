"""Dashboard fixes (Gary, 2026-11-06), change 1: a long generation request must not be the thing the page depends on.

What the investigation found (recorded in the PR): the generation routes run the whole job INSIDE the request (Cloud Run gives the instance CPU only while a request
is in flight, so a background task would be starved), the request therefore stays open for the whole job, and the page used to await it before it showed or polled
anything; a dropped connection then read "Network error. Please try again" while the job ran on. The fix needs no new infrastructure: the page chooses the job id
(`client_job_id`), shows "Generating..." at once, and follows the job by polling an owner-only status route. Offline: an in-memory Firestore, a stub service."""
import asyncio
import json
import uuid

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

import utils.generation_quota as gq
from tests.fakes_pr1 import FakeDB, passthrough_transactional, subscriber

A, B = "sub-a", "sub-b"
TOK_A, TOK_B = "token-a", "token-b"
HA, HB = {"X-Subscriber-Token": TOK_A}, {"X-Subscriber-Token": TOK_B}
ADMIN = {"X-Admin-API-Key": "test-key"}
MONTH = gq.current_month_key()
BODY = {"topic": "a topic", "category": "Physics"}


def new_id():
    return str(uuid.uuid4())


class Service:
    def __init__(self, db):
        self.db, self.seen, self.gate = db, [], None

    async def run_podcast_generation_job(self, job_id, request, subscriber_id=None, **kw):
        self.seen.append(job_id)
        if self.gate is not None:
            await self.gate()
        self.db.collection("podcast_jobs").document(job_id).update({"status": "completed", "result": {"canonical_filename": "ep-1", "title": "A title"}})


@pytest.fixture
def env(monkeypatch):
    import config.database
    import utils.auth as auth
    from endpoints.podcast import routes as podcast_routes
    from endpoints.public import health as health_routes
    from endpoints.subscriber import episode_access as owner_routes
    db = FakeDB(subscribers={A: subscriber(TOK_A, can_generate=True, monthly_quota=10, generations_this_month=0, generation_month=MONTH),
                             B: subscriber(TOK_B, can_generate=True, monthly_quota=10, generations_this_month=0, generation_month=MONTH)}, podcast_jobs={})
    svc = Service(db)
    for mod in (podcast_routes, owner_routes, config.database):
        monkeypatch.setattr(mod, "db", db)
    monkeypatch.setattr(auth, "get_admin_api_key", lambda: "test-key")
    monkeypatch.setattr(gq.firestore, "transactional", passthrough_transactional)
    monkeypatch.setattr(podcast_routes, "_get_service", lambda: svc)
    app = FastAPI()
    app.include_router(podcast_routes.router)
    app.include_router(owner_routes.router)
    app.include_router(health_routes.router)
    return type("Env", (), {"db": db, "svc": svc, "app": app, "client": TestClient(app)})()


def job(env, jid, owner=A, **fields):
    env.db.data["podcast_jobs"][jid] = {"job_id": jid, "subscriber_id": owner, "status": "pending", "created_at": "2026-11-07T10:00:00", "updated_at": "2026-11-07T10:00:00",
                                        "request": {"topic": "SECRET TOPIC"}, "error": "internal detail", **fields}
    return jid


# ---- the owner-only status route ----------------------------------------------------------------------------------------------------------
@pytest.mark.parametrize("status", ["pending", "researching", "generating_content", "audio", "anything-else"])
def test_every_intermediate_status_reads_as_running(env, status):
    jid = job(env, new_id(), status=status)
    r = env.client.get(f"/api/subscribers/jobs/{jid}/status", headers=HA)
    assert r.status_code == 200 and r.json()["state"] == "running" and r.json()["status"] == status
    assert r.headers["cache-control"] == "no-store"


def test_a_finished_job_names_its_episode_and_a_failed_one_says_whether_the_unit_came_back(env):
    done = job(env, new_id(), status="completed", result={"canonical_filename": "ever-phys-990001", "title": "T", "audio_url": "x"})
    r = env.client.get(f"/api/subscribers/jobs/{done}/status", headers=HA).json()
    assert r["state"] == "completed" and r["episode_id"] == "ever-phys-990001" and r["title"] == "T"
    failed = job(env, new_id(), status="failed")
    r = env.client.get(f"/api/subscribers/jobs/{failed}/status", headers=HA).json()
    assert r["state"] == "failed" and r["unit_returned"] is False
    refunded = job(env, new_id(), status="failed", quota_refunded=True)
    assert env.client.get(f"/api/subscribers/jobs/{refunded}/status", headers=HA).json()["unit_returned"] is True


def test_the_answer_never_carries_the_request_the_error_text_or_an_account(env):
    jid = job(env, new_id(), status="failed", result={"canonical_filename": "e"})
    text = env.client.get(f"/api/subscribers/jobs/{jid}/status", headers=HA).text
    for secret in ("SECRET TOPIC", "internal detail", A, "request", "error", "subscriber_id"):
        assert secret not in text


def test_anyone_but_the_owner_gets_the_same_404_as_a_missing_job(env):
    jid = job(env, new_id(), owner=A)
    expect = env.client.get(f"/api/subscribers/jobs/{new_id()}/status", headers=HA)
    assert expect.status_code == 404
    for headers in (HB, {}, {"X-Subscriber-Token": "garbage"}, {"X-Admin-API-Key": "wrong"}):
        r = env.client.get(f"/api/subscribers/jobs/{jid}/status", headers=headers)
        assert r.status_code == 404 and r.json() == expect.json()
    assert env.client.get("/api/subscribers/jobs/not-a-uuid/status", headers=HA).status_code == 404
    assert env.client.get(f"/api/subscribers/jobs/{jid}/status", headers=ADMIN).status_code == 200      # the admin key may look


def test_an_owner_who_is_not_on_the_private_access_list_can_still_follow_their_own_job(env):
    jid = job(env, new_id())
    assert env.db.data.get("system_config") is None                                   # no allow-list at all
    assert env.client.get(f"/api/subscribers/jobs/{jid}/status", headers=HA).status_code == 200


# ---- the page chooses the job id -------------------------------------------------------------------------------------------------------------
def test_the_chosen_id_becomes_the_job_id_and_the_page_can_poll_it(env):
    jid = new_id()
    r = env.client.post(f"/generate-podcast-with-subscriber?subscriber_id={A}&client_job_id={jid}", json=BODY, headers=HA)
    assert r.status_code == 200 and r.json()["job_id"] == jid and env.svc.seen == [jid]
    assert env.client.get(f"/api/subscribers/jobs/{jid}/status", headers=HA).json()["state"] == "completed"


def test_without_one_the_server_still_makes_its_own_id(env):
    r = env.client.post(f"/generate-podcast-with-subscriber?subscriber_id={A}", json=BODY, headers=HA)
    assert r.status_code == 200 and uuid.UUID(r.json()["job_id"]).version == 4


@pytest.mark.parametrize("bad", ["x", "../../etc", "123", "g" * 36, new_id().upper() + "x"])
def test_a_malformed_id_is_a_400_and_gives_the_unit_back(env, bad):
    r = env.client.post(f"/generate-podcast-with-subscriber?subscriber_id={A}&client_job_id={bad}", json=BODY, headers=HA)
    assert r.status_code == 400 and env.svc.seen == [] and env.db.data["podcast_jobs"] == {}
    assert env.db.data["subscribers"][A]["generations_this_month"] == 0


def test_an_id_that_already_names_a_job_is_a_409_and_cannot_touch_another_owners_job(env):
    taken = job(env, new_id(), owner=B, status="completed")
    before = dict(env.db.data["podcast_jobs"][taken])
    r = env.client.post(f"/generate-podcast-with-subscriber?subscriber_id={A}&client_job_id={taken}", json=BODY, headers=HA)
    assert r.status_code == 409 and env.svc.seen == [] and env.db.data["podcast_jobs"][taken] == before
    assert env.db.data["subscribers"][A]["generations_this_month"] == 0


def test_the_paper_route_takes_the_chosen_id_too(env, monkeypatch):
    paper = {"paper_id": "p1", "title": "A paper", "abstract": "An abstract of some length."}
    from endpoints.podcast import routes as pr
    monkeypatch.setattr(pr, "get_paper_by_id", lambda pid: paper)
    jid = new_id()
    r = env.client.post(f"/generate-podcast-from-paper?client_job_id={jid}", json={"subscriber_id": A, "paper_id": "p1", "category": "Biology"}, headers=HA)
    assert r.status_code == 200 and r.json()["job_id"] == jid and env.svc.seen == [jid]


# ---- the property the fix rests on: a dropped client does not stop the job ----------------------------------------------------------------------
def test_the_job_keeps_running_and_finishes_after_the_client_disconnects(env):
    """Drives the app at the ASGI level: the request arrives, the job starts, the client disconnects mid-job, the job still completes and is recorded.
    (The framework does not cancel the handler on disconnect: no BaseHTTPMiddleware is installed, only CORS.)"""
    jid = new_id()
    body = json.dumps(BODY).encode()

    async def run():
        release, started = asyncio.Event(), asyncio.Event()

        async def gate():
            started.set()
            await release.wait()
        env.svc.gate = gate
        sent_body, disconnect, out = False, asyncio.Event(), []

        async def receive():
            nonlocal sent_body
            if not sent_body:
                sent_body = True
                return {"type": "http.request", "body": body, "more_body": False}
            await disconnect.wait()
            return {"type": "http.disconnect"}

        async def send(message):
            out.append(message)
        scope = {"type": "http", "asgi": {"version": "3.0"}, "http_version": "1.1", "method": "POST", "scheme": "http", "path": "/generate-podcast-with-subscriber",
                 "raw_path": b"/generate-podcast-with-subscriber", "root_path": "", "query_string": f"subscriber_id={A}&client_job_id={jid}".encode(),
                 "headers": [(b"content-type", b"application/json"), (b"content-length", str(len(body)).encode()), (b"x-subscriber-token", TOK_A.encode())],
                 "server": ("test", 80), "client": ("127.0.0.1", 1)}
        task = asyncio.ensure_future(env.app(scope, receive, send))
        await asyncio.wait_for(started.wait(), 5)
        disconnect.set()                                         # the client goes away while the job is running
        await asyncio.sleep(0.05)
        assert not task.done(), "the handler was cancelled by the disconnect"
        assert env.db.data["podcast_jobs"][jid]["status"] == "pending"
        release.set()
        await asyncio.wait_for(task, 5)
    asyncio.run(run())
    assert env.db.data["podcast_jobs"][jid]["status"] == "completed"          # the job finished and was recorded though nobody was listening
    assert env.client.get(f"/api/subscribers/jobs/{jid}/status", headers=HA).json()["state"] == "completed"


# ---- change 8: job-status access tightened (GET /status/{job_id}) --------------------------------------------------------------------------
def test_legacy_status_route_allows_the_owner_and_the_admin_only(env):
    jid = job(env, new_id(), status="completed", result={"canonical_filename": "ever-phys-990001", "title": "T"})
    for headers in (HA, ADMIN):
        r = env.client.get(f"/status/{jid}", headers=headers)
        assert r.status_code == 200 and r.json()["state"] == "completed" and r.json()["episode_id"] == "ever-phys-990001"
    expect = env.client.get(f"/status/{new_id()}", headers=HA)                       # a job that does not exist
    assert expect.status_code == 404
    for headers in (HB, {}, {"X-Subscriber-Token": "garbage"}, {"X-Admin-API-Key": "wrong"}):
        r = env.client.get(f"/status/{jid}", headers=headers)
        assert r.status_code == 404 and r.json() == expect.json()                    # another user, anonymous, bad token, bad key: the same 404 as a missing job
    assert env.client.get("/status/not-a-uuid", headers=HA).status_code == 404


def test_legacy_status_route_returns_no_address_and_no_stored_document(env):
    jid = job(env, new_id(), status="completed", subscriber_email="someone@example.invalid", result={"canonical_filename": "e", "title": "T", "notify_to": "someone@example.invalid"},
              request={"topic": "SECRET TOPIC", "email": "someone@example.invalid"})
    for headers in (HA, ADMIN):
        text = env.client.get(f"/status/{jid}", headers=headers).text
        assert "@" not in text and "example.invalid" not in text
        for hidden in ("SECRET TOPIC", "internal detail", "request", "subscriber", "error"):
            assert hidden not in text
        assert set(env.client.get(f"/status/{jid}", headers=headers).json()) <= {"job_id", "state", "status", "created_at", "updated_at", "episode_id", "title", "unit_returned"}


def test_the_admin_may_look_up_a_debug_job_but_nobody_else_may(env):
    jid = "debug-" + new_id()
    env.db.data["podcast_jobs"][jid] = {"job_id": jid, "status": "pending", "created_at": "2026-11-07T10:00:00"}
    assert env.client.get(f"/status/{jid}", headers=ADMIN).status_code == 200
    assert env.client.get(f"/status/{jid}", headers=HA).status_code == 404
    assert env.client.get(f"/status/{jid}").status_code == 404
