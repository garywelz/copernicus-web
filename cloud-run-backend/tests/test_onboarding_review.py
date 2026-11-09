"""Onboarding PR 3b-1: Gary's review of the owners' work (design 4.5, 5.1, 5.7, 6.2 to 6.4): the dashboard data, the proposed-vs-current diff, and Approve / Send back.
Offline: the in-memory Firestore with atomic transactions, a recorded mail service, a mocked clock, and a mocked HTTP layer standing in for
raw.githubusercontent.com and the GitHub commits endpoint (no test touches the network). The engine is a synthetic fixture."""
import json
import re

import pytest

from tests.test_onboarding_gates import ADV, H, IDS, OTH, PAYLOAD, SECRET, STRANGER, X, Y, YMEM, answer_quietly, final, snapshot, stored  # noqa: F401
from tests.test_onboarding_items import ADMIN, env, events, strings  # noqa: F401  (env is a fixture)
from tests.test_onboarding_workspace import section_doc, section_json, set_section
from utils import onboarding as ob
from utils import onboarding_base as base
from utils import onboarding_render as render

A = "/api/admin/onboarding"
REPO = "synthetic-org/synth-x"
SHA = "a" * 40
RAW = f"https://raw.githubusercontent.com/{REPO}/{SHA}/"
BASE_FOCUS = json.dumps({
    "project": "Synthetic project", "updated": "2026-09-19",
    "active_questions": [{"id": "ex-q1", "q": "Original question one?", "terms": ["old term"], "since": "2026-09-19"},
                         {"id": "ex-q2", "q": "Original question two?", "terms": [], "since": "2026-09-19"}],
    "frontier": [], "flagged": [], "categories": ["math.AT"], "horizons": ["old horizon"], "mute": []}, indent=2)
BASE_README = "# Synth X\n\nIntro.\n\n## Scope\n\nOld scope text.\n\n## License\n\nCC0.\n"


class Http:
    """A mocked network: url -> (status, body). Anything not listed is a connection error. Counts the calls."""

    def __init__(self):
        self.table, self.calls = {}, []

    def __call__(self, url, headers=None):
        self.calls.append((url, dict(headers or {})))
        hit = self.table.get(url)
        if hit is None:
            raise ConnectionError("no route")
        if isinstance(hit, Exception):
            raise hit
        return hit[0], hit[1] if isinstance(hit[1], bytes) else hit[1].encode()


@pytest.fixture
def http(monkeypatch):
    h = Http()
    base.clear_cache()
    monkeypatch.setattr(base, "_http_get", h)
    h.table[f"https://api.github.com/repos/{REPO}/commits/main"] = (200, json.dumps({"sha": SHA}))
    h.table[RAW + "docs/research_focus.json"] = (200, BASE_FOCUS)
    h.table[RAW + "README.md"] = (200, BASE_README)
    h.table[RAW + "docs/seed_papers.md"] = (200, "# Seeds\n\nProse.\n")
    yield h
    base.clear_cache()


def with_repo(env, repo=REPO):
    env.db.data["onboarding_engines"][X]["source"] = {"repo": repo, "commit_sha": "0" * 40}


def make_final(env, section):
    answer_quietly(env, section)
    assert final(env, ADV, section).status_code == 200, section
    return section_doc(env, section)


def get(env, path, headers=ADMIN):
    return env.client.get(A + path, headers=headers)


def decide(env, section, what, note="A note.", rev=None, sha=None, headers=ADMIN, engine=X):
    sec = env.db.data.get("onboarding_sections", {}).get(f"{engine}__{section}", {})
    body = {"note": note, "expected_revision": sec.get("revision", 1) if rev is None else rev, "expected_content_sha256": sec.get("content_sha256", "0" * 64) if sha is None else sha}
    return env.client.post(f"{A}/engines/{engine}/sections/{section}/{what}", json=body, headers=headers)


# ---- admin only, on every new route --------------------------------------------------------------------------------------------------------------------
ROUTES = [("GET", "/engines"), ("GET", f"/engines/{X}"), ("GET", f"/engines/{X}/diff?section=scope"),
          ("POST", f"/engines/{X}/sections/scope/approve"), ("POST", f"/engines/{X}/sections/scope/reject")]


def call(env, method, path, headers):
    body = {"note": "n", "expected_revision": 1, "expected_content_sha256": "0" * 64}
    return env.client.request(method, A + path, headers=headers, **({"json": body} if method == "POST" else {}))


