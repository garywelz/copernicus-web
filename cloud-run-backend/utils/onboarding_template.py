"""The onboarding template, as data (template_version 1; docs/design/ENGINE_ONBOARDING_FORM.md section 2).

GENERIC: nothing here belongs to one engine. An engine's own content (its questions, terms, horizons, seeds) is written to Firestore by a loader (PR 4) or, in
tests, by a synthetic fixture; this module only says which sections exist, which kinds of answer each section holds, what choices an owner has, and the caps on
every free-text field (design 9: every free-text field has a length cap and a type, and values are stored as text, never as HTML).

Sections in this version: 2.1 scope and use case, 2.2 research questions, 2.3 keywords and horizons, and the CONFIRM part of 2.4 (each current seed:
yes, no or unsure, with a comment). Adding a seed, the review queue and the private bibliography are PR 4.
"""
import re
from typing import Any, Callable, Dict, List, Optional, Tuple

TEMPLATE_VERSION = 1

ID_RE = re.compile(r"^[a-z0-9][a-z0-9-]{0,60}$")          # section keys and item ids: no underscores, so the 'a__b__c' document keys are unambiguous
_CONTROL = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")  # control characters other than tab and line feed

# caps (characters, or entries for a list)
TEXT_CAP = 2000          # scope statement and use case
LIST_MAX, LIST_ITEM_CAP = 30, 200   # the out-of-scope list
WORDING_CAP, REASON_CAP = 600, 500  # a research question's wording, and the reason for dropping it
TERMS_MAX, TERM_CAP = 60, 120       # a question's terms
ENTRY_CAP = 200                     # a keyword, horizon or mute entry
SEED_COMMENT_CAP = 1000
COMMENT_CAP = 2000                  # a comment on an item

QUESTION_CHOICES = ("accept", "reword", "drop", "split", "add")
TERM_CHOICES = ("keep", "reword", "drop", "add")
ENTRY_CHOICES = ("keep", "reword", "drop", "add")
SEED_CHOICES = ("yes", "no", "unsure")
CENTRALITY = ("central", "background")
KEYWORD_LISTS = ("categories", "horizons", "mute", "frontier", "flagged")

SECTIONS: List[Dict[str, Any]] = [
    {"key": "scope", "title": "Scope and use case", "design": "2.1", "item_types": ["scope_statement", "use_case", "out_of_scope"]},
    {"key": "questions", "title": "Research questions", "design": "2.2", "item_types": ["question"]},
    {"key": "keywords", "title": "Keywords and horizons", "design": "2.3", "item_types": ["keyword_entry"]},
    {"key": "seeds", "title": "Seed papers: confirm", "design": "2.4", "item_types": ["seed_confirm"]},
]
SECTION_KEYS = [s["key"] for s in SECTIONS]


class TemplateError(ValueError):
    """An answer that does not fit the template (a wrong type, a missing required part, a choice that is not offered, a value over its cap)."""


def clean_text(value: Any, cap: int, field: str, required: bool = False) -> str:
    """Plain text: control characters are removed (tab and line feed stay), the ends are trimmed, and a value over `cap` characters is REFUSED, never cut."""
    if not isinstance(value, str):
        raise TemplateError(f"{field} must be text")
    text = _CONTROL.sub("", value.replace("\r\n", "\n").replace("\r", "\n")).strip()
    if len(text) > cap:
        raise TemplateError(f"{field} is longer than {cap} characters")
    if required and not text:
        raise TemplateError(f"{field} is required")
    return text


def _only(value: Any, allowed: Tuple[str, ...], what: str) -> Dict[str, Any]:
    if not isinstance(value, dict):
        raise TemplateError(f"{what} must be an object")
    extra = set(value) - set(allowed)
    if extra:
        raise TemplateError(f"{what} may not contain: {', '.join(sorted(extra))}")
    return value


def _choice(choice: Any, allowed: Tuple[str, ...]) -> str:
    if choice not in allowed:
        raise TemplateError(f"choice must be one of: {', '.join(allowed)}")
    return choice


