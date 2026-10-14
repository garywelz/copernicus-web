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
        topic="t", research_sources=sources, paper_analyses=[], significance=[], interdisciplinary_connections=[],
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
        topic="t", research_sources=[pc.as_research_source(c) for c in conf], paper_analyses=[], significance=[],
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
        if isinstance(text, Exception):          # a model error: the generator's reply was not JSON, or the call timed out
            raise text
        return {"title": "T", "script": text, "description": "Body."}
    monkeypatch.setattr(service, "generate_content_from_research_context", fake_generate)

    calls["attr"] = []   # what the attribution model reports (a list of {quote, pid, verdict, reason}); one list per call, last one repeats
    calls["attr_calls"] = 0

    async def llm(system, user):
        if "PAPERS:" in user and "SCRIPT:" in user:     # the attribution check (fix 4 b)
            seq = calls["attr"]
            calls["attr_calls"] += 1
            items = seq[min(calls["attr_calls"] - 1, len(seq) - 1)] if seq else []
            return json.dumps({"attributions": items})
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
    assert calls["gen"] == 4 and "Zorblatt" in str(e.value) and "no episode was published" in str(e.value)


def test_too_short_then_violation_then_clean_uses_the_shared_budget(monkeypatch):
    req = PodcastRequest(topic="t")
    short = "too short"
    bad = _script(" Zorblatt and Quux showed it.", req)
    good = _script(" Lovelace and Turing showed it.", req)
    service, req, calls = _harness(monkeypatch, [short, bad, good])
    content, result, attempts = run(service._generate_checked_content(req, _ctx(), "k", "job1"))
    assert calls["gen"] == 3 and content["script"] == good


def test_a_script_that_stays_short_fails_and_is_never_kept(monkeypatch):
    req = PodcastRequest(topic="t")
    short_bad = "Zorblatt and Quux showed it."
    service, req, calls = _harness(monkeypatch, [short_bad, short_bad, short_bad])
    with pytest.raises(ScriptTooShortError) as e:
        run(service._generate_checked_content(req, _ctx(), "k", "job1"))
    assert calls["gen"] == 4 and "under the minimum of 600" in str(e.value) and "no episode was published" in str(e.value)
    assert "too short" in calls["feedback"][1] and "minimum is 600 words" in calls["feedback"][1] and "Do not pad" in calls["feedback"][1]


def test_check_unavailable_fails_closed_after_retries(monkeypatch):
    req = PodcastRequest(topic="t")
    good = _script(" Lovelace and Turing showed it.", req)
    service, req, calls = _harness(monkeypatch, [good])

    async def broken(system, user):
        raise RuntimeError("model down")
    monkeypatch.setattr(svc, "make_gemini_llm_call", lambda key: broken)
    with pytest.raises(nw.NamingCheckUnavailable):
        run(service._generate_checked_content(req, _ctx(), "k", "job1"))
    assert calls["gen"] == 1  # the unreadable check was repeated on the same script (3 more times), then the episode failed; nothing was regenerated


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

# ---------------------------------------------------------------- gap 3 fix 1: notation that cannot be read aloud
from speech_text import UnspeakableNotationError

_BS = chr(92)


def test_unknown_notation_is_regenerated_with_feedback_then_accepted(monkeypatch):
    req = PodcastRequest(topic="t")
    bad = _script(" Lovelace and Turing showed $" + _BS + "oint F$.", req)
    good = _script(" Lovelace and Turing showed it.", req)
    service, req, calls = _harness(monkeypatch, [bad, good])
    content, result, attempts = run(service._generate_checked_content(req, _ctx(), "k", "job1"))
    assert calls["gen"] == 2 and attempts[0]["unspeakable_notation"] and "oint" in calls["feedback"][1]
    assert "plain words" in calls["feedback"][1] and attempts[1]["unspeakable_notation"] == [] and "oint" not in content["script"]


def test_unknown_notation_that_never_clears_fails_the_episode(monkeypatch):
    req = PodcastRequest(topic="t")
    bad = _script(" Lovelace and Turing showed $" + _BS + "oint F$.", req)
    service, req, calls = _harness(monkeypatch, [bad, bad, bad])
    with pytest.raises(UnspeakableNotationError):
        run(service._generate_checked_content(req, _ctx(), "k", "job1"))
    assert calls["gen"] == 4


