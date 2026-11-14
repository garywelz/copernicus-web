"""Onboarding PR 2: invitations and engine roles (design 3.1, 5.6, 5.7, 8.1 PR 2 test plan (a) to (j), plus the quota, Q16 and Q17 behaviour).

Offline: an in-memory Firestore with ATOMIC transactions (tests/fakes_pr2.py), a fake email sender, a recorded rate limiter, a mocked clock. No test waits and
none touches the network. Addresses used are on the reserved .invalid domain."""
import hashlib
import json
import re
import threading
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import MagicMock

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from config.constants import ADMIN_SUBSCRIBER_EMAIL
from tests import fakes_pr1
from tests.fakes_pr2 import FakeDB, run_in_transaction
from utils import onboarding as ob
from utils.credential_tokens import hash_token
from utils.subscriber_helpers import generate_subscriber_id

ROOT = Path(__file__).resolve().parents[2]
ADMIN_KEY = {"X-Admin-API-Key": "test-key"}
ENGINE = "tdap-e2e"
OTHER_ENGINE = "other-engine"
NEW_ADDR = "new.person@example.invalid"
OLD_ADDR_TYPED = "Old.Person@Example.invalid"          # an account made before normalisation: its id is the sha256 of THIS spelling
NOW = datetime(2026, 11, 6, 12, 0, 0, tzinfo=timezone.utc)
ADMIN_ID = generate_subscriber_id(ADMIN_SUBSCRIBER_EMAIL)
PASSWORD = "a-good-password-1"
EMAIL_SHAPED = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
CONSENT = {"naming": "role", "licence_confirmed": True, "licence_other": None, "lookups": True, "acknowledged": True}


def fresh_db():
    return FakeDB(
        onboarding_engines={ENGINE: {"label": "TDAP end-to-end", "state": "open", "final_say_subscriber_id": None},
                            OTHER_ENGINE: {"label": "Another", "state": "open", "final_say_subscriber_id": None},
                            "closed-engine": {"label": "Closed", "state": "closed", "final_say_subscriber_id": None}},
        subscribers={ADMIN_ID: {"email": "admin@example.invalid", "can_generate": True, "monthly_quota": None}},
    )


@pytest.fixture
def env(monkeypatch):
    import config.database
    import utils.auth as auth
    import utils.generation_quota as gq
    from endpoints.onboarding import routes
    db = fresh_db()
    sent, limited = [], []

    class Mail:
        async def send_invitation_email(self, address, link, days, engine_label=None):
            sent.append({"address": address, "link": link, "days": days, "engine_label": engine_label})
            return True
    monkeypatch.setattr(ob, "_run_in_transaction", run_in_transaction)
    # THE CLOCK IS PINNED. The invitations here are made at NOW (2026-11-06) with a 7-day expiry, and the accept route reads the clock. Left on the real clock,
    # nine of these tests began failing on 2026-11-13 12:00Z, when every invitation became "expired" (BULLETIN 045, F6). A test that needs another time sets it.
    monkeypatch.setattr(ob, "_utcnow", lambda: NOW)
    monkeypatch.setattr(routes, "db", db)
    monkeypatch.setattr(config.database, "db", db)
    monkeypatch.setattr(routes, "email_service", Mail())
    monkeypatch.setattr(routes, "check_rate_limit", lambda *a, **k: limited.append((a[1:3], k)))
    monkeypatch.setattr(auth, "get_admin_api_key", lambda: "test-key")
    monkeypatch.setattr(gq.firestore, "transactional", fakes_pr1.passthrough_transactional)
    app = FastAPI()
    app.include_router(routes.router)
    return type("Env", (), {"db": db, "client": TestClient(app), "sent": sent, "limited": limited, "routes": routes, "app": app, "mp": monkeypatch})()


def invite(env_or_db, addr=NEW_ADDR, engine=ENGINE, **kw):
    db = getattr(env_or_db, "db", env_or_db)
    return ob.create_invite(db, engine_id=engine, email=addr, now=NOW - timedelta(minutes=1), **kw)


def accept(db, made, addr=NEW_ADDR, now=NOW, token=None, fields="default", consent=CONSENT):
    new = {"name": "New Person", "password_hash": "scrypt$00$11", "subscription_tier": "free"} if fields == "default" else fields
    return ob.accept_invite(db, raw_token=made["raw_token"] if token is None else token, email=addr, new_account_fields=new, consent=dict(consent), now=now,
                            ip_hash="iphash", request_id="req1")


def post_accept(env, made, addr=NEW_ADDR, **over):
    body = {"token": made["raw_token"], "email": addr, "name": "New Person", "password": PASSWORD, "consent": CONSENT, **over}
    return env.client.post("/api/onboarding/invites/accept", json=body)


def events(db, action=None):
    ev = list(db.data.get(ob.EVENTS, {}).values())
    return [e for e in ev if action is None or e["action"] == action]


def strings(o):
    if isinstance(o, str):
        yield o
    elif isinstance(o, dict):
        for v in o.values():
            yield from strings(v)
    elif isinstance(o, (list, tuple)):
        for v in o:
            yield from strings(v)


REFUSAL = {"detail": "This invitation link is not valid."}


# ---- address handling (Q16) -----------------------------------------------------------------------------------------------------------------------
def test_addresses_are_trimmed_and_lower_cased_and_shape_checked():
    assert ob.normalise_address("  New.Person@Example.INVALID ") == NEW_ADDR
    for good in (NEW_ADDR, "a@b.co", "x+tag@sub.example.invalid"):
        assert ob.address_ok(good)
    for bad in ("", "no-at-sign", "two@@x.co", "a@b", "a@.co", "a@b..co", "a b@x.co", "<a@x.co>", "a@x.co\nBcc: y@z.co", "a" * 250 + "@x.co", "a@x.co,b@y.co"):
        assert not ob.address_ok(bad), bad
    assert ob.address_hash(NEW_ADDR) == hashlib.sha256(NEW_ADDR.encode()).hexdigest()


# ---- creating an invitation ------------------------------------------------------------------------------------------------------------------------
def test_an_invitation_stores_neither_the_address_nor_the_token(env):
    """(g) the invitation holds only hashes; the response and the email are the only places the token and address appear."""
    r = env.client.post("/api/admin/onboarding/invites", json={"engine_id": ENGINE, "email": f"  {NEW_ADDR.upper()} "}, headers=ADMIN_KEY)
    assert r.status_code == 200 and set(r.json()) == {"invite_id", "engine_id", "expires_at", "email_sent"} and r.json()["email_sent"] is True
    assert NEW_ADDR not in r.text and "token" not in r.text.lower()
    (inv,) = env.db.data[ob.INVITES].values()
    link = env.sent[0]["link"]
    raw = link.split("#token=")[1]
    assert env.sent[0]["address"] == NEW_ADDR and link.startswith(ob.ACCEPT_PAGE_URL + "#token=") and "?" not in link      # fragment, never a query string
    assert inv["email_sha256"] == ob.address_hash(NEW_ADDR) and inv["token_hash"] == hash_token(raw)
    assert not [s for s in strings(inv) if "@" in s or raw in s or NEW_ADDR in s]
    assert (inv["roles"], inv["can_generate"], inv["monthly_quota"], inv["final_say"], inv["used_at"]) == (["owner"], True, 10, False, None)       # default quota 10
    assert datetime.fromisoformat(inv["expires_at"]) - datetime.fromisoformat(inv["created_at"]) == timedelta(days=7)                                 # default expiry 7 days


