"""The one-off arXiv backfill (backfill_arxiv_window.py; governance/BULLETIN.md entry 045). Offline: the scout's two network
functions (search_arxiv, fetch_arxiv_papers) are replaced by a table, so no test calls arXiv, and every file is written under
pytest's tmp_path.

THE LAYOUT IS THE SCOUT'S REAL ONE, and the fixtures are made BY THE SCOUT: `scout_saves()` runs the scout's own
acquire_recent_papers, which saves to <papers>/arxiv_recent/biology/arxiv_recent_<id>.json with every paper marked biology.
The first version of this script looked for <papers>/<discipline>/arxiv_<id>.json instead, so it would have seen none of the
scout's papers as on disk, overstated "new", and written duplicates under a second name (found in review by Claude Chat,
2026-11-14). The tests marked LAYOUT fail on that version."""

from __future__ import annotations

import importlib.util
import json
import re
import sys
from datetime import date
from pathlib import Path

import pytest

ACQUIRE = Path(__file__).resolve().parents[1]
TODAY = date(2026, 11, 14)
WINDOW = ["--from", "2026-10-18", "--to", "2026-11-14"]


def _load(name):
    spec = importlib.util.spec_from_file_location(name + "_under_test", ACQUIRE / f"{name}.py")
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name + "_under_test"] = mod
    spec.loader.exec_module(mod)
    return mod


backfill = _load("backfill_arxiv_window")


def paper(arxiv_id, category="computer_science"):
    """A paper as the scout's parser returns it: the id carries its version, and the category is whatever arXiv's was (the scout
    overwrites it with biology before saving)."""
    return {"id": f"arxiv_{arxiv_id}", "arxiv_id": arxiv_id, "title": f"Paper {arxiv_id}", "category": category, "discipline": category}


class Arxiv:
    """Stands in for arXiv: `results` maps a substring of the query to the papers it matches, or to an error dict, or to
    (the total arXiv reports, the papers that actually came back)."""

    def __init__(self, results):
        self.results, self.searches, self.fetches = results, [], []

    def _match(self, query):
        return next((v for k, v in self.results.items() if k in query), [])

    def search(self, query, max_results, sort_by="submittedDate", sort_order="descending", start=0):
        self.searches.append((query, max_results))
        got = self._match(query)
        if isinstance(got, dict):
            return {"ok": False, "entries": [], "total": 0, "namespace": None, **got}
        return {"ok": True, "entries": [], "total": got[0] if isinstance(got, tuple) else len(got), "namespace": {}}

    def fetch(self, query, max_results, sort_by="submittedDate", sort_order="descending"):
        self.fetches.append((query, max_results))
        got = self._match(query)
        if isinstance(got, dict):
            return [], got
        return ([dict(p) for p in got[1]], None) if isinstance(got, tuple) else ([dict(p) for p in got][:max_results], None)


@pytest.fixture
def env(tmp_path, monkeypatch):
    scout = backfill.load_scout()
    papers_dir = tmp_path / "papers"
    monkeypatch.setattr(scout, "DELAY_BETWEEN_QUERIES", 0)
    monkeypatch.setattr(scout, "OUTPUT_DIR", papers_dir)
    lines = []

    def use(results):
        arxiv = Arxiv(results)
        monkeypatch.setattr(scout, "search_arxiv", arxiv.search)
        monkeypatch.setattr(scout, "fetch_arxiv_papers", arxiv.fetch)
        return arxiv

    def go(results, *flags, argv=None, default_dir=False):
        arxiv = use(results)
        lines.clear()
        where = [] if default_dir else ["--output-dir", str(papers_dir)]
        rc = backfill.main((argv if argv is not None else WINDOW) + list(flags) + where, scout=scout, today=TODAY, out=lines.append)
        return rc, arxiv, "\n".join(lines)

    def scout_saves(papers):
        """Run the SCOUT's own session (acquire_recent_papers) so the files on disk are exactly what the scout writes."""
        use({"q-bio": papers})
        total, stats = scout.acquire_recent_papers(target_count=150)
        assert stats["saved"] == len(papers)
        return total
    return type("Env", (), {"go": staticmethod(go), "scout_saves": staticmethod(scout_saves), "dir": papers_dir, "scout": scout})()


def files(root):
    return sorted(str(p.relative_to(root)).replace("\\", "/") for p in root.rglob("*") if p.is_file()) if root.exists() else []


def stats(text):
    return {k: int(v) for k, v in re.findall(r"(\w+)=(\d+)", next(l for l in text.split("\n") if l.startswith("BACKFILL_STATS")))}


