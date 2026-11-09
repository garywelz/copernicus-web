"""Onboarding PR 3b-2: the change bundle (design 5.2 option ii, 5.3, 5.4, 6), its linter, its download and close routes, and the agent's re-verify script.
Offline: the in-memory Firestore with atomic transactions, a recorded mail service, a mocked clock, a mocked HTTP layer for the public repository, a dict for the
private bucket, and a real temporary git repository (git, no network) for the script. The engine is a synthetic fixture."""
import copy
import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path

import pytest

from tests.test_onboarding_gates import ADV, H, OTH, STRANGER, X, Y, YMEM, answer_quietly, final, snapshot, stored  # noqa: F401
from tests.test_onboarding_items import ADMIN, env, events  # noqa: F401  (env is a fixture)
from tests.test_onboarding_review import BASE_FOCUS, BASE_README, RAW, REPO, SHA, decide, get, http, make_final, with_repo  # noqa: F401  (http is a fixture)
from tests.test_onboarding_workspace import section_doc, set_section
from utils import onboarding as ob
from utils import onboarding_base as base
from utils import onboarding_bundle as bundles
from utils import onboarding_lint as lint
from utils import onboarding_render as render

A = "/api/admin/onboarding"
ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts" / "onboarding" / "verify_bundle.py"
TDAP_CSV = ('doi,question_ids,title,arxiv_id,admit_policy,status\n'
            '10.1007/s00454-011-9344-x,tdap-q1,"Persistent Cohomology and Circular Coordinates",,all_references,confirmed\n'
            '10.4230/lipics.socg.2023.57,tdap-q1,"Toroidal Coordinates: Decorrelating Circular Coordinates With Lattice Reduction",2212.07201,all_references,proposed\n')


@pytest.fixture
def bucket(monkeypatch):
    store = {}
    monkeypatch.setattr(bundles, "_store_put", lambda path, data: store.__setitem__(path, data))
    monkeypatch.setattr(bundles, "_store_get", lambda path: store.get(path))
    return store


@pytest.fixture(autouse=True)
def _repo_without_a_seed_csv(request):
    """The synthetic repository has no docs/seeds.csv (GitHub answers 404 for it)."""
    if "http" in request.fixturenames:
        request.getfixturevalue("http").table[RAW + "docs/seeds.csv"] = (404, "Not Found")


def approve(env, section):
    make_final(env, section)
    assert decide(env, section, "approve").status_code == 200


def make(env, sections=None, headers=ADMIN, engine=X):
    return env.client.post(f"{A}/engines/{engine}/bundles", json={} if sections is None else {"sections": sections}, headers=headers)


def clean_env(env, http, bucket, sections=("scope", "questions")):
    with_repo(env)
    for s in sections:
        approve(env, s)
    return env


# ---- the format, as built ---------------------------------------------------------------------------------------------------------------------------
def test_git_blob_sha_is_what_git_gives():
    assert base.git_blob_sha(b"hello\n") == "ce013625030ba8dba906f756967f9e9ca394464a"          # `echo hello | git hash-object --stdin`
    assert base.git_blob_sha(b"") == "e69de29bb2d1d6434b8b29ae775ad8c2e48c5391"
    assert base.git_blob_sha("héllo\n".encode()) == subprocess.run(["git", "hash-object", "--stdin"], input="héllo\n".encode(), capture_output=True).stdout.decode().strip()


def test_a_bundle_has_the_design_5_3_shape_and_is_stored_privately_with_a_record(env, http, bucket):
    clean_env(env, http, bucket)
    r = make(env)
    assert r.status_code == 200, r.text
    out = r.json()
    assert out["status"] == "created" and out["sections"] == ["scope", "questions"] and out["checks"]["public_safe"] is True and out["problems"] == {}
    [(path, data)] = list(bucket.items())
    assert path == f"onboarding/bundles/{X}/{out['bundle_id']}.json" and hashlib.sha256(data).hexdigest() == out["bundle_sha256"]
    b = json.loads(data)
    assert b["format"] == "engine_onboarding_bundle" and b["version"] == 1 and b["bundle_id"] == out["bundle_id"] and b["engine_id"] == X and b["created_by"] == "gary"
    assert b["base"] == {"repo": REPO, "branch": "main", "commit_sha": SHA}
    assert [s["section"] for s in b["sections"]] == ["scope", "questions"]
    s = b["sections"][0]
    assert set(s) == {"section", "revision", "content_sha256", "final_by_role", "final_at", "approved_at", "approver_note"} and s["final_by_role"] == "final_say" and s["approver_note"] == "A note."
    assert s["content_sha256"] == section_doc(env, "scope")["approved_content_sha256"]
    by = {f["path"]: f for f in b["files"]}
    assert set(by) == {"README.md", "docs/research_focus.json"}
    for f in b["files"]:
        assert set(f) == {"path", "action", "base_blob_sha", "proposed_sha256", "proposed_content"} and f["action"] == "modify"
        assert f["proposed_sha256"] == hashlib.sha256(f["proposed_content"].encode()).hexdigest()
    assert by["README.md"]["base_blob_sha"] == base.git_blob_sha(BASE_README.encode()) and by["docs/research_focus.json"]["base_blob_sha"] == base.git_blob_sha(BASE_FOCUS.encode())
    assert set(b["checks"]) == {"public_safe", "no_email", "no_not_yet_public", "names_ok", "schema_ok"} and all(b["checks"].values())
    assert set(b["pr_text"]) == {"title", "body"} and "Synthetic X" in b["pr_text"]["title"]
    assert isinstance(b["core_tasks"], list) and b["notes"] == []
    rec = env.db.data[bundles.BUNDLES][out["bundle_id"]]
    assert rec["status"] == "created" and rec["base_commit_sha"] == SHA and rec["object_path"] == path and rec["pr_url"] is None
    [e] = events(env.db, "bundle_create")
    assert e["bundle_id"] == out["bundle_id"] and e["sections"] == ["scope", "questions"] and e["actor_role"] == "admin"
    assert out["preview"] and all(p["lines"] for p in out["preview"])                                 # the response carries the diff for the dashboard


