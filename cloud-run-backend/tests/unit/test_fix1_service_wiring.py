"""Service wiring for gap 3 fix 1 stage 2. The service module needs psutil, which is absent in some environments;
a stub is installed for the import only. Skipped if the module cannot be imported at all."""
import asyncio
import sys
from unittest.mock import MagicMock

import pytest

try:
    import psutil  # noqa: F401
except ImportError:
    sys.modules["psutil"] = MagicMock()
try:
    import services.podcast_generation_service as svc
except Exception as e:  # pragma: no cover - environment without the service's dependencies
    pytest.skip(f"service module not importable here: {e}", allow_module_level=True)

import paper_confirmation as pc
import podcast_research_integrator as pri
from models.podcast import PodcastRequest


def run(coro):
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


class _Stop(Exception):
    pass


def _confirmed(pid="P1", title="Registry Title Of The Requested Paper", venue="Registry Journal"):
    return pc.ConfirmedPaper(pid=pid, title=title, authors=["Ada Lovelace", "Alan Turing"], year=2025, venue=venue,
                             ids={"arxiv": None, "arxiv_version": None, "pmid": None, "doi": "10.1000/x1"},
                             url="https://doi.org/10.1000/x1", abstract="Registry abstract.", registry="crossref",
                             confirmed_at="2026-10-08T00:00:00Z", title_match=1.0)


def test_research_failure_types_cover_the_new_exceptions():
    names = {c.__name__ for c in (pc.InsufficientConfirmedPapers, pc.RegistryUnavailable, pc.PaperNotConfirmed)}
    assert set(svc.RESEARCH_FAILURE_TYPES) == names
    assert len(set(svc.RESEARCH_FAILURE_TYPES.values())) == 3


def test_requested_paper_venue_line_comes_from_the_confirmed_record_and_nothing_is_injected(monkeypatch):
    captured = {}

    def fake_prompt(self, **kw):
        captured.update(kw)
        raise _Stop()
    monkeypatch.setattr(pri.PodcastResearchIntegrator, "build_2_speaker_research_prompt", fake_prompt)
    req = PodcastRequest(topic="t", paper_title="Request Title", paper_doi="10.1000/x1", paper_journal="Wrong Journal From Request",
                         paper_authors=["Someone Else"], paper_year="1999")
    conf = _confirmed()
    sources = [pc.as_research_source(conf)]
    ctx = pri.PodcastResearchContext(
        topic="t", research_sources=sources, paper_analyses=[], paradigm_shifts=[], interdisciplinary_connections=[],
        key_findings=[], real_citations=[], research_quality_score=5.0, recommended_expertise_level="intermediate",
        confirmed_papers=[conf], dropped_candidates=[], requested_pid="P1")
    service = svc.PodcastGenerationService()
    with pytest.raises(_Stop):
        run(service.generate_content_from_research_context(req, ctx, "fake-key"))
    cite = captured["source_paper_citation"]
    assert "Registry Journal" in cite and "Registry Title Of The Requested Paper" in cite and "(2025)" in cite
    assert "Wrong Journal" not in cite and "Someone Else" not in cite and "1999" not in cite
    assert "[P1]" in captured["additional_instructions"] and "Wrong Journal" not in captured["additional_instructions"]
    assert ctx.research_sources == sources and len(ctx.research_sources) == 1  # no injected duplicate


# ---------------------------------------------------------------- C5: the generate-and-check loop
import json

import named_work_check as nw


def _ctx():
    conf = [pc.ConfirmedPaper(pid="P1", title="Analytical engines and the first algorithms", authors=["Ada Lovelace", "Alan Turing"], year=2025,
                              venue=None, ids={"arxiv": None, "arxiv_version": None, "pmid": None, "doi": "10.1/p1"}, url="https://doi.org/10.1/p1",
                              abstract="Abs.", registry="crossref", confirmed_at="t", title_match=1.0)]
    return pri.PodcastResearchContext(
        topic="t", research_sources=[pc.as_research_source(c) for c in conf], paper_analyses=[], paradigm_shifts=[],
        interdisciplinary_connections=[], key_findings=[], real_citations=[], research_quality_score=5.0,
        recommended_expertise_level="intermediate", confirmed_papers=conf, dropped_candidates=[], requested_pid=None)


def _script(extra, request):
    return ("word " * (svc.calculate_minimum_words_for_duration(request.duration) + 10)) + extra