FOUR = {"q-bio.GN": [paper("2610.00001v1"), paper("2610.00002v1")], "q-bio.CB": [paper("2610.00003v2")],
        "cs.LG": [paper("2610.00002v1"), paper("2610.00004v1")], "q-bio.PE": []}


# ---- the queries ---------------------------------------------------------------------------------------------------------------
def test_the_queries_are_the_scouts_own_with_the_window_as_full_timestamps(env):
    rc, arxiv, text = env.go(FOUR, "--count-only")
    queries = [q for q, _ in arxiv.searches]
    assert queries == [
        "(cat:q-bio.GN OR cat:q-bio.MN) AND submittedDate:[202610180000 TO 202611142359]",
        "(cat:q-bio.CB OR cat:q-bio.BM OR cat:q-bio.QM) AND submittedDate:[202610180000 TO 202611142359]",
        "(cat:cs.LG OR cat:cs.NE) AND (all:biology OR all:genomics OR all:gene OR all:regulatory OR all:protein OR all:DNA OR all:RNA) AND submittedDate:[202610180000 TO 202611142359]",
        "(cat:q-bio.PE OR cat:q-bio.NC) AND submittedDate:[202610180000 TO 202611142359]"]
    assert not [q for q in queries if "*" in q], "no wildcard: that is the form arXiv answers with HTTP 500"
    config = json.loads((ACQUIRE / "daily_scout_config.json").read_text(encoding="utf-8"))["arxiv_queries"]
    assert len(queries) == len(config) == 4
    assert queries[0] == env.scout.build_arxiv_query(config[0]["categories"], 27, None, today=TODAY), "built by the scout's own function"


def test_count_only_makes_one_request_per_query_and_fetches_and_writes_nothing(env):
    env.scout_saves([paper("2610.00001v1")])
    before = files(env.dir)
    rc, arxiv, text = env.go(FOUR, "--count-only")
    assert rc == 0 and len(arxiv.searches) == 4 and arxiv.fetches == [] and files(env.dir) == before
    assert all(n == 1 for _, n in arxiv.searches)
    assert stats(text)["matched"] == 5 and stats(text)["fetched"] == 0 and "COUNT ONLY: nothing was fetched or written" in text


# ---- LAYOUT: what the scout saved is on disk -------------------------------------------------------------------------------------
def test_LAYOUT_a_paper_the_scout_already_saved_counts_as_on_disk(env):
    """The scout saved 2610.00001 and 2610.00003 in an earlier session. A dry run over a window that matches them and two others
    must report 2 on disk and 2 new. (The first version of the script reported 0 on disk and 4 new.)"""
    env.scout_saves([paper("2610.00001v1"), paper("2610.00003v2")])
    assert files(env.dir) == ["arxiv_recent/biology/arxiv_recent_2610.00001v1.json", "arxiv_recent/biology/arxiv_recent_2610.00003v2.json"], "the scout's real layout"
    before = files(env.dir)
    rc, arxiv, text = env.go(FOUR, "--dry-run")
    s = stats(text)
    assert rc == 0 and (s["matched"], s["fetched"], s["duplicates"], s["on_disk"], s["new"], s["saved"]) == (5, 5, 1, 2, 2, 0)
    assert "arXiv papers already on disk (any batch name, versions ignored): 2" in text
    assert files(env.dir) == before and "DRY RUN: nothing was written" in text
    assert [n for _, n in arxiv.fetches] == [2, 1, 2], "each query is fetched in full: no cap; a query with nothing is not fetched"


def test_LAYOUT_write_saves_where_and_how_the_scout_does_and_adds_no_second_name_for_a_paper(env):
    env.scout_saves([paper("2610.00001v1"), paper("2610.00003v2")])
    kept = env.dir / "arxiv_recent" / "biology" / "arxiv_recent_2610.00001v1.json"
    kept_text = kept.read_text(encoding="utf-8")
    rc, arxiv, text = env.go(FOUR, "--write")
    s = stats(text)
    assert rc == 0 and (s["new"], s["on_disk"], s["duplicates"], s["saved"]) == (2, 2, 1, 2) and "WROTE" in text
    assert files(env.dir) == [f"arxiv_recent/biology/arxiv_recent_2610.0000{n}v{v}.json" for n, v in ((1, 1), (2, 1), (3, 2), (4, 1))]
    assert kept.read_text(encoding="utf-8") == kept_text, "a paper already on disk is not rewritten"
    ids = [backfill.id_in_filename(Path(f).stem) for f in files(env.dir)]
    assert len(ids) == len(set(ids)) == 4, "one file per paper: no duplicate under a second name"
    again = env.go(FOUR, "--write")
    assert stats(again[2])["new"] == 0 and stats(again[2])["saved"] == 0 and stats(again[2])["on_disk"] == 4, "a second run writes nothing"