def test_a_bundle_holds_no_id_address_or_token(env, http, bucket):
    clean_env(env, http, bucket)
    out = make(env).json()
    text = bucket[bundles.object_path(X, out["bundle_id"])].decode()
    assert not re.search(r"sub-[a-z0-9]+|tok-|test-key", text) and not lint.EMAIL_RE.search(text)


def test_an_engine_with_no_repository_gets_a_bundle_of_adds(env, http, bucket):
    approve(env, "questions")
    b = json.loads(bucket[bundles.object_path(X, make(env).json()["bundle_id"])])
    assert b["base"] == {"repo": None, "branch": "main", "commit_sha": None} and http.calls == []
    assert b["files"] and all(f["action"] == "add" and f["base_blob_sha"] is None for f in b["files"])


# ---- approved revisions only --------------------------------------------------------------------------------------------------------------------------
def test_a_bundle_is_built_from_approved_sections_only(env, http, bucket):
    with_repo(env)
    approve(env, "scope")
    make_final(env, "questions")                                                                   # final, NOT approved
    out = make(env).json()
    b = json.loads(bucket[bundles.object_path(X, out["bundle_id"])])
    assert out["sections"] == ["scope"] and [s["section"] for s in b["sections"]] == ["scope"] and [f["path"] for f in b["files"]] == ["README.md"]
    assert "ex-q1" not in json.dumps(b)
    for asked in (["questions"], ["scope", "questions"], ["keywords"]):                            # naming a section that is not approved is refused
        r = make(env, asked)
        assert r.status_code == 409 and "questions" in json.dumps(r.json()) or r.json()["detail"]["not_approved"]
    assert len(env.db.data[bundles.BUNDLES]) == 1


def test_nothing_approved_is_refused_and_a_bad_section_name_is_400(env, http, bucket):
    make_final(env, "scope")
    assert make(env).status_code == 409 and make(env, ["nope"]).status_code == 400 and make(env, []).status_code == 400 and make(env, ["scope", "scope"]).status_code == 400
    assert bucket == {} and bundles.BUNDLES not in env.db.data


def test_an_approved_section_edited_after_approval_is_not_bundled(env, http, bucket):
    with_repo(env)
    approve(env, "scope")
    stored(env, "use-case", "scope")["value"] = "changed behind the gate"                       # a stored change that did not go through the reopening route
    r = make(env)
    assert r.status_code == 409 and r.json()["detail"]["changed"] == ["scope"] and bucket == {}


def test_core_tasks_follow_the_approved_seeds_and_the_added_and_retired_questions(env, http, bucket):
    with_repo(env)
    answer_quietly(env, "questions")
    qs = [v for v in env.db.data["onboarding_items"].values() if v["engine_id"] == X and v["section"] == "questions"]
    qs.sort(key=lambda i: i["order"])
    qs[0]["choice"], qs[0]["value"] = "drop", {"reason": "no", "terms": []}
    qs[2]["choice"], qs[2]["value"] = "add", {"wording": "New?", "centrality": "central", "terms": []}
    qs[2]["item_id"] = "ex-q9"
    assert final(env, ADV, "questions").status_code == 200 and decide(env, "questions", "approve").status_code == 200
    answer_quietly(env, "seeds")
    sd = [v for v in env.db.data["onboarding_items"].values() if v["engine_id"] == X and v["section"] == "seeds"]
    sd.sort(key=lambda i: i["order"])
    sd[0]["choice"], sd[1]["choice"] = "yes", "no"
    assert final(env, ADV, "seeds").status_code == 200 and decide(env, "seeds", "approve").status_code == 200
    b = json.loads(bucket[bundles.object_path(X, make(env).json()["bundle_id"])])
    kinds = sorted(t["kind"] for t in b["core_tasks"])
    assert kinds == ["ingest_seed", "retag"]
    assert next(t for t in b["core_tasks"] if t["kind"] == "retag")["payload"] == {"added": ["ex-q9"], "retired": ["ex-q1"]}
    assert next(t for t in b["core_tasks"] if t["kind"] == "ingest_seed")["payload"]["identifier"] == "doi:10.0/x"


