"""Onboarding PR 3a-1, part 2: re-opening on edit, question add and split (never-reused ids), comments and the disagree marker, readiness and the progress tracker,
and the default-deny table over every engine route. Uses the fixture and helpers of tests/test_onboarding_items.py."""
import json
import threading

import pytest

from tests.test_onboarding_items import (ADMIN, ADV, H, OTH, STRANGER, T0, X, Y, YMEM, env, events, put, q, seed, snapshot, stored, strings)  # noqa: F401  (env is a fixture)
from utils import onboarding as ob
from utils import onboarding_form as form
from utils import onboarding_template as tpl

BASE = f"/api/onboarding/engines/{X}"


def set_section(env, section, status, engine=X, **extra):
    env.db.data.setdefault("onboarding_sections", {})[form.section_doc_id(engine, section)] = {"engine_id": engine, "section": section, "status": status, "revision": 1, **extra}


def section_doc(env, section, engine=X):
    return env.db.data["onboarding_sections"][form.section_doc_id(engine, section)]


def new_q(env, who, action="add", from_item=None, wordings=None):
    wordings = wordings or [{"wording": "A new question?", "centrality": "background"}]
    return env.client.post(f"{BASE}/questions", json={"action": action, "from_item": from_item, "questions": wordings}, headers=H[who])


def comment(env, who, item_id, body="A comment.", kind="comment", engine=X):
    return env.client.post(f"/api/onboarding/engines/{engine}/items/{item_id}/comments", json={"body": body, "kind": kind}, headers=H[who] if who in H else ADMIN)


def section_json(env, who, section):
    return env.client.get(f"{BASE}/sections/{section}", headers=H[who] if who in H else ADMIN).json()


def progress(env, who=ADV):
    return env.client.get(BASE, headers=H[who] if who in H else ADMIN).json()["progress"]


def row(prog, key):
    return next(r for r in prog["sections"] if r["key"] == key)


# ---- the state machine, part 1: an edit re-opens (design 4.5) -------------------------------------------------------------------------------------------
@pytest.mark.parametrize("status,reopens,new_revision", [("draft", False, 1), ("final", True, 1), ("rejected", True, 1), ("approved", True, 4)])
def test_an_edit_reopens_a_final_rejected_or_approved_section_and_leaves_a_draft_alone(env, status, reopens, new_revision):
    extra = {"revision": 3, "content_sha256": "abc", "approved_at": "2026-11-01T00:00:00", "final_by": ADV, "final_at": "2026-11-01"} if status == "approved" else (
        {"final_by": ADV, "final_via_delegation": False, "final_at": "2026-11-01"} if status == "final" else {})
    set_section(env, "scope", status, **extra)
    if status == "approved":
        section_doc(env, "scope")["revision"] = 3
    r = put(env, OTH, "use-case", "an edit", base=0)
    assert r.status_code == 200 and r.json()["section_status"] == "draft"
    sec = section_doc(env, "scope")
    assert sec["status"] == "draft" and sec["revision"] == (4 if status == "approved" else 1 if status != "draft" else 1)
    assert sec["updated_at"]
    reopen_events = events(env.db, "reopen")
    assert len(reopen_events) == (1 if reopens else 0)
    if reopens:
        assert (reopen_events[0]["from_status"], reopen_events[0]["actor_subscriber_id"], reopen_events[0]["target"]) == (status, OTH, "scope")
        assert sec["reopened_by"] == OTH and sec["final_by"] is None and sec["final_at"] is None
    else:
        assert "reopened_by" not in sec
    if status == "approved":
        assert sec["approved_history"] == [{"revision": 3, "content_sha256": "abc", "approved_at": "2026-11-01T00:00:00"}]         # the approved revision stays in the history
        assert env.client.get(f"{BASE}/sections/scope", headers=ADMIN).json()["section"]["status"] == "draft"


def test_an_edit_that_fails_does_not_reopen_a_final_section(env):
    set_section(env, "scope", "final", final_by=ADV)
    before = snapshot(env.db)
    assert put(env, OTH, "use-case", "x" * 2001, base=0).status_code == 400
    assert put(env, OTH, "use-case", "ok", base=5).status_code == 409                                      # a stale save
    assert snapshot(env.db) == before and section_doc(env, "scope")["status"] == "final"


