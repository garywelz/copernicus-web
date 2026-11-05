"""Onboarding PR 1 (design 7, 8.1): owner access to private episodes, make-public, admin unpublish, quota admin and refund, fix-missing-titles.

Everything is offline: an in-memory Firestore (tests/fakes_pr1.py), fake storage buckets (the ones from test_media_store), a mocked clock for link expiry.
No test waits; none touches the network."""
from datetime import datetime, timedelta, timezone
from unittest.mock import patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

import media_store as ms
from tests.fakes_pr1 import FakeDB, passthrough_transactional, subscriber
from tests.unit.test_media_store import FakeClient, files

ADMIN = {"X-Admin-API-Key": "test-key"}
EID = "ever-math-990001"          # A's private episode
EID_B = "ever-math-990002"        # B's private episode
PUBLIC_EID = "ever-math-990003"   # an old public episode (feed)
A, B = "sub-a", "sub-b"
TOK_A, TOK_B = "token-for-a", "token-for-b"
HA = {"X-Subscriber-Token": TOK_A}
HB = {"X-Subscriber-Token": TOK_B}


def episode(owner, **extra):
    return {"title": "T", "subscriber_id": owner, "submitted_to_rss": False, "visible_on_web": False, **extra}


def build_db(allow=(A, B)):
    return FakeDB(
        subscribers={A: subscriber(TOK_A, can_generate=True, monthly_quota=10), B: subscriber(TOK_B, can_generate=True, monthly_quota=10)},
        episodes={EID: episode(A), EID_B: episode(B), PUBLIC_EID: episode(A, submitted_to_rss=True)},
        system_config={"private_episode_access": {"allowed_subscriber_ids": list(allow)}},
    )


def build_client():
    c = FakeClient()
    for eid in (EID, EID_B):
        for n in files(eid):
            c.buckets[ms.PRIVATE_BUCKET].add(n, f"{n}-bytes".encode())
    return c


@pytest.fixture
def env(monkeypatch):
    """The app, a fake Firestore, fake buckets and the admin key, wired together."""
    from endpoints.admin import routes as admin_routes
    from endpoints.public import routes as public_routes
    from endpoints.subscriber import episode_access as owner_routes
    import config.database
    import utils.auth as auth
    import utils.generation_quota as gq
    db, storage = build_db(), build_client()
    for mod in (admin_routes, public_routes, owner_routes, config.database):
        monkeypatch.setattr(mod, "db", db)
    monkeypatch.setattr(auth, "get_admin_api_key", lambda: "test-key")
    monkeypatch.setattr(ms, "_client", lambda client=None: client or storage)
    monkeypatch.setattr(ms, "_signing_kwargs", lambda: {})
    monkeypatch.setattr(gq.firestore, "transactional", passthrough_transactional)
    app = FastAPI()
    for r in (owner_routes.router, admin_routes.router, public_routes.router):
        app.include_router(r)
    return type("Env", (), {"db": db, "storage": storage, "client": TestClient(app), "app": app})()


# ---- the view rule (design 7.1) -----------------------------------------------------------------------------------------------------------
def test_owner_ok_and_can_view_rules():
    from utils.episode_access import can_view, owner_ok
    rec = episode(A)
    assert owner_ok(rec, A) and not owner_ok(rec, B) and not owner_ok(rec, None) and not owner_ok(None, A) and not owner_ok({"title": "x"}, A)
    assert can_view(rec, None, A) and not can_view(rec, None, B) and not can_view(rec, None)
    assert can_view(episode(B, submitted_to_rss=True), None)            # a public episode is visible to anyone


