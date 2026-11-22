"""Three things heard or seen in finished episodes.

* "pi" was read aloud as the two letters. Only the audio request may be changed for that: the script, the transcript and the notes keep
  the spelling a reader expects, and so does every check.
* The rotation counted the jobs that had already recorded a pick, without the job being created, so the count stayed put until the write
  landed and two episodes in a row took the same expert. Both episodes voiced on 2026-11-22 came out in Eric's voice.
* An approved source's analysis is a model answer parsed as JSON. When the model wraps it in prose or cuts it short, the parse fails, the
  analysis is marked failed and a curated run refuses to go on. Three of five runs died that way, each clearing on a retry.
"""
import re
from pathlib import Path

import pronunciation as pr
import voice_roster as vr

BACKEND = Path(__file__).resolve().parents[2]


# --- how a word is said -----------------------------------------------------------------------------------------------------------
def test_pi_is_said_as_pie():
    assert pr.for_speech("the irrationality exponent of pi is 2") == "the irrationality exponent of pie is 2"
    assert pr.for_speech("Pi is irrational") == "Pie is irrational"
    assert pr.for_speech("PI") == "PIE"


def test_pi_inside_another_word_is_untouched():
    for text in ("pivot", "pin", "Spinoza", "pion", "piano", "copious", "the pigeonhole principle", "Parisi"):
        assert pr.for_speech(text) == text, text


def test_the_greek_letter_is_said_too():
    assert pr.for_speech("the constant π is irrational") == "the constant pie is irrational"


def test_it_is_a_table_other_names_can_join():
    assert isinstance(pr.SPOKEN_AS, dict) and pr.SPOKEN_AS["pi"] == "pie"
    assert pr.changes("pi and pi again")[0]["count"] == "2"
    assert pr.changes("nothing to change") == []


def test_only_the_audio_request_is_changed():
    """The script, the transcript and the notes keep "pi": the substitution happens where the request is made, and nowhere else."""
    service = (BACKEND / "elevenlabs_voice_service.py").read_text(encoding="utf-8")
    assert "pronunciation.for_speech(text)" in service
    assert service.count("pronunciation.for_speech") == 1, "exactly one place changes the words"
    for module in ("curated_script.py", "services/rss_service.py", "feed_text.py", "curated_pipeline.py"):
        text = (BACKEND / module).read_text(encoding="utf-8")
        assert "pronunciation" not in text, f"{module} must not rewrite what a reader sees"


def test_the_published_scripts_still_say_pi():
    fixture = BACKEND / "tests" / "fixtures" / "published_scripts" / "ever-bio-260013.txt"
    assert "pie" not in fixture.read_text(encoding="utf-8").lower().replace("pieces", "")


# --- the rotation ------------------------------------------------------------------------------------------------------------------
def test_two_consecutive_rotation_picks_differ():
    """With the job being created counted, the position moves for every job, so no two in a row share a voice."""
    picks = [vr.expert_for_episode(n) for n in range(1, 9)]
    for a, b in zip(picks, picks[1:]):
        assert a != b, picks
    assert len(set(picks[:len(vr.rotation_for())])) == len(vr.rotation_for())


def test_the_position_counts_the_job_being_created():
    source = (BACKEND / "services" / "podcast_generation_service.py").read_text(encoding="utf-8")
    assert "_rotation_position" in source and "_episodes_voiced_before" not in source
    assert "+ 1" in source.split("_rotation_position")[1][:1200], "this job counts toward the position"


def test_a_requested_expert_is_still_not_a_rotation_pick():
    source = (BACKEND / "services" / "podcast_generation_service.py").read_text(encoding="utf-8")
    assert 'expert_voice_id, expert_source = request.expert_voice_id, "requested"' in source


# --- the analysis retry -----------------------------------------------------------------------------------------------------------
def test_an_analysis_is_attempted_twice_before_it_is_called_failed():
    source = (BACKEND / "enhanced_research_service.py").read_text(encoding="utf-8")
    block = source.split("async def _analyze_single_paper")[1][:2600]
    assert "for attempt in (1, 2)" in block, "one retry before the fallback"
    assert "attempt {attempt} of 2" in block, "each attempt is reported"
    assert block.index("for attempt in (1, 2)") < block.index("_create_fallback_analysis"), "the fallback comes after both attempts"


def test_the_fallback_still_marks_the_analysis_failed():
    """A source whose analysis fails twice must still stop a curated run: the retry must not hide it."""
    source = (BACKEND / "enhanced_research_service.py").read_text(encoding="utf-8")
    assert "analysis_failed=True" in source
    integrator = (BACKEND / "podcast_research_integrator.py").read_text(encoding="utf-8")
    assert "raise CuratedAnalysisFailed(sorted(set(failed)))" in integrator


def test_the_retry_is_reported_not_silent():
    source = (BACKEND / "enhanced_research_service.py").read_text(encoding="utf-8")
    assert re.search(r"failed twice for .*title", source), "a source that fails twice is named in the log"
