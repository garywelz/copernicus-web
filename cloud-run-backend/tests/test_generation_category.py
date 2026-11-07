"""Dashboard fixes (Gary, 2026-11-06), change 2: a subscriber's generation request must name a category from the form's list. No default.

The model's own default ("Computer Science") used to fill in a missing category; the PR 2 smoke test's bees episode was misfiled by it. For a SUBSCRIBER request
the server now refuses a missing, empty or unknown category with 400, before any job exists, and gives back the unit that was counted. The administrator and the
curated routes are not touched (proved here). Offline: an in-memory Firestore and a stub generation service."""
from pathlib import Path

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

import utils.generation_quota as gq
from tests.fakes_pr1 import FakeDB, passthrough_transactional, subscriber

SUB, TOKEN = "sub-c", "token-c"
HS = {"X-Subscriber-Token": TOKEN}
ADMIN = {"X-Admin-API-Key": "test-key"}
MONTH = gq.current_month_key()
FORM_LIST = ["Biology", "Chemistry", "Computer Science", "Mathematics", "Physics"]
REPO = Path(__file__).resolve().parents[2]


class Service:
    def __init__(self, db):
        self.db, self.calls = db, []

    async def run_podcast_generation_job(self, job_id, request, subscriber_id=None, **kw):
        self.calls.append(request.category)
        self.db.collection("podcast_jobs").document(job_id).update({"status": "completed", "result": {"canonical_filename": f"ep-{job_id[:6]}", "title": "t"}})


@pytest.fixture
def env(monkeypatch):
    import config.database
    import utils.auth as auth
    from endpoints.podcast import routes as podcast_routes
    db = FakeDB(subscribers={SUB: subscriber(TOKEN, can_generate=True, monthly_quota=10, generations_this_month=0, generation_month=MONTH)}, podcast_jobs={})
    svc = Service(db)
    for mod in (podcast_routes, config.database):
        monkeypatch.setattr(mod, "db", db)
    monkeypatch.setattr(auth, "get_admin_api_key", lambda: "test-key")
    monkeypatch.setattr(gq.firestore, "transactional", passthrough_transactional)
    monkeypatch.setattr(podcast_routes, "_get_service", lambda: svc)
    monkeypatch.setattr(podcast_routes, "resolve_generation_subscriber_id", lambda sid=None: sid or "admin-sub")   # no real lookup: other test files leave a mock db in utils.subscriber_helpers
    app = FastAPI()
    app.include_router(podcast_routes.router)
    return type("Env", (), {"db": db, "svc": svc, "client": TestClient(app), "routes": podcast_routes})()


def used(env):
    return env.db.data["subscribers"][SUB]["generations_this_month"]


def post(env, route, body, headers=HS, sub=True):
    return env.client.post(route + (f"?subscriber_id={SUB}" if sub else ""), json=body, headers=headers)


ROUTES = ["/generate-podcast-with-subscriber", "/generate-podcast"]


def test_the_form_list_is_the_servers_list():
    from endpoints.podcast import routes
    assert list(routes.GENERATION_CATEGORIES) == FORM_LIST
    html = (REPO / "public" / "subscriber-dashboard.html").read_text(encoding="utf-8")
    for name in FORM_LIST:
        assert f'<option value="{name}">{name}</option>' in html
    assert '<option value="">Select category...</option>' in html           # the form has no preselected category


@pytest.mark.parametrize("route", ROUTES)
@pytest.mark.parametrize("body", [
    {"topic": "t"},                                   # missing: the model default must NOT fill it in
    {"topic": "t", "category": ""},
    {"topic": "t", "category": "Astrology"},
    {"topic": "t", "category": "physics"},            # exact labels only
    {"topic": "t", "category": " Physics"},
    {"topic": "t", "category": "Computer Science "},
])
def test_a_subscriber_request_without_a_valid_category_is_a_400_and_costs_nothing(env, route, body):
    r = post(env, route, body)
    assert r.status_code == 400
    assert r.json() == {"detail": "Choose a category: Biology, Chemistry, Computer Science, Mathematics, Physics."}
    assert env.svc.calls == [] and env.db.data["podcast_jobs"] == {}          # no job, nothing ran
    assert used(env) == 0                                                    # the counted unit was given back


@pytest.mark.parametrize("route", ROUTES)
def test_a_null_category_is_refused_by_the_model_before_anything_is_counted(env, route):
    r = post(env, route, {"topic": "t", "category": None})
    assert r.status_code == 422 and env.svc.calls == [] and env.db.data["podcast_jobs"] == {} and used(env) == 0


@pytest.mark.parametrize("route", ROUTES)
@pytest.mark.parametrize("name", FORM_LIST)
def test_each_listed_category_is_accepted_and_is_what_the_job_stores(env, route, name):
    r = post(env, route, {"topic": "t", "category": name})
    assert r.status_code == 200, r.text
    assert env.svc.calls == [name]
    job = next(iter(env.db.data["podcast_jobs"].values()))
    assert job["request"]["category"] == name and used(env) == 1


def test_a_missing_credential_is_still_a_401_not_a_400(env):
    assert env.client.post("/generate-podcast-with-subscriber", json={"topic": "t"}).status_code == 401


def test_the_paper_route_refuses_an_unknown_category_but_still_infers_a_missing_one(env, monkeypatch):
    monkeypatch.setattr(env.routes, "get_paper_by_id", lambda pid: None)       # stops after the category check: 404 means the check passed
    base = {"subscriber_id": SUB, "paper_id": "p1"}
    r = env.client.post("/generate-podcast-from-paper", json={**base, "category": "Astrology"}, headers=HS)
    assert r.status_code == 400 and "Choose a category" in r.json()["detail"] and used(env) == 0
    assert env.client.post("/generate-podcast-from-paper", json={**base, "category": ""}, headers=HS).status_code == 400
    assert env.client.post("/generate-podcast-from-paper", json=base, headers=HS).status_code == 404            # omitted: inferred from the paper, as before
    assert env.client.post("/generate-podcast-from-paper", json={**base, "category": "Biology"}, headers=HS).status_code == 404


# ---- the administrator and the curated routes are unchanged --------------------------------------------------------------------------------
@pytest.mark.parametrize("route", ROUTES)
def test_the_admin_key_still_gets_the_model_default_and_any_value(env, route):
    r = post(env, route, {"topic": "t"}, headers=ADMIN, sub=False)
    assert r.status_code == 200 and env.svc.calls == ["Computer Science"]
    r = post(env, route, {"topic": "t", "category": "Anything Goes"}, headers=ADMIN, sub=False)
    assert r.status_code == 200 and env.svc.calls[-1] == "Anything Goes"
    assert used(env) == 0                                                    # the admin is unmetered, as before


def test_the_model_default_is_unchanged_and_the_curated_routes_do_not_use_the_check():
    from models.podcast import PodcastRequest
    assert PodcastRequest(topic="t").category == "Computer Science"          # the admin path and the curated routes still rely on it
    curated = (REPO / "cloud-run-backend" / "endpoints" / "curated" / "routes.py").read_text(encoding="utf-8")
    assert "_require_category" not in curated and "GENERATION_CATEGORIES" not in curated