def _text_type(field: str) -> Callable:
    def validate(value, choice):
        if choice is not None:
            raise TemplateError("this answer has no choice")
        return clean_text(value, TEXT_CAP, field), None
    return validate


def _out_of_scope(value, choice):
    if choice is not None:
        raise TemplateError("this answer has no choice")
    if not isinstance(value, list) or len(value) > LIST_MAX:
        raise TemplateError(f"out of scope must be a list of at most {LIST_MAX} entries")
    return [clean_text(v, LIST_ITEM_CAP, "an out-of-scope entry", required=True) for v in value], None


def _question(value, choice):
    choice = _choice(choice, QUESTION_CHOICES)
    v = _only(value if value is not None else {}, ("wording", "centrality", "terms", "reason"), "a question")
    out: Dict[str, Any] = {}
    if "wording" in v:
        out["wording"] = clean_text(v["wording"], WORDING_CAP, "the wording", required=choice in ("reword", "add"))
    elif choice in ("reword", "add"):
        raise TemplateError("the wording is required")
    if choice == "drop":
        out["reason"] = clean_text(v.get("reason", ""), REASON_CAP, "the reason", required=True)
    elif "reason" in v:
        out["reason"] = clean_text(v["reason"], REASON_CAP, "the reason")
    if choice != "drop":
        if v.get("centrality") not in CENTRALITY:
            raise TemplateError("centrality must be central or background")
        out["centrality"] = v["centrality"]
    elif v.get("centrality") in CENTRALITY:
        out["centrality"] = v["centrality"]
    terms = v.get("terms", [])
    if not isinstance(terms, list) or len(terms) > TERMS_MAX:
        raise TemplateError(f"terms must be a list of at most {TERMS_MAX}")
    clean_terms = []
    for t in terms:
        t = _only(t, ("text", "choice", "was"), "a term")
        ct = {"text": clean_text(t.get("text"), TERM_CAP, "a term", required=True), "choice": _choice(t.get("choice"), TERM_CHOICES)}
        if t.get("was") is not None:
            ct["was"] = clean_text(t["was"], TERM_CAP, "a term's old wording")
        clean_terms.append(ct)
    out["terms"] = clean_terms
    return out, choice


def _keyword_entry(value, choice):
    choice = _choice(choice, ENTRY_CHOICES)
    v = _only(value, ("list", "text", "was"), "an entry")
    if v.get("list") not in KEYWORD_LISTS:
        raise TemplateError(f"list must be one of: {', '.join(KEYWORD_LISTS)}")
    out = {"list": v["list"], "text": clean_text(v.get("text"), ENTRY_CAP, "the entry", required=choice != "drop")}
    if v.get("was") is not None:
        out["was"] = clean_text(v["was"], ENTRY_CAP, "the old wording")
    return out, choice


def _seed_confirm(value, choice):
    choice = _choice(choice, SEED_CHOICES)
    v = _only(value if value is not None else {}, ("comment",), "a seed answer")
    return {"comment": clean_text(v.get("comment", ""), SEED_COMMENT_CAP, "the comment")}, choice


# item type -> (section, validator(value, choice) -> (clean value, clean choice))
ITEM_TYPES: Dict[str, Tuple[str, Callable]] = {
    "scope_statement": ("scope", _text_type("the scope statement")),
    "use_case": ("scope", _text_type("the use case")),
    "out_of_scope": ("scope", _out_of_scope),
    "question": ("questions", _question),
    "keyword_entry": ("keywords", _keyword_entry),
    "seed_confirm": ("seeds", _seed_confirm),
}


def validate_item(item_type: str, value: Any, choice: Any) -> Tuple[Any, Optional[str]]:
    """The clean (value, choice) for an answer of this type, or TemplateError. Unknown types and unknown keys are refused."""
    if item_type not in ITEM_TYPES:
        raise TemplateError("unknown item type")
    return ITEM_TYPES[item_type][1](value, choice)


def section_of(item_type: str) -> Optional[str]:
    return ITEM_TYPES[item_type][0] if item_type in ITEM_TYPES else None


def section_title(key: str) -> str:
    return next((s["title"] for s in SECTIONS if s["key"] == key), key)
