"""Onboarding PR 2, option (b): the owner features (PR 1) are also on for an ACTIVE member of an onboarding engine whose record has private_access_enabled: true.

The flag is per engine, absent or false by default, set by a deliberate admin write (no route sets it), and must be exactly true. A removed or otherwise
inactive membership never passes. A flag on engine X opens nothing for a member of only engine Y. A read error is False. The dashboard's
`private_access_enabled` follows the same rule because it calls the same function. Offline."""
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

import media_store as ms
from tests import fakes_pr1
from tests.fakes_pr1 import FakeDB, passthrough_transactional, subscriber
from tests.unit.test_media_store import FakeClient, files
from utils import onboarding as ob
from utils import owner_access
from utils.owner_access import private_access_enabled

A, B, C = "sub-a", "sub-b", "sub-c"
TOK_A, TOK_B, TOK_C = "token-a", "token-b", "token-c"
HA, HB, HC = ({"X-Subscriber-Token": t} for t in (TOK_A, TOK_B, TOK_C))
EID = "ever-math-990001"
X, Y = "engine-x", "engine-y"


def episode(owner):
    return {"title": "T", "subscriber_id": owner, "submitted_to_rss": False, "visible_on_web": False}


def member(db, sid, engine, status="active"):
    db.data.setdefault("onboarding_members", {})[ob.member_id(engine, sid)] = {"engine_id": engine, "subscriber_id": sid, "role": "owner", "status": status}


def flag(db, engine, value="absent"):
    if value == "absent":
        db.data["onboarding_engines"][engine].pop("private_access_enabled", None)
    else:
        db.data["onboarding_engines"][engine]["private_access_enabled"] = value


@pytest.fixture
def env(monkeypatch):
    import config.database
    import utils.auth as auth
    import utils.generation_quota as gq
    from endpoints.public import routes as public_routes
    from endpoints.subscriber import episode_access as owner_routes
    from endpoints.subscriber import routes as sub_routes
    db = FakeDB(
        subscribers={A: subscriber(TOK_A, email="a@example.invalid"), B: subscriber(TOK_B, email="b@example.invalid"), C: subscriber(TOK_C, email="c@example.invalid")},
        episodes={EID: episode(A), "ever-math-990002": episode(B)},
        onboarding_engines={X: {"label": "X", "state": "open"}, Y: {"label": "Y", "state": "open"}},
    )
    storage = FakeClient()
    for n in files(EID):
        storage.buckets[ms.PRIVATE_BUCKET].add(n, f"{n}-bytes".encode())
    for mod in (public_routes, owner_routes, sub_routes, config.database):
        monkeypatch.setattr(mod, "db", db)
    monkeypatch.setattr(auth, "get_admin_api_key", lambda: "test-key")
    monkeypatch.setattr(ms, "_client", lambda client=None: client or storage)
    monkeypatch.setattr(ms, "_signing_kwargs", lambda: {})
    monkeypatch.setattr(gq.firestore, "transactional", passthrough_transactional)
    app = FastAPI()
    for r in (owner_routes.router, public_routes.router, sub_routes.router):
        app.include_router(r)
    return type("Env", (), {"db": db, "client": TestClient(app)})()


def routes_status(env, headers):
    """The owner routes for A's own private episode: (media-links, API record)."""
    return (env.client.get(f"/api/subscribers/episodes/{EID}/media-links", headers=headers).status_code,
            env.client.get(f"/api/episodes/{EID}", headers=headers).status_code)


def dashboard_flag(env, sid=A, headers=HA):
    r = env.client.get(f"/api/subscribers/podcasts/{sid}", headers=headers)
    assert r.status_code == 200, r.text
    return r.json()["private_access_enabled"]


