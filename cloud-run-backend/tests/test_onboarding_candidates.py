"""Onboarding PR 4b-2a: the review of the hold list (design 2.5, 5.6, 5.7): the optional review section, the review view (the only place an abstract is
returned), one decision and bulk marking, the decisions table in docs/hold_list.md, the ingest_keep Core task, the wrong-paper guard and the agent-run abstract
fetch (scripts/onboarding/fetch_abstracts.py). Offline: the in-memory Firestore with atomic transactions, a mocked clock, a mocked repository and a table of
canned registry answers. Synthetic papers only."""
import hashlib
import importlib.util
import inspect
import json
import re
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from tests.test_onboarding_bundle import A, approve, bucket, make  # noqa: F401  (bucket is a fixture)
from tests.test_onboarding_gates import final, final_all
from tests.test_onboarding_items import ADMIN, ADV, H, OTH, STRANGER, X, Y, YMEM, env, events, item, put, snapshot, stored, strings  # noqa: F401  (env is a fixture)
from tests.test_onboarding_lookup import Web, arxiv_feed, crossref, openalex
from tests.test_onboarding_review import RAW, decide, get, http, with_repo  # noqa: F401  (http is a fixture)
from tests.test_onboarding_workspace import progress, section_doc
from utils import onboarding as ob
from utils import onboarding_bundle as bundles
from utils import onboarding_candidates as candidates
from utils import onboarding_form as form
from utils import onboarding_lint as lint
from utils import onboarding_lookup as lookup
from utils import onboarding_render as render
from utils import onboarding_template as tpl

ROOT = Path(__file__).resolve().parents[2]
BASE = f"/api/onboarding/engines/{X}"
SECRET_ABSTRACT = "ZEBRA-ABSTRACT a synthetic abstract that must never leave by any route but the review"
SECRET_COMMENT = "QUOKKA-COMMENT an owner's private remark"
HOLD_BASE = ("# Synthetic hold list\n\n- `cited_by=N` legend line\n\n## Group one (2)\n\n- Held paper one -- `10.9998/held.1`, top_cited, cited_by=5\n"
             "- Held paper two **[Tag: likely]** -- `10.9998/held.2`, top_cited, cited_by=4\n\n## Group two (1)\n\n- Held preprint three -- `2401.00003`, cited_by_2plus_seeds\n")
PAPERS = [("doi:10.9998/held.1", "Held paper one", "Group one (2)", False), ("doi:10.9998/held.2", "Held paper two [Tag: likely]", "Group one (2)", True),
          ("arxiv:2401.00003", "Held preprint three", "Group two (1)", False)]


def rid(key):
    return "cand-" + hashlib.sha256(key.encode()).hexdigest()[:12]


def cid(key, engine=X):
    return f"{engine}__{hashlib.sha256(key.encode()).hexdigest()[:12]}"


IDS = [rid(p[0]) for p in PAPERS]


def with_hold_list(env, engine=X, papers=PAPERS):
    """What the loader writes for a hold list: one candidate and one unanswered review decision per paper."""
    for n, (key, title, group, likely) in enumerate(papers):
        kind = key.split(":", 1)[0]
        env.db.data.setdefault(candidates.CANDIDATES, {})[cid(key, engine)] = {
            "candidate_id": cid(key, engine), "engine_id": engine, "origin": "hold_list", "identifier": key, "identifiers": {kind: key}, "registry_record": None,
            "abstract": None, "decision": None, "question_ids": [], "flags": {"group": group, "likely_keep": likely, "reason": "top_cited", "cited_by": 5, "title": title},
            "source_sha256": "0" * 64}
        doc = item(engine, "review", rid(key), "candidate_decision", n, value={"comment": ""},
                   context={"candidate_id": cid(key, engine), "identifier": key, "identifiers": {kind: key}, "title": title, "group": group, "likely_keep": likely,
                            "reason": "top_cited", "cited_by": 5, "loaded_by": "load_engine"})
        env.db.data["onboarding_items"][form.item_key(engine, "review", rid(key))] = doc
    return env


def cand(env, n, engine=X):
    return env.db.data[candidates.CANDIDATES][cid(PAPERS[n][0], engine)]


def review(env, who=ADV, engine=X):
    return env.client.get(f"/api/onboarding/engines/{engine}/review", headers=H[who] if who in H else ADMIN)


def bulk(env, who, choice, papers, engine=X):
    return env.client.post(f"/api/onboarding/engines/{engine}/review/bulk", headers=H[who] if who in H else ADMIN,
                           json={"choice": choice, "papers": [{"item_id": i, "base_revision": r} for i, r in papers]})


def decide_all(env, choices=("keep", "drop", "unsure")):
    for i, c in zip(IDS, choices):
        assert put(env, ADV, i, {"comment": ""}, c).status_code == 200


