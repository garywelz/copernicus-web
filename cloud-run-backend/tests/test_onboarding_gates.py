"""Onboarding PR 3a-2: the first gate (Mark final, one section or every ready section), delegation of final say, and the e-mails to the final-say owner
(design 3.2, 4.5, 4.6, 5.6, 5.7). Offline: an in-memory Firestore with atomic transactions, a recorded mail service, a mocked clock. No address, token or answer
text appears in any assertion about what is logged or sent."""
import asyncio
import json
import re
from email import message_from_string  # noqa: F401
from unittest.mock import patch

import pytest

import email_service as email_module
from config.constants import ADMIN_SUBSCRIBER_EMAIL
from tests import fakes_pr1
from tests.test_onboarding_items import ADMIN, ADV, CONSENT, H, OTH, STRANGER, T0, TOK, X, Y, YMEM, env, events, put, q, snapshot, stored, strings  # noqa: F401
from tests.test_onboarding_workspace import comment, progress, row, section_doc, section_json, set_section
from utils import onboarding as ob
from utils import onboarding_form as form
from utils import onboarding_gates as gates
from utils.subscriber_helpers import generate_subscriber_id

BASE = f"/api/onboarding/engines/{X}"
OWN3 = "sub-own3"
SECRET = "SECRETANSWER"
PAYLOAD = {"scope-statement": (f"{SECRET} one", None), "use-case": (f"{SECRET} two", None), "out-of-scope": ([f"{SECRET} three"], None),
           "ex-q1": (q(f"{SECRET}?"), "accept"), "ex-q2": (q(), "accept"), "ex-q3": (q(), "accept"),
           "kw-1": ({"list": "mute", "text": SECRET}, "keep"), "kw-2": ({"list": "mute", "text": "t"}, "keep"),
           "seed-1": ({"comment": SECRET}, "yes"), "seed-2": ({"comment": ""}, "yes")}
IDS = {"scope": ["scope-statement", "use-case", "out-of-scope"], "questions": ["ex-q1", "ex-q2", "ex-q3"], "keywords": ["kw-1", "kw-2"], "seeds": ["seed-1", "seed-2"]}


def answer(env, who, section, upto=None):
    """Answer a section's items through the real route (so notifications fire as they would)."""
    for item_id in IDS[section][:upto]:
        value, choice = PAYLOAD[item_id]
        assert put(env, who, item_id, value, choice, base=0).status_code == 200


def answer_quietly(env, section):
    """Mark every item of a section answered, directly in storage (no route, so no notification)."""
    for item_id in IDS[section]:
        it = stored(env, item_id, section)
        it["value"], it["choice"], it["revision"] = PAYLOAD[item_id][0], PAYLOAD[item_id][1], 1


def final(env, who, section="scope", engine=X):
    return env.client.post(f"/api/onboarding/engines/{engine}/sections/{section}/final", headers=H[who] if who in H else ADMIN)


def final_all(env, who, engine=X):
    return env.client.post(f"/api/onboarding/engines/{engine}/sections/final-all", headers=H[who] if who in H else ADMIN)


def delegate(env, who=ADV, scope="all", to="other_owner"):
    return env.client.put(f"{BASE}/delegations", json={"to": to, "scope": scope}, headers=H[who])


def revoke(env, delegation_id, who=ADV):
    return env.client.delete(f"{BASE}/delegations/{delegation_id}", headers=H[who])


def add_third_owner(env):
    env.db.data["subscribers"][OWN3] = fakes_pr1.subscriber("tok-own3", email="sub-own3@example.invalid")
    env.db.data[ob.MEMBERS][ob.member_id(X, OWN3)] = {"engine_id": X, "subscriber_id": OWN3, "role": "owner", "final_say": False, "status": "active", "consent": CONSENT}
    H[OWN3] = {"X-Subscriber-Token": "tok-own3"}


@pytest.fixture(autouse=True)
def _cleanup_header():
    yield
    H.pop(OWN3, None)


# ---- the state machine: draft to final only when ready ---------------------------------------------------------------------------------------------
@pytest.mark.parametrize("status,ready,code,reason", [
    ("draft", True, 200, None), ("draft", False, 409, "not_ready"), ("final", True, 409, "already_final"),
    ("approved", True, 409, "approved"), ("rejected", True, 409, "rejected"), ("approved", False, 409, "approved"), ("rejected", False, 409, "rejected")])
def test_mark_final_transition_table(env, status, ready, code, reason):
    if ready:
        answer_quietly(env, "scope")
    if status != "draft":
        set_section(env, "scope", status, final_by=ADV, approved_at="2026-11-01")
    before = snapshot(env.db)
    r = final(env, ADV)
    assert r.status_code == code, r.text
    if code == 200:
        assert r.json()["status"] == "final" and section_doc(env, "scope")["status"] == "final"
    else:
        assert r.json()["detail"]["reason"] == reason and snapshot(env.db) == before                         # a refusal changes nothing
    if reason == "not_ready":
        assert (r.json()["detail"]["open"], r.json()["detail"]["disagreed"]) == (3, 0)


def test_a_disagreement_blocks_final_until_resolved_and_an_empty_section_is_never_final(env):
    answer_quietly(env, "scope")
    c = comment(env, OTH, "use-case", "No.", kind="disagree").json()
    r = final(env, ADV)
    assert r.status_code == 409 and r.json()["detail"]["reason"] == "not_ready" and r.json()["detail"]["disagreed"] == 1
    assert env.client.post(f"{BASE}/comments/{c['comment_id']}/resolve", headers=H[OTH]).status_code == 200
    assert final(env, ADV).status_code == 200
    env.db.data["onboarding_items"] = {k: v for k, v in env.db.data["onboarding_items"].items() if v["section"] != "seeds"}          # no seed items at all
    assert final(env, ADV, "seeds").status_code == 409