def test_convertible_notation_passes_the_gate_and_is_spoken_at_finalize(monkeypatch):
    from named_work_check import NamingResult
    req = PodcastRequest(topic="t")
    text = _script(" Lovelace and Turing showed $D_s^+ " + _BS + "to K_S^0 K_L^0 " + _BS + "pi^+$.", req)
    service, req, calls = _harness(monkeypatch, [text])
    content, result, attempts = run(service._generate_checked_content(req, _ctx(), "k", "job1"))
    assert calls["gen"] == 1
    content["description"] = "Overview of $K_S^0$ decays." + chr(10)*2 + "## Hashtags" + chr(10) + "#a" + chr(10)
    service._finalize_content(content, req, _ctx(), NamingResult(named_pids=["P1"]))
    assert "D sub s plus to K short K long pi plus" in content["script"] and "$" not in content["script"]
    assert content["description"].startswith("Overview of K short decays.")


# ---------------------------------------------------------------- the description fallback must be publishable
def _fallback_context(findings, shifts=None, directions=None):
    from types import SimpleNamespace as NS
    analysis = NS(future_research_directions=directions or [])
    source = NS(title="A paper about chaos", authors=["A B", "C D"], journal=None, source="arxiv", doi=None,
                url="https://arxiv.org/abs/2601.00001v1", publication_date="2026-01-01")
    return NS(topic="Chaos Theory", key_findings=findings, significance=shifts or [], paper_analyses=[analysis],
              research_sources=[source])


@pytest.mark.parametrize("findings,shifts,directions", [
    (["Neural signals are not Gaussian.", "Orthonormal bases cut redundancy."], ["[P1] Chaos as design principle: high"], ["Test on larger graphs."]),
    ([], [], []),
    (["Research findings require further analysis"], [], []),  # placeholder findings are filtered out, template text is used
])
def test_the_description_fallback_passes_the_pre_publish_gate(findings, shifts, directions):
    from content_fixes import validate_description_before_publish
    desc = svc.PodcastGenerationService._build_fallback_description(_fallback_context(findings, shifts, directions))
    validate_description_before_publish(desc)  # raises if the gate would refuse it
    assert "## Key Concepts Explored" in desc and "## References" in desc
    assert "significant advancement in our understanding" not in desc
    if findings and "require further" not in findings[0]:
        assert findings[0] in desc


# ---------------------------------------------------------------- fix 4 (a): banned wording is a reason to regenerate
from script_style import BannedPhraseError

HYPE = " Lovelace and Turing showed it, and this is a truly revolutionary, unprecedented paradigm shift."


def test_banned_wording_triggers_regeneration_with_the_sentence_quoted_back(monkeypatch):
    req = PodcastRequest(topic="t")
    bad, good = _script(HYPE, req), _script(" Lovelace and Turing showed it.", req)
    service, req, calls = _harness(monkeypatch, [bad, good])
    content, result, attempts = run(service._generate_checked_content(req, _ctx(), "k", "job1"))
    assert calls["gen"] == 2 and content["script"] == good
    assert "truly revolutionary, unprecedented paradigm shift" in calls["feedback"][1] and "overstated or promotional" in calls["feedback"][1]
    assert sorted(h["phrase"] for h in attempts[0]["banned_phrases"]) == ["paradigm shift", "revolutionary", "unprecedented"] and attempts[1]["banned_phrases"] == []


def test_wording_that_never_clears_fails_the_episode(monkeypatch):
    req = PodcastRequest(topic="t")
    bad = _script(HYPE, req)
    service, req, calls = _harness(monkeypatch, [bad, bad, bad])
    with pytest.raises(BannedPhraseError) as e:
        run(service._generate_checked_content(req, _ctx(), "k", "job1"))
    assert calls["gen"] == 4 and "no episode was published" in str(e.value)


def test_banned_wording_in_the_description_counts_too(monkeypatch):
    req = PodcastRequest(topic="t")
    clean = _script(" Lovelace and Turing showed it.", req)
    service, req, calls = _harness(monkeypatch, [clean])
    seen = {"n": 0}

    async def fake_generate(req_, ctx, key, retry_attempt=0, naming_feedback=""):
        calls["feedback"].append(naming_feedback)
        seen["n"] += 1
        return {"title": "T", "script": clean, "description": "A groundbreaking overview." if seen["n"] == 1 else "A careful overview."}
    monkeypatch.setattr(service, "generate_content_from_research_context", fake_generate)
    content, result, attempts = run(service._generate_checked_content(req, _ctx(), "k", "job1"))
    assert seen["n"] == 2 and content["description"] == "A careful overview." and "groundbreaking" in calls["feedback"][1]