def test_creating_an_invitation_is_admin_only_and_validated(env):
    body = {"engine_id": ENGINE, "email": NEW_ADDR}
    for headers in ({}, {"X-Admin-API-Key": "wrong"}, {"X-Subscriber-Token": "tok"}):
        assert env.client.post("/api/admin/onboarding/invites", json=body, headers=headers).status_code in (401, 403)
    assert env.client.delete("/api/admin/onboarding/invites/x", headers={}).status_code in (401, 403)
    assert env.db.data.get(ob.INVITES, {}) == {} and env.sent == []
    bad = [({"engine_id": "Nope"}, 400), ({"engine_id": "a__b"}, 400), ({"email": "not-an-address"}, 400), ({"monthly_quota": 201}, 400),
           ({"monthly_quota": -1}, 400), ({"monthly_quota": True}, 400), ({"monthly_quota": "10"}, 400), ({"expires_days": 0}, 400),
           ({"expires_days": 31}, 400), ({"expires_days": True}, 400), ({"engine_id": "no-such-engine"}, 404), ({"engine_id": "closed-engine"}, 409)]
    for over, status in bad:
        assert env.client.post("/api/admin/onboarding/invites", json={**body, **over}, headers=ADMIN_KEY).status_code == status, over
    assert env.db.data.get(ob.INVITES, {}) == {} and env.sent == []
    assert env.client.post("/api/admin/onboarding/invites", json={**body, "monthly_quota": None}, headers=ADMIN_KEY).status_code == 200      # null = unlimited
    assert list(env.db.data[ob.INVITES].values())[0]["monthly_quota"] is None


def test_one_outstanding_invitation_per_address_and_engine(env):
    invite(env)
    with pytest.raises(ob.InviteError) as e:
        invite(env)
    assert e.value.status == 409
    invite(env, engine=OTHER_ENGINE)                                              # another engine is fine
    invite(env, addr="second.person@example.invalid")                             # another address is fine


# ---- (a) accepting sets the permissions together; a failure partway leaves nothing ----------------------------------------------------------------
def test_a_valid_acceptance_creates_the_account_the_membership_and_marks_the_invitation_used(env):
    made = invite(env)
    r = post_accept(env, made)
    assert r.status_code == 200 and r.json()["engine_id"] == ENGINE and NEW_ADDR not in r.text
    sid = ob.address_hash(NEW_ADDR)
    sub = env.db.data["subscribers"][sid]
    assert (sub["can_generate"], sub["monthly_quota"], sub["email"], sub["subscription_tier"]) == (True, 10, NEW_ADDR, "free")
    assert sub["password_hash"].startswith("scrypt$") and PASSWORD not in json.dumps(sub)
    m = env.db.data[ob.MEMBERS][f"{ENGINE}__{sid}"]
    assert (m["role"], m["final_say"], m["status"], m["engine_id"], m["subscriber_id"]) == ("owner", False, "active", ENGINE, sid)
    assert m["consent"]["naming"] == "role" and m["consent"]["version"] == ob.CONSENT_VERSION and m["consent"]["lookups"] is True
    (inv,) = env.db.data[ob.INVITES].values()
    assert inv["used_at"] and inv["used_by_subscriber_id"] == sid


def test_a_failure_forced_partway_leaves_no_account_no_membership_and_the_invitation_unused(env):
    made = invite(env)
    for knob in ({"fail_after_ops": 3}, {"fail_on_commit": True}, {"fail_writes_to": {ob.EVENTS}}):
        for k, v in knob.items():
            setattr(env.db, k, v)
        before = json.dumps(env.db.data, sort_keys=True, default=str)
        r = post_accept(env, made)
        assert r.status_code == 500 and "Nothing was changed" in r.json()["detail"]
        assert json.dumps(env.db.data, sort_keys=True, default=str) == before                    # not one field differs
        assert ob.address_hash(NEW_ADDR) not in env.db.data["subscribers"] and ob.MEMBERS not in env.db.data
        env.db.fail_after_ops, env.db.fail_on_commit, env.db.fail_writes_to = None, False, set()
    assert post_accept(env, made).status_code == 200                                              # the invitation was never spent: it still works


# ---- (b) registration without an invitation is unchanged ------------------------------------------------------------------------------------------
@pytest.fixture
def reg(monkeypatch):
    import config.database
    import utils.subscriber_helpers as sh
    from endpoints.subscriber import routes as sub_routes
    db = fresh_db()
    for mod in (sub_routes, sh, config.database):
        monkeypatch.setattr(mod, "db", db)
    app = FastAPI()
    app.include_router(sub_routes.router)
    return type("Reg", (), {"db": db, "client": TestClient(app)})()


def test_registration_without_an_invitation_gets_no_permissions_and_no_membership(reg):
    r = reg.client.post("/api/subscribers/register", json={"email": "  Plain.Person@Example.invalid ", "name": "Plain", "password": PASSWORD})
    assert r.status_code == 200
    sid = hashlib.sha256(b"plain.person@example.invalid").hexdigest()                              # Q16: the id is the hash of the NORMALISED address
    assert r.json()["subscriber_id"] == sid and r.json()["email"] == "plain.person@example.invalid"
    sub = reg.db.data["subscribers"][sid]
    assert not sub.get("can_generate") and "monthly_quota" not in sub and sub["email"] == "plain.person@example.invalid"
    assert ob.MEMBERS not in reg.db.data and ob.INVITES not in reg.db.data and ob.EVENTS not in reg.db.data