# ---- the template --------------------------------------------------------------------------------------------------------------------------------------
def test_a_review_decision_is_keep_drop_or_unsure_with_a_capped_comment():
    assert tpl.section_of("candidate_decision") == "review" and tpl.is_optional("review") and not tpl.is_optional("seeds")
    for c in ("keep", "drop", "unsure"):
        assert tpl.validate_item("candidate_decision", {"comment": " ok "}, c) == ({"comment": "ok"}, c)
    assert tpl.validate_item("candidate_decision", None, "keep") == ({"comment": ""}, "keep")
    assert tpl.validate_item("candidate_decision", {"comment": "x" * 1000}, "keep")[0]["comment"] == "x" * 1000
    for value, choice in (({"comment": "x" * 1001}, "keep"), ({"comment": ""}, "yes"), ({"comment": ""}, None), ({"comment": "", "abstract": "x"}, "keep"), ("text", "keep")):
        with pytest.raises(tpl.TemplateError):
            tpl.validate_item("candidate_decision", value, choice)


# ---- an engine with no hold list has no review section ---------------------------------------------------------------------------------------------------
def test_an_engine_with_no_hold_list_shows_no_review_section_anywhere(env):
    assert [r["key"] for r in progress(env)["sections"]] == ["scope", "questions", "keywords", "seeds"]
    assert review(env).status_code == 404 and env.client.get(f"{BASE}/sections/review", headers=H[ADV]).status_code == 404
    assert review(env, "admin").status_code == 404
    engine = env.client.get(BASE, headers=H[ADV]).json()
    assert engine["may_mark"] == ["scope", "questions", "keywords", "seeds"]
    out = final_all(env, ADV).json()
    assert "review" not in [s["section"] for s in out["skipped"]] and "review" not in out["marked"]
    detail = get(env, f"/engines/{X}").json()
    assert [r["key"] for r in detail["sections"]] == ["scope", "questions", "keywords", "seeds"] and len(detail["details"]) == 4
    assert bulk(env, ADV, "keep", [(IDS[0], 0)]).status_code == 404


def test_an_engine_with_a_hold_list_shows_the_review_section_in_the_tracker_and_the_dashboard(env):
    with_hold_list(env)
    rows = {r["key"]: r for r in progress(env)["sections"]}
    assert list(rows) == ["scope", "questions", "keywords", "seeds", "review"]
    assert (rows["review"]["title"], rows["review"]["items"], rows["review"]["open"], rows["review"]["ready"]) == ("Hold list: review", 3, 3, False)
    assert env.client.get(BASE, headers=H[ADV]).json()["may_mark"][-1] == "review"
    detail = get(env, f"/engines/{X}").json()
    assert [r["key"] for r in detail["sections"]][-1] == "review" and [i["context"]["title"] for i in detail["details"][-1]["items"]] == [p[1] for p in PAPERS]


# ---- the review view -------------------------------------------------------------------------------------------------------------------------------------
def test_the_review_lists_every_paper_in_order_with_its_flags_decision_and_abstract(env):
    with_hold_list(env)
    cand(env, 0).update({"abstract": "The first abstract.", "abstract_source": "crossref", "abstract_fetched_at": "2026-11-16T00:00:00+00:00", "lookup_state": "found",
                         "registry_record": {"title": "Held paper one", "authors": ["Ada Example"], "year": 2021}})
    cand(env, 1).update({"lookup_state": "no_abstract", "registry_record": {"title": "Held paper two", "authors": [], "year": 2020}})
    assert put(env, OTH, IDS[0], {"comment": "worth keeping"}, "keep").status_code == 200
    r = review(env, ADV)
    assert r.status_code == 200
    out = r.json()
    assert [p["item_id"] for p in out["papers"]] == IDS and [p["title"] for p in out["papers"]] == [p[1] for p in PAPERS]
    one, two, three = out["papers"]
    assert (one["identifier"], one["group"], one["likely_keep"], one["reason"], one["cited_by"]) == ("doi:10.9998/held.1", "Group one (2)", False, "top_cited", 5)
    assert (one["choice"], one["comment"], one["revision"], one["answered"], one["author"]) == ("keep", "worth keeping", 1, True, "other owner")
    assert (one["abstract"], one["abstract_source"], one["lookup_state"], one["unresolved"], one["warning"]) == ("The first abstract.", "crossref", "found", False, None)
    assert one["registry"] == {"title": "Held paper one", "authors": ["Ada Example"], "year": 2021}
    assert (two["likely_keep"], two["abstract"], two["lookup_state"], two["unresolved"], two["answered"]) == (True, None, "no_abstract", True, False)
    assert (three["lookup_state"], three["unresolved"], three["registry"], three["choice"]) == (None, True, None, None)         # never fetched: unresolved
    assert out["groups"] == ["Group one (2)", "Group two (1)"] and out["choices"] == ["keep", "drop", "unsure"] and out["bulk_max"] == 100
    assert out["counts"] == {"papers": 3, "likely_keep": 1, "unresolved": 2, "keep": 1, "drop": 0, "unsure": 0, "unanswered": 2}
    assert (out["section"]["key"], out["section"]["status"], out["section"]["items"], out["section"]["open"], out["section"]["ready"]) == ("review", "draft", 3, 2, False)
    assert not [s for s in strings(out) if "sub-" in s or "tok-" in s]                                                        # no id of a person