def test_adding_a_question_to_a_final_questions_section_reopens_it(env):
    set_section(env, "questions", "final", final_by=ADV)
    assert new_q(env, OTH).status_code == 200
    assert section_doc(env, "questions")["status"] == "draft" and [e["from_status"] for e in events(env.db, "reopen")] == ["final"]


# ---- questions: add and split, ids assigned by the system and never reused ------------------------------------------------------------------------------
def test_add_assigns_the_next_free_id_from_a_counter_that_only_goes_up(env):
    r = new_q(env, ADV)
    assert r.status_code == 200 and r.json()["ids"] == ["ex-q4"]
    it = stored(env, "ex-q4")
    assert (it["choice"], it["revision"], it["type"], it["author_subscriber_id"], it["context"]) == ("add", 1, "question", ADV, {"added": True})
    assert it["value"] == {"wording": "A new question?", "centrality": "background", "terms": []}
    assert env.db.data[ob.ENGINES][X]["next_question_number"] == 5
    assert new_q(env, OTH).json()["ids"] == ["ex-q5"] and env.db.data[ob.ENGINES][X]["next_question_number"] == 6
    (e, _) = sorted(events(env.db, "question_add"), key=lambda x: x["ts"])
    assert (e["actor_subscriber_id"], e["new_ids"], e["section"]) == (ADV, ["ex-q4"], "questions")
    assert r.json()["items"][0]["item_id"] == "ex-q4" and r.json()["items"][0]["author"] == "you"


def test_an_id_is_never_reused_after_a_drop_a_split_or_a_wrong_counter(env):
    first = new_q(env, ADV).json()["ids"][0]                                                              # ex-q4
    assert put(env, ADV, first, {"reason": "not needed"}, "drop", base=1).status_code == 200            # dropped, but it still exists
    assert new_q(env, ADV).json()["ids"] == ["ex-q5"]                                                     # the dropped number is not given out again
    env.db.data[ob.ENGINES][X]["next_question_number"] = 1                                                # a counter that has fallen behind the items
    assert new_q(env, ADV).json()["ids"] == ["ex-q6"]                                                     # the highest existing number wins
    del env.db.data[ob.ENGINES][X]["next_question_number"]                                                # no counter at all
    assert new_q(env, ADV).json()["ids"] == ["ex-q7"]
    ids = [i["item_id"] for i in env.db.data["onboarding_items"].values() if i["engine_id"] == X and i["type"] == "question"]
    assert len(ids) == len(set(ids)) == 7


def test_a_number_whose_document_was_removed_by_hand_is_still_not_given_out_again_when_the_counter_lags(env):
    """The loop only skips ids that have a document. If a question was removed by hand and the counter is behind, only the floor (the highest number still present)
    keeps the next id above it, so a gap is never refilled."""
    del env.db.data["onboarding_items"][form.item_key(X, "questions", "ex-q2")]
    env.db.data[ob.ENGINES][X]["next_question_number"] = 1
    assert new_q(env, ADV).json()["ids"] == ["ex-q4"]                                                       # not ex-q2, the removed one


def test_the_transaction_itself_skips_an_id_that_already_exists_even_if_the_floor_and_counter_are_stale(env):
    """The floor is read before the transaction; if it is stale, the transaction must still never hand out an id that has a document."""
    env.mp.setattr(form, "_highest_question_number", lambda db, engine_id, prefix: 0)
    env.db.data[ob.ENGINES][X]["next_question_number"] = 1                                                 # counter and floor both claim 'ex-q1' is free; ex-q1..q3 exist
    assert new_q(env, ADV).json()["ids"] == ["ex-q4"]
    assert env.db.data[ob.ENGINES][X]["next_question_number"] == 5
    assert len([i for i in env.db.data["onboarding_items"].values() if i["engine_id"] == X and i["type"] == "question"]) == 4


def test_two_simultaneous_adds_get_different_ids(env):
    out, gate = [], threading.Barrier(2)

    def go(who):
        gate.wait()
        out.append(form.add_questions(env.db, engine_id=X, subscriber_id=who, action="add", wordings=[{"wording": "Q?", "centrality": "central"}]))
    threads = [threading.Thread(target=go, args=(w,)) for w in (ADV, OTH)]
    [t.start() for t in threads]
    [t.join() for t in threads]
    assert sorted(i for ids in out for i in ids) == ["ex-q4", "ex-q5"]


