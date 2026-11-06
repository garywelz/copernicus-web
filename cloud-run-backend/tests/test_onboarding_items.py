"""Onboarding PR 3a-1: the template, items and sections with the revision check, question add and split, comments with the disagree marker, readiness and the
progress tracker (design 2, 4.1 to 4.5, 5.6, 5.7, 9). Offline: an in-memory Firestore with atomic transactions (tests/fakes_pr2.py), a recorded rate limiter and a
mocked clock. No test waits and none touches the network. The engine is a synthetic fixture: no real engine content."""
import json
import re
import threading
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from tests import fakes_pr1
from tests.fakes_pr2 import FakeDB, run_in_transaction
from utils import onboarding as ob
from utils import onboarding_form as form
from utils import onboarding_template as tpl

ADMIN = {"X-Admin-API-Key": "test-key"}
X, Y = "eng-x", "eng-y"
ADV, OTH, YMEM, STRANGER = "sub-adv", "sub-oth", "sub-y", "sub-z"
TOK = {ADV: "tok-adv", OTH: "tok-oth", YMEM: "tok-y", STRANGER: "tok-z"}
H = {k: {"X-Subscriber-Token": v} for k, v in TOK.items()}
T0 = datetime(2026, 11, 6, 12, 0, 0, tzinfo=timezone.utc)
HEX64 = re.compile(r"\b[0-9a-f]{64}\b")
CONSENT = {"naming": "role", "version": "1", "at": T0.isoformat()}


def item(engine, section, item_id, type_, order, **extra):
    return {"engine_id": engine, "section": section, "item_id": item_id, "type": type_, "value": None, "choice": None, "revision": 0, "comment_count": 0,
            "history": [], "context": {}, "order": order, **extra}


def seed():
    db = FakeDB(
        onboarding_engines={X: {"label": "Synthetic X", "state": "open", "final_say_subscriber_id": ADV, "question_id_prefix": "ex", "next_question_number": 4},
                            Y: {"label": "Synthetic Y", "state": "open", "final_say_subscriber_id": None, "question_id_prefix": "ey", "next_question_number": 2}},
        subscribers={s: fakes_pr1.subscriber(t, email=f"{s}@example.invalid") for s, t in TOK.items()},
        onboarding_members={ob.member_id(X, ADV): {"engine_id": X, "subscriber_id": ADV, "role": "owner", "final_say": True, "status": "active", "consent": CONSENT},
                            ob.member_id(X, OTH): {"engine_id": X, "subscriber_id": OTH, "role": "owner", "final_say": False, "status": "active", "consent": CONSENT},
                            ob.member_id(Y, YMEM): {"engine_id": Y, "subscriber_id": YMEM, "role": "owner", "final_say": False, "status": "active", "consent": CONSENT}},
    )
    items = [
        item(X, "scope", "scope-statement", "scope_statement", 1), item(X, "scope", "use-case", "use_case", 2), item(X, "scope", "out-of-scope", "out_of_scope", 3),
        item(X, "questions", "ex-q1", "question", 1, context={"original_wording": "Original question one?"}),
        item(X, "questions", "ex-q2", "question", 2, context={"original_wording": "Original question two?"}),
        item(X, "questions", "ex-q3", "question", 3, context={"original_wording": "Original question three?"}),
        item(X, "keywords", "kw-1", "keyword_entry", 1, context={"list": "horizons"}), item(X, "keywords", "kw-2", "keyword_entry", 2, context={"list": "mute"}),
        item(X, "seeds", "seed-1", "seed_confirm", 1, context={"citation": "A. Author (2020). A title.", "identifier": "doi:10.0/x"}),
        item(X, "seeds", "seed-2", "seed_confirm", 2, context={"citation": "B. Author (2021). Another title.", "identifier": "arxiv:0000.0000"}),
        item(Y, "questions", "ey-q1", "question", 1),
    ]
    db.data["onboarding_items"] = {form.item_key(i["engine_id"], i["section"], i["item_id"]): i for i in items}
    return db


class Clock:
    def __init__(self):
        self.t = T0

    def __call__(self):
        self.t += timedelta(seconds=1)
        return self.t