def test_final_then_any_owner_edit_returns_the_section_to_draft(env):
    answer_quietly(env, "scope")
    assert final(env, ADV).status_code == 200
    assert put(env, OTH, "use-case", "changed", base=1).status_code == 200
    sec = section_doc(env, "scope")
    assert sec["status"] == "draft" and sec["final_by"] is None and sec["reopened_by"] == OTH
    assert final(env, ADV).status_code == 200                                                              # and it can be marked final again


def test_what_a_final_records_who_when_the_hash_the_revision_and_whether_by_delegation(env):
    answer_quietly(env, "scope")
    r = final(env, ADV)
    assert r.json()["via_delegation"] is False and r.json()["progress"]["sections"][0]["status"] == "final"
    sec = section_doc(env, "scope")
    assert (sec["status"], sec["final_by"], sec["final_via_delegation"], sec["revision"], sec["ready_notified"]) == ("final", ADV, False, 1, False)
    assert sec["final_at"] and sec["content_sha256"] == section_json(env, ADV, "scope")["section"]["content_sha256"]          # the hash 3b will approve
    (e,) = events(env.db, "final")
    assert (e["engine_id"], e["actor_subscriber_id"], e["actor_role"], e["target"], e["section"], e["revision"], e["via_delegation"], e["content_sha256"]) == (
        X, ADV, "owner", "scope", "scope", 1, False, sec["content_sha256"])
    assert e["ts"] and "ip_hash" in e and "request_id" in e and not [s for s in strings(e) if "@" in s]
    assert section_json(env, OTH, "scope")["section"]["status"] == "final" and row(progress(env), "scope")["final"] == 3


def test_a_final_on_a_closed_engine_or_an_unknown_section_is_refused(env):
    answer_quietly(env, "scope")
    env.db.data[ob.ENGINES][X]["state"] = "closed"
    assert final(env, ADV).status_code == 409 and section_doc_exists(env) is False
    env.db.data[ob.ENGINES][X]["state"] = "open"
    for bad in ("nope", "SCOPE", "scope__x"):
        assert final(env, ADV, bad).status_code == 404


def section_doc_exists(env):
    return form.section_doc_id(X, "scope") in env.db.data.get("onboarding_sections", {})


# ---- who may mark final -------------------------------------------------------------------------------------------------------------------------------
def test_only_the_holder_or_a_delegate_for_that_section_may_mark_final(env):
    answer_quietly(env, "scope")
    before = snapshot(env.db)
    r = final(env, OTH)                                                                                     # a member, but neither the holder nor a delegate
    assert r.status_code == 403 and "final-say" in r.json()["detail"] and snapshot(env.db) == before
    assert final_all(env, OTH).status_code == 403 and snapshot(env.db) == before
    assert final(env, ADV).status_code == 200


def test_an_administrator_gets_404_on_both_final_routes_and_so_does_everyone_outside(env):
    answer_quietly(env, "scope")
    before = snapshot(env.db)
    for call in (lambda: final(env, "admin"), lambda: final_all(env, "admin"), lambda: final(env, STRANGER), lambda: final_all(env, STRANGER),
                 lambda: final(env, YMEM), lambda: final_all(env, YMEM), lambda: final(env, ADV, engine=Y), lambda: final_all(env, ADV, engine=Y)):
        r = call()
        assert (r.status_code, r.json()) == (404, {"detail": "Not found"})
    assert snapshot(env.db) == before
    assert section_doc_exists(env) is False


def test_the_holder_needs_consent_like_every_owner_route(env):
    answer_quietly(env, "scope")
    del env.db.data[ob.MEMBERS][ob.member_id(X, ADV)]["consent"]
    assert final(env, ADV).status_code == 409


def test_the_holder_is_the_one_the_engine_record_names_not_a_flag_on_a_membership(env):
    answer_quietly(env, "scope")
    env.db.data[ob.MEMBERS][ob.member_id(X, OTH)]["final_say"] = True                                       # a stray flag does not make a holder
    assert final(env, OTH).status_code == 403
    env.db.data[ob.ENGINES][X]["final_say_subscriber_id"] = OTH                                             # succession (an audited admin action) moves the power
    assert final(env, ADV).status_code == 403 and final(env, OTH).status_code == 200


def test_an_engine_with_no_holder_has_nobody_who_may_mark_final_not_even_an_empty_or_missing_id(env):
    answer_quietly(env, "scope")
    env.db.data[ob.ENGINES][X]["final_say_subscriber_id"] = None
    for who in (None, "", OTH, ADV):
        with pytest.raises(form.FormError) as ex:
            gates.mark_final(env.db, engine_id=X, section="scope", subscriber_id=who)
        assert ex.value.status == 403, who
        with pytest.raises(form.FormError) as ex:
            gates.create_delegation(env.db, engine_id=X, subscriber_id=who, to_subscriber_id=OTH, scope="all")
        assert ex.value.status == 403, who
    assert gates.authority_view(env.db, X, env.db.data[ob.ENGINES][X], ADV) == {"can_mark_final": False, "may_mark": []}