# ---- the seed files of the real tdap repo ---------------------------------------------------------------------------------------------------------------
def test_seeds_csv_keeps_the_real_repos_header_quoting_and_untouched_rows_and_sets_status():
    items = [{"item_id": "s1", "choice": "yes", "context": {"identifier": "doi:10.1007/S00454-011-9344-X", "citation": "x"}, "value": {}},
             {"item_id": "s2", "choice": "unsure", "context": {"identifier": "arxiv:2212.07201"}, "value": {}},
             {"item_id": "s3", "choice": "no", "context": {"identifier": "doi:10.9/new", "citation": "A new paper, with comma", "question_ids": ["tdap-q2"]}, "value": {}},
             {"item_id": "s4", "choice": None, "context": {"identifier": "doi:10.9/unanswered"}, "value": {}}]
    text, notes = render.render_seeds_csv(TDAP_CSV, items)
    lines = text.split("\n")
    assert lines[0] == "doi,question_ids,title,arxiv_id,admit_policy,status" and notes == []
    assert lines[1] == '10.1007/s00454-011-9344-x,tdap-q1,"Persistent Cohomology and Circular Coordinates",,all_references,confirmed'
    assert lines[2].endswith(",2212.07201,all_references,proposed")                                  # unsure = proposed
    assert lines[3] == '10.9/new,tdap-q2,"A new paper, with comma",,,rejected' and len(lines) == 5 and "unanswered" not in text
    assert lint.check_schema([{"path": "docs/seeds.csv", "content": text}]) == []
    fresh, _ = render.render_seeds_csv(None, items[:1])
    assert fresh.split("\n")[0] == ",".join(render.CSV_COLUMNS)


def test_the_seed_files_the_renderer_writes_are_exactly_the_real_repos_and_the_design_name_is_superseded():
    assert render.SECTION_FILES["seeds"] == ("docs/seed_papers.md", "docs/seeds.csv") and render.CSV_COLUMNS == ["doi", "question_ids", "title", "arxiv_id", "admit_policy", "status"]
    assert "seed_papers.csv" not in (ROOT / "docs" / "design" / "ENGINE_ONBOARDING_FORM.md").read_text(encoding="utf-8").replace("supersedes the earlier `seed_papers.csv`", "")


def test_the_attribution_line_follows_each_owners_consent_choice():
    owners = [{"naming": "role", "role": "advisor", "name": "Alice Example"}, {"naming": "name_and_role", "role": "owner", "name": "Bob Sample"}, {"naming": "none", "role": "owner", "name": "Cy"}]
    assert render.attribution_text(owners) == "Research owners, as they chose to be named: advisor; Bob Sample (owner)."
    assert render.attribution_text([{"naming": "name", "role": "owner", "name": "Bob Sample"}]).endswith("Bob Sample.")
    assert render.attribution_text([{"naming": "none", "role": "owner", "name": "x"}]) == ""
    [f] = render.render_files({}, {"README.md": "# R\n"}, "2026-11-09", attribution=owners)
    assert f["content"].startswith("# R\n\n" + render.ATTR_BEGIN) and "Alice" not in f["content"]
    [g] = render.render_files({}, {"README.md": f["content"]}, "2026-11-09", attribution=owners)
    assert g["content"] == f["content"], "re-rendering replaces the block, it does not add a second"


# ---- the linter: each check separately, shown able to fail ----------------------------------------------------------------------------------------------
def planted(env, text):
    env.db.data["onboarding_items"][f"{X}__scope__scope-statement"]["value"] = text


def test_no_email_fails_on_a_planted_address_and_passes_on_clean_content(env, http, bucket):
    with_repo(env)
    answer_quietly(env, "scope")
    planted(env, "Write to someone@example.invalid for details")
    assert final(env, ADV, "scope").status_code == 200 and decide(env, "scope", "approve").status_code == 200
    out = make(env).json()
    assert out["status"] == "blocked" and out["checks"]["no_email"] is False and out["checks"]["public_safe"] is False
    assert [k for k, v in out["checks"].items() if not v] == ["no_email", "public_safe"] or out["problems"].keys() == {"no_email"}
    assert "someone@" not in json.dumps(out["problems"]), "the reason names the file, never the text"
    assert out["problems"] == {"no_email": ["README.md: an email-shaped string"]}


def test_no_not_yet_public_fails_on_a_flagged_item(env, http, bucket):
    with_repo(env)
    answer_quietly(env, "seeds")
    stored(env, "seed-1", "seeds")["not_yet_public"] = True
    assert final(env, ADV, "seeds").status_code == 200 and decide(env, "seeds", "approve").status_code == 200
    out = make(env).json()
    assert out["status"] == "blocked" and out["checks"]["no_not_yet_public"] is False and out["checks"]["no_email"] is True
    assert out["problems"] == {"no_not_yet_public": ["item seed-1 is marked not yet public"]}
    assert lint.check_no_not_yet_public([{"item_id": "e", "value": {"not_yet_public": True}}]) and lint.check_no_not_yet_public([{"item_id": "e", "value": {"not_yet_public": False}}, {"item_id": "f"}]) == []


def test_names_ok_blocks_a_name_beyond_the_consent_choice_and_allows_it_when_chosen(env, http, bucket):
    with_repo(env)
    env.db.data["subscribers"][ADV]["name"] = "Alice Example"
    answer_quietly(env, "scope")
    planted(env, "Led by Alice Example at the lab")
    assert final(env, ADV, "scope").status_code == 200 and decide(env, "scope", "approve").status_code == 200
    out = make(env).json()
    assert out["status"] == "blocked" and out["checks"]["names_ok"] is False and out["problems"] == {"names_ok": ["README.md: names an owner who chose not to be named"]}
    planted(env, "Led by alice at the lab")                                                          # a first name alone is caught too, in any case
    set_section(env, "scope", "draft")
    assert final(env, ADV, "scope").status_code == 200 and decide(env, "scope", "approve").status_code == 200
    assert make(env).json()["checks"]["names_ok"] is False
    env.db.data[ob.MEMBERS][ob.member_id(X, ADV)]["consent"]["naming"] = "name_and_role"           # now the owner chose to be named
    out = make(env).json()
    assert out["checks"]["names_ok"] is True and out["status"] == "created"
    readme = next(f for f in json.loads(bucket[bundles.object_path(X, out["bundle_id"])])["files"] if f["path"] == "README.md")["proposed_content"]
    assert "Alice Example (advisor)" in readme                                                       # and the attribution line follows the choice


