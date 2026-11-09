"""Dashboard fixes (Gary, 2026-11-06), change 3: an owner may delete their own episode, private or public, except one in the podcast feed.

What the OLD route did (recorded in the PR; the first tests below pin the new behaviour against it): the dashboard sends the episode id for a finished episode, the
old route looked that id up as a JOB id and crashed (500) without deleting anything; sent a job id it deleted the job and episode records and the owner's count, touched
no media (public or private), wrote no audit, had no feed check and no private-access gate, and turned every 404/403 into a 500.

The rule now: the same gate as Play (owner with private-episode access, or the admin key; anyone else gets 404); an episode in the feed is refused (409); a public
episode is hidden, its public files removed, then its PRIVATE files (Gary, 2026-11-09), then its records; a failure to remove any file keeps the records
(hidden) and can be run again; audited as owner_delete; the admin path is unchanged (records only). Offline: an in-memory Firestore and fake buckets."""
from pathlib import Path

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

import media_store as ms
from tests.fakes_pr1 import FakeDB, passthrough_transactional, subscriber
from tests.unit.test_media_store import FakeClient, files
from utils import onboarding as ob

REPO = Path(__file__).resolve().parents[2]
ADMIN = {"X-Admin-API-Key": "test-key"}
A, B = "sub-a", "sub-b"
TOK_A, TOK_B = "token-a", "token-b"
HA, HB = {"X-Subscriber-Token": TOK_A}, {"X-Subscriber-Token": TOK_B}
PRIV, PUB, FEED, B_EP = "ever-math-990001", "ever-math-990002", "ever-math-990003", "ever-math-990004"
JOBS = {PRIV: "job-priv", PUB: "job-pub", FEED: "job-feed", B_EP: "job-b"}
REFUSAL = "This episode is in the podcast feed; ask the editors to remove it."


def build_db(allow=(A, B)):
    eps = {PRIV: {"title": "P", "subscriber_id": A, "submitted_to_rss": False, "visible_on_web": False},
           PUB: {"title": "U", "subscriber_id": A, "submitted_to_rss": False, "visible_on_web": True},
           FEED: {"title": "F", "subscriber_id": A, "submitted_to_rss": True, "visible_on_web": True},
           B_EP: {"title": "B", "subscriber_id": B, "submitted_to_rss": False, "visible_on_web": False}}
    jobs = {JOBS[e]: {"subscriber_id": eps[e]["subscriber_id"], "status": "completed", "result": {"canonical_filename": e}} for e in eps}
    jobs["job-failed"] = {"subscriber_id": A, "status": "failed"}
    return FakeDB(subscribers={A: subscriber(TOK_A, can_generate=True, podcasts_generated=5), B: subscriber(TOK_B, can_generate=True, podcasts_generated=5)},
                  episodes=eps, podcast_jobs=jobs, system_config={"private_episode_access": {"allowed_subscriber_ids": list(allow)}})


def build_storage():
    c = FakeClient()
    for eid in (PRIV, B_EP):
        for n in files(eid):
            c.buckets[ms.PRIVATE_BUCKET].add(n, f"{n}-bytes".encode())
    for eid in (PUB, FEED):                                       # promoted: a private original and a public copy of each file
        for n in files(eid):
            c.buckets[ms.PRIVATE_BUCKET].add(n, f"{n}-bytes".encode())
            c.buckets[ms.PUBLIC_BUCKET].add(n, f"{n}-bytes".encode())
    return c


@pytest.fixture
def env(monkeypatch):
    import config.database
    import utils.auth as auth
    import utils.generation_quota as gq
    from endpoints.admin import routes as admin_routes
    from endpoints.public import routes as public_routes
    from endpoints.subscriber import episode_access as owner_routes
    from endpoints.subscriber import routes as sub_routes
    db, storage = build_db(), build_storage()
    for mod in (admin_routes, public_routes, owner_routes, sub_routes, config.database):
        monkeypatch.setattr(mod, "db", db)
    monkeypatch.setattr(auth, "get_admin_api_key", lambda: "test-key")
    monkeypatch.setattr(ms, "_client", lambda client=None: client or storage)
    monkeypatch.setattr(ms, "_signing_kwargs", lambda: {})
    monkeypatch.setattr(gq.firestore, "transactional", passthrough_transactional)
    app = FastAPI()
    for r in (sub_routes.router, owner_routes.router, public_routes.router, admin_routes.router):
        app.include_router(r)
    return type("Env", (), {"db": db, "storage": storage, "client": TestClient(app), "pub": storage.buckets[ms.PUBLIC_BUCKET], "priv": storage.buckets[ms.PRIVATE_BUCKET]})()


