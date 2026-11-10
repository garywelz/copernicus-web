"""Onboarding PR 4a: the generic engine loader (scripts/onboarding/load_engine.py; design 2.9, 5.6, 8.1).
Offline: the atomic in-memory Firestore, the fetch layer replaced by a table built from SYNTHETIC fixture files (tests/fixtures/onboarding_loader), and a fixed
clock. No real names, abstracts or repositories appear here; the counts have the shapes of the TDAP files at b384da6 (3 questions, 6 confirmed + 4 proposed seeds,
65 held in groups of 24, 10 and 31, 4 flagged likely keep)."""
import copy
import importlib.util
import shutil
from datetime import datetime, timezone
from pathlib import Path

import pytest

from tests.fakes_pr2 import FakeDB, run_in_transaction
from utils import onboarding as ob
from utils import onboarding_base as base

ROOT = Path(__file__).resolve().parents[2]
FIXTURE = Path(__file__).parent / "fixtures" / "onboarding_loader"
SPEC = importlib.util.spec_from_file_location("load_engine_under_test", ROOT / "scripts" / "onboarding" / "load_engine.py")
le = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(le)

REPO, SHA, SHA2 = "someone/demo-engine", "a" * 40, "b" * 40
RAW = f"{base.RAW_HOST}/{REPO}/"
NOW = datetime(2026, 11, 11, 12, 0, tzinfo=timezone.utc)
ENGINE = "demo"
LINE = f"Approved: load {ENGINE} from {REPO}@{SHA[:12]} into {le.DEFAULT_PROJECT}"


def tree(tmp_path, name="a"):
    dest = tmp_path / name
    shutil.copytree(FIXTURE, dest)
    return dest


@pytest.fixture
def web(monkeypatch):
    """repo files by commit: web.set(SHA, tree) serves that tree at that commit; status overrides per path with web.override[(sha, path)] = (status, bytes)."""
    class Web:
        trees, override, calls = {}, {}, []

        def set(self, sha, root):
            self.trees[sha] = Path(root)

        def get(self, url, headers=None):
            self.calls.append(url)
            assert url.startswith(RAW), url
            sha, path = url[len(RAW):].split("/", 1)
            if (sha, path) in self.override:
                return self.override[(sha, path)]
            f = self.trees[sha] / path
            return (200, f.read_bytes()) if f.is_file() else (404, b"")
    w = Web()
    w.trees, w.override, w.calls = {}, {}, []
    monkeypatch.setattr(le.base, "_http_get", w.get)
    monkeypatch.setattr(le.base, "base_commit", lambda repo, now=None: SHA)
    monkeypatch.setattr(ob, "_run_in_transaction", run_in_transaction)
    return w


def engine_db(**extra):
    return FakeDB(**{ob.ENGINES: {ENGINE: {"label": "Demo", "state": "open"}}, **extra})


def run(args, db, capsys, web_=None):
    code = le.main(["--engine-id", ENGINE, "--repo", REPO, "--commit", SHA, *args], db=db, now=NOW)
    cap = capsys.readouterr()
    return code, cap.out, cap.err


def snapshot(db):
    return copy.deepcopy(db.data)


# ---- counts and shapes -------------------------------------------------------------------------------------------------------------------------------
def test_dry_run_counts_match_the_tdap_shapes_and_writes_nothing(web, capsys):
    web.set(SHA, FIXTURE)
    db = engine_db()
    before = snapshot(db)
    code, out, _ = run([], db, capsys)
    assert code == 0 and snapshot(db) == before, (out, _)
    assert "3 questions, 12 keyword entries, 10 seeds, 65 hold-list candidates (4 likely keep)" in out
    assert "nothing was written (dry run)" in out and LINE in out


