"""Deterministic wording check for generated scripts and descriptions (fix 4, stage a).

The list of banned words and phrases lives in one file, config/banned_phrases.json. A hit is a reason to regenerate (the
sentence is quoted back to the model); after the allowed regenerations the episode fails. Nothing here calls a model, knows about
Firestore or publishes anything.
"""
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Dict, List, Optional

CONFIG_PATH = Path(__file__).resolve().parent / "config" / "banned_phrases.json"


class FinalTextCheckError(Exception):
    """The checks run again on the text that is stored and spoken found something the checks on the generated text did not."""

    def __init__(self, reason: str):
        self.reason = reason
        super().__init__("The final script did not pass the checks that were run again on the text to be published (" + reason +
                         "), so no episode was published.")


class BannedPhraseError(Exception):
    """Raised when the script still uses banned wording after the allowed regenerations."""

    def __init__(self, hits: List[Dict[str, Any]]):
        self.hits = hits
        phrases = sorted({h["phrase"] for h in hits})
        super().__init__("The generated script uses overstated or promotional wording (" + ", ".join(phrases) +
                         ") and regeneration did not remove it, so no episode was published.")


def load_banned_phrases(path: Optional[Path] = None) -> List[str]:
    data = json.loads((path or CONFIG_PATH).read_text(encoding="utf-8"))
    phrases = [str(p).strip() for p in data.get("banned_phrases", []) if str(p).strip()]
    if not phrases:
        raise ValueError("banned_phrases.json has no phrases")  # an empty list would silently switch the check off
    return phrases


def _pattern(phrase: str) -> "re.Pattern[str]":
    words = [w for w in re.split(r"[\s\-]+", phrase.strip()) if w]
    return re.compile(r"(?<![A-Za-z])" + r"[\s\-]+".join(re.escape(w) for w in words) + r"[A-Za-z]*", re.I)


def _sentence_around(text: str, start: int, end: int, limit: int = 240) -> str:
    """The sentence containing text[start:end]. A very long sentence is cut to a window around the match, never to its start."""
    left = max(text.rfind(".", 0, start), text.rfind("?", 0, start), text.rfind("!", 0, start), text.rfind("\n", 0, start)) + 1
    ends = [i for i in (text.find(c, end) for c in ".?!\n") if i != -1]
    right = (min(ends) + 1) if ends else len(text)
    sentence = text[left:right]
    if len(sentence) > limit:
        mid = start - left
        lo, hi = max(0, mid - limit // 2), min(len(sentence), mid + (end - start) + limit // 2)
        piece = sentence[lo:hi]
        if lo > 0:
            piece = "... " + piece.split(" ", 1)[-1]
        if hi < len(sentence):
            piece = piece.rsplit(" ", 1)[0] + " ..."
        sentence = piece
    return re.sub(r"\s+", " ", sentence).strip()


def banned_phrase_hits(script: str, description: str = "", phrases: Optional[List[str]] = None) -> List[Dict[str, Any]]:
    """Every use of a banned phrase in the script and in the description body (the code-built reference sections are not checked).
    Each hit: phrase (as listed), matched (as written), where, sentence."""
    phrases = phrases if phrases is not None else load_banned_phrases()
    body = re.split(r"(?im)^#{1,3}\s*(?:references|further reading|hashtags|episode details)\s*$", description or "")[0]
    hits = []
    for where, text in (("script", script or ""), ("description", body)):
        for phrase in phrases:
            for m in _pattern(phrase).finditer(text):
                hits.append({"phrase": phrase, "matched": m.group(0), "where": where, "sentence": _sentence_around(text, m.start(), m.end())})
    return hits


def banned_feedback(hits: List[Dict[str, Any]], phrases: Optional[List[str]] = None) -> str:
    """Instructions for the next attempt: the offending sentences quoted back, and the full list."""
    phrases = phrases if phrases is not None else load_banned_phrases()
    seen, lines = set(), []
    for h in hits:
        key = (h["where"], h["sentence"])
        if key not in seen:
            seen.add(key)
            lines.append(f'{h["where"]}: "{h["sentence"]}" (uses "{h["matched"]}")')
    return ("\n\n**YOUR PREVIOUS SCRIPT WAS REJECTED because it used overstated or promotional wording:**\n- " + "\n- ".join(lines[:12]) +
            "\n\nRewrite those passages in plain, precise language that says only what the cited papers say. Do not use any of these words or "
            "phrases anywhere in the script or the description: " + ", ".join(f'"{p}"' for p in phrases) + ".\n")


def prompt_list(phrases: Optional[List[str]] = None) -> str:
    return ", ".join(f'"{p}"' for p in (phrases if phrases is not None else load_banned_phrases()))