def test_LAYOUT_a_backfilled_file_is_indistinguishable_from_one_the_scout_saved(env):
    env.scout_saves([paper("2610.00001v1")])
    env.go({"q-bio.GN": [paper("2610.00002v1")]}, "--write")
    by_scout = json.loads((env.dir / "arxiv_recent" / "biology" / "arxiv_recent_2610.00001v1.json").read_text(encoding="utf-8"))
    by_backfill = json.loads((env.dir / "arxiv_recent" / "biology" / "arxiv_recent_2610.00002v1.json").read_text(encoding="utf-8"))
    assert set(by_scout) == set(by_backfill) and by_backfill["category"] == by_scout["category"] == "biology" and by_backfill["discipline"] == by_scout["discipline"] == "biology"
    source = (ACQUIRE / "acquire_arxiv_batch.py").read_text(encoding="utf-8")
    assert 'save_papers(all_papers, OUTPUT_DIR / "arxiv_recent", batch_name="arxiv_recent")' in source, "if the scout's layout changes, this script must follow"
    assert (backfill.SCOUT_SUBDIR, backfill.SCOUT_BATCH_NAME, backfill.SCOUT_DISCIPLINE) == ("arxiv_recent", "arxiv_recent", "biology")


def test_LAYOUT_the_default_papers_directory_is_the_scouts_own(env):
    rc, arxiv, text = env.go({"q-bio.GN": [paper("2610.00009v1")]}, "--write", default_dir=True)
    assert rc == 0 and files(env.dir) == ["arxiv_recent/biology/arxiv_recent_2610.00009v1.json"] and str(env.dir) in text


def test_on_disk_means_any_batch_name_anywhere_under_the_papers_directory_and_ignores_the_version(env):
    for rel in ("arxiv_classic/mathematics/arxiv_classic_2610.00001v3.json", "biology/arxiv_2610.00002.json", "arxiv_test/biology/arxiv_test_2610.00003v1.json",
                "biology/glmp_scout/cited_2610.00004v9.json", "arxiv_classic/physics/arxiv_classic_0301001v1.json",
                "biology/pubmed_38123456.json", "biology/biorxiv_10.1101_2026.10.20.123456.json", "arxiv_recent/biology/notes.txt"):
        f = env.dir / rel
        f.parent.mkdir(parents=True, exist_ok=True)
        f.write_text("{}", encoding="utf-8")
    assert backfill.ids_on_disk(env.dir) == {"2610.00001", "2610.00002", "2610.00003", "2610.00004", "0301001"}, "a PubMed or bioRxiv file is not mistaken for an arXiv id"
    wanted = {"q-bio.GN": [paper("2610.00001v1"), paper("2610.00002v2"), paper("2610.00003v1"), paper("2610.00004v1"), paper("2610.00005v1")]}
    before = files(env.dir)
    rc, arxiv, text = env.go(wanted, "--write")
    s = stats(text)
    assert (s["on_disk"], s["new"], s["saved"]) == (4, 1, 1), "a newer version of a paper on disk is the same paper"
    assert sorted(set(files(env.dir)) - set(before)) == ["arxiv_recent/biology/arxiv_recent_2610.00005v1.json"]


@pytest.mark.parametrize("stem,expected", [
    ("arxiv_recent_2610.01234v1", "2610.01234"), ("arxiv_recent_2610.01234", "2610.01234"), ("arxiv_2401.00001v12", "2401.00001"), ("arxiv_classic_0704.0001v2", "0704.0001"),
    ("cited-2610.01234", "2610.01234"), ("2610.01234v2", "2610.01234"), ("arxiv_classic_0301001v1", "0301001"),
    ("pubmed_38123456", None), ("pubmed_0301001", None), ("biorxiv_10.1101_2026.10.20.123456", None), ("arxiv_recent_report", None), ("x12610.01234", None), ("", None)])
def test_the_id_a_file_is_named_for(stem, expected):
    assert backfill.id_in_filename(stem) == expected
    assert backfill.base_id("2610.01234v2") == backfill.base_id("2610.01234") == "2610.01234"


