"""The curated mode inside the generation code (design §3.1): the research stage that replaces discovery, the prompt, the generate-and-check
loop, the final check, the Sources section, the entry point, and that nothing here can publish. Offline: every model call is faked.
The service module needs psutil, which is absent in some environments; a stub is installed for the import only."""
import ast
import asyncio
import json
import os
import sys
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

try:
    import psutil  # noqa: F401
except ImportError:
    sys.modules["psutil"] = MagicMock()
try:
    import services.podcast_generation_service as svc
except Exception as e:  # pragma: no cover
    pytest.skip(f"service module not importable here: {e}", allow_module_level=True)

import curated_checks as cc
import curated_mode as cm
import curated_sources as cs
import paper_confirmation as pc
import podcast_research_integrator as pri
from models.podcast import PodcastRequest
from tests.unit.test_curated_mode import (PIN, ETH_PATH, approved_doc, base_items, commentary_item, registry_item, release_item)

BACKEND = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def run(coro):
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


def curated_run(items=None, **kw):
    return cm.CuratedRun.from_list_doc(approved_doc(items or base_items()), **kw)


def analysis(title, failed=False):
    from enhanced_research_service import PaperAnalysis
    return PaperAnalysis(title=title, summary="s", key_findings=[f"finding of {title}"], methodology="m", implications="i", related_work="r",
                         technical_complexity="medium", suggested_questions=[], keywords=[], significance=f"it matters ({title})",
                         interdisciplinary_connections=["a link"], practical_applications=[], future_research_directions=[], analysis_failed=failed)


def context(run=None):
    run = run or curated_run()
    conf = run.confirmed_papers()
    papers = [c for c in conf if c.source_class != cs.COMMENTARY]
    return pri.PodcastResearchContext(
        topic=run.topic, research_sources=[pc.as_research_source(c) for c in papers], paper_analyses=[], significance=[], interdisciplinary_connections=[],
        key_findings=[], real_citations=[], research_quality_score=5.0, recommended_expertise_level="intermediate", confirmed_papers=conf,
        dropped_candidates=[], requested_pid=None, curated=run)


# --- the research stage that replaces discovery ----------------------------------------------------------------------------------------
def integrator(analyses=None, gemini_fails=False, gemini_failed_analysis=False):
    it = pri.PodcastResearchIntegrator("fake-key")

    async def analyze(sources, complexity="intermediate"):
        return analyses if analyses is not None else [analysis(s.title) for s in sources]

    async def gemini(paper, options, key):
        if gemini_fails:
            raise RuntimeError("model down")
        return SimpleNamespace(significance=["deep note"], interdisciplinary_connections=[], key_findings=["deep finding"], analysis_failed=gemini_failed_analysis)

    def never(*a, **k):
        raise AssertionError("discovery must not run in the curated mode")
    it.enhanced_research_service.analyze_multiple_papers = analyze
    it.research_pipeline.comprehensive_search = never
    return it, gemini


def test_the_curated_stage_analyses_the_approved_sources_and_never_discovers_or_confirms():
    it, gemini = integrator()
    with patch.object(pri, "analyze_paper_with_gemini", gemini), patch.object(pri, "confirm_sources", side_effect=AssertionError("no confirmation")):
        ctx = run(it.curated_research_for_podcast(curated_run()))
    assert ctx.curated is not None and [c.pid for c in ctx.confirmed_papers] == ["P1", "P2", "P3"] and len(ctx.research_sources) == 3
    assert ctx.dropped_candidates == [] and ctx.requested_pid is None and ctx.topic == "OpenAI mathematics release"
    assert any("deep finding" in f for f in ctx.key_findings) and ctx.significance
    assert all(s.pid in ("P1", "P2", "P3") for s in ctx.research_sources)


def test_commentary_stays_in_the_confirmed_list_but_is_not_analysed_as_a_paper():
    it, gemini = integrator()
    with patch.object(pri, "analyze_paper_with_gemini", gemini):
        ctx = run(it.curated_research_for_podcast(curated_run(base_items() + [commentary_item()])))
    assert [c.pid for c in ctx.confirmed_papers] == ["P1", "P2", "P3", "P4"] and len(ctx.research_sources) == 3
    assert ctx.confirmed_papers[3].source_class == cs.COMMENTARY