def test_apply_writes_every_entry_unanswered(web, capsys):
    web.set(SHA, FIXTURE)
    db = engine_db()
    code, out, _ = run(["--apply", "--approval", LINE], db, capsys)
    assert code == 0, out
    items, cands = db.data[le.ITEMS], db.data[le.CANDIDATES]
    by_section = {s: [d for d in items.values() if d["section"] == s] for s in ("questions", "keywords", "seeds")}
    assert [len(by_section[s]) for s in ("questions", "keywords", "seeds")] == [3, 12, 10]
    assert len(cands) == 65 and sum(c["flags"]["likely_keep"] for c in cands.values()) == 4
    assert {c["flags"]["group"].split(" (")[0] for c in cands.values()} == {"Moved out of the first corpus write on review", "Background material cited by the roadmap",
                                                                                "Reachable only from the proposed seeds"}
    for d in items.values():                                             # unanswered: its own state, nothing pre-filled
        assert d["revision"] == 0 and d["choice"] is None and d["author_subscriber_id"] is None and d["comment_count"] == 0 and d["history"] == []
        assert d["context"]["source_sha256"] and d["context"]["loaded_by"] == "load_engine"
        assert d["engine_id"] == ENGINE
    for c in cands.values():
        assert c["origin"] == "hold_list" and c["decision"] is None and c["abstract"] is None and c["identifier"].startswith("doi:")
    seeds = by_section["seeds"]
    assert sorted(s["context"]["status_in_repo"] for s in seeds) == ["confirmed"] * 6 + ["proposed"] * 4
    assert all(s["value"] == {"comment": ""} for s in seeds)


def test_every_entry_of_every_list_has_an_item(web, capsys):
    """The mute-list lesson: a list entry the loader skipped would vanish from the next bundle."""
    web.set(SHA, FIXTURE)
    db = engine_db()
    run(["--apply", "--approval", LINE], db, capsys)
    import json
    focus = json.loads((FIXTURE / "docs" / "research_focus.json").read_text(encoding="utf-8"))
    stored = {(d["value"]["list"], d["value"]["text"]) for d in db.data[le.ITEMS].values() if d["type"] == "keyword_entry"}
    for key in ("categories", "horizons", "mute", "frontier", "flagged"):
        assert {(key, e) for e in focus[key]} <= stored
    assert {d["item_id"] for d in db.data[le.ITEMS].values() if d["type"] == "question"} == {q["id"] for q in focus["active_questions"]}
    terms = {d["item_id"]: [t["text"] for t in d["value"]["terms"]] for d in db.data[le.ITEMS].values() if d["type"] == "question"}
    assert terms == {q["id"]: q["terms"] for q in focus["active_questions"]}


def test_engine_source_and_one_event_are_recorded(web, capsys):
    web.set(SHA, FIXTURE)
    db = engine_db()
    run(["--apply", "--approval", LINE], db, capsys)
    assert db.data[ob.ENGINES][ENGINE]["source"] == {"repo": REPO, "commit_sha": SHA, "loaded_at": NOW.isoformat()}
    events = list(db.data[ob.EVENTS].values())
    assert len(events) == 1 and events[0]["action"] == "engine_load" and events[0]["target"] == f"{REPO}@{SHA[:12]}"
    assert events[0]["engine_id"] == ENGINE and events[0]["actor_subscriber_id"] == "admin" and events[0]["counts"]["candidates"] == 65
    assert events[0]["before_sha256"] is None and events[0]["after_sha256"]


# ---- identifiers -------------------------------------------------------------------------------------------------------------------------------------
@pytest.mark.parametrize("kind,raw,want", [
    ("doi", "https://doi.org/10.1000/ABC.1", "doi:10.1000/abc.1"), ("doi", "doi:10.1000/abc.1", "doi:10.1000/abc.1"), ("doi", "not a doi", None),
    ("arxiv", "arXiv:2601.00012v3", "arxiv:2601.00012"), ("arxiv", "https://arxiv.org/abs/hep-th/9901001", "arxiv:hep-th/9901001"), ("arxiv", "12", None),
    ("pmid", "PMID: 31452104", "pmid:31452104"), ("pmid", "12ab", None)])
def test_identifier_normalisation(kind, raw, want):
    assert le.normalise_identifier(kind, raw) == want