def delete(env, ident, headers=HA):
    return env.client.delete(f"/api/subscribers/podcasts/{ident}", headers=headers)


def audits(env):
    return [a for a in env.db.data.get("episode_audit", {}).values() if a["action"] == "owner_delete"]


def snapshot(env):
    return ({k: dict(v) for k, v in env.db.data["episodes"].items()}, {k: dict(v) for k, v in env.db.data["podcast_jobs"].items()},
            set(env.pub.store), set(env.priv.store), dict(env.db.data.get("episode_audit", {})))


# ---- an owner deletes a private episode -------------------------------------------------------------------------------------------------------
@pytest.mark.parametrize("ident", [PRIV, JOBS[PRIV]], ids=["by episode id (what the dashboard sends)", "by job id"])
def test_an_owner_deletes_a_private_episode(env, ident):
    r = delete(env, ident)
    assert r.status_code == 200 and r.json() == {"message": "Podcast deleted successfully"}
    assert PRIV not in env.db.data["episodes"] and JOBS[PRIV] not in env.db.data["podcast_jobs"]
    assert env.db.data["subscribers"][A]["podcasts_generated"] == 4
    assert not {n for n in env.priv.store if PRIV in n}                          # the private media goes too: "permanently" is true
    assert env.pub.store.keys().isdisjoint(files(PRIV))
    [a] = audits(env)
    assert a["episode_id"] == PRIV and a["actor"] == f"owner:{A}" and a["was_public"] is False and a["public_files_removed"] == 0 and a["private_files_removed"] == len(files(PRIV)) and a["job_id"] == JOBS[PRIV]


def test_other_episodes_and_files_are_untouched(env):
    delete(env, PRIV)
    for e in (PUB, FEED, B_EP):
        assert e in env.db.data["episodes"] and JOBS[e] in env.db.data["podcast_jobs"]
    assert {n for n in env.pub.store if PUB in n} == set(files(PUB)) and {n for n in env.pub.store if FEED in n} == set(files(FEED))
    assert {n for n in env.priv.store if B_EP in n} == set(files(B_EP))


# ---- an owner deletes a public episode that is not in the feed ----------------------------------------------------------------------------------
def test_an_owner_deletes_a_public_episode_not_in_the_feed_and_its_public_copies_go(env):
    assert env.client.get(f"/api/episodes/{PUB}").status_code == 200                # public before
    r = delete(env, PUB)
    assert r.status_code == 200
    assert PUB not in env.db.data["episodes"] and JOBS[PUB] not in env.db.data["podcast_jobs"]
    assert env.pub.store.keys().isdisjoint(files(PUB))                              # every public copy is gone
    assert not {n for n in env.priv.store if PUB in n}                              # nor is a private original left behind
    [a] = audits(env)
    assert a["episode_id"] == PUB and a["was_public"] is True and a["public_files_removed"] == len(files(PUB)) and a["private_files_removed"] == len(files(PUB)) and a["actor"] == f"owner:{A}"


def test_the_public_page_and_record_are_404_afterwards_allowing_the_60_second_cache(env):
    delete(env, PUB)
    assert env.client.get(f"/api/episodes/{PUB}").status_code == 404                # the record the page is built from
    assert env.client.get(f"/api/subscribers/episodes/{PUB}/media-links", headers=HA).status_code == 404
    page = (REPO / "api" / "episodes" / "[episodeId].js").read_text(encoding="utf-8")
    assert "s-maxage=60, stale-while-revalidate=15" in page                         # so a cached page leaves the CDN within about a minute
    assert "res.setHeader('Cache-Control', 'public, max-age=0, s-maxage=60, stale-while-revalidate=15')" in page