def test_normalisation_leaves_existing_ids_alone_and_finds_either_spelling(reg):
    import utils.subscriber_helpers as sh
    old_id = hashlib.sha256(OLD_ADDR_TYPED.encode()).hexdigest()
    reg.db.data["subscribers"][old_id] = {"email": OLD_ADDR_TYPED, "password_hash": "scrypt$aa$bb"}
    assert sh.get_subscriber_by_email(OLD_ADDR_TYPED).id == old_id                                # an old account is found by the spelling it was made with
    # the same registration again, spelled as typed, is refused (not duplicated)
    assert reg.client.post("/api/subscribers/register", json={"email": OLD_ADDR_TYPED, "name": "x", "password": PASSWORD}).status_code == 409
    assert len([k for k in reg.db.data["subscribers"] if k != ADMIN_ID]) == 1
    # a new account is stored under the normalised id, and is found by any spelling of it
    assert reg.client.post("/api/subscribers/register", json={"email": "Fresh@Example.invalid", "name": "x", "password": PASSWORD}).status_code == 200
    fresh_id = hashlib.sha256(b"fresh@example.invalid").hexdigest()
    assert sh.get_subscriber_by_email("FRESH@example.INVALID").id == fresh_id and sh.get_subscriber_by_email("fresh@example.invalid").id == fresh_id


# ---- the tests do not depend on today's date --------------------------------------------------------------------------------------------------------
def test_the_fixture_pins_the_clock_and_the_same_acceptance_fails_on_any_later_real_date(env):
    """The pin, and what it prevents. With the clock at NOW an invitation made a minute earlier is accepted. With the clock where the real one has been since
    2026-11-13 (more than 7 days after NOW), the SAME request is refused as expired: that is the failure nine tests showed before the fixture pinned the clock."""
    assert ob._utcnow() == NOW and ob._utcnow() is not None
    made = invite(env, addr="pinned.person@example.invalid")
    env.mp.setattr(ob, "_utcnow", lambda: NOW + timedelta(days=7, seconds=1))                  # one second past the expiry: where an unpinned clock now stands
    late = post_accept(env, made, addr="pinned.person@example.invalid")
    assert (late.status_code, late.json()["detail"]) == (400, env.routes.INVITATION_REFUSAL)
    env.mp.setattr(ob, "_utcnow", lambda: NOW + timedelta(days=6, hours=23))                   # still inside the 7 days
    assert post_accept(env, made, addr="pinned.person@example.invalid").status_code == 200


def test_no_test_in_this_file_can_reach_the_real_clock_through_the_accept_route(env):
    import inspect
    src = inspect.getsource(env.routes.accept_invitation)
    assert "ob._utcnow()" in src and "datetime.now" not in src and "utcnow()" not in src.replace("ob._utcnow()", ""), "the route's only clock is the one the fixture pins"


# ---- (c) used, expired, revoked ------------------------------------------------------------------------------------------------------------------
def test_a_used_expired_or_revoked_invitation_is_refused_with_the_same_answer(env):
    used = invite(env, addr="used.person@example.invalid")
    assert post_accept(env, used, addr="used.person@example.invalid").status_code == 200
    second = post_accept(env, used, addr="used.person@example.invalid")
    expired = invite(env, addr="late.person@example.invalid")
    env.mp.setattr(ob, "_utcnow", lambda: NOW + timedelta(days=8))                              # the clock is mocked; nothing waits
    late = post_accept(env, expired, addr="late.person@example.invalid")
    env.mp.setattr(ob, "_utcnow", lambda: NOW)
    revoked = invite(env, addr="gone.person@example.invalid")
    assert env.client.delete(f"/api/admin/onboarding/invites/{revoked['invite_id']}", headers=ADMIN_KEY).json()["outcome"] == "revoked_unused"
    gone = post_accept(env, revoked, addr="gone.person@example.invalid")
    for r in (second, late, gone):
        assert r.status_code == 400 and r.json() == REFUSAL
    assert ob.address_hash("late.person@example.invalid") not in env.db.data["subscribers"]
    assert ob.address_hash("gone.person@example.invalid") not in env.db.data["subscribers"]


def test_a_closed_engine_or_an_existing_membership_is_refused_the_same_way(env):
    made = invite(env)
    env.db.data[ob.ENGINES][ENGINE]["state"] = "closed"
    r = post_accept(env, made)
    assert (r.status_code, r.json()) == (400, REFUSAL) and ob.address_hash(NEW_ADDR) not in env.db.data["subscribers"]
    env.db.data[ob.ENGINES][ENGINE]["state"] = "open"
    assert post_accept(env, made).status_code == 200
    again = ob.create_invite(env.db, engine_id=ENGINE, email=NEW_ADDR, now=NOW - timedelta(minutes=1))       # a fresh invitation for someone already a member
    r2 = post_accept(env, again)
    assert (r2.status_code, r2.json()) == (400, REFUSAL)


# ---- (d) the token and the address are both required ---------------------------------------------------------------------------------------------
def test_a_valid_token_with_the_wrong_address_and_the_right_address_without_the_token_are_both_refused(env):
    made = invite(env)
    other = invite(env, addr="other.person@example.invalid")
    attempts = [
        post_accept(env, made, addr="someone.else@example.invalid"),                          # valid token, wrong address
        post_accept(env, made, addr="other.person@example.invalid"),                          # valid token, another invitee's address
        post_accept(env, other, addr=NEW_ADDR),                                               # the other invitation's token with this address
        env.client.post("/api/onboarding/invites/accept", json={"token": "x", "email": NEW_ADDR, "name": "n", "password": PASSWORD, "consent": CONSENT}),   # right address, no valid token
        env.client.post("/api/onboarding/invites/accept", json={"token": "A" * 43, "email": NEW_ADDR, "name": "n", "password": PASSWORD, "consent": CONSENT}),
        env.client.post("/api/onboarding/invites/accept", json={"token": hash_token(made["raw_token"]), "email": NEW_ADDR, "name": "n", "password": PASSWORD, "consent": CONSENT}),  # the stored HASH is not the token
    ]
    for r in attempts:
        assert (r.status_code, r.json()) == (400, REFUSAL)
    assert env.db.data["subscribers"].keys() == {ADMIN_ID} and ob.MEMBERS not in env.db.data
    assert all(i["used_at"] is None for i in env.db.data[ob.INVITES].values())                  # refusals spend nothing
    assert post_accept(env, made).status_code == 200                                              # the right token and the right address still work


def test_acceptance_checks_both_proofs_in_the_function_itself(env):
    made = invite(env)
    assert accept(env.db, made, addr="someone.else@example.invalid") is None
    assert accept(env.db, made, token="not-the-token") is None
    assert accept(env.db, made) is not None


# ---- (e) two simultaneous acceptances ------------------------------------------------------------------------------------------------------------
def test_two_simultaneous_acceptances_exactly_one_succeeds(env):
    made = invite(env)
    results, gate = [], threading.Barrier(2)

    def go():
        gate.wait()
        results.append(accept(env.db, made))
    threads = [threading.Thread(target=go) for _ in range(2)]
    [t.start() for t in threads]
    [t.join() for t in threads]
    assert sorted(r is not None for r in results) == [False, True]
    assert len(env.db.data[ob.MEMBERS]) == 1 and len(events(env.db, "accept")) == 1
    assert len([k for k in env.db.data["subscribers"] if k != ADMIN_ID]) == 1


