"""The bundle linter (onboarding PR 3b-2; docs/design/ENGINE_ONBOARDING_FORM.md 5.3, 9).

STANDARD LIBRARY ONLY, and no import from this package: the agent's re-verify script (scripts/onboarding/verify_bundle.py) loads this very file by path and runs the
same checks on the proposed content, so the server and the agent can never disagree about what "clean" means.

Four checks, each a separate boolean and each able to fail on its own:
  no_email             no email-shaped string in any proposed file
  no_not_yet_public    no exported item is marked not_yet_public (the private bibliography of PR 4 uses this flag; the check is built now against the item field)
  names_ok             no person's name beyond that owner's consent choice: an owner who chose "role" (the default) or "none" must not appear by name in any file.
                       A name matches as a whole, or as any word of four or more letters from it (so a first name alone is caught). Needs the owners' names, which
                       only the server has; the re-verify script can be given names to refuse with --deny-name.
  schema_ok            docs/research_focus.json parses and every active question has q, terms and since, with only the optional id and priority beside them;
                       a docs/seeds.csv parses with a header that has a doi column and every row the header's width.

`files` are dicts with a `path` and either `content` or `proposed_content`.
"""
import csv
import io
import json
import re
from typing import Any, Dict, Iterable, List, Optional

EMAIL_RE = re.compile(r"[A-Za-z0-9._%+\-]+@[A-Za-z0-9\-]+(?:\.[A-Za-z0-9\-]+)+")
QUESTION_REQUIRED = ("q", "terms", "since")
QUESTION_OPTIONAL = ("id", "priority")
PRIORITIES = ("central", "background")
CHECKS = ("no_email", "no_not_yet_public", "names_ok", "schema_ok")
NO_NAME_CHOICES = ("role", "none")


def _text(f: dict) -> str:
    return f.get("content") if f.get("content") is not None else (f.get("proposed_content") or "")


def check_no_email(files: Iterable[dict]) -> List[str]:
    return [f"{f.get('path')}: an email-shaped string" for f in files if EMAIL_RE.search(_text(f))]


def check_no_not_yet_public(items: Iterable[dict]) -> List[str]:
    out = []
    for i in items or []:
        v = i.get("value") if isinstance(i.get("value"), dict) else {}
        if i.get("not_yet_public") is True or v.get("not_yet_public") is True:
            out.append(f"item {i.get('item_id') or i.get('entry_id') or '?'} is marked not yet public")
    return out


def _name_patterns(name: str) -> List["re.Pattern"]:
    name = (name or "").strip()
    if len(name) < 2:
        return []
    words = [w for w in re.split(r"[^A-Za-zÀ-ɏ]+", name) if len(w) >= 4]
    return [re.compile(r"(?<!\w)" + re.escape(name) + r"(?!\w)", re.I)] + [re.compile(r"(?<!\w)" + re.escape(w) + r"(?!\w)", re.I) for w in words]


def check_names_ok(files: Iterable[dict], owners: Iterable[dict]) -> List[str]:
    """`owners`: [{naming, name}]. Only owners who did NOT choose to be named are searched for."""
    out = []
    files = list(files)
    for o in owners or []:
        if (o.get("naming") or "role") not in NO_NAME_CHOICES:
            continue
        pats = _name_patterns(o.get("name") or "")
        for f in files:
            if any(p.search(_text(f)) for p in pats):
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


def _check_seeds_csv(path: str, text: str) -> List[str]:
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
    for n, r in enumerate(rows[1:], start=2):
        if len(r) != len(header):
            out.append(f"{path}: line {n} has {len(r)} fields, the header {len(header)}")
    return out


def check_schema(files: Iterable[dict]) -> List[str]:
    out = []
    for f in files:
        if f.get("path") == "docs/research_focus.json":
            out += _check_research_focus(f["path"], _text(f))
        elif f.get("path") == "docs/seeds.csv":
            out += _check_seeds_csv(f["path"], _text(f))
    return out


def run_checks(files: List[dict], owners: Optional[List[dict]] = None, items: Optional[List[dict]] = None) -> Dict[str, Any]:
    """{'checks': {name: bool}, 'problems': {name: [reason, ...]}}. A problem names a file or an item, never the offending text."""
    problems = {"no_email": check_no_email(files), "no_not_yet_public": check_no_not_yet_public(items or []),
                "names_ok": check_names_ok(files, owners or []), "schema_ok": check_schema(files)}
    return {"checks": {k: not v for k, v in problems.items()}, "problems": {k: v for k, v in problems.items() if v}}
