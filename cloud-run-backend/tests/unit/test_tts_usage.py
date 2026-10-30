"""Text-to-speech character count (curated-sources design C0, decision Q7): every character sent to ElevenLabs is counted, per
request, including by requests that fail, and stored on the job and the episode. The warning-threshold hook exists and is unset."""
import ast
import asyncio
import os
import sys
from unittest.mock import MagicMock, patch

import pytest

try:
    import psutil  # noqa: F401
except ImportError:
    sys.modules["psutil"] = MagicMock()

import tts_usage
from tts_usage import TtsUsage, over_threshold

try:
    import elevenlabs_voice_service as evs
except Exception as e:  # pragma: no cover - environment without the service's dependencies
    pytest.skip(f"voice service not importable here: {e}", allow_module_level=True)

BACKEND = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def run(coro):
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


def make_service():
    svc = object.__new__(evs.ElevenLabsVoiceService)       # skip __init__: it reads Secret Manager
    svc.api_key = "not-a-real-key"
    svc.base_url = "https://example.invalid/v1"
    svc.voice_configs = {
        "host": evs.ElevenLabsVoiceConfig(voice_id="voice-host", speaker_name="Host", voice_description="h"),
        "expert": evs.ElevenLabsVoiceConfig(voice_id="voice-expert", speaker_name="Expert", voice_description="e"),
    }
    return svc


# --- the tally ---------------------------------------------------------------------------------------------------

def test_tally_counts_characters_segments_and_voices():
    u = TtsUsage()
    u.sent("v1", "hello")           # 5
    u.sent("v2", "twelve chars")    # 12
    u.sent("v1", "again")           # 5
    r = u.as_record()
    assert r["tts_characters"] == 22 and r["tts_segments"] == 3
    assert r["tts_characters_by_voice"] == {"v1": {"characters": 10, "segments": 2}, "v2": {"characters": 12, "segments": 1}}
    assert r["tts_failed_segments"] == 0 and r["tts_characters_succeeded"] == 22
    assert r["tts_model"] == "eleven_multilingual_v2"


def test_a_failed_request_still_counts_as_sent_and_is_also_counted_as_failed():
    u = TtsUsage()
    u.sent("v1", "abcdefghij")
    u.failed("abcdefghij")
    r = u.as_record()
    assert r["tts_characters"] == 10 and r["tts_segments"] == 1
    assert r["tts_failed_segments"] == 1 and r["tts_characters_succeeded"] == 0


def test_characters_are_unicode_characters_not_bytes():
    u = TtsUsage()
    u.sent("v", "Gödel — ∑")        # 9 characters, more bytes
    assert u.as_record()["tts_characters"] == 9


def test_a_fresh_tally_is_all_zero_and_carries_the_headline_fields():
    r = TtsUsage().as_record()
    assert r["tts_characters"] == 0 and r["tts_segments"] == 0
    assert {"tts_characters", "tts_segments"} <= set(r)


def test_the_record_holds_counts_only_no_text():
    u = TtsUsage()
    u.sent("v", "a secret sentence that must not be stored")
    assert "secret sentence" not in repr(u.as_record())


# --- the warning-threshold hook is unset (Q7) -------------------------------------------------------------------------------

def test_no_threshold_is_set_and_nothing_is_flagged_however_long_the_run():
    assert tts_usage.TTS_WARN_THRESHOLD_CHARACTERS is None
    u = TtsUsage()
    u.sent("v", "x" * 10_000_000)
    r = u.as_record()
    assert r["tts_warn_threshold"] is None and r["tts_over_threshold"] is False
    assert over_threshold(10 ** 9) is False


def test_the_hook_flags_when_a_threshold_is_given_or_set():
    assert over_threshold(101, threshold=100) is True and over_threshold(100, threshold=100) is False
    with patch.object(tts_usage, "TTS_WARN_THRESHOLD_CHARACTERS", 50):
        u = TtsUsage()
        u.sent("v", "x" * 51)
        r = u.as_record()
        assert r["tts_warn_threshold"] == 50 and r["tts_over_threshold"] is True


# --- counted at the one place a request is made ---------------------------------------------------------------------------

def test_synthesize_segment_counts_the_text_it_sends_on_success():
    svc, u = make_service(), TtsUsage()
    with patch.object(svc, "_request_speech", return_value=(b"mp3", 1.0)) as req:
        run(svc._synthesize_segment("exactly thirty characters long", svc.voice_configs["host"], usage=u))
    assert req.call_count == 1
    assert u.as_record()["tts_characters"] == len("exactly thirty characters long") == 30
    assert u.failed_segments == 0


def test_synthesize_segment_counts_the_text_when_the_request_fails_and_reraises():
    svc, u = make_service(), TtsUsage()

    async def boom(text, cfg):
        raise ConnectionError("dropped")
    with patch.object(svc, "_request_speech", boom):
        with pytest.raises(ConnectionError):
            run(svc._synthesize_segment("twenty characters!!!", svc.voice_configs["host"], usage=u))
    assert u.characters == 20 and u.segments == 1 and u.failed_segments == 1 and u.characters_failed == 20