# ---- (f) an existing ordinary account gains the permissions and keeps its password -----------------------------------------------------------------
def test_an_existing_account_gains_the_permissions_and_its_password_and_sessions_are_unchanged(env):
    old_id = hashlib.sha256(OLD_ADDR_TYPED.encode()).hexdigest()
    original = {"email": OLD_ADDR_TYPED, "name": "Old Person", "password_hash": "scrypt$cafe$beef", "session_token_hash": "abc", "session_token_expires": "2027-01-01T00:00:00",
                "google_id": None, "podcasts_generated": 3, "can_generate": False}
    env.db.data["subscribers"][old_id] = dict(original)
    made = ob.create_invite(env.db, engine_id=ENGINE, email=OLD_ADDR_TYPED, monthly_quota=7, now=NOW - timedelta(minutes=1))
    r = post_accept(env, made, addr=OLD_ADDR_TYPED.lower(), password="a-different-password-9")             # a password is typed, but it is never used
    assert r.status_code == 200
    sub = env.db.data["subscribers"][old_id]
    assert (sub["can_generate"], sub["monthly_quota"]) == (True, 7)
    for k in ("password_hash", "email", "name", "session_token_hash", "session_token_expires", "podcasts_generated"):
        assert sub[k] == original[k], k
    assert f"{ENGINE}__{old_id}" in env.db.data[ob.MEMBERS]
    assert [k for k in env.db.data["subscribers"] if k not in (ADMIN_ID, old_id)] == []               # no duplicate account was made


# ---- the password and consent are checked before the token is spent ----------------------------------------------------------------------------
def test_a_short_password_or_missing_consent_is_refused_and_the_token_is_not_spent(env):
    made = invite(env)
    for over in ({"password": "short"}, {"password": "x" * 129}):
        r = post_accept(env, made, **over)
        assert r.status_code in (400, 422)
    bad_consent = [{**CONSENT, "acknowledged": False}, {**CONSENT, "naming": "everyone"}]
    for c in bad_consent:
        r = post_accept(env, made, consent=c)
        assert r.status_code == 400 and "consent" in r.json()["detail"].lower()
    assert all(i["used_at"] is None for i in env.db.data[ob.INVITES].values())
    assert post_accept(env, made).status_code == 200


def test_acceptance_is_rate_limited_per_client_and_per_address_and_fails_closed(env):
    made = invite(env)
    post_accept(env, made)
    keys = [(call[0], call[1].get("fail_closed")) for call in env.limited]
    assert [k[0][1] for k in keys] == ["onboarding_accept", "onboarding_accept_address"] and all(k[1] is True for k in keys)
    assert env.limited[1][0][0] == ob.address_hash(NEW_ADDR) and NEW_ADDR not in json.dumps(env.limited, default=str)        # keyed by the hash, not the address


def test_an_unsafe_browser_origin_is_refused_on_every_onboarding_route(env):
    made = invite(env)
    body = {"token": made["raw_token"], "email": NEW_ADDR, "name": "n", "password": PASSWORD, "consent": CONSENT}
    assert env.client.post("/api/onboarding/invites/accept", json=body, headers={"Origin": "https://evil.example"}).status_code == 403
    assert env.client.get(f"/api/onboarding/engines/{ENGINE}", headers={"Origin": "https://evil.example", **ADMIN_KEY}).status_code == 403
    assert all(i["used_at"] is None for i in env.db.data[ob.INVITES].values())
    assert env.client.get(f"/api/onboarding/engines/{ENGINE}", headers={"Origin": ob.ALLOWED_ORIGIN, **ADMIN_KEY}).status_code == 200
    assert env.client.post("/api/onboarding/invites/accept", json=body, headers={"Origin": ob.ALLOWED_ORIGIN}).status_code == 200


# ---- (h) default deny: a non-member gets 404 on every engine route (table-driven) ------------------------------------------------------------------
def member_token(env, sid, engine, raw):
    env.db.data["subscribers"][sid] = fakes_pr1.subscriber(raw, email=f"{sid}@example.invalid")
    env.db.data.setdefault(ob.MEMBERS, {})[ob.member_id(engine, sid)] = {"engine_id": engine, "subscriber_id": sid, "role": "owner", "final_say": False, "status": "active"}
    return {"X-Subscriber-Token": raw}


def walk(routes_list):
    """Every leaf route, through FastAPI's lazily included routers."""
    for r in routes_list:
        if hasattr(r, "original_router"):
            yield from walk(r.original_router.routes)
        elif hasattr(r, "path"):
            yield r


def engine_routes(env):
    out = []
    for r in walk(env.app.routes):
        if r.path.startswith("/api/onboarding/") and r.path != "/api/onboarding/invites/accept":
            for m in sorted(r.methods - {"HEAD", "OPTIONS"}):
                out.append((m, r.path, r))
    return out


def test_every_onboarding_route_is_either_the_accept_route_or_behind_the_membership_gate(env):
    paths = {r.path for r in walk(env.app.routes) if r.path.startswith("/api/onboarding/")}
    assert "/api/onboarding/invites/accept" in paths and len(engine_routes(env)) >= 1
    for method, path, route in engine_routes(env):
        assert "{engine_id}" in path, path                                         # an engine route always names its engine
        assert any(d.call is env.routes.engine_gate for d in route.dependant.dependencies), (method, path)


def test_a_non_member_gets_the_same_404_on_every_engine_route(env):
    a = member_token(env, "sub-a", ENGINE, "token-a")
    b = member_token(env, "sub-b", OTHER_ENGINE, "token-b")                         # a member of a DIFFERENT engine
    c = {"X-Subscriber-Token": "token-c"}
    env.db.data["subscribers"]["sub-c"] = fakes_pr1.subscriber("token-c")           # signed in, member of nothing
    cases = {"no credential": {}, "garbage token": {"X-Subscriber-Token": "zzz"}, "signed in, no engine": c, "member of another engine": b,
             "wrong admin key": {"X-Admin-API-Key": "wrong"}}
    seen = set()
    for method, path, _ in engine_routes(env):
        for name, headers in cases.items():
            for eid in (ENGINE, "no-such-engine", "Bad_Id", "a__b"):
                r = env.client.request(method, path.replace("{engine_id}", eid), headers=headers, json={} if method != "GET" else None)
                assert (r.status_code, r.json()) == (404, {"detail": "Not found"}), (method, path, name, eid, r.status_code)
                seen.add(r.text)
    assert len(seen) == 1                                                           # one and the same body for every refusal
    # the member of the engine and the admin do get in
    got = env.client.get(f"/api/onboarding/engines/{ENGINE}", headers=a).json()
    assert {k: got[k] for k in ("engine_id", "label", "state", "role", "final_say")} == {"engine_id": ENGINE, "label": "TDAP end-to-end", "state": "open", "role": "owner", "final_say": False}
    assert got["template_version"] == 1 and [r["key"] for r in got["progress"]["sections"]] == ["scope", "questions", "keywords", "seeds"]       # PR 3a-1 adds the progress tracker
    assert env.client.get(f"/api/onboarding/engines/{ENGINE}", headers=ADMIN_KEY).json()["role"] == "admin"
    assert env.client.get("/api/onboarding/engines/no-such-engine", headers=ADMIN_KEY).status_code == 404       # the admin cannot read an engine that does not exist
    assert env.client.get(f"/api/onboarding/engines/{OTHER_ENGINE}", headers=a).status_code == 404               # and a member cannot read another engine


