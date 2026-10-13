"""Focused arXiv queries (fix 4, stage i). Offline: the model and arXiv are replayed from a recording made on 2026-10-13 (real Gemini reply
and real arXiv responses for the ever-math topic; summaries cut to 350 characters)."""
import asyncio
import json
import re
from pathlib import Path

import pytest

import paper_confirmation as pc
import research_pipeline as rp
import search_queries as sq

REC = json.loads((Path(__file__).resolve().parents[1] / "fixtures" / "ever_math_arxiv.json").read_text(encoding="utf-8"))
TOPIC = REC["topic"]
TARGET = "2604.24797"          # "The Network Structure of Mathlib"
EMPTY_FEED = '<?xml version="1.0"?><feed xmlns="http://www.w3.org/2005/Atom"></feed>'


def run(coro):
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


# ---------------------------------------------------------------- the query helpers
def test_topic_terms_drop_stop_and_generic_words():
    terms = sq.topic_terms(TOPIC)
    assert terms[:3] == ["proof", "dependency", "graphs"] and "mathlib" in terms and "metamath" in terms
    assert not {"what", "the", "of", "reveals", "built", "how", "about", "and", "in"} & set(terms)
    assert sq.topic_terms("") == [] and sq.topic_terms("the of and") == []


def test_the_fallback_builds_deterministic_queries_from_the_topic_words():
    q = sq.fallback_queries(TOPIC)
    assert q == ["all:proof AND all:dependency AND all:graphs", "all:formal AND all:mathematics AND all:libraries",
                 "all:network AND all:structure AND all:mathlib"]
    assert sq.fallback_queries("cells") == [] and len(sq.fallback_queries("alpha beta gamma delta epsilon zeta eta theta iota kappa lambda mu")) == 3


def test_only_well_formed_queries_are_accepted():
    good = ["all:mathlib AND all:dependency AND all:graph", "all:Metamath AND all:network", "ti:mathlib AND abs:network"]
    assert sq.valid_queries(good) == good
    bad = ["all:mathlib", "all:a AND all:b AND all:c AND all:d", "all:mathlib OR all:network", "all:proof-dependency AND all:network",
           "mathlib AND network", "all:mathlib AND all:x; rm -rf", 'all:"phrase here" AND all:network', "", None, 7, "cat:math AND all:network"]
    assert sq.valid_queries(bad) == []
    assert sq.valid_queries(["all:a1 AND all:b2"] * 2 + good) == ["all:a1 AND all:b2"] + good[:2]          # de-duplicated, at most three


def test_terms_and_lexical_score():
    terms = sq.query_terms(["all:mathlib AND all:Metamath AND all:network", "all:mathlib AND all:dependency AND all:graph"])
    assert terms == ["mathlib", "metamath", "network", "dependency", "graph"]
    assert sq.lexical_score("The Network Structure of Mathlib", "We study mathlib.", terms) == 2 * 2 + 1
    assert sq.lexical_score("Music and mathematics", "Nothing relevant here.", terms) == 0
    assert sq.lexical_score("Networks", "", terms) == 0                                                        # whole words only


def test_the_model_reply_recorded_for_the_ever_math_topic_gives_three_valid_queries():
    async def replay(system, user):
        assert TOPIC in user and "ONE plain word" in user
        return REC["model_reply"]
    qs = run(sq.focused_queries(TOPIC, replay))
    assert qs == ["all:mathlib AND all:Metamath AND all:network", "all:mathlib AND all:dependency AND all:graph", "all:Metamath AND all:dependency AND all:network"]


def test_a_failing_or_useless_model_falls_back_to_the_topic_words():
    async def boom(system, user):
        raise RuntimeError("quota")

    async def garbage(system, user):
        return "I cannot help."

    async def hyphens(system, user):
        return json.dumps({"queries": ["all:proof-dependency AND all:network-structure"]})
    for llm in (boom, garbage, hyphens, None):
        assert run(sq.focused_queries(TOPIC, llm)) == sq.fallback_queries(TOPIC)


# ---------------------------------------------------------------- the pipeline, with the recording
def pipeline(monkeypatch, responder, model=True):
    p = rp.ComprehensiveResearchPipeline()
    calls, sleeps = [], []

    async def fake_request(params):
        calls.append(params["search_query"])
        return 200, responder(params["search_query"]), None

    async def fake_sleep(d):
        sleeps.append(d)

    async def replay(system, user):
        return REC["model_reply"]
    monkeypatch.setattr(p, "_arxiv_request", fake_request)
    monkeypatch.setattr(rp.asyncio, "sleep", fake_sleep)
    p.query_llm = replay if model else None
    return p, calls, sleeps