def test_the_default_consent_names_nobody_in_the_attribution_line(env, http, bucket):
    with_repo(env)
    env.db.data["subscribers"][ADV]["name"] = "Alice Example"
    env.db.data["subscribers"][OTH]["name"] = "Bob Sample"
    approve(env, "scope")
    out = make(env).json()
    readme = next(f for f in json.loads(bucket[bundles.object_path(X, out["bundle_id"])])["files"] if f["path"] == "README.md")["proposed_content"]
    assert out["status"] == "created" and "advisor; owner" in readme and "Alice" not in readme and "Bob" not in readme


def test_schema_ok_fails_on_a_broken_research_focus_and_passes_on_a_good_one(env, http, bucket, monkeypatch):
    with_repo(env)
    approve(env, "questions")
    good = make(env).json()
    assert good["checks"]["schema_ok"] is True and good["status"] == "created"
    monkeypatch.setattr(render, "render_research_focus", lambda *a, **k: ('{"active_questions": [{"q": "x", "terms": []}]', []))        # broken JSON
    out = make(env).json()
    assert out["status"] == "blocked" and out["checks"]["schema_ok"] is False and out["problems"]["schema_ok"][0].startswith("docs/research_focus.json: does not parse")
    monkeypatch.setattr(render, "render_research_focus", lambda *a, **k: (json.dumps({"active_questions": [{"q": "x", "terms": []}]}), []))     # no since
    assert make(env).json()["problems"]["schema_ok"] == ["docs/research_focus.json: question 0 lacks since"]


@pytest.mark.parametrize("doc,fragment", [
    ({"active_questions": [{"q": "x", "terms": ["a"], "since": "2026-01-01", "extra": 1}]}, "outside the contract"),
    ({"active_questions": [{"q": "x", "terms": ["a"], "since": "2026-01-01", "priority": "high"}]}, "priority"),
    ({"active_questions": [{"q": "", "terms": [], "since": "2026-01-01"}]}, "empty q"),
    ({"active_questions": [{"q": "x", "terms": "a", "since": "2026-01-01"}]}, "terms"),
    ({"active_questions": "no"}, "not a list"), ([1], "not a JSON object"), ({"active_questions": [], "horizons": [1]}, "horizons")])
def test_schema_check_refuses_each_kind_of_bad_research_focus(doc, fragment):
    problems = lint.check_schema([{"path": "docs/research_focus.json", "content": json.dumps(doc)}])
    assert problems and fragment in problems[0]


def test_schema_check_accepts_optional_id_and_priority_and_a_good_csv_and_refuses_a_bad_csv():
    ok = {"active_questions": [{"id": "ex-q1", "q": "x", "terms": ["a"], "since": "2026-01-01", "priority": "central"}, {"q": "y", "terms": [], "since": "2026-01-01"}]}
    assert lint.check_schema([{"path": "docs/research_focus.json", "content": json.dumps(ok)}]) == []
    assert lint.check_schema([{"path": "docs/seeds.csv", "content": "title,status\nx,confirmed\n"}])[0].endswith("no doi column")
    assert "has 2 fields" in lint.check_schema([{"path": "docs/seeds.csv", "content": "doi,title,status\n1,2\n"}])[0]
    assert lint.check_schema([{"path": "docs/seeds.csv", "content": ""}])[0].endswith("has no header")
    assert lint.check_schema([{"path": "docs/seeds.csv", "content": TDAP_CSV}]) == []


def test_a_good_bundle_passes_all_four_checks_separately(env, http, bucket):
    clean_env(env, http, bucket)
    c = make(env).json()["checks"]
    assert c == {"no_email": True, "no_not_yet_public": True, "names_ok": True, "schema_ok": True, "public_safe": True}


def test_frontier_and_flagged_entries_are_not_exported_and_the_bundle_says_so(env, http, bucket):
    with_repo(env)
    answer_quietly(env, "keywords")
    stored(env, "kw-1", "keywords")["value"] = {"list": "frontier", "text": "typed into frontier"}
    stored(env, "kw-2", "keywords")["value"] = {"list": "horizons", "text": "a horizon"}
    assert final(env, ADV, "keywords").status_code == 200 and decide(env, "keywords", "approve").status_code == 200
    out = make(env).json()
    b = json.loads(bucket[bundles.object_path(X, out["bundle_id"])])
    assert any("not exported in v1 (shape not yet agreed with Core)" in n for n in b["notes"]) and "typed into frontier" not in json.dumps(b["files"])
    assert json.loads(next(f for f in b["files"] if f["path"] == "docs/research_focus.json")["proposed_content"])["frontier"] == [] and out["status"] == "created"