def test_a_title_mismatch_shows_as_unresolved_with_the_abstract_the_registrys_own_title_and_a_plain_warning(env):
    with_hold_list(env)
    cand(env, 0).update({"abstract": "An abstract of something else.", "abstract_source": "crossref", "lookup_state": "title_mismatch",
                         "registry_record": {"title": "A quite different paper", "authors": ["Bo Sample"], "year": 1999}})
    one = review(env).json()["papers"][0]
    assert one["unresolved"] is True and one["lookup_state"] == "title_mismatch" and one["abstract"] == "An abstract of something else."
    assert one["registry"]["title"] == "A quite different paper" and one["title"] == "Held paper one"
    assert one["warning"] == candidates.MISMATCH_WARNING and "may belong to a different paper" in one["warning"]
    assert review(env).json()["counts"]["unresolved"] == 3


def test_the_review_is_for_members_of_that_engine_and_the_admin_and_bulk_marking_for_its_owners_only(env):
    with_hold_list(env)
    cand(env, 0)["abstract"] = SECRET_ABSTRACT
    before = snapshot(env.db)
    for who in (STRANGER, YMEM):                                              # signed in but no member; an owner of ANOTHER engine
        r = review(env, who)
        assert (r.status_code, r.json()) == (404, {"detail": "Not found"}) and SECRET_ABSTRACT not in r.text
        assert bulk(env, who, "keep", [(IDS[0], 0)]).status_code == 404
    assert env.client.get(f"{BASE}/review").status_code == 404                # no credential
    assert review(env, YMEM, engine=Y).status_code == 404                     # their own engine has no hold list
    admin = review(env, "admin")
    assert admin.status_code == 200 and admin.json()["papers"][0]["abstract"] == SECRET_ABSTRACT          # the admin may read
    assert bulk(env, "admin", "keep", [(IDS[0], 0)]).status_code == 404                                    # and never decide
    assert env.client.put(f"{BASE}/items/{IDS[0]}", json={"value": {"comment": ""}, "choice": "keep", "base_revision": 0}, headers=ADMIN).status_code == 404
    assert snapshot(env.db) == before


# ---- one decision, and "unsure" is an answer ---------------------------------------------------------------------------------------------------------------
def test_one_decision_is_saved_like_any_answer_and_unsure_counts_as_answered(env):
    with_hold_list(env)
    r = put(env, ADV, IDS[0], {"comment": "not sure yet"}, "unsure")
    assert r.status_code == 200 and (r.json()["item"]["choice"], r.json()["item"]["answered"]) == ("unsure", True)
    assert put(env, ADV, IDS[0], {"comment": ""}, "maybe", base=1).status_code == 400 and put(env, ADV, IDS[0], {"comment": ""}, "keep", base=0).status_code == 409
    decide_all_rest = [put(env, ADV, i, {"comment": ""}, "unsure") for i in IDS[1:]]
    assert all(x.status_code == 200 for x in decide_all_rest)
    row = {r["key"]: r for r in progress(env)["sections"]}["review"]
    assert (row["open"], row["answered"], row["ready"]) == (0, 3, True)                    # every paper unsure: the section is ready
    assert final(env, ADV, "review").status_code == 200 and section_doc(env, "review")["status"] == "final"
    (e,) = [e for e in events(env.db, "item_edit") if e["item_id"] == IDS[0]]
    assert e["choice"] == "unsure" and e["section"] == "review"


# ---- bulk marking ------------------------------------------------------------------------------------------------------------------------------------------
def test_bulk_marking_sets_one_choice_keeps_each_comment_and_writes_one_event(env):
    with_hold_list(env)
    put(env, OTH, IDS[0], {"comment": SECRET_COMMENT}, "drop")
    r = bulk(env, ADV, "keep", [(IDS[0], 1), (IDS[1], 0), (IDS[2], 0)])
    assert r.status_code == 200 and r.json() == {"marked": IDS, "unchanged": [], "section_status": "draft"}
    a, b, c = (stored(env, i, "review") for i in IDS)
    assert (a["choice"], a["revision"], a["value"], a["author_subscriber_id"]) == ("keep", 2, {"comment": SECRET_COMMENT}, ADV)
    assert a["history"][0]["choice"] == "drop" and a["history"][0]["author"] == OTH and (b["choice"], b["revision"], b["history"]) == ("keep", 1, [])
    (e,) = events(env.db, "review_bulk")
    assert e["choice"] == "keep" and e["actor_subscriber_id"] == ADV and e["actor_role"] == "owner" and e["section"] == "review"
    assert e["items"] == [{"item_id": IDS[0], "before_choice": "drop", "revision": 2}, {"item_id": IDS[1], "before_choice": None, "revision": 1},
                          {"item_id": IDS[2], "before_choice": None, "revision": 1}]
    assert SECRET_COMMENT not in json.dumps(e)                                                 # the event holds ids and choices, never text
    assert ((ADV, "onboarding_review_bulk"), {"limit": 60, "window_seconds": 3600}) in env.limited
    assert review(env).json()["counts"]["keep"] == 3


def test_a_bulk_mark_with_one_stale_paper_changes_nothing_and_names_it(env):
    with_hold_list(env)
    put(env, OTH, IDS[1], {"comment": "seen"}, "drop")                                        # the other owner got there first
    before = snapshot(env.db)
    r = bulk(env, ADV, "keep", [(IDS[0], 0), (IDS[1], 0), (IDS[2], 0)])                        # ADV still holds revision 0 of the second paper
    assert r.status_code == 409 and snapshot(env.db) == before
    d = r.json()["detail"]
    assert d["reason"] == "stale" and d["stale"] == [{"item_id": IDS[1], "title": PAPERS[1][1]}] and "nothing was marked" in d["message"]
    assert not events(env.db, "review_bulk")
    assert bulk(env, ADV, "keep", [(IDS[0], 0), (IDS[1], 1), (IDS[2], 0)]).status_code == 200  # with the right revision the same batch goes through