def test_a_short_script_with_banned_wording_fails_as_too_short_and_is_not_padded(monkeypatch):
    req = PodcastRequest(topic="t")
    short_hype = "Lovelace and Turing showed a revolutionary result."
    service, req, calls = _harness(monkeypatch, [short_hype, short_hype, short_hype])
    with pytest.raises(ScriptTooShortError):
        run(service._generate_checked_content(req, _ctx(), "k", "job1"))


def test_naming_violations_are_reported_before_banned_wording(monkeypatch):
    req = PodcastRequest(topic="t")
    both = _script(" Zorblatt and Quux showed a revolutionary result.", req)
    service, req, calls = _harness(monkeypatch, [both, both, both])
    with pytest.raises(nw.NamingViolationError):
        run(service._generate_checked_content(req, _ctx(), "k", "job1"))
    assert "ONLY these papers" in calls["feedback"][1] and "overstated or promotional" in calls["feedback"][1]    # both are fed back together


def test_failure_notice_for_banned_wording_is_plain():
    from failure_notice import describe_failure
    d = describe_failure(BannedPhraseError([{"phrase": "revolutionary", "matched": "revolutionary", "where": "script", "sentence": "x"}]))
    assert d["kind"] == "banned_wording" and "overstated or promotional" in d["summary"] and "script" not in d["summary"].lower().replace("the script", "")


def test_the_generator_prompt_does_not_list_or_use_the_banned_words_and_no_longer_teaches_the_hype():
    import inspect
    src = inspect.getsource(pri.PodcastResearchIntegrator.build_2_speaker_research_prompt)
    assert "banned_phrase_list" not in src and "Never use these words or phrases" not in src
    assert "This research represents" not in src and "a paradigm shift because" not in src
    assert "highlight revolutionary implications" not in src and "Present a paradigm shift only" not in src
    assert "recent breakthroughs" not in src and "potential breakthroughs" not in src and "paradigm_shifts_discussed" not in src


# ---------------------------------------------------------------- fix 4 (b): unsupported attributions are a reason to regenerate
from attribution_check import AttributionError

CLAIM = "Lovelace and Turing showed that every machine proves everything."


def _unsupported(quote=CLAIM):
    return [{"quote": quote, "pid": "P1", "verdict": "unsupported", "reason": "The abstract says nothing like this."}]


def test_unsupported_attribution_triggers_regeneration_with_the_sentence_quoted_back(monkeypatch):
    req = PodcastRequest(topic="t")
    bad, good = _script(" " + CLAIM, req), _script(" Lovelace and Turing showed it.", req)
    service, req, calls = _harness(monkeypatch, [bad, good])
    calls["attr"] = [_unsupported(), []]
    content, result, attempts = run(service._generate_checked_content(req, _ctx(), "k", "job1"))
    assert calls["gen"] == 2 and content["script"] == good and calls["attr_calls"] == 2
    assert CLAIM in calls["feedback"][1] and "abstracts do not support" in calls["feedback"][1]
    assert attempts[0]["attribution"]["unsupported"] == 1 and attempts[1]["attribution"]["unsupported"] == 0


def test_attribution_that_never_clears_fails_the_episode(monkeypatch):
    req = PodcastRequest(topic="t")
    bad = _script(" " + CLAIM, req)
    service, req, calls = _harness(monkeypatch, [bad, bad, bad])
    calls["attr"] = [_unsupported()]
    with pytest.raises(AttributionError) as e:
        run(service._generate_checked_content(req, _ctx(), "k", "job1"))
    assert calls["gen"] == 4 and CLAIM[:40] in str(e.value) and "no episode was published" in str(e.value)


def test_a_naming_violation_means_no_attribution_call_that_attempt(monkeypatch):
    req = PodcastRequest(topic="t")
    bad, good = _script(" Zorblatt and Quux showed it.", req), _script(" Lovelace and Turing showed it.", req)
    service, req, calls = _harness(monkeypatch, [bad, good])
    run(service._generate_checked_content(req, _ctx(), "k", "job1"))
    assert calls["attr_calls"] == 1                      # only for the attempt whose papers were all listed