# ---- final-all ------------------------------------------------------------------------------------------------------------------------------------------
def test_final_all_marks_the_ready_sections_and_lists_the_rest_with_one_event_each(env):
    answer_quietly(env, "scope")
    answer_quietly(env, "questions")
    stored(env, "kw-1", "keywords")["revision"] = 1                                                          # keywords half answered
    r = final_all(env, ADV)
    assert r.status_code == 200
    out = r.json()
    assert out["marked"] == ["scope", "questions"] and out["via_delegation"] is False
    assert out["skipped"] == [{"section": "keywords", "reason": "not_ready"}, {"section": "seeds", "reason": "not_ready"}]
    assert [s["status"] for s in out["progress"]["sections"]] == ["final", "final", "draft", "draft"]
    evs = events(env.db, "final_all")
    assert sorted(e["target"] for e in evs) == ["questions", "scope"] and len(evs) == 2 and not events(env.db, "final")
    assert all(e["actor_subscriber_id"] == ADV and e["content_sha256"] and e["via_delegation"] is False for e in evs)
    again = final_all(env, ADV).json()
    assert again["marked"] == [] and {s["section"]: s["reason"] for s in again["skipped"]} == {"scope": "already_final", "questions": "already_final", "keywords": "not_ready", "seeds": "not_ready"}
    assert len(events(env.db, "final_all")) == 2                                                             # nothing new was recorded


def test_final_all_leaves_approved_and_rejected_sections_alone(env):
    for s in ("scope", "questions", "keywords"):
        answer_quietly(env, s)
    set_section(env, "scope", "approved", approved_at="2026-11-01")
    set_section(env, "questions", "rejected")
    out = final_all(env, ADV).json()
    assert out["marked"] == ["keywords"] and {s["section"]: s["reason"] for s in out["skipped"]} == {"scope": "approved", "questions": "rejected", "seeds": "not_ready"}


def test_a_delegate_final_all_marks_only_the_delegated_sections_and_lists_the_others_as_not_delegated(env):
    for s in ("scope", "questions", "keywords"):
        answer_quietly(env, s)
    assert delegate(env, scope=["scope", "keywords"]).status_code == 200
    out = final_all(env, OTH).json()
    assert out["marked"] == ["scope", "keywords"] and out["via_delegation"] is True
    assert {s["section"]: s["reason"] for s in out["skipped"]} == {"questions": "not_delegated", "seeds": "not_delegated"}
    assert all(section_doc(env, k)["final_via_delegation"] is True and section_doc(env, k)["final_by"] == OTH for k in ("scope", "keywords"))
    assert all(e["via_delegation"] is True for e in events(env.db, "final_all"))


# ---- delegation -------------------------------------------------------------------------------------------------------------------------------------
def test_a_delegation_is_created_by_the_holder_and_shown_without_any_id(env):
    r = delegate(env, scope=["scope", "questions"])
    assert r.status_code == 200
    d = r.json()
    assert (d["from"], d["to"], d["scope"], d["active"], d["revoked_at"]) == ("you", "other owner", ["scope", "questions"], True, None) and re.fullmatch(r"[0-9a-f]{32}", d["delegation_id"])
    stored_d = env.db.data["onboarding_delegations"][d["delegation_id"]]
    assert (stored_d["engine_id"], stored_d["from_subscriber_id"], stored_d["to_subscriber_id"], stored_d["revoked_at"]) == (X, ADV, OTH, None)
    assert env.db.data[ob.ENGINES][X]["active_delegation_id"] == d["delegation_id"]
    (e,) = events(env.db, "delegate")
    assert (e["actor_subscriber_id"], e["delegation_id"], e["scope"], e["delegate_subscriber_id"], e["engine_id"]) == (ADV, d["delegation_id"], ["scope", "questions"], OTH, X)
    got = env.client.get(f"{BASE}/delegations", headers=H[ADV]).json()["delegations"]
    assert got == [d]
    for text in (r.text, json.dumps(got)):
        assert ADV not in text and OTH not in text


def test_a_delegate_marks_only_the_delegated_sections_and_the_holder_still_can(env):
    answer_quietly(env, "scope")
    answer_quietly(env, "questions")
    delegate(env, scope=["scope"])
    other = final(env, OTH, "questions")
    assert other.status_code == 403 and other.json()["detail"]["reason"] == "not_delegated" and section_doc_exists(env) is False
    ok = final(env, OTH, "scope")
    assert ok.status_code == 200 and ok.json()["via_delegation"] is True
    assert (section_doc(env, "scope")["final_by"], section_doc(env, "scope")["final_via_delegation"]) == (OTH, True)
    assert events(env.db, "final")[0]["via_delegation"] is True
    assert final(env, ADV, "questions").status_code == 200                                                   # the holder keeps the power while a delegation is active
    assert section_doc(env, "questions")["final_via_delegation"] is False


def test_a_delegation_gives_the_power_to_the_named_owner_alone_not_to_every_owner(env):
    answer_quietly(env, "scope")
    delegate(env, scope="all")
    add_third_owner(env)                                                                                     # an owner who is neither the holder nor the delegate
    before = snapshot(env.db)
    assert final(env, OWN3).status_code == 403 and final_all(env, OWN3).status_code == 403 and snapshot(env.db) == before
    assert gates.authority_view(env.db, X, env.db.data[ob.ENGINES][X], OWN3) == {"can_mark_final": False, "may_mark": []}
    assert final(env, OTH).status_code == 200


def test_a_delegation_record_of_another_engine_confers_nothing(env):
    answer_quietly(env, "scope")
    env.db.data["onboarding_delegations"] = {"e" * 32: {"engine_id": Y, "from_subscriber_id": ADV, "to_subscriber_id": OTH, "scope": "all", "created_at": "t", "revoked_at": None}}
    env.db.data[ob.ENGINES][X]["active_delegation_id"] = "e" * 32                                            # a stray pointer
    assert final(env, OTH).status_code == 403


def test_a_scope_of_all_covers_every_section(env):
    for s in IDS:
        answer_quietly(env, s)
    delegate(env, scope="all")
    assert final_all(env, OTH).json()["marked"] == ["scope", "questions", "keywords", "seeds"]