def test_bulk_refusals_write_nothing(env):
    with_hold_list(env)
    before = snapshot(env.db)
    assert bulk(env, ADV, "keep", [(IDS[0], 0), ("cand-ffffffffffff", 0)]).status_code == 404          # one unknown paper refuses the batch
    assert bulk(env, ADV, "keep", [("ex-q1", 0)]).status_code == 404                                    # an item that is not a review decision
    assert bulk(env, ADV, "keep", [(IDS[0], 0), (IDS[0], 0)]).status_code == 400                        # listed twice
    assert bulk(env, ADV, "yes", [(IDS[0], 0)]).status_code == 400
    assert bulk(env, ADV, "keep", []).status_code == 422
    assert bulk(env, ADV, "keep", [(f"cand-{n:012d}", 0) for n in range(101)]).status_code == 422        # 100 is the most
    assert env.client.post(f"{BASE}/review/bulk", headers=H[ADV], json={"choice": "keep", "papers": [{"item_id": IDS[0], "base_revision": True}]}).status_code == 422
    env.db.data["onboarding_engines"][X]["state"] = "closed"
    assert bulk(env, ADV, "keep", [(IDS[0], 0)]).status_code == 409
    env.db.data["onboarding_engines"][X]["state"] = "open"
    assert snapshot(env.db) == before
    env.db.fail_after_ops = 2                                                                             # a failure partway through: nothing is kept
    with pytest.raises(RuntimeError):
        bulk(env, ADV, "keep", [(i, 0) for i in IDS])
    env.db.fail_after_ops = None
    assert snapshot(env.db) == before


def test_bulk_at_the_limit_of_one_hundred_and_a_paper_that_already_has_the_choice_is_left_alone(env):
    papers = [(f"doi:10.9998/many.{n}", f"Many {n}", "G", False) for n in range(100)]
    with_hold_list(env, papers=papers)
    ids_ = [rid(p[0]) for p in papers]
    put(env, ADV, ids_[0], {"comment": ""}, "drop")
    r = bulk(env, ADV, "drop", [(ids_[0], 1)] + [(i, 0) for i in ids_[1:]])
    assert r.status_code == 200 and len(r.json()["marked"]) == 99 and r.json()["unchanged"] == [ids_[0]]
    assert stored(env, ids_[0], "review")["revision"] == 1                                                # no new revision for a paper that did not change
    before = snapshot(env.db)
    again = bulk(env, ADV, "drop", [(i, 1) for i in ids_])
    assert again.status_code == 200 and again.json()["marked"] == [] and snapshot(env.db) == before        # nothing to change: no write, no event


def test_a_bulk_mark_reopens_a_final_section_and_tells_the_final_say_owner(env):
    with_hold_list(env)
    decide_all(env)
    assert final(env, ADV, "review").status_code == 200
    env.mail.sent.clear()
    assert bulk(env, OTH, "keep", [(IDS[1], 1)]).json()["section_status"] == "draft"
    assert [e["from_status"] for e in events(env.db, "reopen") if e["section"] == "review"] == ["final"]
    assert [(m["kind"], m["section"]) for m in env.mail.sent] == [("reopened", "Hold list: review")]


# ---- an abstract and a comment go nowhere they should not ---------------------------------------------------------------------------------------------------
def approved_review(env, http_):
    with_repo(env)
    with_hold_list(env)
    http_.table[RAW + "docs/hold_list.md"] = (200, HOLD_BASE)
    for n in range(3):
        cand(env, n).update({"abstract": SECRET_ABSTRACT, "abstract_source": "crossref", "lookup_state": "found", "registry_record": {"title": PAPERS[n][1], "authors": [], "year": 2020}})
    put(env, ADV, IDS[0], {"comment": SECRET_COMMENT}, "keep")
    put(env, ADV, IDS[1], {"comment": ""}, "drop")
    put(env, ADV, IDS[2], {"comment": ""}, "unsure")
    assert final(env, ADV, "review").status_code == 200
    return env


def test_an_abstract_appears_in_no_section_view_dashboard_diff_bundle_or_event(env, http, bucket):
    approved_review(env, http)
    assert SECRET_ABSTRACT in review(env).text                                                             # the one route that returns it
    assert SECRET_ABSTRACT not in env.client.get(f"{BASE}/sections/review", headers=H[ADV]).text
    assert SECRET_ABSTRACT not in env.client.get(BASE, headers=H[ADV]).text
    assert SECRET_ABSTRACT not in get(env, f"/engines/{X}").text and SECRET_ABSTRACT not in get(env, "/engines").text
    diff = get(env, f"/engines/{X}/diff?section=review")
    assert diff.status_code == 200 and SECRET_ABSTRACT not in diff.text and "| keep | `doi:10.9998/held.1` | Held paper one |" in diff.text
    assert decide(env, "review", "approve").status_code == 200
    out = make(env, ["review"])
    assert out.status_code == 200 and out.json()["status"] == "created" and SECRET_ABSTRACT not in out.text
    stored_bundle = bucket[bundles.object_path(X, out.json()["bundle_id"])].decode()
    assert SECRET_ABSTRACT not in stored_bundle and "ZEBRA" not in json.dumps(env.db.data.get(ob.EVENTS, {}))
    assert "ZEBRA" not in json.dumps(env.db.data[bundles.BUNDLES])