def test_a_short_script_is_regenerated_then_checked_like_any_other(monkeypatch):
    req = PodcastRequest(topic="t")
    short = "Lovelace and Turing showed that every machine proves everything."
    ok = _script(" Lovelace and Turing showed it.", req)
    service, req, calls = _harness(monkeypatch, [short, ok])
    content, result, attempts = run(service._generate_checked_content(req, _ctx(), "k", "job1"))
    assert content["script"] == ok and calls["gen"] == 2 and attempts[0]["too_short"] == len(short.split())
    assert calls["attr_calls"] == 1                      # the short attempt was not sent to the model checks


def test_attribution_check_unavailable_fails_closed(monkeypatch):
    from attribution_check import AttributionCheckUnavailable
    req = PodcastRequest(topic="t")
    good = _script(" Lovelace and Turing showed it.", req)
    service, req, calls = _harness(monkeypatch, [good])
    plain = svc.make_gemini_llm_call("k")

    async def llm(system, user):
        if "PAPERS:" in user and "SCRIPT:" in user:
            raise RuntimeError("model down")
        return json.dumps({"mentions": [{"quote": "Lovelace and Turing showed", "authors": ["Lovelace", "Turing"], "year": 2025, "title_words": []}]})
    monkeypatch.setattr(svc, "make_gemini_llm_call", lambda key: llm)
    with pytest.raises(AttributionCheckUnavailable):
        run(service._generate_checked_content(req, _ctx(), "k", "job1"))
    assert calls["gen"] == 1 and calls["attr_calls"] == 0     # the check was repeated (three more times), the script was not regenerated


def test_failure_notices_for_attribution():
    from failure_notice import describe_failure
    from attribution_check import AttributionCheckUnavailable
    a = describe_failure(AttributionError(_unsupported()))
    b = describe_failure(AttributionCheckUnavailable("x"))
    assert a["kind"] == "unsupported_attribution" and "abstracts do not support" in a["summary"] and CLAIM not in a["summary"]
    assert b["kind"] == "attribution_check_unavailable" and "try again later" in b["what_to_do"]


# ---------------------------------------------------------------- fix 4 (c): the 5-10 minute target is enforced with a word cap
from utils.script_validation import (calculate_maximum_words_for_duration as max_words_for, calculate_minimum_words_for_duration as min_words_for,
                                     length_feedback, ScriptTooLongError, MAX_WORDS_PER_MINUTE)


def _long(request, extra=" Lovelace and Turing showed it."):
    return ("word " * (max_words_for(request.duration) + 5)) + extra


def test_the_cap_comes_from_the_measured_speech_rate_and_never_contradicts_the_minimum():
    assert MAX_WORDS_PER_MINUTE == 120
    assert max_words_for("5-10 minutes") == 1200                                  # Gary's number, 120 words per minute of the longest length
    assert max_words_for("10 minutes") == min_words_for("10 minutes") + 100          # the existing minimum is already above the speech-rate cap
    assert max_words_for("5 minutes") == min_words_for("5 minutes") + 100
    assert max_words_for("") == 1200 and max_words_for("8-12 minutes") > max_words_for("5-10 minutes")
    for d in ("5-10 minutes", "10 minutes", "5 minutes", "3-4 minutes", ""):
        assert max_words_for(d) > min_words_for(d)
    # the measured episode that was too long (1303 words, 10.8 minutes) is over the cap; the stored episodes of 1193 and 1199 words are under it
    assert 1303 > max_words_for("5-10 minutes") > 1199


def test_a_script_over_the_cap_is_regenerated_with_the_limit_in_the_feedback(monkeypatch):
    req = PodcastRequest(topic="t")
    service, req, calls = _harness(monkeypatch, [_long(req), _script(" Lovelace and Turing showed it.", req)])
    content, result, attempts = run(service._generate_checked_content(req, _ctx(), "k", "job1"))
    assert calls["gen"] == 2 and attempts[0]["too_long"] > attempts[0]["max_words"] == 1200
    assert "too long" in calls["feedback"][1] and "limit is 1200 words" in calls["feedback"][1] and result.passed
    assert calls["attr_calls"] == 1                      # the over-long attempt was not checked for naming or attribution


def test_a_script_that_stays_too_long_fails_the_episode(monkeypatch):
    req = PodcastRequest(topic="t")
    service, req, calls = _harness(monkeypatch, [_long(req)] * 3)
    with pytest.raises(ScriptTooLongError) as e:
        run(service._generate_checked_content(req, _ctx(), "k", "job1"))
    assert calls["gen"] == 4 and "over the limit of 1200" in str(e.value) and "no episode was published" in str(e.value)