def test_revocation_takes_effect_on_the_very_next_action_and_is_audited_once(env):
    answer_quietly(env, "scope")
    answer_quietly(env, "questions")
    d = delegate(env).json()
    assert final(env, OTH, "scope").status_code == 200
    r = revoke(env, d["delegation_id"])
    assert r.status_code == 200 and r.json()["active"] is False and r.json()["revoked_at"]
    assert env.db.data[ob.ENGINES][X]["active_delegation_id"] is None and env.db.data["onboarding_delegations"][d["delegation_id"]]["revoked_by"] == ADV
    before = snapshot(env.db)
    assert final(env, OTH, "questions").status_code == 403 and final_all(env, OTH).status_code == 403
    assert snapshot(env.db) == before
    (e,) = events(env.db, "revoke_delegation")
    assert (e["actor_subscriber_id"], e["delegation_id"], e["replaced"]) == (ADV, d["delegation_id"], False)
    assert revoke(env, d["delegation_id"]).status_code == 200 and len(events(env.db, "revoke_delegation")) == 1       # idempotent: no second event


def test_a_delegate_cannot_delegate_or_revoke_and_other_owners_cannot_either(env):
    d = delegate(env).json()
    add_third_owner(env)                                                                                     # made first: with three owners 'the other owner' is ambiguous
    before = snapshot(env.db)
    for who in (OTH, OWN3):                                                                                  # the delegate, and an owner with no power at all
        assert delegate(env, who).status_code == 403
        assert revoke(env, d["delegation_id"], who).status_code == 403
    assert snapshot(env.db) == before


def test_a_delegate_reads_their_own_and_other_owners_see_none_and_an_admin_gets_404(env):
    d = delegate(env, scope=["seeds"]).json()
    add_third_owner(env)
    mine = env.client.get(f"{BASE}/delegations", headers=H[OTH]).json()["delegations"]
    assert len(mine) == 1 and (mine[0]["from"], mine[0]["to"], mine[0]["scope"]) == ("advisor", "you", ["seeds"])
    assert env.client.get(f"{BASE}/delegations", headers=H[OWN3]).json() == {"delegations": []}
    assert env.client.get(f"{BASE}/delegations", headers=ADMIN).status_code == 404
    assert env.client.put(f"{BASE}/delegations", json={"to": "other_owner", "scope": "all"}, headers=ADMIN).status_code == 404
    assert env.client.delete(f"{BASE}/delegations/{d['delegation_id']}", headers=ADMIN).status_code == 404


@pytest.mark.parametrize("scope", [[], ["nope"], ["scope", "scope"], "some", "ALL", 5, None, ["scope", "questions", "keywords", "seeds", "scope"], [["scope"]]])
def test_a_bad_scope_is_refused_and_nothing_is_written(env, scope):
    before = snapshot(env.db)
    assert delegate(env, scope=scope).status_code in (400, 422) and snapshot(env.db) == before


def test_the_delegate_must_be_the_other_owner(env):
    assert delegate(env, to="someone").status_code == 400 and delegate(env, to="sub-oth").status_code == 400
    del env.db.data[ob.MEMBERS][ob.member_id(X, OTH)]                                                       # the holder is the only owner
    assert delegate(env).status_code == 409
    env.db.data[ob.MEMBERS][ob.member_id(X, OTH)] = {"engine_id": X, "subscriber_id": OTH, "role": "owner", "status": "active", "consent": CONSENT}
    add_third_owner(env)
    assert delegate(env).status_code == 409                                                                  # two other owners: "the other owner" is ambiguous
    assert not env.db.data.get("onboarding_delegations") and events(env.db, "delegate") == [] and "active_delegation_id" not in env.db.data[ob.ENGINES][X]


def test_the_function_refuses_a_non_member_an_admin_an_outsider_and_oneself(env):
    admin_id = generate_subscriber_id(ADMIN_SUBSCRIBER_EMAIL)
    env.db.data[ob.MEMBERS][ob.member_id(X, admin_id)] = {"engine_id": X, "subscriber_id": admin_id, "role": "owner", "status": "active", "consent": CONSENT}   # even as a member
    env.db.data[ob.MEMBERS][ob.member_id(X, "sub-gone")] = {"engine_id": X, "subscriber_id": "sub-gone", "role": "owner", "status": "revoked", "consent": CONSENT}
    env.db.data[ob.MEMBERS][ob.member_id(X, "sub-viewer")] = {"engine_id": X, "subscriber_id": "sub-viewer", "role": "viewer", "status": "active", "consent": CONSENT}
    before = snapshot(env.db)
    for to in (STRANGER, YMEM, admin_id, ADV, "", None, "sub-gone", "sub-viewer", "admin"):
        with pytest.raises(form.FormError) as ex:
            gates.create_delegation(env.db, engine_id=X, subscriber_id=ADV, to_subscriber_id=to, scope="all")
        assert ex.value.status == 400, to
    assert snapshot(env.db) == before
    with pytest.raises(form.FormError) as ex:
        gates.create_delegation(env.db, engine_id=X, subscriber_id=OTH, to_subscriber_id=ADV, scope="all")      # a non-holder cannot, whoever they name
    assert ex.value.status == 403
    assert gates.create_delegation(env.db, engine_id=X, subscriber_id=ADV, to_subscriber_id=OTH, scope="all")["to"] == "other owner"


