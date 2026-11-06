"""Onboarding PR 3a-3: creating a keyword, horizon or mute entry (the fourth addition to design 5.7, approved by Gary 2026-11-06): system-assigned ids that are never
reused, audited, rate limited, capped; owners only. Uses the fixture and helpers of tests/test_onboarding_items.py."""
import threading

import pytest

from tests.test_onboarding_items import ADMIN, ADV, H, OTH, STRANGER, X, Y, YMEM, env, events, put, snapshot, stored, strings  # noqa: F401  (env is a fixture)
from tests.test_onboarding_workspace import comment, progress, row, section_doc, set_section
from utils import onboarding as ob
from utils import onboarding_form as form

BASE = f"/api/onboarding/engines/{X}"


def add(env, who, list_name="horizons", text="a new entry", engine=X):
    return env.client.post(f"/api/onboarding/engines/{engine}/entries", json={"list": list_name, "text": text}, headers=H[who] if who in H else ADMIN)


def entries(env, engine=X):
    return {i["item_id"]: i for i in env.db.data["onboarding_items"].values() if i["engine_id"] == engine and i["type"] == "keyword_entry"}


def test_an_added_entry_gets_the_next_free_id_is_stored_as_added_and_audited(env):
    r = add(env, OTH, "horizons", "  long-run effects \x07 ")
    assert r.status_code == 200 and r.json()["id"] == "ex-k1"
    it = stored(env, "ex-k1", "keywords")
    assert (it["choice"], it["revision"], it["type"], it["author_subscriber_id"], it["context"], it["value"]) == (
        "add", 1, "keyword_entry", OTH, {"added": True}, {"list": "horizons", "text": "long-run effects"})
    assert env.db.data[ob.ENGINES][X]["next_entry_number"] == 2
    view = r.json()["item"]
    assert (view["item_id"], view["author"], view["answered"], view["choice"], view["revision"]) == ("ex-k1", "you", True, "add", 1)
    (e,) = events(env.db, "entry_add")
    assert (e["engine_id"], e["actor_subscriber_id"], e["actor_role"], e["target"], e["section"], e["list"]) == (X, OTH, "owner", "ex-k1", "keywords", "horizons")
    assert e["ts"] and "ip_hash" in e and "request_id" in e and not [s for s in strings(e) if "@" in s or "long-run" in s]          # no text in the audit event
    assert row(progress(env), "keywords")["items"] == 3 and add(env, ADV, "mute", "noise").json()["id"] == "ex-k2"


@pytest.mark.parametrize("list_name", ["categories", "horizons", "mute", "frontier", "flagged"])
def test_every_list_of_the_template_accepts_an_entry(env, list_name):
    assert add(env, ADV, list_name, "x").status_code == 200


def test_an_id_is_never_reused_after_a_drop_a_lagging_counter_a_missing_counter_or_a_removed_number(env):
    first = add(env, ADV).json()["id"]                                                                       # ex-k1
    assert put(env, ADV, first, {"list": "horizons", "text": ""}, "drop", base=1).status_code == 200
    assert add(env, ADV).json()["id"] == "ex-k2"                                                             # the dropped number is not given out again
    env.db.data[ob.ENGINES][X]["next_entry_number"] = 1                                                      # a counter that fell behind
    assert add(env, ADV).json()["id"] == "ex-k3"
    del env.db.data[ob.ENGINES][X]["next_entry_number"]                                                      # no counter at all
    assert add(env, ADV).json()["id"] == "ex-k4"
    del env.db.data["onboarding_items"][form.item_key(X, "keywords", "ex-k2")]                              # one removed by hand
    env.db.data[ob.ENGINES][X]["next_entry_number"] = 1
    assert add(env, ADV).json()["id"] == "ex-k5"
    assert len(entries(env)) == len(set(entries(env))) == 6                                                  # two loaded + four that remain


def test_the_transaction_skips_an_id_that_already_exists_even_if_the_floor_and_counter_are_stale(env):
    env.mp.setattr(form, "_keyword_numbers", lambda db, engine_id, prefix: (0, 0))
    env.db.data["onboarding_items"][form.item_key(X, "keywords", "ex-k1")] = {"engine_id": X, "section": "keywords", "item_id": "ex-k1", "type": "keyword_entry", "value": None,
                                                                              "choice": None, "revision": 0, "comment_count": 0, "history": [], "context": {}, "order": 9}
    env.db.data[ob.ENGINES][X]["next_entry_number"] = 1
    assert add(env, ADV).json()["id"] == "ex-k2" and env.db.data[ob.ENGINES][X]["next_entry_number"] == 3


def test_two_simultaneous_adds_get_different_ids(env):
    out, gate = [], threading.Barrier(2)

    def go(who):
        gate.wait()
        out.append(form.add_entry(env.db, engine_id=X, subscriber_id=who, list_name="mute", text="x"))
    threads = [threading.Thread(target=go, args=(w,)) for w in (ADV, OTH)]
    [t.start() for t in threads]
    [t.join() for t in threads]
    assert sorted(out) == ["ex-k1", "ex-k2"]