def test_the_episode_is_hidden_before_its_files_are_removed(env):
    seen = {}
    pub_blob = env.pub.store[f"audio/{PUB}.mp3"]
    original = pub_blob.delete

    def spy():
        seen["visible_when_first_file_deleted"] = env.db.data["episodes"][PUB]["visible_on_web"]
        original()
    pub_blob.delete = spy
    delete(env, PUB)
    assert seen["visible_when_first_file_deleted"] is False


# ---- an episode in the feed is refused -------------------------------------------------------------------------------------------------------
@pytest.mark.parametrize("ident", [FEED, JOBS[FEED]])
def test_an_episode_in_the_feed_is_refused_with_409_and_nothing_changes(env, ident):
    before = snapshot(env)
    r = delete(env, ident)
    assert r.status_code == 409 and r.json() == {"detail": REFUSAL}
    assert snapshot(env) == before                                                  # no record, file, count or audit changed
    assert env.db.data["subscribers"][A]["podcasts_generated"] == 5


def test_a_non_owner_never_learns_an_episode_is_in_the_feed(env):
    r = delete(env, FEED, HB)
    assert r.status_code == 404 and "feed" not in r.text.lower()


# ---- everyone else gets 404 -----------------------------------------------------------------------------------------------------------------
def test_anyone_who_is_not_the_owner_gets_the_same_404_and_nothing_changes(env):
    missing = delete(env, "ever-math-000000")
    assert missing.status_code == 404
    before = snapshot(env)
    for ident in (PRIV, JOBS[PRIV], PUB):
        for headers in (HB, {}, {"X-Subscriber-Token": "garbage"}, {"X-Admin-API-Key": "wrong"}):
            r = delete(env, ident, headers)
            assert r.status_code == 404 and r.json() == missing.json(), (ident, headers)
    assert snapshot(env) == before


# ---- the PR 1 gate, applied the way Play applies it ----------------------------------------------------------------------------------------------
def test_an_owner_who_is_not_allowed_private_access_gets_404_just_as_play_does(env):
    env.db.data["system_config"]["private_episode_access"]["allowed_subscriber_ids"] = []
    assert env.client.get(f"/api/subscribers/episodes/{PRIV}/media-links", headers=HA).status_code == 404       # Play
    before = snapshot(env)
    assert delete(env, PRIV).status_code == 404 and delete(env, PUB).status_code == 404
    assert snapshot(env) == before


def test_an_active_member_of_an_engine_with_the_flag_on_passes_the_gate_and_one_without_does_not(env):
    env.db.data["system_config"]["private_episode_access"]["allowed_subscriber_ids"] = []
    env.db.data["onboarding_engines"] = {"x": {"label": "X", "state": "open"}}
    env.db.data["onboarding_members"] = {ob.member_id("x", A): {"engine_id": "x", "subscriber_id": A, "role": "owner", "status": "active"}}
    assert delete(env, PRIV).status_code == 404                                    # engine flag absent: off
    env.db.data["onboarding_engines"]["x"]["private_access_enabled"] = True
    assert delete(env, PRIV).status_code == 200                                    # engine flag on: on, exactly as for Play
    env.db.data["onboarding_members"][ob.member_id("x", A)]["status"] = "removed"
    assert delete(env, PUB).status_code == 404                                     # revoked: off again


def test_a_failed_job_with_no_episode_can_be_deleted_by_its_owner(env):
    r = delete(env, "job-failed")
    assert r.status_code == 200 and "job-failed" not in env.db.data["podcast_jobs"] and env.db.data["subscribers"][A]["podcasts_generated"] == 4
    [a] = audits(env)
    assert a["episode_id"] == "job-failed" and a["was_public"] is False and a["public_files_removed"] == 0