def test_a_new_delegation_replaces_the_old_with_a_revoke_event_and_a_create_event(env):
    first = delegate(env, scope="all").json()
    second = delegate(env, scope=["seeds"]).json()
    assert first["delegation_id"] != second["delegation_id"] and second["active"] is True
    rows = env.client.get(f"{BASE}/delegations", headers=H[ADV]).json()["delegations"]
    assert len(rows) == 2 and [r["active"] for r in rows].count(True) == 1 and {r["delegation_id"]: r["active"] for r in rows} == {first["delegation_id"]: False, second["delegation_id"]: True}
    assert env.db.data[ob.ENGINES][X]["active_delegation_id"] == second["delegation_id"]
    assert [e["delegation_id"] for e in sorted(events(env.db, "delegate"), key=lambda e: e["ts"])] == [first["delegation_id"], second["delegation_id"]]
    (rev,) = events(env.db, "revoke_delegation")
    assert (rev["delegation_id"], rev["replaced"], rev["actor_subscriber_id"]) == (first["delegation_id"], True, ADV)
    answer_quietly(env, "scope")
    assert final(env, OTH, "scope").status_code == 403                                                       # the old, wider scope no longer works


def test_creating_or_revoking_is_audited_in_the_same_transaction_or_not_at_all(env):
    delegate(env)
    before = snapshot(env.db)
    env.db.fail_writes_to = {ob.EVENTS}                                                                      # the audit write fails: the change must not stand
    with pytest.raises(RuntimeError):
        gates.create_delegation(env.db, engine_id=X, subscriber_id=ADV, to_subscriber_id=OTH, scope=["seeds"])
    did = env.db.data[ob.ENGINES][X]["active_delegation_id"]
    with pytest.raises(RuntimeError):
        gates.revoke_delegation(env.db, engine_id=X, subscriber_id=ADV, delegation_id=did)
    with pytest.raises(RuntimeError):
        gates.set_notifications(env.db, engine_id=X, subscriber_id=ADV, email=False)
    answer_quietly(env, "scope")
    with pytest.raises(RuntimeError):
        gates.mark_final(env.db, engine_id=X, section="scope", subscriber_id=ADV)
    env.db.fail_writes_to = set()
    assert section_doc_exists(env) is False and "notifications_email" not in env.db.data[ob.MEMBERS][ob.member_id(X, ADV)]
    env.db.fail_after_ops = 3                                                                                # a failure part-way through a replacement
    with pytest.raises(RuntimeError):
        gates.create_delegation(env.db, engine_id=X, subscriber_id=ADV, to_subscriber_id=OTH, scope=["seeds"])
    env.db.fail_after_ops = None
    assert env.db.data[ob.ENGINES][X]["active_delegation_id"] == did and len(env.db.data["onboarding_delegations"]) == 1 and len(events(env.db, "delegate")) == 1
    assert not env.db.data["onboarding_delegations"][did]["revoked_at"]


def test_a_delegation_dies_with_the_delegates_membership_and_with_the_holders_succession(env):
    answer_quietly(env, "scope")
    delegate(env)
    env.db.data[ob.MEMBERS][ob.member_id(X, OTH)]["status"] = "revoked"                                    # the delegate was removed (invitation revoked)
    assert env.client.post(f"{BASE}/sections/scope/final", headers=H[OTH]).status_code == 404               # not a member any more: the gate itself refuses
    with pytest.raises(form.FormError) as ex:
        gates.mark_final(env.db, engine_id=X, section="scope", subscriber_id=OTH)                            # and the function, even if the gate were bypassed
    assert ex.value.status == 403
    env.db.data[ob.MEMBERS][ob.member_id(X, OTH)]["status"] = "active"
    assert final(env, OTH).status_code == 200                                                                # reinstated: the delegation still stands
    set_section(env, "scope", "draft")
    add_third_owner(env)
    env.db.data[ob.ENGINES][X]["final_say_subscriber_id"] = OWN3                                             # succession: the old holder's delegations end
    assert final(env, OTH).status_code == 403


def test_a_revoked_or_foreign_delegation_id_is_a_404_and_the_engine_page_says_who_may_mark(env):
    d = delegate(env, scope=["questions"]).json()
    for bad in ("0" * 32, "x" * 32, "short", "A" * 32):
        assert revoke(env, bad).status_code == 404
    env.db.data["onboarding_delegations"]["f" * 32] = {"engine_id": Y, "from_subscriber_id": YMEM, "to_subscriber_id": "z", "scope": "all", "created_at": "t"}
    assert revoke(env, "f" * 32).status_code == 404                                                          # another engine's delegation
    page = lambda who: env.client.get(BASE, headers=H[who] if who in H else ADMIN).json()
    assert (page(ADV)["can_mark_final"], page(ADV)["may_mark"]) == (True, ["scope", "questions", "keywords", "seeds"])
    assert (page(OTH)["can_mark_final"], page(OTH)["may_mark"]) == (True, ["questions"])
    assert (page("admin")["can_mark_final"], page("admin")["may_mark"]) == (False, [])
    revoke(env, d["delegation_id"])
    assert (page(OTH)["can_mark_final"], page(OTH)["may_mark"]) == (False, [])


# ---- notifications ------------------------------------------------------------------------------------------------------------------------------------
ADV_ADDR, OTH_ADDR = "sub-adv@example.invalid", "sub-oth@example.invalid"


def kinds(env):
    return [(m["kind"], m["to"]) for m in env.mail.sent]


def test_the_holder_is_told_when_a_section_becomes_ready_and_not_before(env):
    answer(env, OTH, "scope", upto=2)
    assert env.mail.sent == []
    put(env, OTH, "out-of-scope", [f"{SECRET} three"], base=0)
    assert kinds(env) == [("ready", ADV_ADDR)]
    m = env.mail.sent[0]
    assert (m["engine"], m["section"], m["link"]) == ("Synthetic X", "Scope and use case", f"https://www.copernicusai.fyi/onboarding/engine.html?engine={X}")
    assert section_doc(env, "scope")["ready_notified"] is True


