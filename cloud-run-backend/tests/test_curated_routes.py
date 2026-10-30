"""The admin routes for curated source lists (design §3): admin key on every route, the whole lifecycle, freezing, and the failure paths.
Offline: Firestore is an in-memory fake and the confirmations are canned (they are tested in tests/unit/test_curated_sources.py)."""
from unittest.mock import MagicMock, patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

with patch('config.database.db', MagicMock()):
    from endpoints.curated import routes
    from endpoints.curated.routes import router

import curated_sources as cs
import openai_math_index as omi
import paper_confirmation as pc
from utils import auth

app = FastAPI()
app.include_router(router)
client = TestClient(app, raise_server_exceptions=False)
KEY = {"X-Admin-API-Key": "test-key"}


# --- fakes ---------------------------------------------------------------------------------------------------------------
class Snap:
    def __init__(self, data):
        self._d, self.exists = data, data is not None

    def to_dict(self):
        import copy
        return copy.deepcopy(self._d) if self._d is not None else None


class Ref:
    def __init__(self, store, doc_id):
        self.store, self.doc_id = store, doc_id

    def get(self, transaction=None):
        return Snap(self.store.get(self.doc_id))

    def set(self, data, **kw):
        import copy
        self.store[self.doc_id] = copy.deepcopy(data)


class FakeDB:
    def __init__(self):
        self.store = {}          # curated_source_lists
        self.other = {}          # every other collection, by name (podcast_jobs)

    def collection(self, name):
        db = self
        store = db.store if name == routes.COLLECTION else db.other.setdefault(name, {})

        class Col:
            def document(self_c, doc_id):
                return Ref(store, doc_id)

            def stream(self_c):
                return [type("D", (), {"to_dict": lambda s, d=d: d})() for d in store.values()]
        return Col()

    def transaction(self):
        return object()


class Txn:
    def set(self, ref, data):
        ref.set(data)


def fake_run(fn, *args):
    return fn(Txn(), *args)


def item(cls, n, status=cs.CONFIRMED, approved=True, **extra):
    ids = {"doi": f"10.1000/{cls}{n}"}
    base = {"item_id": cs.item_id(ids), "input": f"in{n}", "class": cls, "added_by": "gary", "identifiers": ids, "title": f"Title {cls} {n}",
            "authors": [], "year": 2025, "venue": None, "url": "u", "evidence_text": f"evidence {n}",
            "confirmation": {"status": status, "source_class": cls}, "relevance_score": None, "approved": approved}
    base.update(extra)
    return base


def refused(raw, reason="not_found"):
    return {"item_id": None, "input": raw, "class": None, "added_by": "gary",
            "confirmation": {"status": cs.REFUSED, "reason": reason, "detail": "", "directories": []}, "approved": False}


@pytest.fixture
def env():
    fake = FakeDB()
    canned = {}

    async def fake_confirm(raw, commit, http_get=None, fetch=None):
        v = canned[raw]
        if isinstance(v, Exception):
            raise v
        return v
    with patch.object(routes, "db", fake), patch.object(routes, "_run_in_transaction", fake_run), \
         patch.object(auth, "get_admin_api_key", return_value="test-key"), patch.object(cs, "confirm_pasted", fake_confirm):
        yield fake, canned


def new_list(**body):
    r = client.post("/api/admin/curated/lists", json={"title": "Series one", **body}, headers=KEY)
    assert r.status_code == 200, r.text
    return r.json()["list_id"]


def add(list_id, canned, raws_to_items):
    canned.update(raws_to_items)
    return client.post(f"/api/admin/curated/lists/{list_id}/items", json={"items": list(raws_to_items)}, headers=KEY)


# --- admin key on every route ---------------------------------------------------------------------------------------------------------
def test_every_route_on_the_router_needs_the_admin_key():
    routes_ = [r for r in router.routes if hasattr(r, "methods")]
    assert len(routes_) == 8
    with patch.object(auth, "get_admin_api_key", return_value="test-key"), patch.object(routes, "db", FakeDB()):
        for r in routes_:
            path = r.path.replace("{list_id}", "L").replace("{item_id}", "I")
            for method in r.methods:
                none = client.request(method, path, json={})
                wrong = client.request(method, path, json={}, headers={"X-Admin-API-Key": "wrong"})
                assert none.status_code == 401, (method, path)
                assert wrong.status_code == 403, (method, path)