# ---- 1/2. owner media links ---------------------------------------------------------------------------------------------------------------
def test_media_links_owner_other_signed_out_admin_and_missing(env):
    url = f"/api/subscribers/episodes/{EID}/media-links"
    owner = env.client.get(url, headers=HA)
    assert owner.status_code == 200 and owner.headers["cache-control"] == "no-store"
    assert env.client.get(url, headers=HB).status_code == 404                     # another signed-in user
    assert env.client.get(url).status_code == 404                                 # signed out
    assert env.client.get(url, headers={"X-Subscriber-Token": "garbage"}).status_code == 404
    assert env.client.get(url, headers={"X-Admin-API-Key": "wrong"}).status_code == 404
    assert env.client.get(url, headers=ADMIN).status_code == 200                  # admin
    assert env.client.get("/api/subscribers/episodes/no-such-episode/media-links", headers=HA).status_code == 404
    # the answers for "exists but not yours" and "does not exist" are the same, so nothing is revealed
    assert env.client.get(url, headers=HB).json() == env.client.get("/api/subscribers/episodes/no-such-episode/media-links", headers=HB).json()


def test_media_links_offer_only_audio_and_artwork_as_signed_links(env):
    body = env.client.get(f"/api/subscribers/episodes/{EID}/media-links", headers=HA).json()
    names = set(body["links"])
    assert names == {f"audio/{EID}.mp3", f"thumbnails/{EID}-thumb.jpg", f"episode-images/{EID}-image-1.jpg", f"episode-images/{EID}-image-2.jpg"}
    assert all(u.startswith("signed://") for u in body["links"].values()) and body["media_state"] == "private"
    assert not any("transcripts/" in n or "animations/" in n or "videos/" in n for n in names)
    assert all(EID_B not in n for n in names)                                      # nothing of another episode


def test_links_are_minted_fresh_on_every_call_and_never_public_urls(env):
    env.client.get(f"/api/subscribers/episodes/{EID}/media-links", headers=HA)
    env.client.get(f"/api/subscribers/episodes/{EID}/media-links", headers=HA)
    signed = env.storage.buckets[ms.PRIVATE_BUCKET].signed
    audio_signings = [s for s in signed if s[0] == f"audio/{EID}.mp3"]
    assert len(audio_signings) == 2                                                # one signing per call: nothing cached or reused
    assert env.storage.buckets[ms.PUBLIC_BUCKET].store == {}                      # asking for links never copies anything public


def test_default_lifetime_is_15_minutes_and_60_is_the_ceiling(env):
    env.client.get(f"/api/subscribers/episodes/{EID}/media-links", headers=HA)
    assert {int(kw["expiration"].total_seconds()) for _, kw in env.storage.buckets[ms.PRIVATE_BUCKET].signed} == {900}
    assert env.client.get(f"/api/subscribers/episodes/{EID}/media-links?minutes=60", headers=HA).json()["expires_in_seconds"] == 3600
    assert env.client.get(f"/api/subscribers/episodes/{EID}/media-links?minutes=61", headers=HA).status_code == 422
    assert env.client.get(f"/api/subscribers/episodes/{EID}/media-links?minutes=0", headers=HA).status_code == 422
    assert env.client.get(f"/api/subscribers/episodes/{EID}/media-links?minutes=1", headers=HA).json()["expires_in_seconds"] == 60


def test_a_link_expires_after_15_minutes_by_a_mocked_clock(env):
    t0 = datetime(2026, 11, 5, 12, 0, 0, tzinfo=timezone.utc)
    out = ms.owner_media_links(EID, now=lambda: t0, client=env.storage, signer=lambda: {})
    assert out["minutes"] == 15 and out["expires_at"] == (t0 + timedelta(minutes=15)).isoformat()
    assert not ms.link_expired(out["expires_at"], now=lambda: t0 + timedelta(minutes=14, seconds=59))
    assert ms.link_expired(out["expires_at"], now=lambda: t0 + timedelta(minutes=15, seconds=1))
    with patch.object(ms, "_now", return_value=t0):                                # the same, through the module clock
        again = ms.owner_media_links(EID, client=env.storage, signer=lambda: {})
    assert again["expires_at"] == out["expires_at"]
    # the lifetime the storage service is asked to enforce is the same 15 minutes (the real expiry is enforced by Cloud Storage, not by this code)
    assert {int(kw["expiration"].total_seconds()) for _, kw in env.storage.buckets[ms.PRIVATE_BUCKET].signed} == {900}