def test_identifier_priority_doi_then_arxiv_then_pmid_and_the_others_are_kept():
    found, key = le.identifiers("10.1000/x", "2601.00001", "123")
    assert key == "doi:10.1000/x" and found == {"doi": "doi:10.1000/x", "arxiv": "arxiv:2601.00001", "pmid": "pmid:123"}
    assert le.identifiers("", "2601.00001", "123")[1] == "arxiv:2601.00001" and le.identifiers("", "", "123")[1] == "pmid:123"


def test_a_seed_keyed_only_by_author_name_is_refused(web, tmp_path, capsys):
    root = tree(tmp_path)
    p = root / "docs" / "seeds.csv"
    p.write_text(p.read_text(encoding="utf-8").replace("10.9999/demo.seed.04", ""), encoding="utf-8")
    web.set(SHA, root)
    code, _, err = run([], engine_db(), capsys)
    assert code == 1 and "no doi, arxiv id or pmid" in err


def test_a_pmid_only_seed_is_keyed_by_pmid(web, tmp_path, capsys):
    root = tree(tmp_path)
    (root / "docs" / "seeds.csv").write_text("doi,pmid,question_ids,title,status\n,31452104,demo-q1,Synthetic pmid seed,proposed\n", encoding="utf-8")
    (root / "docs" / "seed_papers.md").write_text("# none\n", encoding="utf-8")
    web.set(SHA, root)
    db = engine_db()
    assert run(["--apply", "--approval", LINE], db, capsys)[0] == 0
    seed = next(d for d in db.data[le.ITEMS].values() if d["section"] == "seeds")
    assert seed["context"]["identifier"] == "pmid:31452104"


# ---- idempotence and a new commit ---------------------------------------------------------------------------------------------------------------------
def test_rerun_at_the_same_commit_changes_nothing(web, capsys):
    web.set(SHA, FIXTURE)
    db = engine_db()
    run(["--apply", "--approval", LINE], db, capsys)
    before = snapshot(db)
    db.fail_writes_to = {le.ITEMS, le.CANDIDATES, ob.EVENTS, ob.ENGINES}          # any write at all would raise
    code, out, _ = run(["--apply", "--approval", LINE], db, capsys)
    assert code == 0 and snapshot(db) == before and "no write was made" in out
    code, out, _ = run([], db, capsys)
    assert code == 0 and "0 create, 0 update (untouched by owners), 90 unchanged, 0 conflict" in out


def changed_tree(tmp_path):
    root = tree(tmp_path, "b")
    p = root / "docs" / "research_focus.json"
    p.write_text(p.read_text(encoding="utf-8").replace("question number 2?", "question number two, reworded?").replace('"synthetic muted topic four"', '"synthetic muted topic four", "a new muted topic"'), encoding="utf-8")
    h = root / "docs" / "hold_list.md"
    h.write_text(h.read_text(encoding="utf-8").replace("cited_by=101", "cited_by=999"), encoding="utf-8")
    return root


def test_a_new_commit_reports_a_diff_and_updates_only_untouched_items(web, tmp_path, capsys):
    web.set(SHA, FIXTURE)
    web.set(SHA2, changed_tree(tmp_path))
    db = engine_db()
    run(["--apply", "--approval", LINE], db, capsys)
    code = le.main(["--engine-id", ENGINE, "--repo", REPO, "--commit", SHA2, "--apply", "--approval", f"Approved: load {ENGINE} from {REPO}@{SHA2[:12]} into {le.DEFAULT_PROJECT}"], db=db, now=NOW)
    out = capsys.readouterr().out
    assert code == 0 and "a diff against" in out
    q2 = db.data[le.ITEMS][f"{ENGINE}__questions__demo-q2"]
    assert q2["value"]["wording"] == "Synthetic research question number two, reworded?" and q2["revision"] == 0
    assert any(d["value"].get("text") == "a new muted topic" for d in db.data[le.ITEMS].values() if d["type"] == "keyword_entry")
    assert db.data[ob.ENGINES][ENGINE]["source"]["commit_sha"] == SHA2
    assert [e["previous_commit_sha"] for e in db.data[ob.EVENTS].values()].count(SHA) == 1


