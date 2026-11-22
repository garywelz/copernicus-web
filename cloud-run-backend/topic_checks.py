"""Two deterministic checks tied to the episode topic (fix 7). Neither calls a model.

1. Coverage statement. When the topic names something (for example "Metamath") and no confirmed paper's title or abstract covers it, the
   script must say plainly that the reviewed papers do not cover it. ``uncovered_named_things`` finds such names; ``missing_coverage_statements``
   checks the script for a sentence that names the thing and says the papers do not cover it. A script that talks about the uncovered thing
   without saying so, or never mentions it, is sent back with feedback.

2. The topic is not read aloud. The host introduces the question in her own words; a sentence that contains (nearly) the whole topic title
   is the title read out, and is sent back.
"""
from __future__ import annotations

import re
import unicodedata
from typing import Any, Dict, List, Sequence

from search_queries import stem, term_hits

_SENTENCE_SPLIT = re.compile(r"(?<=[.!?])\s+|\n+")
_STOP_CAPS = {"the", "a", "an", "in", "on", "of", "and", "or", "for", "to", "with", "from", "what", "how", "why", "when", "where", "is", "are"}

# A company or a laboratory is never a thing the reviewed papers must "not cover". Asked for such a sentence, the model wrote "The papers
# reviewed here do not cover OpenAI.", which says nothing and names the company as if it were a subject. The coverage statement is about the
# CLAIM, so the body that made the claim is not a name this check collects (episode 017, 2026-11-22).
_BODIES = {"openai", "anthropic", "google", "deepmind", "microsoft", "meta", "nvidia", "ibm", "apple", "amazon", "xai", "mistral",
           "huggingface", "epoch", "quanta", "arxiv", "github", "lean", "mathlib"}

# Dashes that join two names ("Mezard-Parisi", "Mézard–Parisi", "Landau—Siegel"). Every form must compare equal, and a name must be able to
# begin at a letter outside ASCII: the old token pattern started at [A-Za-z], so "Mézard-Parisi" was collected as the fragment "zard-Parisi"
# and no comparison with any source could ever succeed (episode 221, 2026-11-22).
_DASHES = "‐‑‒–—―−"
_NAME_CHAR = r"[^\W\d_]"                     # a letter in any script, not a digit or underscore
_NAME_TOKEN = re.compile(rf"{_NAME_CHAR}[{_DASHES}\-\w]*", re.UNICODE)


def fold(s: str) -> str:
    """A name as it must be compared: accents removed, every dash form a plain hyphen, lower case. "Mézard–Parisi" and "Mezard-Parisi"
    both become "mezard-parisi", so a source that spells it one way covers a topic that spells it the other."""
    s = unicodedata.normalize("NFKD", s or "")
    s = "".join(ch for ch in s if not unicodedata.combining(ch))
    return re.sub(rf"[{_DASHES}]", "-", s).lower()


class CoverageStatementError(Exception):
    """The script never says that the reviewed papers do not cover something the topic names, after the allowed regenerations."""

    def __init__(self, missing: List[str]):
        self.missing = missing
        super().__init__("The generated script does not say that the reviewed papers do not cover " + ", ".join(missing) +
                         ", which the topic names and no confirmed paper covers, and regeneration did not add it, so no episode was published.")


class TopicReadAloudError(Exception):
    """The script still reads the topic title out loud after the allowed regenerations."""

    def __init__(self, sentences: List[str]):
        self.sentences = sentences
        super().__init__("The generated script reads the topic title aloud and regeneration did not remove it, so no episode was published.")


# ---------------------------------------------------------------- 1. things the topic names that no paper covers
def named_things(topic: str) -> List[str]:
    """Names in the topic: words that start with a capital letter in the middle of a clause (not the first word, not right after a colon or
    full stop), words in quotation marks or backticks, and words with a digit, a hyphen or a capital inside (GPT-4, CRISPR-Cas9, iPhone)."""
    text = topic or ""
    found: List[str] = []
    for m in re.finditer(rf"[`\"‘“']({_NAME_CHAR}[{_DASHES}\-\w]{{3,30}})[`\"’”']", text, re.UNICODE):
        found.append(m.group(1))
    tokens = list(_NAME_TOKEN.finditer(text))
    for i, m in enumerate(tokens):
        w = m.group(0)
        if len(w) < 4 or w.lower() in _STOP_CAPS or fold(w).strip("-") in _BODIES:
            continue
        before = text[:m.start()].rstrip()
        clause_start = i == 0 or before.endswith((":", ".", "?", "!", ";", "—", "-"))
        inner_caps = any(c.isupper() for c in w[1:]) or any(c.isdigit() for c in w) or "-" in fold(w)
        if inner_caps or (w[0].isupper() and not clause_start):
            found.append(w)
    out, seen = [], set()
    for w in found:
        if stem(fold(w)) not in seen:
            seen.add(stem(fold(w)))
            out.append(w)
    return out


def _covers(text: str, name: str) -> bool:
    """Whether `text` covers `name`, comparing accent-free and with every dash form alike. A name joined by a dash is covered when both of
    its parts are present, so "Mézard–Parisi" is covered by a source that writes "Mezard-Parisi", "Mezard and Parisi" or either surname
    beside the other."""
    hay, needle = fold(text), fold(name).strip("-")
    if not needle:
        return False
    if term_hits(hay, [needle]):
        return True
    parts = [p for p in needle.split("-") if len(p) > 2]
    return bool(parts) and all(term_hits(hay, [p]) for p in parts)


