"""Focused arXiv queries for a topic (fix 4, stage i).

The pipeline used to send the whole topic sentence to arXiv as ``all:<sentence>``. arXiv ranks by how many of the sentence's words a
paper contains, so generic words ("mathematics library proof built") outrank the one paper that is exactly about the question: for
"Proof dependency graphs in formal mathematics libraries: what the network structure of mathlib and Metamath reveals about how
mathematics is built" the top 15 held the Lean library paper, mizar-items, two didactics essays and a music-and-mathematics paper,
and not arXiv 2604.24797, "The Network Structure of Mathlib".

This module makes two to three extra, focused queries (2 or 3 distinctive terms joined with AND) to run alongside the full sentence,
and scores candidates by how many of those distinctive terms they contain so the focused hits are not buried. A model proposes the
queries (temperature 0, validated by code); if it is unavailable or answers nothing valid, a deterministic fallback builds them from
the topic words. Nothing here calls arXiv or knows about Firestore; ``llm_call`` is injected so tests run offline.
"""
from __future__ import annotations

import re
from typing import Awaitable, Callable, Iterable, List, Optional, Sequence

from json_reply import parse_json_reply

LlmCall = Callable[[str, str], Awaitable[str]]  # (system, user) -> JSON text

MAX_FOCUSED_QUERIES = 3
TERM = r"(?:all|ti|abs):[A-Za-z0-9]{2,40}"
VALID_QUERY = re.compile(rf"^{TERM}(?: AND {TERM}){{1,2}}$")

SYSTEM = "You write search queries for the arXiv API. You return JSON only."
INSTRUCTIONS = (
    "Write {n} arXiv API search_query strings that would find papers that directly analyse this research question.\n"
    "Each query joins 2 or 3 terms with AND, each term written as all:word where word is ONE plain word of letters and digits (no hyphens, "
    "no compounds, no phrases), for example \"all:mathlib AND all:network AND all:dependency\". Two terms are often better than three: "
    "every extra term can make the query match nothing.\n"
    "Prefer distinctive technical terms and names (software, libraries, methods, datasets, organisms, instruments) over generic words "
    "such as mathematics, proof, study, analysis, formal, library, method. Use a different combination in each query, and put the most "
    "specific names in more than one of them.\n"
    "Return JSON: {{\"queries\": [\"all:a AND all:b\", ...]}}."
)

_STOP = set("""a an the and or of in on at to for from with without by as is are was were be been being this that these those it its their
what which who whom whose how why when where whether if then than so such into onto about above below between among through during before
after over under again further once here there both each few more most other some any no nor not only own same too very can will just
should now reveals reveal revealed shows show showed built build using use used via per vs versus new""".split())
_GENERIC = set("""study studies analysis analyses approach approaches based role roles review overview effect effects impact impacts understanding
exploring explore investigating investigation implications implication toward towards case work works paper papers research method methods
methodology model models system systems framework frameworks application applications problem problems question questions""".split())


def topic_terms(topic: str) -> List[str]:
    """The topic's content words in order, lower-cased, without stop words and generic research words (duplicates removed)."""
    out, seen = [], set()
    for w in re.findall(r"[A-Za-z][A-Za-z0-9\-]{2,}", topic or ""):
        lw = w.lower().strip("-")
        if lw in _STOP or lw in _GENERIC or lw in seen or len(lw) < 3:
            continue
        seen.add(lw)
        out.append(lw)
    return out


def fallback_queries(topic: str, n: int = MAX_FOCUSED_QUERIES) -> List[str]:
    """No model: consecutive content words, three at a time ("network structure mathlib" in the example topic). Weak but deterministic."""
    terms = topic_terms(topic)
    queries = []
    for i in range(0, len(terms), 3):
        chunk = terms[i:i + 3]
        if len(chunk) >= 2:
            queries.append(" AND ".join(f"all:{t}" for t in chunk))
    # prefer the chunks from the middle and end of the topic (the subtitle usually holds the specific question) when there are too many
    return queries[-n:] if len(queries) > n else queries


def valid_queries(candidates: Iterable[object], n: int = MAX_FOCUSED_QUERIES) -> List[str]:
    out = []
    for c in candidates:
        q = re.sub(r"\s+", " ", str(c or "")).strip()
        if VALID_QUERY.match(q) and q.lower() not in [x.lower() for x in out]:
            out.append(q)
    return out[:n]