def test_no_second_ready_mail_while_the_section_stays_ready_but_one_when_it_becomes_ready_again(env):
    answer(env, OTH, "scope")
    assert len(env.mail.sent) == 1
    put(env, ADV, "use-case", "an edit that keeps it ready", base=1)
    put(env, OTH, "use-case", "another", base=2)
    assert len(env.mail.sent) == 1                                                                           # still ready: no repeat
    c = comment(env, OTH, "use-case", "I disagree.", kind="disagree").json()
    comment(env, ADV, "use-case", "A plain comment changes nothing.")
    assert len(env.mail.sent) == 1 and section_doc(env, "scope")["ready_notified"] is False                  # not ready any more: the flag clears, no mail
    env.client.post(f"{BASE}/comments/{c['comment_id']}/resolve", headers=H[ADV])
    assert [k for k, _ in kinds(env)] == ["ready", "ready"]                                                  # ready again: told again
    env.client.post(f"{BASE}/comments/{c['comment_id']}/resolve", headers=H[ADV])
    assert len(env.mail.sent) == 2


def test_adding_a_question_to_a_ready_questions_section_does_not_resend_and_a_final_section_gets_no_ready_mail(env):
    answer(env, OTH, "questions")
    assert len(env.mail.sent) == 1
    env.client.post(f"{BASE}/questions", json={"action": "add", "questions": [{"wording": "More?", "centrality": "central"}]}, headers=H[OTH])
    assert len(env.mail.sent) == 1
    answer_quietly(env, "keywords")
    final(env, ADV, "keywords")
    env.mail.sent.clear()
    comment(env, OTH, "kw-1", "A note on a final section.", kind="disagree")
    assert env.mail.sent == []


def test_a_section_that_is_final_gets_no_ready_mail_when_its_last_disagreement_is_resolved(env):
    answer_quietly(env, "keywords")
    final(env, ADV, "keywords")
    env.db.data["onboarding_comments"] = {"c" * 32: {"engine_id": X, "section": "keywords", "item_id": "kw-1", "kind": "disagree", "body": "x", "author_subscriber_id": OTH,
                                                   "author_role": "owner", "created_at": "t", "resolved": False}}
    r = env.client.post(f"{BASE}/comments/{'c' * 32}/resolve", headers=H[ADV])
    assert r.status_code == 200 and row(progress(env), "keywords")["status"] == "final" and env.mail.sent == []


def test_a_re_open_from_final_tells_the_holder_once_and_a_section_still_ready_gets_no_second_mail(env):
    answer_quietly(env, "scope")
    final(env, ADV)
    put(env, OTH, "use-case", "an edit after final", base=1)
    assert [k for k, _ in kinds(env)] == ["reopened"] and kinds(env)[0][1] == ADV_ADDR                      # one mail: the re-open, not also "ready"
    assert env.mail.sent[0]["section"] == "Scope and use case" and section_doc(env, "scope")["ready_notified"] is True
    put(env, OTH, "use-case", "and again", base=2)
    assert len(env.mail.sent) == 1


def test_a_re_open_from_approved_also_tells_the_holder(env):
    answer_quietly(env, "scope")
    set_section(env, "scope", "approved", approved_at="2026-11-01", content_sha256="abc")
    put(env, OTH, "use-case", "an edit to approved content", base=1)
    assert kinds(env) == [("reopened", ADV_ADDR)] and section_doc(env, "scope")["revision"] == 2


def test_a_re_open_from_rejected_or_draft_sends_no_re_open_mail(env):
    answer_quietly(env, "scope")
    set_section(env, "scope", "rejected")
    put(env, OTH, "use-case", "revised after rejection", base=1)
    assert [k for k, _ in kinds(env)] == ["ready"]                                                           # the revised section is ready: that is the news
    env.mail.sent.clear()
    set_section(env, "questions", "draft")
    put(env, OTH, "ex-q1", q(), "accept", base=0)
    assert env.mail.sent == []


def test_a_covering_delegate_is_told_too_and_one_who_does_not_cover_the_section_is_not(env):
    delegate(env, scope=["scope"])
    answer(env, ADV, "scope")
    assert sorted(to for _, to in kinds(env)) == sorted([ADV_ADDR, OTH_ADDR])
    env.mail.sent.clear()
    delegate(env, scope=["seeds"])
    answer(env, ADV, "questions")
    assert kinds(env) == [("ready", ADV_ADDR)]
    env.mail.sent.clear()
    answer_quietly(env, "scope")
    final(env, ADV)
    put(env, ADV, "use-case", "x", base=1)
    assert [to for _, to in kinds(env)] == [ADV_ADDR]                                                        # a re-open of 'scope': the delegation covers seeds only
    revoke(env, env.db.data[ob.ENGINES][X]["active_delegation_id"])
    env.mail.sent.clear()
    answer(env, ADV, "keywords")
    assert [to for _, to in kinds(env)] == [ADV_ADDR]


