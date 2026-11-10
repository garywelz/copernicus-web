"""Paper identifiers for the onboarding form (PR 4b-1; docs/design/ENGINE_ONBOARDING_FORM.md 2.4, 5.5).

A seed or a paper is identified by a DOI, an arXiv id or a PubMed id, written 'doi:..', 'arxiv:..' or 'pmid:..'. Never by an author name. The patterns, the
normalisation and the seed item id are the SAME as the loader's (scripts/onboarding/load_engine.py); tests/test_onboarding_lookup.py checks the two agree, so a seed
an owner adds and the same seed read later from the engine's repository land on one document.
"""
import hashlib
import re
from typing import Optional, Tuple

DOI_RE = re.compile(r"^10\.\d{4,9}/\S+$")
ARXIV_RE = re.compile(r"^(?:\d{4}\.\d{4,5}|[a-z][a-z\-]*(?:\.[a-z]{2})?/\d{7})$")
PMID_RE = re.compile(r"^\d{1,9}$")
IDENTIFIER_CAP = 200          # a normalised identifier longer than this is refused
QUERY_CAP = 400               # what an owner may type into the lookup box
TITLE_MIN = 8
_CONTROL = re.compile(r"[\x00-\x1f\x7f]")
_DOI_PREFIX = re.compile(r"^(?:https?://(?:dx\.)?doi\.org/|doi:\s*)", re.I)
_ARXIV_PREFIX = re.compile(r"^(?:https?://arxiv\.org/(?:abs|pdf)/|arxiv:\s*)", re.I)
_PMID_PREFIX = re.compile(r"^(?:https?://pubmed\.ncbi\.nlm\.nih\.gov/|pmid:\s*)", re.I)


def normalise_identifier(kind: str, raw: Optional[str]) -> Optional[str]:
    """'doi:..', 'arxiv:..' or 'pmid:..' (lower case; prefixes and an arXiv version suffix removed), or None when the text is not a valid identifier of that kind."""
    s = (raw or "").strip().strip("`").strip()
    if kind == "doi":
        s = _DOI_PREFIX.sub("", s).lower()
        out = "doi:" + s if DOI_RE.match(s) else None
    elif kind == "arxiv":
        s = re.sub(r"v\d+$", "", _ARXIV_PREFIX.sub("", s).lower())
        out = "arxiv:" + s if ARXIV_RE.match(s) else None
    elif kind == "pmid":
        s = _PMID_PREFIX.sub("", s).rstrip("/")
        out = "pmid:" + s if PMID_RE.match(s) else None
    else:
        out = None
    return out if out and len(out) <= IDENTIFIER_CAP else None


def seed_item_id(key: str) -> str:
    """The item id of the seed with this identifier ('doi:..' or 'arxiv:..'): the loader's formula."""
    return "seed-" + hashlib.sha256(key.encode("utf-8")).hexdigest()[:12]


def classify(raw: object) -> Tuple[Optional[str], Optional[str]]:
    """What an owner typed, as ('doi' | 'arxiv' | 'pmid', the normalised identifier) or ('title', the title with its spaces collapsed), or (None, None) when it is
    neither a valid identifier nor a plausible title. Something that LOOKS like an identifier but is not a valid one is refused; it is never searched as a title."""
    if not isinstance(raw, str) or len(raw) > QUERY_CAP or _CONTROL.search(raw.replace("\n", " ").replace("\t", " ")):
        return None, None
    s = " ".join(raw.split())
    if not s:
        return None, None
    low = s.lower()
    if _DOI_PREFIX.match(s) or low.startswith("10."):
        n = normalise_identifier("doi", s)
        return ("doi", n) if n else (None, None)
    if _ARXIV_PREFIX.match(s) or re.match(r"^\d{4}\.\d{4,5}(v\d+)?$", low) or re.match(r"^[a-z][a-z\-]*(\.[a-z]{2})?/\d{7}(v\d+)?$", low):
        n = normalise_identifier("arxiv", s)
        return ("arxiv", n) if n else (None, None)
    if _PMID_PREFIX.match(s) or re.match(r"^\d+$", s):
        n = normalise_identifier("pmid", s)
        return ("pmid", n) if n else (None, None)
    if len(s) < TITLE_MIN or not re.search(r"[^\W\d_]{3}", s):
        return None, None
    return "title", s