def test_a_key_in_the_query_string_does_not_work():
    with patch.object(auth, "get_admin_api_key", return_value="test-key"), patch.object(routes, "db", FakeDB()):
        assert client.get("/api/admin/curated/lists?admin_key=test-key").status_code == 401


def test_without_a_configured_key_the_routes_are_closed():
    with patch.object(auth, "get_admin_api_key", return_value=None), patch.object(routes, "db", FakeDB()):
        assert client.get("/api/admin/curated/lists", headers=KEY).status_code == 503


def test_a_route_added_without_the_dependency_would_be_caught():
    deps = [d.dependency for d in router.dependencies]
    assert auth.verify_admin_api_key in deps


# --- creating a list -------------------------------------------------------------------------------------------------------------------
def test_a_new_list_is_a_draft_pinned_to_the_default_commit(env):
    fake, _ = env
    lid = new_list(topic="OpenAI mathematics release")
    doc = fake.store[lid]
    assert doc["status"] == "draft" and doc["pin"] == {"repo": "openai/math", "commit": omi.DEFAULT_COMMIT} and doc["items"] == []
    assert doc["list_hash"] is None and doc["created_by"] == "admin"


def test_a_given_pin_must_be_a_full_commit_id(env):
    assert client.post("/api/admin/curated/lists", json={"title": "x", "pin_commit": "main"}, headers=KEY).status_code == 422
    assert client.post("/api/admin/curated/lists", json={"title": "x", "pin_commit": "7ef5c0cc5"}, headers=KEY).status_code == 422
    ok = client.post("/api/admin/curated/lists", json={"title": "x", "pin_commit": "A" * 40}, headers=KEY)
    assert ok.status_code == 200 and ok.json()["pin"]["commit"] == "a" * 40


def test_title_is_required_and_bounded(env):
    for body in ({}, {"title": ""}, {"title": "x" * 201}):
        assert client.post("/api/admin/curated/lists", json=body, headers=KEY).status_code == 422


# --- adding items -----------------------------------------------------------------------------------------------------------------------
def test_confirmed_items_are_stored_and_refused_ones_are_reported_but_not_stored(env):
    fake, canned = env
    lid = new_list()
    r = add(lid, canned, {"a": [item(cs.PREPRINT, 1)], "b": [refused("b", "not_found")], "c": [item(cs.PEER_REVIEWED, 2)]})
    body = r.json()
    assert r.status_code == 200 and len(body["added"]) == 2 and len(body["refused"]) == 1
    assert body["refused"][0]["reason"] == "not_found" and body["refused"][0]["input"] == "b"
    assert len(fake.store[lid]["items"]) == 2 and fake.store[lid]["refused"][0]["reason"] == "not_found"


def test_a_duplicate_is_refused_as_a_duplicate(env):
    fake, canned = env
    lid = new_list()
    add(lid, canned, {"a": [item(cs.PREPRINT, 1)]})
    r = add(lid, canned, {"a2": [item(cs.PREPRINT, 1)]})
    assert r.json()["added"] == [] and r.json()["refused"][0]["reason"] == "duplicate" and len(fake.store[lid]["items"]) == 1


def test_an_unreachable_registry_or_repository_adds_nothing_and_is_503(env):
    fake, canned = env
    lid = new_list()
    r = add(lid, canned, {"ok": [item(cs.PREPRINT, 1)], "down": pc.RegistryUnavailable(["crossref"])})
    assert r.status_code == 503 and fake.store[lid]["items"] == []
    r = add(lid, canned, {"ok2": [item(cs.PREPRINT, 2)], "repo": omi.RepoUnavailable("rate limited")})
    assert r.status_code == 503 and fake.store[lid]["items"] == []


def test_a_list_holds_at_most_sixty_items(env):
    fake, canned = env
    lid = new_list()
    for start in range(0, 60, 30):
        r = add(lid, canned, {f"x{n}": [item(cs.PREPRINT, n)] for n in range(start, start + 30)})
        assert r.status_code == 200
    r = add(lid, canned, {"one more": [item(cs.PREPRINT, 999)]})
    assert r.status_code == 409 and len(fake.store[lid]["items"]) == 60


