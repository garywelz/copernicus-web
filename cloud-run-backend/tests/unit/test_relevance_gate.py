"""Relevance gate (fix 1b, stage b): offline, embeddings are faked."""
import asyncio
import sys
from types import SimpleNamespace as NS
from unittest.mock import MagicMock

import pytest

try:
    import psutil  # noqa: F401
except ImportError:
    sys.modules["psutil"] = MagicMock()

import paper_confirmation as pc
import relevance_gate as rg


def run(coro):
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


def paper(pid, title="A paper", doi=None, abstract="abstract text", arxiv=None):
    return NS(pid=pid, title=title, abstract=abstract, ids={"doi": doi, "arxiv": arxiv, "pmid": None, "arxiv_version": None})


# ---------------------------------------------------------------- scoring
def test_cosine_basics():
    assert rg.cosine([1, 0], [1, 0]) == 1.0 and rg.cosine([1, 0], [0, 1]) == 0.0 and rg.cosine([0, 0], [1, 1]) == 0.0


def test_scores_are_cosine_to_the_topic_and_embedded_in_one_call():
    calls = []

    def embed(texts):
        calls.append(list(texts))
        return [[1.0, 0.0], [1.0, 0.0], [0.6, 0.8]]
    scores = run(rg.relevance_scores("the topic", [paper("P1"), paper("P2")], embed))
    assert scores == {"P1": 1.0, "P2": 0.6} and len(calls) == 1 and calls[0][0] == "the topic" and calls[0][1].startswith("A paper. abstract text")


def test_a_failing_embedding_is_retried_once_then_fails_closed():
    n = {"calls": 0}

    def embed(texts):
        n["calls"] += 1
        raise RuntimeError("quota")
    with pytest.raises(rg.RelevanceCheckUnavailable):
        run(rg.relevance_scores("t", [paper("P1")], embed))
    assert n["calls"] == 2
    n["calls"] = 0

    def flaky(texts):
        n["calls"] += 1
        if n["calls"] == 1:
            raise RuntimeError("blip")
        return [[1.0, 0.0], [1.0, 0.0]]
    assert run(rg.relevance_scores("t", [paper("P1")], flaky)) == {"P1": 1.0}


def test_a_wrong_number_of_vectors_fails_closed():
    with pytest.raises(rg.RelevanceCheckUnavailable):
        run(rg.relevance_scores("t", [paper("P1"), paper("P2")], lambda texts: [[1.0, 0.0]]))


# ---------------------------------------------------------------- the threshold
def test_the_threshold_is_0_25_and_the_boundary_is_kept():
    assert rg.RELEVANCE_THRESHOLD == 0.25
    ps = [paper("P1"), paper("P2"), paper("P3")]
    kept, dropped = rg.apply_gate(ps, {"P1": 0.2499, "P2": 0.25, "P3": 0.9})
    assert [p.pid for p in kept] == ["P2", "P3"] and [(d.reason, d.score) for d in dropped] == [("off_topic", 0.2499)]


def test_a_directly_requested_paper_is_exempt():
    kept, dropped = rg.apply_gate([paper("P1"), paper("P2")], {"P1": 0.01, "P2": 0.01}, exempt_pids=["P1"])
    assert [p.pid for p in kept] == ["P1"] and len(dropped) == 1


# ---------------------------------------------------------------- the real first-generation case, with the measured scores
def test_the_ever_math_260007_papers_would_have_been_dropped():
    zen = "10.5281/zenodo."
    ps = [paper(f"P{i}", doi=f"{zen}{i}") for i in range(1, 6)]
    scores = dict(zip(["P1", "P2", "P3", "P4", "P5"], [0.174, 0.137, 0.306, 0.101, 0.171]))   # measured 2026-10-13
    kept, dropped = rg.apply_gate(ps, scores)
    assert [p.pid for p in kept] == ["P3"] and len(dropped) == 4
    assert rg.outside_zenodo(kept) == 0                                                         # and none counts toward the minimum


def test_zenodo_papers_do_not_count_toward_the_minimum():
    ps = [paper("P1", doi="10.5281/zenodo.1"), paper("P2", doi="10.5281/ZENODO.2"), paper("P3", arxiv="2601.00001"),
          paper("P4", doi="10.1000/journal.1")]
    assert rg.outside_zenodo(ps) == 2 and rg.is_zenodo(ps[1]) and not rg.is_zenodo(ps[2])


# ---------------------------------------------------------------- inside the integrator (every outside call faked)
def integrator(monkeypatch, confirmed, embed):
    import podcast_research_integrator as pri

    it = pri.PodcastResearchIntegrator("fake-key", embed_batch=embed)
    cs = []
    for c in confirmed:
        cs.append(pc.ConfirmedPaper(pid=c["pid"], title=c["title"], authors=["A B"], year=2026, venue=c.get("venue"),
                                    ids={"arxiv": c.get("arxiv"), "arxiv_version": "v1" if c.get("arxiv") else None, "pmid": None, "doi": c.get("doi")},
                                    url="https://x/" + c["pid"], abstract="About " + c["title"], registry=c.get("registry", "arxiv"),
                                    confirmed_at="t", title_match=1.0))

    async def fake_confirm(sources, required_first=None):
        return pc.ConfirmationResult(confirmed=list(cs), dropped=[], stats={})

    async def fake_search(**kw):
        return [NS(title=c.title, url=c.url, doi=c.ids["doi"], publication_date="2026", source="arxiv", authors=["A B"], abstract="x", journal=None, pid=None) for c in cs]

    class A:
        def __init__(self, title):
            self.title, self.analysis_failed, self.significance = title, False, "high"
            self.interdisciplinary_connections, self.key_findings, self.technical_complexity = [], [f"f {title}"], "low"

    async def fake_multi(srcs, complexity=None):
        return [A(s.title) for s in srcs]

    class G:
        significance, interdisciplinary_connections, key_findings = [], [], ["g"]
        analysis_failed = False

    async def fake_gemini(paper, options, key):
        return G()
    monkeypatch.setattr(pri, "confirm_sources", fake_confirm)
    monkeypatch.setattr(it.research_pipeline, "comprehensive_search", fake_search)
    monkeypatch.setattr(it.enhanced_research_service, "analyze_multiple_papers", fake_multi)
    monkeypatch.setattr(pri, "analyze_paper_with_gemini", fake_gemini)
    return it