def test_an_expired_session_or_a_removed_membership_gets_404(env):
    a = member_token(env, "sub-a", ENGINE, "token-a")
    assert env.client.get(f"/api/onboarding/engines/{ENGINE}", headers=a).status_code == 200
    env.db.data["subscribers"]["sub-a"]["session_token_expires"] = (datetime.utcnow() - timedelta(days=1)).isoformat()
    assert env.client.get(f"/api/onboarding/engines/{ENGINE}", headers=a).status_code == 404
    env.db.data["subscribers"]["sub-a"]["session_token_expires"] = (datetime.utcnow() + timedelta(days=1)).isoformat()
    env.db.data[ob.MEMBERS][ob.member_id(ENGINE, "sub-a")]["status"] = "removed"
    assert env.client.get(f"/api/onboarding/engines/{ENGINE}", headers=a).status_code == 404


# ---- (i) final say is exclusive per engine --------------------------------------------------------------------------------------------------------
def test_final_say_is_exclusive_per_engine(env):
    first = invite(env, addr="advisor@example.invalid", final_say=True)
    with pytest.raises(ob.InviteError) as e:                                        # one outstanding final-say invitation at a time
        invite(env, addr="second.advisor@example.invalid", final_say=True)
    assert e.value.status == 409
    invite(env, addr="student@example.invalid")                                     # an ordinary invitation is unaffected
    assert env.client.delete(f"/api/admin/onboarding/invites/{first['invite_id']}", headers=ADMIN_KEY).status_code == 200
    second = invite(env, addr="second.advisor@example.invalid", final_say=True)     # the slot is free again
    assert accept(env.db, second, addr="second.advisor@example.invalid") is not None
    holder = ob.address_hash("second.advisor@example.invalid")
    assert env.db.data[ob.ENGINES][ENGINE]["final_say_subscriber_id"] == holder
    assert env.db.data[ob.MEMBERS][ob.member_id(ENGINE, holder)]["final_say"] is True
    with pytest.raises(ob.InviteError) as e2:                                       # and once there is a holder, no one else can be invited as one
        invite(env, addr="third.advisor@example.invalid", final_say=True)
    assert e2.value.status == 409
    assert env.db.data[ob.ENGINES][OTHER_ENGINE]["final_say_subscriber_id"] is None  # exclusive per ENGINE, not global
    invite(env, addr="third.advisor@example.invalid", engine=OTHER_ENGINE, final_say=True)


def test_a_final_say_holder_set_in_the_meantime_makes_the_acceptance_fail_and_changes_nothing(env):
    made = invite(env, addr="advisor@example.invalid", final_say=True)
    env.db.data[ob.ENGINES][ENGINE]["final_say_subscriber_id"] = "someone-else"
    assert accept(env.db, made, addr="advisor@example.invalid") is None
    assert ob.address_hash("advisor@example.invalid") not in env.db.data["subscribers"] and ob.MEMBERS not in env.db.data
    assert env.db.data[ob.ENGINES][ENGINE]["final_say_subscriber_id"] == "someone-else"


# ---- (j) every state change writes an event, in the same transaction ------------------------------------------------------------------------------
def test_every_state_change_writes_an_event_and_no_event_holds_an_address_or_a_token(env):
    r = env.client.post("/api/admin/onboarding/invites", json={"engine_id": ENGINE, "email": NEW_ADDR}, headers=ADMIN_KEY)
    raw = env.sent[0]["link"].split("#token=")[1]
    assert [e["action"] for e in events(env.db)] == ["invite"]
    post_accept(env, {"raw_token": raw})
    assert sorted(e["action"] for e in events(env.db)) == ["accept", "consent", "invite"]
    iid = r.json()["invite_id"]
    env.client.delete(f"/api/admin/onboarding/invites/{iid}", headers=ADMIN_KEY)
    unused = invite(env, addr="unused.person@example.invalid")
    env.client.delete(f"/api/admin/onboarding/invites/{unused['invite_id']}", headers=ADMIN_KEY)
    assert sorted(e["action"] for e in events(env.db)) == ["accept", "consent", "invite", "invite", "revoke_invite", "revoke_member"]
    for e in events(env.db):
        assert {"ts", "engine_id", "actor_subscriber_id", "actor_role", "action", "target", "before_sha256", "after_sha256", "ip_hash", "request_id"} <= set(e)
        assert e["engine_id"] == ENGINE and datetime.fromisoformat(e["ts"])
    assert not [s for e in events(env.db) for s in strings(e) if "@" in s or raw in s or NEW_ADDR in s]
    inv_event = events(env.db, "invite")[0]
    assert inv_event["actor_subscriber_id"] == "admin" and inv_event["actor_role"] == "admin"


@pytest.mark.parametrize("scenario", ["create", "accept", "revoke_unused", "revoke_used"])
def test_there_is_no_state_change_without_its_event(env, scenario):
    """If the event cannot be written, the change is not made (they share one transaction)."""
    if scenario == "create":
        env.db.fail_writes_to = {ob.EVENTS}
        with pytest.raises(RuntimeError):
            invite(env)
        assert env.db.data.get(ob.INVITES, {}) == {}
        return
    made = invite(env)
    if scenario in ("revoke_used",):
        accept(env.db, made)
    before_all = json.dumps(env.db.data, sort_keys=True, default=str)
    env.db.fail_writes_to = {ob.EVENTS}
    with pytest.raises(RuntimeError):
        if scenario == "accept":
            accept(env.db, made)
        else:
            ob.revoke_invite(env.db, made["invite_id"], admin_subscriber_id=ADMIN_ID, now=NOW)
    assert json.dumps(env.db.data, sort_keys=True, default=str) == before_all


