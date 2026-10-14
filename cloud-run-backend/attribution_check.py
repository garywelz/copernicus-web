"""Post-generation check: a claim attributed to a named paper must be supported by that paper's abstract (fix 4, stage b).

One short model call reads the script and the abstracts of the papers it names, finds every sentence that attributes a claim to
one of them (by name, or by pointing back: "that paper", "the authors", "their work") and judges each against the abstract of that
paper only. The model returns quotes and verdicts; the code accepts a verdict only if the quoted sentence really occurs in the
script and the paper is one of the papers it was given. An unsupported attribution is a reason to regenerate (the sentence is quoted
back); after the allowed regenerations the episode fails. The check fails closed: if it cannot run, the episode is not accepted.
There is no rewriting pass.

Nothing here knows about Firestore, audio or publishing. ``llm_call`` is injected so tests run offline.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Awaitable, Callable, Dict, List, Sequence

from json_reply import parse_json_reply

LlmCall = Callable[[str, str], Awaitable[str]]  # (system, user) -> JSON text

PROMPT_ID = "ATTRIBUTIONS@1"
MAX_ABSTRACT_CHARS = 2500
SYSTEM = ("You check whether a podcast script's claims about named papers are supported by those papers' abstracts. "
          "You return JSON only. You judge only against the abstract text you are given, never against what you know.")
INSTRUCTIONS = (
    "Below are PAPERS (each with an id and its abstract) and a SCRIPT.\n"
    "Find every sentence in the SCRIPT that attributes a claim, finding, method, argument, position or conclusion to one of the PAPERS "
    "or to its authors. That includes sentences that name the paper or authors (\"Smith and Lee show that ...\", \"according to ...\", "
    "\"the paper highlights ...\") and sentences that point back to a paper just discussed (\"that paper explicitly says ...\", \"the "
    "authors argue ...\", \"their work demonstrates ...\", \"it positions ...\"). Do not include sentences that only name a paper "
    "without saying what it claims, and do not include the speakers' own opinions that are not attributed to a paper.\n"
    "For each such sentence give: quote (the attributing sentence, copied verbatim from the SCRIPT, at most 300 characters), pid (the "
    "paper id it is attributed to), verdict, reason.\n"
    "verdict is \"supported\" if the abstract states what the sentence attributes to the paper, or clearly implies it as a plain "
    "paraphrase. verdict is \"unsupported\" if the abstract does not say it, contradicts it, or if the sentence attributes to the paper "
    "stronger certainty, novelty, significance or scope than the abstract claims (for example \"explicitly\", \"fundamentally "
    "challenges\", \"proves\", \"redefines\", \"for all\") that the abstract does not. Judge only the abstract. The reason is one short "
    "sentence.\n"
    "Return JSON: {\"attributions\": [{\"quote\": \"...\", \"pid\": \"P1\", \"verdict\": \"supported\", \"reason\": \"...\"}]}. "
    "Return {\"attributions\": []} if there are none. Never put a backslash or LaTeX command in the JSON; write notation as plain words."
)


class AttributionCheckUnavailable(Exception):
    """The check could not run (model error or unparseable answer). The episode must not be accepted unchecked."""

    def __init__(self, message: str, raw: str = ""):
        self.raw = (raw or "")[:300]
        super().__init__(message)


class AttributionError(Exception):
    """Raised when the script still attributes claims its cited papers' abstracts do not support after the allowed regenerations."""

    def __init__(self, violations: List[Dict[str, Any]]):
        self.violations = violations
        super().__init__("The generated script attributes " + str(len(violations)) + " claim(s) to papers whose abstracts do not support them, "
                         "and regeneration did not remove them, so no episode was published: " +
                         "; ".join(f'"{v["quote"][:90]}"' for v in violations[:4]) + ("; ..." if len(violations) > 4 else ""))