def test_split_replaces_one_question_with_two_or_more_each_with_its_own_wording(env):
    put(env, ADV, "ex-q2", q("Original two, accepted?"), "accept", base=0)
    r = new_q(env, OTH, "split", "ex-q2", [{"wording": "Part A?", "centrality": "central"}, {"wording": "Part B?", "centrality": "background"}, {"wording": "Part C?", "centrality": "central"}])
    assert r.status_code == 200 and r.json()["ids"] == ["ex-q4", "ex-q5", "ex-q6"]
    orig = stored(env, "ex-q2")
    assert orig["choice"] == "split" and orig["value"]["split_into"] == ["ex-q4", "ex-q5", "ex-q6"] and orig["revision"] == 2 and orig["author_subscriber_id"] == OTH
    assert orig["history"][-1]["value"]["wording"] == "Original two, accepted?" and orig["history"][-1]["choice"] == "accept"          # the old answer is kept in the history
    assert [stored(env, i)["value"]["wording"] for i in ("ex-q4", "ex-q5", "ex-q6")] == ["Part A?", "Part B?", "Part C?"]
    assert all(stored(env, i)["choice"] == "add" and stored(env, i)["context"] == {"split_from": "ex-q2"} for i in ("ex-q4", "ex-q5", "ex-q6"))
    (e,) = events(env.db, "question_split")
    assert (e["target"], e["new_ids"], e["actor_subscriber_id"]) == ("ex-q2", ["ex-q4", "ex-q5", "ex-q6"], OTH)
    assert env.db.data[ob.ENGINES][X]["next_question_number"] == 7


def test_split_and_add_refusals_change_nothing(env):
    two = [{"wording": "A?", "centrality": "central"}, {"wording": "B?", "centrality": "central"}]
    one = [{"wording": "A?", "centrality": "central"}]
    before = snapshot(env.db)
    for label, r in {
        "split of one": new_q(env, ADV, "split", "ex-q1", one), "split of six": new_q(env, ADV, "split", "ex-q1", two * 3), "split with no source": new_q(env, ADV, "split", None, two),
        "split of a missing question": new_q(env, ADV, "split", "no-such-q", two), "split of a non-question": new_q(env, ADV, "split", "kw-1", two),
        "add of two": new_q(env, ADV, "add", None, two), "unknown action": new_q(env, ADV, "merge", None, one), "no wording": new_q(env, ADV, "add", None, [{"wording": "", "centrality": "central"}]),
        "bad centrality": new_q(env, ADV, "add", None, [{"wording": "W?", "centrality": "huge"}]), "wording over its cap": new_q(env, ADV, "add", None, [{"wording": "w" * 601, "centrality": "central"}]),
        "empty list": env.client.post(f"{BASE}/questions", json={"action": "add", "questions": []}, headers=H[ADV]),
    }.items():
        assert r.status_code in (400, 409, 422), (label, r.status_code)
    assert snapshot(env.db) == before
    assert new_q(env, ADV, "split", "ex-q1", two).status_code == 200
    assert new_q(env, ADV, "split", "ex-q1", two).status_code == 409                                        # already split
    put(env, ADV, "ex-q3", {"reason": "gone"}, "drop", base=0)
    assert new_q(env, ADV, "split", "ex-q3", two).status_code == 409                                        # dropped


def test_questions_are_for_owners_of_that_engine_only_and_a_closed_engine_refuses(env):
    before = snapshot(env.db)
    assert new_q(env, STRANGER).status_code == 404 and new_q(env, YMEM).status_code == 404
    assert env.client.post(f"{BASE}/questions", json={"action": "add", "questions": [{"wording": "W?", "centrality": "central"}]}, headers=ADMIN).status_code == 404       # not the administrator
    assert snapshot(env.db) == before
    env.db.data[ob.ENGINES][X]["state"] = "closed"
    assert new_q(env, ADV).status_code == 409


