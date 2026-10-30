"""Result status of an `openai/math` manuscript, read from the pinned commit (curated-sources design §4, reduced C3).

Per MANUSCRIPT, never per family (status varies inside a family). Three statuses are computed here, all from the repository's own files at
the commit, none from a model:

  withdrawn               the manuscript's directory README is a withdrawal notice ("Withdrawal notice: <title>", "Withdrawn on <date>")
  has_lean_formalization  the manuscript's directory is a `sources:` entry of `lean/formalization.yaml`
  unverified              neither (the default)

Precedence: withdrawn, then has_lean_formalization, then unverified. `checked_by_experts` is never computed here: it exists only when a cited
commentary source says so (C4). `history.md` is read as a cross-check: its "Withdrawals" lists give the date the repository's changelog records,
which can differ from the notice's own (they do for the first three withdrawals: October 6 in the notice, October 7 in the changelog).

"Has a Lean formalization" is a catalogue fact. The catalogue's own metadata says `scope: "Partial progress."` and `review.status: unchecked`;
it does not say the Lean file states the paper's theorem. See design §4.

`recheck_items` is the publish-day check: the same computation against the CURRENT head of the repository, compared with what was recorded.
"""
from __future__ import annotations

import json
import re
from typing import Any, Awaitable, Callable, Dict, List, Optional, Set, Tuple
from urllib.parse import quote

import openai_math_index as omi
from safe_fetch import FetchRefused, FetchResult, guarded_get

STATUS_HAS_LEAN, STATUS_UNVERIFIED, STATUS_WITHDRAWN = "has_lean_formalization", "unverified", "withdrawn"
Fetch = Callable[..., Awaitable[FetchResult]]

_NOTICE_HEAD = re.compile(r"^#\s*\[?\s*Withdrawal notice:\s*(.+?)\s*\]?(?:\([^)]*\))?\s*$", re.I | re.M)
_NOTICE_DATE = re.compile(r"Withdrawn on\s+([A-Z][a-z]+ \d{1,2}, \d{4})", re.I)
_NOTICE_REVISION = re.compile(r"Repository revision:\s*`([0-9a-f]{40})`")
_NOTICE_SCOPE = re.compile(r"This withdrawal concerns the proof[^.]*\.[^.]*\.?", re.I)
_LEAN_ID = re.compile(r"^\s*id:\s*\.\./preprints/([^/\n]+)/", re.M)
_HISTORY_DATE = re.compile(r"^##\s+([A-Z][a-z]+ \d{1,2}, \d{4})\s*$", re.M)

_LEAN_CACHE: Dict[str, Set[str]] = {}
_HISTORY_CACHE: Dict[str, List[Dict[str, Any]]] = {}


# --- reading files at a commit ----------------------------------------------------------------------------------------------
async def read_file(commit: str, path: str, fetch: Optional[Fetch] = None) -> Optional[str]:
    """A text file at a commit, or None if it does not exist there. Raises RepoUnavailable on anything else."""
    if not omi.COMMIT_RE.match(commit or ""):
        raise omi.RepoUnavailable("not a full commit id")
    url = f"https://{omi.RAW_HOST}/{omi.REPO}/{commit}/{quote(path, safe='/()')}"
    try:
        res = await (fetch or guarded_get)(url, allowed_hosts=[omi.RAW_HOST])
    except FetchRefused as e:
        raise omi.RepoUnavailable(f"{path} could not be read ({e.reason})")
    except Exception as e:  # noqa: BLE001
        raise omi.RepoUnavailable(f"{path} could not be read ({type(e).__name__})")
    if res.status == 404:
        return None
    if res.status != 200:
        raise omi.RepoUnavailable(f"{path} answered HTTP {res.status}")
    return res.body.decode("utf-8", "replace")


# --- the Lean catalogue ---------------------------------------------------------------------------------------------------------
def parse_lean_sources(text: str) -> Set[str]:
    """Directories named by the `sources:` entries of formalization.yaml (the section before `related_formalizations:`)."""
    head = re.split(r"^related_formalizations:", text or "", maxsplit=1, flags=re.M)[0]
    return {m.group(1) for m in _LEAN_ID.finditer(head)}


async def load_lean_sources(commit: str, fetch: Optional[Fetch] = None, use_cache: bool = True) -> Set[str]:
    if use_cache and commit in _LEAN_CACHE:
        return _LEAN_CACHE[commit]
    text = await read_file(commit, "lean/formalization.yaml", fetch)
    if text is None:
        raise omi.RepoUnavailable("lean/formalization.yaml does not exist at that commit")
    sources = parse_lean_sources(text)
    if not sources:
        raise omi.RepoUnavailable("lean/formalization.yaml had an unexpected format")
    if use_cache:
        _LEAN_CACHE[commit] = sources
    return sources