def test_the_off_switch_is_the_owners_own_stored_on_the_membership_and_audited(env):
    r = env.client.put(f"{BASE}/notifications", json={"email": False}, headers=H[ADV])
    assert r.status_code == 200 and r.json() == {"email": False} and env.db.data[ob.MEMBERS][ob.member_id(X, ADV)]["notifications_email"] is False
    assert env.client.get(BASE, headers=H[ADV]).json()["notifications_email"] is False and env.client.get(BASE, headers=H[OTH]).json()["notifications_email"] is True
    answer(env, OTH, "scope")
    assert env.mail.sent == []                                                                               # nothing to a holder who switched off
    (e,) = events(env.db, "notifications")
    assert (e["actor_subscriber_id"], e["email"], e["target"]) == (ADV, False, "self") and not [s for s in strings(e) if "@" in s]
    delegate(env, scope="all")
    env.client.put(f"{BASE}/notifications", json={"email": False}, headers=H[OTH])
    env.client.put(f"{BASE}/notifications", json={"email": True}, headers=H[ADV])
    answer(env, ADV, "seeds")
    assert kinds(env) == [("ready", ADV_ADDR)]                                                               # the delegate switched off, the holder back on


@pytest.mark.parametrize("body", [{}, {"email": "yes"}, {"email": 1}, {"email": None}, {"email": "false"}, {"on": True}])
def test_the_switch_takes_a_real_boolean_only(env, body):
    before = snapshot(env.db)
    assert env.client.put(f"{BASE}/notifications", json=body, headers=H[ADV]).status_code == 422 and snapshot(env.db) == before


def test_the_off_switch_cannot_be_used_by_an_admin_or_a_stranger_or_on_another_engine(env):
    before = snapshot(env.db)
    for headers in (ADMIN, H[STRANGER], H[YMEM]):
        assert env.client.put(f"{BASE}/notifications", json={"email": False}, headers=headers).status_code == 404
    assert snapshot(env.db) == before


def test_a_mail_carries_the_names_a_link_and_no_answer_and_no_address_in_the_link(env):
    answer(env, OTH, "scope")
    answer_quietly(env, "questions")
    final(env, ADV, "questions")
    put(env, OTH, "ex-q1", q("Edited?"), "accept", base=1)
    assert [k for k, _ in kinds(env)] == ["ready", "reopened"]
    blob = json.dumps([{k: v for k, v in m.items() if k != "to"} for m in env.mail.sent])
    assert SECRET not in blob and "Edited" not in blob and "@" not in blob
    for m in env.mail.sent:
        assert re.fullmatch(r"https://www\.copernicusai\.fyi/onboarding/engine\.html\?engine=eng-x", m["link"])
        assert set(m) == {"to", "kind", "engine", "section", "link"}


def test_a_mail_failure_never_undoes_the_change_and_is_logged_by_error_type_only(env):
    logged = []
    from endpoints.onboarding import routes

    class Log:
        def error(self, msg, **kw):
            logged.append(("error", msg, kw))

        def info(self, msg, **kw):
            logged.append(("info", msg, kw))
    env.mp.setattr(routes, "structured_logger", Log())
    env.mail.raises = True
    answer(env, OTH, "scope", upto=2)
    r = put(env, OTH, "out-of-scope", [f"{SECRET} three"], base=0)
    assert r.status_code == 200 and r.json()["item"]["revision"] == 1 and stored(env, "out-of-scope", "scope")["value"] == [f"{SECRET} three"]       # committed
    assert [(m, kw) for lv, m, kw in logged if lv == "error"] == [("Onboarding notice could not be sent", {"error_type": "RuntimeError"})]
    blob = json.dumps(logged, default=str)
    assert "@" not in blob and "example.invalid" not in blob and SECRET not in blob and "down" not in blob and "engine.html" not in blob
    assert section_doc(env, "scope")["ready_notified"] is True and env.mail.sent == []                      # the flag is set; the mail was lost (the tracker line is the fallback)


def asgi_order(env, who, method, path, payload):
    """Drive the ASGI app directly and record the ORDER of 'the mail was sent' and 'the response began' (the test client would hide it: it waits for background work)."""
    order, original = [], env.mail.send_onboarding_notice

    async def noting(*a, **k):
        order.append("mail")
        return await original(*a, **k)
    env.mail.send_onboarding_notice = noting
    body = json.dumps(payload).encode()
    scope = {"type": "http", "asgi": {"version": "3.0"}, "http_version": "1.1", "method": method, "path": path, "raw_path": path.encode(), "query_string": b"", "scheme": "http",
             "root_path": "", "client": ("127.0.0.1", 1), "server": ("testserver", 80),
             "headers": [(b"content-type", b"application/json"), (b"content-length", str(len(body)).encode()), (b"x-subscriber-token", TOK[who].encode())]}
    state = {"sent": False}

    async def receive():
        if not state["sent"]:
            state["sent"] = True
            return {"type": "http.request", "body": body, "more_body": False}
        return {"type": "http.disconnect"}

    async def send(message):
        if message["type"] == "http.response.start":
            order.append(("response", message["status"]))
    loop = asyncio.new_event_loop()
    try:
        loop.run_until_complete(env.app(scope, receive, send))
    finally:
        loop.close()
    return order


def test_the_mail_is_sent_before_the_response_begins_not_after_it(env):
    answer(env, OTH, "scope", upto=2)
    order = asgi_order(env, OTH, "PUT", f"{BASE}/items/out-of-scope", {"value": [f"{SECRET} three"], "choice": None, "base_revision": 0})
    assert order == ["mail", ("response", 200)]                                                              # the notice went out first
    assert [m["kind"] for m in env.mail.sent] == ["ready"]
    plain = asgi_order(env, OTH, "PUT", f"{BASE}/items/use-case", {"value": "x", "choice": None, "base_revision": 1})
    assert plain == [("response", 200)]                                                                      # a save that calls for no notice sends none


def test_a_mail_that_fails_before_the_response_still_leaves_the_change_committed_and_the_response_ok(env):
    env.mail.raises = True
    answer(env, OTH, "scope", upto=2)
    order = asgi_order(env, OTH, "PUT", f"{BASE}/items/out-of-scope", {"value": ["kept"], "choice": None, "base_revision": 0})
    assert order == ["mail", ("response", 200)] and stored(env, "out-of-scope", "scope")["value"] == ["kept"]