# ---- download and the blocked rule --------------------------------------------------------------------------------------------------------------------
def test_a_blocked_bundle_cannot_be_downloaded_as_ready_and_a_clean_one_can(env, http, bucket):
    with_repo(env)
    answer_quietly(env, "scope")
    planted(env, "mail me at someone@example.invalid")
    assert final(env, ADV, "scope").status_code == 200 and decide(env, "scope", "approve").status_code == 200
    blocked = make(env).json()
    before = snapshot(env.db)
    r = env.client.get(f"{A}/engines/{X}/bundles/{blocked['bundle_id']}", headers=ADMIN)
    assert r.status_code == 409 and r.json()["detail"]["failed_checks"] == ["no_email"] and "someone@" not in r.text
    assert snapshot(env.db) == before and events(env.db, "export") == []
    planted(env, "a clean statement")                                                              # fix it, re-open, approve again, build again
    set_section(env, "scope", "draft")
    assert final(env, ADV, "scope").status_code == 200 and decide(env, "scope", "approve").status_code == 200
    good = make(env).json()
    assert good["status"] == "created"
    r = env.client.get(f"{A}/engines/{X}/bundles/{good['bundle_id']}", headers=ADMIN)
    assert r.status_code == 200 and r.headers["content-disposition"].startswith("attachment; filename=\"bundle-") and r.headers["cache-control"] == "no-store"
    assert hashlib.sha256(r.content).hexdigest() == good["bundle_sha256"] and json.loads(r.content)["bundle_id"] == good["bundle_id"]
    assert env.db.data[bundles.BUNDLES][good["bundle_id"]]["status"] == "exported" and len(events(env.db, "export")) == 1
    assert env.client.get(f"{A}/engines/{X}/bundles/{blocked['bundle_id']}", headers=ADMIN).status_code == 409


def test_a_missing_or_altered_stored_object_is_never_served(env, http, bucket):
    clean_env(env, http, bucket)
    out = make(env).json()
    path = bundles.object_path(X, out["bundle_id"])
    bucket[path] = bucket[path] + b" "
    assert env.client.get(f"{A}/engines/{X}/bundles/{out['bundle_id']}", headers=ADMIN).status_code == 500
    del bucket[path]
    assert env.client.get(f"{A}/engines/{X}/bundles/{out['bundle_id']}", headers=ADMIN).status_code == 500
    assert env.db.data[bundles.BUNDLES][out["bundle_id"]]["status"] == "created"
    for bad in ("nope", "0" * 32, "../../x"):
        assert env.client.get(f"{A}/engines/{X}/bundles/{bad}", headers=ADMIN).status_code == 404
    assert env.client.get(f"{A}/engines/{Y}/bundles/{out['bundle_id']}", headers=ADMIN).status_code == 404       # another engine's id


def test_the_list_shows_status_checks_and_the_failed_check_newest_first(env, http, bucket):
    clean_env(env, http, bucket)
    first = make(env).json()
    second = make(env, ["scope"]).json()
    rows = get(env, f"/engines/{X}/bundles").json()["bundles"]
    assert [r["bundle_id"] for r in rows] == [second["bundle_id"], first["bundle_id"]] and rows[0]["checks"]["public_safe"] is True and rows[0]["problems"] == {}


# ---- close: merged, superseded ------------------------------------------------------------------------------------------------------------------------
def merged(env, bid, url, engine=X):
    return env.client.post(f"{A}/engines/{engine}/bundles/{bid}/merged", json={"pr_url": url}, headers=ADMIN)


def test_the_merged_route_validates_the_pr_url_and_notifies_every_owner_without_content(env, http, bucket):
    clean_env(env, http, bucket)
    bid = make(env).json()["bundle_id"]
    before = snapshot(env.db)
    for bad in (f"https://github.com/other/repo/pull/1", f"http://github.com/{REPO}/pull/1", f"https://github.com/{REPO}/pull/1/", f"https://github.com/{REPO}/pull/0",
                f"https://github.com/{REPO}/pull/1?x=1", f"https://github.com/{REPO}/issues/1", f"https://github.com/{REPO}x/pull/1", f"https://evil.example/https://github.com/{REPO}/pull/1",
                f" https://github.com/{REPO}/pull/1", "javascript:alert(1)", "https://github.com/synthetic-org/synth-x/pull/abc"):
        assert merged(env, bid, bad).status_code == 400, bad
    assert snapshot(env.db) == before and events(env.db, "bundle_merged") == []
    env.mail.sent.clear()
    r = merged(env, bid, f"https://github.com/{REPO}/pull/7")
    assert r.status_code == 200 and r.json()["status"] == "merged" and r.json()["pr_url"] == f"https://github.com/{REPO}/pull/7" and r.json()["mail_sent"] == 2
    assert sorted(m["to"] for m in env.mail.sent) == sorted([f"{ADV}@example.invalid", f"{OTH}@example.invalid"]) and {m["kind"] for m in env.mail.sent} == {"bundle_merged"}
    assert all("README" not in json.dumps(m) and "ex-q" not in json.dumps(m) for m in env.mail.sent)
    [e] = events(env.db, "bundle_merged")
    assert e["bundle_id"] == bid and e["pr_url"].endswith("/pull/7")
    assert merged(env, bid, f"https://github.com/{REPO}/pull/8").status_code == 409                # a bundle closes once


def test_merge_is_refused_for_a_blocked_bundle_a_superseded_one_and_an_engine_without_a_repository(env, http, bucket):
    with_repo(env)
    answer_quietly(env, "scope")
    planted(env, "x@example.invalid")
    assert final(env, ADV, "scope").status_code == 200 and decide(env, "scope", "approve").status_code == 200
    blocked = make(env).json()["bundle_id"]
    assert merged(env, blocked, f"https://github.com/{REPO}/pull/3").status_code == 409
    env.db.data["onboarding_engines"][X]["source"] = {}
    assert merged(env, blocked, f"https://github.com/{REPO}/pull/3").status_code == 409