@pytest.mark.parametrize("method,path", ROUTES)
def test_every_review_route_is_admin_only(env, http, method, path):
    make_final(env, "scope")
    before = snapshot(env.db)
    assert call(env, method, path, {}).status_code == 401                                                       # no credential at all
    assert call(env, method, path, {"X-Admin-API-Key": "wrong"}).status_code == 401                             # a wrong key and no session
    for who in (ADV, OTH, YMEM, STRANGER):                                                                      # owners, other engines' members, strangers: 404
        assert call(env, method, path, H[who]).status_code == 404, who
    assert call(env, method, path, {**H[ADV], "X-Admin-API-Key": "wrong"}).status_code == 404                  # a session with a wrong key is still not the admin
    assert call(env, method, path, {"X-Subscriber-Token": "garbage"}).status_code == 404
    assert snapshot(env.db) == before                                                                           # and nothing changed
    assert call(env, method, path, ADMIN).status_code in (200, 409)                                             # the admin gets through (409: the section's own rules)


def test_a_browser_from_another_origin_is_refused(env):
    assert env.client.get(A + "/engines", headers={**ADMIN, "Origin": "https://evil.example"}).status_code == 403
    assert env.client.get(A + "/engines", headers={**ADMIN, "Origin": ob.ALLOWED_ORIGIN}).status_code == 200


# ---- the dashboard data ----------------------------------------------------------------------------------------------------------------------------------
def test_the_dashboard_lists_every_engine_with_state_sections_age_and_who_waits(env):
    make_final(env, "scope")
    answer_quietly(env, "questions")
    set_section(env, "keywords", "approved", approved_at="2026-11-01T12:00:00+00:00", approved_revision=1)
    out = get(env, "/engines").json()["engines"]
    assert [e["engine_id"] for e in out] == [X, Y]
    x = out[0]
    rows = {r["key"]: r for r in x["sections"]}
    assert x["label"] == "Synthetic X" and x["state"] == "open" and x["awaiting_review"] == 1 and x["repo"] is None
    assert rows["scope"]["status"] == "final" and rows["scope"]["waiting_on"] == {"who": "admin", "label": "admin"} and rows["scope"]["revision"] == 1
    assert rows["questions"]["waiting_on"]["who"] == "final_say" and rows["questions"]["ready"] is True                # ready, draft: the final-say owner
    assert rows["seeds"]["waiting_on"]["who"] == "owners" and rows["seeds"]["ready"] is False
    assert rows["keywords"]["status"] == "approved" and rows["keywords"]["waiting_on"]["who"] == "none"
    assert rows["scope"]["age_seconds"] is not None and rows["scope"]["age_seconds"] >= 0 and rows["keywords"]["age_seconds"] > 86400 * 3            # age in status


def test_the_dashboard_and_detail_show_roles_never_ids_or_addresses(env):
    make_final(env, "scope")
    env.client.post(f"/api/onboarding/engines/{X}/items/use-case/comments", json={"body": "hello"}, headers=H[OTH])
    out = [get(env, "/engines").text, get(env, f"/engines/{X}").text]
    for text in out:
        assert not re.search(r"sub-[a-z0-9]+", text) and "@" not in text and "example.invalid" not in text, "no subscriber id and no address"


def test_the_engine_detail_has_item_history_and_comment_threads_read_only(env):
    make_final(env, "scope")
    env.client.post(f"/api/onboarding/engines/{X}/items/use-case/comments", json={"body": "A thread comment."}, headers=H[OTH])
    r = get(env, f"/engines/{X}")
    assert r.status_code == 200
    scope = next(d for d in r.json()["details"] if d["section"]["key"] == "scope")
    uc = next(i for i in scope["items"] if i["item_id"] == "use-case")
    assert uc["comments"][0]["body"] == "A thread comment." and uc["comments"][0]["author"] in ("owner", "advisor") and "history" in uc
    assert get(env, "/engines/nope-x").status_code == 404
    assert env.client.put(f"{A}/engines/{X}", headers=ADMIN, json={}).status_code == 405                       # read only: no write verb on the detail


# ---- the render module: the same function 3b-2 will use --------------------------------------------------------------------------------------------------
def items_of(env, section):
    return sorted((v for v in env.db.data["onboarding_items"].values() if v["engine_id"] == X and v["section"] == section), key=lambda i: i["order"])