def vectors():
    """embed(texts): the topic first, then one vector per paper chosen by a keyword in its text."""
    def embed(texts):
        out = [[1.0, 0.0]]
        for t in texts[1:]:
            out.append([1.0, 0.0] if "relevant" in t else [0.0, 1.0])
        return out
    return embed


def test_off_topic_papers_are_dropped_and_the_scores_are_kept(monkeypatch):
    papers = [dict(pid=f"P{i}", title="relevant paper %d" % i, arxiv="2601.0000%d" % i) for i in range(1, 5)] + [dict(pid="P5", title="garment design", arxiv="2601.00005")]
    ctx = run(integrator(monkeypatch, papers, vectors()).comprehensive_research_for_podcast("graphs"))
    assert [c.pid for c in ctx.confirmed_papers] == ["P1", "P2", "P3", "P4"]
    assert [(d.reason, d.score) for d in ctx.dropped_candidates] == [("off_topic", 0.0)] and ctx.relevance_scores["P5"] == 0.0 and ctx.relevance_scores["P1"] == 1.0


def test_too_few_relevant_papers_fails_with_the_off_topic_count(monkeypatch):
    papers = [dict(pid="P1", title="relevant a", arxiv="2601.00001"), dict(pid="P2", title="relevant b", arxiv="2601.00002")] + \
             [dict(pid=f"P{i}", title="garment %d" % i, arxiv="2601.0000%d" % i) for i in range(3, 7)]
    with pytest.raises(pc.InsufficientConfirmedPapers) as e:
        run(integrator(monkeypatch, papers, vectors()).comprehensive_research_for_podcast("graphs"))
    assert e.value.confirmed == 2 and e.value.drop_counts == {"off_topic": 4} and all(d["reason"] == "off_topic" and "score" in d for d in e.value.dropped)


def test_three_relevant_zenodo_records_are_not_enough(monkeypatch):
    papers = [dict(pid=f"P{i}", title="relevant zenodo %d" % i, doi="10.5281/zenodo.%d" % i, registry="datacite") for i in range(1, 4)] + \
             [dict(pid="P4", title="relevant arxiv", arxiv="2601.00004")]
    with pytest.raises(pc.InsufficientConfirmedPapers) as e:
        run(integrator(monkeypatch, papers, vectors()).comprehensive_research_for_podcast("graphs"))
    assert e.value.outside_zenodo == 1 and "Zenodo records do not count" in str(e.value)


def test_three_relevant_non_zenodo_papers_pass_even_with_zenodo_extras(monkeypatch):
    papers = [dict(pid=f"P{i}", title="relevant arxiv %d" % i, arxiv="2601.0000%d" % i) for i in range(1, 4)] + \
             [dict(pid="P4", title="relevant zenodo", doi="10.5281/zenodo.4", registry="datacite")]
    ctx = run(integrator(monkeypatch, papers, vectors()).comprehensive_research_for_podcast("graphs"))
    assert len(ctx.confirmed_papers) == 4


def test_a_broken_embedding_service_fails_the_episode(monkeypatch):
    def boom(texts):
        raise RuntimeError("no key")
    papers = [dict(pid=f"P{i}", title="relevant %d" % i, arxiv="2601.0000%d" % i) for i in range(1, 4)]
    with pytest.raises(rg.RelevanceCheckUnavailable):
        run(integrator(monkeypatch, papers, boom).comprehensive_research_for_podcast("graphs"))


# ---------------------------------------------------------------- what the requester is told
def test_failure_messages_for_the_new_cases():
    from failure_notice import describe_failure
    none = describe_failure(pc.InsufficientConfirmedPapers("t", 0, 0, 3, {}))["summary"]
    assert none.startswith("No research sources were found for this topic.") and "only 0" not in none and "We found 0" not in none
    off = describe_failure(pc.InsufficientConfirmedPapers("t", 8, 2, 3, {"off_topic": 6}))["summary"]
    assert "6 of them were not about the topic" in off and "only 2 remained" in off
    zen = describe_failure(pc.InsufficientConfirmedPapers("t", 8, 4, 3, {}, outside_zenodo=1))["summary"]
    assert "only 1 of them are published papers from arXiv, PubMed or Crossref" in zen and "Zenodo records do not count" in zen
    plain = describe_failure(pc.InsufficientConfirmedPapers("t", 9, 2, 3, {"no_identifier": 5}))["summary"]
    assert "9 possible research sources" in plain and "only 2 could be confirmed" in plain
    chk = describe_failure(rg.RelevanceCheckUnavailable("RuntimeError: key"))
    assert chk["kind"] == "relevance_check_unavailable" and "key" not in chk["summary"]