@dataclass
class AttributionResult:
    checked: List[Dict[str, Any]] = field(default_factory=list)      # every attribution the model reported and the code accepted
    violations: List[Dict[str, Any]] = field(default_factory=list)   # the unsupported ones
    skipped_reason: str = ""                                          # set when there was nothing to check

    @property
    def passed(self) -> bool:
        return not self.violations

    def summary(self) -> Dict[str, Any]:
        return {"passed": self.passed, "attributions": len(self.checked), "unsupported": len(self.violations), "skipped": self.skipped_reason,
                "unsupported_quotes": [v["quote"] for v in self.violations]}


def _flat(s: str) -> str:
    return re.sub(r"\s+", " ", s or "").strip().lower()


def _in_script(quote: str, flat_script: str) -> bool:
    q = _flat(quote)
    return len(q) >= 12 and q[:80] in flat_script


def _label(paper: Any) -> str:
    first = (paper.authors[0] if paper.authors else "").split()
    who = (first[-1] if first else "the authors") + (" and colleagues" if len(paper.authors) > 2 else "")
    return f"{who} ({paper.year})" if paper.year else who


async def check_attributions(script: str, named_papers: Sequence[Any], llm_call: LlmCall) -> AttributionResult:
    """`named_papers`: the confirmed papers the script names (each with pid, title, authors, year, abstract). Raises
    AttributionCheckUnavailable if the model step fails."""
    papers = [p for p in named_papers if (getattr(p, "abstract", "") or "").strip()]
    result = AttributionResult()
    if not papers or not (script or "").strip():
        result.skipped_reason = "no named papers with abstracts" if not papers else "empty script"
        return result
    block = "\n\n".join(f"[{p.pid}] {', '.join(p.authors[:3])} ({p.year}). {p.title}\nABSTRACT: {p.abstract.strip()[:MAX_ABSTRACT_CHARS]}" for p in papers)
    user = f"{INSTRUCTIONS}\n\nPAPERS:\n{block}\n\nSCRIPT:\n{script}"
    try:
        raw = await llm_call(SYSTEM, user)
    except Exception as e:
        raise AttributionCheckUnavailable(f"attribution check failed: {type(e).__name__}: {e}")
    try:
        data = parse_json_reply(raw)
    except Exception:
        data = None
    items = data.get("attributions") if isinstance(data, dict) else None
    if not isinstance(items, list):
        raise AttributionCheckUnavailable("attribution check returned an unparseable answer", raw)
    by_pid = {p.pid: p for p in papers}
    flat_script = _flat(script)
    for it in items:
        if not isinstance(it, dict):
            continue
        quote, pid = str(it.get("quote") or "").strip(), str(it.get("pid") or "").strip()
        verdict = str(it.get("verdict") or "").strip().lower()
        # the model reports; the code decides what counts: a real quote from the script, about a paper it was given
        if pid not in by_pid or verdict not in ("supported", "unsupported") or not _in_script(quote, flat_script):
            continue
        paper = by_pid[pid]
        rec = {"quote": quote[:600], "pid": pid, "label": _label(paper), "verdict": verdict, "reason": str(it.get("reason") or "")[:300],
               "title": paper.title, "authors": list(paper.authors)[:6], "year": paper.year, "abstract": (paper.abstract or "").strip()[:MAX_ABSTRACT_CHARS]}
        result.checked.append(rec)
        if verdict == "unsupported":
            result.violations.append(rec)
    return result


def attribution_feedback(result: AttributionResult) -> str:
    """Instructions for the next attempt: each unsupported sentence quoted back with the paper it was pinned on."""
    lines = [f'"{v["quote"]}" (attributed to {v["label"]}; {v["reason"] or "the abstract does not say this"})' for v in result.violations[:8]]
    return ("\n\n**YOUR PREVIOUS SCRIPT WAS REJECTED because it attributes claims to papers whose abstracts do not support them:**\n- "
            + "\n- ".join(lines) +
            "\n\nAttribute to a paper only what its abstract states. Remove each unsupported claim, or state it as general background without "
            "naming the paper as its source. Do not add emphasis the paper does not claim (\"explicitly\", \"fundamentally\", \"proves\").\n")
