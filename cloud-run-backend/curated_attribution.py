"""Curated mode: attribution BY TARGET. Every sentence that credits something is tested against the thing it credits, not against a paper's abstract.

Routing is done by code, from the list's own records:

  * the sentence names a listed commentary outlet or author, or a person who appears in a listed item's pasted text  -> that item's private text
    (the one model call; it judges only "does this text support this sentence, as credited to this source");
  * it refers to OpenAI's catalogue, a formalization status, a review status or a withdrawal notice                    -> the list's status records,
    deterministically (no model call);
  * it attributes a content claim to a listed paper                                                                      -> that paper's abstract, by
    the existing check (attribution_check.py), on the sentences that were not routed elsewhere;
  * it credits a source that is not on the list                                                                          -> a violation.

The model's verdicts are supported, partly or unsupported. "Partly" is a failure only when the sentence credits a person with words the text gives
to someone else (a reporter's own phrase credited to an expert). The supporting excerpt is found by code in the source text and is kept privately: it
is never put in a reason, a log line or a job record. The ordinary (non-curated) mode does not use this module.

Nothing here knows about Firestore, audio or publishing. ``llm_call`` is injected so tests run offline.
"""
from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Sequence, Tuple

import curated_checks as cc
import curated_mode
import curated_sources as cs
from attribution_check import AttributionCheckUnavailable, AttributionResult, LlmCall, check_attributions
from json_reply import parse_json_reply
from speakable import spoken_source

MAX_SOURCE_CHARS = 16000        # of one source text sent to the model
MAX_ROUTED_SOURCES = 4           # a sentence about a person who appears in many texts is judged against the few texts that name them most
EXCERPT_WORDS = 25
SYSTEM = ("You check whether a source text supports sentences that credit it. You return JSON only. You judge only against the source texts you are "
          "given, never against what you know.")
INSTRUCTIONS = (
    "Below are SOURCES (each with an id, its outlet and its full text) and numbered SENTENCES from a podcast script. Each sentence credits one or more "
    "of the sources (the ones listed after it) or a person who appears in them. For each sentence, judge whether the text of the source it is credited "
    "to supports it AS CREDITED: the claim, who made it, and its strength.\n"
    "verdict is \"supported\" if the text says it, or plainly paraphrases it, and the credited source and person are right. \"partly\" if some of the "
    "sentence is in the text and some is not, or the strength is changed. \"unsupported\" if the text does not say it, contradicts it, or it is in "
    "another source but not this one.\n"
    "credited_person: the person the sentence credits with words, a judgement or a position (null if it credits no person). "
    "person_words_belong_to_someone_else: true if the text gives those words, judgement or position to someone else, for example when a phrase is the "
    "reporter's or the writer's own description and the sentence credits it to a person quoted, or a quote belongs to a different speaker; otherwise false.\n"
    "Return JSON: {\"verdicts\": [{\"n\": 1, \"verdict\": \"supported\", \"credited_person\": null, \"person_words_belong_to_someone_else\": false, "
    "\"reason\": \"one short sentence\"}]}. One entry per sentence. Never put a backslash or LaTeX command in the JSON."
)

def _depossess(token: str) -> str:
    """"openai's" -> "openai". A credited subject is often possessive, and the tokeniser keeps the apostrophe."""
    return re.sub(r"[’']s?$", "", token)


_GENERIC_SUBJECTS = {"experts", "mathematicians", "researchers", "reviewers", "scientists", "critics", "reporters", "commentators", "observers", "people",
                     "others", "some", "many", "they", "he", "she", "it", "we", "who", "which", "that", "one", "both", "each", "all", "nobody", "host",
                     "expert", "and", "but", "so", "then", "even", "first", "second", "third", "also", "right", "this", "these", "those", "here"}
_LEADING = {"the", "a", "an", "and", "but", "so", "then", "even", "also", "first", "second", "third", "right", "now", "still", "yet", "because", "as"}
_SUBJECT = re.compile(
    rf"(?-i:\b([A-Z][\w'’.\-]*(?:\s+(?:of|the|and|&|[A-Z][\w'’.\-]*)){{0,4}}))\s+{cc._REPORT_VERB}\b")