def test_an_analysis_that_cannot_be_read_stops_the_run_rather_than_dropping_an_approved_source():
    titles = [i["title"] for i in base_items()]
    it, gemini = integrator(analyses=[analysis(titles[0]), analysis(titles[1], failed=True), analysis(titles[2])])
    with patch.object(pri, "analyze_paper_with_gemini", gemini):
        with pytest.raises(pri.CuratedAnalysisFailed) as e:
            run(it.curated_research_for_podcast(curated_run()))
    assert e.value.pids == ["P2"] and "CuratedAnalysisFailed" not in svc.RESEARCH_FAILURE_TYPES      # the ordinary table keeps its three entries
    it2, gemini2 = integrator(gemini_failed_analysis=True)
    with patch.object(pri, "analyze_paper_with_gemini", gemini2):
        with pytest.raises(pri.CuratedAnalysisFailed):
            run(it2.curated_research_for_podcast(curated_run()))


def test_a_deep_analysis_that_errors_is_a_supplement_that_is_skipped_as_in_the_ordinary_mode():
    it, gemini = integrator(gemini_fails=True)
    with patch.object(pri, "analyze_paper_with_gemini", gemini):
        ctx = run(it.curated_research_for_podcast(curated_run()))
    assert len(ctx.confirmed_papers) == 3 and not any("deep finding" in f for f in ctx.key_findings)


# --- the prompt -------------------------------------------------------------------------------------------------------------------------
class _Stop(Exception):
    pass


def captured_prompt_call(monkeypatch, ctx):
    got = {}

    def fake(self, **kw):
        got.update(kw)
        raise _Stop()
    monkeypatch.setattr(pri.PodcastResearchIntegrator, "build_2_speaker_research_prompt", fake)
    with pytest.raises(_Stop):
        run(svc.PodcastGenerationService().generate_content_from_research_context(PodcastRequest(topic="t"), ctx, "k"))
    return got


def test_the_curated_block_and_neutral_labels_reach_the_prompt_only_in_this_mode(monkeypatch):
    got = captured_prompt_call(monkeypatch, context())
    assert got["neutral_labels"] is True and cm.CHANNEL in got["additional_instructions"] and "[P3] (company release)" in got["additional_instructions"]
    plain = pri.PodcastResearchContext(topic="t", research_sources=[], paper_analyses=[], significance=[], interdisciplinary_connections=[],
                                       key_findings=[], real_citations=[], research_quality_score=5.0, recommended_expertise_level="intermediate")
    got2 = captured_prompt_call(monkeypatch, plain)
    assert got2["neutral_labels"] is False and "CURATED SOURCES MODE" not in got2["additional_instructions"]


def test_the_real_prompt_uses_host_and_expert_labels_when_asked_and_the_voice_names_otherwise():
    it = pri.PodcastResearchIntegrator("fake-key")
    ctx = context()
    neutral = it.build_2_speaker_research_prompt(ctx, "15-20 minutes", "interview", neutral_labels=True)
    assert 'Use ONLY "HOST:" and "EXPERT:" as speaker labels' in neutral and "MATILDA" not in neutral and "ADAM" not in neutral
    assert "Matilda" not in neutral and "Adam" not in neutral        # not even in the "Voice:" lines
    default = it.build_2_speaker_research_prompt(ctx, "15-20 minutes", "interview")
    assert 'Use ONLY "MATILDA:" and "ADAM:" as speaker labels' in default