@pytest.fixture
def env(monkeypatch):
    import config.database
    import utils.auth as auth
    from endpoints.onboarding import routes
    db, limited, clock = seed(), [], Clock()
    monkeypatch.setattr(ob, "_run_in_transaction", run_in_transaction)
    monkeypatch.setattr(ob, "_utcnow", clock)
    monkeypatch.setattr(routes, "db", db)
    monkeypatch.setattr(config.database, "db", db)
    monkeypatch.setattr(routes, "check_rate_limit", lambda *a, **k: limited.append((a[1:3], k)))
    monkeypatch.setattr(auth, "get_admin_api_key", lambda: "test-key")
    app = FastAPI()
    app.include_router(routes.router)
    return type("Env", (), {"db": db, "client": TestClient(app), "routes": routes, "app": app, "limited": limited, "clock": clock, "mp": monkeypatch})()


def put(env, who, item_id, value, choice=None, base=0, engine=X):
    return env.client.put(f"/api/onboarding/engines/{engine}/items/{item_id}", json={"value": value, "choice": choice, "base_revision": base}, headers=H[who])


def q(wording="A question?", centrality="central", terms=None, **extra):
    return {"wording": wording, "centrality": centrality, "terms": terms or [], **extra}


def snapshot(db):
    return json.dumps(db.data, sort_keys=True, default=str)


def events(db, action=None):
    return [e for e in db.data.get(ob.EVENTS, {}).values() if action is None or e["action"] == action]


def strings(o):
    if isinstance(o, str):
        yield o
    elif isinstance(o, dict):
        for v in o.values():
            yield from strings(v)
    elif isinstance(o, (list, tuple)):
        for v in o:
            yield from strings(v)


def stored(env, item_id, section="questions", engine=X):
    return env.db.data["onboarding_items"][form.item_key(engine, section, item_id)]


# ---- the template as data ------------------------------------------------------------------------------------------------------------------------------
def test_the_template_is_versioned_generic_data():
    assert tpl.TEMPLATE_VERSION == 1 and tpl.SECTION_KEYS == ["scope", "questions", "keywords", "seeds"]
    src = Path(tpl.__file__).read_text(encoding="utf-8").lower()
    assert "tdap" not in src and "bees" not in src                                          # no engine's content in the template
    assert {t for s in tpl.SECTIONS for t in s["item_types"]} == set(tpl.ITEM_TYPES)
    assert all(tpl.section_of(t) == s["key"] for s in tpl.SECTIONS for t in s["item_types"])
    assert tpl.QUESTION_CHOICES == ("accept", "reword", "drop", "split", "add") and tpl.SEED_CHOICES == ("yes", "no", "unsure")


@pytest.mark.parametrize("type_,at_cap,over_cap,choice", [
    ("scope_statement", "x" * 2000, "x" * 2001, None),
    ("use_case", "y" * 2000, "y" * 2001, None),
    ("out_of_scope", ["z" * 200] * 30, ["z" * 201], None),
    ("out_of_scope", ["z"] * 30, ["z"] * 31, None),
    ("question", {"wording": "w" * 600, "centrality": "central"}, {"wording": "w" * 601, "centrality": "central"}, "reword"),
    ("question", {"centrality": "central", "terms": [{"text": "t" * 120, "choice": "keep"}] * 60}, {"centrality": "central", "terms": [{"text": "t" * 120, "choice": "keep"}] * 61}, "accept"),
    ("question", {"centrality": "central", "terms": [{"text": "t" * 120, "choice": "keep"}]}, {"centrality": "central", "terms": [{"text": "t" * 121, "choice": "keep"}]}, "accept"),
    ("question", {"reason": "r" * 500}, {"reason": "r" * 501}, "drop"),
    ("keyword_entry", {"list": "horizons", "text": "k" * 200}, {"list": "horizons", "text": "k" * 201}, "keep"),
    ("seed_confirm", {"comment": "c" * 1000}, {"comment": "c" * 1001}, "yes"),
])
def test_every_cap_accepts_the_limit_and_refuses_one_over_never_cutting(type_, at_cap, over_cap, choice):
    tpl.validate_item(type_, at_cap, choice)
    with pytest.raises(tpl.TemplateError):
        tpl.validate_item(type_, over_cap, choice)


