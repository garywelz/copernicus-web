"""Factual claims no source supports.

The attribution check reads a sentence the script credits to a listed paper and asks whether that paper's abstract bears it out. A sentence
that credits nobody is never examined, so the strongest assertions can pass by citing nothing: on 2026-11-19 four runs asserted that a named
company had withdrawn a manuscript "for a sign error", twice in episodes whose lists held no company source at all, and a phage episode's
draft widened its subject from bacteriophage genomes to "a virus, or even a cell".

This check is deterministic. It reads the words of the sources (title and abstract of every listed item) and refuses three kinds of
unattributed assertion:

* `withdrawal_without_record` - a withdrawal, retraction or correction asserted when no listed item's status record shows one;
* `scope_widened` - a subject term the sources never use (a cell, an organism, a patient) asserted as part of what was done;
* `named_body_without_source` - a company, laboratory or institution named in an assertion when no listed source names it.

Each violation names the sentence and says what the sources do say, so the writer can cut it or bring it back inside the sources.
"""
import re
from typing import Any, Dict, List, Optional, Sequence

# Subject terms that widen a paper's scope. A term is refused only when NO source uses it: a genuine cell paper is unaffected.
SCOPE_TERMS = (
    "cell", "cells", "cellular", "organism", "organisms", "human", "humans", "patient", "patients", "clinical",
    "therapy", "therapies", "therapeutic", "cure", "cures", "disease", "diseases", "tissue", "tissues",
    "embryo", "embryos", "animal", "animals", "mouse", "mice", "plant", "plants",
)
WITHDRAWAL = re.compile(r"\b(withdrawn|withdrew|withdrawal|retracted|retraction|corrigend\w*|a correction to)\b", re.I)
# A body that releases work. Named here only as a shape to look for in an assertion; the sources decide whether naming it is allowed.
BODY = re.compile(r"\b(OpenAI|Anthropic|Google|DeepMind|Meta|Microsoft|NVIDIA|IBM|Baker lab|ETH(?: Zurich)?|MIT|Stanford|Harvard|Oxford|"
                  r"Cambridge|Nature|Science|Quanta)\b")
# A hedge is not an exemption. Only an explicit NEGATION keeps a withdrawal sentence: saying there is no record of one is not a claim of one.
# "It could have been withdrawn" is still a claim about a withdrawal, and "it could cure diseases in patients" still brings in patients.
NEGATED = re.compile(r"\bno record\b|\bthere (?:is|are|was|were) no\b|\bnot been\b|\bwas not\b|\bwere not\b|\bnone of\b|\bneither\b|"
                     r"\bdo(?:es)? not (?:indicate|record|say|show|mention)\b|\bnothing (?:in|on) the record\b", re.I)
SPEAKER = re.compile(r"^\s*(HOST|EXPERT)\s*:\s*", re.I)


def source_words(sources: Sequence[Any]) -> frozenset:
    """Every WORD the listed sources offer, as whole words: titles, abstracts, the evidence text of a supplied item, and the body that
    released or published it. Whole words matter: a substring test finds "cell" in "excellent" and "MIT" in "transmitted", and would then
    let a widening through as if it were sourced.

    The releasing body counts because a company release IS that company's statement: a list holding OpenAI's manuscript supports naming
    OpenAI, whether or not the manuscript's text happens to spell the name. Without it the writer is pushed into "this company's own
    manuscript", which then fails the naming check and makes a coverage statement that must name the company impossible to write."""
    parts: List[str] = []
    for s in sources or []:
        for attr in ("title", "abstract", "evidence_text", "venue", "company"):
            v = getattr(s, attr, None)
            if v is None and isinstance(s, dict):
                v = s.get(attr)
            if isinstance(v, str):
                parts.append(v)
        pin = getattr(s, "pin", None) or (s.get("pin") if isinstance(s, dict) else None)
        if isinstance(pin, dict):
            for key in ("company", "repo"):            # a web release records its company; a repository release records "openai/math"
                if isinstance(pin.get(key), str):
                    parts.append(pin[key])
        authors = getattr(s, "authors", None) or (s.get("authors") if isinstance(s, dict) else None)
        for a in authors or []:                        # a company release's author IS the company ("OpenAI")
            if isinstance(a, str):
                parts.append(a)
    return frozenset(stem(w) for w in re.findall(r"[a-z0-9]+", " ".join(parts).lower()))