def second(db, capsys):
    return le.main(["--engine-id", ENGINE, "--repo", REPO, "--commit", SHA2, "--apply", "--approval", f"Approved: load {ENGINE} from {REPO}@{SHA2[:12]} into {le.DEFAULT_PROJECT}"], db=db, now=NOW)


def test_an_item_an_owner_edited_is_left_untouched_and_a_conflict_stops_the_load(web, tmp_path, capsys):
    web.set(SHA, FIXTURE)
    web.set(SHA2, changed_tree(tmp_path))
    db = engine_db()
    run(["--apply", "--approval", LINE], db, capsys)
    key = f"{ENGINE}__questions__demo-q2"
    db.data[le.ITEMS][key].update({"revision": 2, "choice": "reword", "author_subscriber_id": "s1", "value": {"wording": "the owners' own wording"}})
    before = snapshot(db)
    assert second(db, capsys) == 1
    out = capsys.readouterr().out
    assert f"CONFLICT: {le.ITEMS}/{key}" in out and "nothing was written" in out
    assert snapshot(db) == before


def test_an_owner_edited_item_whose_source_did_not_change_is_simply_unchanged(web, tmp_path, capsys):
    web.set(SHA, FIXTURE)
    web.set(SHA2, changed_tree(tmp_path))
    db = engine_db()
    run(["--apply", "--approval", LINE], db, capsys)
    key = f"{ENGINE}__questions__demo-q1"
    db.data[le.ITEMS][key].update({"revision": 3, "choice": "accept", "author_subscriber_id": "s1"})
    kept = copy.deepcopy(db.data[le.ITEMS][key])
    assert second(db, capsys) == 0                       # q2 (untouched, changed upstream) is updated; q1 (edited, unchanged upstream) is not a conflict
    assert db.data[le.ITEMS][key] == kept
    assert db.data[le.ITEMS][f"{ENGINE}__questions__demo-q2"]["value"]["wording"].endswith("reworded?")


def test_removed_upstream_is_reported_never_deleted(web, tmp_path, capsys):
    web.set(SHA, FIXTURE)
    root = tree(tmp_path, "c")
    p = root / "docs" / "research_focus.json"
    p.write_text(p.read_text(encoding="utf-8").replace('    "synthetic muted topic one",' + chr(10), ""), encoding="utf-8")
    web.set(SHA2, root)
    db = engine_db()
    run(["--apply", "--approval", LINE], db, capsys)
    n = len(db.data[le.ITEMS])
    assert second(db, capsys) == 0
    out = capsys.readouterr().out
    assert "removed upstream: " in out and "1 removed upstream" in out and len(db.data[le.ITEMS]) == n


def test_an_open_bundle_on_a_different_base_refuses_apply_and_is_listed(web, capsys):
    web.set(SHA, FIXTURE)
    db = engine_db(**{le.BUNDLES: {"b1": {"engine_id": ENGINE, "status": "exported", "base_commit_sha": SHA2}, "b2": {"engine_id": ENGINE, "status": "merged", "base_commit_sha": SHA2},
                                     "b3": {"engine_id": ENGINE, "status": "created", "base_commit_sha": SHA}}})
    before = snapshot(db)
    code, out, _ = run(["--apply", "--approval", LINE], db, capsys)
    assert code == 1 and "BLOCKED: bundle b1 is exported" in out and "bundle b2" not in out and "bundle b3" not in out
    assert snapshot(db) == before


# ---- the approval gate and the dry run ----------------------------------------------------------------------------------------------------------------
@pytest.mark.parametrize("approval", ["", "approved", LINE.replace(ENGINE, "other"), LINE + " please", LINE.replace(SHA[:12], SHA2[:12])])
def test_apply_needs_the_exact_typed_line(web, capsys, approval):
    web.set(SHA, FIXTURE)
    db = engine_db()
    before = snapshot(db)
    code, _, err = run(["--apply", "--approval", approval], db, capsys)
    assert code == 2 and "approval line" in err and snapshot(db) == before and web.calls == []