def test_text_is_plain_control_characters_go_html_stays_text_and_the_rest_is_refused():
    v, c = tpl.validate_item("scope_statement", "  line one\r\nline\ttwo\x00\x07 <script>alert(1)</script> &amp; <b>x</b>  ", None)
    assert v == "line one\nline\ttwo <script>alert(1)</script> &amp; <b>x</b>" and c is None            # stored as text, exactly; nothing is interpreted or escaped here
    for bad in (5, None, ["a"], {"a": 1}):
        with pytest.raises(tpl.TemplateError):
            tpl.validate_item("scope_statement", bad, None)
    with pytest.raises(tpl.TemplateError):
        tpl.validate_item("scope_statement", "ok", "accept")                                              # a text answer has no choice
    with pytest.raises(tpl.TemplateError):
        tpl.validate_item("nope", "x", None)


def test_question_rules_choices_required_parts_and_unknown_keys():
    ok = lambda v, c: tpl.validate_item("question", v, c)
    assert ok({"centrality": "background"}, "accept")[1] == "accept"
    assert ok({"wording": "New wording?", "centrality": "central"}, "reword")[0]["wording"] == "New wording?"
    assert ok({"reason": "Out of scope"}, "drop")[0]["reason"] == "Out of scope"
    for bad_value, choice in [({"centrality": "central"}, "reword"),                                      # reword needs wording
                              ({"centrality": "central"}, "drop"),                                         # drop needs a reason
                              ({"wording": "x"}, "accept"),                                                # centrality is required unless dropped
                              ({"wording": "x", "centrality": "huge"}, "accept"),
                              ({"centrality": "central", "evil": 1}, "accept"),                            # unknown keys are refused
                              ({"centrality": "central", "terms": [{"text": "t", "choice": "maybe"}]}, "accept"),
                              ({"centrality": "central", "terms": [{"text": "", "choice": "keep"}]}, "accept"),
                              ({"centrality": "central", "terms": "not a list"}, "accept"),
                              ({"centrality": "central"}, "discard"), ({"centrality": "central"}, None)]:
        with pytest.raises(tpl.TemplateError):
            ok(bad_value, choice)
    assert ok({"centrality": "central", "terms": [{"text": "new", "choice": "reword", "was": "old"}]}, "accept")[0]["terms"] == [{"text": "new", "choice": "reword", "was": "old"}]


def test_keyword_and_seed_rules():
    assert tpl.validate_item("keyword_entry", {"list": "mute", "text": "noise"}, "keep")[0] == {"list": "mute", "text": "noise"}
    assert tpl.validate_item("keyword_entry", {"list": "horizons", "text": ""}, "drop")[0]["text"] == ""      # a dropped entry needs no text
    for bad in ({"list": "elsewhere", "text": "x"}, {"list": "mute", "text": ""}, {"list": "mute", "text": "x", "extra": 1}):
        with pytest.raises(tpl.TemplateError):
            tpl.validate_item("keyword_entry", bad, "keep")
    assert tpl.validate_item("seed_confirm", None, "unsure") == ({"comment": ""}, "unsure")
    with pytest.raises(tpl.TemplateError):
        tpl.validate_item("seed_confirm", {"comment": "x"}, "maybe")


# ---- saving an item: the revision check, provenance, history, audit -------------------------------------------------------------------------------------
def test_a_save_moves_the_revision_records_who_and_when_and_returns_the_view(env):
    r = put(env, OTH, "scope-statement", "What this engine is for.")
    assert r.status_code == 200
    body = r.json()
    assert body["section_status"] == "draft" and body["item"]["revision"] == 1 and body["item"]["answered"] is True and body["item"]["value"] == "What this engine is for."
    assert body["item"]["author"] == "you" and body["item"]["updated_at"] and body["item"]["history"] == []
    mine = stored(env, "scope-statement", "scope")
    assert (mine["revision"], mine["author_subscriber_id"]) == (1, OTH)
    other_view = env.client.get(f"/api/onboarding/engines/{X}/sections/scope", headers=H[ADV]).json()["items"][0]
    assert other_view["author"] == "other owner" and other_view["value"] == "What this engine is for."      # the advisor sees who changed it, without an id
    adv_labelled = env.client.get(f"/api/onboarding/engines/{X}/sections/scope", headers=H[OTH]).json()
    put(env, ADV, "scope-statement", "Revised by the advisor.", base=1)
    assert env.client.get(f"/api/onboarding/engines/{X}/sections/scope", headers=H[OTH]).json()["items"][0]["author"] == "advisor"
    assert env.client.get(f"/api/onboarding/engines/{X}/sections/scope", headers=ADMIN).json()["items"][0]["author"] == "advisor"
    assert env.client.get(f"/api/onboarding/engines/{X}/sections/scope", headers=ADMIN).json()["items"][1]["author"] is None