def test_a_bundle_whose_main_moved_can_be_superseded_and_a_new_one_created(env, http, bucket):
    clean_env(env, http, bucket)
    bid = make(env).json()["bundle_id"]
    assert env.client.post(f"{A}/engines/{X}/bundles/{bid}/supersede", headers=ADMIN).status_code == 409          # main has not moved
    base.clear_cache()
    new = "b" * 40
    http.table[f"https://api.github.com/repos/{REPO}/commits/main"] = (200, json.dumps({"sha": new}))
    http.table[f"https://raw.githubusercontent.com/{REPO}/{new}/README.md"] = (200, BASE_README)
    http.table[f"https://raw.githubusercontent.com/{REPO}/{new}/docs/research_focus.json"] = (200, BASE_FOCUS)
    r = env.client.post(f"{A}/engines/{X}/bundles/{bid}/supersede", headers=ADMIN)
    assert r.status_code == 200 and r.json()["status"] == "superseded" and len(events(env.db, "bundle_superseded")) == 1
    assert env.client.get(f"{A}/engines/{X}/bundles/{bid}", headers=ADMIN).status_code == 409
    assert merged(env, bid, f"https://github.com/{REPO}/pull/9").status_code == 409
    again = make(env).json()
    assert again["status"] == "created" and again["base_commit_sha"] == new and again["bundle_id"] != bid


def test_no_bundle_is_built_when_the_repositorys_state_cannot_be_read(env, http, bucket):
    clean_env(env, http, bucket)
    http.table[f"https://api.github.com/repos/{REPO}/commits/main"] = (503, "busy")
    assert make(env).status_code == 503
    base.clear_cache()
    http.table[f"https://api.github.com/repos/{REPO}/commits/main"] = (200, json.dumps({"sha": SHA}))
    http.table[RAW + "README.md"] = (503, "busy")
    assert make(env).status_code == 503 and bucket == {} and bundles.BUNDLES not in env.db.data


# ---- audit and atomicity -----------------------------------------------------------------------------------------------------------------------------
def test_creating_a_bundle_writes_its_record_and_its_event_in_one_transaction(env, http, bucket):
    clean_env(env, http, bucket)
    before = snapshot(env.db)
    env.db.fail_writes_to = {ob.EVENTS}
    r = make(env)
    assert r.status_code == 500 and snapshot(env.db) == before                                      # no record without its event
    env.db.fail_writes_to = set()
    assert make(env).status_code == 200


# ---- access ------------------------------------------------------------------------------------------------------------------------------------------------
def test_every_bundle_route_is_admin_only_and_owners_get_404(env, http, bucket):
    clean_env(env, http, bucket)
    bid = make(env).json()["bundle_id"]
    routes = [("GET", f"/engines/{X}/bundles"), ("POST", f"/engines/{X}/bundles"), ("GET", f"/engines/{X}/bundles/{bid}"), ("POST", f"/engines/{X}/bundles/{bid}/merged"),
              ("POST", f"/engines/{X}/bundles/{bid}/supersede")]
    before = snapshot(env.db)
    for method, path in routes:
        kw = {"json": {"pr_url": f"https://github.com/{REPO}/pull/1"}} if path.endswith("merged") else ({"json": {}} if method == "POST" else {})
        assert env.client.request(method, A + path, **kw).status_code == 401, path
        assert env.client.request(method, A + path, headers={"X-Admin-API-Key": "wrong"}, **kw).status_code == 401, path
        for who in (ADV, OTH, YMEM, STRANGER):
            assert env.client.request(method, A + path, headers=H[who], **kw).status_code == 404, (path, who)
    assert snapshot(env.db) == before


def test_owners_see_a_bundles_status_read_only_and_nothing_else(env, http, bucket):
    clean_env(env, http, bucket)
    eng = lambda who: env.client.get(f"/api/onboarding/engines/{X}", headers=H[who]).json()
    assert eng(OTH)["bundles"] == []
    bid = make(env).json()["bundle_id"]
    [v] = eng(OTH)["bundles"]
    assert v["status"] == "created" and v["sections"] == ["Scope and use case", "Research questions"]
    assert set(v) == {"status", "at", "sections"} and BASE_README not in json.dumps(v) and bid not in json.dumps(v)
    assert env.client.get(f"{A}/engines/{X}/bundles/{bid}", headers=H[OTH]).status_code == 404
    assert env.client.post(f"/api/onboarding/engines/{X}/bundles", json={}, headers=H[OTH]).status_code in (404, 405)
    env.client.get(f"{A}/engines/{X}/bundles/{bid}", headers=ADMIN)                                  # exported still reads as created
    assert eng(ADV)["bundles"][0]["status"] == "created"
    merged(env, bid, f"https://github.com/{REPO}/pull/4")
    assert eng(OTH)["bundles"][0]["status"] == "merged"
    assert env.client.get(f"/api/onboarding/engines/{Y}", headers=H[YMEM]).json()["bundles"] == []          # another engine's owner sees nothing of this one


def test_a_blocked_or_superseded_bundle_is_not_shown_to_owners(env, http, bucket):
    with_repo(env)
    answer_quietly(env, "scope")
    planted(env, "x@example.invalid")
    assert final(env, ADV, "scope").status_code == 200 and decide(env, "scope", "approve").status_code == 200
    assert make(env).json()["status"] == "blocked"
    assert env.client.get(f"/api/onboarding/engines/{X}", headers=H[OTH]).json()["bundles"] == []


# ---- the agent's re-verify script: against a real temporary git repository --------------------------------------------------------------------------
def git(repo, *args, **kw):
    return subprocess.run(["git", "-c", "user.name=T", "-c", "user.email=t@example.invalid", "-c", "commit.gpgsign=false", "-C", str(repo), *args], capture_output=True, text=True, **kw)