def test_there_is_no_scratch_flag_and_apply_cannot_run_offline_or_from_files(web, capsys):
    web.set(SHA, FIXTURE)
    assert run(["--scratch"], engine_db(), capsys)[0] == 2
    assert run(["--apply", "--approval", LINE, "--offline"], engine_db(), capsys)[0] == 2
    assert run(["--apply", "--approval", LINE, "--files-dir", str(FIXTURE)], engine_db(), capsys)[0] == 2


def test_dry_run_needs_no_approval_and_a_missing_engine_is_an_error(web, capsys):
    web.set(SHA, FIXTURE)
    assert run([], FakeDB(), capsys)[0] == 2
    assert run(["--offline"], None, capsys)[0] == 0


@pytest.mark.parametrize("args", [["--engine-id", "Bad_ID", "--repo", REPO, "--commit", SHA], ["--engine-id", ENGINE, "--repo", "../etc/passwd", "--commit", SHA],
                                  ["--engine-id", ENGINE, "--repo", REPO, "--commit", "main"], ["--engine-id", ENGINE, "--repo", REPO, "--commit", SHA[:12]]])
def test_bad_arguments_are_a_usage_error(web, capsys, args):
    assert le.main(args, db=engine_db()) == 2 and web.calls == []


def test_a_main_that_moved_ahead_of_the_pinned_commit_warns(web, monkeypatch, capsys):
    web.set(SHA, FIXTURE)
    monkeypatch.setattr(le.base, "base_commit", lambda repo, now=None: SHA2)
    code, out, _ = run([], engine_db(), capsys)
    assert code == 0 and f"WARNING: main is at {SHA2[:12]}" in out


# ---- refusals (each shown capable of failing: the clean fixture passes) ------------------------------------------------------------------------------------
def edit(tmp_path, rel, fn):
    root = tree(tmp_path)
    p = root / rel
    p.write_text(fn(p.read_text(encoding="utf-8")), encoding="utf-8")
    return root


REFUSALS = {
    "malformed json": ("docs/research_focus.json", lambda t: t[:-20], "does not parse"),
    "questions not a list": ("docs/research_focus.json", lambda t: t.replace('"active_questions": [', '"active_questions": {"x": ['), "does not parse"),
    "an email in a value": ("docs/research_focus.json", lambda t: t.replace("synthetic horizon one", "write to someone@example.org"), "email-shaped"),
    "an email in an ignored field": ("docs/research_focus.json", lambda t: t.replace('"updated": "2026-01-01"', '"updated": "a@b.co"'), "email-shaped"),
    "html in a value": ("docs/research_focus.json", lambda t: t.replace("synthetic horizon one", "<b>bold</b> horizon"), "HTML or a script"),
    "a script in a value": ("docs/research_focus.json", lambda t: t.replace("synthetic horizon one", "<script>alert(1)</script>"), "HTML or a script"),
    "a javascript url": ("docs/research_focus.json", lambda t: t.replace("synthetic horizon one", "javascript:alert(1)"), "HTML or a script"),
    "a control character": ("docs/research_focus.json", lambda t: t.replace("synthetic horizon one", "synthetic\\u0007 horizon"), "control characters"),
    "an over-cap wording": ("docs/research_focus.json", lambda t: t.replace("Synthetic research question number 1?", "x" * 601), "longer than 600"),
    "an invalid priority": ("docs/research_focus.json", lambda t: t.replace('"id": "demo-q1",', '"id": "demo-q1", "priority": "urgent",'), "priority"),
    "an invalid question id": ("docs/research_focus.json", lambda t: t.replace('"demo-q1",\n      "q"', '"Demo_Q1",\n      "q"'), "not a valid item id"),
    "a duplicate question id": ("docs/research_focus.json", lambda t: t.replace('"id": "demo-q2"', '"id": "demo-q1"'), "appears twice"),
    "a ragged csv row": ("docs/seeds.csv", lambda t: t.replace("Synthetic Seed Paper 02,,", "Synthetic Seed Paper 02,"), "fields, the header"),
    "a repeated csv column": ("docs/seeds.csv", lambda t: t.replace("doi,question_ids", "doi,doi"), "repeats a column"),
    "a csv with no doi column": ("docs/seeds.csv", lambda t: t.replace("doi,", "id,", 1), "no doi column"),
    "an invalid doi": ("docs/seeds.csv", lambda t: t.replace("10.9999/demo.seed.01", "ten-point-nine"), "not a valid identifier"),
    "a duplicate seed": ("docs/seeds.csv", lambda t: t.replace("10.9999/demo.seed.02", "10.9999/demo.seed.01"), "is also on line"),
    "an email in a csv cell": ("docs/seeds.csv", lambda t: t.replace("Synthetic Seed Paper 03", "Paper by me@example.org"), "email-shaped"),
    "html in a csv cell": ("docs/seeds.csv", lambda t: t.replace("Synthetic Seed Paper 03", "Paper <img src=x onerror=1>"), "HTML or a script"),
    "a seed listed only in the markdown": ("docs/seeds.csv", lambda t: "\n".join(l for l in t.split("\n") if "demo.seed.05" not in l), "would drop it"),
    "html in the seed markdown": ("docs/seed_papers.md", lambda t: t.replace("Synthetic source 1", "<iframe src=x>"), "HTML or a script"),
    "a hold entry without an identifier": ("docs/hold_list.md", lambda t: t.replace("-- `10.9998/held.010`", "-- see the notes"), "without an identifier"),
    "a duplicate hold entry": ("docs/hold_list.md", lambda t: t.replace("held.011", "held.010"), "is also on line"),
    "an invalid hold identifier": ("docs/hold_list.md", lambda t: t.replace("10.9998/held.010", "10.99"), "not a valid identifier"),
    "an email in a hold title": ("docs/hold_list.md", lambda t: t.replace("Synthetic held paper 010", "Held paper (me@example.org)"), "email-shaped"),
}