def test_a_stale_save_is_refused_with_the_current_answer_and_nothing_is_written(env):
    assert put(env, ADV, "use-case", "Advisor's version.", base=0).status_code == 200
    before = snapshot(env.db)
    r = put(env, OTH, "use-case", "The other owner's version.", base=0)                                  # based on revision 0, but the item is at 1
    assert r.status_code == 409
    detail = r.json()["detail"]
    assert detail["stale"] is True and detail["current"]["value"] == "Advisor's version." and detail["current"]["revision"] == 1 and detail["current"]["author"] == "advisor"
    assert snapshot(env.db) == before                                                                     # not one field differs: no revision, no history, no event, no clock-driven change
    assert stored(env, "use-case", "scope")["value"] == "Advisor's version."


def test_two_owners_editing_one_item_nothing_is_lost_and_a_merge_goes_through(env):
    put(env, ADV, "scope-statement", "First.", base=0)
    assert put(env, OTH, "scope-statement", "Second, from an old view.", base=0).status_code == 409
    current = env.client.get(f"/api/onboarding/engines/{X}/sections/scope", headers=H[OTH]).json()["items"][0]
    merged = current["value"] + " And the other owner's addition."                                       # the one-click merge: re-send on the current revision
    r = put(env, OTH, "scope-statement", merged, base=current["revision"])
    assert r.status_code == 200 and r.json()["item"]["revision"] == 2
    item = stored(env, "scope-statement", "scope")
    assert item["value"] == "First. And the other owner's addition." and [h["value"] for h in item["history"]] == ["First."]       # the advisor's text survives in the history
    stale_again = put(env, OTH, "scope-statement", "x", base=1)
    assert stale_again.status_code == 409 and stale_again.json()["detail"]["current"]["revision"] == 2
    assert [e["action"] for e in events(env.db, "item_edit")].count("item_edit") == 2                   # only the two accepted saves were recorded


def test_an_item_never_moves_backwards_or_skips_and_a_future_revision_is_refused(env):
    assert put(env, ADV, "use-case", "a", base=1).status_code == 409                                      # a revision the item has not reached
    assert put(env, ADV, "use-case", "a", base=0).status_code == 200
    assert put(env, ADV, "use-case", "b", base=0).status_code == 409
    assert put(env, ADV, "use-case", "b", base=1).status_code == 200 and stored(env, "use-case", "scope")["revision"] == 2


def test_history_is_capped_and_the_audit_log_keeps_every_prior_value(env):
    base = 0
    for n in range(1, 26):
        assert put(env, ADV if n % 2 else OTH, "use-case", f"version {n}", base=base).status_code == 200
        base += 1
    it = stored(env, "use-case", "scope")
    assert it["revision"] == 25 and len(it["history"]) == form.HISTORY_CAP == 20
    assert [h["revision"] for h in it["history"]] == list(range(5, 25))                                   # the last 20 prior revisions
    edits = sorted(events(env.db, "item_edit"), key=lambda e: e["revision"])
    assert [e["before_value"] for e in edits][:3] == [None, "version 1", "version 2"] and edits[24]["before_value"] == "version 24"      # the audit log still has every prior value
    assert all(e["before_sha256"] != e["after_sha256"] for e in edits[1:])


def test_the_audit_event_for_an_edit_is_complete_and_holds_no_address(env):
    put(env, OTH, "ex-q1", q("Reworded?"), "reword", base=0)
    (e,) = events(env.db, "item_edit")
    assert (e["engine_id"], e["actor_subscriber_id"], e["actor_role"], e["target"], e["section"], e["revision"], e["choice"]) == (X, OTH, "owner", "questions/ex-q1", "questions", 1, "reword")
    assert e["before_value"] is None and e["before_sha256"] is None and e["after_sha256"] and e["ts"] and "ip_hash" in e and "request_id" in e
    assert not [s for s in strings(events(env.db)) if "@" in s]


