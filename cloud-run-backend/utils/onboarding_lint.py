"""The bundle linter (onboarding PR 3b-2; docs/design/ENGINE_ONBOARDING_FORM.md 5.3, 9).

STANDARD LIBRARY ONLY, and no import from this package: the agent's re-verify script (scripts/onboarding/verify_bundle.py) loads this very file by path and runs the
same checks on the proposed content, so the server and the agent can never disagree about what "clean" means.

ADDED LINES ONLY (found when the real tdap README, which already carries its project contact address, blocked every bundle that touched it): `no_email` and
`names_ok` look only at the lines a bundle ADDS OR CHANGES, not at text already in the base file. `bases` maps a path to the file's current text; a file with no
base (an add, or a base that could not be read) is checked whole. A line the bundle changes counts as added, so an address kept in a changed line is still caught.

Four checks, each a separate boolean and each able to fail on its own:
  no_email             no email-shaped string in any line a bundle adds or changes
  no_not_yet_public    no exported item is marked not_yet_public (the private bibliography of PR 4 uses this flag; the check is built now against the item field)
  names_ok             no person's name beyond that owner's consent choice, in any line a bundle adds or changes: an owner who chose "role" (the default) or "none"
                       must not appear by name. A name matches as the FULL name or as the SURNAME alone (the last word, four or more letters), never the first name
                       alone, so "Jordan" in "Jordan curve" cannot block a bundle. Needs the owners' names, which only the server has; the re-verify script can be
                       given names to refuse with --deny-name.
  schema_ok            docs/research_focus.json parses and every active question has q, terms and since, with only the optional id and priority beside them;
                       a docs/seeds.csv parses with a header that has a doi column, every row the header's width, and every row the bundle adds or changes has a doi
                       or an arxiv_id (a row with neither cannot be ingested).

`files` are dicts with a `path` and either `content` or `proposed_content`.
"""
import csv
import io
import json
import re
from collections import Counter
from typing import Any, Dict, Iterable, List, Optional

EMAIL_RE = re.compile(r"[A-Za-z0-9._%+\-]+@[A-Za-z0-9\-]+(?:\.[A-Za-z0-9\-]+)+")
QUESTION_REQUIRED = ("q", "terms", "since")
QUESTION_OPTIONAL = ("id", "priority")
PRIORITIES = ("central", "background")
CHECKS = ("no_email", "no_not_yet_public", "names_ok", "schema_ok")
NO_NAME_CHOICES = ("role", "none")


def _text(f: dict) -> str:
    return f.get("content") if f.get("content") is not None else (f.get("proposed_content") or "")


def added_lines(base: Optional[str], proposed: str) -> List[str]:
    """The lines of `proposed` that are not in `base` (a changed line counts as added). With no base, every line."""
    if base is None:
        return proposed.splitlines()
    have = Counter(base.splitlines())
    out = []
    for line in proposed.splitlines():
        if have[line] > 0:
            have[line] -= 1
        else:
            out.append(line)
    return out


def _new_text(f: dict, bases: Optional[Dict[str, Optional[str]]]) -> str:
    base = (bases or {}).get(f.get("path"))
    return "\n".join(added_lines(base, _text(f)))


def check_no_email(files: Iterable[dict], bases: Optional[Dict[str, Optional[str]]] = None) -> List[str]:
    return [f"{f.get('path')}: an email-shaped string" for f in files if EMAIL_RE.search(_new_text(f, bases))]


def check_no_not_yet_public(items: Iterable[dict]) -> List[str]:
    out = []
    for i in items or []:
        v = i.get("value") if isinstance(i.get("value"), dict) else {}
        if i.get("not_yet_public") is True or v.get("not_yet_public") is True:
            out.append(f"item {i.get('item_id') or i.get('entry_id') or '?'} is marked not yet public")
    return out


def _name_patterns(name: str) -> List["re.Pattern"]:
    """The full name, and the surname alone (the last word of a name of two or more words, letters only, four or more of them). Never the first name alone."""
    name = " ".join((name or "").split())
    if len(name) < 2:
        return []
    pats = [re.compile(r"(?<!\w)" + re.escape(name) + r"(?!\w)", re.I)]
    parts = name.split(" ")
    if len(parts) >= 2 and re.fullmatch(r"(?:[^\W\d_]|['\-])+", parts[-1]) and sum(c.isalpha() for c in parts[-1]) >= 4:
        pats.append(re.compile(r"(?<!\w)" + re.escape(parts[-1]) + r"(?!\w)", re.I))
    return pats


