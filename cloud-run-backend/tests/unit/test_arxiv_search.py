"""arXiv search must retry and then fail as 'registry unavailable' (never carry on with only the other sources)."""
import asyncio

import pytest

import paper_confirmation as pc
import research_pipeline as rp

ATOM = ('<?xml version="1.0"?><feed xmlns="http://www.w3.org/2005/Atom">{entries}</feed>')
ENTRY = ('<entry><id>http://arxiv.org/abs/2601.00001v1</id><title>A paper on proofs</title><summary>About proofs.</summary>'
         '<published>2026-01-01T00:00:00Z</published><author><name>A B</name></author>'
         '<link href="http://arxiv.org/abs/2601.00001v1" rel="alternate"/></entry>')


def run(coro):
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


def pipeline(monkeypatch, replies):
    """replies: list of (status, text, retry_after) or an Exception to raise, consumed in order. Returns (pipeline, sleeps, calls)."""
    p = rp.ComprehensiveResearchPipeline()
    sleeps, calls = [], []
    queue = list(replies)

    async def fake_request(params):
        calls.append(params)
        r = queue.pop(0)
        if isinstance(r, Exception):
            raise r
        return r

    async def fake_sleep(d):
        sleeps.append(d)
    async def openalex_down(params):  # the OpenAlex fallback (stage d) is down too, and no test may reach the real service
        return 503, None
    monkeypatch.setattr(p, "_arxiv_request", fake_request)
    monkeypatch.setattr(p, "_openalex_request", openalex_down)
    monkeypatch.setattr(rp.asyncio, "sleep", fake_sleep)
    return p, sleeps, calls


def test_a_429_then_a_200_succeeds_after_waiting(monkeypatch):
    p, sleeps, calls = pipeline(monkeypatch, [(429, "", None), (429, "", None), (200, ATOM.format(entries=ENTRY), None)])
    out = run(p._search_arxiv("proofs", "comprehensive"))
    assert len(out) == 1 and out[0].title == "A paper on proofs" and sleeps == [3.0, 6.0] and len(calls) == 3


def test_every_attempt_failing_raises_registry_unavailable(monkeypatch):
    p, sleeps, calls = pipeline(monkeypatch, [(429, "", None)] * 4)
    with pytest.raises(pc.RegistryUnavailable) as e:
        run(p._search_arxiv("proofs", "comprehensive"))
    assert e.value.registries == ["arxiv", "openalex"] and sleeps == [3.0, 6.0, 12.0, 2.0, 4.0] and len(calls) == 4   # arXiv 4 tries, then OpenAlex 3


def test_other_statuses_and_network_errors_are_retried_too(monkeypatch):
    p, sleeps, calls = pipeline(monkeypatch, [(503, "", None), asyncio.TimeoutError(), ConnectionError("dns"), (200, ATOM.format(entries=ENTRY), None)])
    assert len(run(p._search_arxiv("proofs", "comprehensive"))) == 1 and len(calls) == 4


def test_retry_after_lengthens_the_wait_but_is_capped(monkeypatch):
    p, sleeps, _ = pipeline(monkeypatch, [(429, "", "10"), (429, "", "999"), (429, "", "bad"), (200, ATOM.format(entries=ENTRY), None)])
    run(p._search_arxiv("proofs", "comprehensive"))
    assert sleeps == [10.0, 30.0, 12.0]


def test_a_200_with_no_entries_is_a_real_empty_result_and_is_not_retried(monkeypatch):
    p, sleeps, calls = pipeline(monkeypatch, [(200, ATOM.format(entries=""), None)])
    assert run(p._search_arxiv("proofs", "comprehensive")) == [] and sleeps == [] and len(calls) == 1


def test_each_attempt_is_logged_with_status_and_retry_after(monkeypatch, capsys):
    p, _, _ = pipeline(monkeypatch, [(429, "", "7"), (200, ATOM.format(entries=ENTRY), None)])
    run(p._search_arxiv("proofs", "comprehensive"))
    out = capsys.readouterr().out
    assert "arxiv_search attempt=1/4 status=429 retry_after=7" in out and "arxiv_search attempt=2/4 status=200" in out


def test_comprehensive_search_fails_when_arxiv_is_unavailable_but_tolerates_other_sources_failing(monkeypatch):
    p, _, _ = pipeline(monkeypatch, [(429, "", None)] * 4)

    async def boom(*a, **k):
        raise RuntimeError("zenodo down")

    async def empty(*a, **k):
        return []
    for name in ("_search_pubmed", "_search_biorxiv", "_search_core", "_search_youtube"):
        monkeypatch.setattr(p, name, empty)
    monkeypatch.setattr(p, "_search_zenodo", boom)
    with pytest.raises(pc.RegistryUnavailable):
        run(p.comprehensive_search("proofs"))


def test_comprehensive_search_continues_when_a_non_arxiv_source_fails(monkeypatch):
    p, _, _ = pipeline(monkeypatch, [(200, ATOM.format(entries=ENTRY), None)])

    async def boom(*a, **k):
        raise RuntimeError("zenodo down")

    async def empty(*a, **k):
        return []
    for name in ("_search_pubmed", "_search_biorxiv", "_search_core", "_search_youtube"):
        monkeypatch.setattr(p, name, empty)
    monkeypatch.setattr(p, "_search_zenodo", boom)
    out = run(p.comprehensive_search("proofs"))
    assert [s.title for s in out] == ["A paper on proofs"]


def test_category_queries_use_real_spaces_and_general_math_has_no_filter():
    q = rp.ComprehensiveResearchPipeline._arxiv_search_query("number theory of primes", "math.NT")
    assert q == "cat:math.NT AND (number theory of primes)" and "+" not in q
    p = rp.ComprehensiveResearchPipeline()
    topic = "Proof dependency graphs in formal mathematics libraries: mathlib and Metamath"
    assert p._map_to_arxiv_category(topic) == ""                    # 'math' is not an arXiv category
    assert rp.ComprehensiveResearchPipeline._arxiv_search_query(topic, "").startswith("all:Proof dependency")
    assert p._map_to_arxiv_category("quantum error correction") == "quant-ph"