def test_the_request_is_bounded(env):
    lid = new_list()
    assert client.post(f"/api/admin/curated/lists/{lid}/items", json={"items": []}, headers=KEY).status_code == 422
    assert client.post(f"/api/admin/curated/lists/{lid}/items", json={"items": ["x"] * 41}, headers=KEY).status_code == 422


def test_an_unknown_list_is_404(env):
    assert client.get("/api/admin/curated/lists/nope", headers=KEY).status_code == 404
    assert client.post("/api/admin/curated/lists/nope/approve", headers=KEY).status_code == 404
    assert client.post("/api/admin/curated/lists/nope/items", json={"items": ["x"]}, headers=KEY).status_code == 404


# --- striking and overriding -------------------------------------------------------------------------------------------------------------
def test_an_item_can_be_struck_from_a_draft(env):
    fake, canned = env
    lid = new_list()
    add(lid, canned, {"a": [item(cs.PREPRINT, 1), item(cs.PREPRINT, 2)]})
    iid = fake.store[lid]["items"][0]["item_id"]
    assert client.delete(f"/api/admin/curated/lists/{lid}/items/{iid}", headers=KEY).status_code == 200
    assert [i["item_id"] for i in fake.store[lid]["items"]] != [iid] and len(fake.store[lid]["items"]) == 1
    assert client.delete(f"/api/admin/curated/lists/{lid}/items/{iid}", headers=KEY).status_code == 404


def test_the_only_class_change_allowed_is_peer_reviewed_to_preprint(env):
    fake, canned = env
    lid = new_list()
    add(lid, canned, {"a": [item(cs.PEER_REVIEWED, 1), item(cs.PREPRINT, 2), item(cs.COMPANY_RELEASE, 3)]})
    pr, pre, co = [i["item_id"] for i in fake.store[lid]["items"]]
    url = lambda iid: f"/api/admin/curated/lists/{lid}/items/{iid}/class"
    assert client.put(url(pr), json={"source_class": "preprint"}, headers=KEY).status_code == 200
    assert fake.store[lid]["items"][0]["class"] == "preprint"
    for iid, target in ((pre, "peer_reviewed"), (co, "preprint"), (pre, "company_release"), (pre, "commentary"), (pr, "peer_reviewed"), (pre, "bogus")):
        r = client.put(url(iid), json={"source_class": target}, headers=KEY)
        assert r.status_code == 422, (iid, target)
    assert [i["class"] for i in fake.store[lid]["items"]] == ["preprint", "preprint", "company_release"]


def test_an_override_on_a_missing_item_is_404(env):
    lid = new_list()
    assert client.put(f"/api/admin/curated/lists/{lid}/items/none/class", json={"source_class": "preprint"}, headers=KEY).status_code == 404


# --- approving and freezing ----------------------------------------------------------------------------------------------------------------
def test_approval_needs_three_confirmed_non_commentary_sources_and_commentary_never_counts(env):
    fake, canned = env
    lid = new_list()
    add(lid, canned, {"a": [item(cs.PREPRINT, 1), item(cs.PEER_REVIEWED, 2)]})
    r = client.post(f"/api/admin/curated/lists/{lid}/approve", headers=KEY)
    assert r.status_code == 422 and r.json()["detail"]["counts"]["non_commentary"] == 2
    add(lid, canned, {"c": [item(cs.COMMENTARY, 3, approved=True), item(cs.COMMENTARY, 4), item(cs.COMMENTARY, 5)]})
    r = client.post(f"/api/admin/curated/lists/{lid}/approve", headers=KEY)
    assert r.status_code == 422 and fake.store[lid]["status"] == "draft" and fake.store[lid]["list_hash"] is None


def test_unconfirmed_items_block_approval_until_they_are_removed(env):
    fake, canned = env
    lid = new_list()
    add(lid, canned, {"a": [item(cs.PREPRINT, 1), item(cs.PEER_REVIEWED, 2), item(cs.COMPANY_RELEASE, 3),
                            item(cs.COMMENTARY, 4, status=cs.PENDING, approved=False)]})
    r = client.post(f"/api/admin/curated/lists/{lid}/approve", headers=KEY)
    assert r.status_code == 409 and len(r.json()["detail"]["items"]) == 1
    pending = r.json()["detail"]["items"][0]
    client.delete(f"/api/admin/curated/lists/{lid}/items/{pending}", headers=KEY)
    assert client.post(f"/api/admin/curated/lists/{lid}/approve", headers=KEY).status_code == 200


