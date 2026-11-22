"""Three things heard or seen in finished episodes.

* "pi" was read aloud as the two letters. Only the audio request may be changed for that: the script, the transcript and the notes keep
  the spelling a reader expects, and so does every check.
* The rotation asked `firebase_admin` for a Firestore client. That package is not a dependency of this service, so the import raised
  ModuleNotFoundError on every run, the count came back 0 and every episode took the first voice in the rotation. Both episodes voiced on
  2026-11-22 came out in Eric's voice, and the logs carry "No module named 'firebase_admin'" for each. The service's own client also has to
  name the database: this project's Firestore database is "copernicusai" and there is no default one.
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


def test_an_all_caps_word_is_an_abbreviation_and_is_left_alone():
    """PI is a principal investigator, not the constant."""
    assert pr.for_speech("the PI of the lab") == "the PI of the lab"
    assert pr.for_speech("PI") == "PI"
    assert pr.changes("the PI of the lab") == []
    assert pr.changes("the PI of the lab and pi itself")[0]["count"] == "1"


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
    """Each recorded pick moves the count on by one, so no two episodes in a row share a voice."""
    picks = [vr.expert_for_episode(n) for n in range(0, 9)]
    for a, b in zip(picks, picks[1:]):
        assert a != b, picks
    assert len(set(picks[:len(vr.rotation_for())])) == len(vr.rotation_for())


def test_the_count_uses_the_service_firestore_client_not_firebase_admin():
    """The real failure: firebase_admin is not a dependency, so asking it for a client raised ModuleNotFoundError every run."""
    source = (BACKEND / "services" / "podcast_generation_service.py").read_text(encoding="utf-8")
    block = source.split("def _rotation_position")[1][:1800]
    code = block.split('"""')[2] if block.count('"""') >= 2 else block   # past the docstring, which names the old mistake
    assert "firebase_admin" not in code, "the service's own client, not one from a package this service does not install"
    assert "db.collection('podcast_jobs')" in block and "'voices.expert_chosen_by', '==', 'rotation'" in block
    assert "+ 1" not in block, "the count is the episodes voiced BEFORE this one; expert_for_episode expects that"


def test_firebase_admin_is_not_a_dependency_of_this_service():
    """Holds the diagnosis in place: if this ever becomes a dependency, the old code would have 'worked' on the wrong database."""
    requirements = (BACKEND / "requirements.txt").read_text(encoding="utf-8").lower()
    assert "firebase-admin" not in requirements and "firebase_admin" not in requirements


def test_the_named_database_is_the_only_one():
    """firebase_admin's client would have read the (default) database, which does not exist for this project; the service's client names
    copernicusai."""
    config = (BACKEND / "config" / "database.py").read_text(encoding="utf-8")
    assert 'database="copernicusai"' in config
    source = (BACKEND / "services" / "podcast_generation_service.py").read_text(encoding="utf-8")
    assert "from config.database import db" in source


def test_a_count_that_cannot_be_read_is_reported_as_an_error():
    """A silent warning let every episode take the first voice for two runs without anything looking wrong."""
    block = (BACKEND / "services" / "podcast_generation_service.py").read_text(encoding="utf-8").split("def _rotation_position")[1][:1800]
    assert "structured_logger.error" in block, "a rotation that cannot be counted is an error, not a passing note"


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
