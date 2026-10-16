"""The text the generator is shown is neutral (fix 5): the paper-analysis prompts, the significance notes and the fallback description. Offline."""
import asyncio
import json
import sys
from types import SimpleNamespace as NS
from unittest.mock import MagicMock

import pytest

try:
    import psutil  # noqa: F401
except ImportError:
    sys.modules["psutil"] = MagicMock()

import enhanced_research_service as ers
import paper_processor as pp
import podcast_research_integrator as pri
from script_style import banned_phrase_hits

HYPE_WORDS = ("paradigm", "revolution", "breakthrough", "transformative", "groundbreaking", "unprecedented", "game-chang", "cutting-edge")


def run(coro):
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


def assert_neutral(text):
    low = text.lower()
    assert not [w for w in HYPE_WORDS if w in low], [w for w in HYPE_WORDS if w in low]
    assert banned_phrase_hits(text) == []


# ---------------------------------------------------------------- the deep analysis prompt (paper_processor)
def capture_deep_prompt(monkeypatch, reply):
    seen = {}

    class Model:
        def __init__(self, name):
            pass

        def generate_content(self, prompt):
            seen["prompt"] = prompt
            return NS(text=reply)
    monkeypatch.setattr(pp.genai, "GenerativeModel", Model)
    monkeypatch.setattr(pp.genai, "configure", lambda **k: None)
    paper = pp.ResearchPaper(title="The Network Structure of Mathlib", authors=["A B"], content="", abstract="We present a network analysis.", doi=None)
    opts = pp.AnalyzeOptions(focus_areas=["significance", "implications", "methodology"], significance_analysis=True)
    analysis = run(pp.analyze_paper_with_gemini(paper, opts, "k"))
    return seen["prompt"], analysis


def test_the_deep_analysis_prompt_asks_what_the_paper_shows_in_neutral_words(monkeypatch):
    reply = json.dumps({"summary": "S", "key_findings": ["F"], "significance": ["It shows hierarchies compress."], "interdisciplinary_connections": [],
                        "implications": [], "methodology_analysis": "M", "future_research_directions": [], "confidence_score": 0.9})
    prompt, analysis = capture_deep_prompt(monkeypatch, reply)
    assert_neutral(prompt)
    assert "report what it actually shows" in prompt and "as far as the paper itself supports" in prompt
    assert '"significance"' in prompt and "paradigm_shifts" not in prompt
    assert "Do not add claims, numbers or importance" in prompt
    assert analysis.significance == ["It shows hierarchies compress."] and analysis.analysis_failed is False
    assert analysis.paradigm_shifts == analysis.significance                      # read-only alias for the older generation paths


def test_an_unparseable_deep_analysis_has_no_invented_significance(monkeypatch):
    prompt, analysis = capture_deep_prompt(monkeypatch, "I could not produce JSON for this one.")
    assert analysis.analysis_failed is True and analysis.significance == []


# ---------------------------------------------------------------- the quick analysis prompt (enhanced_research_service)
def test_the_quick_analysis_prompt_is_neutral_and_asks_for_significance_not_paradigm_potential():
    svc = ers.EnhancedResearchService("k")
    prompt = svc.analysis_prompts["paper_analysis"].format(complexity="medium", title="T", authors="A", abstract="X")
    assert_neutral(prompt)
    assert '"significance"' in prompt and "paradigm_shift_potential" not in prompt and "none stated" in prompt
    assert "title exactly as given" in prompt and "accessible terms" not in prompt          # the model no longer rewrites the paper's title


def test_a_missing_significance_defaults_to_none_stated_not_medium():
    svc = ers.EnhancedResearchService("k")
    a = svc._validate_paper_analysis({"title": "T", "summary": "S", "key_findings": ["F"], "methodology": "M", "implications": "I",
                                      "related_work": "R", "technical_complexity": "low", "suggested_questions": [], "keywords": []})
    assert a.significance == "none stated" and not hasattr(a, "paradigm_shift_potential")


def test_only_real_significance_notes_reach_the_generator():
    def analysis(title, significance, failed=False):
        return NS(title=title, significance=significance, analysis_failed=failed, interdisciplinary_connections=[], key_findings=["f " + title])
    sig, conns, findings = pri.aggregate_enhanced_analyses(
        [analysis("A", "Shows centrality tracks infrastructure."), analysis("B", "none stated"), analysis("C", "unknown"), analysis("D", ""),
         analysis("E", "x", failed=True)], {"A": "P1", "B": "P2"})
    assert sig == ["[P1] A: Shows centrality tracks infrastructure."]
    assert findings == ["[P1] f A", "[P2] f B", "f C", "f D"]