def test_a_script_exactly_at_the_cap_passes(monkeypatch):
    req = PodcastRequest(topic="t")
    body = "word " * (max_words_for(req.duration) - 5)
    service, req, calls = _harness(monkeypatch, [body + " Lovelace and Turing showed it."])
    assert len((body + " Lovelace and Turing showed it.").split()) == 1200
    run(service._generate_checked_content(req, _ctx(), "k", "job1"))
    assert calls["gen"] == 1


def test_too_long_then_hype_then_clean_shares_the_budget(monkeypatch):
    req = PodcastRequest(topic="t")
    service, req, calls = _harness(monkeypatch, [_long(req), _script(HYPE, req), _script(" Lovelace and Turing showed it.", req)])
    run(service._generate_checked_content(req, _ctx(), "k", "job1"))
    assert calls["gen"] == 3


def test_the_prompt_states_the_maximum_and_the_failure_notice_is_plain():
    import inspect
    from failure_notice import describe_failure
    assert "MAXIMUM: {calculate_maximum_words_for_duration(duration)} words" in inspect.getsource(pri.PodcastResearchIntegrator.build_2_speaker_research_prompt)
    d = describe_failure(ScriptTooLongError(1300, 1200))
    assert d["kind"] == "script_too_long" and "1300" not in d["summary"] and "narrower topic" in d["what_to_do"]
    assert "1303 words" in length_feedback(1303, 1200, 600) and "between 600 and 1200" in length_feedback(1303, 1200, 600)


# ---------------------------------------------------------------- fix 4: no padding, and every check runs again on the final text
from script_style import FinalTextCheckError
from utils.script_validation import ScriptTooShortError, validate_script_length, short_feedback


def test_validation_never_pads_a_script_that_is_close_to_the_minimum():
    import inspect
    import utils.script_validation as sv
    assert not hasattr(sv, "extend_script_if_close") and "auto_extend" not in inspect.signature(validate_script_length).parameters
    near = " ".join(["word"] * (min_words_for("5-10 minutes") - 20))
    ok, msg, out = validate_script_length(near, "5-10 minutes")
    assert not ok and "too short" in msg and out == near                       # before: padded with unchecked boilerplate and accepted
    ok, msg, out = validate_script_length(near + " " + " ".join(["word"] * 20), "5-10 minutes")
    assert ok and out.endswith("word")
    assert "tremendous potential" not in inspect.getsource(sv) and "significant step forward" not in inspect.getsource(sv)


def test_the_service_has_no_padding_path():
    import inspect
    src = inspect.getsource(svc)
    assert "auto_extend" not in src and "Script automatically extended" not in src and "proceeding to validation" not in src
    assert "_verify_final_text(content, request, research_context, google_key, job_id, on_rejection=" in src


def _final_content(req, script_extra=" Lovelace and Turing showed it.", description="Overview of the episode."):
    return {"title": "T", "script": _script(script_extra, req), "description": description + "\n\n## References\n\n- Lovelace and Turing (2025). A. DOI: 10.1/p1\n",
            "papers_named": ["P1"]}


def _final_service(monkeypatch, attributions=None, mentions=None):
    service = svc.PodcastGenerationService()
    seen = {"calls": []}

    async def llm(system, user):
        seen["calls"].append("attribution" if ("PAPERS:" in user and "SCRIPT:" in user) else "naming")
        if "PAPERS:" in user and "SCRIPT:" in user:
            return json.dumps({"attributions": attributions or []})
        ms = []
        if "Lovelace" in user:
            ms.append({"quote": "Lovelace and Turing showed", "authors": ["Lovelace", "Turing"], "year": 2025, "title_words": []})
        if "Zorblatt" in user:
            ms.append({"quote": "Zorblatt and Quux showed", "authors": ["Zorblatt", "Quux"], "year": 2019, "title_words": []})
        return json.dumps({"mentions": ms})
    monkeypatch.setattr(svc, "make_gemini_llm_call", lambda key: llm)
    return service, seen