def test_research_focus_output_parses_and_every_question_has_q_terms_since_with_priority_optional(env):
    answer_quietly(env, "questions")
    qs = items_of(env, "questions")
    qs[0]["value"], qs[0]["choice"] = {"wording": "New wording?", "centrality": "central", "terms": [{"text": "kept", "choice": "keep"}, {"text": "gone", "choice": "drop"}]}, "reword"
    qs[1]["value"], qs[1]["choice"] = {"centrality": "background", "terms": []}, "accept"
    qs[2]["choice"] = "drop"
    qs[2]["value"] = {"reason": "no", "terms": []}
    qs[0]["context"], qs[1]["context"] = {"original_wording": "Original question one?"}, {"original_wording": "Original question two?"}
    [f] = render.render_files({"questions": qs}, {"docs/research_focus.json": BASE_FOCUS}, "2026-11-09")
    doc = json.loads(f["content"])
    rows = doc["active_questions"]
    assert [r["id"] for r in rows] == ["ex-q1", "ex-q2"] and all({"q", "terms", "since"} <= set(r) for r in rows)
    assert rows[0] == {"id": "ex-q1", "q": "New wording?", "terms": ["kept"], "since": "2026-09-19", "priority": "central"}      # since kept from the matched question
    assert rows[1]["q"] == "Original question two?" and rows[1]["priority"] == "background"
    assert doc["project"] == "Synthetic project" and doc["categories"] == ["math.AT"] and doc["horizons"] == ["old horizon"]        # what the form does not own is untouched
    qs[1]["value"]["centrality"] = None
    del qs[1]["value"]["centrality"]
    [g] = render.render_files({"questions": qs[:2]}, {"docs/research_focus.json": BASE_FOCUS}, "2026-11-09")
    assert "priority" not in json.loads(g["content"])["active_questions"][1]                                      # priority is optional


def test_a_new_question_gets_the_as_of_date_and_keywords_replace_only_their_lists(env):
    answer_quietly(env, "questions")
    answer_quietly(env, "keywords")
    qs = items_of(env, "questions")
    qs[0]["item_id"], qs[0]["context"] = "ex-q9", {"added": True}
    qs[0]["value"], qs[0]["choice"] = {"wording": "Brand new?", "centrality": "central", "terms": []}, "add"
    kws = items_of(env, "keywords")
    kws[0]["value"], kws[0]["choice"] = {"list": "horizons", "text": "a horizon"}, "add"
    kws[1]["value"], kws[1]["choice"] = {"list": "frontier", "text": "typed into frontier"}, "add"
    [f] = render.render_files({"questions": qs[:1], "keywords": kws}, {"docs/research_focus.json": BASE_FOCUS}, "2026-11-09")
    doc = json.loads(f["content"])
    assert doc["active_questions"][0]["since"] == "2026-11-09" and doc["horizons"] == ["a horizon"] and doc["frontier"] == []
    assert any("frontier or flagged" in n for n in f["notes"]), "an entry the contract's object shape cannot hold is reported, not silently written"
    assert f["sections"] == ["questions", "keywords"] and f["sha256"] == render.sha256_text(f["content"])


def test_the_scope_paragraph_replaces_the_scope_section_and_the_seeds_block_is_replaced_in_place():
    items = [{"item_id": "scope-statement", "value": "What it is for."}, {"item_id": "use-case", "value": "private use"}, {"item_id": "out-of-scope", "value": ["a", "b"]}]
    [f] = render.render_files({"scope": items}, {"README.md": BASE_README}, "2026-11-09")
    assert f["content"] == "# Synth X\n\nIntro.\n\n## Scope\n\nWhat it is for.\n\nOut of scope: a; b.\n\n## License\n\nCC0.\n" and "private use" not in f["content"]
    [bare] = render.render_files({"scope": items}, {"README.md": None}, "2026-11-09")
    assert bare["content"].startswith("## Scope and use case\n\nWhat it is for.")
    seeds = [{"item_id": "seed-1", "choice": "yes", "value": {"comment": "good"}, "context": {"citation": "A. Author (2020).", "identifier": "doi:10.0/x"}}]
    [s1, _csv1] = render.render_files({"seeds": seeds}, {"docs/seed_papers.md": "# Seeds\n\nProse.\n"}, "2026-11-09")
    seeds[0]["choice"] = "no"
    [s2, _csv2] = render.render_files({"seeds": seeds}, {"docs/seed_papers.md": s1["content"]}, "2026-11-09")
    assert s1["content"].startswith("# Seeds\n\nProse.\n") and "confirmed" in s1["content"] and "not confirmed" in s2["content"] and s2["content"].count(render.SEEDS_BEGIN) == 1