def test_owner_not_on_the_allow_list_gets_404_and_the_gate_fails_closed(env):
    url = f"/api/subscribers/episodes/{EID}/media-links"
    env.db.data["system_config"]["private_episode_access"] = {"allowed_subscriber_ids": [B]}
    assert env.client.get(url, headers=HA).status_code == 404                     # A is not listed
    assert env.client.post(f"/api/subscribers/episodes/{EID}/make-public", json={"confirm_irreversible": True}, headers=HA).status_code == 404
    assert env.client.get(url, headers=ADMIN).status_code == 200                  # admin is never gated
    env.db.data["system_config"].clear()                                          # no config document at all
    assert env.client.get(url, headers=HA).status_code == 404
    env.db.data["system_config"]["private_episode_access"] = {"enabled_for_all": True}
    assert env.client.get(url, headers=HA).status_code == 200


def test_the_api_record_follows_the_same_view_rule(env):
    url = f"/api/episodes/{EID}"
    assert env.client.get(url, headers=HA).status_code == 200                     # owner
    assert env.client.get(url, headers=HB).status_code == 404                     # other signed-in user
    assert env.client.get(url).status_code == 404                                 # signed out
    assert env.client.get(url, headers=ADMIN).status_code == 200                  # admin
    assert env.client.get(f"/api/episodes/{PUBLIC_EID}").status_code == 200       # public: unchanged, no credential needed
    assert env.client.get(f"/api/episodes/{PUBLIC_EID}", headers=HB).status_code == 200


def test_the_catalog_list_and_search_do_not_show_private_episodes_to_an_owner(env):
    for e in (EID, EID_B, PUBLIC_EID):
        env.db.data["episodes"][e]["generated_at"] = "2026-11-01"
    ids = [e["episode_id"] for e in env.client.get("/api/episodes", headers=HA).json()["episodes"]]
    assert ids == [PUBLIC_EID]                                                    # unchanged: only the admin key widens the list


# ---- 3. make public -----------------------------------------------------------------------------------------------------------------------
def make_public(env, eid=EID, headers=HA, body=None):
    return env.client.post(f"/api/subscribers/episodes/{eid}/make-public", json={"confirm_irreversible": True} if body is None else body, headers=headers)


def test_make_public_by_the_owner_copies_verified_files_and_flips_the_record(env):
    r = make_public(env)
    assert r.status_code == 200 and r.json()["visible_on_web"] is True and r.json()["in_feed"] is False
    pub, priv = env.storage.buckets[ms.PUBLIC_BUCKET].store, env.storage.buckets[ms.PRIVATE_BUCKET].store
    assert set(pub) == set(files(EID))                                             # exactly this episode's files, nothing of the other
    assert all(pub[n].md5_hash == priv[n].md5_hash and pub[n].crc32c == priv[n].crc32c and pub[n].size == priv[n].size for n in pub)
    rec = env.db.data["episodes"][EID]
    assert rec["visible_on_web"] is True and rec["media_state"] == "public" and rec["submitted_to_rss"] is False
    assert env.client.get(f"/api/episodes/{EID}").status_code == 200              # now readable by anyone
    audit = list(env.db.data["episode_audit"].values())
    assert len(audit) == 1 and audit[0]["action"] == "make_public" and audit[0]["actor"] == f"owner:{A}" and audit[0]["episode_id"] == EID


def test_make_public_never_touches_the_feed(env):
    make_public(env)
    assert {c for c, _, _ in env.db.writes} <= {"episodes", "episode_audit"}      # no feed, job or subscriber write
    assert env.db.data["episodes"][EID]["submitted_to_rss"] is False
    ids_before = sorted(e["episode_id"] for e in env.client.get("/api/episodes?submitted=true").json()["episodes"])
    assert ids_before == [PUBLIC_EID]                                              # the feed list is the same as before: the new episode is not in it
    assert "submit-to-rss" not in " ".join(r.path for r in __import__("endpoints.subscriber.episode_access", fromlist=["router"]).router.routes)