def recorded(q):
    return REC["responses"].get(q, EMPTY_FEED)


def ids(sources):
    return [re.search(r"abs/(\d{4}\.\d{4,5})", s.url).group(1) for s in sources]


def test_the_full_sentence_alone_misses_the_mathlib_network_paper(monkeypatch):
    """The defect: arXiv's top 15 for the whole topic sentence does not contain 2604.24797."""
    p, calls, _ = pipeline(monkeypatch, recorded)
    monkeypatch.setattr(p, "FOCUSED_QUERIES", False)
    out = run(p._search_arxiv(TOPIC, "comprehensive"))
    assert len(out) == 15 and TARGET not in ids(out) and calls == ["all:" + TOPIC]


def test_the_ever_math_topic_retrieves_arxiv_2604_24797_among_the_first_twelve(monkeypatch):
    p, calls, sleeps = pipeline(monkeypatch, recorded)
    out = run(p._search_arxiv(TOPIC, "comprehensive"))
    got = ids(out)
    assert TARGET in got and got.index(TARGET) < 12              # the paper confirmation keeps at most 12
    assert next(s for s in out if TARGET in s.url).title == "The Network Structure of Mathlib"
    assert calls[0] == "all:" + TOPIC and calls[1:] == sq.valid_queries(json.loads(REC["model_reply"])["queries"])
    assert sleeps == [3.0, 3.0, 3.0]                              # one request per three seconds
    assert len(got) == len(set(got)) <= 20                        # no duplicates, bounded
    assert got[0] == TARGET                                        # the best match for the distinctive terms comes first


def test_a_model_outage_still_runs_the_deterministic_fallback_queries(monkeypatch):
    feed = recorded("all:mathlib AND all:dependency AND all:graph")
    head = re.search(r"<feed[^>]*>", feed).group(0)                                  # keeps the namespaces the entries use
    target_entry = next(e for e in re.findall(r"<entry>.*?</entry>", feed, re.S) if TARGET in e)
    p, calls, _ = pipeline(monkeypatch, lambda q: '<?xml version="1.0"?>' + head + target_entry + "</feed>"
                           if "all:network AND all:structure AND all:mathlib" in q else recorded(q), model=False)
    out = run(p._search_arxiv(TOPIC, "comprehensive"))
    assert calls[1:] == sq.fallback_queries(TOPIC) and TARGET in ids(out)


def test_focused_hits_that_repeat_the_sentence_results_are_not_duplicated(monkeypatch):
    p, calls, _ = pipeline(monkeypatch, lambda q: recorded("all:" + TOPIC))                       # every query returns the same 15 papers
    out = run(p._search_arxiv(TOPIC, "comprehensive"))
    assert len(ids(out)) == 15 == len(set(ids(out)))


def test_if_arxiv_refuses_a_focused_query_the_rest_are_skipped_but_the_sentence_results_stay(monkeypatch):
    p = rp.ComprehensiveResearchPipeline()
    sleeps = []
    calls = []

    async def fake_request(params):
        calls.append(params["search_query"])
        return (200, recorded(params["search_query"]), None) if len(calls) == 1 else (429, "", None)

    async def fake_sleep(d):
        sleeps.append(d)

    async def replay(system, user):
        return REC["model_reply"]
    monkeypatch.setattr(p, "_arxiv_request", fake_request)
    monkeypatch.setattr(rp.asyncio, "sleep", fake_sleep)
    p.query_llm = replay
    out = run(p._search_arxiv(TOPIC, "comprehensive"))
    assert len(out) == 15 and TARGET not in ids(out)
    assert len(calls) == 1 + 4                                     # the sentence once, then the first focused query's four attempts, then stop


def test_a_failure_of_the_sentence_query_still_means_registry_unavailable(monkeypatch):
    p = rp.ComprehensiveResearchPipeline()

    async def down(params):
        return 429, "", None

    async def openalex_down(params):
        return 503, None

    async def no_sleep(d):
        return None
    monkeypatch.setattr(p, "_arxiv_request", down)
    monkeypatch.setattr(p, "_openalex_request", openalex_down)
    monkeypatch.setattr(rp.asyncio, "sleep", no_sleep)
    with pytest.raises(pc.RegistryUnavailable):
        run(p._search_arxiv(TOPIC, "comprehensive"))


def test_the_integrator_gives_the_pipeline_a_model_for_the_queries_only_when_it_has_a_key():
    import podcast_research_integrator as pri
    assert pri.PodcastResearchIntegrator("a-key").research_pipeline.query_llm is not None
    assert pri.PodcastResearchIntegrator("").research_pipeline.query_llm is None