# ---- the diff ---------------------------------------------------------------------------------------------------------------------------------------------
def test_the_diff_of_a_final_section_against_the_repository_with_the_base_commit(env, http):
    with_repo(env)
    make_final(env, "scope")
    stored(env, "scope-statement", "scope")["value"] = "A statement of scope."
    r = get(env, f"/engines/{X}/diff?section=scope")
    assert r.status_code == 200, r.text
    d = r.json()
    assert d["repo"] == REPO and d["no_repo"] is False and d["base"] == {"branch": "main", "commit_sha": SHA, "commit_state": "ok"} and d["section_status"] == "final"
    [f] = d["files"]
    assert f["path"] == "README.md" and f["action"] == "modify" and f["base_state"] == "ok"
    assert {"t": "-", "text": "Old scope text."} in f["lines"] and {"t": "+", "text": "A statement of scope."} in f["lines"]
    assert f["added"] >= 1 and f["removed"] == 1
    urls = [c[0] for c in http.calls]
    assert all(u.startswith(("https://raw.githubusercontent.com/", "https://api.github.com/")) for u in urls)
    assert all("authorization" not in {k.lower() for k in c[1]} for c in http.calls), "no token is ever sent"


def test_a_questions_diff_is_a_diff_of_research_focus_json_and_an_approved_section_has_one_too(env, http):
    with_repo(env)
    make_final(env, "questions")
    d = get(env, f"/engines/{X}/diff?section=questions").json()
    [f] = d["files"]
    assert f["path"] == "docs/research_focus.json" and f["action"] == "modify"
    assert json.loads(next(c for c in [render.render_files({"questions": [v for v in env.db.data["onboarding_items"].values() if v["section"] == "questions" and v["engine_id"] == X]},
                                                          {"docs/research_focus.json": BASE_FOCUS}, "x")[0]["content"]]))["active_questions"]
    assert decide(env, "questions", "approve").status_code == 200
    assert get(env, f"/engines/{X}/diff?section=questions").json()["section_status"] == "approved"


def test_an_engine_with_no_repository_is_diffed_against_empty_and_says_so(env, http):
    make_final(env, "questions")
    d = get(env, f"/engines/{X}/diff?section=questions").json()
    assert d["no_repo"] is True and d["repo"] is None and "no repository" in d["note"] and d["base"]["commit_sha"] is None
    [f] = d["files"]
    assert f["action"] == "add" and f["base_state"] == "none" and f["removed"] == 0 and all(l["t"] == "+" for l in f["lines"])
    assert http.calls == [], "nothing is fetched for an engine with no repository"
    json.loads("".join(l["text"] + "\n" for l in f["lines"]))                                                   # the proposed file parses


@pytest.mark.parametrize("fail", ["network", "500", "oversize", "garbage_commit"])
def test_a_fetch_failure_degrades_to_current_file_unavailable_never_a_500(env, http, fail):
    with_repo(env)
    make_final(env, "scope")
    if fail == "network":
        http.table[RAW + "README.md"] = ConnectionError("down")
    elif fail == "500":
        http.table[RAW + "README.md"] = (503, "busy")
    elif fail == "oversize":
        http.table[RAW + "README.md"] = (200, b"x" * (base.MAX_BYTES + 1))
    else:
        http.table[f"https://api.github.com/repos/{REPO}/commits/main"] = (200, "not json")
        http.table[f"https://raw.githubusercontent.com/{REPO}/main/README.md"] = (503, "busy")
    r = get(env, f"/engines/{X}/diff?section=scope")
    assert r.status_code == 200
    [f] = r.json()["files"]
    assert f["base_state"] == "unavailable" and f["action"] == "unknown" and f["lines"], "the proposed file is still shown"
    if fail == "garbage_commit":
        assert r.json()["base"]["commit_state"] == "unavailable" and r.json()["base"]["commit_sha"] is None


def test_a_file_the_repository_does_not_have_is_an_add_and_a_lost_commit_lookup_falls_back_to_main(env, http):
    with_repo(env)
    make_final(env, "seeds")
    del http.table[RAW + "docs/seed_papers.md"]
    http.table[RAW + "docs/seed_papers.md"] = (404, "Not Found")
    [f, csv_file] = get(env, f"/engines/{X}/diff?section=seeds").json()["files"]
    assert f["base_state"] == "missing" and f["action"] == "add" and csv_file["path"] == "docs/seeds.csv"
    base.clear_cache()
    http.table[f"https://api.github.com/repos/{REPO}/commits/main"] = (404, "{}")
    http.table[f"https://raw.githubusercontent.com/{REPO}/main/docs/seed_papers.md"] = (200, "# Seeds\n")
    d = get(env, f"/engines/{X}/diff?section=seeds").json()
    assert d["base"]["commit_state"] == "unavailable" and d["files"][0]["base_state"] == "ok" and "main" in d["note"]