def ready_list(canned):
    lid = new_list()
    add(lid, canned, {"a": [item(cs.PREPRINT, 1), item(cs.PEER_REVIEWED, 2), item(cs.COMPANY_RELEASE, 3)]})
    return lid


def test_approval_freezes_the_list_with_a_hash_and_nothing_can_change_afterwards(env):
    fake, canned = env
    lid = ready_list(canned)
    r = client.post(f"/api/admin/curated/lists/{lid}/approve", headers=KEY)
    assert r.status_code == 200 and r.json()["status"] == "approved" and len(r.json()["list_hash"]) == 64
    doc = fake.store[lid]
    assert doc["status"] == "approved" and doc["list_hash"] == r.json()["list_hash"] and doc["approved_at"]
    assert doc["list_hash"] == cs.list_hash(doc["pin"], doc["items"])
    frozen = client.get(f"/api/admin/curated/lists/{lid}", headers=KEY).json()
    iid = frozen["items"][0]["item_id"]
    attempts = [client.post(f"/api/admin/curated/lists/{lid}/items", json={"items": ["a"]}, headers=KEY),
                client.delete(f"/api/admin/curated/lists/{lid}/items/{iid}", headers=KEY),
                client.put(f"/api/admin/curated/lists/{lid}/items/{iid}/class", json={"source_class": "preprint"}, headers=KEY),
                client.post(f"/api/admin/curated/lists/{lid}/approve", headers=KEY)]
    assert [a.status_code for a in attempts] == [409] * 4
    assert fake.store[lid]["list_hash"] == r.json()["list_hash"]
    assert client.get(f"/api/admin/curated/lists/{lid}", headers=KEY).json()["items"] == frozen["items"]


def test_the_hash_changes_when_a_draft_is_edited_before_approval(env):
    fake, canned = env
    a, b = ready_list(canned), ready_list(canned)
    iid = fake.store[b]["items"][0]["item_id"]
    client.delete(f"/api/admin/curated/lists/{b}/items/{iid}", headers=KEY)
    add(b, canned, {"d": [item(cs.PREPRINT, 7)]})
    ha = client.post(f"/api/admin/curated/lists/{a}/approve", headers=KEY).json()["list_hash"]
    hb = client.post(f"/api/admin/curated/lists/{b}/approve", headers=KEY).json()["list_hash"]
    assert ha != hb


def test_a_failed_approval_writes_nothing(env):
    fake, canned = env
    lid = new_list()
    add(lid, canned, {"a": [item(cs.PREPRINT, 1)]})
    before = dict(fake.store[lid])
    assert client.post(f"/api/admin/curated/lists/{lid}/approve", headers=KEY).status_code == 422
    after = fake.store[lid]
    assert (after["status"], after["list_hash"], after["items"]) == (before["status"], before["list_hash"], before["items"])


# --- reading ---------------------------------------------------------------------------------------------------------------------------------
def test_reading_a_list_shows_the_minimum_status(env):
    fake, canned = env
    lid = new_list()
    add(lid, canned, {"a": [item(cs.PREPRINT, 1)]})
    doc = client.get(f"/api/admin/curated/lists/{lid}", headers=KEY).json()
    assert doc["minimum"] == {"required": 3, "met": False, "counts": {**doc["minimum"]["counts"]}} and doc["minimum"]["counts"]["non_commentary"] == 1


def test_the_index_lists_lists_without_their_items(env):
    fake, canned = env
    lid = ready_list(canned)
    r = client.get("/api/admin/curated/lists", headers=KEY).json()["lists"]
    assert len(r) == 1 and r[0]["list_id"] == lid and r[0]["items"] == 3 and "items_detail" not in r[0]


# --- no logging of what Gary pastes -----------------------------------------------------------------------------------------------------------
def test_pasted_text_is_not_written_to_the_log(env):
    fake, canned = env
    lid = new_list()
    with patch.object(routes, "structured_logger") as log:
        add(lid, canned, {"https://example.org/very-private-looking-link": [refused("https://example.org/very-private-looking-link")]})
    assert "very-private-looking-link" not in repr(log.mock_calls)


