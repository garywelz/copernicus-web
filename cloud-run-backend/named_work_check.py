"""Post-generation check: the script may name only confirmed papers (gap 3 fix 1, design 3.3).

One short model call finds every place where a specific work or its authors are named or alluded to (it returns
quotes, not judgments). Matching those mentions to the confirmed list is deterministic code: a listed author's
surname plus the year or title words. A mention that matches nothing is a violation; so is a "the link is in the
description" phrase that is not attached to a matched paper. The check fails closed: if it cannot run, the episode
is not accepted.

Nothing here knows about Firestore, audio or publishing. ``llm_call`` is injected so tests run offline.
"""
from __future__ import annotations

import asyncio
import json
import re
import unicodedata
from dataclasses import dataclass, field
from typing import Any, Awaitable, Callable, Dict, List, Optional, Sequence

LlmCall = Callable[[str, str], Awaitable[str]]  # (system, user) -> JSON text

PROMPT_ID = "NAMED-WORKS@1"
SYSTEM = ("You find named scientific works in a podcast script. You return JSON only and never judge whether anything is true.")
INSTRUCTIONS = (
    "List every place in the TEXT where a specific published work, study or its authors are named or alluded to, for example "
    "'Smith and Jones showed ...', 'a 2025 paper by Lee', a quoted paper title, 'according to the Nature paper by ...'. "
    "Include the attribution even when no title is given.\n"
    "Do NOT include: well-known theories, laws or people with no specific work attached (for example Einstein's relativity), "
    "institutions, companies, journals named on their own, or the podcast hosts.\n"
    "For each mention return: quote (copied verbatim from the TEXT, at most 200 characters), authors (the surnames as written, "
    "[] if none), year (an integer, or null), title_words (the distinctive words of any title quoted, [] if none).\n"
    "Return JSON: {\"mentions\": [{\"quote\": \"...\", \"authors\": [\"...\"], \"year\": 2025, \"title_words\": []}]}. "
    "Return {\"mentions\": []} if there are none."
)

LINK_PHRASE = re.compile(r"\b(?:links?|linked)\b[^.?!\n]{0,60}\b(?:description|show notes)\b|\bshow notes\b", re.I)


class NamingCheckUnavailable(Exception):
    """The check could not run (model error or unparseable answer). The episode must not be accepted unchecked."""


class NamingViolationError(Exception):
    """Raised when the script still names unlisted works after the allowed regenerations."""

    def __init__(self, violations: List[Dict[str, Any]]):
        self.violations = violations
        super().__init__(
            "The generated script names " + str(len(violations)) + " work(s) or phrase(s) that are not among the confirmed papers, "
            "and regeneration did not remove them, so no episode was published: " +
            "; ".join(violation_label(v) for v in violations[:6]) + ("; ..." if len(violations) > 6 else ""))


@dataclass
class NamingResult:
    violations: List[Dict[str, Any]] = field(default_factory=list)
    named_pids: List[str] = field(default_factory=list)  # confirmed papers the text names, in order of first mention
    mentions: List[Dict[str, Any]] = field(default_factory=list)  # every mention with its match

    @property
    def passed(self) -> bool:
        return not self.violations

    def summary(self) -> Dict[str, Any]:
        return {"passed": self.passed, "violations": self.violations, "named_pids": self.named_pids, "mentions": len(self.mentions)}


def violation_label(v: Dict[str, Any]) -> str:
    if v["kind"] == "unlisted_work":
        who = ", ".join(v.get("authors") or []) or "a work"
        return f"{who}{' (' + str(v['year']) + ')' if v.get('year') else ''}: \"{v['quote'][:80]}\""
    return f"a link-in-the-description phrase not attached to a listed paper: \"{v['quote'][:80]}\""


# ---------------------------------------------------------------- matching
def _norm(s: str) -> str:
    s = unicodedata.normalize("NFKD", s or "")
    s = "".join(ch for ch in s if not unicodedata.combining(ch))
    return re.sub(r"[^a-z0-9 ]", "", s.lower()).strip()


def _surname(author: str) -> str:
    parts = _norm(author).split()
    return parts[-1] if parts else ""


def _words(s: str) -> set:
    return {w for w in re.findall(r"[a-z0-9]{4,}", _norm(s))}


def match_mention(mention: Dict[str, Any], confirmed: Sequence[Any]) -> Optional[str]:
    """pid of the confirmed paper this mention refers to, or None. Deterministic."""
    names = {_norm(a).split()[-1] for a in (mention.get("authors") or []) if _norm(a)}
    tw = _words(" ".join(mention.get("title_words") or []))
    year = mention.get("year")
    for c in confirmed:
        csur = {_surname(a) for a in c.authors}
        title_overlap = len(tw & _words(c.title))
        if names & csur:
            if year is None or c.year is None or abs(int(year) - int(c.year)) <= 1 or title_overlap >= 2:
                return c.pid
        elif not names and title_overlap >= 3:
            return c.pid
    return None


