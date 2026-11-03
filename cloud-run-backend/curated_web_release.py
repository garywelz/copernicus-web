"""A company release published at a stable web address (a PDF or a page), confirmed by a guarded fetch and pinned by the SHA-256 of the bytes.

`openai/math` is the one repository whose manuscripts the curated mode can confirm (curated_sources, openai_math_index). A company release that is
NOT in that repository (for example a company's own paper on its website) is confirmed here instead:

  * the address is fetched through `safe_fetch.guarded_get` (public addresses only, redirects re-checked, size and time capped);
  * the answer must be HTTP 200 with a PDF or a web page, from which plain text can be read;
  * the producer-supplied title must occur in that text (compared without spaces or punctuation, because a PDF's text layer loses both), and so must the company's name (or the company's name in the address),
    so a wrong page or a wrong company is refused rather than trusted;
  * the item is PINNED by the SHA-256 of the fetched bytes and the fetch date. Nothing is taken from a model.

The publish-day re-check (scripts/recheck_curated_statuses.py) fetches the same address again and compares the hash: a different hash, or a
release that is gone (404 or 410), is a change and means DO NOT PUBLISH; an address that cannot be read at all means nothing is known (exit 3).
A page that embeds changing content (a timestamp, a script nonce) will hash differently on every fetch; a PDF is the stable case. That is a
limit of pinning bytes, and the re-check reports it as a change for Gary to look at.

The status of a web release is always "unverified" (there is no catalogue to consult); it can be marked "checked by experts" the same way as any
other company release. Nothing here touches Firestore. The network layer and the PDF reader are injectable, so this is tested offline.
"""
from __future__ import annotations

import hashlib
import io
import re
from datetime import datetime, timezone
from html.parser import HTMLParser
from typing import Any, Callable, Dict, List, Optional

import curated_sources as cs
from safe_fetch import FetchRefused, guarded_get, validate_url

REGISTRY = "web_release"
MAX_RELEASE_BYTES = 15_000_000          # a long paper is a few MB; the ordinary 2 MB cap for commentary pages is too small for a PDF
MIN_TEXT_CHARS = 200
EVIDENCE_CHARS = 6000                   # the opening of the document (title, abstract, introduction): what the script may be checked against
MAX_COMPANY_CHARS = 60
GONE_STATUSES = (404, 410)