def test_the_fetched_base_is_cached_briefly_and_a_failure_is_not(env, http):
    with_repo(env)
    make_final(env, "scope")
    get(env, f"/engines/{X}/diff?section=scope")
    n = len(http.calls)
    get(env, f"/engines/{X}/diff?section=scope")
    assert len(http.calls) == n, "a second look within the cache window fetches nothing"
    base.clear_cache()
    http.table[RAW + "README.md"] = (503, "busy")
    get(env, f"/engines/{X}/diff?section=scope")
    http.table[RAW + "README.md"] = (200, BASE_README)
    assert get(env, f"/engines/{X}/diff?section=scope").json()["files"][0]["base_state"] == "ok"


@pytest.mark.parametrize("repo", ["../etc/passwd", "a/b/c", "has space/x", "x", "o/..", "a\\b/c", "http://evil/x", ""])
def test_a_repository_name_that_is_not_a_plain_owner_slash_name_is_never_fetched(env, http, repo):
    env.db.data["onboarding_engines"][X]["source"] = {"repo": repo}
    make_final(env, "scope")
    d = get(env, f"/engines/{X}/diff?section=scope").json()
    assert d["no_repo"] is True and http.calls == []


def test_only_a_final_or_approved_section_has_a_diff_and_unknown_things_are_404(env, http):
    with_repo(env)
    assert get(env, f"/engines/{X}/diff?section=scope").status_code == 409                                      # a draft
    assert get(env, f"/engines/{X}/diff?section=nope").status_code == 404
    assert get(env, "/engines/nope-q/diff?section=scope").status_code == 404
    assert get(env, f"/engines/{X}/diff").status_code == 422


# ---- approve and send back ------------------------------------------------------------------------------------------------------------------------------
def test_approve_records_the_exact_revision_and_hash_audits_it_and_freezes_the_section(env):
    sec = make_final(env, "scope")
    r = decide(env, "scope", "approve", note="Looks right.")
    assert r.status_code == 200 and r.json()["status"] == "approved" and r.json()["revision"] == 1
    s = section_doc(env, "scope")
    assert s["status"] == "approved" and s["approved_revision"] == 1 and s["approved_content_sha256"] == sec["content_sha256"] and s["approver_note"] == "Looks right."
    [e] = events(env.db, "approve")
    assert e["engine_id"] == X and e["actor_role"] == "admin" and e["revision"] == 1 and e["content_sha256"] == sec["content_sha256"] and e["note_sha256"] and "Looks right." not in json.dumps(e)
    # frozen: a later owner edit starts a NEW draft revision, and the approved one stays in the history (as 3a built)
    assert env.client.put(f"/api/onboarding/engines/{X}/items/use-case", json={"value": "changed", "choice": None, "base_revision": 1}, headers=H[OTH]).status_code == 200
    s = section_doc(env, "scope")
    assert s["status"] == "draft" and s["revision"] == 2 and s["approved_history"][-1]["revision"] == 1


def test_approve_note_is_optional_and_capped_plain_text(env):
    make_final(env, "scope")
    assert decide(env, "scope", "approve", note=None).status_code == 200
    assert section_doc(env, "scope")["approver_note"] is None
    make_final(env, "questions")
    assert decide(env, "questions", "approve", note="x" * 1001).status_code == 400
    assert section_doc(env, "questions")["status"] == "final"
    assert decide(env, "questions", "approve", note="x" * 1000).status_code == 200


@pytest.mark.parametrize("status", ["draft", "approved", "rejected"])
def test_only_a_final_section_can_be_approved_or_sent_back(env, status):
    if status != "draft":
        answer_quietly(env, "scope")
        set_section(env, "scope", status, content_sha256="0" * 64)
    before = snapshot(env.db)
    for what in ("approve", "reject"):
        r = decide(env, "scope", what, rev=1, sha="0" * 64)
        assert r.status_code == 409 and r.json()["detail"]["reason"] == "not_final"
    assert snapshot(env.db) == before and events(env.db, "approve") == [] and events(env.db, "reject") == []


def test_a_section_that_changed_since_the_dashboard_loaded_is_refused_with_409_and_nothing_changes(env):
    sec = make_final(env, "scope")
    before = snapshot(env.db)
    for what in ("approve", "reject"):
        assert decide(env, "scope", what, rev=sec["revision"] + 1).status_code == 409                     # the revision moved on
        assert decide(env, "scope", what, sha="f" * 64).status_code == 409                                 # the content moved on (same revision number)
    assert snapshot(env.db) == before
    # final -> draft (an owner edit) -> final again keeps the revision number but changes the content: the old hash is refused
    old_sha = sec["content_sha256"]
    env.client.put(f"/api/onboarding/engines/{X}/items/use-case", json={"value": "different", "choice": None, "base_revision": 1}, headers=H[OTH])
    assert final(env, ADV, "scope").status_code == 200
    assert section_doc(env, "scope")["revision"] == sec["revision"]
    r = decide(env, "scope", "approve", sha=old_sha)
    assert r.status_code == 409 and section_doc(env, "scope")["status"] == "final"
    assert decide(env, "scope", "approve").status_code == 200