# --- the generate-and-check loop --------------------------------------------------------------------------------------------------------
def harness(monkeypatch, scripts):
    calls = {"gen": 0, "feedback": []}
    service = svc.PodcastGenerationService()

    async def fake_generate(req, ctx, key, retry_attempt=0, naming_feedback=""):
        calls["feedback"].append(naming_feedback)
        text = scripts[min(calls["gen"], len(scripts) - 1)]
        calls["gen"] += 1
        return {"title": "T", "script": text, "description": "Body."}
    monkeypatch.setattr(service, "generate_content_from_research_context", fake_generate)

    async def llm(system, user):
        return json.dumps({"attributions": []}) if ("PAPERS:" in user and "SCRIPT:" in user) else json.dumps({"mentions": []})
    monkeypatch.setattr(svc, "make_gemini_llm_call", lambda key: llm)

    async def no_sleep(*a, **k):
        return None
    monkeypatch.setattr(svc.asyncio, "sleep", no_sleep)
    return service, PodcastRequest(topic="t"), calls


def padded(extra, request=None):
    request = request or PodcastRequest(topic="t")
    return ("word " * (svc.calculate_minimum_words_for_duration(request.duration) + 10)) + extra


CLEAN = ("EXPERT: This is a company release that has not been peer reviewed: The Exponential Time Hypothesis is False. "
         "It is OpenAI's own manuscript, not independently checked. A second work, a preprint, is also in the list.")
BAD = "EXPERT: The exponential time hypothesis disproof was formally verified. Also, hello, I'm Matilda."


def test_a_clean_curated_script_passes_first_time_with_the_curated_checks_recorded(monkeypatch):
    service, req, calls = harness(monkeypatch, [padded(CLEAN)])
    content, naming, attempts = run(service._generate_checked_content(req, context(), "k", "job1"))
    assert calls["gen"] == 1 and attempts[0]["curated_checks"] == {} and naming.passed


def test_a_curated_violation_regenerates_with_feedback_and_then_passes(monkeypatch):
    service, req, calls = harness(monkeypatch, [padded(BAD), padded(CLEAN)])
    content, naming, attempts = run(service._generate_checked_content(req, context(), "k", "job2"))
    assert calls["gen"] == 2 and attempts[0]["curated_checks"] and attempts[1]["curated_checks"] == {}
    assert "REJECTED" in calls["feedback"][1] and "formally verified" in calls["feedback"][1] and "HOST and EXPERT" in calls["feedback"][1]
    assert any(r["check"] == "status_wording" for r in service._last_rejections) and any(r["check"] == "spoken_name" for r in service._last_rejections)


def test_a_curated_violation_that_never_clears_fails_the_episode_after_four_attempts(monkeypatch):
    service, req, calls = harness(monkeypatch, [padded(BAD)])
    with pytest.raises(cc.CuratedCheckError) as e:
        run(service._generate_checked_content(req, context(), "k", "job3"))
    assert calls["gen"] == 4 and {v["kind"] for v in e.value.violations} >= {"forbidden_term", "spoken_name"}


def test_the_ordinary_mode_is_untouched_by_all_of_this(monkeypatch):
    service, req, calls = harness(monkeypatch, [padded(BAD)])
    plain = context()
    plain.curated = None                     # the same words, but no curated run: no curated check can fire
    content, naming, attempts = run(service._generate_checked_content(req, plain, "k", "job4"))
    assert calls["gen"] == 1 and "curated_checks" in attempts[0] and attempts[0]["curated_checks"] == {}


# --- the final check, on the text that is stored and spoken ------------------------------------------------------------------------------
def final_content(script):
    return {"title": "T", "script": script, "description": "Body.", "papers_named": []}


def test_the_final_text_is_checked_again_and_a_violation_fails_the_episode(monkeypatch):
    service, req, calls = harness(monkeypatch, [padded(CLEAN)])
    run(service._verify_final_text(final_content(padded(CLEAN)), req, context(), "k", "job5"))            # clean: passes
    with pytest.raises(cc.CuratedCheckError):
        run(service._verify_final_text(final_content(padded(BAD)), req, context(), "k", "job6"))
    plain = context()
    plain.curated = None
    run(service._verify_final_text(final_content(padded(BAD)), req, plain, "k", "job7"))                    # ordinary: no curated checks


# --- the Sources section and the record ------------------------------------------------------------------------------------------------
def finalize(ctx, named):
    content = {"title": "A title that is long enough", "script": "EXPERT: Text.", "description": "Intro.\n\n## References\n\n- invented line\n"}
    service = svc.PodcastGenerationService()
    metrics = service._finalize_content(content, PodcastRequest(topic="t"), ctx, SimpleNamespace(named_pids=named))
    return content, metrics


