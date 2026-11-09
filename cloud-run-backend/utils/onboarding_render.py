"""Rendering an engine's approved onboarding answers into the files they change (onboarding PR 3b-1; docs/design/ENGINE_ONBOARDING_FORM.md 6.2, 6.4).

ONE MODULE FOR BOTH USES. The dashboard's proposed-vs-current diff (3b-1) and the change bundle (3b-2) call the same `render_files`, so what Gary reviews is
byte-for-byte what a bundle will carry. It is pure: it takes items and the current text of each file (or None) and returns text. It reads no database and no network.

THE MAPPING (design 6.2):
  scope      -> README.md          the scope paragraph only (the statement, and the out-of-scope list). The use case is not a repo file (design 2.1).
  questions  -> docs/research_focus.json   active_questions
  keywords   -> docs/research_focus.json   categories, horizons, mute
  seeds      -> docs/seed_papers.md        a generated "owners' confirmation" block; the rest of the file is left exactly as it is

EVERY FILE IS MERGED INTO ITS CURRENT TEXT, never rewritten from nothing, so a diff shows only what the owners changed. With no current text (the engine has
no repository, or the file is new) the file holds only the generated part.

research_focus.json: each question keeps the A2 fields `q`, `terms`, `since` (the acquisition contract reads these) and the file's existing `id`; the one new field
is the optional `priority` ("central" or "background", design 6.4), which nothing reads yet. `since` is the matched question's existing date, or `as_of` for a new
question. Keys the form does not own (`project`, `updated`, `frontier`, `flagged`, ...) are carried over untouched. The `frontier` and `flagged` lists hold
objects in the A2 contract, which the template's one-line text entries cannot express, so entries an owner typed into those two lists are NOT rendered; they are
returned in `notes` for Core to decide.
"""
import hashlib
import json
import re
from typing import Any, Dict, List, Optional

SECTION_FILES = {"scope": "README.md", "questions": "docs/research_focus.json", "keywords": "docs/research_focus.json", "seeds": "docs/seed_papers.md"}
STRING_LISTS = ("categories", "horizons", "mute")
OBJECT_LISTS = ("frontier", "flagged")
SEEDS_BEGIN = "<!-- onboarding:seed-confirmations:begin -->"
SEEDS_END = "<!-- onboarding:seed-confirmations:end -->"
SEED_WORDS = {"yes": "confirmed", "no": "not confirmed", "unsure": "unsure"}


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def files_for(sections: List[str]) -> List[str]:
    """The distinct output paths for these sections, in a stable order."""
    out: List[str] = []
    for s in sections:
        p = SECTION_FILES.get(s)
        if p and p not in out:
            out.append(p)
    return out


# ---- research_focus.json ------------------------------------------------------------------------------------------------------------------------------
def _scalar(v: Any) -> str:
    return json.dumps(v, ensure_ascii=False)


def dump_json(obj: Any, indent: int = 0) -> str:
    """The house style of the engines' research_focus.json: two-space indent, lists of plain values on one line, a blank line between top-level keys. Matching it
    keeps a diff to the real changes."""
    pad, inner = "  " * indent, "  " * (indent + 1)
    if isinstance(obj, dict):
        if not obj:
            return "{}"
        parts = [f"{inner}{_scalar(k)}: {dump_json(v, indent + 1)}" for k, v in obj.items()]
        return "{\n" + (",\n\n" if indent == 0 else ",\n").join(parts) + "\n" + pad + "}"
    if isinstance(obj, list):
        if not obj:
            return "[]"
        if all(not isinstance(v, (dict, list)) for v in obj):
            return "[" + ", ".join(_scalar(v) for v in obj) + "]"
        return "[\n" + ",\n".join(inner + dump_json(v, indent + 1) for v in obj) + "\n" + pad + "]"
    return _scalar(obj)


def _live_terms(value: dict) -> List[str]:
    return [t["text"] for t in (value.get("terms") or []) if t.get("choice") != "drop" and t.get("text")]


def _question_row(item: dict, base_questions: List[dict], as_of: str) -> Optional[dict]:
    """One research question as it should appear in the file, or None when it is dropped or was split into others."""
    value, choice, ctx = item.get("value") or {}, item.get("choice"), item.get("context") or {}
    if choice in ("drop", "split"):
        return None
    iid, original = item.get("item_id"), ctx.get("original_wording")
    prior = next((b for b in base_questions if b.get("id") == iid or (original and b.get("q") == original)), None)
    wording = value.get("wording") or original or (prior or {}).get("q") or ""
    row: Dict[str, Any] = {}
    if iid:
        row["id"] = iid
    row.update({"q": wording, "terms": _live_terms(value), "since": (prior or {}).get("since") or as_of})
    if value.get("centrality") in ("central", "background"):
        row["priority"] = value["centrality"]
    return row


