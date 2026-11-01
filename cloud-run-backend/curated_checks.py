"""Deterministic checks for curated-sources episodes (design §4.1, §5, §7; decisions Q3 and Q4). No model is called here.

Four checks, each returning a list of violations (empty = passed), run on the script of every attempt and again on the final text:

  status wording    a result with a Lean formalization is never called verified, proved, machine-checked or confirmed correct in the
                    episode's own voice; a withdrawn manuscript is never mentioned without saying it was withdrawn
  verbatim runs     no run of EIGHT or more consecutive words is shared between the script and any pasted or fetched commentary text,
                    except a quotation Gary marked approved
  spoken names      no voice name (Matilda, Adam ...) is spoken: introduced, used to address the other speaker, or thanked
  class labels      a named preprint is called a preprint; a named company release is said not to be peer reviewed

A violation is a dict {"check", "kind", "sentence" or "quote", ...}. `feedback_text` turns a list of them into the instruction fed back to
the next attempt. These checks are conservative on purpose: a false alarm costs one regeneration, a miss costs a wrong claim on the air.
"""
from __future__ import annotations

import re
import unicodedata
from typing import Any, Dict, Iterable, List, Optional, Sequence, Set, Tuple

VERBATIM_RUN_WORDS = 8


class CuratedCheckError(Exception):
    """The script still fails a curated-sources check after the allowed regenerations. The episode fails; nothing is repaired."""

    def __init__(self, violations):
        self.violations = list(violations)
        kinds = sorted({v["kind"] for v in self.violations})
        super().__init__("The script did not pass the curated-sources checks (" + ", ".join(kinds) + "), so no episode was generated.")
STATUS_HAS_LEAN, STATUS_CHECKED, STATUS_UNVERIFIED, STATUS_WITHDRAWN = "has_lean_formalization", "checked_by_experts", "unverified", "withdrawn"
STATUSES = (STATUS_HAS_LEAN, STATUS_CHECKED, STATUS_UNVERIFIED, STATUS_WITHDRAWN)

VOICE_NAMES = ("Matilda", "Bella", "Sam", "Adam", "Bryan", "Brian", "Daniel", "Bill", "Lily", "Sarah", "Tom", "Mary", "Bob")

_LABEL = re.compile(r"^[ \t]*(?:\*\*)?[A-Z][A-Z .'\-]{1,24}(?:\*\*)?:[ \t]*", re.M)
_SENTENCE_BREAK = re.compile(r"(?<=[.!?])[\"')\]]*\s+(?=[\"'(\[]?[A-Z0-9])")
_WORD = re.compile(r"[a-z0-9]+(?:'[a-z]+)?")


def dialogue_text(script: str) -> str:
    """The spoken words: speaker labels (HOST:, EXPERT:) removed."""
    return _LABEL.sub("", script or "")


def split_sentences(text: str) -> List[str]:
    out: List[str] = []
    for para in re.split(r"\n+", text or ""):
        para = para.strip()
        if para:
            out.extend(s.strip() for s in _SENTENCE_BREAK.split(para) if s.strip())
    return out


def words(text: str) -> List[str]:
    """Lower-case word tokens, accents and typographic apostrophes folded away."""
    t = unicodedata.normalize("NFKD", text or "").encode("ascii", "ignore").decode("ascii").lower().replace("’", "'")
    return _WORD.findall(t)


# --- finding a named result in a sentence -------------------------------------------------------------------------------
_STOP = {"the", "and", "for", "with", "from", "that", "this", "into", "over", "under", "between", "about", "their", "there", "which",
         "when", "where", "while", "every", "some", "than", "then", "have", "been", "being", "were", "what", "does", "also"}


def distinctive_words(title: str) -> List[str]:
    seen, out = set(), []
    for w in words(title):
        if len(w) >= 5 and w not in _STOP and w not in seen:
            seen.add(w)
            out.append(w)
    return out