def test_a_comment_appears_in_no_proposed_file_and_the_bundle_carries_the_decisions_table_and_the_keep_task(env, http, bucket):
    approved_review(env, http)
    assert SECRET_COMMENT in review(env).text                                                              # the owners and Gary still see it in the form
    assert SECRET_COMMENT in get(env, f"/engines/{X}").text
    assert SECRET_COMMENT not in get(env, f"/engines/{X}/diff?section=review").text
    assert decide(env, "review", "approve").status_code == 200
    out = make(env, ["review"]).json()
    b = json.loads(bucket[bundles.object_path(X, out["bundle_id"])])
    assert "QUOKKA" not in json.dumps(b) and all(b["checks"].values())
    (f,) = [f for f in b["files"] if f["path"] == "docs/hold_list.md"]
    assert f["action"] == "modify" and f["proposed_content"].startswith(HOLD_BASE)                         # the list itself is left exactly as it is
    block = f["proposed_content"][len(HOLD_BASE):]
    assert block == ("\n" + render.HOLD_BEGIN + "\n" + render.HOLD_CAPTION + "\n\n| Decision | Identifier | Title |\n|---|---|---|\n"
                     "| keep | `doi:10.9998/held.1` | Held paper one |\n| drop | `doi:10.9998/held.2` | Held paper two [Tag: likely] |\n"
                     "| unsure | `arxiv:2401.00003` | Held preprint three |\n" + render.HOLD_END + "\n")
    assert [t for t in b["core_tasks"] if t["kind"] == "ingest_keep"] == [{"kind": "ingest_keep", "payload": {"identifier": "doi:10.9998/held.1"}}]
    assert "Hold list: review" in b["pr_text"]["title"]


