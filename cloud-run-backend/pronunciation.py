"""How a word is said aloud, where the spelling would be read wrongly.

This applies ONLY to the text handed to the speech service. The script, the transcript and the episode's notes keep the real spelling, so
nothing a reader sees is altered and nothing a check reads is altered: "pi" stays "pi" everywhere except in the audio request, where it
becomes "pie" because the model otherwise reads it as the two letters.

Each entry is matched as a WHOLE word, case-insensitively, so "pivot", "pin" and "Spinoza" are untouched. A replacement keeps the case
shape of what it replaced, so a word at the start of a sentence still reads as one.
"""
import re
from typing import Dict, List, Tuple

# what is written -> how it should be said. Add an entry only where the model is heard to get it wrong.
SPOKEN_AS: Dict[str, str] = {
    "pi": "pie",
    "π": "pie",          # the Greek letter, if it ever reaches the audio text
}


def _match_case(original: str, replacement: str) -> str:
    if original.isupper() and len(original) > 1:
        return replacement.upper()
    if original[:1].isupper():
        return replacement[:1].upper() + replacement[1:]
    return replacement


def _pattern(written: str) -> "re.Pattern[str]":
    """A whole-word match. For a letter like π, which is not a word character, the boundary is the absence of a letter or digit."""
    if re.match(r"^\w", written, re.UNICODE) and written.isalnum():
        return re.compile(rf"(?<![^\W\d_]){re.escape(written)}(?![^\W\d_])", re.IGNORECASE | re.UNICODE)
    return re.compile(re.escape(written), re.IGNORECASE | re.UNICODE)


_COMPILED: List[Tuple["re.Pattern[str]", str]] = [(_pattern(w), s) for w, s in SPOKEN_AS.items()]


def for_speech(text: str) -> str:
    """`text` as it should be SAID. Never store this: it is the audio request's text and nothing else."""
    out = text or ""
    for pattern, spoken in _COMPILED:
        out = pattern.sub(lambda m: _match_case(m.group(0), spoken), out)
    return out


def changes(text: str) -> List[Dict[str, str]]:
    """Which entries would be applied, for a report or a test. Each: written, spoken, count."""
    found = []
    for (pattern, spoken), written in zip(_COMPILED, SPOKEN_AS):
        n = len(pattern.findall(text or ""))
        if n:
            found.append({"written": written, "spoken": spoken, "count": str(n)})
    return found