# ---- failure handling ------------------------------------------------------------------------------------------------------------------------
def test_a_public_file_that_cannot_be_removed_keeps_the_records_hides_the_episode_and_can_be_run_again(env):
    stuck = env.pub.store[f"audio/{PUB}.mp3"]
    stuck.delete = lambda: (_ for _ in ()).throw(RuntimeError("storage error"))
    r = delete(env, PUB)
    assert r.status_code == 500 and "try again" in r.json()["detail"]
    assert PUB in env.db.data["episodes"] and JOBS[PUB] in env.db.data["podcast_jobs"]           # nothing else was deleted
    assert env.db.data["episodes"][PUB]["visible_on_web"] is False                                # but it is hidden
    assert env.client.get(f"/api/episodes/{PUB}").status_code == 404
    assert audits(env) == [] and env.db.data["subscribers"][A]["podcasts_generated"] == 5
    del stuck.delete                                                                             # storage recovers
    assert delete(env, PUB).status_code == 200 and env.pub.store.keys().isdisjoint(files(PUB)) and PUB not in env.db.data["episodes"]


def test_a_private_file_that_cannot_be_removed_keeps_the_records_hidden_and_can_be_run_again(env):
    stuck = env.priv.store[f"audio/{PUB}.mp3"]
    stuck.delete = lambda: (_ for _ in ()).throw(RuntimeError("storage error"))
    r = delete(env, PUB)
    assert r.status_code == 500 and "try again" in r.json()["detail"]
    assert env.pub.store.keys().isdisjoint(files(PUB))                                           # the public copies had already gone (the order)
    assert PUB in env.db.data["episodes"] and JOBS[PUB] in env.db.data["podcast_jobs"]           # the records stay
    assert env.db.data["episodes"][PUB]["visible_on_web"] is False and env.client.get(f"/api/episodes/{PUB}").status_code == 404
    assert audits(env) == [] and env.db.data["subscribers"][A]["podcasts_generated"] == 5
    del stuck.delete
    assert delete(env, PUB).status_code == 200 and not {n for n in env.priv.store if PUB in n} and PUB not in env.db.data["episodes"]


def test_the_private_copies_are_removed_after_the_public_ones_and_before_the_records(env):
    order = []
    for kind, store in (("public", env.pub.store), ("private", env.priv.store)):
        blob = store[f"audio/{PUB}.mp3"]
        orig = blob.delete
        blob.delete = (lambda o, k: (lambda: (order.append((k, PUB in env.db.data["episodes"])), o())))(orig, kind)
    assert delete(env, PUB).status_code == 200
    assert order == [("public", True), ("private", True)]                                        # public first; the record still existed for both
    assert PUB not in env.db.data["episodes"]


def test_the_admin_delete_still_touches_no_media(env):
    before = (set(env.pub.store), set(env.priv.store))
    assert delete(env, PRIV, ADMIN).status_code == 200
    assert (set(env.pub.store), set(env.priv.store)) == before


def test_an_audit_that_cannot_be_written_does_not_undo_the_delete(env, monkeypatch):
    import utils.owner_access as oa
    monkeypatch.setattr(oa, "write_audit", lambda *a, **k: (_ for _ in ()).throw(RuntimeError("audit down")))
    r = delete(env, PRIV)
    assert r.status_code == 200 and PRIV not in env.db.data["episodes"]


# ---- the admin path is unchanged ---------------------------------------------------------------------------------------------------------------
def test_the_admin_key_deletes_records_only_with_no_media_no_feed_check_and_no_audit(env):
    before_pub = set(env.pub.store)
    r = delete(env, JOBS[FEED], ADMIN)                      # a FEED episode: the admin path has never refused it
    assert r.status_code == 200 and FEED not in env.db.data["episodes"] and JOBS[FEED] not in env.db.data["podcast_jobs"]
    assert set(env.pub.store) == before_pub and audits(env) == []
    assert env.db.data["subscribers"][A]["podcasts_generated"] == 4
    assert delete(env, PRIV, ADMIN).status_code == 200      # and by episode id, which used to crash
    assert delete(env, "nope", ADMIN).status_code == 404    # a missing podcast is an honest 404, not a 500


# ---- the page --------------------------------------------------------------------------------------------------------------------------------
def test_the_dashboard_asks_before_deleting_with_the_agreed_words():
    html = (REPO / "public" / "subscriber-dashboard.html").read_text(encoding="utf-8")
    assert "Delete this episode permanently? This can't be undone." in html
    assert "Are you sure you want to delete this podcast? This action cannot be undone." not in html