# ---- comments and the disagree marker ---------------------------------------------------------------------------------------------------------------
def test_a_comment_is_plain_text_capped_and_counted_and_the_audit_event_holds_no_text(env):
    r = comment(env, OTH, "scope-statement", "<script>alert(1)</script> & <b>bold</b>\x00\x07")
    assert r.status_code == 200 and r.headers["content-type"].startswith("application/json")
    c = r.json()
    assert c["body"] == "<script>alert(1)</script> & <b>bold</b>" and (c["author"], c["role"], c["kind"], c["resolved"]) == ("you", "owner", "comment", False)       # text, exactly; control characters gone
    assert stored(env, "scope-statement", "scope")["comment_count"] == 1
    other = section_json(env, ADV, "scope")["items"][0]
    assert other["comments"][0]["author"] == "other owner" and other["comment_count"] == 1 and other["disagreed"] is False
    (e,) = events(env.db, "comment")
    assert e["comment_id"] == c["comment_id"] and e["kind"] == "comment" and "body" not in e and "alert" not in json.dumps(e)
    assert comment(env, OTH, "scope-statement", "x" * 2000).status_code == 200
    for bad in ("", "   ", "x" * 2001, "\x00\x01"):
        assert comment(env, OTH, "scope-statement", bad).status_code in (400, 422), repr(bad)
    assert comment(env, OTH, "scope-statement", "ok", kind="shout").status_code == 400
    assert comment(env, OTH, "no-such-item").status_code == 404


def test_a_disagree_comment_marks_the_item_and_blocks_readiness_until_either_owner_resolves_it(env):
    for item_id in ("scope-statement", "use-case", "out-of-scope"):
        put(env, ADV, item_id, ["a"] if item_id == "out-of-scope" else "answer", base=0)
    assert row(progress(env), "scope")["ready"] is True
    c = comment(env, OTH, "use-case", "I disagree with this.", kind="disagree").json()
    assert section_json(env, ADV, "scope")["items"][1]["disagreed"] is True
    p = row(progress(env), "scope")
    assert (p["disagreed"], p["answered"], p["ready"]) == (1, 2, False)
    assert {"section": "scope", "item_id": "use-case", "reason": "disagreed"} in progress(env)["left"]
    assert env.client.post(f"{BASE}/comments/{c['comment_id']}/resolve", headers=H[ADV]).status_code == 200            # the OTHER owner resolves it
    assert section_json(env, ADV, "scope")["items"][1]["disagreed"] is False and row(progress(env), "scope")["ready"] is True
    again = env.client.post(f"{BASE}/comments/{c['comment_id']}/resolve", headers=H[OTH])
    assert again.status_code == 200 and again.json()["resolved"] is True and len(events(env.db, "comment_resolve")) == 1      # idempotent: one event
    c2 = comment(env, ADV, "use-case", "Second thought.", kind="disagree").json()
    assert env.client.post(f"{BASE}/comments/{c2['comment_id']}/resolve", headers=H[ADV]).status_code == 200            # the author may resolve their own
    r = comment(env, OTH, "use-case", "A plain comment does not block.")
    assert r.status_code == 200 and row(progress(env), "scope")["ready"] is True


def test_resolving_shows_who_and_when_and_unknown_comments_are_404(env):
    c = comment(env, OTH, "use-case", "x", kind="disagree").json()
    out = env.client.post(f"{BASE}/comments/{c['comment_id']}/resolve", headers=H[ADV]).json()
    assert out["resolved"] is True and out["resolved_by"] == "you" and out["resolved_at"]
    assert section_json(env, OTH, "scope")["items"][1]["comments"][0]["resolved_by"] == "advisor"
    for bad in ("0" * 32, "not-a-comment-id", "A" * 32):
        assert env.client.post(f"{BASE}/comments/{bad}/resolve", headers=H[ADV]).status_code == 404
    yc = comment(env, YMEM, "ey-q1", "in Y", engine=Y).json()
    assert env.client.post(f"{BASE}/comments/{yc['comment_id']}/resolve", headers=H[ADV]).status_code == 404            # another engine's comment
    assert stored(env, "ey-q1", "questions", Y)["comment_count"] == 1 and not [c2 for c2 in env.db.data["onboarding_comments"].values() if c2["engine_id"] == Y and c2["resolved"]]