def test_the_request_must_carry_the_expected_revision_and_hash(env):
    make_final(env, "scope")
    for body in ({"note": "x"}, {"note": "x", "expected_revision": 1}, {"note": "x", "expected_revision": "1", "expected_content_sha256": "0" * 64},
                 {"note": "x", "expected_revision": 1, "expected_content_sha256": "short"}):
        assert env.client.post(f"{A}/engines/{X}/sections/scope/approve", json=body, headers=ADMIN).status_code == 422
    assert section_doc(env, "scope")["status"] == "final"


def test_send_back_returns_the_section_to_draft_with_the_note_visible_to_owners_until_the_next_final(env):
    sec = make_final(env, "scope")
    r = decide(env, "scope", "reject", note="Please narrow the scope.")
    assert r.status_code == 200 and r.json()["status"] == "draft"
    s = section_doc(env, "scope")
    assert s["status"] == "draft" and s["rejection_note"] == "Please narrow the scope." and s["final_by"] is None and s["final_at"] is None and s["rejected_at"]
    for who in (ADV, OTH):                                                                                   # the owners see it on the section and on the engine page
        assert section_json(env, who, "scope")["section"]["rejection_note"] == "Please narrow the scope."
        row = next(r for r in env.client.get(f"/api/onboarding/engines/{X}", headers=H[who]).json()["progress"]["sections"] if r["key"] == "scope")
        assert row["rejection_note"] == "Please narrow the scope." and row["status"] == "draft"
    # an owner edit keeps the note (it is cleared only when the section is next marked final)
    env.client.put(f"/api/onboarding/engines/{X}/items/use-case", json={"value": "narrower", "choice": None, "base_revision": 1}, headers=H[OTH])
    assert section_json(env, OTH, "scope")["section"]["rejection_note"] == "Please narrow the scope."
    assert final(env, ADV, "scope").status_code == 200
    assert section_json(env, OTH, "scope")["section"]["rejection_note"] is None and section_doc(env, "scope")["rejection_note"] is None
    assert get(env, "/engines").json()["engines"][0]["sections"][0]["rejection_note"] is None
    assert section_doc(env, "scope")["revision"] == sec["revision"]


def test_a_note_is_required_to_send_back(env):
    make_final(env, "scope")
    for note in (None, "", "   "):
        assert decide(env, "scope", "reject", note=note).status_code == 400
    assert section_doc(env, "scope")["status"] == "final"


def test_a_section_sent_back_is_not_sent_a_ready_mail_again_and_reads_as_draft_everywhere(env):
    make_final(env, "scope")
    env.mail.sent.clear()
    decide(env, "scope", "reject", note="No.")
    kinds = [m["kind"] for m in env.mail.sent]
    assert kinds == ["sent_back"] * 2, kinds          # one to each owner, and no "ready" mail
    env.client.post(f"/api/onboarding/engines/{X}/items/use-case/comments", json={"body": "ok"}, headers=H[OTH])
    assert [m["kind"] for m in env.mail.sent] == ["sent_back"] * 2
    assert section_json(env, ADV, "scope")["section"]["status"] == "draft"


def test_both_decisions_are_audited_in_the_same_transaction(env):
    make_final(env, "scope")
    make_final(env, "questions")
    before = snapshot(env.db)
    env.db.fail_writes_to = {ob.EVENTS}                                                                       # the audit write fails: the change must not happen
    for sec, what in (("scope", "approve"), ("questions", "reject")):
        with pytest.raises(RuntimeError):
            decide(env, sec, what)
    env.db.fail_writes_to = set()
    assert snapshot(env.db) == before
    env.db.fail_after_ops = 2                                                                                 # a failure partway through: all or nothing
    with pytest.raises(RuntimeError):
        decide(env, "scope", "approve")
    env.db.fail_after_ops = None
    assert snapshot(env.db) == before
    assert decide(env, "scope", "approve").status_code == 200 and decide(env, "questions", "reject", note="n").status_code == 200
    assert [e["action"] for e in events(env.db) if e["action"] in ("approve", "reject")] == ["approve", "reject"]


