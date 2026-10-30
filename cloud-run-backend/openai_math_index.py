"""Company-release confirmation for the `openai/math` repository, at a pinned commit (curated-sources design §3.4).

The repository's own manuscript map (`CONTENTS.md`) at the pinned commit is the source of truth for which manuscripts are *standing*,
what each is called, which family it belongs to and what its abstract says. A manuscript is confirmed only if (1) it is in that map,
(2) its directory and file exist at that commit (checked with the git tree listing, which also yields the blob ids recorded as the
pin), and (3) it is named unambiguously. Nothing is taken from a model. Only this one repository is supported.

An older edition or a withdrawn manuscript is not in the map and is refused here as a source for a standing claim; how withdrawn
manuscripts are used as content (design §4.2) belongs to the result-status work (C3).
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Awaitable, Callable, Dict, List, Optional, Tuple
from urllib.parse import quote, unquote, urlsplit

from safe_fetch import FetchRefused, FetchResult, guarded_get

REPO = "openai/math"
DEFAULT_COMMIT = "7ef5c0cc5ca4b0e072b7a050fca09ab24bc6fa3a"
RAW_HOST = "raw.githubusercontent.com"
API_HOST = "api.github.com"
COMMIT_RE = re.compile(r"^[0-9a-f]{40}$")
MONTHS = ("January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December")
_DIR_DATE = re.compile(r"-(" + "|".join(MONTHS) + r")-(\d{1,2})-(\d{4})$")

Fetch = Callable[..., Awaitable[FetchResult]]


class RepoUnavailable(Exception):
    """The repository could not be read (network, rate limit, or an unexpected answer). Distinct from a refusal: try again later."""


@dataclass
class Manuscript:
    family: str
    family_title: str
    dir: str
    file: str
    title: str
    abstract: str
    note: str = ""   # text after the link on the same line in the map, for example "secondary writeup"

    @property
    def stem(self) -> str:
        return _DIR_DATE.sub("", self.dir)

    @property
    def year(self) -> Optional[int]:
        m = _DIR_DATE.search(self.dir)
        return int(m.group(3)) if m else None


@dataclass
class Family:
    number: str
    title: str
    description: str
    manuscripts: List[Manuscript] = field(default_factory=list)


@dataclass
class Index:
    commit: str
    families: Dict[str, Family]
    by_dir: Dict[str, Manuscript]


@dataclass
class Refusal:
    reason: str            # a short stable code
    detail: str = ""
    directories: Optional[List[str]] = None


# --- parsing the map ----------------------------------------------------------------------------------------------
_FAMILY = re.compile(r"^\*\*(\d{3})\. (.*?)\*\* ?(.*)$", re.M)
# A directory name can contain parentheses (".../Sharp-integral-fillings-in-CAT(0)-spaces-..."), and a link can be followed by a note on
# the same line ("... .pdf) - secondary writeup").
_MANUSCRIPT = re.compile(r"^&emsp;\[(.*?)\]\(preprints/([^/\n]+)/([^\n]+?)\)([^\n]*)\n\s*\n(.*?)\n\s*\n", re.M | re.S)
_TAGS = re.compile(r"<[^>]+>")


def _clean(s: str) -> str:
    return re.sub(r"\s+", " ", _TAGS.sub("", s or "")).strip()


def parse_contents(text: str, commit: str) -> Index:
    """Parse `CONTENTS.md`: numbered families, each followed by its manuscripts (title link, then the abstract paragraph)."""
    events: List[Tuple[int, str, Any]] = []
    for m in _FAMILY.finditer(text):
        events.append((m.start(), "family", m))
    for m in _MANUSCRIPT.finditer(text):
        events.append((m.start(), "manuscript", m))
    events.sort(key=lambda e: e[0])
    families: Dict[str, Family] = {}
    by_dir: Dict[str, Manuscript] = {}
    current: Optional[Family] = None
    for _pos, kind, m in events:
        if kind == "family":
            current = Family(number=m.group(1), title=_clean(m.group(2)).rstrip("."), description=_clean(m.group(3)))
            families[current.number] = current
        elif current is not None:
            ms = Manuscript(family=current.number, family_title=current.title, dir=unquote(m.group(2)), file=unquote(m.group(3)),
                            title=_clean(m.group(1)), abstract=_clean(m.group(5)), note=re.sub(r"^[^A-Za-z0-9]+", "", _clean(m.group(4))))
            current.manuscripts.append(ms)
            by_dir[ms.dir] = ms
    return Index(commit=commit, families=families, by_dir=by_dir)


_INDEX_CACHE: Dict[str, Index] = {}


async def load_index(commit: str, fetch: Optional[Fetch] = None, use_cache: bool = True) -> Index:
    """The manuscript map at `commit`, fetched once from raw.githubusercontent.com and cached for the life of the process."""
    if not COMMIT_RE.match(commit or ""):
        raise RepoUnavailable("the pinned commit is not a 40-character commit id")
    if use_cache and commit in _INDEX_CACHE:
        return _INDEX_CACHE[commit]
    url = f"https://{RAW_HOST}/{REPO}/{commit}/CONTENTS.md"
    try:
        res = await (fetch or guarded_get)(url, allowed_hosts=[RAW_HOST])
    except FetchRefused as e:
        raise RepoUnavailable(f"the repository map could not be fetched ({e.reason})")
    except Exception as e:
        raise RepoUnavailable(f"the repository map could not be fetched ({type(e).__name__})")
    if res.status != 200:
        raise RepoUnavailable(f"the repository map answered HTTP {res.status}")
    index = parse_contents(res.body.decode("utf-8", "replace"), commit)
    if not index.families or not index.by_dir:
        raise RepoUnavailable("the repository map had an unexpected format")
    if use_cache:
        _INDEX_CACHE[commit] = index
    return index


# --- naming a manuscript --------------------------------------------------------------------------------------------
_FAMILY_REF = re.compile(r"^(?:openai/math[:\s]+)?family[\s:#]*(\d{3})$", re.I)
_REPO_PATH = re.compile(r"preprints/([^/?#\s]+)")


def is_repo_reference(raw: str) -> bool:
    """True if the text names something in this repository (a family, a preprints path, or a github.com/openai/math address)."""
    s = (raw or "").strip()
    if _FAMILY_REF.match(s):
        return True
    low = s.lower()
    return "github.com/openai/math" in low or "raw.githubusercontent.com/openai/math" in low or bool(re.match(r"^preprints/[^/\s]+/?$", s))


def parse_reference(raw: str) -> Tuple[str, str]:
    """('family', '378') or ('path', directory) from what Gary typed; raises ValueError for a repository address that names neither."""
    s = (raw or "").strip()
    m = _FAMILY_REF.match(s)
    if m:
        return "family", m.group(1)
    low = s.lower()
    if low.startswith(("http://", "https://")):
        host = (urlsplit(s).hostname or "").lower()
        path = urlsplit(s).path
        if host not in ("github.com", "www.github.com", RAW_HOST) or not re.match(r"^/openai/math(/|$)", path, re.I):
            raise ValueError("not_this_repository")
    p = _REPO_PATH.search(s)
    if p:
        return "path", unquote(p.group(1))
    raise ValueError("no_manuscript_named")


def _norm_title(t: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", (t or "").lower()).strip()


def ambiguous_groups(family: Family) -> List[List[Manuscript]]:
    """Manuscripts in a family that a bare family number cannot tell apart: same map title, or same directory name apart from the date."""
    groups: Dict[Tuple[str, str], List[Manuscript]] = {}
    for m in family.manuscripts:
        groups.setdefault(("title", _norm_title(m.title)), []).append(m)
        groups.setdefault(("stem", m.stem.lower()), []).append(m)
    return [g for g in groups.values() if len(g) > 1]


def resolve(index: Index, kind: str, value: str) -> Tuple[List[Manuscript], Optional[Refusal]]:
    """The manuscripts a reference names at the pinned map, or why it names none."""
    if kind == "family":
        fam = index.families.get(value)
        if fam is None:
            return [], Refusal("unknown_family", value)
        bad = ambiguous_groups(fam)
        if bad:
            dirs = sorted({m.dir for g in bad for m in g})
            return [], Refusal("ambiguous_family", "name the manuscript by its directory", directories=dirs)
        return list(fam.manuscripts), None
    ms = index.by_dir.get(value)
    if ms is None:
        return [], Refusal("not_a_standing_manuscript", "not in the repository's manuscript map at the pinned commit "
                           "(an older edition, a withdrawn manuscript, or not a manuscript)")
    return [ms], None


# --- confirming a manuscript exists at the commit --------------------------------------------------------------------------
def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


async def confirm_manuscript(ms: Manuscript, commit: str, fetch: Optional[Fetch] = None) -> Tuple[Optional[Dict[str, Any]], Optional[Refusal]]:
    """Check that the directory and the mapped file exist at `commit` (git tree listing) and record their blob ids.

    Returns (confirmation, None) or (None, Refusal). Raises RepoUnavailable when the repository cannot be read."""
    url = f"https://{API_HOST}/repos/{REPO}/git/trees/{commit}:preprints%2F{quote(ms.dir, safe='')}"
    try:
        res = await (fetch or guarded_get)(url, allowed_hosts=[API_HOST], extra_headers={"Accept": "application/vnd.github+json"})
    except FetchRefused as e:
        raise RepoUnavailable(f"the repository could not be read ({e.reason})")
    except Exception as e:
        raise RepoUnavailable(f"the repository could not be read ({type(e).__name__})")
    if res.status == 404:
        return None, Refusal("file_missing_at_commit", f"preprints/{ms.dir} does not exist at the pinned commit")
    if res.status != 200:
        raise RepoUnavailable(f"the repository answered HTTP {res.status}")
    try:
        entries = {e["path"]: e for e in (json.loads(res.body.decode("utf-8", "replace")).get("tree") or [])}
    except (ValueError, KeyError, TypeError, AttributeError):
        raise RepoUnavailable("the repository gave an unexpected answer")
    entry = entries.get(ms.file)
    if not entry or entry.get("type") != "blob" or not entry.get("sha"):
        return None, Refusal("file_missing_at_commit", f"preprints/{ms.dir}/{ms.file} does not exist at the pinned commit")
    readme = entries.get("README.md") or {}
    return {
        "status": "confirmed",
        "source_class": "company_release",
        "registry": "openai_math",
        "repo": REPO, "commit": commit, "family": ms.family, "family_title": ms.family_title,
        "path": f"preprints/{ms.dir}", "file": ms.file, "blob_sha": entry["sha"], "readme_blob_sha": readme.get("sha"),
        "title": ms.title, "abstract": ms.abstract, "authors": ["OpenAI"], "year": ms.year, "map_note": ms.note or None,
        "url": f"https://github.com/{REPO}/tree/{commit}/preprints/{quote(ms.dir)}",
        "confirmed_at": _now(),
    }, None
