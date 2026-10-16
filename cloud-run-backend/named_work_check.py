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
    "For each mention return: quote (copied verbatim from the TEXT, at most 200 characters), authors (the surnames as written, with the first name or initials added when the text gives them, "
    "[] if none), year (an integer, or null), title_words (the distinctive words of any title quoted, [] if none).\n"
    "Return JSON: {\"mentions\": [{\"quote\": \"...\", \"authors\": [\"...\"], \"year\": 2025, \"title_words\": []}]}. "
    "Return {\"mentions\": []} if there are none. In quotes, write any mathematical notation as plain words or leave it out: "
    "never put a backslash or LaTeX command in the JSON."
)

LINK_PHRASE = re.compile(r"\b(?:links?|linked)\b[^.?!\n]{0,60}\b(?:description|show notes)\b|\bshow notes\b", re.I)


class NamingCheckUnavailable(Exception):
    """The check could not run (model error or unparseable answer). The episode must not be accepted unchecked."""

    def __init__(self, message: str, raw: str = ""):
        self.raw = (raw or "")[:300]  # start of the model's answer, for the administrator's diagnosis only
        super().__init__(message)


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


GROUP_MARKERS = ("collaboration", "consortium", "group", "team")


def _name_tokens(s: str) -> set:
    return {w for w in _norm(s).split() if w not in ("the", "and") and w not in GROUP_MARKERS}


def _surname_compatible(mention_author: str, listed_author: str) -> bool:
    """Same surname, and (when both give a first name or initial) the same first initial: 'Guanrui Wang' is not 'Yi Wang',
    but 'S. Wang' is 'Song Wang' and a bare 'Wang' matches either."""
    m, l = _norm(mention_author).split(), _norm(listed_author).split()
    if not m or not l or m[-1] != l[-1] or m[-1] in GROUP_MARKERS:
        return False
    if len(m) >= 2 and len(l) >= 2 and m[0][0] != l[0][0]:
        return False
    return True


_NOT_A_GIVEN_NAME = set("""and by the of from with in to as at for on according per that this their his her its our then so but also while when
first second third next now however similarly meanwhile recently today early later we it he she they what where which who how why if because since
after before during although yet still just even only both each every some any many most other another such like via without within among between
through these those there here again once further indeed""".split())


def _with_given_names(authors: Sequence[str], quote: str) -> List[str]:
    """The model is asked for surnames; when the quote shows a capitalised first name or initial right before a
    surname ('Song Wang', 'M.F. Perutz'), put it back so common surnames are not matched to the wrong person."""
    out = []
    for a in authors:
        if len(_norm(a).split()) == 1 and a.strip():
            m = re.search(r"((?:[A-Z][a-z\-']+|(?:[A-Z]\.\s?)+))\s+" + re.escape(a.strip()) + r"(?![A-Za-z])", quote or "")
            if m and _norm(m.group(1)).split() and _norm(m.group(1)).split()[0] not in _NOT_A_GIVEN_NAME:
                out.append(f"{m.group(1)} {a.strip()}")
                continue
        out.append(a)
    return out


def _tokens(s: str) -> List[str]:
    """Name tokens: accents, case and punctuation removed; a comma only separates tokens, so "Liu, Zhiqiang" and
    "Zhiqiang Liu" give the same tokens."""
    s = unicodedata.normalize("NFKD", s or "")
    s = "".join(ch for ch in s if not unicodedata.combining(ch)).lower()
    return [x for x in re.sub(r"[^a-z0-9]+", " ", s).split() if x]


def _token_match(a: str, b: str) -> bool:
    return a == b or (len(a) == 1 and b.startswith(a)) or (len(b) == 1 and a.startswith(b))


def _name_match(mention_author: str, listed_author: str) -> bool:
    """Order-free name match (handles "Surname, Given", "Given Surname" and compound surnames like "Valadez Huerta").
    Every token of the mention must match a token of the listed author (a one-letter token matches a token starting with
    it), and at least one mention word longer than one letter must equal a listed token exactly, so that an initial on the
    listed side ("R. D. L. Henderson") cannot stand in for a whole surname ("Robert L. Devaney")."""
    skip = set(GROUP_MARKERS) | {"the", "and"}
    m = [x for x in _tokens(mention_author) if x not in skip]
    l = [x for x in _tokens(listed_author) if x not in {"the", "and"}]
    if not m or not l:
        return False
    return all(any(_token_match(a, b) for b in l) for a in m) and any(len(a) > 1 and a in l for a in m)