def test_the_decision_mail_names_the_section_and_engine_and_never_carries_the_note(env):
    make_final(env, "scope")
    make_final(env, "questions")
    env.mail.sent.clear()
    NOTE = "UNIQUE-NOTE-TEXT-7731"
    assert decide(env, "scope", "approve", note=NOTE).status_code == 200
    assert decide(env, "questions", "reject", note=NOTE).status_code == 200
    assert [(m["kind"], m["section"], m["engine"]) for m in env.mail.sent] == [("approved", "Scope and use case", "Synthetic X")] * 2 + [("sent_back", "Research questions", "Synthetic X")] * 2
    assert all(NOTE not in json.dumps(m) and m["link"].endswith(f"engine.html?engine={X}") for m in env.mail.sent)
    assert sorted(m["to"] for m in env.mail.sent) == sorted([f"{ADV}@example.invalid", f"{OTH}@example.invalid"] * 2)                  # every active owner, not only the final-say holder


def test_every_active_owner_is_told_each_respecting_their_own_switch_and_a_stranger_never(env):
    make_final(env, "scope")
    env.mail.sent.clear()
    decide(env, "scope", "approve")
    assert sorted(m["to"] for m in env.mail.sent) == sorted([f"{ADV}@example.invalid", f"{OTH}@example.invalid"])        # not eng-y's member, not a stranger
    make_final(env, "questions")
    env.mail.sent.clear()
    assert env.client.put(f"/api/onboarding/engines/{X}/notifications", json={"email": False}, headers=H[ADV]).status_code == 200
    decide(env, "questions", "reject", note="n")
    assert [m["to"] for m in env.mail.sent] == [f"{OTH}@example.invalid"]                                       # the one who opted out is not mailed; the other owner is
    make_final(env, "keywords")
    env.mail.sent.clear()
    assert env.client.put(f"/api/onboarding/engines/{X}/notifications", json={"email": False}, headers=H[OTH]).status_code == 200
    decide(env, "keywords", "approve")
    assert env.mail.sent == []                                                                                 # both opted out: the decision stands, nothing is sent
    env.db.data[ob.MEMBERS][ob.member_id(X, OTH)]["status"] = "removed"
    env.db.data[ob.MEMBERS][ob.member_id(X, ADV)]["notifications_email"] = True
    make_final(env, "seeds")
    env.mail.sent.clear()
    decide(env, "seeds", "approve")
    assert [m["to"] for m in env.mail.sent] == [f"{ADV}@example.invalid"]                                       # a removed member is not mailed


def test_a_mail_failure_never_undoes_or_fails_a_decision(env):
    make_final(env, "scope")
    env.mail.raises = True
    r = decide(env, "scope", "approve")
    assert r.status_code == 200 and r.json()["mail_sent"] == 0 and section_doc(env, "scope")["status"] == "approved"


def test_the_owners_cannot_call_the_decision_routes_even_on_their_own_section(env):
    make_final(env, "scope")
    for who in (ADV, OTH, STRANGER):
        for what in ("approve", "reject"):
            assert decide(env, "scope", what, headers=H[who]).status_code == 404
    assert section_doc(env, "scope")["status"] == "final"


def test_the_approved_status_and_note_are_read_only_to_the_owners(env):
    make_final(env, "scope")
    decide(env, "scope", "approve", note="Fine.")
    sec = section_json(env, OTH, "scope")["section"]
    assert sec["status"] == "approved" and sec["approver_note"] == "Fine." and sec["approved_revision"] == 1
    assert env.client.post(f"/api/onboarding/engines/{X}/sections/scope/final", headers=H[ADV]).status_code == 409        # already approved: the owner path is unchanged


def test_nothing_in_the_review_responses_or_logs_holds_a_token_or_an_address(env, http, caplog):
    with_repo(env)
    make_final(env, "scope")
    texts = [get(env, "/engines").text, get(env, f"/engines/{X}").text, get(env, f"/engines/{X}/diff?section=scope").text, decide(env, "scope", "approve").text]
    for t in texts + [r.getMessage() for r in caplog.records]:
        assert not re.search(r"[\w.+-]+@[\w-]+\.[\w.-]+", t) and "tok-" not in t and "test-key" not in t


# ---- the pages (static checks; the review script is also RUN in Node by tests/onboarding_pages.test.js) --------------------------------------------------
from pathlib import Path  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
PUBLIC = ROOT / "public"
API = "https://copernicus-podcast-api-phzp4ie2sq-uc.a.run.app"


def text_of(path):
    return Path(path).read_text(encoding="utf-8").replace("\r\n", "\n")