def test_the_administrator_may_read_and_comment_labelled_admin_and_nothing_more(env):
    r = comment(env, "admin", "use-case", "A note from Gary.")
    assert r.status_code == 200 and (r.json()["author"], r.json()["role"]) == ("admin", "admin")
    seen = section_json(env, ADV, "scope")["items"][1]["comments"][0]
    assert (seen["author"], seen["role"], seen["body"]) == ("admin", "admin", "A note from Gary.")
    assert comment(env, "admin", "use-case", "x", kind="disagree").status_code == 400                       # an administrator cannot block readiness
    c = comment(env, OTH, "use-case", "x", kind="disagree").json()
    before = snapshot(env.db)
    assert env.client.post(f"{BASE}/comments/{c['comment_id']}/resolve", headers=ADMIN).status_code == 404  # nor resolve
    assert env.client.put(f"{BASE}/items/use-case", json={"value": "x", "base_revision": 0}, headers=ADMIN).status_code == 404       # nor edit
    assert snapshot(env.db) == before
    (admin_event,) = [e for e in events(env.db, "comment") if e["actor_role"] == "admin"]
    assert admin_event["actor_subscriber_id"] == "admin"


# ---- readiness and the progress tracker -------------------------------------------------------------------------------------------------------------
def test_the_tracker_counts_every_section_lists_what_is_left_and_says_who_is_waited_on(env):
    p = progress(env)
    assert [r["key"] for r in p["sections"]] == ["scope", "questions", "keywords", "seeds"] and p["template_version"] == 1
    assert [(r["items"], r["open"], r["answered"], r["disagreed"], r["final"], r["approved"], r["ready"], r["status"]) for r in p["sections"]] == [
        (3, 3, 0, 0, 0, 0, False, "draft"), (3, 3, 0, 0, 0, 0, False, "draft"), (2, 2, 0, 0, 0, 0, False, "draft"), (2, 2, 0, 0, 0, 0, False, "draft")]
    assert p["left_total"] == 10 and len(p["left"]) == 10 and {x["reason"] for x in p["left"]} == {"unanswered"}
    assert p["waiting_on"] == {"who": ["owners"], "line": "Waiting on the owners to answer 10 item(s) and resolve 0 disagreement(s)"}
    for item_id, v in (("scope-statement", "s"), ("use-case", "u")):
        put(env, ADV, item_id, v, base=0)
    put(env, ADV, "out-of-scope", [], base=0)                                                              # an empty list, saved, is an answer
    p = progress(env)
    assert (row(p, "scope")["answered"], row(p, "scope")["open"], row(p, "scope")["ready"]) == (3, 0, True) and p["left_total"] == 7
    assert p["waiting_on"]["who"] == ["final_say", "owners"] and p["waiting_on"]["line"].startswith("Waiting on the final-say owner to mark ready sections final; the owners")
    assert progress(env, OTH) == p == progress(env, "admin")                                              # everyone sees the same tracker


def test_final_and_approved_counts_and_the_waiting_on_line_for_gary(env):
    for it, v in (("scope-statement", "s"), ("use-case", "u")):
        put(env, ADV, it, v, base=0)
    put(env, ADV, "out-of-scope", ["x"], base=0)
    set_section(env, "scope", "final", final_by=ADV)
    p = progress(env)
    assert (row(p, "scope")["final"], row(p, "scope")["approved"], row(p, "scope")["status"]) == (3, 0, "final")
    assert "admin" in p["waiting_on"]["who"] and "Gary to approve or reject" in p["waiting_on"]["line"] and "final_say" not in p["waiting_on"]["who"]
    set_section(env, "scope", "approved", approved_at="2026-11-02")
    p = progress(env)
    assert (row(p, "scope")["final"], row(p, "scope")["approved"]) == (0, 3) and "admin" not in p["waiting_on"]["who"]
    # a fully answered, fully approved engine waits on nobody
    for sec_key, ids in (("questions", ["ex-q1", "ex-q2", "ex-q3"]), ("keywords", ["kw-1", "kw-2"]), ("seeds", ["seed-1", "seed-2"])):
        for i in ids:
            put(env, ADV, i, q() if sec_key == "questions" else ({"list": "mute", "text": "t"} if sec_key == "keywords" else {"comment": ""}),
                "accept" if sec_key == "questions" else ("keep" if sec_key == "keywords" else "yes"), base=0)
        set_section(env, sec_key, "approved", approved_at="2026-11-02")
    p = progress(env)
    assert p["waiting_on"] == {"who": [], "line": "Nothing is waiting."} and p["left_total"] == 0 and all(r["approved"] == r["items"] for r in p["sections"])


