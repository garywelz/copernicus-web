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


# ---------------------------------------------------------------- the pipeline, with the recordings
# The full topic sentence goes to arXiv (recorded 2026-10-13); the focused queries go to OpenAlex (recorded 2026-10-14), because from Cloud Run
# arXiv refused or timed out on the second and third request in a row and the one paper the focused queries exist to find was lost.
OA = json.loads((Path(__file__).resolve().parents[1] / "fixtures" / "ever_math_openalex.json").read_text(encoding="utf-8"))["responses"]
SENTENCE = "all:" + TOPIC


def pipeline(monkeypatch, openalex=None, arxiv_after_first="refuse", model=True):
    p = rp.ComprehensiveResearchPipeline()
    calls = {"arxiv": [], "openalex": []}

    async def fake_arxiv(params):
        calls["arxiv"].append(params["search_query"])
        if len(calls["arxiv"]) == 1:
            return 200, REC["responses"][SENTENCE], None
        raise AssertionError("arXiv must be asked once, for the full sentence: " + params["search_query"])

    async def fake_openalex(params):
        calls["openalex"].append(params["search"])
        if openalex is not None:
            return openalex(params["search"])
        return 200, OA.get(params["search"], {"results": []})

    async def no_sleep(d):
        return None

    async def replay(system, user):
        return REC["model_reply"]
    monkeypatch.setattr(p, "_arxiv_request", fake_arxiv)
    monkeypatch.setattr(p, "_openalex_request", fake_openalex)
    monkeypatch.setattr(rp.asyncio, "sleep", no_sleep)
    p.query_llm = replay if model else None
    return p, calls


def ids(sources):
    return [re.search(r"abs/(\d{4}\.\d{4,5})", s.url).group(1) for s in sources]


def test_the_full_sentence_alone_misses_the_mathlib_network_paper(monkeypatch):
    """The defect: arXiv's top 15 for the whole topic sentence does not contain 2604.24797."""
    p, calls = pipeline(monkeypatch)
    monkeypatch.setattr(p, "FOCUSED_QUERIES", False)
    out = run(p._search_arxiv(TOPIC, "comprehensive"))
    assert len(out) == 15 and TARGET not in ids(out) and calls == {"arxiv": [SENTENCE], "openalex": []}


def test_the_ever_math_topic_retrieves_arxiv_2604_24797_among_the_first_twelve(monkeypatch):
    p, calls = pipeline(monkeypatch)
    out = run(p._search_arxiv(TOPIC, "comprehensive"))
    got = ids(out)
    assert TARGET in got and got.index(TARGET) < 12 and got[0] == TARGET        # the paper confirmation keeps at most 12
    target = next(s for s in out if TARGET in s.url)
    assert target.title == "The Network Structure of Mathlib" and target.confirm_via == "datacite" and target.doi == "10.48550/arXiv." + TARGET
    assert calls["arxiv"] == [SENTENCE]                                          # arXiv is asked once; its limits no longer matter to the focused queries
    assert calls["openalex"] == ["mathlib metamath network", "mathlib dependency graph", "metamath dependency network"]
    assert len(got) == len(set(got)) <= 20                                       # no duplicates (OpenAlex lists the paper twice), bounded


def test_the_focused_papers_are_confirmed_through_datacite_not_arxiv():
    import paper_confirmation as pcf
    target = next(w for w in OA["mathlib dependency graph"]["results"] if "2604.24797" in (w.get("doi") or ""))
    p = rp.ComprehensiveResearchPipeline()
    src = run(_one_openalex_source(p, target))
    assert src.confirm_via == "datacite" and src.url == "https://arxiv.org/abs/2604.24797" and pcf is not None


async def _one_openalex_source(p, work):
    async def fake_openalex(params):
        return 200, {"results": [work]}
    p._openalex_request = fake_openalex
    return (await p._search_openalex_arxiv("mathlib dependency graph", "comprehensive", per_page=10))[0]


def test_arxiv_rate_limiting_after_the_first_request_is_irrelevant_to_the_focused_queries(monkeypatch):
    p, calls = pipeline(monkeypatch)             # fake_arxiv raises if it is asked twice, so reaching the end proves it was not
    assert TARGET in ids(run(p._search_arxiv(TOPIC, "comprehensive")))


def test_a_model_outage_still_runs_the_deterministic_fallback_queries_through_openalex(monkeypatch):
    feed = OA["mathlib dependency graph"]
    p, calls = pipeline(monkeypatch, openalex=lambda search: (200, feed) if "mathlib" in search else (200, {"results": []}), model=False)
    out = run(p._search_arxiv(TOPIC, "comprehensive"))
    assert calls["openalex"] == ["proof dependency graphs", "formal mathematics libraries", "network structure mathlib"] and TARGET in ids(out)


def test_focused_hits_that_repeat_the_sentence_results_are_not_duplicated(monkeypatch):
    sentence_ids = ids(run(_sentence_only(monkeypatch)))
    results = [{"id": "w", "doi": "https://doi.org/10.48550/arxiv." + i, "title": "T " + i, "publication_year": 2020,
                "authorships": [], "abstract_inverted_index": {"x": [0]}} for i in sentence_ids]
    p, calls = pipeline(monkeypatch, openalex=lambda search: (200, {"results": results}))
    out = run(p._search_arxiv(TOPIC, "comprehensive"))
    assert len(ids(out)) == 15 == len(set(ids(out)))


async def _sentence_only(monkeypatch):
    p, calls = pipeline(monkeypatch)
    monkeypatch.setattr(p, "FOCUSED_QUERIES", False)
    return await p._search_arxiv(TOPIC, "comprehensive")


def test_if_openalex_refuses_a_focused_query_the_rest_are_skipped_but_the_sentence_results_stay(monkeypatch):
    p, calls = pipeline(monkeypatch, openalex=lambda search: (503, None))
    out = run(p._search_arxiv(TOPIC, "comprehensive"))
    assert len(out) == 15 and TARGET not in ids(out)
    assert len(calls["openalex"]) == 3                                           # the first query's three attempts (2 s and 4 s waits), then stop


def test_a_failure_of_the_sentence_query_still_means_the_openalex_fallback_then_registry_unavailable(monkeypatch):
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