def sentences(script: str):
    """Each sentence of spoken dialogue, with its speaker, in order."""
    for line in (script or "").splitlines():
        line = line.strip()
        if not line:
            continue
        m = SPEAKER.match(line)
        who, body = (m.group(1).upper(), line[m.end():]) if m else ("?", line)
        for s in re.findall(r"[^.!?]+[.!?]+", body) or ([body] if body else []):
            s = s.strip()
            if s:
                yield who, s


def stem(word: str) -> str:
    """A light stem, so a plural matches its singular and the other way about: "diseases" and "disease-associated" are the same subject,
    and so are "therapeutic" and "therapeutics". Only the common English endings, and never below three letters, so "cell" is untouched
    and "excellent" still stems to itself."""
    w = word.lower()
    if len(w) > 4 and w.endswith("ies"):
        return w[:-3] + "y"
    # One trailing "s" only. Stripping "es" as well would be asymmetric: "diseases" would become "diseas" while "disease", which the
    # source says, stays as it is, and the two would never meet.
    if len(w) > 3 and w.endswith("s") and not w.endswith("ss"):
        return w[:-1]
    return w


def _in_sources(term: str, words: frozenset) -> bool:
    """Whether the sources use `term`, matched as whole words and compared by stem. A term of several words ("Baker lab", "ETH Zurich")
    counts only when the sources use every word of it."""
    pieces = [stem(p) for p in re.findall(r"[a-z0-9]+", term.lower())]
    return bool(pieces) and all(p in words for p in pieces)


def _attributed(sentence: str, attributed: Sequence[str]) -> bool:
    """True when the attribution check already examined this sentence (it quoted it)."""
    flat = re.sub(r"\s+", " ", sentence).strip().lower()
    return any(flat and flat in re.sub(r"\s+", " ", q or "").strip().lower() for q in attributed or [])


def check(script: str, sources: Sequence[Any], attributed_quotes: Sequence[str] = (),
          withdrawal_on_record: bool = False) -> List[Dict[str, Any]]:
    """Violations in `script`. `sources` are the listed items; `attributed_quotes` the sentences the attribution check already read;
    `withdrawal_on_record` is True only when a listed item's status record shows a withdrawal or correction."""
    words = source_words(sources)
    out: List[Dict[str, Any]] = []
    for who, s in sentences(script):
        if _attributed(s, attributed_quotes):
            continue
        negated = bool(NEGATED.search(s))
        if WITHDRAWAL.search(s) and not withdrawal_on_record and not negated:
            out.append({"check": "unattributed_claim", "kind": "withdrawal_without_record", "where": who, "find": s,
                        "message": f"{s!r} asserts a withdrawal, retraction or correction, but no listed source's status record shows one. "
                                   "Remove the sentence. A hedge does not help: 'may have been withdrawn' is still a claim about one."})
            continue
        widened = sorted({t for t in SCOPE_TERMS if re.search(rf"\b{t}\b", s, re.I) and not _in_sources(t, words)})
        if widened:
            out.append({"check": "unattributed_claim", "kind": "scope_widened", "where": who, "find": s,
                        "message": f"{s!r} brings in {', '.join(widened)}, which no listed source mentions. Say only what the sources are "
                                   "about, or remove the sentence. A hedge does not help: what might one day be done to a patient is still "
                                   "about patients."})
            continue
        named = sorted({m.group(0) for m in BODY.finditer(s) if not _in_sources(m.group(0), words)})
        if named:
            out.append({"check": "unattributed_claim", "kind": "named_body_without_source", "where": who, "find": s,
                        "message": f"{s!r} names {', '.join(named)}, which no listed source names. Remove the name, or attribute the "
                                   "sentence to a source that names it."})
    return out


def summary(violations: Sequence[Dict[str, Any]]) -> Dict[str, Any]:
    kinds: Dict[str, int] = {}
    for v in violations or []:
        kinds[v["kind"]] = kinds.get(v["kind"], 0) + 1
    return {"passed": not violations, "count": len(violations or []), "kinds": kinds}


def feedback(violations: Sequence[Dict[str, Any]]) -> Optional[str]:
    """Instructions for the next attempt."""
    if not violations:
        return None
    lines = [f"- {v['message']}" for v in violations[:8]]
    return ("Some sentences assert things no listed source supports. A sentence that credits no source is still a claim:\n"
            + "\n".join(lines))