def test_a_failure_while_planning_a_notice_also_leaves_the_change_committed(env):
    from endpoints.onboarding import routes
    logged = []

    class Log:
        def error(self, msg, **kw):
            logged.append((msg, kw))

        def info(self, msg, **kw):
            pass
    env.mp.setattr(routes, "structured_logger", Log())
    env.mp.setattr(gates, "plan_notifications", lambda *a, **k: (_ for _ in ()).throw(ValueError("db hiccup for sub-adv@example.invalid")))
    r = put(env, OTH, "use-case", "kept", base=0)
    assert r.status_code == 200 and stored(env, "use-case", "scope")["value"] == "kept"
    assert logged == [("Onboarding notice could not be planned", {"error_type": "ValueError"})]


def test_a_holder_with_no_address_or_no_membership_is_skipped_quietly(env):
    saved = env.db.data["subscribers"][ADV].pop("email")
    answer(env, OTH, "scope")
    assert env.mail.sent == []
    env.db.data["subscribers"][ADV]["email"] = saved                                                         # the address is back, but the membership is gone
    env.db.data[ob.MEMBERS][ob.member_id(X, ADV)]["status"] = "revoked"
    set_section(env, "questions", "draft")
    answer(env, OTH, "questions")
    assert env.mail.sent == []


def test_the_administrators_comment_does_not_trigger_a_notice_and_the_other_engines_are_untouched(env):
    answer_quietly(env, "scope")
    comment(env, "admin", "use-case", "From Gary.")
    assert env.mail.sent == [] and "ready_notified" not in env.db.data.get("onboarding_sections", {}).get(form.section_doc_id(X, "scope"), {})
    put(env, YMEM, "ey-q1", q(), "accept", engine=Y)
    assert all(m["engine"] != "Synthetic X" for m in env.mail.sent)


def test_final_and_delegation_and_switch_routes_are_rate_limited_per_account(env):
    answer_quietly(env, "scope")
    final(env, ADV)
    delegate(env)
    d = env.db.data[ob.ENGINES][X]["active_delegation_id"]
    revoke(env, d)
    env.client.put(f"{BASE}/notifications", json={"email": False}, headers=H[ADV])
    final_all(env, ADV)
    assert [k[1] for k, _ in env.limited] == ["onboarding_final", "onboarding_delegation", "onboarding_delegation", "onboarding_notifications", "onboarding_final"]
    assert all(k[0] == ADV for k, _ in env.limited)


# ---- the e-mail itself ----------------------------------------------------------------------------------------------------------------------------------
LINK = f"https://www.copernicusai.fyi/onboarding/engine.html?engine={X}"


def build(kind="ready", label="Synthetic X", section="Scope and use case", link=LINK, password="not-a-real-secret"):
    """Run the real builder with SMTP replaced; return (sent messages, result)."""
    with patch.dict("os.environ", {"NOTIFICATION_EMAIL": "site@example.invalid", "NOTIFICATION_EMAIL_PASSWORD": password}):
        svc = email_module.EmailService()
    sent, loop = [], asyncio.new_event_loop()
    try:
        with patch.object(email_module.smtplib, "SMTP") as smtp:
            smtp.return_value.__enter__.return_value.send_message.side_effect = lambda m: sent.append(m)
            ok = loop.run_until_complete(svc.send_onboarding_notice("someone@example.invalid", kind, label, section, link))
    finally:
        loop.close()
    return sent, ok


def parts(msg):
    return {p.get_content_type(): p.get_payload(decode=True).decode("utf-8") for p in msg.get_payload()}


def test_the_ready_and_reopened_emails_name_the_engine_and_section_and_carry_only_a_link():
    for kind, phrase in (("ready", "is ready to mark final"), ("reopened", "was edited and is open again")):
        (msg,), ok = build(kind)
        assert ok is True
        p = parts(msg)
        assert phrase in msg["Subject"] and "Synthetic X" in msg["Subject"] and msg["From"].startswith("CopernicusAI")
        assert LINK in p["text/plain"] and LINK in p["text/html"] and "Scope and use case" in p["text/plain"]
        assert re.findall(r"https?://\S+", p["text/plain"]) == [LINK] and "@" not in LINK
        assert "someone@example.invalid" not in p["text/plain"] + p["text/html"] + msg["Subject"]
        assert "switch them off" in p["text/plain"]


def test_a_label_with_a_line_break_cannot_inject_a_header_and_html_is_escaped():
    (msg,), ok = build(label="Evil\r\nBcc: x@example.invalid <b>", section="Sec\r\ntion")
    assert ok and "Bcc" not in msg.keys() and "\n" not in msg["Subject"] and "\r" not in msg["Subject"]
    assert "<b>" not in parts(msg)["text/html"] and "&lt;b&gt;" in parts(msg)["text/html"]


def test_an_unknown_kind_no_password_or_a_smtp_failure_returns_false_and_never_raises():
    assert build("bogus") == ([], False)
    assert build(password="") == ([], False)
    with patch.dict("os.environ", {"NOTIFICATION_EMAIL": "site@example.invalid", "NOTIFICATION_EMAIL_PASSWORD": "x"}):
        svc = email_module.EmailService()
    loop = asyncio.new_event_loop()
    try:
        with patch.object(email_module.smtplib, "SMTP", side_effect=OSError("refused")):
            assert loop.run_until_complete(svc.send_onboarding_notice("someone@example.invalid", "ready", "X", "S", LINK)) is False
    finally:
        loop.close()