def test_make_public_is_refused_for_everyone_else_and_changes_nothing(env):
    for headers in (HB, {}, {"X-Subscriber-Token": "garbage"}):
        assert make_public(env, headers=headers).status_code == 404
    assert make_public(env, eid="no-such-episode").status_code == 404
    assert env.storage.buckets[ms.PUBLIC_BUCKET].store == {} and env.db.writes == []


def test_make_public_needs_the_explicit_irreversible_confirmation(env):
    for body in ({}, {"confirm_irreversible": False}, {"confirm_irreversible": "yes"}):
        r = make_public(env, body=body)
        assert r.status_code == 400 and "only the site administrator" in r.json()["detail"]
    assert env.storage.buckets[ms.PUBLIC_BUCKET].store == {} and env.db.writes == []


def test_make_public_rolls_back_the_copies_when_the_record_write_fails(env):
    env.db.fail_set_on = {"episodes"}
    with pytest.raises(RuntimeError):
        make_public(env)
    assert env.storage.buckets[ms.PUBLIC_BUCKET].store == {}                      # every copy removed again
    assert env.db.data["episodes"][EID]["visible_on_web"] is False
    assert len(env.storage.buckets[ms.PRIVATE_BUCKET].store) == 2 * len(files(EID))


def test_make_public_on_an_already_public_episode_is_a_no_op(env):
    r = make_public(env, eid=PUBLIC_EID)
    assert r.status_code == 200 and r.json()["already_public"] is True
    assert env.db.writes == [] and env.storage.buckets[ms.PUBLIC_BUCKET].store == {}


def test_the_owner_cannot_make_a_public_episode_private(env):
    make_public(env)
    for path in (f"/api/admin/episodes/{EID}/unpublish",):
        for headers in (HA, HB, {}):
            r = env.client.post(path, json={"reason": "I changed my mind"}, headers=headers)
            assert r.status_code in (401, 403), r.status_code
    assert env.db.data["episodes"][EID]["visible_on_web"] is True
    owner_paths = [r.path for r in __import__("endpoints.subscriber.episode_access", fromlist=["router"]).router.routes]
    assert not any(w in p for p in owner_paths for w in ("private", "unpublish", "hide", "withdraw"))   # the owner router has no way back


# ---- 4. admin unpublish -------------------------------------------------------------------------------------------------------------------
def published(env):
    make_public(env)
    env.db.writes.clear()
    env.db.data["episode_audit"].clear()


def test_unpublish_removes_public_copies_keeps_private_ones_and_writes_the_audit(env):
    published(env)
    r = env.client.post(f"/api/admin/episodes/{EID}/unpublish", json={"reason": "owner asked for it back"}, headers=ADMIN)
    assert r.status_code == 200 and r.json()["files_removed"] == len(files(EID)) and r.json()["private_copies_untouched"] and r.json()["feed_untouched"]
    assert env.storage.buckets[ms.PUBLIC_BUCKET].store == {}                      # checksums gone with the files
    assert set(env.storage.buckets[ms.PRIVATE_BUCKET].store) >= set(files(EID))   # private copies intact
    rec = env.db.data["episodes"][EID]
    assert rec["visible_on_web"] is False and rec["media_state"] == "private" and rec["submitted_to_rss"] is False
    assert env.client.get(f"/api/episodes/{EID}").status_code == 404             # private again for the public
    assert env.client.get(f"/api/episodes/{EID}", headers=HA).status_code == 200   # still the owner's
    audit = list(env.db.data["episode_audit"].values())
    assert len(audit) == 1
    a = audit[0]
    assert a["action"] == "unpublish" and a["episode_id"] == EID and a["reason"] == "owner asked for it back" and a["actor"] == "admin-key"
    assert a["files_removed"] == len(files(EID)) and a["files_failed"] == 0 and datetime.fromisoformat(a["at"])
    assert {c for c, _, _ in env.db.writes} <= {"episodes", "episode_audit"}      # no feed write