# ---- the decisions table: the loader still reads the same papers; the linter guards the block ------------------------------------------------------------------
def load_script(name):
    spec = importlib.util.spec_from_file_location(f"{name}_under_test_4b2", ROOT / "scripts" / "onboarding" / f"{name}.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def review_items(choices=("keep", "drop", "unsure")):
    return [{"item_id": rid(k), "type": "candidate_decision", "choice": c, "value": {"comment": SECRET_COMMENT}, "context": {"identifier": k, "title": t}}
            for (k, t, _, _), c in zip(PAPERS, choices)]


def test_the_loader_reads_the_same_papers_after_the_decisions_block_is_added_and_a_second_render_replaces_the_block():
    le = load_script("load_engine")
    before, skipped_before = le.parse_hold(HOLD_BASE)
    once, _ = render.render_hold_list(HOLD_BASE, review_items())
    after, skipped_after = le.parse_hold(once)
    assert after == before and skipped_after == skipped_before and len(after) == 3
    fixture = (Path(__file__).parent / "fixtures" / "onboarding_loader" / "docs" / "hold_list.md").read_text(encoding="utf-8")
    real, _ = le.parse_hold(fixture)
    items = [{"item_id": le.review_item_id(c["key"]), "choice": "keep", "context": {"identifier": c["key"], "title": c["flags"]["title"]}} for c in real]
    assert le.parse_hold(render.render_hold_list(fixture, items)[0])[0] == real and len(real) == 65                 # the 65 synthetic papers of the loader fixture
    twice, _ = render.render_hold_list(once, review_items(("drop", "drop", "keep")))
    assert twice.count(render.HOLD_BEGIN) == 1 and twice.count(render.HOLD_END) == 1 and twice.startswith(HOLD_BASE) and "| drop | `doi:10.9998/held.1` |" in twice
    assert "| keep | `doi:10.9998/held.1` |" not in twice and SECRET_COMMENT not in once + twice
    alone, _ = render.render_hold_list(None, review_items())
    assert alone.startswith(render.HOLD_BEGIN) and le.parse_hold(alone) == ([], [])
    piped, _ = render.render_hold_list("", [{"item_id": "cand-1", "choice": "keep", "context": {"identifier": "doi:10.1/x", "title": "A | B\nC"}}])
    assert "| keep | `doi:10.1/x` | A \\| B C |" in piped


def test_the_linter_refuses_a_decisions_block_that_would_change_what_the_loader_reads():
    good, _ = render.render_hold_list(HOLD_BASE, review_items())
    check = lambda text: lint.run_checks([{"path": "docs/hold_list.md", "proposed_content": text}], [], [], {"docs/hold_list.md": HOLD_BASE})   # noqa: E731
    assert check(good)["checks"]["schema_ok"] is True and check(HOLD_BASE)["checks"]["schema_ok"] is True
    planted = {"a bullet in the block": good.replace(render.HOLD_CAPTION, render.HOLD_CAPTION + "\n- Smuggled paper -- `10.9998/x`"),
               "a heading in the block": good.replace(render.HOLD_CAPTION, "## A new group"),
               "a row with no decision": good.replace("| unsure |", "| unanswered |"),
               "two blocks": good + good[len(HOLD_BASE):],
               "an end with no begin": good.replace(render.HOLD_BEGIN, "")}
    for name, text in planted.items():
        out = check(text)
        assert out["checks"]["schema_ok"] is False, name
        assert all("Smuggled" not in p and "Held paper" not in p for p in out["problems"]["schema_ok"]), name          # a problem names the file, never the text


def test_the_ingest_keep_task_is_one_per_kept_paper_and_only_for_review_decisions():
    tasks = bundles.core_tasks({"review": review_items(("keep", "keep", "drop"))})
    assert tasks == [{"kind": "ingest_keep", "payload": {"identifier": "doi:10.9998/held.1"}}, {"kind": "ingest_keep", "payload": {"identifier": "doi:10.9998/held.2"}}]
    assert bundles.core_tasks({"review": review_items(("unsure", "drop", "drop"))}) == []


# ---- the wrong-paper guard ---------------------------------------------------------------------------------------------------------------------------------
@pytest.mark.parametrize("ours,theirs,same", [
    ("Persistent cohomology and circular coordinates", "Persistent Cohomology and Circular Coordinates.", True),
    ("Held paper two [Tag: likely]", "Held paper two", True),
    ("Toroidal coordinates: decorrelating circular coordinates", "Toroidal Coordinates: Decorrelating Circular Coordinates With Lattice Reduction", True),
    ("Sparse circular coordinates via principal Z-bundles", "Sparse Circular Coordinates via Principal ℤ-Bundles", True),
    ("A study of synthetic things", "A quite different paper about other matters", False),
    ("Circular coordinates", "Erratum", False), ("", "", False), ("A title", None, False),
    ("Topology of data", "Topology of viral evolution in host populations", False),
])
def test_two_titles_resemble_each_other_only_when_they_look_like_the_same_paper(ours, theirs, same):
    assert candidates.title_resembles(ours, theirs) is same and candidates.title_resembles(theirs, ours) is same


def found(title, abstract="An abstract.", source="crossref"):
    return {"state": "found", "results": [{"title": title, "authors": ["Ada Example"], "year": 2021, "abstract": abstract, "identifiers": {"doi": "doi:10.9998/held.1"},
                                           "sources": {"title": source, "authors": source, "year": source, "abstract": source if abstract else None}}]}


def test_a_fetch_can_only_add_and_never_replaces_what_an_earlier_run_stored():
    c = {"flags": {"title": "Held paper one"}, "abstract": None}
    out = candidates.fetch_update(c, found("Held paper one"), "T")
    assert (out["lookup_state"], out["abstract"], out["abstract_source"], out["registry_record"]["title"]) == ("found", "An abstract.", "crossref", "Held paper one")
    assert set(out["registry_record"]) == {"title", "authors", "year", "identifiers", "sources"}
    none = candidates.fetch_update(c, found("Held paper one", abstract=""), "T")
    assert none["lookup_state"] == "no_abstract" and "abstract" not in none and "abstract_source" not in none
    wrong = candidates.fetch_update(c, found("Something else entirely here"), "T")
    assert wrong["lookup_state"] == "title_mismatch" and wrong["abstract"] == "An abstract." and wrong["registry_record"]["title"] == "Something else entirely here"
    assert candidates.fetch_update(c, {"state": "not_found", "results": []}, "T") == {"lookup_state": "not_found", "abstract_fetched_at": "T"}
    assert candidates.fetch_update(c, {"state": "unavailable", "results": []}, "T")["lookup_state"] == "unavailable"
    have = {**c, "abstract": "Already here.", "lookup_state": "found"}
    assert not candidates.needs_fetch(have) and candidates.fetch_update(have, found("Held paper one", abstract="A newer one."), "T") is None
    partial = {**c, "lookup_state": "no_abstract", "registry_record": {"title": "Held paper one"}}
    assert candidates.fetch_update(partial, {"state": "unavailable", "results": []}, "T") is None            # a bad minute does not erase the record
    assert candidates.fetch_update(partial, found("Held paper one"), "T")["lookup_state"] == "found"         # and a later run fills the abstract in
    assert candidates.fetch_update({**c, "lookup_state": "not_found"}, {"state": "not_found", "results": []}, "T") is None


# ---- the agent-run abstract fetch ---------------------------------------------------------------------------------------------------------------------------
NOW = datetime(2026, 11, 16, 18, 0, tzinfo=timezone.utc)
LINE = f"Approved: fetch abstracts for {X} into regal-scholar-453620-r7"
CR1 = "https://api.crossref.org/works/10.9998%2Fheld.1"
CR2 = "https://api.crossref.org/works/10.9998%2Fheld.2"
OA2 = "https://api.openalex.org/works/doi:10.9998/held.2"
S22 = "https://api.semanticscholar.org/graph/v1/paper/DOI:10.9998/held.2?fields=title%2Cyear%2Cauthors%2Cabstract%2CexternalIds"
AX3 = "https://export.arxiv.org/api/query?id_list=2401.00003&max_results=1"


@pytest.fixture
def fetch(env, monkeypatch):
    fa = load_script("fetch_abstracts")
    web = Web()
    monkeypatch.setattr(lookup, "_http_get", web)
    slept = []

    def run(*args):
        lines = []
        code = fa.main(["--engine-id", X, *args], db=env.db, now=NOW, out=lines.append, sleep=slept.append, modules=(ob, candidates, lookup))
        return code, "\n".join(lines)
    return type("Fetch", (), {"run": staticmethod(run), "web": web, "slept": slept, "fa": fa})()


def canned(web):
    web.table[CR1] = (200, crossref(title="Held paper one", doi="10.9998/held.1"))
    web.table[CR2] = (200, crossref(title="Held paper two", doi="10.9998/held.2", abstract=None))                 # Crossref has no abstract; OpenAlex and S2 have nothing
    web.table[OA2] = (200, openalex(title="Held paper two", doi="10.9998/held.2", words=()))
    web.table[AX3] = (200, arxiv_feed().replace(b"2401.00001", b"2401.00003"))                                    # its title is "A synthetic preprint": not ours


def test_the_fetch_says_in_its_docstring_that_no_owner_consent_is_needed_and_why(fetch):
    doc = " ".join(fetch.fa.__doc__.split())
    assert "NO OWNER'S CONSENT IS NEEDED" in doc and "PUBLIC repository" in doc and "not from anything an owner typed or uploaded" in doc


def test_a_dry_run_calls_no_registry_and_writes_nothing(env, fetch):
    with_hold_list(env)
    canned(fetch.web)
    before = snapshot(env.db)
    code, out = fetch.run()
    assert code == 0 and fetch.web.calls == [] and snapshot(env.db) == before
    assert "3 hold-list papers, 0 already have an abstract, 3 to look up" in out and "would look up: doi:10.9998/held.1" in out and LINE in out


def test_apply_needs_the_exact_typed_line(env, fetch, capsys):
    with_hold_list(env)
    before = snapshot(env.db)
    for args in (["--apply"], ["--apply", "--approval", "Approved"], ["--apply", "--approval", LINE.replace(X, Y)], ["--pace", "0.5"], ["--limit", "401"]):
        assert fetch.run(*args)[0] == 2
    assert fetch.web.calls == [] and snapshot(env.db) == before
    assert fetch.fa.main(["--engine-id", "no-such-engine"], db=env.db, now=NOW, out=lambda s: None, modules=(ob, candidates, lookup)) == 2
    capsys.readouterr()


def test_apply_fetches_each_paper_paced_and_writes_everything_in_one_transaction_with_one_event(env, fetch):
    with_hold_list(env)
    canned(fetch.web)
    items_before = json.dumps(env.db.data["onboarding_items"], sort_keys=True, default=str)
    code, out = fetch.run("--apply", "--approval", LINE)
    assert code == 0 and fetch.slept == [3.0, 3.0]                                                                 # one paper every three seconds
    calls = fetch.web.calls                                                                                        # papers go in candidate-id order
    assert sorted(calls) == sorted([AX3, CR1, CR2, OA2, S22]) and calls.index(CR2) < calls.index(OA2) < calls.index(S22)      # only the four registries
    one, two, three = (cand(env, n) for n in range(3))
    assert (one["lookup_state"], one["abstract"], one["abstract_source"], one["abstract_fetched_at"]) == ("found", "The abstract text.", "crossref", NOW.isoformat())
    assert one["registry_record"]["title"] == "Held paper one" and one["registry_record"]["identifiers"] == {"doi": "doi:10.9998/held.1"}
    assert (two["lookup_state"], two["abstract"], two["registry_record"]["title"]) == ("no_abstract", None, "Held paper two")
    assert (three["lookup_state"], three["abstract"], three["registry_record"]["title"]) == ("title_mismatch", "Its summary.", "A synthetic preprint")
    assert one["flags"]["title"] == "Held paper one" and one["decision"] is None and one["source_sha256"] == "0" * 64     # nothing else on the paper changed
    (e,) = events(env.db, "abstract_fetch")
    assert e["counts"] == {"found": 1, "no_abstract": 1, "title_mismatch": 1} and e["actor_role"] == "admin" and e["engine_id"] == X
    assert e["candidates"]["found"] == [cid(PAPERS[0][0])] and "abstract text" not in json.dumps(e) and "Held paper" not in json.dumps(e)
    assert json.dumps(env.db.data["onboarding_items"], sort_keys=True, default=str) == items_before                 # no decision, no item, was touched
    assert lookup.CACHE not in env.db.data                                                                          # the lookup cache is not written
    assert "APPLIED: 3 papers written (1 found, 1 no_abstract, 1 title_mismatch)" in out
    shown = review(env).json()
    assert [p["unresolved"] for p in shown["papers"]] == [False, True, True] and shown["papers"][2]["warning"]


def test_each_paper_keeps_its_own_lookup_time_the_event_the_writes_time_and_every_line_is_timestamped(env, fetch):
    """BULLETIN 049, F2: every paper and the event used to carry the run's start time."""
    with_hold_list(env)
    canned(fetch.web)
    steps = [NOW + timedelta(seconds=s) for s in (0, 70, 140, 210)]                  # three lookups a minute apart, then the write
    ticks, lines = iter(steps), []
    code = fetch.fa.main(["--engine-id", X, "--apply", "--approval", LINE], db=env.db, out=lines.append, sleep=lambda s: None,
                         modules=(ob, candidates, lookup), clock=lambda: next(ticks))
    assert code == 0
    stamped = [ln for ln in lines if re.match(r"^  \[\d\d:\d\d:\d\dZ\] \d/3 ", ln)]
    assert [ln.split("]")[0] for ln in stamped] == ["  [18:00:00Z", "  [18:01:10Z", "  [18:02:20Z"]
    assert all(re.search(r"\(\d+\.\d s\)$", ln) for ln in stamped)                    # and how long that lookup took
    fetched = sorted(cand(env, n)["abstract_fetched_at"] for n in range(3))
    assert fetched == [t.isoformat() for t in steps[:3]]                              # three different times, one per paper
    (e,) = events(env.db, "abstract_fetch")
    assert e["ts"] == steps[3].isoformat()                                            # the event is dated by the write


def test_progress_lines_are_flushed_by_default(fetch, monkeypatch):
    seen = []
    monkeypatch.setattr("builtins.print", lambda *a, **k: seen.append((a, k)))
    fetch.fa.flushed("a line")
    assert seen == [(("a line",), {"flush": True})]
    assert inspect.signature(fetch.fa.main).parameters["out"].default is fetch.fa.flushed


def test_the_dry_run_states_the_worst_case_time_from_the_lookup_budget(env, fetch):
    with_hold_list(env)
    code, out = fetch.run()
    assert code == 0 and "about 9 seconds" in out and f"at most about {3 * (3 + lookup.TOTAL_BUDGET_SECONDS + 1)} seconds" in out


def test_a_later_run_fills_only_what_is_missing(env, fetch):
    with_hold_list(env)
    canned(fetch.web)
    fetch.run("--apply", "--approval", LINE)
    fetch.web.calls.clear()
    fetch.web.table[S22] = (200, json.dumps({"title": "Held paper two", "year": 2020, "authors": [], "abstract": "Found later.", "externalIds": {"DOI": "10.9998/held.2"}}).encode())
    fetch.web.table[CR1] = (200, crossref(title="Held paper one", doi="10.9998/held.1", abstract="A DIFFERENT abstract now."))
    one_before, three_before = json.dumps(cand(env, 0), sort_keys=True), json.dumps(cand(env, 2), sort_keys=True)
    code, out = fetch.run("--apply", "--approval", LINE)
    assert code == 0 and "2 already have an abstract, 1 to look up" in out
    assert fetch.web.calls == [CR2, OA2, S22]                                                                       # the two papers that have an abstract are not asked about
    assert json.dumps(cand(env, 0), sort_keys=True) == one_before and json.dumps(cand(env, 2), sort_keys=True) == three_before
    two = cand(env, 1)
    assert (two["lookup_state"], two["abstract"], two["abstract_source"]) == ("found", "Found later.", "s2")
    assert len(events(env.db, "abstract_fetch")) == 2
    before = snapshot(env.db)
    fetch.web.calls.clear()
    code, out = fetch.run("--apply", "--approval", LINE)
    assert code == 0 and fetch.web.calls == [] and snapshot(env.db) == before and "nothing to look up" in out


def test_registries_that_are_down_leave_the_papers_unavailable_and_a_rerun_learning_nothing_writes_nothing(env, fetch):
    with_hold_list(env)
    for url in (CR1, CR2, AX3):
        fetch.web.table[url] = (500, b"")
    fetch.web.table[OA2] = TimeoutError("slow")
    code, out = fetch.run("--apply", "--approval", LINE)
    assert code == 0 and [cand(env, n)["lookup_state"] for n in range(3)] == ["unavailable"] * 3 and all(cand(env, n)["abstract"] is None for n in range(3))
    before = snapshot(env.db)
    code, out = fetch.run("--apply", "--approval", LINE)
    assert code == 0 and snapshot(env.db) == before and "nothing new was learned" in out


def test_a_paper_that_gained_an_abstract_between_the_lookups_and_the_write_is_skipped(env, fetch):
    with_hold_list(env)
    canned(fetch.web)
    real = candidates.apply_abstracts

    def meanwhile(db, **kw):
        cand(env, 0)["abstract"] = "Written by someone else meanwhile."
        return real(db, **kw)
    env.mp.setattr(candidates, "apply_abstracts", meanwhile)
    code, out = fetch.run("--apply", "--approval", LINE)
    assert code == 0 and cand(env, 0)["abstract"] == "Written by someone else meanwhile." and cand(env, 0).get("lookup_state") is None
    assert "2 papers written" in out and "1 skipped because they changed meanwhile" in out


def test_a_failed_write_keeps_nothing_and_more_papers_than_the_limit_are_refused_not_cut(env, fetch, capsys):
    with_hold_list(env)
    canned(fetch.web)
    before = snapshot(env.db)
    env.db.fail_on_commit = True
    assert fetch.run("--apply", "--approval", LINE)[0] == 2 and snapshot(env.db) == before
    env.db.fail_on_commit = False
    fetch.web.calls.clear()
    assert fetch.run("--apply", "--approval", LINE, "--limit", "2")[0] == 1
    assert fetch.web.calls == [] and snapshot(env.db) == before and "over the limit of 2" in capsys.readouterr().err
