"""References and Further reading, built by code (gap 3 fix 1, design 3.4).

The model never writes these. Any reference section it wrote anyway is removed first. "References" lists the
confirmed papers the script names (and always the directly requested paper); "Further reading" lists the other
confirmed papers the generator received, clearly labeled as not discussed. Lines come only from registry records.
"""
from __future__ import annotations

import re
from typing import Any, List, Optional, Sequence

from paper_confirmation import format_citation_line

BUILT_BY = "code@2"
MAX_TITLE_CHARS = 110
FURTHER_READING_POINTER = ("*Further reading: the other papers reviewed for this episode are listed on the episode page at "
                           "www.copernicusai.fyi.*")

_HEADING = re.compile(r"(?im)^(#{1,3})[ \t]*(references|further reading|bibliography|sources|works cited)[ \t]*$")
_ANY_HEADING = re.compile(r"(?m)^#{1,3}[ \t]+\S")
_STOP = re.compile(r"(?m)^##[ \t]*(?:Hashtags|Episode Details)\b")


def strip_model_reference_sections(description: str) -> str:
    """Remove any References / Further reading / Bibliography / Sources section, up to the next heading."""
    out, pos = [], 0
    text = description or ""
    while True:
        m = _HEADING.search(text, pos)
        if not m:
            out.append(text[pos:])
            break
        out.append(text[pos:m.start()])
        nxt = _ANY_HEADING.search(text, m.end())
        if not nxt:
            break
        pos = nxt.start()
    return "".join(out).rstrip() + ("\n" if description and description.endswith("\n") else "")


# A collective author ("The mathlib Community", "LIGO Scientific Collaboration") has no surname: its last word ("Community") is
# not a name. It is shown whole.
COLLECTIVE_WORDS = {"community", "collaboration", "consortium", "group", "team", "project", "committee", "society", "association",
                    "foundation", "institute", "initiative", "network", "working", "authors", "contributors"}


def is_collective(name: str) -> bool:
    words = [w.lower().strip(".,;:()") for w in (name or "").split()]
    return bool(words) and (words[0] == "the" or any(w in COLLECTIVE_WORDS for w in words))


def _surname(name: str) -> str:
    if is_collective(name):
        return (name or "").strip()
    if "," in (name or ""):  # "Dijkstra, Edsger W." is Surname, Given
        head = name.split(",", 1)[0].split()
        if head:
            return head[-1]
    parts = (name or "").split()
    return parts[-1] if parts else ""


def compact_line(c: Any) -> str:
    """One short line per paper for the description: Surname et al. (year). Title. Venue. Identifier.
    Built from registry fields only; the full citation (all identifiers and the URL) is on the episode web page."""
    from speech_text import latex_display
    names = [_surname(a) for a in c.authors if _surname(a)]
    who = names[0] if len(names) == 1 else f"{names[0]} and {names[1]}" if len(names) == 2 else f"{names[0]} et al." if names else ""
    title = latex_display(c.title).rstrip(".")
    if len(title) > MAX_TITLE_CHARS:
        title = title[:MAX_TITLE_CHARS].rsplit(" ", 1)[0].rstrip(" ,;:") + "\u2026"
    ids = c.ids or {}
    ident = (f"arXiv:{ids['arxiv']}{ids.get('arxiv_version') or ''}" if ids.get("arxiv")
             else f"DOI: {ids['doi']}" if ids.get("doi") else f"PMID {ids['pmid']}" if ids.get("pmid") else "")
    venue = (c.venue or "").rstrip(".")
    if len(venue) > 50:
        venue = venue[:50].rsplit(" ", 1)[0]
    head = f"{who} ({c.year})." if who and c.year else f"{who}." if who else (f"({c.year})." if c.year else "")
    return "- " + " ".join(p for p in (head, title + ".", venue + "." if venue else "", ident) if p)


def full_line(c: Any) -> str:
    """The full citation line (all identifiers, venue and URL) for the episode web page."""
    return "- " + format_citation_line(c)