_ACCORDING = re.compile(r"(?i:according to|told|by)\s+(?-i:((?:the\s+)?[A-Z][\w'’.\-]*(?:\s+(?:of|the|and|&|[A-Z][\w'’.\-]*)){0,3}))")
_POSSESSIVE = re.compile(r"(?-i:\b([A-Z][\w\-]*)[’']s)\s+(?i:remark|assessment|view|views|account|statement|judgement|judgment|comment|comparison)")
_STATUS_CUE = re.compile(r"\bcatalog(?:ue)?s?\b|\bnotice\b|\breview status\b", re.I)
_LEAN_LISTED = re.compile(r"\blists?\b[^.]{0,40}\blean\b|\blean formali[sz]ation", re.I)
_UNCHECKED = re.compile(r"\bunchecked\b", re.I)
_ATTESTING = re.compile(r"\bverified\b|\bmachine[- ]checked\b|\bchecked by experts\b|\breviewed by experts\b|\bconfirmed\b|\bproved\b|\bproven\b", re.I)
# A sentence that speaks about a PARTICULAR listed manuscript, by pointing at one or by taking several together. Such a sentence is judged
# against those items' status records. A sentence with none of this, which only says what a catalogue listing is and is not, asserts nothing
# about any item and is a gloss.
_ITEM_REFERENCE = re.compile(r"\b(?:this|that|these|those|both|each|all (?:two|three|four))\s+(?:specific\s+|other\s+)?"
                             r"(?:manuscripts?|papers?|preprints?|releases?|formali[sz]ations?|results?|claims?|works?)\b"
                             r"|\bfor (?:it|them|this one)\b|\ball three\b|\ball of them\b", re.I)
_COLLECTIVE = re.compile(r"\b(?:these|those|both|all three|all four|all of them|each of (?:them|these))\b", re.I)
# What makes a sentence a limit on the status rather than a claim from it.
# Only specific limiting constructions. A bare "is not" was too broad: "OpenAI's catalogue indicates the result is not in doubt" is a
# finding dressed as a negation, and it was read as a gloss.
_LIMITING = re.compile(r"\bdoes(?:\s+not|n['’]t)\s+mean\b|\bnot\s+(?:been\s+)?independent\w*\b|\bha(?:s|ve)\s+not\s+been\b"
                       r"|\bno guarantee\b|\bsays nothing\b|\bonly means\b|\bnot a verdict\b"
                       r"|\bn(?:ot|o)\s+(?:a\s+|any\s+)?(?:step|progress|advance|evidence)\b"
                       r"|\bhas its own\b|\bits own stated\b|\bunchecked\b", re.I)
# An assertion that something WAS examined. Allowed in a gloss only inside a limiting construction ("has not been independently checked").
_EXAMINED = re.compile(r"\bindependently\s+(?:reviewed|checked|verified|validated|confirmed|examined)\b|\bpeer[- ]reviewed\b"
                       r"|\bha(?:s|ve)\s+been\s+(?:checked|reviewed|verified|validated)\b"
                       r"|\b(?:was|were)\s+(?:checked|reviewed|verified|validated|examined)\b", re.I)
def _asserted_outside_a_limit(pattern: "re.Pattern[str]", sentence: str) -> bool:
    """Whether `pattern` matches somewhere that is NOT inside a limiting construction.

    A limit is written before what it limits: "its correctness has not been independently confirmed" states a limit, while "the catalogue
    confirmed it, which does not mean much" states a finding and then shrugs. So a match counts as asserted unless a limiting phrase opens
    before it. 003 was refused twice for sentences of the first kind, because any attesting word at all disqualified them (2026-11-22).
    """
    limits = [m.start() for m in _LIMITING.finditer(sentence)]
    first_limit = min(limits) if limits else None
    return any(first_limit is None or m.start() < first_limit for m in pattern.finditer(sentence))


# The publication status a class already records: "not peer reviewed", "not yet published". True of every preprint and every company
# release by definition, and never stated in an abstract.
_NOT_PEER_REVIEWED = re.compile(r"\b(?:not|never|without|yet to be|awaiting|pending)\b[^.?!]{0,60}"
                                r"\b(?:peer[- ]reviewed|peer[- ]review|published|publication)\b", re.I)
_CLASS_WORD = re.compile(r"\bpreprints?\b", re.I)
# Everything a class-status sentence may say besides the sources' own words. Nothing here asserts a finding.
_STATUS_VOCAB = {"preprint", "preprints", "peer", "reviewed", "review", "reviews", "publication", "publications", "published",
                 "process", "full", "formal", "formally", "status", "yet", "undergone", "undergo", "undergoing", "journal",
                 "journals", "other", "others", "also", "these", "those", "this", "that", "they", "them", "it", "its", "their",
                 "there", "have", "has", "had", "not", "never", "been", "are", "is", "was", "were", "and", "or", "but", "like",
                 "such", "as", "of", "the", "a", "an", "to", "in", "on", "still", "any", "all", "both", "awaiting", "await",
                 "awaits", "pending", "however", "so", "therefore", "neither", "nor", "one", "two", "three", "titled", "called",
                 "company", "release", "releases", "manuscript", "manuscripts", "paper", "papers", "own", "openai"}