def _group_sets(paper: Any) -> List[set]:
    """Token sets of a paper's group authors ("The LIGO Scientific Collaboration" -> {ligo, scientific}), whose
    surname-by-last-word would be the useless word "collaboration"."""
    return [_name_tokens(a) for a in paper.authors if any(m in _norm(a).split() for m in GROUP_MARKERS) and _name_tokens(a)]


def match_mention(mention: Dict[str, Any], confirmed: Sequence[Any], named_before: Sequence[str] = ()) -> Optional[str]:
    """pid of the confirmed paper this mention refers to, or None. Deterministic. `named_before` is the pids already matched
    earlier in the same text, used only to resolve a later "Alama's 2011 research" that gives no title."""
    names = {_norm(a).split()[-1] for a in (mention.get("authors") or []) if _norm(a)} - set(GROUP_MARKERS)  # empty means no usable author
    full_names = _with_given_names(mention.get("authors") or [], mention.get("quote") or "")
    mention_groups = [_name_tokens(a) for a in (mention.get("authors") or []) if _name_tokens(a)]
    quote_words = set(_norm(mention.get("quote") or "").split())
    tw = _words(" ".join(mention.get("title_words") or []))
    qw = _words(mention.get("quote") or "")  # title words can sit in the quoted passage itself ("work on `mizar-items`")
    year = mention.get("year")
    candidates = []  # (paper, title_overlap) for every paper the author and year (or title) fit
    for c in confirmed:
        gsets = _group_sets(c)
        title_overlap = len(tw & _words(c.title))
        year_ok = year is None or c.year is None or abs(int(year) - int(c.year)) <= 1 or title_overlap >= 2
        by_surname = any(_name_match(ma, la) for ma in full_names for la in c.authors)
        by_group = any(m and m <= g for m in mention_groups for g in gsets)
        by_group_in_quote = not names and any(g <= quote_words for g in gsets) and year is not None  # "the BESIII Collaboration's 2026 ..." with no author listed
        if by_surname or by_group or by_group_in_quote:
            if year_ok:
                candidates.append((c, len((tw | qw) & _words(c.title)) if tw or qw else 0))
        elif not names and title_overlap >= 3:
            candidates.append((c, title_overlap))
    if not candidates:
        return None
    if len(candidates) == 1 or not (year or tw):
        return candidates[0][0].pid  # one fit, or a bare "Alama's work" that names no specific paper
    # Several listed works fit the author and year: the title decides, otherwise nothing is matched (fail closed).
    exact = [x for x in candidates if year is not None and x[0].year is not None and int(x[0].year) == int(year)]
    pool = exact or candidates
    if len(pool) == 1:
        return pool[0][0].pid
    ranked = sorted(pool, key=lambda x: x[1], reverse=True)
    if ranked[0][1] >= 2 and ranked[0][1] > ranked[1][1]:
        return ranked[0][0].pid
    # No title decides. A mention that gives no title at all ("Alama's 2011 research") refers back to a paper already named
    # in the text, but only when exactly one of the competing papers has been named before it.
    if not tw:
        earlier = [x[0].pid for x in pool if x[0].pid in set(named_before)]
        if len(earlier) == 1:
            return earlier[0]
    return None


def context_around(text: str, quote: str, span: int = 450) -> str:
    """A few sentences of the checked text around a quoted passage (about 450 characters each side, trimmed to word
    boundaries), so whoever reviews a flag can read it in place. '' if the quote cannot be found."""
    flat = re.sub(r"\s+", " ", text or "")
    q = re.sub(r"\s+", " ", quote or "").strip()[:60]
    i = flat.find(q) if q else -1
    if i < 0:
        return ""
    a, b = max(0, i - span), min(len(flat), i + len(quote) + span)
    if a > 0:
        a = flat.find(" ", a) + 1 or a
    if b < len(flat):
        b = flat.rfind(" ", 0, b) if flat.rfind(" ", 0, b) > i else b
    return flat[a:b].strip()


def _locate(text: str, quote: str) -> int:
    q = re.sub(r"\s+", " ", quote or "").strip()[:60]
    if not q:
        return -1
    flat = re.sub(r"\s+", " ", text)
    return flat.find(q)