def build_sections(confirmed: Sequence[Any], named_pids: Sequence[str], requested_pid: Optional[str] = None) -> str:
    """The code-built description section as Markdown ('' if there is nothing to list): References, one compact line per paper
    the script names (and always the requested paper), then one pointer line to the episode page when other confirmed papers
    were reviewed. The Further reading list itself is shown on the episode web page only (see further_reading)."""
    by_pid = {c.pid: c for c in confirmed}
    ref_order: List[str] = []
    if requested_pid and requested_pid in by_pid:
        ref_order.append(requested_pid)
    for pid in named_pids:
        if pid in by_pid and pid not in ref_order:
            ref_order.append(pid)
    parts = []
    if ref_order:
        parts.append("\n".join(compact_line(by_pid[p]) for p in ref_order))
    if len(ref_order) < len(by_pid):
        parts.append(FURTHER_READING_POINTER)
    if not parts:
        return ""
    return ("## References" if ref_order else "## Further reading") + "\n\n" + "\n\n".join(parts)


def further_reading(confirmed: Sequence[Any], named_pids: Sequence[str], requested_pid: Optional[str] = None) -> List[Any]:
    """The confirmed papers that are not in References (not named and not the requested paper), in list order."""
    listed = set(named_pids) | ({requested_pid} if requested_pid else set())
    return [c for c in confirmed if c.pid not in listed]


def apply_reference_sections(description: str, confirmed: Sequence[Any], named_pids: Sequence[str], requested_pid: Optional[str] = None) -> str:
    """Strip model-written reference sections and insert the code-built ones before Hashtags / Episode Details (or at the end)."""
    body = strip_model_reference_sections(description or "")
    sections = build_sections(confirmed, named_pids, requested_pid)
    if not sections:
        return body
    m = _STOP.search(body)
    if m:
        return body[:m.start()].rstrip() + "\n\n" + sections + "\n\n" + body[m.start():]
    return body.rstrip() + "\n\n" + sections + "\n"


# ---- feed rendering: applied when the RSS item is built; the stored description is never rewritten ----
_REF_START = re.compile(r"(?im)^##[ \t]*(references)[ \t]*$")
_NEXT_SECTION = re.compile(r"(?m)^##[ \t]")
_POINTER_LINE = re.compile(r"(?im)^[*_]*[ \t]*Further reading:[^\n]*$")
_BULLET = re.compile(r"^([-*][ \t]+)(.+?)[ \t]*$")
_ARXIV = re.compile(r"arXiv:\s*((?:\d{4}\.\d{4,5}|[a-z-]+(?:\.[A-Z]{2})?/\d{7})(?:v\d+)?)", re.I)
_DOI = re.compile(r"\bDOI:?\s*(10\.\d{4,9}/\S+?)[.,;]*(?=\s|$)", re.I)
_PMID = re.compile(r"\bPMID:?\s*(\d{5,9})\b", re.I)


def reference_url(line: str) -> str:
    """The one URL a reference line points to: arXiv abs URL (with its version), else DOI URL, else PubMed URL; '' if none."""
    m = _ARXIV.search(line)
    if m:
        return f"https://arxiv.org/abs/{m.group(1)}"
    m = _DOI.search(line)
    if m:
        return f"https://doi.org/{m.group(1)}"
    m = _PMID.search(line)
    return f"https://pubmed.ncbi.nlm.nih.gov/{m.group(1)}/" if m else ""


def render_for_feed(description: str, page_url: str) -> str:
    """Link each reference line (the whole line is the link, as on the episode page) and point the Further reading line at the episode's own
    page. Lines that already carry a link are left alone; lines with no identifier stay plain text."""
    text = description or ""
    m = _REF_START.search(text)
    if m:
        end = _NEXT_SECTION.search(text, m.end())
        stop = end.start() if end else len(text)
        out = []
        for line in text[m.end():stop].split("\n"):
            b = _BULLET.match(line)
            if b and "](" not in line:
                url = reference_url(b.group(2))
                if url:
                    label = b.group(2).replace("[", "(").replace("]", ")")
                    line = f"{b.group(1)}[{label}]({url})"
            out.append(line)
        text = text[:m.end()] + "\n".join(out) + text[stop:]
    if page_url:
        text = _POINTER_LINE.sub(
            f"*Further reading: the other papers reviewed for this episode are listed on [the episode page]({page_url}).*", text)
    return text