# --- withdrawal notices ------------------------------------------------------------------------------------------------------------
def parse_notice(readme: Optional[str]) -> Optional[Dict[str, Any]]:
    """The withdrawal notice a manuscript README contains, or None. Only a README that STARTS as a notice counts."""
    if not readme:
        return None
    first = readme.lstrip().splitlines()[0] if readme.strip() else ""
    m = _NOTICE_HEAD.match(first.strip())
    if not m:
        return None
    body = readme.split("\n", 1)[1] if "\n" in readme else ""
    date = _NOTICE_DATE.search(body)
    paragraphs = [p.strip() for p in re.split(r"\n\s*\n", body) if p.strip()]
    explanation = next((p for p in paragraphs if not p.startswith(("OpenAI", "**Withdrawn")) and not p.startswith("#")), "")
    rev = _NOTICE_REVISION.search(body)
    scope = _NOTICE_SCOPE.search(body)
    return {"title": m.group(1).strip(), "withdrawn_on": date.group(1) if date else None, "explanation": re.sub(r"\s+", " ", explanation)[:700],
            "archived_revision": rev.group(1) if rev else None, "scope": re.sub(r"\s+", " ", scope.group(0)).strip() if scope else None}


def _norm(t: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", (t or "").lower()).strip()


def parse_history(text: str) -> List[Dict[str, Any]]:
    """[{date, titles}] for every 'Withdrawals' list in history.md."""
    out: List[Dict[str, Any]] = []
    sections = list(_HISTORY_DATE.finditer(text or ""))
    for i, m in enumerate(sections):
        block = text[m.end(): sections[i + 1].start() if i + 1 < len(sections) else len(text)]
        w = re.search(r"\*\*Withdrawals?\*\*(.*?)(?=\n\*\*|\Z)", block, re.S)
        if not w:
            continue
        titles = [re.sub(r"^[*_]+|[*_]+$", "", l.strip()[2:].strip()).strip() for l in w.group(1).splitlines() if l.strip().startswith("- ")]
        if titles:
            out.append({"date": m.group(1), "titles": titles})
    return out


async def load_history(commit: str, fetch: Optional[Fetch] = None, use_cache: bool = True) -> List[Dict[str, Any]]:
    if use_cache and commit in _HISTORY_CACHE:
        return _HISTORY_CACHE[commit]
    text = await read_file(commit, "history.md", fetch)
    parsed = parse_history(text or "")
    if use_cache:
        _HISTORY_CACHE[commit] = parsed
    return parsed


def history_dates_for(title: str, history: List[Dict[str, Any]]) -> List[str]:
    return [h["date"] for h in history if any(_norm(t) == _norm(title) for t in h["titles"])]


# --- the status of one manuscript ---------------------------------------------------------------------------------------------------
async def compute_status(commit: str, dirname: str, fetch: Optional[Fetch] = None, use_cache: bool = True) -> Dict[str, Any]:
    """{status, basis} for the manuscript in `preprints/<dirname>` at `commit`."""
    readme = await read_file(commit, f"preprints/{dirname}/README.md", fetch)
    notice = parse_notice(readme)
    lean = await load_lean_sources(commit, fetch, use_cache)
    history = await load_history(commit, fetch, use_cache)
    basis: Dict[str, Any] = {"commit": commit, "lean_catalogue_entries": len(lean), "in_lean_catalogue": dirname in lean,
                             "readme_present": readme is not None, "withdrawal_notice": bool(notice)}
    if notice:
        basis["withdrawal"] = {**notice, "history_dates": history_dates_for(notice["title"], history)}
        return {"status": STATUS_WITHDRAWN, "basis": basis}
    return {"status": STATUS_HAS_LEAN if dirname in lean else STATUS_UNVERIFIED, "basis": basis}


async def withdrawn_manuscript(commit: str, dirname: str, fetch: Optional[Fetch] = None) -> Tuple[Optional[Dict[str, Any]], Optional[omi.Refusal]]:
    """A manuscript that is NOT in the map but whose README is a withdrawal notice: its confirmation, so the series can tell the story of a
    withdrawal. Anything else outside the map (an older edition, a name that does not exist) is refused."""
    url = f"https://{omi.API_HOST}/repos/{omi.REPO}/git/trees/{commit}:preprints%2F{quote(dirname, safe='')}"
    try:
        res = await (fetch or guarded_get)(url, allowed_hosts=[omi.API_HOST], extra_headers={"Accept": "application/vnd.github+json"})
    except FetchRefused as e:
        raise omi.RepoUnavailable(f"the repository could not be read ({e.reason})")
    except Exception as e:  # noqa: BLE001
        raise omi.RepoUnavailable(f"the repository could not be read ({type(e).__name__})")
    if res.status == 404:
        return None, omi.Refusal("not_a_standing_manuscript", "not in the manuscript map, and no such directory at the pinned commit")
    if res.status != 200:
        raise omi.RepoUnavailable(f"the repository answered HTTP {res.status}")
    try:
        entries = {e["path"]: e for e in (json.loads(res.body.decode("utf-8", "replace")).get("tree") or [])}
    except (ValueError, KeyError, TypeError, AttributeError):
        raise omi.RepoUnavailable("the repository gave an unexpected answer")
    readme = await read_file(commit, f"preprints/{dirname}/README.md", fetch)
    notice = parse_notice(readme)
    if not notice:
        return None, omi.Refusal("not_a_standing_manuscript", "not in the manuscript map and not a withdrawn manuscript "
                                 "(an older edition or a superseded version)")
    pdfs = sorted(p for p, e in entries.items() if p.lower().endswith(".pdf") and e.get("type") == "blob")
    history = await load_history(commit, fetch)
    year = omi.Manuscript("", "", dirname, "", "", "").year
    explanation = notice["explanation"] or notice["title"]
    return {
        "status": "confirmed", "source_class": "company_release", "registry": "openai_math", "repo": omi.REPO, "commit": commit, "family": None,
        "family_title": None, "path": f"preprints/{dirname}", "file": pdfs[0] if pdfs else None, "blob_sha": (entries.get(pdfs[0]) or {}).get("sha") if pdfs else None,
        "readme_blob_sha": (entries.get("README.md") or {}).get("sha"), "title": notice["title"],
        "abstract": f"Withdrawn by OpenAI on {notice['withdrawn_on'] or 'an unrecorded date'}. {explanation}", "authors": ["OpenAI"], "year": year,
        "withdrawal": {**notice, "history_dates": history_dates_for(notice["title"], history)},
        "url": f"https://github.com/{omi.REPO}/tree/{commit}/preprints/{quote(dirname)}", "confirmed_at": omi._now(),
    }, None


# --- the publish-day re-check -----------------------------------------------------------------------------------------------------------
async def resolve_head(fetch: Optional[Fetch] = None) -> str:
    """The commit id at the head of the repository's default branch."""
    async def get_json(url):
        try:
            res = await (fetch or guarded_get)(url, allowed_hosts=[omi.API_HOST], extra_headers={"Accept": "application/vnd.github+json"})
        except (FetchRefused, OSError) as e:
            raise omi.RepoUnavailable(f"the repository could not be read ({type(e).__name__})")
        if res.status != 200:
            raise omi.RepoUnavailable(f"the repository answered HTTP {res.status}")
        return json.loads(res.body.decode("utf-8", "replace"))
    branch = (await get_json(f"https://{omi.API_HOST}/repos/{omi.REPO}")).get("default_branch")
    if not branch:
        raise omi.RepoUnavailable("the repository did not name a default branch")
    sha = (await get_json(f"https://{omi.API_HOST}/repos/{omi.REPO}/commits/{quote(branch, safe='')}")).get("sha")
    if not sha or not omi.COMMIT_RE.match(sha):
        raise omi.RepoUnavailable("the repository did not give a commit id")
    return sha


async def recheck_items(items: List[Dict[str, Any]], head: str, fetch: Optional[Fetch] = None) -> List[Dict[str, Any]]:
    """For every company-release item: its status at `head` against the status recorded in the list. One row per item:
    {item_id, title, path, recorded, current, changed (bool), notes}. A manuscript whose mapped file changed since the pin is flagged too."""
    rows = []
    index = await omi.load_index(head, fetch=fetch, use_cache=False)
    for it in items:
        if it.get("class") != "company_release":
            continue
        c = it.get("confirmation") or {}
        dirname = (c.get("path") or "").split("preprints/", 1)[-1]
        recorded = it.get("result_status") or STATUS_UNVERIFIED
        notes: List[str] = []
        try:
            cur = await compute_status(head, dirname, fetch, use_cache=False)
            current = cur["status"]
        except omi.RepoUnavailable as e:
            current, notes = "unreadable", [str(e)]
        in_map = dirname in index.by_dir
        if current != "unreadable":
            if recorded == STATUS_WITHDRAWN and in_map:
                notes.append("recorded as withdrawn but now back in the manuscript map")
            if recorded != STATUS_WITHDRAWN and not in_map and current != STATUS_WITHDRAWN:
                notes.append("no longer in the manuscript map at the head (superseded or removed)")
                current = "not_standing"
            ms = index.by_dir.get(dirname)
            if ms is not None and c.get("file"):
                tree = await omi.confirm_manuscript(ms, head, fetch=fetch)
                if tree[0] and tree[0].get("blob_sha") and c.get("blob_sha") and tree[0]["blob_sha"] != c["blob_sha"]:
                    notes.append("the manuscript file has changed since the pinned commit")
        rows.append({"item_id": it.get("item_id"), "title": it.get("title"), "path": c.get("path"), "recorded": recorded, "current": current,
                     "changed": current != recorded or bool(notes), "notes": notes})
    return rows