@pytest.fixture
def clone(tmp_path):
    repo = tmp_path / "clone"
    repo.mkdir()
    git(repo, "init", "-q", "-b", "main")
    (repo / "docs").mkdir()
    (repo / "README.md").write_text(BASE_README, encoding="utf-8", newline="")
    (repo / "docs" / "research_focus.json").write_text(BASE_FOCUS, encoding="utf-8", newline="")
    git(repo, "add", "-A")
    git(repo, "commit", "-q", "-m", "base")
    return repo


def blob(repo, path):
    return git(repo, "rev-parse", f"HEAD:{path}").stdout.strip()


def tip(repo):
    return git(repo, "rev-parse", "HEAD").stdout.strip()


def good_bundle(repo, **over):
    focus = json.dumps({"active_questions": [{"id": "ex-q1", "q": "Q one?", "terms": ["a"], "since": "2026-09-19", "priority": "central"}]}, indent=2) + "\n"
    files = [{"path": "README.md", "action": "modify", "base_blob_sha": blob(repo, "README.md"), "proposed_content": BASE_README.replace("Old scope text.", "New scope text.")},
             {"path": "docs/research_focus.json", "action": "modify", "base_blob_sha": blob(repo, "docs/research_focus.json"), "proposed_content": focus},
             {"path": "docs/seeds.csv", "action": "add", "base_blob_sha": None, "proposed_content": TDAP_CSV}]
    for f in files:
        f["proposed_sha256"] = hashlib.sha256(f["proposed_content"].encode()).hexdigest()
    b = {"format": "engine_onboarding_bundle", "version": 1, "bundle_id": "b" * 32, "engine_id": "eng-x", "base": {"repo": REPO, "branch": "main", "commit_sha": tip(repo)},
         "sections": [], "files": files, "core_tasks": [], "checks": {"public_safe": True, "no_email": True, "no_not_yet_public": True, "names_ok": True, "schema_ok": True},
         "pr_text": {"title": "t", "body": "b"}, "notes": []}
    b.update(over)
    return b


def verify(tmp_path, repo, bundle, *args):
    p = tmp_path / "bundle.json"
    p.write_text(json.dumps(bundle), encoding="utf-8")
    return subprocess.run([sys.executable, str(SCRIPT), str(p), str(repo), *args], capture_output=True, text=True)


def snap_repo(repo):
    return git(repo, "log", "--oneline").stdout, git(repo, "status", "--porcelain").stdout, sorted(str(p.relative_to(repo)) for p in repo.rglob("*") if ".git" not in p.parts)


def test_verify_passes_a_matching_bundle_and_writes_nothing_without_apply(tmp_path, clone):
    before = snap_repo(clone)
    r = verify(tmp_path, clone, good_bundle(clone))
    assert r.returncode == 0 and "VERIFIED: 3 file(s)" in r.stdout and "APPLIED" not in r.stdout
    assert snap_repo(clone) == before and (clone / "README.md").read_text(encoding="utf-8") == BASE_README


def test_verify_fails_on_a_moved_tip_and_prints_the_regenerated_diff(tmp_path, clone):
    b = good_bundle(clone)
    (clone / "docs" / "other.md").write_text("new\n")
    git(clone, "add", "-A")
    git(clone, "commit", "-q", "-m", "main moved")
    before = snap_repo(clone)
    r = verify(tmp_path, clone, b, "--apply")
    assert r.returncode == 1 and "the base moved" in r.stdout and "--- a/README.md" in r.stdout and "+New scope text." in r.stdout and "-Old scope text." in r.stdout
    assert snap_repo(clone) == before, "--apply wrote nothing"


def test_verify_fails_on_a_changed_base_blob_and_an_add_that_already_exists(tmp_path, clone):
    r = verify(tmp_path, clone, good_bundle(clone, base={"repo": REPO, "branch": "main", "commit_sha": tip(clone)}) | {"files": [dict(f, base_blob_sha="0" * 40) if f["action"] == "modify" else f for f in good_bundle(clone)["files"]]})
    assert r.returncode == 1 and "the base file changed" in r.stdout
    b = good_bundle(clone)
    b["files"][2]["path"] = "README.md"
    assert "already exists on main" in verify(tmp_path, clone, b).stdout


def test_verify_fails_on_tampered_proposed_content(tmp_path, clone):
    b = good_bundle(clone)
    b["files"][0]["proposed_content"] += "\nsneaked in\n"
    r = verify(tmp_path, clone, b, "--apply")
    assert r.returncode == 1 and "proposed_sha256 does not match" in r.stdout
    assert (clone / "README.md").read_text(encoding="utf-8") == BASE_README


def test_verify_runs_the_same_linter_on_the_proposed_content(tmp_path, clone):
    b = good_bundle(clone)
    b["files"][1]["proposed_content"] = '{"active_questions": [{"q": "x"}]}'
    b["files"][1]["proposed_sha256"] = hashlib.sha256(b["files"][1]["proposed_content"].encode()).hexdigest()
    r = verify(tmp_path, clone, b)
    assert r.returncode == 1 and "schema_ok" in r.stdout and "lacks terms" in r.stdout
    b = good_bundle(clone)
    b["files"][0]["proposed_content"] += "mail me: someone@example.invalid\n"
    b["files"][0]["proposed_sha256"] = hashlib.sha256(b["files"][0]["proposed_content"].encode()).hexdigest()
    assert "no_email" in verify(tmp_path, clone, b).stdout
    b = good_bundle(clone)
    assert verify(tmp_path, clone, b, "--deny-name", "scope text").returncode == 1                  # a name the agent knows must not appear
    assert verify(tmp_path, clone, good_bundle(clone, checks={"public_safe": False, "no_email": False, "no_not_yet_public": True, "names_ok": True, "schema_ok": True})).returncode == 1