def test_the_curated_description_carries_the_code_built_sources_and_code_at_3():
    content, _ = finalize(context(), ["P1", "P3"])
    d = content["description"]
    assert "## References" in d and "invented line" not in d and "[company release, not peer reviewed; status: unverified]" in d and "[peer reviewed]" in d
    assert content["references_built_by"] == "code@3" and "## Sources" not in d


def test_the_ordinary_description_is_still_built_the_old_way():
    plain = context()
    plain.curated = None
    content, _ = finalize(plain, ["P1"])
    assert "## References" in content["description"] and "[peer reviewed]" not in content["description"] and content["references_built_by"] == svc.REFERENCES_BUILT_BY


def test_eleven_named_sources_fit_in_the_description_with_every_class_label_intact():
    items = [release_item(title=f"Manuscript number {n} about topic {n}", path=f"preprints/Dir-{n}-October-1-2026", family=f"{300 + n}") for n in range(1, 10)]
    items += [registry_item(cs.PEER_REVIEWED, 1), registry_item(cs.PREPRINT, 2, registry="arxiv")]
    run_ = cm.CuratedRun.from_list_doc(approved_doc(items))
    conf = run_.confirmed_papers()
    content = {"title": "A title that is long enough", "script": "EXPERT: Text.",
               "description": ("Intro paragraph. " * 140) + "\n\n## Hashtags\n#math #ai"}
    ctx = SimpleNamespace(curated=run_, confirmed_papers=conf, requested_pid=None)
    metrics = svc.PodcastGenerationService()._finalize_content(content, PodcastRequest(topic="t"), ctx, SimpleNamespace(named_pids=[c.pid for c in conf]))
    d = content["description"]
    assert len(d) <= 4000 and d.count("[company release, not peer reviewed; status: unverified]") == 9
    assert "[peer reviewed]" in d and "[preprint, not peer reviewed]" in d and "## Hashtags" in d and "...." not in d
    assert metrics["body_chars_removed_by_limit"] >= 0


# --- the entry point ---------------------------------------------------------------------------------------------------------------------
def test_a_list_that_cannot_be_used_marks_the_job_failed_and_generates_nothing():
    updates = {}

    class Ref:
        def update(self, data):
            updates.update(data)

    class DB:
        def collection(self, name):
            return self

        def document(self, doc_id):
            return Ref()
    service = svc.PodcastGenerationService()
    called = []

    async def fake_job(*a, **k):
        called.append(1)
    service.run_podcast_generation_job = fake_job
    with patch.object(svc, "db", DB()):
        run(service.run_curated_generation_job("j1", approved_doc(base_items(), status="draft"), PodcastRequest(topic="t")))
    assert called == [] and updates["status"] == "failed" and updates["error_type"] == "curated_list_invalid" and "not approved" in updates["error"]


def test_a_usable_list_runs_the_ordinary_job_with_the_curated_run():
    service = svc.PodcastGenerationService()
    seen = {}

    async def fake_job(job_id, request, subscriber_id=None, curated_run=None):
        seen.update(job_id=job_id, topic=request.topic, subscriber_id=subscriber_id, run=curated_run)
    service.run_podcast_generation_job = fake_job
    run(service.run_curated_generation_job("j2", approved_doc(base_items()), PodcastRequest(topic="Episode one"), subscriber_id="admin-id"))
    assert seen["job_id"] == "j2" and seen["topic"] == "Episode one" and seen["subscriber_id"] == "admin-id"
    assert isinstance(seen["run"], cm.CuratedRun) and seen["run"].topic == "Episode one"


# --- nothing here can publish ------------------------------------------------------------------------------------------------------------
PUBLISHING_NAMES = {"promote", "demote", "update_rss_feed", "submit_podcast_to_rss", "rss_service", "update_episode_submission_state", "make_public"}