def _harness(monkeypatch, scripts, short_first=False):
    """A service whose generator returns the scripted texts in order, and whose naming model finds a mention for
    'Lovelace' (listed) and 'Zorblatt' (not listed). Returns (service, request, calls)."""
    calls = {"gen": 0, "feedback": []}
    request = PodcastRequest(topic="t")
    service = svc.PodcastGenerationService()

    async def fake_generate(req, ctx, key, retry_attempt=0, naming_feedback=""):
        calls["feedback"].append(naming_feedback)
        text = scripts[min(calls["gen"], len(scripts) - 1)]
        calls["gen"] += 1
        return {"title": "T", "script": text, "description": "Body."}
    monkeypatch.setattr(service, "generate_content_from_research_context", fake_generate)

    async def llm(system, user):
        ms = []
        if "Lovelace" in user:
            ms.append({"quote": "Lovelace and Turing showed", "authors": ["Lovelace", "Turing"], "year": 2025, "title_words": []})
        if "Zorblatt" in user:
            ms.append({"quote": "Zorblatt and Quux showed", "authors": ["Zorblatt", "Quux"], "year": 2019, "title_words": []})
        return json.dumps({"mentions": ms})
    monkeypatch.setattr(svc, "make_gemini_llm_call", lambda key: llm)

    async def no_sleep(*a, **k):
        return None
    monkeypatch.setattr(svc.asyncio, "sleep", no_sleep)
    return service, request, calls


def test_clean_script_is_accepted_first_time(monkeypatch):
    req = PodcastRequest(topic="t")
    service, req, calls = _harness(monkeypatch, [_script(" Lovelace and Turing showed it. The link is in the description.", req)])
    content, result, attempts = run(service._generate_checked_content(req, _ctx(), "k", "job1"))
    assert calls["gen"] == 1 and result.passed and result.named_pids == ["P1"] and len(attempts) == 1
    assert calls["feedback"] == [""]


def test_violation_triggers_regeneration_with_feedback_then_passes(monkeypatch):
    req = PodcastRequest(topic="t")
    bad = _script(" Zorblatt and Quux showed it.", req)
    good = _script(" Lovelace and Turing showed it.", req)
    service, req, calls = _harness(monkeypatch, [bad, good])
    content, result, attempts = run(service._generate_checked_content(req, _ctx(), "k", "job1"))
    assert calls["gen"] == 2 and content["script"] == good and result.passed
    assert calls["feedback"][0] == "" and "Zorblatt" in calls["feedback"][1] and "ONLY these papers" in calls["feedback"][1]
    assert [a["passed"] for a in attempts] == [False, True]


def test_three_bad_scripts_fail_the_episode_and_nothing_is_returned(monkeypatch):
    req = PodcastRequest(topic="t")
    bad = _script(" Zorblatt and Quux showed it.", req)
    service, req, calls = _harness(monkeypatch, [bad, bad, bad])
    with pytest.raises(nw.NamingViolationError) as e:
        run(service._generate_checked_content(req, _ctx(), "k", "job1"))
    assert calls["gen"] == 3 and "Zorblatt" in str(e.value) and "no episode was published" in str(e.value)


def test_too_short_then_violation_then_clean_uses_the_shared_budget(monkeypatch):
    req = PodcastRequest(topic="t")
    short = "too short"
    bad = _script(" Zorblatt and Quux showed it.", req)
    good = _script(" Lovelace and Turing showed it.", req)
    service, req, calls = _harness(monkeypatch, [short, bad, good])
    content, result, attempts = run(service._generate_checked_content(req, _ctx(), "k", "job1"))
    assert calls["gen"] == 3 and content["script"] == good


def test_short_last_attempt_is_still_checked(monkeypatch):
    req = PodcastRequest(topic="t")
    short_bad = "Zorblatt and Quux showed it."
    service, req, calls = _harness(monkeypatch, [short_bad, short_bad, short_bad])
    with pytest.raises(nw.NamingViolationError):
        run(service._generate_checked_content(req, _ctx(), "k", "job1"))


def test_check_unavailable_fails_closed_after_retries(monkeypatch):
    req = PodcastRequest(topic="t")
    good = _script(" Lovelace and Turing showed it.", req)
    service, req, calls = _harness(monkeypatch, [good])

    async def broken(system, user):
        raise RuntimeError("model down")
    monkeypatch.setattr(svc, "make_gemini_llm_call", lambda key: broken)
    with pytest.raises(nw.NamingCheckUnavailable):
        run(service._generate_checked_content(req, _ctx(), "k", "job1"))
    assert calls["gen"] == 3  # each attempt generated, none could be accepted


def test_legacy_reference_fallbacks_are_gone_from_the_service():
    import inspect
    src = inspect.getsource(svc)
    assert "real_citations" not in src                       # no model-era or template reference lists are stored or read
    assert src.count("ensure_source_paper_reference") == 1  # imported only; the call that added the request-based reference is gone
    assert "References missing in upload_description_to_gcs" not in src and "LLM did not include References section" not in src
    assert "apply_reference_sections(" in src and "confirmed_papers" in src


def test_episode_document_carries_the_confirmed_papers_fields():
    from services.episode_service import EpisodeService
    doc = EpisodeService._prepare_episode_document(
        "job1", None, {"topic": "t"},
        {"title": "T", "script": "s", "description": "d", "papers": [{"pid": "P1"}], "papers_named": ["P1"], "references_built_by": "code@1"},
        {}, {}, False, None)
    assert doc["papers"] == [{"pid": "P1"}] and doc["papers_named"] == ["P1"] and doc["references_built_by"] == "code@1"
