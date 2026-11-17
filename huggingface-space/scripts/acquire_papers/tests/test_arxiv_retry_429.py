"""The arXiv scout waits and tries again when arXiv answers HTTP 429.

On 2026-11-15 the evening run asked four queries within seconds, arXiv answered 429 to each, and the run fetched
nothing. A 429 is a request to slow down, so the scout now waits and retries: a few attempts with growing waits,
the wait arXiv names in Retry-After when it sends one, and a cap on the waiting of a whole run. No test here
calls arXiv or sleeps: the fetch and the sleep are replaced.
"""

from __future__ import annotations

import importlib.util
import sys
from datetime import datetime, timezone
from pathlib import Path

import pytest

MODULE_PATH = Path(__file__).resolve().parents[1] / "acquire_arxiv_batch.py"
FEED = (b'<feed xmlns="http://www.w3.org/2005/Atom" xmlns:opensearch="http://a9.com/-/spec/opensearch/1.1/">'
        b"<opensearch:totalResults>1</opensearch:totalResults><entry><id>http://arxiv.org/abs/2611.00001v1</id></entry></feed>")


def _load_mod():
    spec = importlib.util.spec_from_file_location("acquire_arxiv_batch_retry", MODULE_PATH)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    sys.modules["acquire_arxiv_batch_retry"] = mod
    spec.loader.exec_module(mod)
    return mod


class Net:
    """Answers in order: bytes are returned, an exception is raised. Records every call and every sleep."""

    def __init__(self, mod, answers):
        self.mod, self.answers, self.calls, self.slept = mod, list(answers), [], []

    def fetch(self, url):
        self.calls.append(url)
        answer = self.answers.pop(0) if self.answers else FEED
        if isinstance(answer, BaseException):
            raise answer
        return answer

    def refused(self, retry_after=None, status=429):
        headers = {} if retry_after is None else {"Retry-After": retry_after}
        response = type("Response", (), {"status_code": status, "headers": headers})()
        error = self.mod.requests.HTTPError(f"{status} Client Error")
        error.response = response
        return error


@pytest.fixture
def scout(monkeypatch):
    mod = _load_mod()
    assert mod.REQUESTS_AVAILABLE
    mod.reset_retry_budget()
    net = Net(mod, [])
    monkeypatch.setattr(mod, "_fetch", net.fetch)
    monkeypatch.setattr(mod, "_sleep", net.slept.append)
    return mod, net


def test_one_refusal_is_retried_after_a_wait_and_the_query_succeeds(scout):
    mod, net = scout
    net.answers = [net.refused(), FEED]
    out = mod.search_arxiv("cat:q-bio.GN", 10)
    assert out["ok"] is True and out["total"] == 1 and len(out["entries"]) == 1
    assert len(net.calls) == 2 and net.calls[0] == net.calls[1] and net.slept == [20.0]


def test_the_waits_grow_and_the_attempts_are_limited(scout):
    mod, net = scout
    net.answers = [net.refused(), net.refused(), net.refused(), FEED]
    assert mod.search_arxiv("cat:q-bio.GN", 10)["ok"] is True
    assert net.slept == [20.0, 60.0, 120.0] and len(net.calls) == 4
    mod.reset_retry_budget()
    net.calls.clear()
    net.slept.clear()
    net.answers = [net.refused()] * 5
    out = mod.search_arxiv("cat:q-bio.GN", 10)
    assert out["ok"] is False and out["error_kind"] == "http_429"            # still a failure when arXiv keeps refusing
    assert len(net.calls) == 4 and net.slept == [20.0, 60.0, 120.0]          # one try and three retries, never more


