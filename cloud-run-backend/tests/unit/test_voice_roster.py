"""A voice is chosen by id, and a role by the script's own label.

The service held a six-entry map from voice id to name and worked a role out from the name. Any voice outside those six fell back to
"Matilda" and "Adam", so an episode asked to use a new expert could have had its lines read in the wrong voice with nothing to show for it.
"""
import re
from pathlib import Path

import voice_roster as vr

BACKEND = Path(__file__).resolve().parents[2]
NEW_EXPERTS = {
    "Xb7hH8MSUJpSbSDYk0k2": "Alice",
    "onwK4e9ZLuTAKqWW03F9": "Daniel",
    "JBFqnCBsd6RMkjVDRZzb": "George",
    "pqHfZKP75CvOlQylNhV4": "Bill",
    "cjVigY5qzO86Huf0OWal": "Eric",
    "SAz9YHcvj6GT2YYXdXww": "River",
    "hpp4J3VqNfWAUOO0d1Us": "Bella",
    "IKne3meq5aSn9XLyUdCD": "Charlie",
}


def test_every_roster_voice_resolves_to_its_own_name():
    for vid, name in NEW_EXPERTS.items():
        assert vr.name_for(vid) == name, f"{vid} should be {name}"


def test_a_voice_outside_the_roster_never_borrows_another_name():
    assert vr.name_for("not-a-voice-id") == ""
    assert vr.name_for("not-a-voice-id", "Adam") == "Adam"      # only because the caller asked for that fallback
    assert vr.is_known("not-a-voice-id") is False


def test_the_roster_is_a_mix_of_gender_age_and_accent():
    experts = [vr.ROSTER[v] for v in NEW_EXPERTS]
    assert len({e["gender"] for e in experts}) >= 3
    assert len({e["accent"] for e in experts}) >= 3
    assert len({e["age"] for e in experts}) >= 3


def test_a_role_comes_from_the_label_not_from_a_name():
    assert vr.role_for_label("HOST:") == vr.HOST
    assert vr.role_for_label("expert") == vr.EXPERT
    assert vr.role_for_label("QUESTIONER:") == vr.HOST
    assert vr.role_for_label("CORRESPONDENT:") == vr.EXPERT
    assert vr.role_for_label("Matilda:") is None, "a name must not decide a role"


def test_each_role_reads_in_the_voice_the_request_asked_for():
    assert vr.voice_for_role(vr.HOST, host_voice_id="Xb7hH8MSUJpSbSDYk0k2") == "Xb7hH8MSUJpSbSDYk0k2"
    assert vr.voice_for_role(vr.EXPERT, expert_voice_id="SAz9YHcvj6GT2YYXdXww") == "SAz9YHcvj6GT2YYXdXww"
    assert vr.voice_for_role(vr.HOST) == vr.DEFAULT_HOST_ID
    assert vr.voice_for_role(vr.EXPERT) == vr.DEFAULT_EXPERT_ID
    assert vr.DEFAULT_HOST_ID not in vr.EXPERT_IDS, "the anchor host is not offered as an expert"


def test_the_service_names_voices_from_the_roster_and_not_from_its_own_map():
    text = (BACKEND / "elevenlabs_voice_service.py").read_text(encoding="utf-8")
    assert "voice_roster.id_to_name()" in text
    assert not re.search(r'VOICE_ID_TO_NAME = \{', text), "the hard-coded id-to-name maps should be gone"
    assert 'voice_roster.name_for(host_voice_id' in text and 'voice_roster.name_for(expert_voice_id' in text


def test_describe_reads_as_a_roster_line():
    assert vr.describe("cjVigY5qzO86Huf0OWal") == "Eric (male, middle aged, american): smooth, trustworthy"
    assert "not in the roster" in vr.describe("nope")