# ---------------------------------------------------------------- the description fallback
def fallback_context(findings, significance=None, directions=None, n_sources=2):
    analysis = NS(future_research_directions=directions or [])
    sources = [NS(title=f"A paper {i}", authors=["A B", "C D"], journal=None, source="arxiv", doi=None, url=f"https://arxiv.org/abs/2601.0000{i}v1",
                  publication_date="2026-01-01") for i in range(n_sources)]
    return NS(topic="Chaos Theory", key_findings=findings, significance=significance or [], paper_analyses=[analysis], research_sources=sources)


def test_the_fallback_description_is_built_only_from_what_the_research_found():
    import services.podcast_generation_service as svc
    from content_fixes import validate_description_before_publish
    ctx = fallback_context(["Neural signals are not Gaussian."], ["[P1] A paper: Shows hierarchies compress."], ["Test on larger graphs."])
    desc = svc.PodcastGenerationService._build_fallback_description(ctx)
    validate_description_before_publish(desc)
    assert_neutral(desc)
    assert "drawing on 2 research papers" in desc and "- Neural signals are not Gaussian." in desc and "Shows hierarchies compress." in desc
    assert "Test on larger graphs." in desc and "## References" in desc and "## Key Concepts Explored" in desc
    for filler in ("rapidly evolving", "far-reaching", "tremendous promise", "pressing challenges", "fundamental insights"):
        assert filler not in desc


def test_the_fallback_description_with_no_findings_has_no_filler_either():
    import services.podcast_generation_service as svc
    from content_fixes import validate_description_before_publish
    desc = svc.PodcastGenerationService._build_fallback_description(fallback_context(["Research findings require further analysis"], n_sources=1))
    validate_description_before_publish(desc)
    assert_neutral(desc)
    assert "drawing on 1 research paper reviewed" in desc and "Research findings require" not in desc and "## Research Insights" not in desc
    assert "## Future Directions" not in desc


# ---------------------------------------------------------------- the generator reads the whole abstract (the text the attribution check reads)
def evidence_for(abstracts):
    sources = [NS(pid=f"P{i}", title=f"Paper {i}", authors=["A B"], journal=None, source="arxiv", doi=None, url=f"https://arxiv.org/abs/2601.0000{i}v1",
                  publication_date="2026-01-01", abstract=a) for i, a in enumerate(abstracts, 1)]
    ctx = NS(research_sources=sources, significance=[], interdisciplinary_connections=[], key_findings=[])
    return pri.PodcastResearchIntegrator("k")._format_research_evidence(ctx)


def test_the_evidence_shows_the_full_abstract_not_300_characters():
    from attribution_check import MAX_ABSTRACT_CHARS
    full = ("We present a network analysis of Mathlib. " * 30).strip()          # about 1,200 characters
    assert len(full) > 1000
    ev = evidence_for([full])
    assert f"Abstract: {full}\n" in ev + "\n" and "..." not in ev
    long_one = "word " * 1000                                                    # 5,000 characters: capped at what the check reads, with a mark
    ev = evidence_for([long_one])
    line = next(l for l in ev.split("\n") if l.strip().startswith("Abstract:"))
    assert len(line.strip()) == len("Abstract: ") + MAX_ABSTRACT_CHARS + 3 and line.endswith("...")


def test_abstract_whitespace_is_normalised_and_missing_abstracts_do_not_break_the_prompt():
    ev = evidence_for(["Line one.\n\n  Line two.", None])
    assert "Abstract: Line one. Line two." in ev and "Abstract: " in ev


def test_the_attribution_check_and_the_generator_read_the_same_cap():
    import attribution_check as ac
    import inspect
    assert "MAX_ABSTRACT_CHARS" in inspect.getsource(pri.PodcastResearchIntegrator._format_research_evidence) and ac.MAX_ABSTRACT_CHARS == 2500


# ---------------------------------------------------------------- the generator writes the description in the same call as the script: its spec is neutral too
def test_the_description_and_title_spec_and_task_lines_invite_no_hype():
    import inspect
    src = inspect.getsource(pri.PodcastResearchIntegrator.build_2_speaker_research_prompt)
    low = src.lower()
    for phrase in ("engaging", "compelling", "maximizes discoverability", "industry impact", "why this research matters", "fascinating",
                   "future impact", "highlight interdisciplinary implications", "potential uses"):
        assert phrase not in low, phrase
    assert "no promotional or superlative language" in src and "no superlatives or promotional wording" in src
    assert "if they describe none, say that the papers do not discuss applications" in src
    assert "do not predict impact beyond what they claim" in src


def test_there_is_exactly_one_model_call_that_writes_the_description_and_it_is_the_script_call():
    """The description is written inside the generator's JSON reply; after it only deterministic code touches the text (references, hashtags,
    placeholder cleanup, length limit, venue rewriting). If a model call is ever added after the script, this test is the place to extend."""
    import inspect
    import services.podcast_generation_service as svc
    src = inspect.getsource(svc.PodcastGenerationService._finalize_content)
    for model_call in ("generate_content(", "generateContent", "genai.", "make_gemini_llm_call", "openai", "chat.completions"):
        assert model_call not in src, model_call