def test_a_rejected_section_waits_on_the_owners_and_an_empty_section_is_never_ready(env):
    set_section(env, "seeds", "rejected", approver_note="Please look again.")
    p = progress(env)
    assert row(p, "seeds")["status"] == "rejected" and row(p, "seeds")["ready"] is False and "owners" in p["waiting_on"]["who"]
    ey = env.client.get(f"/api/onboarding/engines/{Y}", headers=H[YMEM]).json()["progress"]
    assert (row(ey, "scope")["items"], row(ey, "scope")["ready"]) == (0, False) and ey["waiting_on"]["who"] == ["owners"]           # only the questions item is open
    assert row(ey, "keywords")["ready"] is False and ey["left_total"] == 1


def test_the_left_list_is_capped_but_the_total_is_honest(env):
    for n in range(60):
        env.db.data["onboarding_items"][form.item_key(X, "keywords", f"kw-extra-{n}")] = {"engine_id": X, "section": "keywords", "item_id": f"kw-extra-{n}", "type": "keyword_entry",
                                                                                          "value": None, "choice": None, "revision": 0, "comment_count": 0, "history": [], "context": {}, "order": 100 + n}
    p = progress(env)
    assert len(p["left"]) == form.LEFT_LIST_CAP == 50 and p["left_total"] == 70


def test_the_content_hash_changes_with_the_content_and_differs_between_sections(env):
    a = section_json(env, ADV, "scope")["section"]["content_sha256"]
    assert a == section_json(env, OTH, "scope")["section"]["content_sha256"] != section_json(env, ADV, "questions")["section"]["content_sha256"]
    put(env, ADV, "use-case", "changed", base=0)
    b = section_json(env, ADV, "scope")["section"]["content_sha256"]
    assert b != a and b == section_json(env, ADV, "scope")["section"]["content_sha256"]
    comment(env, OTH, "use-case", "a comment")
    assert section_json(env, ADV, "scope")["section"]["content_sha256"] == b                                # a comment is not content


def test_section_view_lists_items_in_order_with_context_and_unknown_sections_are_404(env):
    s = section_json(env, ADV, "questions")
    assert [i["item_id"] for i in s["items"]] == ["ex-q1", "ex-q2", "ex-q3"] and s["items"][0]["context"] == {"original_wording": "Original question one?"}
    assert (s["section"]["title"], s["section"]["design"], s["section"]["status"], s["template_version"]) == ("Research questions", "2.2", "draft", 1)
    for bad in ("nope", "SCOPE", "scope__x"):
        assert env.client.get(f"{BASE}/sections/{bad}", headers=H[ADV]).status_code == 404


# ---- default deny: no route without a session; an owner of X gets 404 on Y -----------------------------------------------------------------------------
BODIES = {"PUT": {"value": "x", "choice": None, "base_revision": 0}, "POST": {"body": "x", "kind": "comment"}}


def engine_routes(env):
    from tests.test_onboarding_invites import walk
    out = []
    for r in walk(env.app.routes):
        if r.path.startswith("/api/onboarding/engines/"):
            for m in sorted(r.methods - {"HEAD", "OPTIONS"}):
                out.append((m, r.path))
    return sorted(out)


def fill(path, engine):
    return (path.replace("{engine_id}", engine).replace("{section_key}", "scope").replace("{item_id}", "ex-q1" if engine == X else "ey-q1")
            .replace("{comment_id}", "0" * 32))


def send(env, method, path, headers):
    body = BODIES.get(method)
    if path.endswith("/questions"):
        body = {"action": "add", "questions": [{"wording": "W?", "centrality": "central"}]}
    return env.client.request(method, path, headers=headers, **({"json": body} if body is not None and not path.endswith("/resolve") else {}))


def test_the_engine_routes_are_exactly_these(env):
    assert engine_routes(env) == sorted([
        ("GET", "/api/onboarding/engines/{engine_id}"), ("GET", "/api/onboarding/engines/{engine_id}/sections/{section_key}"),
        ("PUT", "/api/onboarding/engines/{engine_id}/items/{item_id}"), ("POST", "/api/onboarding/engines/{engine_id}/items/{item_id}/comments"),
        ("POST", "/api/onboarding/engines/{engine_id}/comments/{comment_id}/resolve"), ("POST", "/api/onboarding/engines/{engine_id}/questions")])