async def focused_queries(topic: str, llm_call: Optional[LlmCall] = None, n: int = MAX_FOCUSED_QUERIES) -> List[str]:
    """Up to n valid focused queries for the topic: the model's, else the deterministic fallback. Never raises."""
    if llm_call is not None:
        try:
            raw = await llm_call(SYSTEM, INSTRUCTIONS.format(n=n) + f"\n\nRESEARCH QUESTION:\n{topic}")
            data = parse_json_reply(raw)
            items = data.get("queries") if isinstance(data, dict) else None
            queries = valid_queries(items if isinstance(items, list) else [], n)
            if queries:
                return queries
        except Exception:
            pass
    return valid_queries(fallback_queries(topic, n), n)


def query_terms(queries: Sequence[str]) -> List[str]:
    """The distinctive words of the focused queries, lower-cased."""
    seen, out = set(), []
    for q in queries:
        for m in re.finditer(r"(?:all|ti|abs):([A-Za-z0-9][A-Za-z0-9\-]+)", q):
            t = m.group(1).lower()
            if t not in seen:
                seen.add(t)
                out.append(t)
    return out


# ---------------------------------------------------------------- distinctive topic terms (fix 7)
# Words that say little about WHICH question a topic asks: broad words of mathematics, computing and research. A topic's distinctive terms are
# its content words minus these ("mathlib", "metamath", "dependency" in the ever-math topic; "network", "graph", "proof" are generic).
GENERIC_TOPIC_STEMS = set("""proof graph formal mathematic mathematical math library network structure theory system model method data learning
algorithm computer computational computation science scientific software language logic framework approach study research paper knowledge information
neural machine analysis technique tool application problem concept general design process development performance experiment result evidence effect factor
role pattern feature type form field area world human time work way""".split())


def stem(word: str) -> str:
    """A light plural stem: dependencies -> dependency, graphs -> graph, libraries -> library, classes -> class."""
    w = (word or "").lower()
    if len(w) > 4 and w.endswith("ies"):
        return w[:-3] + "y"
    if len(w) > 4 and (w.endswith("sses") or w.endswith("xes") or w.endswith("ches") or w.endswith("shes")):
        return w[:-2]
    if len(w) > 3 and w.endswith("s") and not w.endswith("ss"):
        return w[:-1]
    return w


def distinctive_terms(topic: str) -> List[str]:
    """The topic's distinctive words (lower-case surface forms, in topic order): content words that are not generic."""
    return [w for w in topic_terms(topic) if len(w) >= 4 and stem(w) not in GENERIC_TOPIC_STEMS]


def _stems_in(text: str) -> set:
    return {stem(w) for w in re.findall(r"[a-z0-9][a-z0-9\-]*", (text or "").lower())}


def term_hits(text: str, terms: Sequence[str]) -> set:
    """Which of the terms (as stems) occur in the text."""
    have = _stems_in(text)
    return {stem(t) for t in terms if stem(t) in have}


def keep_focused_paper(title: str, abstract: str, distinctive: Sequence[str]) -> bool:
    """A paper that only a focused query found is kept when its title has a distinctive topic term, or its abstract has at least two different
    ones (one, if the topic has only one). A single mention in an abstract (a tool the paper happens to use) is not enough. With no
    distinctive terms there is nothing to test and the paper is kept."""
    if not distinctive:
        return True
    if term_hits(title, distinctive):
        return True
    need = min(2, len({stem(t) for t in distinctive}))
    return len(term_hits(abstract, distinctive)) >= need


def lexical_score(title: str, abstract: str, terms: Sequence[str], distinctive: Sequence[str] = ()) -> float:
    """2 points for each term in the title, 1 for each in the abstract (a term is a whole word, case-insensitive); a distinctive term counts
    three times as much, so papers that contain the topic's rare words come before papers that only share its generic ones."""
    tw = set(re.findall(r"[a-z0-9][a-z0-9\-]*", (title or "").lower()))
    aw = set(re.findall(r"[a-z0-9][a-z0-9\-]*", (abstract or "").lower()))
    rare = {stem(t) for t in distinctive}
    score = 0.0
    for t in terms:
        weight = 3 if stem(t) in rare else 1
        score += weight * (2 * (t in tw) + 1 * (t in aw))
    return score