# ---- revocation (Q17) ---------------------------------------------------------------------------------------------------------------------------------
def test_revoking_a_used_invitation_removes_the_membership_and_clears_generation_but_keeps_the_account(env):
    made = invite(env, addr="advisor@example.invalid", final_say=True)
    accept(env.db, made, addr="advisor@example.invalid")
    sid = ob.address_hash("advisor@example.invalid")
    env.db.data["subscribers"][sid]["podcasts_generated"] = 4
    r = env.client.delete(f"/api/admin/onboarding/invites/{made['invite_id']}", headers=ADMIN_KEY)
    assert r.json() == {"invite_id": made["invite_id"], "outcome": "revoked_member"}
    sub = env.db.data["subscribers"][sid]
    assert sub["can_generate"] is False and "monthly_quota" not in sub and sub["podcasts_generated"] == 4          # the account and its history stay
    assert ob.member_id(ENGINE, sid) not in env.db.data[ob.MEMBERS]
    assert env.db.data[ob.ENGINES][ENGINE]["final_say_subscriber_id"] is None
    assert env.client.get(f"/api/onboarding/engines/{ENGINE}", headers={"X-Subscriber-Token": "none"}).status_code == 404
    assert env.client.delete(f"/api/admin/onboarding/invites/{made['invite_id']}", headers=ADMIN_KEY).json()["outcome"] == "already_revoked"
    assert env.client.delete("/api/admin/onboarding/invites/nonexistent", headers=ADMIN_KEY).status_code == 404


def test_revocation_never_touches_the_administrators_account_or_a_second_membership(env):
    admin_made = ob.create_invite(env.db, engine_id=ENGINE, email=ADMIN_SUBSCRIBER_EMAIL, now=NOW - timedelta(minutes=1))
    env.db.data["subscribers"].pop(ADMIN_ID)
    env.db.data["subscribers"][ADMIN_ID] = {"email": ADMIN_SUBSCRIBER_EMAIL, "can_generate": True, "monthly_quota": None}
    assert accept(env.db, admin_made, addr=ADMIN_SUBSCRIBER_EMAIL) is not None
    env.db.data["subscribers"][ADMIN_ID].update(can_generate=True, monthly_quota=None)
    env.client.delete(f"/api/admin/onboarding/invites/{admin_made['invite_id']}", headers=ADMIN_KEY)
    assert env.db.data["subscribers"][ADMIN_ID]["can_generate"] is True and env.db.data["subscribers"][ADMIN_ID]["monthly_quota"] is None
    # a person who is a member of two engines keeps the generation permission when one invitation is revoked
    one = invite(env, addr="two.engines@example.invalid")
    two = invite(env, addr="two.engines@example.invalid", engine=OTHER_ENGINE)
    accept(env.db, one, addr="two.engines@example.invalid")
    accept(env.db, two, addr="two.engines@example.invalid")
    sid = ob.address_hash("two.engines@example.invalid")
    env.client.delete(f"/api/admin/onboarding/invites/{one['invite_id']}", headers=ADMIN_KEY)
    assert ob.member_id(ENGINE, sid) not in env.db.data[ob.MEMBERS] and ob.member_id(OTHER_ENGINE, sid) in env.db.data[ob.MEMBERS]
    assert env.db.data["subscribers"][sid]["can_generate"] is True and env.db.data["subscribers"][sid]["monthly_quota"] == 10


# ---- an accepted invitation's account can generate, counted against quota 10 --------------------------------------------------------------------------
def test_an_accepted_invitations_account_can_generate_and_is_counted_against_quota_10(env):
    import utils.generation_quota as gq
    made = invite(env)
    assert post_accept(env, made).status_code == 200
    sid = ob.address_hash(NEW_ADDR)
    for n in range(1, 11):
        quota, count = gq.check_and_increment_quota(env.db, sid)
        assert (quota, count) == (10, n)
    with pytest.raises(gq.QuotaExceeded) as e:
        gq.check_and_increment_quota(env.db, sid)
    assert str(e.value) == "monthly limit reached"
    # and an account that registered without an invitation cannot generate at all
    env.db.data["subscribers"]["plain"] = {"email": "plain@example.invalid"}
    with pytest.raises(gq.GenerationNotAllowed):
        gq.check_and_increment_quota(env.db, "plain")


# ---- no address, token or password reaches a log line or stdout --------------------------------------------------------------------------------------
def test_no_address_token_or_password_reaches_any_log_or_stdout(env, capsys, caplog):
    import logging
    caplog.set_level(logging.DEBUG)
    env.client.post("/api/admin/onboarding/invites", json={"engine_id": ENGINE, "email": NEW_ADDR}, headers=ADMIN_KEY)
    raw = env.sent[0]["link"].split("#token=")[1]
    post_accept(env, {"raw_token": raw}, password="distinctive-password-77")
    post_accept(env, {"raw_token": raw})                                            # a refused second use
    post_accept(env, {"raw_token": "garbage"}, addr="other@example.invalid")        # and a refused guess
    out = capsys.readouterr()
    text = out.out + out.err + "\n".join(r.getMessage() for r in caplog.records)
    assert "Invitation" in text                                                      # something was logged, so the scan below means something
    assert NEW_ADDR not in text and raw not in text and "distinctive-password-77" not in text and EMAIL_SHAPED.findall(text) == []


def test_the_invitation_email_sender_prints_no_address_and_no_link(capsys):
    import asyncio
    from unittest.mock import patch
    import email_service as email_module
    with patch.dict("os.environ", {"NOTIFICATION_EMAIL": "site@example.invalid", "NOTIFICATION_EMAIL_PASSWORD": "not-a-real-secret"}):
        svc = email_module.EmailService()
    link = ob.ACCEPT_PAGE_URL + "#token=SECRETTOKENVALUE"
    sent = []
    loop = asyncio.new_event_loop()
    try:
        with patch.object(email_module.smtplib, "SMTP") as smtp:
            smtp.return_value.__enter__.return_value.send_message.side_effect = lambda m: sent.append(m)
            assert loop.run_until_complete(svc.send_invitation_email(NEW_ADDR, link, 7)) is True
        with patch.object(email_module.smtplib, "SMTP", side_effect=OSError(f"recipient refused: <{NEW_ADDR}>")):
            assert loop.run_until_complete(svc.send_invitation_email(NEW_ADDR, link, 7)) is False
    finally:
        loop.close()
    text = capsys.readouterr().out
    assert NEW_ADDR not in text and "SECRETTOKENVALUE" not in text and EMAIL_SHAPED.findall(text) == []
    body = sent[0].get_payload()[0].get_payload(decode=True).decode()
    assert "SECRETTOKENVALUE" in body and "expires in 7 days" in body and "CopernicusAI" in body
    assert "podcast" not in body.lower() and "research" not in body.lower()           # plain wording, no research content
    assert sent[0]["From"].startswith("CopernicusAI")                                  # the site's existing sender, signed by the site