def test_unpublish_needs_the_admin_key_and_a_reason(env):
    published(env)
    assert env.client.post(f"/api/admin/episodes/{EID}/unpublish", json={"reason": "valid reason"}).status_code in (401, 403)
    assert env.client.post(f"/api/admin/episodes/{EID}/unpublish", json={"reason": "valid reason"}, headers={"X-Admin-API-Key": "wrong"}).status_code in (401, 403)
    assert env.client.post(f"/api/admin/episodes/{EID}/unpublish", json={}, headers=ADMIN).status_code == 422
    assert env.client.post(f"/api/admin/episodes/{EID}/unpublish", json={"reason": "x"}, headers=ADMIN).status_code == 422
    assert env.client.post("/api/admin/episodes/none/unpublish", json={"reason": "valid reason"}, headers=ADMIN).status_code == 404
    assert env.db.data["episodes"][EID]["visible_on_web"] is True and env.db.data["episode_audit"] == {}


def test_unpublish_refuses_an_episode_that_is_in_the_feed_and_leaves_the_feed_alone(env):
    r = env.client.post(f"/api/admin/episodes/{PUBLIC_EID}/unpublish", json={"reason": "valid reason"}, headers=ADMIN)
    assert r.status_code == 409 and "feed" in r.json()["detail"]
    assert env.db.data["episodes"][PUBLIC_EID]["submitted_to_rss"] is True and env.db.writes == []


def test_unpublish_refuses_when_a_public_file_has_no_private_copy_and_removes_nothing(env):
    published(env)
    del env.storage.buckets[ms.PRIVATE_BUCKET].store[f"transcripts/{EID}-transcript.md"]       # an older-style episode: one file exists only in public
    r = env.client.post(f"/api/admin/episodes/{EID}/unpublish", json={"reason": "valid reason"}, headers=ADMIN)
    assert r.status_code == 409
    assert set(env.storage.buckets[ms.PUBLIC_BUCKET].store) == set(files(EID))     # nothing removed
    assert env.db.data["episodes"][EID]["visible_on_web"] is True and env.db.data["episode_audit"] == {}


def test_unpublish_on_a_private_episode_changes_nothing_and_writes_no_audit(env):
    r = env.client.post(f"/api/admin/episodes/{EID}/unpublish", json={"reason": "valid reason"}, headers=ADMIN)
    assert r.status_code == 200 and r.json()["already_private"] is True
    assert env.db.writes == [] and env.db.data.get("episode_audit", {}) == {}


def test_a_partial_unpublish_reports_failure_hides_the_episode_and_can_be_run_again(env):
    published(env)
    pub = env.storage.buckets[ms.PUBLIC_BUCKET]
    stuck = pub.store[f"audio/{EID}.mp3"]
    stuck.delete = lambda: (_ for _ in ()).throw(RuntimeError("storage error"))
    r = env.client.post(f"/api/admin/episodes/{EID}/unpublish", json={"reason": "valid reason"}, headers=ADMIN)
    assert r.status_code == 500 and env.db.data["episodes"][EID]["visible_on_web"] is False
    assert list(env.db.data["episode_audit"].values())[0]["files_failed"] == 1
    del stuck.delete                                                               # storage recovers; the second run removes the rest
    r2 = env.client.post(f"/api/admin/episodes/{EID}/unpublish", json={"reason": "valid reason"}, headers=ADMIN)
    assert r2.status_code == 200 and pub.store == {}


