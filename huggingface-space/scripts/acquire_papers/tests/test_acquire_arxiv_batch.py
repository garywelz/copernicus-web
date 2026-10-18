"""Unit tests for arXiv acquire failure accounting and SCOUT_STATS."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from xml.etree.ElementTree import ParseError

import pytest

MODULE_PATH = Path(__file__).resolve().parents[1] / "acquire_arxiv_batch.py"


def _load_mod():
    spec = importlib.util.spec_from_file_location("acquire_arxiv_batch", MODULE_PATH)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    sys.modules["acquire_arxiv_batch"] = mod
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture
def arxiv(tmp_path, monkeypatch):
    mod = _load_mod()
    monkeypatch.setattr(mod, "OUTPUT_DIR", tmp_path / "papers")
    monkeypatch.setattr(mod, "DELAY_BETWEEN_QUERIES", 0)
    return mod


def _paper(arxiv_id: str) -> dict:
    return {
        "id": f"arxiv_{arxiv_id}",
        "arxiv_id": arxiv_id,
        "title": f"Paper {arxiv_id}",
        "category": "biology",
        "discipline": "biology",
    }


def test_classify_http_timeout_parse(arxiv):
    class FakeHTTPError(Exception):
        def __init__(self, code):
            self.response = type("R", (), {"status_code": code})()
            super().__init__(f"{code} error")

    if arxiv.REQUESTS_AVAILABLE:
        # Prefer requests.HTTPError shape when available
        import requests

        err = requests.HTTPError("429")
        err.response = type("R", (), {"status_code": 429})()
        assert arxiv.classify_arxiv_exception(err) == "http_429"
        err5 = requests.HTTPError("500")
        err5.response = type("R", (), {"status_code": 503})()
        assert arxiv.classify_arxiv_exception(err5) == "http_5xx"

    assert arxiv.classify_arxiv_exception(TimeoutError("timed out")) == "timeout"
    assert arxiv.classify_arxiv_exception(ParseError("not well-formed")) == "parse"


def test_all_queries_failed_exits_nonzero(arxiv, monkeypatch, capsys):
    def boom(query, max_results, sort_by="submittedDate", sort_order="descending"):
        return [], {"error": "429 Client Error", "error_kind": "http_429"}

    monkeypatch.setattr(arxiv, "fetch_arxiv_papers", boom)
    monkeypatch.setattr(
        arxiv,
        "load_config_queries",
        lambda _p: [
            {"name": "q1", "categories": ["q-bio.GN"], "days_back": 14, "share": 0.5},
            {"name": "q2", "categories": ["q-bio.MN"], "days_back": 14, "share": 0.5},
        ],
    )

    count, stats = arxiv.acquire_recent_papers(10, config_queries_path="dummy.json")
    assert count == 0
    assert stats["queries_attempted"] == 2
    assert stats["queries_failed"] == 2
    assert stats["errors"] == 2
    assert arxiv.all_queries_failed(stats)

    monkeypatch.setattr(
        sys,
        "argv",
        ["acquire_arxiv_batch.py", "--recent", "10", "--classic", "0", "--config-queries", "dummy.json"],
    )
    # Re-bind acquire inside main path by patching the functions main calls
    rc = arxiv.main()
    assert rc == 1
    out = capsys.readouterr().out
    assert "SCOUT_STATS fetched=0" in out
    assert "errors=2" in out
    assert "all 2 arXiv queries failed" in out


def test_partial_fail_exits_zero_and_logs(arxiv, monkeypatch, capsys):
    calls = {"n": 0}

    def mixed(query, max_results, sort_by="submittedDate", sort_order="descending"):
        calls["n"] += 1
        if calls["n"] == 1:
            return [], {"error": "503 Server Error", "error_kind": "http_5xx"}
        return [_paper("2601.00001")], None

    monkeypatch.setattr(arxiv, "fetch_arxiv_papers", mixed)
    monkeypatch.setattr(
        arxiv,
        "load_config_queries",
        lambda _p: [
            {"name": "failing", "categories": ["q-bio.GN"], "days_back": 14, "share": 0.5},
            {"name": "ok", "categories": ["q-bio.MN"], "days_back": 14, "share": 0.5},
        ],
    )

    count, stats = arxiv.acquire_recent_papers(10, config_queries_path="dummy.json")
    assert count == 1
    assert stats["queries_attempted"] == 2
    assert stats["queries_failed"] == 1
    assert stats["errors"] == 1
    assert stats["fetched"] == 1
    assert not arxiv.all_queries_failed(stats)

    monkeypatch.setattr(
        sys,
        "argv",
        ["acquire_arxiv_batch.py", "--recent", "10", "--classic", "0", "--config-queries", "dummy.json"],
    )
    # Reset call counter for main()'s second acquire_recent_papers call
    calls["n"] = 0
    rc = arxiv.main()
    assert rc == 0
    out = capsys.readouterr().out
    assert "Query failures this run:" in out
    assert "WARNING:" in out and "queries failed" in out
    assert "SCOUT_STATS" in out and "errors=1" in out
    assert "fetched=1" in out


def test_success_emits_scout_stats(arxiv, monkeypatch, capsys):
    def ok(query, max_results, sort_by="submittedDate", sort_order="descending"):
        return [_paper("2601.00002"), _paper("2601.00003")], None

    monkeypatch.setattr(arxiv, "fetch_arxiv_papers", ok)
    monkeypatch.setattr(
        arxiv,
        "load_config_queries",
        lambda _p: [
            {"name": "only", "categories": ["q-bio.GN"], "days_back": 14, "share": 1.0},
        ],
    )
    monkeypatch.setattr(
        sys,
        "argv",
        ["acquire_arxiv_batch.py", "--recent", "10", "--classic", "0", "--config-queries", "dummy.json"],
    )
    rc = arxiv.main()
    assert rc == 0
    out = capsys.readouterr().out
    assert "SCOUT_STATS fetched=2 new_json=2 updated_json=0 errors=0" in out
    assert arxiv.all_queries_failed({"queries_attempted": 0, "queries_failed": 0}) is False


def test_search_arxiv_returns_ok_false_on_http_error(arxiv, monkeypatch):
    class Resp:
        status_code = 429
        content = b""

        def raise_for_status(self):
            import requests

            err = requests.HTTPError("429 Client Error")
            err.response = self
            raise err

    if not arxiv.REQUESTS_AVAILABLE:
        pytest.skip("requests not available")

    monkeypatch.setattr(arxiv.requests, "get", lambda *a, **k: Resp())
    result = arxiv.search_arxiv("cat:q-bio.GN", 5)
    assert result["ok"] is False
    assert result["error_kind"] == "http_429"


def test_empty_successful_feed_is_not_a_failure(arxiv, monkeypatch):
    def empty_ok(query, max_results, sort_by="submittedDate", sort_order="descending", start=0):
        return {
            "ok": True,
            "entries": [],
            "total": 0,
            "namespace": {"atom": "http://www.w3.org/2005/Atom"},
        }

    monkeypatch.setattr(arxiv, "search_arxiv", empty_ok)
    papers, err = arxiv.fetch_arxiv_papers("cat:q-bio.GN", 5)
    assert papers == []
    assert err is None