# --- generating one private episode from an approved list ---------------------------------------------------------------------------------
from endpoints.curated.routes import GenerateCuratedEpisode  # noqa: E402
import curated_mode  # noqa: E402


class FakeService:
    def __init__(self, db_, fail=None):
        self.calls, self.db, self.fail = [], db_, fail

    async def run_curated_generation_job(self, job_id, list_doc, request, subscriber_id=None):
        self.calls.append({"job_id": job_id, "list_id": list_doc["list_id"], "topic": request.topic, "category": request.category,
                           "duration": request.duration, "subscriber_id": subscriber_id})
        job = self.db.other["podcast_jobs"][job_id]
        job.update({"status": self.fail or "completed", "error_type": "curated_check_failed" if self.fail else None,
                    "curated_run": {"mode": "curated_sources", "published": False}})
        self.db.other["podcast_jobs"][job_id] = job


def approved_list(fake, canned):
    lid = ready_list(canned)
    assert client.post(f"/api/admin/curated/lists/{lid}/approve", headers=KEY).status_code == 200
    return lid


@pytest.fixture
def gen_env(env):
    fake, canned = env
    service = FakeService(fake)
    with patch.object(routes, "_get_service", return_value=service), patch.object(routes, "resolve_generation_subscriber_id", return_value="admin-id"):
        yield fake, canned, service


def generate(lid, **body):
    return client.post("/api/admin/curated/generate", json={"list_id": lid, **body}, headers=KEY)


def test_generation_makes_one_private_job_from_an_approved_list_and_publishes_nothing(gen_env):
    fake, canned, service = gen_env
    lid = approved_list(fake, canned)
    fake.store[lid]["topic"] = "OpenAI mathematics release"
    r = generate(lid, duration="15-20 minutes")
    assert r.status_code == 200 and r.json()["published"] is False and r.json()["status"] == "completed"
    jid = r.json()["job_id"]
    job = fake.other["podcast_jobs"][jid]
    assert job["submitted_to_rss"] is False and job["mode"] == "curated_sources" and job["curated_list_id"] == lid and job["subscriber_id"] == "admin-id"
    assert service.calls == [{"job_id": jid, "list_id": lid, "topic": "OpenAI mathematics release", "category": "Mathematics",
                              "duration": "15-20 minutes", "subscriber_id": "admin-id"}]
    assert fake.store[lid]["jobs"] == [jid]


def test_generation_refuses_a_list_that_is_not_approved_or_has_changed_before_any_job_exists(gen_env):
    fake, canned, service = gen_env
    draft = new_list()
    r = generate(draft)
    assert r.status_code == 409 and "not approved" in r.json()["detail"]
    lid = approved_list(fake, canned)
    fake.store[lid]["items"][0]["title"] = "edited after approval"
    r = generate(lid)
    assert r.status_code == 409 and "no longer matches" in r.json()["detail"]
    assert service.calls == [] and fake.other.get("podcast_jobs", {}) == {}


def test_generation_for_an_unknown_list_or_without_a_service(gen_env):
    fake, canned, service = gen_env
    assert generate("nope").status_code == 404
    lid = approved_list(fake, canned)
    with patch.object(routes, "_get_service", return_value=None):
        assert generate(lid).status_code == 503
    assert fake.other.get("podcast_jobs", {}) == {}


def test_a_failed_generation_is_reported_with_its_error_type_and_still_not_published(gen_env):
    fake, canned, service = gen_env
    lid = approved_list(fake, canned)
    service.fail = "failed"
    r = generate(lid)
    assert r.status_code == 200 and r.json()["status"] == "failed" and r.json()["error_type"] == "curated_check_failed" and r.json()["published"] is False


def test_the_request_is_bounded(gen_env):
    assert client.post("/api/admin/curated/generate", json={}, headers=KEY).status_code == 422
    assert client.post("/api/admin/curated/generate", json={"list_id": ""}, headers=KEY).status_code == 422
    assert client.post("/api/admin/curated/generate", json={"list_id": "x", "duration": "x" * 41}, headers=KEY).status_code == 422