# ---- 5. quota admin -----------------------------------------------------------------------------------------------------------------------
def test_quota_route_reads_sets_raises_clears_and_audits(env):
    url = f"/api/admin/subscribers/{A}/quota"
    assert env.client.get(url, headers=ADMIN).json()["monthly_quota"] == 10
    assert env.client.put(url, json={"monthly_quota": 25}, headers=ADMIN).json() == {"subscriber_id": A, "monthly_quota": 25, "previous": 10}
    assert env.db.data["subscribers"][A]["monthly_quota"] == 25
    assert env.client.put(url, json={"monthly_quota": 0}, headers=ADMIN).status_code == 200 and env.db.data["subscribers"][A]["monthly_quota"] == 0
    assert env.client.put(url, json={"monthly_quota": 200}, headers=ADMIN).status_code == 200
    assert env.client.put(url, json={"monthly_quota": None}, headers=ADMIN).status_code == 200 and env.db.data["subscribers"][A]["monthly_quota"] is None
    assert env.client.get(url, headers=ADMIN).json()["monthly_quota"] is None
    actions = [a for a in env.db.data["episode_audit"].values() if a["action"] == "quota_set"]
    assert len(actions) == 4 and actions[0]["subscriber_id"] == A and actions[0]["previous"] == 10 and actions[0]["current"] == 25 and actions[0]["actor"] == "admin-key"
    assert env.db.data["subscribers"][A]["can_generate"] is True                   # only the quota changed


@pytest.mark.parametrize("bad", [-1, 201, 1.5, "5", True, False, [], {}])
def test_quota_route_refuses_invalid_values(env, bad):
    r = env.client.put(f"/api/admin/subscribers/{A}/quota", json={"monthly_quota": bad}, headers=ADMIN)
    assert r.status_code == 400 and env.db.data["subscribers"][A]["monthly_quota"] == 10


def test_quota_route_is_refused_without_the_admin_key_and_for_unknown_subscribers(env):
    url = f"/api/admin/subscribers/{A}/quota"
    for headers in ({}, {"X-Admin-API-Key": "wrong"}, HA, HB):                    # an owner cannot raise their own quota
        assert env.client.put(url, json={"monthly_quota": 99}, headers=headers).status_code in (401, 403)
        assert env.client.get(url, headers=headers).status_code in (401, 403)
    assert env.client.put(url, json={}, headers=ADMIN).status_code == 422          # the field is required (null means unlimited, absent means a mistake)
    assert env.client.put("/api/admin/subscribers/ghost/quota", json={"monthly_quota": 5}, headers=ADMIN).status_code == 404
    assert env.db.data["subscribers"][A]["monthly_quota"] == 10


# ---- 7. fix-missing-titles ----------------------------------------------------------------------------------------------------------------
def job(owner, **extra):
    return {"subscriber_id": owner, "request": {"topic": f"topic of {owner}"}, "result": {}, **extra}


def test_fix_missing_titles_refuses_an_email_in_the_url_before_reading_anything(env):
    env.db.data["podcast_jobs"] = {"j1": job(A)}
    env.db.collections_read.clear()
    for query in ("subscriber_email=someone@example.org", "subscriber_id=someone@example.org", "subscriber_email=x&subscriber_id=" + A):
        r = env.client.post(f"/api/admin/podcasts/fix-missing-titles?{query}", headers=ADMIN)
        assert r.status_code == 400 and "Email" in r.json()["detail"]
    assert "podcast_jobs" not in env.db.collections_read and env.db.data["podcast_jobs"]["j1"]["result"] == {}


def test_fix_missing_titles_is_admin_key_only(env):
    env.db.data["podcast_jobs"] = {"a1": job(A), "b1": job(B)}
    base = "/api/admin/podcasts/fix-missing-titles"
    for headers in (HA, HB, {}, {"X-Admin-API-Key": "wrong"}):                     # no subscriber token, own or otherwise, is accepted
        assert env.client.post(f"{base}?subscriber_id={A}", headers=headers).status_code in (401, 403)
        assert env.client.post(base, headers=headers).status_code in (401, 403)
    assert env.client.post(f"{base}?subscriber_id={A}", headers=HA).status_code == 401
    assert env.db.data["podcast_jobs"]["a1"]["result"] == {} and env.db.data["podcast_jobs"]["b1"]["result"] == {}
    # the admin key works with an opaque subscriber_id, and without one
    assert env.client.post(f"{base}?subscriber_id={A}", headers=ADMIN).json()["fixed_count"] == 1
    assert env.db.data["podcast_jobs"]["a1"]["result"]["title"] == f"topic of {A}" and env.db.data["podcast_jobs"]["b1"]["result"] == {}
    assert env.client.post(base, headers=ADMIN).json()["fixed_count"] == 1
    assert env.db.data["podcast_jobs"]["b1"]["result"]["title"] == f"topic of {B}"