def test_an_error_status_from_the_service_counts_as_sent_and_failed():
    svc, u = make_service(), TtsUsage()
    with patch.object(evs.aiohttp, "ClientSession", return_value=_FakeSession(status=429)):
        with pytest.raises(Exception, match="429"):
            run(svc._synthesize_segment("0123456789", svc.voice_configs["expert"], usage=u))
    assert u.characters == 10 and u.failed_segments == 1
    assert u.by_voice == {"voice-expert": {"characters": 10, "segments": 1}}


def test_without_a_tally_nothing_changes_and_nothing_is_counted():
    svc = make_service()
    with patch.object(svc, "_request_speech", return_value=(b"mp3", 1.0)):
        assert run(svc._synthesize_segment("text", svc.voice_configs["host"])) == (b"mp3", 1.0)


def test_a_whole_run_counts_exactly_the_characters_of_the_segments_it_sends_including_one_that_fails():
    svc, u = make_service(), TtsUsage()
    script = "HOST: First line of the show.\n\nEXPERT: A second line that is a little longer than the first.\n\nHOST: Third."
    sent_texts = []

    async def fake_request(text, cfg):
        sent_texts.append(text)
        if len(sent_texts) == 2:
            raise OSError("second request fails")
        return b"mp3", 1.0

    async def combine(segments):
        return b"".join(segments)

    async def bumpers(audio, intro, outro):
        return audio
    with patch.object(svc, "_request_speech", fake_request), patch.object(svc, "_combine_audio_segments", combine), \
         patch.object(svc, "add_audio_bumpers", bumpers), patch("google.cloud.storage.Client", MagicMock()), \
         patch.object(evs.media_store, "public_url", return_value="https://example.invalid/a.mp3"):
        run(svc.generate_multi_voice_audio_with_bumpers(script, "job", "canon", "i", "o", tts_usage=u))
    assert len(sent_texts) == 3
    assert u.characters == sum(len(t) for t in sent_texts) > 0
    assert u.segments == 3 and u.failed_segments == 1
    assert u.characters_failed == len(sent_texts[1])


def test_a_whole_run_without_a_tally_still_works():
    svc = make_service()

    async def fake_request(text, cfg):
        return b"mp3", 1.0

    async def combine(segments):
        return b"".join(segments)

    async def bumpers(audio, intro, outro):
        return audio
    with patch.object(svc, "_request_speech", fake_request), patch.object(svc, "_combine_audio_segments", combine), \
         patch.object(svc, "add_audio_bumpers", bumpers), patch("google.cloud.storage.Client", MagicMock()), \
         patch.object(evs.media_store, "public_url", return_value="https://example.invalid/a.mp3"):
        assert run(svc.generate_multi_voice_audio_with_bumpers("HOST: Only line.", "job", "canon", "i", "o")).endswith(".mp3")


# --- wiring in the generation service (source level: the service module is too large to run end to end here) ------------------

def _service_tree():
    return ast.parse(open(os.path.join(BACKEND, "services", "podcast_generation_service.py"), encoding="utf-8").read())


def _calls(tree, attr):
    return [n for n in ast.walk(tree) if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute) and n.func.attr == attr]


def test_the_service_passes_a_tally_to_the_audio_call():
    calls = _calls(_service_tree(), "generate_multi_voice_audio_with_bumpers")
    assert len(calls) == 1 and "tts_usage" in {k.arg for k in calls[0].keywords}


def test_the_service_stores_the_usage_on_the_job_even_when_the_audio_step_fails():
    tree = _service_tree()
    tries = [n for n in ast.walk(tree) if isinstance(n, ast.Try) and n.finalbody and any(
        isinstance(c, ast.Call) and getattr(c.func, "attr", "") == "generate_multi_voice_audio_with_bumpers"
        for b in n.body for c in ast.walk(b))]
    assert len(tries) == 1
    final_src = "\n".join(ast.unparse(s) for s in tries[0].finalbody)
    assert "job_ref.update(tts_usage.as_record())" in final_src


def test_the_job_result_and_the_episode_record_both_carry_the_usage():
    src = open(os.path.join(BACKEND, "services", "podcast_generation_service.py"), encoding="utf-8").read()
    assert src.count("**tts_usage.as_record()") == 2        # the completed job update, and the episode document


def test_the_new_module_is_in_the_image():
    assert os.path.exists(os.path.join(BACKEND, "tts_usage.py"))
    assert "COPY . ." in open(os.path.join(BACKEND, "Dockerfile"), encoding="utf-8").read()


# --- helpers ---------------------------------------------------------------------------------------------------------------

class _FakeResponse:
    def __init__(self, status):
        self.status = status

    async def __aenter__(self):
        return self

    async def __aexit__(self, *a):
        return False

    async def text(self):
        return "rate limited"

    async def read(self):
        return b"mp3"


class _FakeSession:
    def __init__(self, status):
        self._status = status

    async def __aenter__(self):
        return self

    async def __aexit__(self, *a):
        return False

    def post(self, *a, **k):
        return _FakeResponse(self._status)