def render_research_focus(base_text: Optional[str], question_items: Optional[List[dict]], keyword_items: Optional[List[dict]], as_of: str):
    """(text, notes). `question_items` / `keyword_items` of None leave that part of the file exactly as it is."""
    notes: List[str] = []
    try:
        doc = json.loads(base_text) if base_text else {}
        if not isinstance(doc, dict):
            raise ValueError("not an object")
    except ValueError:
        doc, notes = {}, ["The current research_focus.json could not be parsed, so the proposed file holds only the owners' parts."]
    if question_items is not None:
        base_questions = [b for b in (doc.get("active_questions") or []) if isinstance(b, dict)]
        rows = [r for r in (_question_row(i, base_questions, as_of) for i in question_items) if r]
        doc["active_questions"] = rows
    if keyword_items is not None:
        lists: Dict[str, List[str]] = {name: [] for name in STRING_LISTS}
        skipped = 0
        for i in keyword_items:
            v, choice = i.get("value") or {}, i.get("choice")
            if choice == "drop":
                continue
            if v.get("list") in STRING_LISTS and v.get("text"):
                lists[v["list"]].append(v["text"])
            elif v.get("list") in OBJECT_LISTS:
                skipped += 1
        for name in STRING_LISTS:
            if lists[name] or name in doc:
                doc[name] = lists[name]
        if skipped:
            notes.append(f"{skipped} entr{'y' if skipped == 1 else 'ies'} typed into frontier or flagged were not rendered: those lists hold objects in the acquisition contract, "
                         "which a one-line entry cannot express. Core decides how to carry them.")
    return dump_json(doc) + "\n", notes


# ---- README.md: the scope paragraph ----------------------------------------------------------------------------------------------------------------------
def scope_paragraph(items: List[dict]) -> str:
    by = {i.get("item_id"): i.get("value") for i in items}
    statement = (by.get("scope-statement") or "").strip() if isinstance(by.get("scope-statement"), str) else ""
    out_of_scope = [s for s in (by.get("out-of-scope") or []) if isinstance(s, str) and s.strip()] if isinstance(by.get("out-of-scope"), list) else []
    parts = [statement] if statement else []
    if out_of_scope:
        parts.append("Out of scope: " + "; ".join(out_of_scope) + ".")
    return "\n\n".join(parts)


def render_readme(base_text: Optional[str], paragraph: str):
    """(text, notes). The scope paragraph replaces the body of the README's existing 'Scope' heading (up to the next heading of the same or a higher level); with no
    such heading it is appended under a new '## Scope and use case' heading; with no README it is the whole file."""
    if not paragraph:
        return (base_text or ""), ["The scope statement is empty, so the README is unchanged."]
    block = paragraph.rstrip() + "\n"
    if not base_text:
        return "## Scope and use case\n\n" + block, []
    lines = base_text.split("\n")
    for n, line in enumerate(lines):
        m = re.match(r"^(#{1,6})\s+.*\bscope\b", line, re.I)
        if m:
            level = len(m.group(1))
            end = next((k for k in range(n + 1, len(lines)) if re.match(r"^#{1,%d}\s" % level, lines[k])), len(lines))
            new = lines[:n + 1] + [""] + block.rstrip("\n").split("\n") + [""] + lines[end:]
            return "\n".join(new).rstrip("\n") + "\n", []
    return base_text.rstrip("\n") + "\n\n## Scope and use case\n\n" + block, []


# ---- docs/seed_papers.md -------------------------------------------------------------------------------------------------------------------------------
def seeds_block(items: List[dict]) -> str:
    rows = []
    for i in items:
        ctx, v = i.get("context") or {}, i.get("value") or {}
        label = SEED_WORDS.get(i.get("choice"), "unanswered")
        line = f"- {ctx.get('citation') or i.get('item_id')}" + (f" (`{ctx['identifier']}`)" if ctx.get("identifier") else "") + f": {label}"
        if v.get("comment"):
            line += f". Owners' comment: {v['comment']}"
        rows.append(line)
    return "\n".join([SEEDS_BEGIN, "## Owners' confirmation of the seed papers", "", *rows, SEEDS_END]) + "\n"


def render_seed_papers(base_text: Optional[str], items: List[dict]):
    block = seeds_block(items)
    if not base_text:
        return block, []
    if SEEDS_BEGIN in base_text and SEEDS_END in base_text:
        head, rest = base_text.split(SEEDS_BEGIN, 1)
        tail = rest.split(SEEDS_END, 1)[1].lstrip("\n")
        return head + block + (("\n" + tail) if tail else ""), []
    return base_text.rstrip("\n") + "\n\n" + block, []


# ---- the one entry point ---------------------------------------------------------------------------------------------------------------------------------
def render_files(items_by_section: Dict[str, List[dict]], bases: Dict[str, Optional[str]], as_of: str) -> List[Dict[str, Any]]:
    """The proposed files for these sections. `items_by_section` maps a section key to its stored items; `bases` maps a path to its current text (or None).
    Returns [{path, content, sha256, sections, notes}] in a stable order. Sections that share a file (questions and keywords) are rendered into it together."""
    out = []
    for path in files_for(list(items_by_section)):
        secs = [s for s in items_by_section if SECTION_FILES.get(s) == path]
        base = bases.get(path)
        if path == "README.md":
            text, notes = render_readme(base, scope_paragraph(items_by_section["scope"]))
        elif path == "docs/research_focus.json":
            text, notes = render_research_focus(base, items_by_section.get("questions"), items_by_section.get("keywords"), as_of)
        else:
            text, notes = render_seed_papers(base, items_by_section["seeds"])
        out.append({"path": path, "content": text, "sha256": sha256_text(text), "sections": secs, "notes": notes})
    return out