def test_the_clean_fixture_is_accepted_so_every_refusal_below_can_fail(web, capsys):
    web.set(SHA, FIXTURE)
    assert run([], engine_db(), capsys)[0] == 0


@pytest.mark.parametrize("name", sorted(REFUSALS))
def test_hostile_or_malformed_input_is_refused_and_nothing_is_written(web, tmp_path, capsys, name):
    rel, fn, why = REFUSALS[name]
    web.set(SHA, edit(tmp_path, rel, fn))
    db = engine_db()
    before = snapshot(db)
    code, out, err = run(["--apply", "--approval", LINE], db, capsys)
    assert code == 1 and "REFUSED" in err and why in err, (out, err)
    assert snapshot(db) == before


def test_an_oversize_file_is_refused(web, capsys):
    web.set(SHA, FIXTURE)
    web.override[(SHA, "docs/hold_list.md")] = (200, b"x" * (base.MAX_BYTES + 1))
    code, _, err = run([], engine_db(), capsys)
    assert code == 1 and "larger than" in err


def test_a_missing_required_file_is_refused_but_the_hold_list_is_optional(web, tmp_path, capsys):
    root = tree(tmp_path)
    (root / "docs" / "hold_list.md").unlink()
    web.set(SHA, root)
    code, out, _ = run([], engine_db(), capsys)
    assert code == 0 and "hold_list.md (absent)" in out and "0 hold-list candidates" in out
    (root / "docs" / "seeds.csv").unlink()
    code, _, err = run([], engine_db(), capsys)
    assert code == 1 and "seeds.csv: not found" in err


def test_an_unreachable_host_is_exit_2_and_a_non_utf8_file_is_refused(web, capsys):
    web.set(SHA, FIXTURE)
    web.override[(SHA, "docs/seeds.csv")] = (503, b"")
    assert run([], engine_db(), capsys)[0] == 2
    web.override[(SHA, "docs/seeds.csv")] = (200, b"\xff\xfe\x00bad")
    assert run([], engine_db(), capsys)[0] == 1


def test_the_loader_holds_nothing_engine_specific():
    src = (ROOT / "scripts" / "onboarding" / "load_engine.py").read_text(encoding="utf-8").lower()
    assert "tdap" not in src