def test_the_ids_on_disk_are_collected_once_not_once_per_paper(env, monkeypatch):
    env.scout_saves([paper(f"2610.{n:05d}v1") for n in range(40)])
    walks = []
    real = Path.rglob

    def counting(self, pattern):
        walks.append((str(self), pattern))
        return real(self, pattern)
    monkeypatch.setattr(Path, "rglob", counting)
    rc, arxiv, text = env.go({"q-bio.GN": [paper(f"2610.{n:05d}v1") for n in range(30, 300)]}, "--dry-run")
    monkeypatch.setattr(Path, "rglob", real)
    assert walks == [(str(env.dir), "*.json")], "one walk of the papers directory for 270 papers"
    assert (stats(text)["on_disk"], stats(text)["new"]) == (10, 260)
    code = (ACQUIRE / "backfill_arxiv_window.py").read_text(encoding="utf-8").split('"""', 2)[2]
    assert ".exists()" not in code.replace("output_dir.exists()", "") and "iterdir" not in code and "glob(" not in code.replace("rglob(", ""), "no filesystem search inside the per-paper loop"


# ---- no cap, failures, usage ---------------------------------------------------------------------------------------------------
def test_there_is_no_cap_but_a_query_over_the_safety_ceiling_is_refused_not_cut(env):
    many = {"q-bio.GN": [paper(f"2610.{n:05d}v1") for n in range(1500)]}
    rc, arxiv, text = env.go(many, "--dry-run")
    assert rc == 0 and stats(text)["new"] == 1500 and arxiv.fetches[0][1] == 1500, "1,500 papers are all fetched: ten sessions' worth of the scout's 150"
    rc, arxiv, text = env.go(many, "--write", "--ceiling", "1499")
    assert rc == 1 and arxiv.fetches == [] and files(env.dir) == [] and "REFUSED: more than the safety ceiling of 1499" in text
    assert stats(text)["over_ceiling"] == 1 and "NOT COMPLETE" in text


def test_a_failed_query_is_not_reported_as_empty_and_the_others_still_run(env):
    broken = dict(FOUR, **{"q-bio.CB": {"error": "500 Server Error", "error_kind": "http_5xx"}})
    rc, arxiv, text = env.go(broken, "--write")
    s = stats(text)
    assert rc == 1 and s["failed"] == 1 and "FAILED (http_5xx)" in text and "nothing is concluded about this query" in text
    assert s["saved"] == 3 and len(files(env.dir)) == 3, "what the other queries found is saved; a re-run fills in the rest"


def test_fewer_papers_than_arxiv_counted_is_incomplete_not_success(env):
    short = dict(FOUR, **{"q-bio.GN": (5, [paper("2610.00001v1"), paper("2610.00002v1")])})
    rc, arxiv, text = env.go(short, "--dry-run")
    assert rc == 1 and stats(text)["incomplete"] == 1 and "INCOMPLETE: fetched 2 of 5" in text and "NOT COMPLETE" in text


@pytest.mark.parametrize("argv", [
    WINDOW, WINDOW + ["--dry-run", "--write"], WINDOW + ["--count-only", "--dry-run"],
    ["--from", "2026-11-14", "--to", "2026-10-18", "--dry-run"], ["--from", "2026-10-18", "--to", "2026-11-15", "--dry-run"],
    ["--from", "18 Oct", "--to", "2026-11-14", "--dry-run"], ["--to", "2026-11-14", "--dry-run"], WINDOW + ["--dry-run", "--ceiling", "0"],
    WINDOW + ["--dry-run", "--config", "no-such-file.json"]])
def test_no_mode_two_modes_a_bad_window_or_a_missing_config_is_a_usage_error_before_any_request(env, argv, capsys):
    rc, arxiv, text = env.go(FOUR, argv=argv)
    assert rc == 2 and arxiv.searches == [] and arxiv.fetches == [] and files(env.dir) == []


def test_the_script_reuses_the_scout_and_has_no_network_or_firestore_code_of_its_own():
    source = (ACQUIRE / "backfill_arxiv_window.py").read_text(encoding="utf-8")
    code = source.split('"""', 2)[2]
    for call in ("scout.build_arxiv_query(", "scout.search_arxiv(", "scout.fetch_arxiv_papers(", "scout.save_papers(to_save, output_dir / SCOUT_SUBDIR, batch_name=SCOUT_BATCH_NAME)"):
        assert call in code, call
    for token in ("requests", "urllib", "export.arxiv.org", "firestore", "google.cloud", "subprocess", "submittedDate:"):
        assert token not in code, f"{token}: the script goes through the scout for that"
    assert "open(" not in code.replace("spec.loader", "") and ".unlink(" not in code and "rmtree" not in code and "write_text" not in code