def test_final_text_that_is_clean_passes_all_checks_and_records_a_summary(monkeypatch):
    req = PodcastRequest(topic="t")
    service, seen = _final_service(monkeypatch)
    content = _final_content(req)
    summary = run(service._verify_final_text(content, req, _ctx(), "k", "job1"))
    assert summary["named_pids"] == ["P1"] and summary["max_words"] == 1200 and content["final_text_checks"] == summary
    assert seen["calls"][-1] == "attribution" and set(seen["calls"]) == {"naming", "attribution"}     # naming reads the script and the description body


def test_final_text_with_banned_wording_added_after_the_loop_is_refused(monkeypatch):
    req = PodcastRequest(topic="t")
    service, seen = _final_service(monkeypatch)
    content = _final_content(req, description="A groundbreaking overview.")                     # e.g. introduced by a post-processing step
    with pytest.raises(BannedPhraseError):
        run(service._verify_final_text(content, req, _ctx(), "k", "job1"))
    assert seen["calls"] == []                          # the deterministic checks come first and cost nothing


def test_the_reference_sections_are_not_read_as_prose_by_the_final_check(monkeypatch):
    req = PodcastRequest(topic="t")
    service, seen = _final_service(monkeypatch)
    content = _final_content(req)
    content["description"] += "\n- A revolutionary title (2020). Unprecedented results. DOI: 10.1/x\n"
    run(service._verify_final_text(content, req, _ctx(), "k", "job1"))


def test_final_text_length_is_enforced_both_ways(monkeypatch):
    req = PodcastRequest(topic="t")
    service, seen = _final_service(monkeypatch)
    long_c = {"title": "T", "script": "word " * 1300, "description": "d", "papers_named": ["P1"]}
    with pytest.raises(ScriptTooLongError):
        run(service._verify_final_text(long_c, req, _ctx(), "k", "job1"))
    short_c = {"title": "T", "script": "word " * 100, "description": "d", "papers_named": ["P1"]}
    with pytest.raises(ScriptTooShortError):
        run(service._verify_final_text(short_c, req, _ctx(), "k", "job1"))


def test_final_text_with_unspeakable_notation_or_a_new_unlisted_work_or_unsupported_claim_is_refused(monkeypatch):
    req = PodcastRequest(topic="t")
    service, seen = _final_service(monkeypatch)
    with pytest.raises(UnspeakableNotationError):
        run(service._verify_final_text(_final_content(req, " Lovelace and Turing showed $" + _BS + "oint F$."), req, _ctx(), "k", "job1"))
    service, seen = _final_service(monkeypatch)
    with pytest.raises(nw.NamingViolationError):
        run(service._verify_final_text(_final_content(req, " Zorblatt and Quux showed it."), req, _ctx(), "k", "job1"))
    service, seen = _final_service(monkeypatch, attributions=_unsupported())
    with pytest.raises(AttributionError):
        run(service._verify_final_text(_final_content(req, " " + CLAIM), req, _ctx(), "k", "job1"))


def test_final_text_naming_a_paper_the_references_were_not_built_for_is_refused(monkeypatch):
    req = PodcastRequest(topic="t")
    service, seen = _final_service(monkeypatch)
    content = _final_content(req)
    content["papers_named"] = []                        # references were built for an empty set
    with pytest.raises(FinalTextCheckError) as e:
        run(service._verify_final_text(content, req, _ctx(), "k", "job1"))
    assert "P1" in str(e.value) and "no episode was published" in str(e.value)


def test_failure_notices_for_short_and_final_check():
    from failure_notice import describe_failure
    a = describe_failure(ScriptTooShortError(300, 600))
    b = describe_failure(FinalTextCheckError("x"))
    assert a["kind"] == "script_too_short" and "300" not in a["summary"] and b["kind"] == "final_text_check_failed" and "x" not in b["summary"]
    assert "300 words" in short_feedback(300, 600, 1200)


# ---------------------------------------------------------------- fix 5: four content attempts, transient errors counted apart, every rejection recorded in full
from types import SimpleNamespace as NS


def test_four_content_attempts_are_allowed(monkeypatch):
    req = PodcastRequest(topic="t")
    bad = _script(" Zorblatt and Quux showed it.", req)
    good = _script(" Lovelace and Turing showed it.", req)
    service, req, calls = _harness(monkeypatch, [bad, bad, bad, good])
    content, result, attempts = run(service._generate_checked_content(req, _ctx(), "k", "job1"))
    assert calls["gen"] == 4 and content["script"] == good and svc.PodcastGenerationService.MAX_CONTENT_RETRIES == 3