def test_verify_refuses_unsafe_paths_and_unreadable_input(tmp_path, clone):
    for bad in ("../outside.txt", "/etc/x", ".git/config", "a//b", "docs/../../x"):
        b = good_bundle(clone)
        b["files"][2]["path"] = bad
        r = verify(tmp_path, clone, b, "--apply")
        assert r.returncode == 1 and "nothing else was checked" in r.stdout, bad
    assert not (tmp_path / "outside.txt").exists()
    (tmp_path / "junk.json").write_text("{not json")
    assert subprocess.run([sys.executable, str(SCRIPT), str(tmp_path / "junk.json"), str(clone)], capture_output=True, text=True).returncode == 2
    assert verify(tmp_path, tmp_path / "not-a-clone", good_bundle(clone)).returncode == 2
    assert subprocess.run([sys.executable, str(SCRIPT)], capture_output=True, text=True).returncode == 2


def test_apply_writes_the_files_into_the_working_tree_and_makes_no_commit(tmp_path, clone):
    log_before = git(clone, "log", "--oneline").stdout
    r = verify(tmp_path, clone, good_bundle(clone), "--apply")
    assert r.returncode == 0 and "APPLIED" in r.stdout and "no commit" in r.stdout
    assert "New scope text." in (clone / "README.md").read_text(encoding="utf-8") and (clone / "docs" / "seeds.csv").read_text(encoding="utf-8") == TDAP_CSV
    assert git(clone, "log", "--oneline").stdout == log_before and tip(clone) == good_bundle(clone)["base"]["commit_sha"]
    status = git(clone, "status", "--porcelain").stdout
    assert " M README.md" in status and " M docs/research_focus.json" in status and "?? docs/seeds.csv" in status          # in the tree, uncommitted
    assert git(clone, "branch", "--list").stdout.split() == ["*", "main"] and git(clone, "stash", "list").stdout == ""
    r = verify(tmp_path, clone, good_bundle(clone), "--apply")                                                             # a dirty file is refused, nothing more is written
    assert r.returncode == 1 and "REFUSED" in r.stdout or "base file" in r.stdout


def test_a_bundle_from_the_server_verifies_against_a_real_clone_blob_for_blob(env, http, bucket, tmp_path, clone):
    """End to end: the repository the server read is a real git repository, so base_blob_sha is proved to be git's own."""
    sha = tip(clone)
    base.clear_cache()
    http.table.clear()
    http.table[f"https://api.github.com/repos/{REPO}/commits/main"] = (200, json.dumps({"sha": sha}))
    for p in ("README.md", "docs/research_focus.json"):
        http.table[f"https://raw.githubusercontent.com/{REPO}/{sha}/{p}"] = (200, (clone / p).read_bytes())
    with_repo(env)
    approve(env, "scope")
    approve(env, "questions")
    out = make(env).json()
    assert out["status"] == "created", out
    data = env.client.get(f"{A}/engines/{X}/bundles/{out['bundle_id']}", headers=ADMIN).content
    r = verify(tmp_path, clone, json.loads(data), "--apply")
    assert r.returncode == 0, r.stdout
    assert json.loads((clone / "docs" / "research_focus.json").read_text(encoding="utf-8"))["active_questions"][0]["id"] == "ex-q1"
    assert git(clone, "log", "--oneline").stdout.count("\n") == 1


# ---- the pages ---------------------------------------------------------------------------------------------------------------------------------------
def text_of(path):
    return Path(path).read_text(encoding="utf-8").replace("\r\n", "\n")


def test_the_dashboard_has_a_bundle_panel_that_renders_text_only_and_uses_only_real_routes():
    html, js = text_of(ROOT / "public" / "admin-onboarding.html"), text_of(ROOT / "public" / "admin-review.js")
    for el in ("bundleBox", "bundleSections", "createBundle", "bundleList", "bundleChecks", "bundleMsg"):
        assert f'id="{el}"' in html, el
    assert "innerHTML" not in js and "insertAdjacentHTML" not in js and "textContent" in js
    from endpoints.onboarding import routes
    known = {(m, r.path) for r in routes.router.routes for m in getattr(r, "methods", ())}
    for verb, path in (("GET", "/api/admin/onboarding/engines/{engine_id}/bundles"), ("POST", "/api/admin/onboarding/engines/{engine_id}/bundles"),
                       ("GET", "/api/admin/onboarding/engines/{engine_id}/bundles/{bundle_id}"), ("POST", "/api/admin/onboarding/engines/{engine_id}/bundles/{bundle_id}/merged"),
                       ("POST", "/api/admin/onboarding/engines/{engine_id}/bundles/{bundle_id}/supersede")):
        assert (verb, path) in known, (verb, path)
    assert "/bundles'" in js and "'merged'" in js and "'supersede'" in js and "pr_url" in js and "/' + what" in js


def test_the_owner_engine_page_shows_the_bundle_status_as_text():
    html, js = text_of(ROOT / "public" / "onboarding" / "engine.html"), text_of(ROOT / "public" / "onboarding" / "engine.js")
    assert 'id="bundleBox"' in html and 'id="bundleList"' in html and "e.bundles" in js and "innerHTML" not in js