def check_names_ok(files: Iterable[dict], owners: Iterable[dict], bases: Optional[Dict[str, Optional[str]]] = None) -> List[str]:
    """`owners`: [{naming, name}]. Only owners who did NOT choose to be named are searched for, and only in the lines a bundle adds or changes."""
    out = []
    files = list(files)
    for o in owners or []:
        if (o.get("naming") or "role") not in NO_NAME_CHOICES:
            continue
        pats = _name_patterns(o.get("name") or "")
        for f in files:
            if any(p.search(_new_text(f, bases)) for p in pats):
                out.append(f"{f.get('path')}: names an owner who chose not to be named")
    return out


def _check_research_focus(path: str, text: str) -> List[str]:
    try:
        doc = json.loads(text)
    except ValueError as e:
        return [f"{path}: does not parse ({e.__class__.__name__})"]
    if not isinstance(doc, dict):
        return [f"{path}: is not a JSON object"]
    out = []
    qs = doc.get("active_questions", [])
    if not isinstance(qs, list):
        return [f"{path}: active_questions is not a list"]
    for n, q in enumerate(qs):
        if not isinstance(q, dict):
            out.append(f"{path}: question {n} is not an object")
            continue
        for k in QUESTION_REQUIRED:
            if k not in q:
                out.append(f"{path}: question {n} lacks {k}")
        extra = set(q) - set(QUESTION_REQUIRED) - set(QUESTION_OPTIONAL)
        if extra:
            out.append(f"{path}: question {n} has fields outside the contract: {', '.join(sorted(extra))}")
        if "q" in q and not (isinstance(q["q"], str) and q["q"].strip()):
            out.append(f"{path}: question {n} has an empty q")
        if "terms" in q and not (isinstance(q["terms"], list) and all(isinstance(t, str) for t in q["terms"])):
            out.append(f"{path}: question {n} terms is not a list of text")
        if "since" in q and not (isinstance(q["since"], str) and q["since"].strip()):
            out.append(f"{path}: question {n} has an empty since")
        if "priority" in q and q["priority"] not in PRIORITIES:
            out.append(f"{path}: question {n} priority is not central or background")
    for k in ("categories", "horizons", "mute"):
        if k in doc and not (isinstance(doc[k], list) and all(isinstance(t, str) for t in doc[k])):
            out.append(f"{path}: {k} is not a list of text")
    return out


def _check_seeds_csv(path: str, text: str, base: Optional[str] = None) -> List[str]:
    try:
        rows = list(csv.reader(io.StringIO(text)))
    except csv.Error as e:
        return [f"{path}: does not parse ({e.__class__.__name__})"]
    if not rows or not rows[0]:
        return [f"{path}: has no header"]
    header = rows[0]
    out = []
    if "doi" not in header:
        out.append(f"{path}: the header has no doi column")
    if len(set(header)) != len(header):
        out.append(f"{path}: the header repeats a column")
    try:
        old_rows = {tuple(r) for r in list(csv.reader(io.StringIO(base)))[1:]} if base else set()
    except csv.Error:
        old_rows = set()
    ident = [header.index(c) for c in ("doi", "arxiv_id") if c in header]
    for n, r in enumerate(rows[1:], start=2):
        if len(r) != len(header):
            out.append(f"{path}: line {n} has {len(r)} fields, the header {len(header)}")
        elif ident and tuple(r) not in old_rows and not any((r[i] or "").strip() for i in ident):
            out.append(f"{path}: line {n} (added or changed) has neither a doi nor an arxiv_id")
    return out


def check_schema(files: Iterable[dict], bases: Optional[Dict[str, Optional[str]]] = None) -> List[str]:
    out = []
    for f in files:
        if f.get("path") == "docs/research_focus.json":
            out += _check_research_focus(f["path"], _text(f))
        elif f.get("path") == "docs/seeds.csv":
            out += _check_seeds_csv(f["path"], _text(f), (bases or {}).get(f["path"]))
    return out


def run_checks(files: List[dict], owners: Optional[List[dict]] = None, items: Optional[List[dict]] = None, bases: Optional[Dict[str, Optional[str]]] = None) -> Dict[str, Any]:
    """{'checks': {name: bool}, 'problems': {name: [reason, ...]}}. A problem names a file or an item, never the offending text. `bases` maps a path to the file's
    current text (or None): the email and name checks then look only at the lines the bundle adds or changes, and the seeds check only at the rows it adds or changes."""
    problems = {"no_email": check_no_email(files, bases), "no_not_yet_public": check_no_not_yet_public(items or []),
                "names_ok": check_names_ok(files, owners or [], bases), "schema_ok": check_schema(files, bases)}
    return {"checks": {k: not v for k, v in problems.items()}, "problems": {k: v for k, v in problems.items() if v}}