def _parse(raw: str):
    """JSON from the model's answer: plain, then with code fences removed, then with stray backslashes (LaTeX in a
    quoted passage is not a valid JSON escape) doubled. Returns None if nothing parses."""
    text = re.sub(r"^```(?:json)?\s*|\s*```$", "", (raw or "").strip())
    for variant in (text, text.replace("\\", "\\\\").replace('\\\\"', '\\"')):
        try:
            return json.loads(variant)
        except Exception:
            pass
        i = variant.find("{")
        if i > 0:
            try:
                return json.JSONDecoder().raw_decode(variant[i:])[0]
            except Exception:
                pass
    return None


# ---------------------------------------------------------------- the check
async def _extract(llm_call: LlmCall, label: str, text: str) -> List[Dict[str, Any]]:
    user = f"{INSTRUCTIONS}\n\nTEXT ({label}):\n{text}"
    try:
        raw = await llm_call(SYSTEM, user)
    except Exception as e:
        raise NamingCheckUnavailable(f"named-work extraction failed: {type(e).__name__}: {e}")
    data = _parse(raw)
    ms = data.get("mentions") if isinstance(data, dict) else None
    if not isinstance(ms, list):
        raise NamingCheckUnavailable("named-work extraction returned an unparseable answer", raw)
    out = []
    for m in ms:
        if not isinstance(m, dict) or not (m.get("quote") or "").strip():
            continue
        yr = m.get("year")
        out.append({"quote": str(m["quote"])[:200], "authors": [str(a) for a in (m.get("authors") or [])][:6],
                    "year": int(yr) if isinstance(yr, (int, float)) or (isinstance(yr, str) and yr.isdigit()) else None,
                    "title_words": [str(w) for w in (m.get("title_words") or [])][:12], "where": label})
    return out


# The episode's own topic is not a work: a host who says 'today we're exploring "<the topic>"' has quoted the question, not a paper.
TOPIC_OVERLAP = 0.8
MIN_TOPIC_WORDS = 4


def is_topic_mention(mention: Dict[str, Any], topic: Optional[str]) -> bool:
    """True when a mention without authors quotes (nearly) the episode topic itself."""
    if not topic or mention.get("authors"):
        return False
    topic_words = _words(topic)
    for text in (mention.get("quote") or "", " ".join(mention.get("title_words") or [])):
        words = _words(text)
        if len(words) >= MIN_TOPIC_WORDS and len(words & topic_words) / len(words) >= TOPIC_OVERLAP:
            return True
    return False


# A tool or system the host names without an author ("tools like 'mizar-items'") is not an unlisted paper when a listed paper's own title or
# abstract uses that name: the listed paper is where the name comes from. A name that no listed paper mentions is still a violation.
_QUOTED_NAME = re.compile(r"""`([^`]{3,60})`|"([^"]{3,60})"|(?<![A-Za-z0-9])'([^']{3,60})'(?![A-Za-z0-9])|\u2018([^\u2019]{3,60})\u2019|\u201c([^\u201d]{3,60})\u201d""")


def tool_names(mention: Dict[str, Any]) -> List[str]:
    names = []
    for m in _QUOTED_NAME.finditer(mention.get("quote") or ""):
        name = next(g for g in m.groups() if g)
        if len(name.split()) <= 4 and _norm(name):
            names.append(name)
    if not names:
        tw = [w for w in (mention.get("title_words") or []) if _norm(w)]
        if 1 <= len(tw) <= 2:
            names = tw
    return names


def match_tool_name(mention: Dict[str, Any], confirmed: Sequence[Any]) -> Optional[str]:
    """pid of the listed paper whose title or abstract contains every name the mention quotes, or None. Only for mentions without authors."""
    if mention.get("authors"):
        return None
    names = tool_names(mention)
    if not names:
        return None
    for c in confirmed:
        text = _norm(f"{c.title} {getattr(c, 'abstract', '') or ''}")
        if all(_norm(n) in text for n in names):
            return c.pid
    return None


async def check_naming(script: str, description: str, confirmed_papers: Sequence[Any], llm_call: LlmCall, topic: Optional[str] = None) -> NamingResult:
    """Check script and description. Raises NamingCheckUnavailable if the model step fails. `topic`: a quoted passage that is the episode's own
    topic is not a work."""
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
        pid = match_mention(m, confirmed_papers, seen_pids)
        if pid is None and is_topic_mention(m, topic):
            m["pid"], m["ignored"] = None, "episode topic"
            result.mentions.append(m)
            continue
        if pid is None:
            pid = match_tool_name(m, confirmed_papers)
            if pid:
                m["matched_by"] = "tool name in the paper's title or abstract"
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
                                      "authors": m["authors"], "year": m["year"],
                                      "context": context_around(script if m["where"] == "script" else body, m["quote"])})
    result.named_pids = seen_pids

    flat = re.sub(r"\s+", " ", script)
    for ph in LINK_PHRASE.finditer(flat):
        near = any(ph.start() - 400 <= p <= ph.end() + 250 for p in matched_positions)
        if not near and not unknown_position_matched:
            result.violations.append({"kind": "link_phrase_unattached", "where": "script", "quote": ph.group(0)[:200],
                                      "context": flat[max(0, ph.start() - 450): ph.end() + 450].strip()})
    return result


