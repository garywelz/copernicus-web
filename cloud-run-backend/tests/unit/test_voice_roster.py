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


# --- the roles the voices actually read -------------------------------------------------------------------------------------------
SCRIPT = ("HOST: What did the paper show?\n"
          "EXPERT: It designed an enzyme from scratch.\n"
          "HOST: And what is left open?\n"
          "EXPERT: Whether the design holds outside the laboratory.\n")


def segments_for(host_id, expert_id, script=SCRIPT):
    from elevenlabs_voice_service import ElevenLabsVoiceService
    svc = ElevenLabsVoiceService.__new__(ElevenLabsVoiceService)
    svc.voice_configs = {}
    return ElevenLabsVoiceService._parse_script_segments(svc, script, host_voice_id=host_id, expert_voice_id=expert_id)


def test_bill_and_bella_as_experts_read_only_the_expert_lines():
    """Bill used to mean "questioner" and Bella "host" in a table of guessed names, whatever voice the episode was given."""
    for expert_id, name in (("pqHfZKP75CvOlQylNhV4", "Bill"), ("hpp4J3VqNfWAUOO0d1Us", "Bella")):
        segs = segments_for(vr.DEFAULT_HOST_ID, expert_id)
        roles = [x["speaker"] for x in segs]
        assert roles == ["host", "expert", "host", "expert"], f"{name}: {roles}"
        expert_lines = " ".join(x["content"] for x in segs if x["speaker"] == "expert")
        assert "designed an enzyme" in expert_lines and "What did the paper show" not in expert_lines


def test_a_bare_name_no_voice_answers_to_does_not_start_a_speaker():
    script = "HOST: A question.\nMarcus: and a line that names nobody in this episode.\nEXPERT: An answer.\n"
    segs = segments_for(vr.DEFAULT_HOST_ID, "cjVigY5qzO86Huf0OWal", script)
    assert [x["speaker"] for x in segs] == ["host", "expert"]
    assert "names nobody" in segs[0]["content"], "the stray line stays with the speaker who was talking"


def test_the_service_no_longer_guesses_a_role_from_a_name():
    text = (BACKEND / "elevenlabs_voice_service.py").read_text(encoding="utf-8")
    assert "fallback_mappings" not in text
    assert '"bill": "questioner"' not in text and '"bella": "host"' not in text
    assert "voice_roster.role_for_label(" in text, "a label decides the role"
    assert "voice_roster.voice_for_role(" in text, "a role decides the voice"


# --- the rotation ------------------------------------------------------------------------------------------------------------------
def test_the_rotation_never_pairs_the_host_with_a_too_similar_expert():
    """Matilda is a middle-aged American woman, and so is Bella: two of those are hard to tell apart as the two speakers."""
    order = vr.rotation_for(vr.DEFAULT_HOST_ID)
    assert "hpp4J3VqNfWAUOO0d1Us" not in order, "Bella matches Matilda in gender and accent"
    assert vr.DEFAULT_HOST_ID not in order, "the host does not also take the expert chair"
    for vid in order:
        assert not vr.too_similar(vr.DEFAULT_HOST_ID, vid), vr.describe(vid)
    assert len(order) == 7, order


def test_too_similar_needs_both_gender_and_accent():
    assert vr.too_similar("XrExE9yKIg1WjnnlVkGX", "hpp4J3VqNfWAUOO0d1Us") is True      # both female American
    assert vr.too_similar("XrExE9yKIg1WjnnlVkGX", "Xb7hH8MSUJpSbSDYk0k2") is False     # female, but British
    assert vr.too_similar("XrExE9yKIg1WjnnlVkGX", "cjVigY5qzO86Huf0OWal") is False     # American, but male


def test_the_rotation_comes_round_in_a_fixed_order():
    order = vr.rotation_for(vr.DEFAULT_HOST_ID)
    picks = [vr.expert_for_episode(n) for n in range(len(order) * 2)]
    assert picks[:len(order)] == list(order)
    assert picks[len(order):] == list(order), "it comes round again in the same order"
    assert vr.expert_for_episode(0) == vr.DEFAULT_EXPERT_ID


def test_a_requested_expert_still_wins():
    text = (BACKEND / "services" / "podcast_generation_service.py").read_text(encoding="utf-8")
    assert "if request.expert_voice_id:" in text
    assert 'expert_voice_id, expert_source = request.expert_voice_id, "requested"' in text