# ---- the rule -----------------------------------------------------------------------------------------------------------------------------------
def test_a_member_of_an_engine_with_the_flag_off_or_absent_gets_404_and_with_it_on_gets_200(env):
    member(env.db, A, X)
    for value in ("absent", False):
        flag(env.db, X, value)
        assert routes_status(env, HA) == (404, 404), value                       # the flag off (or never set): the features stay dark
        assert dashboard_flag(env) is False
    flag(env.db, X, True)
    assert routes_status(env, HA) == (200, 200)
    assert dashboard_flag(env) is True                                           # the dashboard payload follows the same rule


def test_the_flag_must_be_exactly_true(env):
    member(env.db, A, X)
    for loose in ("true", "yes", 1, [True], {"on": True}, "True"):
        flag(env.db, X, loose)
        assert private_access_enabled(env.db, A) is False, loose
    flag(env.db, X, True)
    assert private_access_enabled(env.db, A) is True


def test_a_revoked_or_inactive_membership_never_passes(env):
    member(env.db, A, X)
    flag(env.db, X, True)
    assert routes_status(env, HA) == (200, 200)
    env.db.data["onboarding_members"].pop(ob.member_id(X, A))                    # revocation (Q17) deletes the membership
    assert routes_status(env, HA) == (404, 404) and dashboard_flag(env) is False
    for status in ("removed", "revoked", "pending", "", None):
        member(env.db, A, X, status=status)
        assert private_access_enabled(env.db, A) is False, status
    member(env.db, A, X, status="active")
    assert private_access_enabled(env.db, A) is True


def test_a_non_member_gets_404_whatever_the_flag_says(env):
    flag(env.db, X, True)
    flag(env.db, Y, True)
    member(env.db, B, X)                                                          # B is a member, but A (who owns the episode) is not
    assert routes_status(env, HA) == (404, 404) and dashboard_flag(env) is False
    assert private_access_enabled(env.db, A) is False and private_access_enabled(env.db, C) is False
    # and a member is not a viewer of someone ELSE's private episode: the owner rule still applies
    assert env.client.get(f"/api/subscribers/episodes/{EID}/media-links", headers=HB).status_code == 404
    assert env.client.get(f"/api/episodes/{EID}", headers=HB).status_code == 404


def test_the_flag_on_one_engine_opens_nothing_for_a_member_of_only_another(env):
    member(env.db, A, Y)
    flag(env.db, X, True)                                                         # engine X is on, but A belongs only to Y
    flag(env.db, Y, "absent")
    assert routes_status(env, HA) == (404, 404) and dashboard_flag(env) is False
    flag(env.db, Y, True)
    assert routes_status(env, HA) == (200, 200)
    member(env.db, A, X)                                                          # a member of two engines passes if either is on
    flag(env.db, Y, False)
    assert private_access_enabled(env.db, A) is True
    flag(env.db, X, False)
    assert private_access_enabled(env.db, A) is False


def test_an_engine_record_that_is_missing_does_not_pass(env):
    member(env.db, A, "no-such-engine")
    assert private_access_enabled(env.db, A) is False
    member(env.db, A, None)
    assert private_access_enabled(env.db, A) is False


def test_the_manual_list_still_works_and_the_two_ways_combine(env):
    assert private_access_enabled(env.db, A) is False
    env.db.data["system_config"] = {"private_episode_access": {"allowed_subscriber_ids": [A]}}
    assert private_access_enabled(env.db, A) is True and private_access_enabled(env.db, B) is False        # PR 1 behaviour, unchanged
    env.db.data["system_config"]["private_episode_access"] = {"allowed_subscriber_ids": []}
    member(env.db, B, X)
    flag(env.db, X, True)
    assert private_access_enabled(env.db, B) is True and private_access_enabled(env.db, A) is False         # the list may be empty and a member still passes
    env.db.data["system_config"]["private_episode_access"] = {"enabled_for_all": True}
    assert private_access_enabled(env.db, C) is True