class WebReleaseUnavailable(Exception):
    """The address could not be reached (a network failure, not a refusal), so nothing is known. The route answers 503; the re-check exits 3."""


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def sha256_hex(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


# --- reading the text ----------------------------------------------------------------------------------------------------------
class _Text(HTMLParser):
    _SKIP = {"script", "style", "noscript", "template", "svg"}

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.parts: List[str] = []
        self._skip = 0

    def handle_starttag(self, tag, attrs):
        if tag in self._SKIP:
            self._skip += 1

    def handle_endtag(self, tag):
        if tag in self._SKIP and self._skip:
            self._skip -= 1

    def handle_data(self, data):
        if not self._skip:
            self.parts.append(data)


def html_text(body: bytes) -> str:
    p = _Text()
    p.feed(body.decode("utf-8", "replace"))
    return re.sub(r"\s+", " ", " ".join(p.parts)).strip()


def pdf_text(body: bytes) -> str:
    """Plain text of a PDF, from the first pages (enough for the evidence excerpt and the title check). Raises ValueError if it cannot be read."""
    try:
        try:
            from pypdf import PdfReader
        except ImportError:
            from PyPDF2 import PdfReader
    except ImportError:
        raise ValueError("no PDF reader is installed")
    try:
        reader = PdfReader(io.BytesIO(body))
        out, n = [], 0
        for page in reader.pages[:8]:
            out.append(page.extract_text() or "")
            n += len(out[-1])
            if n > 4 * EVIDENCE_CHARS:
                break
    except Exception as e:  # noqa: BLE001 - any parser failure means the text cannot be read
        raise ValueError(f"the PDF could not be read ({type(e).__name__})")
    return re.sub(r"\s+", " ", " ".join(out)).strip()


def extract_text(body: bytes, content_type: str, pdf_reader: Optional[Callable[[bytes], str]] = None) -> str:
    ct = (content_type or "").split(";")[0].strip().lower()
    if ct == "application/pdf" or body[:5] == b"%PDF-":
        if body[:5] != b"%PDF-":
            raise ValueError("it says it is a PDF but is not one")
        return (pdf_reader or pdf_text)(body)
    if ct in ("text/html", "application/xhtml+xml"):
        return html_text(body)
    raise ValueError(f"unsupported_content_type:{ct or 'unknown'}")


# --- fetching ----------------------------------------------------------------------------------------------------------------------
async def fetch_release(url: str, fetch=None):
    """The guarded answer for `url`. Raises WebReleaseUnavailable for a network failure; FetchRefused (a guard) is left to the caller."""
    try:
        return await (fetch or guarded_get)(url, max_bytes=MAX_RELEASE_BYTES, timeout=30)
    except FetchRefused:
        raise
    except OSError as e:
        raise WebReleaseUnavailable(f"the address could not be read ({type(e).__name__})")
    except Exception as e:  # noqa: BLE001 - aiohttp and asyncio errors that are not guards: nothing is known
        raise WebReleaseUnavailable(f"the address could not be read ({type(e).__name__})")


def _refused(url: str, reason: str, detail: str = "") -> Dict[str, Any]:
    return {"item_id": None, "input": url[:cs.MAX_ITEM_CHARS], "class": cs.COMPANY_RELEASE, "added_by": "gary",
            "confirmation": {"status": cs.REFUSED, "reason": reason, "detail": detail, "directories": []}, "approved": False}


def _norm(s: str) -> str:
    return cs._norm_words(s)


MIN_TITLE_SQUASHED = 12


def _squash(s: str) -> str:
    """Letters and digits only, lower case, no spaces or punctuation. A PDF's text layer loses the spacing and the superscripts of a title
    ("A 2^{o(n)} Time Algorithm for 3-SAT" is read as "A2 o(n) TIME ALGORITHM FOR 3-SAT"), so titles are compared with the spacing removed."""
    return "".join(_norm(s).split())


def title_in_text(title: str, text: str) -> bool:
    """Whether `title` occurs in `text`, ignoring case, accents, spaces and punctuation. A title with fewer than MIN_TITLE_SQUASHED letters and
    digits is too short to identify a document this way and never matches."""
    t = _squash(title)
    return len(t) >= MIN_TITLE_SQUASHED and t in _squash(text)


async def confirm_web_release(url: str, title: str, company: str, date: str, authors=(), fetch=None,
                              pdf_reader: Optional[Callable[[bytes], str]] = None) -> Dict[str, Any]:
    """A confirmed company-release item for `url`, or a refused entry. Raises WebReleaseUnavailable when the address cannot be reached."""
    url, title, company = (url or "").strip(), (title or "").strip(), (company or "").strip()
    if not url.lower().startswith("https://"):
        return _refused(url, "not_https", "a company release is pinned only at an https address")
    try:
        validate_url(url)
    except FetchRefused as e:
        return _refused(url, "bad_address", e.reason)
    if not title or len(title) > 300:
        return _refused(url, "bad_title", "the title is required (at most 300 characters)")
    if not company or len(company) > MAX_COMPANY_CHARS:
        return _refused(url, "bad_company", f"the company is required (at most {MAX_COMPANY_CHARS} characters)")
    if not cs._DATE.match(date or "") or not cs._real_date(date):
        return _refused(url, "bad_date", "the date must be a real date: YYYY, YYYY-MM or YYYY-MM-DD")
    authors = [a.strip() for a in (authors or []) if isinstance(a, str) and a.strip()]
    if len(authors) > 5 or any(len(a) > 120 for a in authors):
        return _refused(url, "bad_authors", "at most five authors, each at most 120 characters")

    try:
        res = await fetch_release(url, fetch)
    except FetchRefused as e:
        return _refused(url, f"fetch_refused:{e.reason}", e.detail)
    if res.status != 200:
        return _refused(url, f"http_{res.status}", "the address did not answer 200")
    if not res.body:
        return _refused(url, "empty", "the address returned nothing")
    ctype = res.headers.get("content-type", "")
    try:
        text = extract_text(res.body, ctype, pdf_reader)
    except ValueError as e:
        msg = str(e)
        return _refused(url, msg if msg.startswith("unsupported_content_type") else "text_not_readable", msg)
    if len(text) < MIN_TEXT_CHARS:
        return _refused(url, "no_readable_text", f"only {len(text)} readable characters (a scanned or image-only PDF cannot be used)")
    if not title_in_text(title, text):
        return _refused(url, "title_not_in_document", "the title you gave does not occur in the fetched document")
    host = (validate_url(res.final_url)[1] or "").lower()
    if _norm(company) not in _norm(text) and _norm(company).replace(" ", "") not in host.replace("-", "").replace(".", ""):
        return _refused(url, "company_not_found", "the company's name occurs neither in the document nor in its address")

    sha, fetched_at = sha256_hex(res.body), _now()
    identifiers = {"release_url": url}
    conf = {"status": cs.CONFIRMED, "source_class": cs.COMPANY_RELEASE, "registry": REGISTRY, "url": url, "final_url": res.final_url,
            "sha256": sha, "bytes": len(res.body), "content_type": ctype.split(";")[0].strip().lower(), "fetched_at": fetched_at,
            "confirmed_at": fetched_at, "company": company, "date": date, "title": title}
    return {"item_id": cs.item_id(identifiers), "input": url[:cs.MAX_ITEM_CHARS], "class": cs.COMPANY_RELEASE, "added_by": "gary",
            "identifiers": identifiers, "title": title, "authors": authors or [company], "year": int(date[:4]), "venue": None, "url": url,
            "evidence_text": text[:EVIDENCE_CHARS], "confirmation": conf, "relevance_score": None, "approved": True,
            "company": company, "date": date, "result_status": "unverified",
            "status_basis": {"web_release": True, "url": url, "sha256": sha, "fetched_at": fetched_at}}


def is_web_release(item: Dict[str, Any]) -> bool:
    return item.get("class") == cs.COMPANY_RELEASE and (item.get("confirmation") or {}).get("registry") == REGISTRY


# --- the publish-day re-check ----------------------------------------------------------------------------------------------------
async def recheck_web_releases(items: List[Dict[str, Any]], fetch=None) -> List[Dict[str, Any]]:
    """One row per web release: fetch the recorded address again and compare the SHA-256 with the pinned one. Same row keys as
    openai_math_status.recheck_items. `current` is 'unreadable' when nothing is known (the command then exits 3)."""
    rows = []
    for it in items:
        if not is_web_release(it):
            continue
        c = it.get("confirmation") or {}
        pinned = c.get("sha256") or ""
        recorded = f"sha256 {pinned[:12]}"
        notes: List[str] = []
        current, changed = recorded, False
        try:
            res = await fetch_release(c.get("url") or "", fetch)
            if res.status in GONE_STATUSES:
                current, changed = f"HTTP {res.status}", True
                notes.append("the release is no longer at its address")
            elif res.status != 200:
                current, notes = "unreadable", [f"the address answered HTTP {res.status}"]
            else:
                now = sha256_hex(res.body)
                current = f"sha256 {now[:12]}"
                changed = now != pinned
                if changed:
                    notes.append(f"the fetched bytes differ from the pinned ones (fetched {c.get('fetched_at')}); a page with changing content "
                                 "hashes differently on every fetch, a PDF should not")
        except FetchRefused as e:
            current, notes = "unreadable", [f"the address was refused by a guard ({e.reason})"]
        except WebReleaseUnavailable as e:
            current, notes = "unreadable", [str(e)]
        rows.append({"item_id": it.get("item_id"), "title": it.get("title"), "path": c.get("url"), "recorded": recorded, "baseline": recorded,
                     "current": current, "changed": changed, "notes": notes})
    return rows