def test_the_voice_used_is_recorded_on_the_job():
    text = (BACKEND / "services" / "podcast_generation_service.py").read_text(encoding="utf-8")
    assert '"voices": {"host_voice_id"' in text
    for field in ("expert_voice_id", "expert_name", "host_name", "expert_chosen_by"):
        assert field in text, f"the record should name {field}"


def test_a_series_may_be_given_its_own_host_but_none_is():
    assert vr.SERIES_HOST == {}, "no series has its own host yet"
    assert vr.host_for_series("Biology") == vr.DEFAULT_HOST_ID
    assert vr.host_for_series(None) == vr.DEFAULT_HOST_ID
    assert vr.host_for_series("a series that does not exist") == vr.DEFAULT_HOST_ID


def test_a_series_host_changes_the_rotation_it_is_paired_with(monkeypatch):
    """Whatever host a series is ever given, the rotation drops the experts too like it."""
    monkeypatch.setitem(vr.SERIES_HOST, "physics", "cjVigY5qzO86Huf0OWal")        # Eric: a middle-aged American man
    host = vr.host_for_series("Physics")
    assert host == "cjVigY5qzO86Huf0OWal"
    order = vr.rotation_for(host)
    assert "cjVigY5qzO86Huf0OWal" not in order and "pqHfZKP75CvOlQylNhV4" not in order, "Bill is also an American man"
    assert "Xb7hH8MSUJpSbSDYk0k2" in order and "hpp4J3VqNfWAUOO0d1Us" in order


# --- what a script may never do ---------------------------------------------------------------------------------------------------
def test_the_speakers_are_never_given_character_names():
    """The voices have names in the roster; the script's speakers are HOST and EXPERT and nothing else."""
    rules = __import__("curated_script").SHOW_RULES
    assert "Nobody has a first name" in rules
    assert "Every non-empty line starts with HOST: or EXPERT:" in rules
    for name in ("Matilda", "Adam", "Eric", "Alice", "Bella", "Bill"):
        assert name not in rules, f"the rules must not put {name} in a script"
    templates = {t[0]: t[3] for t in __import__("curated_script").SECTION_TEMPLATES}
    for key, text in templates.items():
        for name in ("Matilda", "Adam", "Eric", "Alice", "Bella", "Bill"):
            assert name not in text, f"the {key} template names {name}"


def test_the_opening_goes_straight_into_the_topic():
    """No greeting, no welcome, no show name, no sign-off: the bumpers do that, and a script that does it too repeats itself."""
    import curated_script as cs
    opening = {t[0]: t[3] for t in cs.SECTION_TEMPLATES}["opening"]
    assert "No greeting" in opening and "no welcome" in opening
    assert "does not name the show" in opening
    closing = {t[0]: t[3] for t in cs.SECTION_TEMPLATES}["closing"]
    assert "no sign-off" in closing or "No sign-off" in closing
    from script_style import GREETING_PHRASES, greeting_hits
    for phrase in ("welcome to", "thanks for listening", "i'm your host", "in this episode", "until next time"):
        assert phrase in GREETING_PHRASES, f"{phrase!r} should be refused outright"
    greeted = "HOST: Welcome to the programme. In this episode we look at enzymes.\nEXPERT: Thanks for listening.\n"
    kinds_found = {h["phrase"] for h in greeting_hits(greeted)}
    assert {"welcome to", "in this episode", "thanks for listening"} <= kinds_found
    assert greeting_hits("HOST: For decades this was out of reach.\nEXPERT: It was.\n") == []


def test_both_check_paths_refuse_a_greeting():
    text = (BACKEND / "curated_pipeline.py").read_text(encoding="utf-8")
    assert text.count("greeting_hits(script)") == 2, "the generated and the supplied path both check it"
    assert text.count('"kind": "greeting_or_sign_off"') == 2


def test_the_ordinary_prompt_no_longer_tells_the_host_to_greet():
    """Ordinary mode instructed the host to introduce the show as "Welcome to ..." and gave an example that greeted and thanked."""
    text = (BACKEND / "services" / "podcast_generation_service.py").read_text(encoding="utf-8")
    assert "Welcome to {CHANNEL_NAME_SPOKEN}" not in text
    assert "does NOT greet the listener" in text
    assert "Thank you for having me" not in text