def test_a_generator_reply_that_is_not_json_does_not_use_a_content_attempt(monkeypatch):
    req = PodcastRequest(topic="t")
    bad = _script(" Zorblatt and Quux showed it.", req)
    good = _script(" Lovelace and Turing showed it.", req)
    boom = ValueError("No JSON object found in the AI's response.")
    # two model errors, three content rejections, then a good script: still inside 4 content attempts plus 3 transient retries
    service, req, calls = _harness(monkeypatch, [boom, bad, boom, bad, bad, good])
    content, result, attempts = run(service._generate_checked_content(req, _ctx(), "k", "job1"))
    assert content["script"] == good and calls["gen"] == 6
    kinds = [r["check"] for r in service._last_rejections]
    assert kinds.count("transient_error") == 2 and kinds.count("naming") == 3
    assert [r["attempt"] for r in service._last_rejections if r["check"] == "transient_error"] == [1, 2]       # the content attempt each one interrupted
    assert "ONLY these papers" in calls["feedback"][3]                                                         # the feedback survived the model error


def test_model_errors_have_their_own_budget_and_then_the_error_is_raised(monkeypatch):
    req = PodcastRequest(topic="t")
    service, req, calls = _harness(monkeypatch, [ValueError("No JSON object found in the AI's response.")])
    with pytest.raises(ValueError):
        run(service._generate_checked_content(req, _ctx(), "k", "job1"))
    assert calls["gen"] == 4 == 1 + svc.PodcastGenerationService.MAX_TRANSIENT_RETRIES              # never touched a content attempt
    assert [r["check"] for r in service._last_rejections] == ["transient_error"] * 4


def test_a_timeout_is_a_model_error_too(monkeypatch):
    req = PodcastRequest(topic="t")
    good = _script(" Lovelace and Turing showed it.", req)
    service, req, calls = _harness(monkeypatch, [asyncio.TimeoutError(), good])
    content, *_ = run(service._generate_checked_content(req, _ctx(), "k", "job1"))
    assert calls["gen"] == 2 and service._last_rejections[0]["error_type"] == "TimeoutError"


def test_an_unreadable_check_answer_is_repeated_on_the_same_script_not_regenerated(monkeypatch):
    req = PodcastRequest(topic="t")
    good = _script(" Lovelace and Turing showed it.", req)
    service, req, calls = _harness(monkeypatch, [good])
    inner = svc.make_gemini_llm_call("k")           # the harness's fake model
    state = {"n": 0}

    async def flaky(system, user):
        if "PAPERS:" not in user:
            state["n"] += 1
            if state["n"] <= 2:                      # the naming check answers garbage twice, then works
                return "not json at all"
        return await inner(system, user)
    monkeypatch.setattr(svc, "make_gemini_llm_call", lambda key: flaky)
    content, result, attempts = run(service._generate_checked_content(req, _ctx(), "k", "job1"))
    assert calls["gen"] == 1 and content["script"] == good and result.passed
    stages = [r["stage"] for r in service._last_rejections if r["check"] == "transient_error"]
    assert stages == ["naming_check"] * 2


def test_every_rejection_is_recorded_in_full_and_handed_to_the_job(monkeypatch):
    req = PodcastRequest(topic="t")
    bad = _script(" It is a truly revolutionary result. Zorblatt and Quux showed it.", req)
    good = _script(" Lovelace and Turing showed it.", req)
    service, req, calls = _harness(monkeypatch, [bad, good])
    stored = []
    content, *_ = run(service._generate_checked_content(req, _ctx(), "k", "job1", on_rejection=stored.extend))
    assert stored == service._last_rejections
    naming = next(r for r in stored if r["check"] == "naming")
    assert naming["attempt"] == 1 and "Zorblatt" in naming["quote"] and naming["context"]
    banned = next(r for r in stored if r["check"] == "banned_wording")
    assert banned["matched"] == "revolutionary" and "truly revolutionary result" in banned["sentence"]