@pytest.mark.parametrize("body", [{"list": "nowhere", "text": "x"}, {"list": "mute", "text": ""}, {"list": "mute", "text": "   "}, {"list": "mute", "text": "x" * 201},
                                  {"list": "mute", "text": "\x00\x07"}, {"list": "", "text": "x"}, {"text": "x"}, {"list": "mute"}, {"list": 5, "text": "x"}, {"list": "mute", "text": 5}])
def test_a_bad_entry_is_refused_and_nothing_is_written(env, body):
    before = snapshot(env.db)
    r = env.client.post(f"{BASE}/entries", json=body, headers=H[ADV])
    assert r.status_code in (400, 422) and snapshot(env.db) == before


def test_the_text_cap_is_exact_and_the_per_engine_cap_is_enforced(env):
    assert add(env, ADV, "mute", "x" * 200).status_code == 200 and add(env, ADV, "mute", "x" * 201).status_code == 400
    env.mp.setattr(form, "MAX_KEYWORD_ENTRIES", 3)                                                           # two loaded + one added
    before = snapshot(env.db)
    r = add(env, ADV)
    assert r.status_code == 409 and "3" in r.json()["detail"] and snapshot(env.db) == before
    env.mp.setattr(form, "MAX_KEYWORD_ENTRIES", 4)
    assert add(env, ADV).status_code == 200


def test_only_owners_of_that_engine_may_add_an_entry(env):
    before = snapshot(env.db)
    for call in (lambda: add(env, "admin"), lambda: add(env, STRANGER), lambda: add(env, YMEM), lambda: add(env, ADV, engine=Y), lambda: add(env, YMEM, engine=X)):
        r = call()
        assert (r.status_code, r.json()) == (404, {"detail": "Not found"})
    assert env.client.post(f"{BASE}/entries", json={"list": "mute", "text": "x"}).status_code == 404         # no session at all
    assert snapshot(env.db) == before
    env.db.data[ob.ENGINES][X]["state"] = "closed"
    assert add(env, ADV).status_code == 409
    env.db.data[ob.ENGINES][X]["state"] = "open"
    del env.db.data[ob.MEMBERS][ob.member_id(X, OTH)]["consent"]
    assert add(env, OTH).status_code == 409


def test_adding_entries_is_rate_limited_per_account(env):
    add(env, ADV)
    add(env, OTH)
    assert [(k[0], k[1]) for k, kw in env.limited] == [(ADV, "onboarding_entry"), (OTH, "onboarding_entry")]
    assert all(kw.get("limit") == 60 and kw.get("window_seconds") == 3600 for _, kw in env.limited)


def test_the_creation_is_audited_in_the_same_transaction_or_not_at_all(env):
    before = snapshot(env.db)
    env.db.fail_writes_to = {ob.EVENTS}
    with pytest.raises(RuntimeError):
        form.add_entry(env.db, engine_id=X, subscriber_id=ADV, list_name="mute", text="x")
    env.db.fail_writes_to = set()
    assert snapshot(env.db) == before                                                                        # no item, no counter, no section change


def test_an_added_entry_can_be_edited_or_dropped_but_not_turned_into_a_kept_one(env):
    entry = add(env, ADV, "mute", "noise").json()["id"]
    assert put(env, OTH, entry, {"list": "mute", "text": "better noise"}, "add", base=1).status_code == 200
    assert put(env, OTH, entry, {"list": "mute", "text": "x"}, "keep", base=2).status_code == 400
    assert put(env, OTH, entry, {"list": "mute", "text": ""}, "drop", base=2).status_code == 200
    assert put(env, OTH, "kw-1", {"list": "mute", "text": "x"}, "add", base=0).status_code == 400            # a loaded entry cannot become 'added'


def test_adding_an_entry_reopens_a_final_section_and_tells_the_holder_once(env):
    for i in ("kw-1", "kw-2"):
        stored(env, i, "keywords").update({"revision": 1, "choice": "keep", "value": {"list": "mute", "text": "t"}})
    set_section(env, "keywords", "final", final_by=ADV)
    assert add(env, OTH).status_code == 200
    assert section_doc(env, "keywords")["status"] == "draft" and section_doc(env, "keywords")["reopened_by"] == OTH
    assert [e["from_status"] for e in events(env.db, "reopen")] == ["final"]
    assert [m["kind"] for m in env.mail.sent] == ["reopened"] and env.mail.sent[0]["section"] == "Keywords and horizons"
    assert add(env, OTH).status_code == 200 and len(env.mail.sent) == 1                                      # still ready: no second mail


def test_an_added_entry_counts_as_answered_so_it_never_holds_up_readiness_and_can_be_disagreed_with(env):
    entry = add(env, ADV).json()["id"]
    assert row(progress(env), "keywords")["answered"] == 1 and row(progress(env), "keywords")["open"] == 2
    c = comment(env, OTH, entry, "I do not think this belongs.", kind="disagree")
    assert c.status_code == 200 and row(progress(env), "keywords")["disagreed"] == 1


def test_adding_entries_never_touches_another_engine(env):
    add(env, ADV)
    assert entries(env, Y) == {} and "next_entry_number" not in env.db.data[ob.ENGINES][Y]
    assert add(env, YMEM, "mute", "y", engine=Y).status_code == 200
    assert sorted(entries(env, Y)) == ["ey-k1"] and "ex-k1" in entries(env)