def test_no_response_carries_a_subscriber_id_or_a_hash_of_one(env):
    put(env, ADV, "scope-statement", "x", base=0)
    env.client.post(f"/api/onboarding/engines/{X}/items/scope-statement/comments", json={"body": "hello"}, headers=H[OTH])
    bodies = [env.client.get(f"/api/onboarding/engines/{X}", headers=H[OTH]).text, env.client.get(f"/api/onboarding/engines/{X}/sections/scope", headers=H[OTH]).text,
              env.client.get(f"/api/onboarding/engines/{X}/sections/scope", headers=ADMIN).text,
              put(env, OTH, "scope-statement", "y", base=1).text, put(env, ADV, "scope-statement", "stale", base=0).text]
    def without_content_hashes(o):                       # a section's content_sha256 is a hash of content, not of a person: the one hash that is meant to be there
        if isinstance(o, dict):
            return {k: without_content_hashes(v) for k, v in o.items() if k != "content_sha256"}
        return [without_content_hashes(v) for v in o] if isinstance(o, list) else o
    for text in bodies:
        scan = json.dumps(without_content_hashes(json.loads(text)))
        assert not HEX64.findall(scan) and ADV not in scan and OTH not in scan and YMEM not in scan, text[:200]


def test_validation_errors_are_400_with_a_reason_and_write_nothing(env):
    before = snapshot(env.db)
    for item_id, value, choice in [("scope-statement", "x" * 2001, None), ("scope-statement", 5, None), ("ex-q1", q(), "discard"), ("ex-q1", {"centrality": "central"}, "reword"),
                                   ("kw-1", {"list": "nowhere", "text": "x"}, "keep"), ("seed-1", {"comment": "ok"}, "perhaps")]:
        r = put(env, ADV, item_id, value, choice)
        assert r.status_code == 400 and isinstance(r.json()["detail"], str) and r.json()["detail"], (item_id, r.text)
    assert snapshot(env.db) == before


def test_unknown_items_and_other_engines_items_are_404_and_nothing_is_created(env):
    before = snapshot(env.db)
    for item_id in ("no-such-item", "BAD ID", "ex-q1__x", "ey-q1"):                                       # ey-q1 exists, but in engine Y
        assert put(env, ADV, item_id, "x", base=0).status_code == 404, item_id
    assert put(env, YMEM, "ex-q1", q(), "accept", engine=Y).status_code == 404                           # Y's owner cannot reach X's item through Y's path either
    assert snapshot(env.db) == before                                                                     # a save never creates an item


def test_a_closed_engine_a_missing_consent_and_an_oversized_body_are_refused(env):
    env.db.data[ob.ENGINES][X]["state"] = "closed"
    before = snapshot(env.db)
    assert put(env, ADV, "use-case", "x", base=0).status_code == 409 and snapshot(env.db) == before
    env.db.data[ob.ENGINES][X]["state"] = "open"
    del env.db.data[ob.MEMBERS][ob.member_id(X, OTH)]["consent"]
    r = put(env, OTH, "use-case", "x", base=0)
    assert r.status_code == 409 and "consent" in r.json()["detail"]
    big = env.client.put(f"/api/onboarding/engines/{X}/items/use-case", content=json.dumps({"value": "x" * 70000, "base_revision": 0}), headers={**H[ADV], "Content-Type": "application/json"})
    assert big.status_code == 413


def test_choice_transitions_a_split_question_is_closed_and_add_is_only_for_added_questions(env):
    assert put(env, ADV, "ex-q1", q(), "split").status_code == 400                                       # splitting has its own action
    assert put(env, ADV, "ex-q1", q(), "add").status_code == 400                                         # 'add' is only for a question that was added
    assert put(env, ADV, "ex-q1", q("Reworded?"), "reword").status_code == 200
    added = env.client.post(f"/api/onboarding/engines/{X}/questions", json={"action": "add", "questions": [{"wording": "New?", "centrality": "background"}]}, headers=H[ADV]).json()["ids"][0]
    assert put(env, ADV, added, q("New, edited?", "background"), "add", base=1).status_code == 200
    assert put(env, ADV, added, q(), "accept", base=2).status_code == 400                                 # an added question cannot become 'accept'
    assert put(env, ADV, added, {"reason": "not needed"}, "drop", base=2).status_code == 200
    env.client.post(f"/api/onboarding/engines/{X}/questions", json={"action": "split", "from_item": "ex-q2", "questions": [{"wording": "A?", "centrality": "central"}, {"wording": "B?", "centrality": "central"}]}, headers=H[ADV])
    r = put(env, ADV, "ex-q2", q(), "accept", base=1)
    assert r.status_code == 409 and "split" in r.json()["detail"]