def _locate(text: str, quote: str) -> int:
    q = re.sub(r"\s+", " ", quote or "").strip()[:60]
    if not q:
        return -1
    flat = re.sub(r"\s+", " ", text)
    return flat.find(q)


# ---------------------------------------------------------------- the check
async def _extract(llm_call: LlmCall, label: str, text: str) -> List[Dict[str, Any]]:
    user = f"{INSTRUCTIONS}\n\nTEXT ({label}):\n{text}"
    try:
        raw = await llm_call(SYSTEM, user)
    except Exception as e:
        raise NamingCheckUnavailable(f"named-work extraction failed: {type(e).__name__}: {e}")
    try:
        data = json.loads(re.sub(r"^```(?:json)?\s*|\s*```$", "", (raw or "").strip()))
        ms = data["mentions"]
        assert isinstance(ms, list)
    except Exception:
        raise NamingCheckUnavailable("named-work extraction returned an unparseable answer")
    out = []
    for m in ms:
        if not isinstance(m, dict) or not (m.get("quote") or "").strip():
            continue
        yr = m.get("year")
        out.append({"quote": str(m["quote"])[:200], "authors": [str(a) for a in (m.get("authors") or [])][:6],
                    "year": int(yr) if isinstance(yr, (int, float)) or (isinstance(yr, str) and yr.isdigit()) else None,
                    "title_words": [str(w) for w in (m.get("title_words") or [])][:12], "where": label})
    return out


async def check_naming(script: str, description: str, confirmed_papers: Sequence[Any], llm_call: LlmCall) -> NamingResult:
    """Check script and description. Raises NamingCheckUnavailable if the model step fails."""
    body = (description or "")
    # the code-built reference sections are added later; strip any model-written ones so they are not read as mentions
    body = re.split(r"(?im)^#{1,3}\s*(?:references|further reading|bibliography|sources)\s*$", body)[0]
    mentions = await _extract(llm_call, "script", script)
    if body.strip():
        mentions += await _extract(llm_call, "description", body)

    result = NamingResult()
    seen_pids: List[str] = []
    unknown_position_matched = False
    matched_positions: List[int] = []
    for m in mentions:
        pid = match_mention(m, confirmed_papers)
        m["pid"] = pid
        result.mentions.append(m)
        if pid:
            if pid not in seen_pids:
                seen_pids.append(pid)
            if m["where"] == "script":
                pos = _locate(script, m["quote"])
                if pos >= 0:
                    matched_positions.append(pos)
                else:
                    unknown_position_matched = True
        elif m["authors"] or m["title_words"]:
            result.violations.append({"kind": "unlisted_work", "where": m["where"], "quote": m["quote"],
                                      "authors": m["authors"], "year": m["year"]})
    result.named_pids = seen_pids

    flat = re.sub(r"\s+", " ", script)
    for ph in LINK_PHRASE.finditer(flat):
        near = any(ph.start() - 400 <= p <= ph.end() + 250 for p in matched_positions)
        if not near and not unknown_position_matched:
            result.violations.append({"kind": "link_phrase_unattached", "where": "script", "quote": ph.group(0)[:200]})
    return result


def feedback_text(result: NamingResult, confirmed_papers: Sequence[Any]) -> str:
    """Instructions added to the next generation attempt, listing what was wrong and what is allowed."""
    allowed = "; ".join(f"[{c.pid}] {', '.join(c.authors[:2])}{' et al.' if len(c.authors) > 2 else ''} ({c.year})" for c in confirmed_papers)
    lines = [violation_label(v) for v in result.violations]
    return (
        "\n\n**YOUR PREVIOUS SCRIPT WAS REJECTED because it named works that are not in the numbered list, or promised a link "
        "for a paper that is not in the list:**\n- " + "\n- ".join(lines) +
        f"\n\nRewrite it so that it names ONLY these papers: {allowed}. Remove every other author, study or paper from the script "
        "and the description, and say \"the link is in the description\" only right after naming one of these papers.\n")


def make_gemini_llm_call(api_key: str, model: str = "gemini-2.5-flash") -> LlmCall:
    """Production wrapper: the same Google AI key the generator already uses, temperature 0, JSON out."""
    async def call(system: str, user: str) -> str:
        import google.generativeai as genai
        genai.configure(api_key=api_key)

        def run() -> str:
            m = genai.GenerativeModel(model, system_instruction=system)
            r = m.generate_content(user, generation_config=genai.types.GenerationConfig(
                temperature=0, max_output_tokens=4096, response_mime_type="application/json"))
            return r.text
        return await asyncio.to_thread(run)
    return call