def uncovered_named_things(topic: str, confirmed_papers: Sequence[Any]) -> List[str]:
    """Names in the topic that appear in no confirmed source's title, abstract or attached release text. A company or laboratory is not
    collected at all: the coverage statement is about the claim, never about who made it."""
    out = []
    for name in named_things(topic):
        texts = [f"{p.title} {getattr(p, 'abstract', '') or ''} {getattr(p, 'evidence_text', '') or ''}" for p in confirmed_papers]
        if not any(_covers(t, name) for t in texts):
            out.append(name)
    return out


_COVERAGE_VERB = r"(?:cover|covers|covered|address|addresses|addressed|discuss|discusses|discussed|include|includes|included|examine|examines|examined|analy[sz]e|analy[sz]es|analy[sz]ed|mention|mentions|mentioned|treat|treats|treated|study|studies|studied|consider|considers|considered|touch on|speak to|deal with)"
_NOT_COVERED = [
    re.compile(r"\b(?:do|does|did)(?:\s+not|n['’]t)\b[^.?!]{0,80}\b" + _COVERAGE_VERB + r"\b", re.I),
    re.compile(r"\b(?:never|neither|nor)\b[^.?!]{0,80}\b" + _COVERAGE_VERB + r"\b", re.I),
    re.compile(r"\b(?:no|none of the|not one of the)\b[^.?!]{0,60}\bpapers?\b[^.?!]{0,80}\b" + _COVERAGE_VERB + r"\b", re.I),
    re.compile(r"\bnot\s+(?:been\s+)?(?:covered|addressed|discussed|included|examined|analy[sz]ed|mentioned|treated|studied|considered)\b", re.I),
    re.compile(r"\b(?:outside|beyond)\b[^.?!]{0,60}\b(?:papers|reviewed|reviewed here|what was reviewed|the scope)\b", re.I),
    re.compile(r"\b(?:remains?|is|are|left|stays?)\s+(?:an\s+)?(?:open|unaddressed|uncovered|unexplored)\b", re.I),
]


def sentences(text: str) -> List[str]:
    return [s.strip() for s in _SENTENCE_SPLIT.split(text or "") if s.strip()]


def missing_coverage_statements(script: str, uncovered: Sequence[str]) -> List[str]:
    """The uncovered names for which no single sentence both names the thing and says the reviewed papers do not cover it."""
    missing = []
    sents = sentences(script)
    for name in uncovered:
        # The sentence is matched folded, so a script that writes "Mezard-Parisi" satisfies a name spelt "Mézard–Parisi" and the other way
        # round. Without this the script could not say the sentence the check demands.
        word = re.compile(r"(?<![a-z0-9])" + re.escape(fold(name).strip("-")) + r"(?:'s|s)?(?![a-z0-9])")
        if not any(word.search(fold(s)) and any(p.search(s) for p in _NOT_COVERED) for s in sents):
            missing.append(name)
    return missing


def coverage_prompt_block(uncovered: Sequence[str]) -> str:
    if not uncovered:
        return ""
    names = ", ".join(uncovered)
    return (f"**TOPIC PARTS THE REVIEWED PAPERS DO NOT COVER:** the topic names {names}, but none of the numbered papers covers "
            f"{'it' if len(uncovered) == 1 else 'them'}. In one sentence of the script that names {names}, say plainly that the papers reviewed here "
            f"do not cover {'it' if len(uncovered) == 1 else 'them'} (for example: \"The papers reviewed here do not cover {uncovered[0]}.\"). "
            "Do not describe it or draw conclusions about it from your own knowledge.\n")


def coverage_feedback(missing: Sequence[str]) -> str:
    return ("\n\n**YOUR PREVIOUS SCRIPT WAS REJECTED because the topic names " + ", ".join(missing) + " and none of the numbered papers covers "
            f"{'it' if len(missing) == 1 else 'them'}, yet the script never says so.**\nAdd one sentence that names "
            + ", ".join(missing) + " and says plainly that the papers reviewed here do not cover "
            f"{'it' if len(missing) == 1 else 'them'}. Do not describe it from your own knowledge.\n")


# ---------------------------------------------------------------- 2. the topic title read aloud
READ_ALOUD_OVERLAP = 0.8
MIN_TOPIC_WORDS = 5


def read_aloud_sentences(script: str, topic: str) -> List[str]:
    """Sentences that contain at least 80 percent of the topic's words (of four letters or more): the title read out. A topic with fewer
    than five such words is too short to tell from ordinary speech and is never reported."""
    topic_words = {stem(w.lower()) for w in re.findall(r"[A-Za-z][A-Za-z0-9\-]{3,}", topic or "")}
    if len(topic_words) < MIN_TOPIC_WORDS:
        return []
    hits = []
    for s in sentences(script):
        have = {stem(w.lower()) for w in re.findall(r"[A-Za-z][A-Za-z0-9\-]{3,}", s)}
        if len(topic_words & have) / len(topic_words) >= READ_ALOUD_OVERLAP:
            hits.append(s)
    return hits


def read_aloud_feedback(hits: Sequence[str]) -> str:
    quoted = "\n- ".join(f'"{h[:240]}"' for h in hits[:3])
    return ("\n\n**YOUR PREVIOUS SCRIPT WAS REJECTED because the host reads the topic title aloud:**\n- " + quoted +
            "\n\nThe host introduces the question in her own words, in one or two natural sentences. She does not read the title out or put it "
            "in quotation marks.\n")