# ---- the pages and the route headers ------------------------------------------------------------------------------------------------------------------
def read(p):
    return Path(p).read_text(encoding="utf-8").replace("\r\n", "\n")


def test_the_accept_page_has_a_strict_csp_no_inline_or_third_party_script_and_posts_the_routes_fields():
    from endpoints.onboarding.routes import AcceptRequest, Consent
    html, js = read(ROOT / "public/onboarding/accept.html"), read(ROOT / "public/onboarding/accept.js")
    assert "noindex" in html and "script-src 'self'" in html and "default-src 'none'" in html and "unsafe-inline" not in html and "unsafe-eval" not in html
    scripts = re.findall(r"<script\b[^>]*>", html)
    assert scripts == ['<script src="accept.js">'] and "http" not in scripts[0]
    assert not re.search(r"<script[^>]*>[^<]+</script>", html) and " onclick=" not in html and " style=" not in html and "<style" not in html
    assert "innerHTML" not in js and "outerHTML" not in js and "document.write" not in js and "eval(" not in js
    assert "textContent" in js and "history.replaceState" in js and "/api/onboarding/invites/accept" in js
    sent = set(re.findall(r"^\s{12}(token|email|name|password|consent):", js, re.M)) | {"token", "email", "name", "password", "consent"}
    assert sent == set(AcceptRequest.model_fields)                                  # the page sends exactly the fields the route expects
    assert set(re.findall(r"\b(naming|licence_confirmed|licence_other|lookups|acknowledged):", js)) == set(Consent.model_fields)
    assert "location.search" not in js and "?token" not in js                         # the token is read from the fragment only


@pytest.mark.parametrize("src", ["/onboarding/(.*)", "/admin-(?:onboarding|review)(.*)"])
def test_vercel_serves_the_onboarding_pages_with_strict_headers(src):
    cfg = json.loads(read(ROOT / "vercel.json"))
    route = next(r for r in cfg["routes"] if r.get("src") == src)
    assert cfg["routes"].index(route) < next(i for i, r in enumerate(cfg["routes"]) if r.get("src") == "/(.*)")        # before the catch-all
    h = route["headers"]
    assert route.get("continue") is True and "script-src 'self'" in h["Content-Security-Policy"] and "frame-ancestors 'none'" in h["Content-Security-Policy"]
    assert h["X-Robots-Tag"].startswith("noindex") and h["Referrer-Policy"] == "no-referrer" and h["Cache-Control"] == "no-store"


def test_the_admin_invitation_page_is_strict_sends_the_admin_key_and_renders_text_only():
    from endpoints.onboarding.routes import InviteCreate
    html, js = read(ROOT / "public/admin-onboarding.html"), read(ROOT / "public/admin-onboarding.js")
    assert "noindex" in html and "script-src 'self'" in html and "unsafe-inline" not in html and re.findall(r"<script\b[^>]*>", html) == ['<script src="admin-onboarding.js">', '<script src="admin-review.js">']
    assert not re.search(r"<script[^>]*>[^<]+</script>", html) and " onclick=" not in html and "<style" not in html
    assert "/api/admin/onboarding/invites" in js and "'X-Admin-API-Key': readKey()" in js and "method: 'POST'" in js and "method: 'DELETE'" in js
    assert "innerHTML" not in js and "eval(" not in js and "textContent" in js and "$('invEmail').value = ''" in js                # the address is cleared after sending
    assert "?email" not in js and "email=" not in js                                    # the address is never put in a URL
    assert "'admin_api_key'" in js and "localStorage.setItem" in js                       # the same browser-storage name the admin dashboard uses
    assert set(re.findall(r"^\s{12}(engine_id|email|final_say|can_generate|monthly_quota|expires_days):", js, re.M)) == set(InviteCreate.model_fields)
    dash = read(ROOT / "public/admin-dashboard.html")
    assert 'href="admin-onboarding.html"' in dash and "sendInvitation" not in dash


# ---- guards that other guards would otherwise mask ---------------------------------------------------------------------------------------------------
def test_a_used_invitation_cannot_be_reused_even_after_its_membership_is_gone(env):
    """Single use is enforced by the invitation itself, not only by 'already a member'."""
    made = invite(env)
    assert accept(env.db, made) is not None
    sid = ob.address_hash(NEW_ADDR)
    env.db.data[ob.MEMBERS].pop(ob.member_id(ENGINE, sid))            # the membership disappears by some other route
    env.db.data["subscribers"].pop(sid)                               # and so does the account
    assert accept(env.db, made) is None
    assert sid not in env.db.data["subscribers"] and ob.MEMBERS in env.db.data and env.db.data[ob.MEMBERS] == {}


def test_the_transaction_rechecks_the_token_and_the_address_itself(env):
    """find_invite_by_token already selects by the token's hash; the transaction must still refuse if the invitation it re-reads does not match (a change
    between the lookup and the commit)."""
    made = invite(env)
    iid = made["invite_id"]
    good_token, good_addr = hash_token(made["raw_token"]), ob.address_hash(NEW_ADDR)
    sid, acct = ob.address_hash(NEW_ADDR), {"name": "n", "password_hash": "scrypt$00$11", "subscriber_id": ob.address_hash(NEW_ADDR), "email": NEW_ADDR}
    def run(token_hash, addr_hash):
        return run_in_transaction(env.db, ob._accept_in, env.db, iid, token_hash, addr_hash, sid, acct, dict(CONSENT), NOW, None, None)
    assert run(hash_token("a different token"), good_addr) is None
    assert run(good_token, ob.address_hash("another@example.invalid")) is None
    assert env.db.data[ob.INVITES][iid]["used_at"] is None and sid not in env.db.data["subscribers"]
    assert run(good_token, good_addr) is not None


def test_the_gate_is_on_the_engine_router_so_a_future_route_is_denied_by_default(env):
    assert any(d.dependency is env.routes.engine_gate for d in env.routes.engine_router.dependencies)
    probe_router = env.routes.engine_router

    async def probe():
        return {"leak": "a route that forgot its own guard"}
    probe_router.add_api_route("/probe", probe, methods=["GET"])
    try:
        app = FastAPI()
        app.include_router(probe_router)
        c = TestClient(app)
        for headers in ({}, {"X-Subscriber-Token": "zzz"}):
            r = c.get(f"/api/onboarding/engines/{ENGINE}/probe", headers=headers)
            assert (r.status_code, r.json()) == (404, {"detail": "Not found"})
        assert c.get(f"/api/onboarding/engines/{ENGINE}/probe", headers=ADMIN_KEY).status_code == 200      # the gate let the admin through, so the route is reachable at all
    finally:
        probe_router.routes.pop()


