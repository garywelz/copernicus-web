"""Text-to-speech usage for one generation run: how many characters were sent to ElevenLabs.

ElevenLabs bills by the characters of the text in each request, so the count is taken at the one place a request is made
(`ElevenLabsVoiceService._synthesize_segment`), per attempt: a request that fails still sent its characters, and is counted as
sent and as failed. Nothing here talks to ElevenLabs or to Firestore; the caller creates one `TtsUsage` per run, passes it
down, and stores `as_record()` on the job and the episode.

The warning-threshold hook (design decision Q7) is deliberately unset: `TTS_WARN_THRESHOLD_CHARACTERS` is None until Gary
names a number, and while it is None nothing is flagged and nothing is capped.
"""
from typing import Dict, Optional

# Set by Gary after reading the plan's allowance off the account page. None = record only (no warning, no cap).
TTS_WARN_THRESHOLD_CHARACTERS: Optional[int] = None

TTS_MODEL = "eleven_multilingual_v2"  # the model `_synthesize_segment` requests


def over_threshold(characters: int, threshold: Optional[int] = None) -> bool:
    """True when a threshold is set and the characters exceed it. With no threshold set, always False."""
    limit = TTS_WARN_THRESHOLD_CHARACTERS if threshold is None else threshold
    return limit is not None and characters > limit


class TtsUsage:
    """Characters sent to the text-to-speech service during one run, in total and per voice."""

    def __init__(self, model: str = TTS_MODEL):
        self.model = model
        self.characters = 0            # sent, every attempt
        self.segments = 0              # requests made
        self.failed_segments = 0
        self.characters_failed = 0
        self.by_voice: Dict[str, Dict[str, int]] = {}

    def sent(self, voice_id: str, text: str) -> None:
        """Call just before a request is made."""
        n = len(text)
        self.characters += n
        self.segments += 1
        v = self.by_voice.setdefault(voice_id, {"characters": 0, "segments": 0})
        v["characters"] += n
        v["segments"] += 1

    def failed(self, text: str) -> None:
        """Call when the request that `sent` counted did not succeed."""
        self.failed_segments += 1
        self.characters_failed += len(text)

    def as_record(self, threshold: Optional[int] = None) -> Dict[str, object]:
        """What is stored on the job and the episode. Counts only: no text, no addresses."""
        limit = TTS_WARN_THRESHOLD_CHARACTERS if threshold is None else threshold
        return {
            "tts_characters": self.characters,
            "tts_segments": self.segments,
            "tts_characters_succeeded": self.characters - self.characters_failed,
            "tts_failed_segments": self.failed_segments,
            "tts_characters_by_voice": {k: dict(v) for k, v in self.by_voice.items()},
            "tts_model": self.model,
            "tts_warn_threshold": limit,
            "tts_over_threshold": over_threshold(self.characters, limit),
        }