@pytest.mark.parametrize("rel", ["curated_mode.py", "curated_checks.py", "curated_sources.py", os.path.join("endpoints", "curated", "routes.py")])
def test_the_curated_modules_never_name_anything_that_publishes(rel):
    tree = ast.parse(open(os.path.join(BACKEND, rel), encoding="utf-8").read())
    names = {n.id for n in ast.walk(tree) if isinstance(n, ast.Name)} | {n.attr for n in ast.walk(tree) if isinstance(n, ast.Attribute)}
    assert not (names & PUBLISHING_NAMES)


def test_the_curated_job_is_private_by_construction():
    src = open(os.path.join(BACKEND, "services", "podcast_generation_service.py"), encoding="utf-8").read()
    assert "submitted_to_rss=False" in src and '"media_state": "private"' in src
    routes_src = open(os.path.join(BACKEND, "endpoints", "curated", "routes.py"), encoding="utf-8").read()
    assert "'submitted_to_rss': False" in routes_src and '"published": False' in routes_src


# --- the job itself: the curated stage is the one that runs ---------------------------------------------------------------------------------
def test_the_job_runs_the_curated_research_stage_and_never_discovery(monkeypatch):
    updates = []

    class Ref:
        def update(self, data):
            updates.append(dict(data))

    class DB:
        def collection(self, name):
            return self

        def document(self, doc_id):
            return Ref()

    called = {"curated": 0, "discovery": 0}

    class FakeIntegrator:
        def __init__(self, key, *a, **k):
            pass

        async def curated_research_for_podcast(self, run_, level):
            called["curated"] += 1
            assert isinstance(run_, cm.CuratedRun) and level == "intermediate"
            raise pri.CuratedAnalysisFailed(["P2"])

        async def comprehensive_research_for_podcast(self, **kw):
            called["discovery"] += 1
            raise AssertionError("discovery must not run for a curated job")

    notified = []

    async def notify(exc, job_id, topic, email):
        notified.append(type(exc).__name__)
    service = svc.PodcastGenerationService()
    service._notify_failure = notify
    monkeypatch.setattr(svc, "db", DB())
    monkeypatch.setattr(svc, "PodcastResearchIntegrator", FakeIntegrator)
    monkeypatch.setattr(svc, "get_google_api_key", lambda: "k")
    monkeypatch.setattr(svc.psutil, "virtual_memory", lambda: SimpleNamespace(percent=10.0))      # the stub psutil would return a mock
    run_ = curated_run()
    run(service.run_podcast_generation_job("job-x", PodcastRequest(topic="t"), subscriber_id=None, curated_run=run_))
    assert called == {"curated": 1, "discovery": 0} and notified == ["CuratedAnalysisFailed"]
    failed = [u for u in updates if u.get("status") == "failed"]
    assert failed and failed[0]["error_type"] == "curated_analysis_failed"


def test_the_ordinary_job_still_runs_discovery(monkeypatch):
    class Ref:
        def update(self, data):
            pass

    class DB:
        def collection(self, name):
            return self

        def document(self, doc_id):
            return Ref()

    called = {"curated": 0, "discovery": 0}

    class FakeIntegrator:
        def __init__(self, key, *a, **k):
            pass

        async def curated_research_for_podcast(self, run_, level):
            called["curated"] += 1
            raise AssertionError("not a curated job")

        async def comprehensive_research_for_podcast(self, **kw):
            called["discovery"] += 1
            raise pc.RegistryUnavailable(["crossref"])

    async def notify(*a, **k):
        return None
    service = svc.PodcastGenerationService()
    service._notify_failure = notify
    monkeypatch.setattr(svc, "db", DB())
    monkeypatch.setattr(svc, "PodcastResearchIntegrator", FakeIntegrator)
    monkeypatch.setattr(svc, "get_google_api_key", lambda: "k")
    monkeypatch.setattr(svc.psutil, "virtual_memory", lambda: SimpleNamespace(percent=10.0))      # the stub psutil would return a mock
    run(service.run_podcast_generation_job("job-y", PodcastRequest(topic="t")))
    assert called == {"curated": 0, "discovery": 1}