def test_a_read_error_is_false_and_the_list_alone_survives_a_membership_read_error(env):
    member(env.db, A, X)
    flag(env.db, X, True)

    class Broken:
        def __init__(self, inner, bad):
            self.inner, self.bad = inner, bad

        def collection(self, name):
            if name == self.bad:
                raise RuntimeError("read failed")
            return self.inner.collection(name)
    for bad in ("onboarding_members", "onboarding_engines", "system_config"):
        assert private_access_enabled(Broken(env.db, bad), A) is False, bad          # fail closed, whichever read fails
    env.db.data["system_config"] = {"private_episode_access": {"allowed_subscriber_ids": [A]}}
    assert private_access_enabled(Broken(env.db, "onboarding_members"), A) is True    # listed: decided before the membership read
    assert private_access_enabled(None, A) is False and private_access_enabled(env.db, None) is False and private_access_enabled(env.db, "") is False


def test_the_collection_names_match_the_onboarding_module():
    assert owner_access.MEMBERS_COLLECTION == ob.MEMBERS and owner_access.ENGINES_COLLECTION == ob.ENGINES


def test_an_accepted_invitation_followed_by_the_flag_turns_the_features_on_with_no_other_step(monkeypatch):
    """The point of option (b): invite, accept, and the engine flag is the only switch; revocation turns it off with no second write."""
    from tests.fakes_pr2 import FakeDB as AtomicDB, run_in_transaction
    monkeypatch.setattr(ob, "_run_in_transaction", run_in_transaction)
    db = AtomicDB(onboarding_engines={X: {"label": "X", "state": "open", "final_say_subscriber_id": None}})
    made = ob.create_invite(db, engine_id=X, email="new.person@example.invalid")
    result = ob.accept_invite(db, raw_token=made["raw_token"], email="new.person@example.invalid",
                              new_account_fields={"name": "n", "password_hash": "scrypt$00$11"}, consent={"naming": "role"})
    sid = result["subscriber_id"]
    assert private_access_enabled(db, sid) is False                              # a member, engine flag still off: dark
    db.data[ob.ENGINES][X]["private_access_enabled"] = True
    assert private_access_enabled(db, sid) is True                               # flag on: on, with no allow-list entry anywhere
    assert "system_config" not in db.data
    ob.revoke_invite(db, made["invite_id"])
    assert private_access_enabled(db, sid) is False                              # revocation removes the membership: off again, no second write


# ---- the survivor: a membership record with no subscriber id must never match ------------------------------------------------------------------------
def junk_members(db, engine=X):
    """Active membership records that carry no usable subscriber id, stored under every key a missing or empty id could build."""
    db.data["onboarding_members"] = {
        f"{engine}__": {"engine_id": engine, "status": "active", "role": "owner"},                                  # keyed with an empty id, field absent
        f"{engine}__None": {"engine_id": engine, "status": "active", "subscriber_id": None},                       # keyed with 'None'
        "loose": {"engine_id": engine, "status": "active", "role": "owner"},                                        # no subscriber_id field at all
        "blank": {"engine_id": engine, "status": "active", "subscriber_id": ""},
        "spaces": {"engine_id": engine, "status": "active", "subscriber_id": "   "},
    }


def test_a_member_record_with_no_subscriber_id_never_matches_a_missing_or_empty_caller(env):
    flag(env.db, X, True)                                                       # the engine's flag is ON
    junk_members(env.db)
    for who in (None, "", "   ", 0, [], {}, b"x"):
        assert private_access_enabled(env.db, who) is False, repr(who)
    assert owner_access._active_member_of_an_enabled_engine(env.db, None) is False and owner_access._active_member_of_an_enabled_engine(env.db, "") is False
    assert private_access_enabled(env.db, A) is False                           # and a real subscriber is not swept in by the junk records