def test_the_admin_page_keeps_the_invitations_panel_and_adds_the_review_panel_with_a_strict_csp_and_noindex():
    html = text_of(PUBLIC / "admin-onboarding.html")
    csp = re.search(r'http-equiv="Content-Security-Policy" content="([^"]+)"', html).group(1)
    assert 'name="robots" content="noindex, nofollow"' in html and "default-src 'none'" in csp and "script-src 'self'" in csp and f"connect-src {API}" in csp
    assert "unsafe-inline" not in html and "unsafe-eval" not in html and "<style" not in html and " style=" not in html and not re.search(r"\son\w+\s*=", html)
    assert re.findall(r'<link\b[^>]*>', html) == ['<link rel="stylesheet" href="onboarding/accept.css">', '<link rel="stylesheet" href="admin-review.css">']
    assert not re.search(r"<script[^>]*>[^<]+</script>", html) and "<iframe" not in html and not re.findall(r"""(?:src|href|action)\s*=\s*["']https?:""", html)
    for el in ("loadEngines", "engineList", "review", "diffBox", "historyBox", "decisionNote", "approve", "reject", "sendInvite", "revokeInvite", "loadList", "inviteList"):
        assert f'id="{el}"' in html, el                                                                       # the invitations panel stays; the review panel is added
    assert "Send back" in html and "not emailed" in html


def test_vercel_serves_the_review_script_and_stylesheet_with_the_same_strict_headers():
    cfg = json.loads(text_of(ROOT / "vercel.json"))
    route = next(r for r in cfg["routes"] if r.get("src") == "/admin-(?:onboarding|review)(.*)")
    for name in ("/admin-onboarding.html", "/admin-onboarding.js", "/admin-review.js", "/admin-review.css"):
        assert re.match(route["src"].replace("(.*)", "(.*)"), name), name
    assert route["headers"]["Cache-Control"] == "no-store" and route["headers"]["X-Robots-Tag"].startswith("noindex")


def test_the_review_script_renders_text_only_sends_the_admin_key_and_talks_only_to_the_api():
    js = text_of(PUBLIC / "admin-review.js")
    for token in ("innerHTML", "outerHTML", "insertAdjacentHTML", "document.write", "eval(", "new Function", "setTimeout('", "srcdoc", "javascript:", "createContextualFragment", "DOMParser",
                  "document.cookie", "sessionStorage", "window.open", "location.href", "postMessage", "WebSocket", "EventSource", "localStorage.setItem"):
        assert token not in js, token
    assert set(re.findall(r"https?://[^\s'\"`)]+", js)) <= {API} and "'X-Admin-API-Key': readKey()" in js and "textContent" in js and "createElement" in js
    assert not re.search(r"\.on[a-z]+\s*=", js) and "X-Subscriber-Token" not in js
    # every route it calls exists in the backend, with the verbs it uses
    from endpoints.onboarding import routes
    known = {(m, r.path) for r in routes.router.routes for m in getattr(r, "methods", ())}
    for verb, path in (("GET", "/api/admin/onboarding/engines"), ("GET", "/api/admin/onboarding/engines/{engine_id}"), ("GET", "/api/admin/onboarding/engines/{engine_id}/diff"),
                       ("POST", "/api/admin/onboarding/engines/{engine_id}/sections/{section_key}/approve"), ("POST", "/api/admin/onboarding/engines/{engine_id}/sections/{section_key}/reject")):
        assert (verb, path) in known, (verb, path)
    assert "/engines/' + encodeURIComponent(engine)" in js and "/sections/' + encodeURIComponent(c.section) + '/' + what" in js
    sent = re.search(r"\{ note: note, expected_revision: c\.diff\.revision, expected_content_sha256: c\.diff\.content_sha256 \}", js)
    assert sent, "a decision carries the revision and hash of the diff the reviewer was shown"
    from endpoints.onboarding.routes import DecisionIn
    assert {"note", "expected_revision", "expected_content_sha256"} == set(DecisionIn.model_fields)


def test_the_owner_pages_show_the_send_back_note_and_the_approval_as_text_only():
    html_s, js_s = text_of(PUBLIC / "onboarding" / "section.html"), text_of(PUBLIC / "onboarding" / "section.js")
    html_e, js_e = text_of(PUBLIC / "onboarding" / "engine.html"), text_of(PUBLIC / "onboarding" / "engine.js")
    for el in ("sentBack", "sentBackNote", "approval", "approvalLine", "approvalNote"):
        assert f'id="{el}"' in html_s, el
    assert 'id="sentBackBox"' in html_e and 'id="sentBackList"' in html_e
    assert "$('sentBackNote').textContent = s.rejection_note" in js_s and "$('approvalNote').textContent" in js_s and "rejection_note" in js_e
    assert "innerHTML" not in js_s + js_e
