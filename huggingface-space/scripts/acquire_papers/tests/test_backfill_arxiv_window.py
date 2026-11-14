"""The one-off arXiv backfill (backfill_arxiv_window.py; governance/BULLETIN.md entry 045). Offline: the scout's two network
functions (search_arxiv, fetch_arxiv_papers) are replaced by a table, so no test calls arXiv, and every file is written under
pytest's tmp_path. The queries, the saving and the file layout are the scout's own."""

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


def paper(arxiv_id, category="biology"):
    return {"id": f"arxiv_{arxiv_id}", "arxiv_id": arxiv_id, "title": f"Paper {arxiv_id}", "category": category, "discipline": category}


class Arxiv:
    """Stands in for arXiv: `results` maps a substring of the query to the papers it matches (or an Exception-like error dict)."""

    def __init__(self, scout, results):
        self.scout, self.results, self.searches, self.fetches = scout, results, [], []

    def _match(self, query):
        return next(v for k, v in self.results.items() if k in query)

    def search(self, query, max_results, sort_by="submittedDate", sort_order="descending", start=0):
        self.searches.append((query, max_results))
        got = self._match(query)
        if isinstance(got, dict):
            return {"ok": False, "entries": [], "total": 0, "namespace": None, **got}
        total = got[0] if isinstance(got, tuple) else len(got)
        return {"ok": True, "entries": [], "total": total, "namespace": {}}

    def fetch(self, query, max_results, sort_by="submittedDate", sort_order="descending"):
        self.fetches.append((query, max_results))
        got = self._match(query)
        if isinstance(got, tuple):                      # (the total arXiv reports, the papers that actually came back)
            return list(got[1]), None
        return list(got)[:max_results], None


@pytest.fixture
def env(tmp_path, monkeypatch):
    scout = backfill.load_scout()
    monkeypatch.setattr(scout, "DELAY_BETWEEN_QUERIES", 0)
    papers_dir = tmp_path / "papers"
    lines = []

    def go(results, *flags, argv=None):
        arxiv = Arxiv(scout, results)
        monkeypatch.setattr(scout, "search_arxiv", arxiv.search)
        monkeypatch.setattr(scout, "fetch_arxiv_papers", arxiv.fetch)
        lines.clear()
        rc = backfill.main((argv if argv is not None else WINDOW) + list(flags) + ["--output-dir", str(papers_dir)], scout=scout, today=TODAY, out=lines.append)
        return rc, arxiv, "\n".join(lines)
    return type("Env", (), {"go": staticmethod(go), "dir": papers_dir, "scout": scout})()


def files(root):
    return sorted(str(p.relative_to(root)).replace("\\", "/") for p in root.rglob("*") if p.is_file()) if root.exists() else []


def stats(text):
    return {k: int(v) for k, v in re.findall(r"(\w+)=(\d+)", next(l for l in text.split("\n") if l.startswith("BACKFILL_STATS")))}


FOUR = {"q-bio.GN": [paper("2610.00001"), paper("2610.00002")], "q-bio.CB": [paper("2610.00003")],
        "cs.LG": [paper("2610.00002"), paper("2610.00004", "computer_science")], "q-bio.PE": []}


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
    rc, arxiv, text = env.go(FOUR, "--count-only")
    assert rc == 0 and len(arxiv.searches) == 4 and arxiv.fetches == [] and files(env.dir) == []
    assert all(n == 1 for _, n in arxiv.searches)
    assert stats(text)["matched"] == 5 and stats(text)["fetched"] == 0 and "COUNT ONLY: nothing was fetched or written" in text


def test_a_dry_run_reports_what_would_be_new_and_writes_nothing(env):
    (env.dir / "biology").mkdir(parents=True)
    (env.dir / "biology" / "arxiv_2610.00003.json").write_text('{"kept": true}', encoding="utf-8")
    before = files(env.dir)
    rc, arxiv, text = env.go(FOUR, "--dry-run")
    s = stats(text)
    assert rc == 0 and files(env.dir) == before and "DRY RUN: nothing was written" in text
    assert (s["matched"], s["fetched"], s["duplicates"], s["on_disk"], s["new"], s["saved"]) == (5, 5, 1, 1, 3, 0)
    assert [n for _, n in arxiv.fetches] == [2, 1, 2], "each query is fetched in full: no cap; a query with nothing is not fetched"


def test_write_saves_only_the_new_papers_in_the_scouts_layout_and_never_rewrites_one_on_disk(env):
    (env.dir / "interdisciplinary").mkdir(parents=True)
    kept = env.dir / "interdisciplinary" / "arxiv_2610.00001.json"          # already saved, under another discipline directory
    kept.write_text('{"kept": true}', encoding="utf-8")
    rc, arxiv, text = env.go(FOUR, "--write")
    s = stats(text)
    assert rc == 0 and (s["new"], s["on_disk"], s["duplicates"], s["saved"]) == (3, 1, 1, 3) and "WROTE" in text
    assert files(env.dir) == ["biology/arxiv_2610.00002.json", "biology/arxiv_2610.00003.json", "computer_science/arxiv_2610.00004.json",
                              "interdisciplinary/arxiv_2610.00001.json"]
    assert kept.read_text(encoding="utf-8") == '{"kept": true}', "a paper already on disk is not rewritten"
    assert json.loads((env.dir / "biology" / "arxiv_2610.00002.json").read_text(encoding="utf-8"))["arxiv_id"] == "2610.00002"
    again = env.go(FOUR, "--write")
    assert stats(again[2])["new"] == 0 and stats(again[2])["saved"] == 0 and stats(again[2])["on_disk"] == 4, "a second run writes nothing"


def test_there_is_no_cap_but_a_query_over_the_safety_ceiling_is_refused_not_cut(env):
    many = {"q-bio.GN": [paper(f"2610.{n:05d}") for n in range(1500)], "q-bio.CB": [], "cs.LG": [], "q-bio.PE": []}
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
    short = dict(FOUR, **{"q-bio.GN": (5, [paper("2610.00001"), paper("2610.00002")])})
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
    for call in ("scout.build_arxiv_query(", "scout.search_arxiv(", "scout.fetch_arxiv_papers(", "scout.save_papers("):
        assert call in code, call
    for token in ("requests", "urllib", "export.arxiv.org", "firestore", "google.cloud", "subprocess", "submittedDate:"):
        assert token not in code, f"{token}: the script goes through the scout for that"
    assert "open(" not in code.replace("spec.loader", "") and ".unlink(" not in code and "rmtree" not in code and "write_text" not in code