def feedback_text(result: NamingResult, confirmed_papers: Sequence[Any]) -> str:
    """Instructions added to the next generation attempt, listing what was wrong and what is allowed."""
    allowed = "; ".join(f"[{c.pid}] {', '.join(c.authors[:2])}{' et al.' if len(c.authors) > 2 else ''} ({c.year})" for c in confirmed_papers)
    lines = [violation_label(v) for v in result.violations]
    several = []  # authors with more than one listed paper: the model must say which one
    for v in result.violations:
        for a in v.get("authors") or []:
            mine = [c for c in confirmed_papers if any(_name_match(a, la) for la in c.authors)]
            if len(mine) > 1 and a not in [x[0] for x in several]:
                several.append((a, mine))
    extra = "".join(
        f"\nThe list has {len(mine)} papers by {a}: " + "; ".join(f'[{c.pid}] "{c.title}" ({c.year})' for c in mine) +
        f". Whenever you mention {a}'s work, name the paper by its title (or its distinctive title words) so it is clear which one; "
        f"never write only '{a}'s {mine[0].year} research'.\n" for a, mine in several)
    return (
        "\n\n**YOUR PREVIOUS SCRIPT WAS REJECTED because it named works that are not in the numbered list, or promised a link "
        "for a paper that is not in the list:**\n- " + "\n- ".join(lines) +
        f"\n\nRewrite it so that it names ONLY these papers: {allowed}. Remove every other author, study or paper from the script "
        "and the description, and say \"the link is in the description\" only right after naming one of these papers.\n" + extra)


CHECK_MAX_OUTPUT_TOKENS = 8192
CHECK_THINKING_BUDGET = 0     # these calls extract structured text and need no reasoning; with dynamic thinking on, hidden reasoning counts
#                               against the output limit and a slow call returns an empty or cut-off answer (seen on the paper analyses on
#                               2026-10-12 and on the naming check on Cloud Run on 2026-10-14: four unreadable answers in a row, 30 s each)


def check_request(system: str, user: str) -> Dict[str, Any]:
    return {"systemInstruction": {"parts": [{"text": system}]}, "contents": [{"parts": [{"text": user}]}],
            "generationConfig": {"temperature": 0, "maxOutputTokens": CHECK_MAX_OUTPUT_TOKENS, "responseMimeType": "application/json",
                                 "thinkingConfig": {"thinkingBudget": CHECK_THINKING_BUDGET}}}


def check_reply_text(payload: Dict[str, Any]) -> str:
    """The text of a check call's reply; a call that did not finish with STOP raises (the caller treats it as a model error)."""
    cands = payload.get("candidates") or []
    if not cands:
        raise RuntimeError("no candidate in the reply" + (f" (blocked: {payload['promptFeedback']})" if payload.get("promptFeedback") else ""))
    finish = cands[0].get("finishReason")
    if finish not in (None, "STOP"):
        raise RuntimeError(f"the reply ended with {finish}, not STOP")
    parts = ((cands[0].get("content") or {}).get("parts")) or []
    return "".join(p.get("text", "") for p in parts if not p.get("thought"))


def make_gemini_llm_call(api_key: str, model: str = "gemini-2.5-flash", post=None) -> LlmCall:
    """Production wrapper: the same Google AI key the generator already uses, temperature 0, JSON out, thinking off (REST, because the older
    SDK cannot set the thinking budget). Used by the naming check, the attribution check and the focused-query writer."""
    import requests
    send = post or requests.post

    async def call(system: str, user: str) -> str:
        def run() -> str:
            r = send(f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent",
                     headers={"x-goog-api-key": api_key, "Content-Type": "application/json"}, json=check_request(system, user), timeout=120)
            if r.status_code != 200:
                raise RuntimeError(f"{model} answered HTTP {r.status_code}: {r.text[:200]}")
            return check_reply_text(r.json())
        return await asyncio.to_thread(run)
    return call
