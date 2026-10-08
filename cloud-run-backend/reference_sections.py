"""References and Further reading, built by code (gap 3 fix 1, design 3.4).

The model never writes these. Any reference section it wrote anyway is removed first. "References" lists the
confirmed papers the script names (and always the directly requested paper); "Further reading" lists the other
confirmed papers the generator received, clearly labeled as not discussed. Lines come only from registry records.
"""
from __future__ import annotations

import re
from typing import Any, List, Optional, Sequence

from paper_confirmation import format_citation_line

BUILT_BY = "code@1"

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


def _line(c: Any, with_venue: bool) -> str:
    if with_venue:
        return "- " + format_citation_line(c)
    venue, c.venue = c.venue, None
    try:
        return "- " + format_citation_line(c)
    finally:
        c.venue = venue


def build_sections(confirmed: Sequence[Any], named_pids: Sequence[str], requested_pid: Optional[str] = None) -> str:
    """The code-built sections as Markdown ('' if there is nothing to list)."""
    by_pid = {c.pid: c for c in confirmed}
    ref_order: List[str] = []
    if requested_pid and requested_pid in by_pid:
        ref_order.append(requested_pid)
    for pid in named_pids:
        if pid in by_pid and pid not in ref_order:
            ref_order.append(pid)
    further = [c for c in confirmed if c.pid not in ref_order]
    parts = []
    if ref_order:
        parts.append("## References\n\n" + "\n".join(_line(by_pid[p], True) for p in ref_order))
    if further:
        parts.append("## Further reading\n\n*Papers reviewed while preparing this episode but not discussed in it.*\n\n" +
                     "\n".join(_line(c, False) for c in further))
    return "\n\n".join(parts)


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