def test_no_route_is_reachable_without_a_session_and_a_stranger_gets_the_same_404(env):
    before = snapshot(env.db)
    cases = {"no credential": {}, "garbage token": {"X-Subscriber-Token": "zzz"}, "wrong admin key": {"X-Admin-API-Key": "wrong"}, "signed in, member of nothing": H[STRANGER],
             "member of the other engine": H[YMEM]}
    seen = set()
    for method, path in engine_routes(env):
        for name, headers in cases.items():
            r = send(env, method, fill(path, X), headers)
            assert (r.status_code, r.json()) == (404, {"detail": "Not found"}), (method, path, name, r.status_code)
            seen.add(r.text)
    assert len(seen) == 1 and snapshot(env.db) == before


def test_an_owner_of_engine_x_gets_404_on_engine_y_on_every_route(env):
    before = snapshot(env.db)
    for method, path in engine_routes(env):
        for who in (ADV, OTH):
            r = send(env, method, fill(path, Y), H[who])
            assert (r.status_code, r.json()) == (404, {"detail": "Not found"}), (method, path, who, r.status_code)
        r = send(env, method, fill(path, X), H[YMEM])                                                    # and Y's owner on X
        assert r.status_code == 404, (method, path)
    assert snapshot(env.db) == before


def test_an_item_id_from_another_engine_cannot_be_reached_through_ones_own_path(env):
    before = snapshot(env.db)
    assert put(env, YMEM, "ex-q1", q(), "accept", engine=Y).status_code == 404
    assert comment(env, YMEM, "ex-q1", "x", engine=Y).status_code == 404
    assert put(env, ADV, "ey-q1", q(), "accept", engine=X).status_code == 404
    assert snapshot(env.db) == before


def test_the_administrator_may_read_and_comment_but_every_owner_only_route_is_404(env):
    assert env.client.get(BASE, headers=ADMIN).status_code == 200 and env.client.get(f"{BASE}/sections/scope", headers=ADMIN).status_code == 200
    assert comment(env, "admin", "use-case", "ok").status_code == 200
    before = snapshot(env.db)
    for method, path in ((m, p) for m, p in engine_routes(env) if (m, p) not in {("GET", "/api/onboarding/engines/{engine_id}"), ("GET", "/api/onboarding/engines/{engine_id}/sections/{section_key}"),
                                                                                 ("POST", "/api/onboarding/engines/{engine_id}/items/{item_id}/comments")}):
        assert send(env, method, fill(path, X), ADMIN).status_code == 404, (method, path)
    assert snapshot(env.db) == before


def test_autosave_comments_and_questions_are_rate_limited_per_account_and_never_by_address(env):
    put(env, ADV, "use-case", "x", base=0)
    comment(env, OTH, "use-case", "c")
    comment(env, "admin", "use-case", "c")
    new_q(env, ADV)
    routes_seen = [k[1] for k, _ in env.limited]
    assert routes_seen == ["onboarding_autosave", "onboarding_comment", "onboarding_comment", "onboarding_question"]
    assert [k[0] for k, _ in env.limited] == [ADV, OTH, "admin", ADV]                                        # keyed by the account id, or 'admin'
    assert all(kw.get("fail_closed") is not True for _, kw in env.limited)                                  # autosave and comments fail open (the credential routes fail closed)
    assert not [s for s in strings(env.limited) if "@" in s]


def test_every_change_in_this_part_wrote_an_event_with_no_address_and_no_text(env):
    put(env, ADV, "use-case", "typed <b>text</b>", base=0)
    comment(env, OTH, "use-case", "a comment with text", kind="disagree")
    new_q(env, ADV)
    set_section(env, "scope", "final", final_by=ADV)
    put(env, OTH, "scope-statement", "reopens", base=0)
    actions = sorted(e["action"] for e in events(env.db))
    assert actions == ["comment", "item_edit", "item_edit", "question_add", "reopen"]
    for e in events(env.db):
        assert e["engine_id"] == X and e["ts"] and e["actor_role"] == "owner"
    assert not [s for e in events(env.db, "comment") + events(env.db, "question_add") for s in strings(e) if "a comment with text" in s or "@" in s]