def test_fix_missing_titles_still_refuses_an_email_for_the_admin_too(env):
    env.db.data["podcast_jobs"] = {"a1": job(A)}
    for q in ("subscriber_email=x@example.org", "subscriber_id=x@example.org"):
        assert env.client.post(f"/api/admin/podcasts/fix-missing-titles?{q}", headers=ADMIN).status_code == 400
    assert env.db.data["podcast_jobs"]["a1"]["result"] == {}


# ---- the feed is editor-only (Q1, Q7) -----------------------------------------------------------------------------------------------------
@pytest.fixture
def feed(env, monkeypatch):
    from unittest.mock import AsyncMock, MagicMock
    from endpoints.subscriber import routes as sub_routes
    monkeypatch.setattr(sub_routes, "db", env.db)
    rss = MagicMock()
    rss.update_rss_feed = AsyncMock()
    monkeypatch.setattr(sub_routes, "rss_service", rss)
    monkeypatch.setattr(sub_routes, "episode_service", MagicMock())
    env.app.include_router(sub_routes.router)
    env.db.data["podcast_jobs"] = {"job1": {"subscriber_id": A, "result": {"canonical_filename": EID}, "status": "completed"}}
    env.rss = rss
    return env


SUBMIT = "/api/subscribers/podcasts/submit-to-rss"


@pytest.mark.parametrize("submit", [True, False])
def test_an_owner_cannot_add_to_or_remove_from_the_feed(feed, submit):
    before = {k: dict(v) for k, v in feed.db.data["episodes"].items()}
    jobs_before = {k: dict(v) for k, v in feed.db.data["podcast_jobs"].items()}
    feed.db.writes.clear()
    feed.db.collections_read.clear()
    for pid in ("job1", EID, "no-such-podcast"):
        for headers in (HA, HB, {}, {"X-Admin-API-Key": "wrong"}):
            r = feed.client.post(SUBMIT, json={"podcast_id": pid, "submit_to_rss": submit}, headers=headers)
            assert r.status_code == 403 and r.json() == {"detail": "The podcast feed is managed by the editors."}, (pid, r.text)
    assert feed.db.writes == [] and feed.db.data["episodes"] == before and feed.db.data["podcast_jobs"] == jobs_before
    assert feed.db.collections_read == []                                          # the key is checked before any Firestore read
    feed.rss.update_rss_feed.assert_not_called()
    assert feed.storage.buckets[ms.PUBLIC_BUCKET].store == {}                      # and nothing was copied public


def test_the_admin_key_still_adds_to_and_removes_from_the_feed(feed):
    r = feed.client.post(SUBMIT, json={"podcast_id": "job1", "submit_to_rss": True}, headers=ADMIN)
    assert r.status_code == 200 and r.json()["submitted_to_rss"] is True
    assert feed.rss.update_rss_feed.await_args.args[2] is True
    assert feed.db.data["podcast_jobs"]["job1"]["submitted_to_rss"] is True
    assert set(feed.storage.buckets[ms.PUBLIC_BUCKET].store) == set(files(EID))   # the verified copy to the public bucket still happens first
    r = feed.client.post(SUBMIT, json={"podcast_id": "job1", "submit_to_rss": False}, headers=ADMIN)
    assert r.status_code == 200 and r.json()["submitted_to_rss"] is False
    assert feed.rss.update_rss_feed.await_args.args[2] is False