def test_an_unsupported_attribution_is_recorded_with_sentence_paper_abstract_verdict_and_reason(monkeypatch):
    req = PodcastRequest(topic="t")
    claim = "Lovelace and Turing showed that every machine proves everything."
    bad, good = _script(" " + claim, req), _script(" Lovelace and Turing showed it.", req)
    service, req, calls = _harness(monkeypatch, [bad, good])
    calls["attr"] = [[{"quote": claim, "pid": "P1", "verdict": "unsupported", "reason": "The abstract says nothing like this."},
                      {"quote": "Lovelace and Turing showed that every", "pid": "P1", "verdict": "supported", "reason": "Stated."}], []]
    run(service._generate_checked_content(req, _ctx(), "k", "job1"))
    items = [r for r in service._last_rejections if r["check"] == "attribution"]
    unsup = next(r for r in items if r["verdict"] == "unsupported")
    assert unsup == {"attempt": 1, "check": "attribution", "verdict": "unsupported", "quote": claim, "pid": "P1",
                     "paper": "Analytical engines and the first algorithms", "authors": ["Ada Lovelace", "Alan Turing"], "year": 2025,
                     "abstract": "Abs.", "reason": "The abstract says nothing like this."}
    sup = next(r for r in items if r["verdict"] == "supported")
    assert sup["abstract"] is None and sup["reason"] == "Stated."                 # supported verdicts are kept for comparison, without the abstract


def test_storing_on_the_job_is_best_effort_and_uses_array_union(monkeypatch):
    from google.cloud import firestore
    updates = []
    ref = NS(update=lambda d: updates.append(d))
    svc.PodcastGenerationService._job_rejection_sink(ref)([{"check": "naming"}])
    assert list(updates[0]) == ["rejections"] and isinstance(updates[0]["rejections"], type(firestore.ArrayUnion([1])))
    req = PodcastRequest(topic="t")
    good = _script(" Lovelace and Turing showed it.", req)
    service, req, calls = _harness(monkeypatch, [_script(" Zorblatt and Quux showed it.", req), good])

    def broken(items):
        raise RuntimeError("firestore down")
    content, *_ = run(service._generate_checked_content(req, _ctx(), "k", "job1", on_rejection=broken))
    assert content["script"] == good                                                  # a storage error never fails the episode


def test_the_final_text_check_records_what_it_refused(monkeypatch):
    req = PodcastRequest(topic="t")
    service, seen = _final_service(monkeypatch)
    stored = []
    content = _final_content(req, description="A groundbreaking overview.")
    with pytest.raises(BannedPhraseError):
        run(service._verify_final_text(content, req, _ctx(), "k", "job1", on_rejection=stored.extend))
    assert stored[0]["check"] == "banned_wording" and stored[0]["attempt"] == 0 and stored[0]["matched"].lower() == "groundbreaking"


def test_a_final_check_whose_answer_cannot_be_read_is_repeated(monkeypatch):
    req = PodcastRequest(topic="t")
    service = svc.PodcastGenerationService()
    state = {"n": 0}

    async def llm(system, user):
        if "PAPERS:" in user:
            return json.dumps({"attributions": []})
        state["n"] += 1
        if state["n"] <= 2:
            return "garbage"
        return json.dumps({"mentions": [{"quote": "Lovelace and Turing showed", "authors": ["Lovelace", "Turing"], "year": 2025, "title_words": []}]})
    monkeypatch.setattr(svc, "make_gemini_llm_call", lambda key: llm)
    stored = []
    summary = run(service._verify_final_text(_final_content(req), req, _ctx(), "k", "job1", on_rejection=stored.extend))
    assert summary["named_pids"] == ["P1"] and [r["stage"] for r in stored if r["check"] == "transient_error"] == ["final_naming_check"] * 2


def test_the_loop_passes_the_episode_topic_so_a_quoted_topic_is_not_an_unlisted_work(monkeypatch):
    topic = "Chaos theory in neural network models of cells"
    req = PodcastRequest(topic=topic)
    text = _script(' Today we are exploring "' + topic + '". Lovelace and Turing showed it.', req)
    service, req, calls = _harness(monkeypatch, [text])
    req.topic = topic                                   # _harness returns its own request
    inner = svc.make_gemini_llm_call("k")

    async def llm(system, user):
        if "PAPERS:" not in user and topic in user:
            return json.dumps({"mentions": [{"quote": topic, "authors": [], "year": None, "title_words": []},
                                            {"quote": "Lovelace and Turing showed", "authors": ["Lovelace", "Turing"], "year": 2025, "title_words": []}]})
        return await inner(system, user)
    monkeypatch.setattr(svc, "make_gemini_llm_call", lambda key: llm)
    content, result, attempts = run(service._generate_checked_content(req, _ctx(), "k", "job1"))
    assert calls["gen"] == 1 and result.passed and [x.get("ignored") for x in result.mentions][:1] == ["episode topic"]