def mentions(sentence: str, result: Dict[str, Any]) -> bool:
    """True if the sentence names this result: its whole title, or most of the distinctive words of its title or of its family's title."""
    sw = words(sentence)
    sset = set(sw)
    joined = " ".join(sw)
    for title in (result.get("title"), result.get("family_title")):
        if not title:
            continue
        tw = words(title)
        if tw and " ".join(tw) in joined:
            return True
        dw = distinctive_words(title)
        if len(dw) >= 2 and sum(1 for w in dw if w in sset) >= max(2, -(-len(dw) * 3 // 5)):
            return True
    return False


# --- status wording ---------------------------------------------------------------------------------------------------------
_NEGATION = {"not", "no", "never", "without", "neither", "nor", "cannot", "isn't", "wasn't", "hasn't", "haven't", "hadn't", "doesn't", "didn't",
             "aren't", "weren't", "yet", "unless", "n't", "nobody", "noone", "nothing", "none", "hardly", "barely", "unable", "lacks", "lacking"}
_ATTRIBUTION = re.compile(r"\b(?:openai|the (?:company|authors|manuscript|paper)|they|it)\s+(?:says?|said|claims?|claimed|reports?|reported|states?|stated|"
                          r"describes?|described|asserts?|asserted|announced?|writes?|wrote|argues?|argued|purports?)\b|according to|as claimed by|"
                          r"claims? (?:to|that)|purports? to", re.I)
# A named source reporting, in any tense: "Quanta reports that ...", "Scientific American said ...", "The Washington Times wrote ...", and the
# plural who report ("experts say", "mathematicians told Nature"). The name must be capitalised (this pattern is case-sensitive), so a lower-case
# "the proof says" is not an attribution; it only moves the claim onto someone else, it never lets the episode's own voice say "verified".
_REPORT_VERB = (r"(?:reports?|reported|reporting|says?|said|writes?|wrote|notes?|noted|states?|stated|claims?|claimed|told|argues?|argued|"
                r"adds?|added|explains?|explained|describes?|described|calls?|called|quotes?|quoted)")
_ATTRIBUTION_NAMED = re.compile(
    rf"(?-i:\b[A-Z][\w'’.\-]*(?:\s+(?:of|the|and|&|[A-Z][\w'’.\-]*)){{0,4}})\s+{_REPORT_VERB}\b"
    rf"|\b(?i:experts|mathematicians|researchers|reviewers|scientists|critics|reporters|commentators|observers|reports?|articles?|outlets?)\s+"
    rf"(?i:say|said|report(?:ed)?|write|wrote|note[sd]?|argue[sd]?|agree[sd]?|believe[sd]?|told)\b")
_FORBIDDEN = [
    ("formally verified", re.compile(r"\bformally verif(?:y|ies|ied)\b", re.I)),
    ("machine-checked", re.compile(r"\bmachine[- ]checked\b", re.I)),
    ("verified", re.compile(r"\bverified\b", re.I)),
    ("proved", re.compile(r"\bproved\b|\bproven\b", re.I)),
    ("confirmed correct", re.compile(r"\bconfirmed (?:to be )?correct\b|\bproof is correct\b|\bis correct\b.{0,20}\bproof\b", re.I)),
]
_LEAN_CUE = re.compile(r"\blean\b|formaliz|formalis", re.I)
_WITHDRAWAL = re.compile(r"\bwithdr(?:awn|ew|awal|aw)\b|\bretract(?:ed|ion)\b", re.I)


def _negated_before(sentence: str, start: int) -> bool:
    before = words(sentence[:start])[-6:]
    return any(w in _NEGATION or w.endswith("n't") for w in before)


def _forbidden_hits(sentence: str) -> List[str]:
    hits = []
    attributed = bool(_ATTRIBUTION.search(sentence) or _ATTRIBUTION_NAMED.search(sentence))
    for name, rx in _FORBIDDEN:
        for m in rx.finditer(sentence):
            if _negated_before(sentence, m.start()) or attributed:
                continue
            if name == "verified" and re.search(r"formally verif", sentence[max(0, m.start() - 10):m.end()], re.I):
                continue   # reported under the more specific name
            hits.append(name)
            break
    return hits


def check_status_wording(script: str, results: Sequence[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """`results`: dicts with title, family_title (optional), status, pid. Applies to every named result and, for the forbidden terms, to
    any sentence about Lean or formalization."""
    sentences = split_sentences(dialogue_text(script))
    violations: List[Dict[str, Any]] = []
    flagged: Set[Tuple[int, str]] = set()
    for i, s in enumerate(sentences):
        for r in results:
            if r.get("status") is None:
                continue
            if mentions(s, r):
                window = [s] + ([sentences[i + 1]] if i + 1 < len(sentences) else [])     # the sentence and the one after it
                for j, w in enumerate(window):
                    for term in _forbidden_hits(w):
                        key = (i + j, term)
                        if key not in flagged:
                            flagged.add(key)
                            violations.append({"check": "status_wording", "kind": "forbidden_term", "term": term, "sentence": w,
                                               "result": r.get("title"), "pid": r.get("pid"), "status": r.get("status")})
                if r.get("status") == STATUS_WITHDRAWN and not _WITHDRAWAL.search(s):
                    violations.append({"check": "status_wording", "kind": "withdrawn_not_stated", "sentence": s, "result": r.get("title"),
                                       "pid": r.get("pid"), "status": STATUS_WITHDRAWN})
        if _LEAN_CUE.search(s):
            for term in _forbidden_hits(s):
                key = (i, term)
                if key not in flagged:
                    flagged.add(key)
                    violations.append({"check": "status_wording", "kind": "forbidden_term", "term": term, "sentence": s, "result": None,
                                       "pid": None, "status": None})
    return violations


# --- verbatim runs -----------------------------------------------------------------------------------------------------------
def _grams(tokens: Sequence[str], n: int) -> Set[Tuple[str, ...]]:
    return {tuple(tokens[i:i + n]) for i in range(len(tokens) - n + 1)} if len(tokens) >= n else set()


def check_verbatim_runs(script: str, texts: Iterable[str], approved_quotes: Iterable[str] = (), n: int = VERBATIM_RUN_WORDS) -> List[Dict[str, Any]]:
    """Runs of `n` or more consecutive words (case, punctuation and accents ignored) that the script shares with any of `texts`."""
    st = words(dialogue_text(script))
    approved_text = [" ".join(words(q)) for q in approved_quotes if q]
    out: List[Dict[str, Any]] = []
    for ti, text in enumerate(texts):
        tw = words(text)
        shared = _grams(tw, n)
        if not shared or len(st) < n:
            continue
        hit = [i for i in range(len(st) - n + 1) if tuple(st[i:i + n]) in shared]
        start = prev = None
        runs: List[Tuple[int, int]] = []
        for i in hit:
            if start is None:
                start = prev = i
            elif i == prev + 1:
                prev = i
            else:
                runs.append((start, prev + n))
                start = prev = i
        if start is not None:
            runs.append((start, prev + n))
        for a, b in runs:
            run_text = " ".join(st[a:b])
            if any(run_text in q for q in approved_text):
                continue
            out.append({"check": "verbatim_run", "kind": "verbatim_run", "words": b - a, "quote": " ".join(st[a:min(b, a + 25)]), "source_index": ti})
    return out


# --- spoken names ---------------------------------------------------------------------------------------------------------------
def _name_patterns(names: Sequence[str]) -> List[re.Pattern]:
    alt = "|".join(re.escape(n) for n in names)
    nm = rf"(?:{alt})\b(?!\s+[A-Z][a-z])"      # not followed by a surname: "Daniel Litt" is a person, "Daniel." is the speaker
    return [
        re.compile(rf"\b(?i:I'm|I am|my name is|this is|call me)\s+{nm}"),
        re.compile(rf"(?:^|[.!?]\s+)(?:{alt}),"),
        re.compile(rf",\s*(?:{alt})\s*[.!?]"),
        re.compile(rf"\b(?i:thanks|thank you|hi|hello|welcome(?: back)?|good question|great question|exactly|right|well),?\s+{nm}"),
        re.compile(rf"\b{nm}\s+(?:and I|here)\b"),
    ]


def check_spoken_names(script: str, names: Sequence[str] = VOICE_NAMES) -> List[Dict[str, Any]]:
    """A voice name used as an introduction, a form of address or a thank-you. A real person with that first name, named in the normal way
    ("Daniel Litt wrote ..."), is not flagged."""
    out = []
    for s in split_sentences(dialogue_text(script)):
        for rx in _name_patterns(names):
            m = rx.search(s)
            if m:
                out.append({"check": "spoken_name", "kind": "spoken_name", "sentence": s, "matched": m.group(0).strip()})
                break
    return out


# --- class labels -----------------------------------------------------------------------------------------------------------------
_NOT_PEER = re.compile(r"\b(?:not|n't|never been|hasn't been|has not been|isn't|is not|yet to be|without)\b[^.]{0,30}\bpeer[- ]review", re.I)
_PREPRINT = re.compile(r"\bpre-?prints?\b", re.I)


def check_class_labels(script: str, items: Sequence[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """If the script names a preprint it must say preprint; if it names a company release it must say it is not peer reviewed.
    (At least once in the episode; the first-mention rule is carried by the prompt.)"""
    sentences = split_sentences(dialogue_text(script))
    text = " ".join(sentences)
    named = {"preprint": False, "company_release": False}
    for it in items:
        cls = it.get("class")
        if cls in named and any(mentions(s, it) for s in sentences):
            named[cls] = True
    out = []
    if named["preprint"] and not _PREPRINT.search(text):
        out.append({"check": "class_label", "kind": "preprint_not_labelled", "quote": "a named preprint is never called a preprint"})
    if named["company_release"] and not _NOT_PEER.search(text):
        out.append({"check": "class_label", "kind": "company_release_not_labelled",
                    "quote": "a named company release is never said to be not peer reviewed"})
    return out


# --- all of them, and the feedback --------------------------------------------------------------------------------------------------
def run_all(script: str, results: Sequence[Dict[str, Any]], commentary_texts: Sequence[str] = (), approved_quotes: Sequence[str] = (),
            items: Optional[Sequence[Dict[str, Any]]] = None) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    out += check_status_wording(script, results)
    out += check_verbatim_runs(script, commentary_texts, approved_quotes)
    out += check_spoken_names(script)
    out += check_class_labels(script, items if items is not None else results)
    return out


def summary(violations: Sequence[Dict[str, Any]]) -> Dict[str, int]:
    s: Dict[str, int] = {}
    for v in violations:
        s[v["check"]] = s.get(v["check"], 0) + 1
    return s


def feedback_text(violations: Sequence[Dict[str, Any]]) -> str:
    """The instruction fed back to the next attempt."""
    if not violations:
        return ""
    lines = ["\n\n**THE PREVIOUS SCRIPT WAS REJECTED. Fix every one of these and keep everything else:**"]
    for v in violations[:12]:
        k = v["kind"]
        if k == "forbidden_term":
            lines.append(f"- Never say \"{v['term']}\" about a result in your own voice. A result may only be described with the exact status wording you were given. "
                         f"Rewrite this sentence: \"{v['sentence']}\"")
        elif k == "withdrawn_not_stated":
            lines.append(f"- This result was WITHDRAWN. Every sentence that mentions it must say it was withdrawn: \"{v['sentence']}\"")
        elif k == "verbatim_run":
            lines.append(f"- {v['words']} words in a row were copied from a commentary text. Paraphrase it in your own words and attribute it: \"{v['quote']}\"")
        elif k == "spoken_name":
            lines.append(f"- The speakers have no names. Remove the name from the dialogue (labels are HOST and EXPERT only): \"{v['sentence']}\"")
        elif k == "preprint_not_labelled":
            lines.append("- You named a preprint without saying it is a preprint. Say \"a preprint\" the first time you mention it.")
        elif k == "company_release_not_labelled":
            lines.append("- You named a company release without saying it has not been peer reviewed. Say \"a company release that has not been peer reviewed\" the first time.")
    return "\n".join(lines) + "\n"
