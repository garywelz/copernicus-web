"""A chapter in a scholarly book, confirmed either by its registry record or, where there is none, by the excerpt Gary attaches.

The podcast's other classes all rest on something a machine can fetch: a registry record, a repository blob, a web address whose bytes can
be hashed. A large part of the scholarly literature is not like that. A historian's argument lives in a chapter of an edited volume: it may
carry a DOI, it may be reachable only by a JSTOR stable number or a handle, and it may exist for the reader only on paper. Refusing those
sources does not make the podcast more careful; it makes it unable to discuss the scholarship that exists, and leaves an episode leaning on
whatever happens to be free on the web, which is the weaker evidence.

So a chapter is confirmed one of two ways:

  by its record   a DOI whose Crossref record is a book chapter, a book part, a book section, a monograph or a reference entry. This is the
                  ordinary registry confirmation (paper_confirmation), unchanged, and nothing here is involved beyond naming the class.

  by its excerpt  a STABLE IDENTIFIER with no usable record - a JSTOR stable number, a handle, an ISBN with a chapter - plus the passage
                  Gary transcribes from the chapter itself. The identifier must be one that still resolves to the same work years from now:
                  a library search result or a bookseller's page is refused, because it identifies a copy for sale, not a work.

The excerpt is the evidence, and this module treats it as such. It is pinned by the SHA-256 of its text, so changing a word changes the list
hash and a frozen list cannot be quietly re-edited. The supplied title must occur in the excerpt, compared without spaces or punctuation the
way a web release's title is, so a passage pasted from the wrong chapter is refused rather than trusted. The excerpt is held in the private
store and never published: what the list records is its hash, its length and where it came from.

What this module can NOT do is tell whether the transcription is faithful. No code can: the book is on a shelf. That is why the class states
its own limit in every episode that uses it - a chapter is not a peer-reviewed journal article, and the script must say so - and why the
status wording below never claims the chapter was verified, only that it was published in a scholarly book and quoted from a passage Gary
attached. Nothing here touches Firestore or the network.
"""
from __future__ import annotations

import hashlib
import re
import unicodedata
from datetime import datetime, timezone
from typing import Any, Dict, Optional, Tuple
from urllib.parse import urlparse

REGISTRY = "chapter_excerpt"

MIN_EXCERPT_CHARS = 200          # shorter than this is a citation, not a passage to write from
MAX_EXCERPT_CHARS = 40_000
MAX_TITLE_CHARS = 300
MAX_BOOK_CHARS = 300

# Crossref record types that ARE a scholarly book or a part of one. "book-chapter" is the common case; the others appear for volumes
# catalogued whole, for reference works, and for the parts of a series. A journal article and posted content keep their own classes.
BOOK_RECORD_TYPES = ("book-chapter", "book-part", "book-section", "book", "monograph", "reference-entry", "reference-book", "edited-book")

_JSTOR = re.compile(r"^https?://(?:www\.)?jstor\.org/stable/([A-Za-z0-9.\-/]+)$", re.I)
_HANDLE = re.compile(r"^https?://(?:hdl\.)?handle\.net/(\d+(?:\.\d+)*/\S+)$", re.I)
_HANDLE_BARE = re.compile(r"^hdl:(\d+(?:\.\d+)*/\S+)$", re.I)
_ISBN = re.compile(r"^isbn:\s*([0-9][0-9\-xX ]{8,24})$", re.I)