def test_the_owner_dashboard_no_longer_has_the_rss_button():
    html = _page("subscriber-dashboard.html")
    for gone in ("Post to RSS", "Remove from RSS", "submitToRSS", "submit-to-rss", "submit_to_rss"):
        assert gone not in html, gone


def test_the_admin_dashboard_rss_buttons_are_untouched():
    html = _page("admin-dashboard.html")
    assert html.count("/api/admin/podcasts/${podcastId}/rss`") == 2 and "addToRss(" in html and "removeFromRss(" in html


# ---- 8. unaffected: admin-generated and curated episodes, the public feed, existing public pages ----------------------------------------------
def test_admin_generated_and_curated_episodes_behave_exactly_as_before(env):
    """An episode the admin generated (or a curated one) belongs to the admin account. Everyone else gets 404 for it while it is private; the admin key
    sees it; nothing about it needs an allow-list or a session. Public ones are unchanged."""
    env.db.data["subscribers"]["admin-sub"] = subscriber("tok-admin", can_generate=True)
    env.db.data["episodes"]["ever-curated-260001"] = episode("admin-sub", curated=True)
    env.db.data["episodes"]["ever-curated-260002"] = episode("admin-sub", curated=True, submitted_to_rss=True)
    assert env.client.get("/api/episodes/ever-curated-260001", headers=HA).status_code == 404
    assert env.client.get("/api/episodes/ever-curated-260001").status_code == 404
    assert env.client.get("/api/episodes/ever-curated-260001", headers=ADMIN).status_code == 200
    assert env.client.get("/api/episodes/ever-curated-260002").status_code == 200
    assert env.client.get("/api/subscribers/episodes/ever-curated-260001/media-links", headers=HA).status_code == 404   # not A's episode


def test_a_public_episode_record_is_the_same_for_everyone(env):
    anon = env.client.get(f"/api/episodes/{PUBLIC_EID}").json()
    assert env.client.get(f"/api/episodes/{PUBLIC_EID}", headers=HA).json() == anon == env.client.get(f"/api/episodes/{PUBLIC_EID}", headers=HB).json()
    assert env.client.get(f"/api/episodes/{PUBLIC_EID}", headers=ADMIN).json() == anon


def test_the_admin_publish_site_route_and_the_admin_media_links_route_are_unchanged(env):
    r = env.client.post(f"/api/admin/episodes/{EID}/publish-site", headers=ADMIN)
    assert r.status_code == 200 and r.json()["visible_on_web"] is True and r.json()["promoted_files"] == len(files(EID))
    assert env.client.get(f"/api/admin/episodes/{EID_B}/media-links?hours=2", headers=ADMIN).json()["expires_in_seconds"] == 7200
    assert env.client.get(f"/api/admin/episodes/{EID_B}/media-links", headers=HA).status_code in (401, 403)


# ---- 6. the buttons (static checks of the two pages) --------------------------------------------------------------------------------------
def _page(name):
    from pathlib import Path
    return (Path(__file__).resolve().parents[2] / "public" / name).read_text(encoding="utf-8")


def test_owner_dashboard_has_play_and_make_public_with_the_irreversible_warning_and_no_way_back():
    html = _page("subscriber-dashboard.html")
    for needle in ("playPrivate(podcast)", "makePublic(podcast)", "This cannot be undone by you", "Only the site administrator can take it down",
                   "It will not be added to the podcast feed", "confirm_irreversible: true", "media-links?minutes=15"):
        assert needle in html, needle
    assert html.index("This cannot be undone by you") < html.index("/make-public`")        # the warning is shown before the request is made
    for forbidden in ("make-private", "makePrivate", "Make private", "unpublish"):
        assert forbidden not in html, forbidden


def test_admin_dashboard_has_unpublish_and_the_quota_control():
    html = _page("admin-dashboard.html")
    for needle in ("unpublishEpisode(", "/unpublish`", "reason", "setQuota(", "/quota`", "method: 'PUT'"):
        assert needle in html, needle