# Progress towards verification claimed from a catalogue listing. The status module documents what the record does and does not say:
# `scope: "Partial progress."`, `review.status: unchecked`, and "it does not say the Lean file states the paper's theorem". A listing is
# therefore not a step, an advance or evidence towards the result being verified, however hedged the sentence is.
_PROGRESS_TOWARD = re.compile(
    r"\b(?:step|steps|stepping|progress|progresses|advance|advances|advancement|move|moves|moving|closer|nearer|partial|partway|"
    r"headway|milestone|towards?|underway|on the way|en route)\b[^.?!]{0,40}"
    r"\b(?:verif\w*|confirm\w*|validat\w*|correctness|checked|checking)\b"
    r"|\b(?:verif\w*|confirm\w*|validat\w*|correctness)\b[^.?!]{0,40}"
    r"\b(?:step|steps|progress|advance\w*|closer|nearer|partial|partway|headway|milestone|underway)\b"
    r"|\bevidence\b[^.?!]{0,40}\b(?:verif\w*|confirm\w*|validat\w*|correctness)\b", re.I)

# A withdrawal is a record about a particular manuscript, never a gloss on the wording.
_WITHDRAWAL_CLAIM = re.compile(r"\bwithdr(?:awn|ew|awal)\b|\bnotice\b|\bretract\w*\b", re.I)
_MONTHS = ("january", "february", "march", "april", "may", "june", "july", "august", "september", "october", "november", "december")
_ONES = ["zero", "one", "two", "three", "four", "five", "six", "seven", "eight", "nine", "ten", "eleven", "twelve", "thirteen", "fourteen", "fifteen",
         "sixteen", "seventeen", "eighteen", "nineteen", "twenty"]
_ORD = {2: "halves", 3: "thirds", 4: "quarters", 5: "fifths", 6: "sixths", 7: "sevenths", 8: "eighths", 9: "ninths", 10: "tenths", 11: "elevenths",
        12: "twelfths", 13: "thirteenths", 14: "fourteenths", 15: "fifteenths", 16: "sixteenths", 17: "seventeenths", 18: "eighteenths",
        19: "nineteenths", 20: "twentieths"}


_DAYS = {w: n for n, w in enumerate("first second third fourth fifth sixth seventh eighth ninth tenth eleventh twelfth thirteenth fourteenth fifteenth sixteenth "
                                     "seventeenth eighteenth nineteenth twentieth".split(), start=1)}
_DAYS.update({"twenty-first": 21, "twenty-second": 22, "twenty-third": 23, "twenty-fourth": 24, "twenty-fifth": 25, "twenty-sixth": 26, "twenty-seventh": 27,
              "twenty-eighth": 28, "twenty-ninth": 29, "thirtieth": 30, "thirty-first": 31})


def _day(word: Optional[str]) -> Optional[int]:
    """The day of the month a word names ("sixth", "6", "6th"), or None if it is not a day."""
    w = (word or "").lower().strip(",.")
    if w in _DAYS:
        return _DAYS[w]
    m = re.fullmatch(r"(\d{1,2})(?:st|nd|rd|th)?", w)
    return int(m.group(1)) if m else None


def _fold(text: str) -> str:
    return " ".join(cc.words(text))


def _has_phrase(folded_sentence: str, phrase: str) -> bool:
    p = _fold(phrase)
    return bool(p) and re.search(rf"(?<![a-z0-9']){re.escape(p)}(?![a-z0-9'])", folded_sentence) is not None