class ChapterRefused(Exception):
    """The identifier or the excerpt cannot support an item. The message is the fixed reason, safe to log."""

    def __init__(self, reason: str, detail: str = ""):
        super().__init__(f"{reason}{f': {detail}' if detail else ''}")
        self.reason = reason
        self.detail = detail


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def sha256_hex(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def is_book_record(record_type: Optional[str]) -> bool:
    """Whether a Crossref record type is a scholarly book or a part of one."""
    return (record_type or "").strip().lower() in BOOK_RECORD_TYPES


# --- the identifier ------------------------------------------------------------------------------------------------------------
def parse_identifier(raw: Any) -> Tuple[str, str]:
    """(scheme, value) for a stable identifier this class accepts, or raise ChapterRefused.

    Accepted: a JSTOR stable number, a handle (as a handle.net address or as `hdl:<prefix>/<suffix>`), an ISBN. Everything else is
    refused by shape, before any network call, so a bookseller's address or a search result never reaches the list."""
    if not isinstance(raw, str) or not raw.strip():
        return _refuse("identifier_empty")
    s = raw.strip()
    if len(s) > 500:
        _refuse("identifier_too_long")
    m = _JSTOR.match(s)
    if m:
        return "jstor", m.group(1)
    m = _HANDLE.match(s) or _HANDLE_BARE.match(s)
    if m:
        return "handle", m.group(1)
    m = _ISBN.match(s)
    if m:
        digits = re.sub(r"[^0-9Xx]", "", m.group(1))
        if len(digits) not in (10, 13):
            _refuse("isbn_wrong_length", f"{len(digits)} characters")
        return "isbn", digits.upper()
    host = (urlparse(s).hostname or "").lower() if s.lower().startswith(("http://", "https://")) else ""
    _refuse("identifier_not_stable", host or s[:60])
    raise AssertionError("unreachable")       # _refuse always raises; this keeps the return type honest


def _refuse(reason: str, detail: str = ""):
    raise ChapterRefused(reason, detail)


def identifier_url(scheme: str, value: str) -> str:
    """The address a listener can follow, for the show notes. An ISBN has no single address, so it is cited as an ISBN."""
    if scheme == "jstor":
        return f"https://www.jstor.org/stable/{value}"
    if scheme == "handle":
        return f"https://hdl.handle.net/{value}"
    return f"isbn:{value}"


# --- the excerpt ---------------------------------------------------------------------------------------------------------------
def _flat(s: str) -> str:
    """Letters and digits only, lower case, accents folded: how a title is compared with a passage that was retyped or read out of a PDF."""
    norm = unicodedata.normalize("NFKD", s or "")
    return re.sub(r"[^a-z0-9]+", "", "".join(ch for ch in norm if not unicodedata.combining(ch)).lower())


def title_in_excerpt(title: str, excerpt: str) -> bool:
    """Whether the supplied title occurs in the excerpt, ignoring spacing, punctuation, case and accents."""
    t = _flat(title)
    return bool(t) and t in _flat(excerpt)


def confirm(identifier: Any, title: str, excerpt: str, *, book_title: str = "", authors: str = "", year: Any = "",
            source_note: str = "") -> Dict[str, Any]:
    """Confirm a chapter from a stable identifier and the passage Gary attached, or raise ChapterRefused.

    Returns the confirmation record for the item: the identity, the bibliographic details Gary supplied, and the pin - the hash and
    length of the excerpt. The excerpt text itself is NOT in the record; the caller stores it privately."""
    scheme, value = parse_identifier(identifier)
    title = (title or "").strip()
    if not title:
        _refuse("title_missing")
    if len(title) > MAX_TITLE_CHARS:
        _refuse("title_too_long")
    book = (book_title or "").strip()
    if len(book) > MAX_BOOK_CHARS:
        _refuse("book_title_too_long")
    text = (excerpt or "").strip()
    if len(text) < MIN_EXCERPT_CHARS:
        _refuse("excerpt_too_short", f"{len(text)} characters; at least {MIN_EXCERPT_CHARS} are needed")
    if len(text) > MAX_EXCERPT_CHARS:
        _refuse("excerpt_too_long", f"{len(text)} characters")
    if not title_in_excerpt(title, text):
        _refuse("title_not_in_excerpt", "the passage does not contain the chapter title as given")
    try:
        year_s = str(int(str(year).strip())) if str(year).strip() else ""
    except ValueError:
        _refuse("year_not_a_number", str(year)[:20])
    return {
        "status": "confirmed",
        "registry": REGISTRY,
        "scheme": scheme,
        "identifier": value,
        "url": identifier_url(scheme, value),
        "title": title,
        "book_title": book or None,
        "authors": (authors or "").strip() or None,
        "year": year_s or None,
        "record_type": "chapter_excerpt",
        "excerpt_sha256": sha256_hex(text),
        "excerpt_chars": len(text),
        "source_note": (source_note or "").strip() or None,
        "confirmed_at": _now(),
    }


def identifiers_of(confirmation: Dict[str, Any]) -> Dict[str, Any]:
    """The identity block for the item, which `curated_sources.item_key` turns into this item's key."""
    return {"chapter": f"{confirmation['scheme']}:{confirmation['identifier']}", "url": confirmation.get("url") or ""}
