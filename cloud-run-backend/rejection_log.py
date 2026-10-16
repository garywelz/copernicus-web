"""Complete records of everything a generated script was rejected for (fix 5).

Each item is a plain dict that is logged in full (one structured log line per item) and stored on the job record, so that whoever judges a
check can read the whole sentence, the paper it was pinned on, that paper's abstract, the verdict and the reason, not a 160-character
excerpt. Nothing here calls a model or knows about Firestore.
"""
from __future__ import annotations

from typing import Any, Dict, List, Sequence


def naming_items(attempt: int, violations: Sequence[Dict[str, Any]]) -> List[Dict[str, Any]]:
    return [{"attempt": attempt, "check": "naming", "kind": v.get("kind"), "where": v.get("where"), "quote": v.get("quote"),
             "authors": v.get("authors"), "year": v.get("year"), "context": v.get("context")} for v in violations]


def banned_items(attempt: int, hits: Sequence[Dict[str, Any]]) -> List[Dict[str, Any]]:
    return [{"attempt": attempt, "check": "banned_wording", "phrase": h.get("phrase"), "matched": h.get("matched"), "where": h.get("where"),
             "sentence": h.get("sentence")} for h in hits]


def notation_items(attempt: int, problems: Sequence[str]) -> List[Dict[str, Any]]:
    return [{"attempt": attempt, "check": "notation", "problem": p} for p in problems]


def attribution_items(attempt: int, checked: Sequence[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """One item per attribution the model reported. Supported ones are kept too (without the abstract, to save space) so that a later
    re-check can be compared with the production verdict sentence by sentence; unsupported ones carry the whole abstract."""
    return [{"attempt": attempt, "check": "attribution", "verdict": c.get("verdict"), "quote": c.get("quote"), "pid": c.get("pid"),
             "paper": c.get("title"), "authors": c.get("authors"), "year": c.get("year"),
             "abstract": c.get("abstract") if c.get("verdict") == "unsupported" else None, "reason": c.get("reason")} for c in checked]


def coverage_items(attempt: int, missing) -> List[Dict[str, Any]]:
    return [{"attempt": attempt, "check": "coverage_statement", "name": n,
             "problem": "the topic names this, no confirmed paper covers it, and the script does not say the papers do not cover it"} for n in missing]


def read_aloud_items(attempt: int, sentences) -> List[Dict[str, Any]]:
    return [{"attempt": attempt, "check": "topic_read_aloud", "sentence": s} for s in sentences]


def length_item(attempt: int, kind: str, words: int, limit: int) -> Dict[str, Any]:
    return {"attempt": attempt, "check": kind, "words": words, "limit": limit}


def transient_item(attempt: int, stage: str, error: Exception) -> Dict[str, Any]:
    item = {"attempt": attempt, "check": "transient_error", "stage": stage, "error_type": type(error).__name__, "error": str(error)[:300]}
    raw = getattr(error, "raw", "")
    if raw:
        item["raw_head"] = str(raw)[:300]       # what the model actually answered when its answer could not be read
    return item