def _closest_by_title(folded_sentence: str, matched: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Of several releases an alias matched, the one whose FULL title the sentence carries most of - or all of them when nothing decides.

    Two manuscripts in one family answer to the same words: 003 holds "The Quasi-Riemann Hypothesis: A Zero-Free Half-Plane Re s > 7/8"
    and "The Quasi-Riemann Hypothesis (alternate 11/12 proof)", and `cc.mentions` matched both for a sentence naming the first. A Lean
    claim then had to hold for BOTH, so a sentence about the half-plane manuscript - which does have a Lean entry - was refused because the
    alternate proof does not (2026-11-22). The sentence said which one it meant; taking every match threw that away.
    """
    if len(matched) < 2:
        return matched
    said = set(folded_sentence.split())
    scored = sorted(((len(said & set(cc.words(i.get("title") or ""))), n, i) for n, i in enumerate(matched)), key=lambda x: (-x[0], x[1]))
    if scored[0][0] > scored[1][0]:
        return [scored[0][2]]
    return matched                                          # nothing distinguishes them: every one must hold, as before


def _surname(name: str) -> str:
    toks = cc.words(name)
    return toks[-1] if toks and len(toks[-1]) >= 4 else ""


# --- the records the routing uses ------------------------------------------------------------------------------------------------------------------
@dataclass
class Source:
    pid: str
    item_id: str
    label: str                      # how the sentence is said to credit it (the spoken name)
    names: List[str]
    authors: List[str]
    text: str
    tokens: set = field(default_factory=set)


def commentary_sources(run) -> List[Source]:
    out = []
    for i in run.items:
        if i["class"] != cs.COMMENTARY or not i.get("evidence_text"):
            continue
        venue = i.get("venue") or ""
        aliases = [a for a in (i.get("aliases") or []) if isinstance(a, str)]      # how a sentence names the item without its outlet: a group author, "the declaration"
        names = [spoken_source(venue), venue, re.sub(r"\s*\([^)]*\)", "", venue)] + aliases
        names = [n for n in dict.fromkeys(names) if n and _fold(n)]
        text = i["evidence_text"]
        out.append(Source(pid=run.pids[i["item_id"]], item_id=i["item_id"], label=spoken_source(venue), names=names, authors=list(i.get("authors") or []),
                          text=text, tokens=set(cc.words(text))))
    return out


def _person_tokens(source: Source) -> set:
    """The capitalised words of a source text: the names that appear in it."""
    return {t for w in re.findall(r"[A-Z][\w'’\-]+", unicodedata.normalize("NFC", source.text)) for t in cc.words(w) if len(t) >= 3}


def _release_aliases(item: Dict[str, Any]) -> List[str]:
    title = item.get("title") or ""
    out: List[str] = []
    for a, b in re.findall(r"(\d+)\s*/\s*(\d+)", title):
        a, b = int(a), int(b)
        if a <= 20 and b in _ORD:
            out.append(f"{_ONES[a]} {_ORD[b]}")
    caps = re.findall(r"\b[A-Z][a-z]+(?:-[A-Z][a-z]+)?", title)
    run_, best = [], []
    for w in re.findall(r"[A-Za-z][\w\-]*", title):
        if w[0].isupper() and w.lower() not in ("the", "a", "an"):
            run_.append(w)
        else:
            best = run_ if len(run_) > len(best) else best
            run_ = []
    best = run_ if len(run_) > len(best) else best
    if len(best) >= 3:
        out.append("".join(w[0] for w in best).lower())
    del caps
    return [_fold(a) for a in out if _fold(a)]


# --- one sentence --------------------------------------------------------------------------------------------------------------------------------------
@dataclass
class Routed:
    sentence: str
    route: str                                  # commentary | status | content | unlisted_source | none
    sources: List[str] = field(default_factory=list)
    verdict: Optional[str] = None
    reason: str = ""
    credited_person: Optional[str] = None
    person_misattributed: bool = False
    excerpt: str = ""                           # private
    model_reason: str = ""                      # private
    passed: bool = True
    pids: List[str] = field(default_factory=list)


def _clean(subject: str) -> List[str]:
    toks = [t for t in re.findall(r"[\w'’\-]+", subject)]
    while toks and toks[0].lower() in _LEADING:
        toks = toks[1:]
    return toks


def credited_subjects(sentence: str) -> List[List[str]]:
    """The capitalised names the sentence credits: before a reporting verb, after 'according to' / 'told', before a possessive remark."""
    found: List[List[str]] = []
    for m in _SUBJECT.finditer(sentence):
        toks = _clean(m.group(1))
        if toks:
            found.append(toks)
    for m in _ACCORDING.finditer(sentence):
        toks = _clean(m.group(1))
        if toks:
            found.append(toks)
    for m in _POSSESSIVE.finditer(sentence):
        found.append([m.group(1)])
    return found


class Router:
    def __init__(self, run):
        self.run = run
        self.sources = commentary_sources(run)
        self.releases = [i for i in run.items if i["class"] != cs.COMMENTARY]
        self.person_index = {s.item_id: _person_tokens(s) for s in self.sources}
        # The companies whose releases are listed. Naming one IS naming a listed source: a list holding OpenAI's manuscripts supports
        # "OpenAI's claim", and the required coverage statement has to name the company to say what the other papers do not cover.
        # Taken from the items rather than hard-coded, so a release from any other company works the same way.
        self.companies = {t for i in self.releases if i["class"] == cs.COMPANY_RELEASE
                          for t in cc.words(curated_mode.company_of(i))}
        vocab: set = {"lean"} | self.companies
        for s in self.sources:
            vocab |= s.tokens
            for n in s.names + s.authors:
                vocab |= set(cc.words(n))
        for i in run.items:
            vocab |= set(cc.words(i.get("title") or "")) | set(cc.words(" ".join(i.get("authors") or []))) | set(cc.words(i.get("venue") or ""))
        self.vocab = vocab

    # -- who the sentence credits -------------------------------------------------------------------------------------------------------------------
    def outlets_named(self, folded: str) -> List[Source]:
        hits = []
        for s in self.sources:
            if any(_has_phrase(folded, n) for n in s.names) or any(_surname(a) and _has_phrase(folded, _surname(a)) for a in s.authors):
                hits.append(s)
        return hits

    def persons_credited(self, sentence: str) -> Tuple[List[Source], List[str]]:
        """(sources whose text names the credited persons, the credited subjects that no listed text or record knows)."""
        sources: Dict[str, Source] = {}
        unknown: List[str] = []
        for toks in credited_subjects(sentence):
            # "OpenAI's" must read as "openai": cc.words keeps the apostrophe, so a possessive would otherwise match nothing.
            low = [_depossess(t) for t in cc.words(" ".join(toks))]
            if not low or all(t in _GENERIC_SUBJECTS for t in low):
                continue
            if all(t in {"lean"} | self.companies for t in low):
                continue                               # the company whose release is listed, or the catalogue: not a person to check
            keyed = [t for t in low if len(t) >= 3]
            hit = [s for s in self.sources if any(t in self.person_index[s.item_id] for t in keyed)]
            if hit:
                hit.sort(key=lambda s: -sum(s.text.lower().count(t) for t in keyed))
                for s in hit[:MAX_ROUTED_SOURCES]:
                    sources[s.item_id] = s
            elif not any(t in self.vocab for t in keyed):
                unknown.append(" ".join(toks))
            elif not any(t in {"lean"} | self.companies or t in _GENERIC_SUBJECTS for t in keyed):
                pass                                   # a word the list knows (a title word, say), used as a subject: not a person to check
        return list(sources.values()), unknown

    # -- the status records -------------------------------------------------------------------------------------------------------------------------
    def releases_named(self, sentence: str) -> List[Dict[str, Any]]:
        folded = _fold(sentence)
        by_alias = [i for i in self.releases if any(_has_phrase(folded, a) for a in _release_aliases(i))]
        if by_alias:
            return _closest_by_title(folded, by_alias)
        results = {r["item_id"]: r for r in self.run.results()}
        named = [i for i in self.releases if i["class"] == cs.COMPANY_RELEASE and cc.mentions(sentence, results[i["item_id"]])]
        if named:
            return _closest_by_title(folded, named)
        if re.search(r"\bwithdrawn (?:paper|manuscript)\b", sentence, re.I):
            return [i for i in self.releases if self.run.status_of(i) == cc.STATUS_WITHDRAWN]
        return []

    def is_status_gloss(self, sentence: str) -> bool:
        """Whether the sentence only says what a catalogue listing IS, claiming nothing about any listed manuscript.

        "The presence of a Lean formalization in OpenAI's catalogue does not mean it has been independently checked for correctness." is
        true of every entry, states the limit of the record rather than a finding from it, and matches the module's own documentation. It
        was refused because any sentence mentioning a Lean formalization was read as claiming one for a paper, which left 197 and 003
        unable to explain a status they are required to explain (2026-11-22).

        A gloss may not assert anything: it must name no item, point at none, take none together, credit nobody with examining anything
        except inside a limiting phrase, and - where it does mention a Lean formalization - only say what that listing does not mean.
        """
        if _asserted_outside_a_limit(_ATTESTING, sentence):
            return False                                    # it credits somebody with a verdict
        if _asserted_outside_a_limit(_PROGRESS_TOWARD, sentence):
            return False                                    # it reads the listing as progress towards verification
        if self.releases_named(sentence) or _ITEM_REFERENCE.search(sentence):
            return False                                    # it speaks about particular items: judge it against their records
        if _WITHDRAWAL_CLAIM.search(sentence):
            return False                                    # a withdrawal is a record about a manuscript, judged against the notice
        if _asserted_outside_a_limit(_EXAMINED, sentence):
            return False                                    # it says something WAS examined
        # It must state a LIMIT of the record. Any other assertion about the catalogue - "the catalogue has many entries" - is a claim the
        # status records cannot confirm, and keeps failing as one.
        return bool(_LIMITING.search(sentence))

    def lean_scope(self, sentence: str, named: List[Dict[str, Any]]):
        """Which listed items a Lean claim is about, or None with the reason it cannot be told."""
        if named:
            return named, ""
        if _COLLECTIVE.search(sentence):
            # "these manuscripts", "all three": every release the list holds must have the record, or the sentence overstates.
            releases = [i for i in self.releases if i["class"] == cs.COMPANY_RELEASE]
            if releases:
                return releases, ""
        return None, "it says the catalogue lists a Lean formalization but does not say for which listed manuscript; name the manuscript"

    def check_status(self, sentence: str) -> Tuple[bool, str]:
        run = self.run
        named = self.releases_named(sentence)
        claims = 0
        if _asserted_outside_a_limit(_ATTESTING, sentence):
            return False, "the catalogue or a notice is credited with verifying or confirming a result; it records a listing or a withdrawal, not a verdict"
        if _asserted_outside_a_limit(_PROGRESS_TOWARD, sentence):
            return False, ("the listing is read as progress towards verification; the catalogue record says the entry's review status is "
                           "unchecked and does not say the Lean file states the paper's theorem, so it is no step towards the result "
                           "being verified")
        if self.is_status_gloss(sentence):
            return True, "a gloss on the status wording that claims nothing about any listed manuscript"
        if _LEAN_LISTED.search(sentence):
            claims += 1
            scope, why = self.lean_scope(sentence, named)
            if scope is None:
                return False, why
            for i in scope:
                if not (i.get("status_basis") or {}).get("in_lean_catalogue"):
                    return False, f"the catalogue record does not list a Lean formalization for {run.pids[i['item_id']]}"
        if _UNCHECKED.search(sentence):
            claims += 1
            scope = named or [i for i in self.releases if (i.get("status_basis") or {}).get("in_lean_catalogue")]
            if not scope:
                return False, "it gives a review status but no listed entry has one"
            for i in scope:
                if run.status_of(i) != cc.STATUS_HAS_LEAN:
                    return False, f"the status record for {run.pids[i['item_id']]} is not 'has a Lean formalization, unchecked'"
        if re.search(r"\bwithdr(?:awn|ew|awal)\b|\bnotice\b", sentence, re.I):
            claims += 1
            withdrawn = [i for i in (named or self.releases) if run.status_of(i) == cc.STATUS_WITHDRAWN]
            if not withdrawn or (named and any(run.status_of(i) != cc.STATUS_WITHDRAWN for i in named)):
                return False, "the status records do not say that the paper named was withdrawn"
            basis = (withdrawn[0].get("status_basis") or {})
            explanation = ((basis.get("withdrawal") or {}).get("explanation") or "").lower()
            if re.search(r"\b(?:error|mistake|flaw)\b", sentence, re.I):
                word = re.search(r"\b(sign error|error|mistake|flaw)\b", sentence, re.I).group(1).lower()
                if word not in explanation:
                    return False, f"the withdrawal notice does not mention a {word}"
            on = ((basis.get("withdrawal") or {}).get("withdrawn_on") or "").lower()
            for month in _MONTHS:
                m = re.search(rf"\b{month}\b(?:\s+(?:the\s+)?([\w\-]+))?", sentence, re.I)
                if m:
                    day = _day(m.group(1))
                    on_day = re.search(r"\b(\d{1,2})\b", on)
                    if month not in on or (day is not None and on_day and day != int(on_day.group(1))):
                        return False, "the withdrawal date given is not the one in the notice"
        if claims == 0:
            return False, "a statement about the catalogue or a notice that the status records cannot confirm"
        return True, "agrees with the list's status records"

    # -- the publication status a class already records -------------------------------------------------------------------------------------------------
    def class_status_only(self, sentence: str) -> Tuple[bool, str]:
        """Whether the sentence says no more than the publication status the ITEM'S CLASS already records.

        "As a preprint, it has not yet undergone the full peer-review process" is true of every item the list classes `preprint`, but an
        abstract never states its own publication status, so the sentence was judged against the abstract and refused. The pipeline asks a
        script to give each source's status and then refused it for doing so (episode 221, 2026-11-22).

        It passes only if the sentence asserts NOTHING else: every content word must be status vocabulary, or a word from a listed title,
        or a listed author's surname. "...which are important contributions to the field, but their findings are still undergoing
        scientific scrutiny" keeps failing, because "important", "contributions", "scrutiny" are in no source.
        """
        if not _NOT_PEER_REVIEWED.search(sentence):
            return False, ""
        named = [i for i in self.run.items if cc.mentions(sentence, {"item_id": i["item_id"], "title": i.get("title") or "",
                                                                     "authors": i.get("authors") or [], "year": i.get("year")})]
        by_class = [i for i in self.run.items if i["class"] == cs.PREPRINT] if _CLASS_WORD.search(sentence) else []
        scope = named or by_class
        if not scope:
            return False, ""
        for i in scope:
            if i["class"] not in (cs.PREPRINT, cs.COMPANY_RELEASE):
                return False, ""                            # a peer-reviewed item is not "not peer reviewed"; judge it as content
        allowed = set(_STATUS_VOCAB)
        for i in self.run.items:
            allowed |= set(cc.words(i.get("title") or ""))
            for a in (i.get("authors") or []):
                allowed |= set(cc.words(a))
        extra = [w for w in cc.words(sentence) if _depossess(w) not in allowed and w not in allowed and not w.isdigit()]
        if extra:
            return False, ""
        classes = ", ".join(sorted({self.run.pids[i["item_id"]] for i in scope}))
        return True, f"the publication status the list already records for {classes}"

    # -- routing ----------------------------------------------------------------------------------------------------------------------------------------
    def route(self, sentence: str) -> Routed:
        folded = _fold(sentence)
        outlets = self.outlets_named(folded)
        people, unknown = self.persons_credited(sentence)
        if unknown:
            return Routed(sentence, "unlisted_source", [", ".join(unknown)], "unsupported", f"it credits a source that is not on the list: {', '.join(unknown)}", passed=False)
        if outlets or (people and not _STATUS_CUE.search(sentence)):
            chosen = outlets or people
            return Routed(sentence, "commentary", [s.label for s in chosen], pids=[s.pid for s in chosen])
        if _STATUS_CUE.search(sentence):
            ok, why = self.check_status(sentence)
            return Routed(sentence, "status", ["the list's status records"], "supported" if ok else "unsupported", why, passed=ok)
        ok, why = self.class_status_only(sentence)
        if ok:
            return Routed(sentence, "status", ["the list's status records"], "supported", why, passed=True)
        return Routed(sentence, "content")


# --- the commentary route: the one model call ------------------------------------------------------------------------------------------------------
def _best_excerpt(sentence: str, texts: Sequence[str]) -> str:
    want = {w for w in cc.words(sentence) if len(w) >= 4}
    best, best_score = "", 0
    for t in texts:
        for s in cc.split_sentences(t):
            score = len(want & set(cc.words(s)))
            if score > best_score:
                best, best_score = s, score
    return " ".join(best.split()[:EXCERPT_WORDS])


async def _judge_commentary(routed: List[Routed], router: Router, llm: LlmCall) -> None:
    if not routed:
        return
    by_pid = {s.pid: s for s in router.sources}
    used: Dict[str, Source] = {}
    for r in routed:
        for p in r.pids:
            used[p] = by_pid[p]
    block = "\n\n".join(f"[{s.pid}] {s.label}\nTEXT: {s.text.strip()[:MAX_SOURCE_CHARS]}" for s in used.values())
    lines = "\n".join(f"{n}. {r.sentence}  [credited to: " + ", ".join(r.pids) + "]" for n, r in enumerate(routed, 1))
    try:
        raw = await llm(SYSTEM, f"{INSTRUCTIONS}\n\nSOURCES:\n{block}\n\nSENTENCES:\n{lines}")
    except Exception as e:
        raise AttributionCheckUnavailable(f"attribution check failed: {type(e).__name__}: {e}")
    try:
        data = parse_json_reply(raw)
    except Exception:
        data = None
    items = data.get("verdicts") if isinstance(data, dict) else None
    if not isinstance(items, list):
        raise AttributionCheckUnavailable("attribution check returned an unparseable answer", raw)
    answered: Dict[int, Dict[str, Any]] = {}
    for it in items:
        if isinstance(it, dict):
            try:
                answered[int(it.get("n"))] = it
            except (TypeError, ValueError):
                continue
    for n, r in enumerate(routed, 1):
        it = answered.get(n)
        verdict = str((it or {}).get("verdict") or "").strip().lower()
        if verdict not in ("supported", "partly", "unsupported"):
            raise AttributionCheckUnavailable("attribution check did not judge every sentence", raw)
        r.verdict = verdict
        r.credited_person = (it.get("credited_person") or None) if isinstance(it.get("credited_person"), str) else None
        r.person_misattributed = bool(it.get("person_words_belong_to_someone_else")) and r.credited_person is not None
        r.model_reason = str(it.get("reason") or "")[:300]
        r.excerpt = _best_excerpt(r.sentence, [by_pid[p].text for p in r.pids])
        r.passed = verdict == "supported" or (verdict == "partly" and not r.person_misattributed)
        r.reason = ("the source text supports it" if verdict == "supported" else
                    "the source text supports only part of it" if verdict == "partly" and r.passed else
                    "it credits a person with words the source text gives to someone else" if verdict == "partly" else
                    "the source text does not support this sentence as credited to this source")


# --- the check -----------------------------------------------------------------------------------------------------------------------------------------
class CuratedAttributionResult(AttributionResult):
    def __init__(self):
        super().__init__()
        self.routing: List[Routed] = []

    def summary(self) -> Dict[str, Any]:
        base = super().summary()
        counts: Dict[str, int] = {}
        for r in self.routing:
            counts[r.route] = counts.get(r.route, 0) + 1
        base["by_target"] = True
        base["routes"] = counts
        return base

    def detail(self) -> List[Dict[str, Any]]:
        """Per attributed sentence, for the administrator only: the route, the sources, the verdict and the supporting excerpt. Never logged or stored."""
        return [{"sentence": r.sentence, "route": r.route, "sources": list(dict.fromkeys(r.sources)), "verdict": r.verdict, "passed": r.passed, "reason": r.reason,
                 "credited_person": r.credited_person, "person_words_belong_to_someone_else": r.person_misattributed, "excerpt": r.excerpt,
                 "model_reason": r.model_reason} for r in self.routing if r.route != "content"]


def _record(r: Routed) -> Dict[str, Any]:
    # `reason` goes to logs and job records, so it is the fixed wording, never text from a source; the excerpt and the model's reason stay private
    return {"quote": r.sentence[:600], "pid": (r.pids[0] if r.pids else None), "label": ", ".join(dict.fromkeys(r.sources)), "verdict": "supported" if r.passed else "unsupported",
            "reason": r.reason, "route": r.route, "title": None, "authors": [], "year": None, "abstract": None}


async def check_curated_attributions(script: str, run, named_papers: Sequence[Any], llm: LlmCall) -> CuratedAttributionResult:
    result = CuratedAttributionResult()
    router = Router(run)
    sentences = cc.split_sentences(cc.dialogue_text(script))
    routed = [router.route(s) for s in sentences]
    commentary = [r for r in routed if r.route == "commentary"]
    await _judge_commentary(commentary, router, llm)
    result.routing = [r for r in routed]
    content_text = "\n".join(r.sentence for r in routed if r.route == "content")
    papers = [p for p in named_papers if getattr(p, "source_class", None) != cs.COMMENTARY and (getattr(p, "abstract", "") or "").strip()]
    content = await check_attributions(content_text, papers, llm) if content_text.strip() else AttributionResult()
    for r in routed:
        if r.route in ("commentary", "status", "unlisted_source"):
            rec = _record(r)
            result.checked.append(rec)
            if not r.passed:
                result.violations.append(rec)
    for rec in content.checked:
        rec = dict(rec, route="content")
        result.checked.append(rec)
        if rec["verdict"] == "unsupported":
            result.violations.append(rec)
    if not result.checked:
        result.skipped_reason = "no attributed sentences"
    return result


def credited_commentary_pids(script: str, run) -> List[str]:
    """The commentary items the script credits: those the routing sends to the commentary branch. Code only, no model call; in the order of the list."""
    router = Router(run)
    found = set()
    for sentence in cc.split_sentences(cc.dialogue_text(script)):
        r = router.route(sentence)
        if r.route == "commentary":
            found.update(r.pids)
    order = {run.pids[i["item_id"]]: n for n, i in enumerate(run.items)}
    return sorted(found, key=lambda p: order.get(p, 10**6))


async def check_attributions_for(script: str, named_papers: Sequence[Any], llm: LlmCall, curated_run=None):
    """The ordinary check when there is no curated run, attribution by target when there is."""
    if curated_run is None:
        return await check_attributions(script, named_papers, llm)
    return await check_curated_attributions(script, curated_run, named_papers, llm)