def test_an_anonymous_or_none_caller_gets_404_on_the_owner_routes_with_a_flag_on_and_a_record_with_no_id(env):
    flag(env.db, X, True)
    junk_members(env.db)
    assert routes_status(env, {}) == (404, 404)                                  # anonymous, on a real owner's private episode
    assert routes_status(env, {"X-Subscriber-Token": "garbage"}) == (404, 404)
    assert routes_status(env, HC) == (404, 404)                                  # a valid session that is not the owner
    # an episode record with NO owner at all, and a caller with no usable identity or a valid but unrelated session
    env.db.data["episodes"]["ownerless"] = {"title": "x", "submitted_to_rss": False, "visible_on_web": False}
    env.db.data["episodes"]["ownerless-none"] = {"title": "x", "subscriber_id": None, "submitted_to_rss": False, "visible_on_web": False}
    env.db.data["episodes"]["ownerless-empty"] = {"title": "x", "subscriber_id": "", "submitted_to_rss": False, "visible_on_web": False}
    for eid in ("ownerless", "ownerless-none", "ownerless-empty"):
        for headers in ({}, HA, HC):
            assert env.client.get(f"/api/subscribers/episodes/{eid}/media-links", headers=headers).status_code == 404, (eid, headers)
            assert env.client.get(f"/api/episodes/{eid}", headers=headers).status_code == 404, (eid, headers)
    from utils.owner_access import session_owner_id
    assert session_owner_id(env.db, {"title": "x"}, None) is None and session_owner_id(env.db, {"subscriber_id": ""}, TOK_A) is None
    assert session_owner_id(env.db, {"subscriber_id": None}, TOK_A) is None
    assert dashboard_flag(env) is False                                          # the dashboard payload for a real, non-member owner


def test_the_membership_lookup_refuses_a_missing_empty_or_mismatched_id_before_and_after_the_lookup(env):
    flag(env.db, X, True)
    junk_members(env.db)
    for sid in (None, "", "   ", 5, [], b"x"):
        assert ob.active_membership(env.db, X, sid) is None, repr(sid)
    for eid in (None, "", "  ", 5):
        assert ob.active_membership(env.db, eid, "sub-a") is None, repr(eid)
    # a record found at the right key must still carry exactly this engine and this subscriber, and be active
    key = ob.member_id(X, "sub-z")
    env.db.data["onboarding_members"][key] = {"engine_id": X, "status": "active"}                                       # subscriber_id missing
    assert ob.active_membership(env.db, X, "sub-z") is None
    env.db.data["onboarding_members"][key] = {"engine_id": X, "status": "active", "subscriber_id": "someone-else"}      # mismatched
    assert ob.active_membership(env.db, X, "sub-z") is None
    env.db.data["onboarding_members"][key] = {"engine_id": Y, "status": "active", "subscriber_id": "sub-z"}             # wrong engine
    assert ob.active_membership(env.db, X, "sub-z") is None
    env.db.data["onboarding_members"][key] = {"engine_id": X, "status": "removed", "subscriber_id": "sub-z"}            # inactive
    assert ob.active_membership(env.db, X, "sub-z") is None
    env.db.data["onboarding_members"][key] = {"engine_id": X, "status": "active", "subscriber_id": "sub-z"}
    assert ob.active_membership(env.db, X, "sub-z")["subscriber_id"] == "sub-z"                                         # and the right one still works


def test_the_engine_gate_admits_nobody_on_a_record_with_no_id(env):
    """The default-deny gate: records under 'X__' and 'X__None' must not admit an anonymous caller, a garbage token or a session that has no membership."""
    import utils.auth as auth
    from endpoints.onboarding import routes as onboarding_routes
    onboarding_routes_db = env.db
    from unittest.mock import patch
    junk_members(env.db)
    with patch.object(onboarding_routes, "db", onboarding_routes_db):
        app = FastAPI()
        app.include_router(onboarding_routes.router)
        c = TestClient(app)
        for headers in ({}, {"X-Subscriber-Token": "garbage"}, HC):
            r = c.get(f"/api/onboarding/engines/{X}", headers=headers)
            assert (r.status_code, r.json()) == (404, {"detail": "Not found"}), headers