def test_a_retry_after_header_is_honoured_in_seconds_and_as_a_date(scout):
    mod, net = scout
    net.answers = [net.refused(retry_after="90"), FEED]
    assert mod.search_arxiv("q", 10)["ok"] is True and net.slept == [90.0]   # longer than our own first wait: arXiv's is used
    mod.reset_retry_budget()
    net.slept.clear()
    net.answers = [net.refused(retry_after="5"), FEED]
    assert mod.search_arxiv("q", 10)["ok"] is True and net.slept == [20.0]   # never less than our own wait
    now = datetime(2026, 11, 16, 1, 10, 0, tzinfo=timezone.utc)
    assert mod.retry_after_seconds(net.refused(retry_after="Mon, 16 Nov 2026 01:11:30 GMT"), now=now) == 90.0
    assert mod.retry_after_seconds(net.refused(retry_after="Mon, 16 Nov 2026 01:00:00 GMT"), now=now) == 0.0
    assert mod.retry_after_seconds(net.refused(retry_after="soon"), now=now) is None
    assert mod.retry_after_seconds(net.refused(), now=now) is None


def test_a_retry_after_longer_than_the_limit_is_not_waited_for(scout):
    mod, net = scout
    net.answers = [net.refused(retry_after="3600"), FEED]
    out = mod.search_arxiv("q", 10)
    assert out["ok"] is False and out["error_kind"] == "http_429" and net.slept == [] and len(net.calls) == 1


@pytest.mark.parametrize("status,kind", [(500, "http_5xx"), (503, "http_5xx"), (400, "http_400")])
def test_only_a_429_is_retried(scout, status, kind):
    mod, net = scout
    net.answers = [net.refused(status=status), FEED]
    out = mod.search_arxiv("q", 10)
    assert out["ok"] is False and out["error_kind"] == kind and net.slept == [] and len(net.calls) == 1
    mod.reset_retry_budget()
    net.calls.clear()
    net.answers = [TimeoutError("timed out"), FEED]
    assert mod.search_arxiv("q", 10)["error_kind"] == "timeout" and net.slept == [] and len(net.calls) == 1


def test_four_queries_each_refused_once_all_succeed(scout):
    """The run of 2026-11-15: every query refused once. Before, all four failed; now all four are answered."""
    mod, net = scout
    net.answers = [net.refused(), FEED, net.refused(), FEED, net.refused(), FEED, net.refused(), FEED]
    results = [mod.search_arxiv(f"query {n}", 10) for n in range(4)]
    assert [r["ok"] for r in results] == [True] * 4 and net.slept == [20.0] * 4 and len(net.calls) == 8


def test_the_waiting_of_a_whole_run_is_capped_so_the_scout_ends_before_the_ingest(scout):
    mod, net = scout
    assert sum(mod.RETRY_429_WAITS) <= mod.RETRY_429_BUDGET <= 270          # 20:10:05 start + a normal run + the budget is before 20:15
    net.answers = [net.refused()] * 20
    first = mod.search_arxiv("query 0", 10)
    assert first["ok"] is False and net.slept == [20.0, 60.0, 120.0]          # 200 of the 240 seconds
    second = mod.search_arxiv("query 1", 10)
    assert second["ok"] is False and net.slept == [20.0, 60.0, 120.0, 20.0]   # one more 20-second wait fits; the 60-second one does not
    third = mod.search_arxiv("query 2", 10)
    assert third["ok"] is False and sum(net.slept) == 240.0                   # a last 20-second wait fits exactly; then the budget is spent
    fourth = mod.search_arxiv("query 3", 10)
    assert fourth["ok"] is False and sum(net.slept) == 240.0                  # a refusal now fails at once, with no wait
    assert len(net.calls) == 4 + 2 + 2 + 1
    mod.reset_retry_budget()
    net.answers = [net.refused(), FEED]
    assert mod.search_arxiv("query 3", 10)["ok"] is True


def test_the_file_still_parses_as_python_3_8():
    """The Jetson runs the scout under Python 3.8."""
    import ast
    ast.parse(MODULE_PATH.read_text(encoding="utf-8"), feature_version=(3, 8))