# ---- listing invitations (admin) -----------------------------------------------------------------------------------------------------------------
LIST_FIELDS = {"invite_id", "engine_id", "status", "final_say", "can_generate", "monthly_quota", "created_at", "expires_at", "used_at", "revoked_at"}
FORBIDDEN_FIELDS = {"email_sha256", "token_hash", "used_by_subscriber_id", "email", "token", "created_by", "revoked_by", "roles"}


def list_url(engine=ENGINE):
    return f"/api/admin/onboarding/invites?engine_id={engine}"


def test_the_invitation_list_is_admin_only(env):
    invite(env)
    for headers in ({}, {"X-Admin-API-Key": "wrong"}, {"X-Subscriber-Token": "tok"}):
        assert env.client.get(list_url(), headers=headers).status_code in (401, 403)
    assert env.client.get(list_url(), headers=ADMIN_KEY).status_code == 200
    assert env.client.get("/api/admin/onboarding/invites", headers=ADMIN_KEY).status_code == 422          # engine_id is required
    assert env.client.get(list_url("Bad_Id"), headers=ADMIN_KEY).status_code == 400
    assert env.client.get(list_url("a__b"), headers=ADMIN_KEY).status_code == 400
    assert env.client.get(list_url("no-such-engine"), headers=ADMIN_KEY).json() == {"engine_id": "no-such-engine", "invites": []}


def test_the_list_has_exactly_the_allowed_fields_and_no_hash_address_or_token(env):
    made = invite(env, addr="listed.person@example.invalid")
    accept(env.db, made, addr="listed.person@example.invalid")
    invite(env, addr="second.person@example.invalid", engine=ENGINE, final_say=True)
    r = env.client.get(list_url(), headers=ADMIN_KEY)
    rows = r.json()["invites"]
    assert len(rows) == 2 and all(set(row) == LIST_FIELDS for row in rows)                          # the keys, exactly
    assert not any(set(row) & FORBIDDEN_FIELDS for row in rows)
    stored = list(env.db.data[ob.INVITES].values())
    secrets_in_store = {s for inv in stored for k in ("email_sha256", "token_hash", "used_by_subscriber_id") for s in [inv.get(k)] if s}
    assert secrets_in_store and not [s for s in secrets_in_store if s in r.text]                    # none of the stored hashes or ids appears anywhere in the response
    assert "@" not in r.text and "example.invalid" not in r.text and made["raw_token"] not in r.text


def test_the_status_of_each_of_the_four_states_is_computed_correctly(env):
    env.mp.setattr(ob, "_utcnow", lambda: NOW)
    unused = invite(env, addr="unused@example.invalid")
    used = invite(env, addr="used@example.invalid")
    accept(env.db, used, addr="used@example.invalid")
    revoked = invite(env, addr="revoked@example.invalid")
    env.client.delete(f"/api/admin/onboarding/invites/{revoked['invite_id']}", headers=ADMIN_KEY)
    used_then_revoked = invite(env, addr="gone@example.invalid")
    accept(env.db, used_then_revoked, addr="gone@example.invalid")
    env.client.delete(f"/api/admin/onboarding/invites/{used_then_revoked['invite_id']}", headers=ADMIN_KEY)
    expired = ob.create_invite(env.db, engine_id=ENGINE, email="expired@example.invalid", expires_days=1, now=NOW - timedelta(days=5))
    status = {row["invite_id"]: row["status"] for row in env.client.get(list_url(), headers=ADMIN_KEY).json()["invites"]}
    assert status == {unused["invite_id"]: "unused", used["invite_id"]: "used", revoked["invite_id"]: "revoked",
                      used_then_revoked["invite_id"]: "revoked", expired["invite_id"]: "expired"}            # revoked wins over used; a past expiry reads expired
    env.mp.setattr(ob, "_utcnow", lambda: NOW + timedelta(days=8))                                            # the clock moves (mocked, no waiting): the unused one expires
    later = {row["invite_id"]: row["status"] for row in env.client.get(list_url(), headers=ADMIN_KEY).json()["invites"]}
    assert later[unused["invite_id"]] == "expired" and later[used["invite_id"]] == "used" and later[revoked["invite_id"]] == "revoked"


def test_the_list_is_per_engine_newest_first_and_carries_the_dates_and_flags(env):
    first = ob.create_invite(env.db, engine_id=ENGINE, email="first@example.invalid", final_say=True, monthly_quota=4, now=NOW - timedelta(hours=2))
    second = ob.create_invite(env.db, engine_id=ENGINE, email="second@example.invalid", can_generate=False, monthly_quota=None, now=NOW - timedelta(hours=1))
    other = ob.create_invite(env.db, engine_id=OTHER_ENGINE, email="elsewhere@example.invalid", now=NOW)
    rows = env.client.get(list_url(), headers=ADMIN_KEY).json()["invites"]
    assert [r["invite_id"] for r in rows] == [second["invite_id"], first["invite_id"]]                        # newest first, the other engine's invitation is not here
    assert other["invite_id"] not in {r["invite_id"] for r in rows}
    by_id = {r["invite_id"]: r for r in rows}
    assert (by_id[first["invite_id"]]["final_say"], by_id[first["invite_id"]]["monthly_quota"], by_id[first["invite_id"]]["can_generate"]) == (True, 4, True)
    assert (by_id[second["invite_id"]]["can_generate"], by_id[second["invite_id"]]["monthly_quota"]) == (False, None)
    assert by_id[first["invite_id"]]["used_at"] is None and by_id[first["invite_id"]]["revoked_at"] is None and by_id[first["invite_id"]]["expires_at"]
    assert env.client.get(list_url(OTHER_ENGINE), headers=ADMIN_KEY).json()["invites"][0]["invite_id"] == other["invite_id"]


def test_the_list_route_is_rate_limited_failing_closed_and_the_admin_page_shows_it_safely(env):
    env.client.get(list_url(), headers=ADMIN_KEY)
    assert env.limited[-1][0][1] == "onboarding_invite_list" and env.limited[-1][1].get("fail_closed") is True
    js, html = read(ROOT / "public/admin-onboarding.js"), read(ROOT / "public/admin-onboarding.html")
    start = js.index("function cell(")
    code = js[start:js.index("$('loadList').addEventListener")]
    assert "id=\"loadList\"" in html and "id=\"inviteList\"" in html
    assert "/api/admin/onboarding/invites?engine_id=' + encodeURIComponent(engine)" in code and "headers: headers()" in code
    assert "createElement" in code and "textContent" in code and "innerHTML" not in code and "insertAdjacentHTML" not in code
    assert "window.confirm(" in js and "inv.status !== 'revoked'" in code and "revoke(inv.invite_id)" in code        # a Revoke button per row, with a confirmation
    for forbidden in FORBIDDEN_FIELDS - {"email", "token", "roles"}:
        assert forbidden not in js, forbidden
