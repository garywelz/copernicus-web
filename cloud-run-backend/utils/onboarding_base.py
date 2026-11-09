"""The current state of an engine's repository, for the proposed-vs-current diff (onboarding PR 3b-1; docs/design/ENGINE_ONBOARDING_FORM.md 5.1, 5.2, 6.3).

NO CREDENTIAL, ANYWHERE: files come from https://raw.githubusercontent.com by a plain GET and the base commit from the unauthenticated GitHub commits endpoint. The
repository name comes from the engine record and is checked against a strict pattern before it goes into a URL; the path is one of the renderer's fixed paths.

EVERY FAILURE DEGRADES, NEVER RAISES: a fetch that fails, times out, is too large or answers with anything but the file is reported as `unavailable` (the dashboard
says "current file unavailable"), and a file the repository does not have is `missing` (shown as an add). Results are cached in memory for a short time per
repository, so a reviewer paging through sections does not re-fetch; failures are not cached.

The files are fetched AT THE BASE COMMIT when the commit lookup worked (so the file and the commit shown are the same state even if `main` moves between the two
requests), and from `main` when it did not.
"""
import difflib
import re
import threading
import time
from typing import Any, Dict, List, Optional, Tuple

import requests

RAW_HOST = "https://raw.githubusercontent.com"
COMMITS_URL = "https://api.github.com/repos/{repo}/commits/main"
REPO_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,38}/[A-Za-z0-9._-]{1,100}$")
SHA_RE = re.compile(r"^[0-9a-f]{40}$")
TIMEOUT_SECONDS = 8
MAX_BYTES = 1_000_000
CACHE_SECONDS = 60
CACHE_MAX = 64
MAX_DIFF_LINES = 1500

_cache: Dict[Tuple, Tuple[float, Any]] = {}
_lock = threading.Lock()


def _http_get(url: str, headers: Optional[dict] = None) -> Tuple[int, bytes]:
    """The only network call. Tests replace it. Never sends a credential; reads at most MAX_BYTES + 1."""
    r = requests.get(url, headers={"User-Agent": "copernicus-onboarding-review", **(headers or {})}, timeout=TIMEOUT_SECONDS, stream=True, allow_redirects=False)
    try:
        return r.status_code, r.raw.read(MAX_BYTES + 1, decode_content=True)
    finally:
        r.close()


def clear_cache() -> None:
    with _lock:
        _cache.clear()


def _cached(key: Tuple, now: float, make):
    with _lock:
        hit = _cache.get(key)
        if hit and now - hit[0] < CACHE_SECONDS:
            return hit[1]
    value, cacheable = make()
    if cacheable:
        with _lock:
            if len(_cache) >= CACHE_MAX:
                _cache.pop(min(_cache, key=lambda k: _cache[k][0]), None)
            _cache[key] = (now, value)
    return value


def engine_repo(engine: dict) -> Optional[str]:
    """The engine's repository as 'owner/name', or None when it has none (or the stored value is not a plausible name)."""
    repo = ((engine.get("source") or {}).get("repo") if isinstance(engine.get("source"), dict) else None) or engine.get("repo")
    return repo if isinstance(repo, str) and REPO_RE.match(repo) and ".." not in repo else None


def base_commit(repo: str, now: Optional[float] = None) -> Optional[str]:
    """The tip of the repository's main, or None if it could not be learned."""
    def make():
        try:
            status, body = _http_get(COMMITS_URL.format(repo=repo), {"Accept": "application/vnd.github+json"})
            if status != 200 or len(body) > MAX_BYTES:
                return None, False
            import json
            sha = (json.loads(body.decode("utf-8")) or {}).get("sha")
            return (sha, True) if isinstance(sha, str) and SHA_RE.match(sha) else (None, False)
        except Exception:                                        # noqa: BLE001 - any failure is "unavailable"
            return None, False
    return _cached(("commit", repo), time.time() if now is None else now, make)


def fetch_file(repo: str, path: str, ref: str, now: Optional[float] = None) -> Tuple[str, Optional[str]]:
    """('ok', text) | ('missing', None) | ('unavailable', None)."""
    def make():
        try:
            status, body = _http_get(f"{RAW_HOST}/{repo}/{ref}/{path}")
            if status == 404:
                return ("missing", None), True
            if status != 200 or len(body) > MAX_BYTES:
                return ("unavailable", None), False
            return ("ok", body.decode("utf-8").replace("\r\n", "\n")), True
        except Exception:                                        # noqa: BLE001
            return ("unavailable", None), False
    return _cached(("file", repo, ref, path), time.time() if now is None else now, make)


def fetch_bases(engine: dict, paths: List[str], now: Optional[float] = None) -> Dict[str, Any]:
    """{'repo', 'commit_sha', 'commit_state', 'no_repo', 'files': {path: (state, text)}}. `state` is 'ok', 'missing', 'unavailable' or 'none' (no repository)."""
    repo = engine_repo(engine)
    if not repo:
        return {"repo": None, "commit_sha": None, "commit_state": "none", "no_repo": True, "files": {p: ("none", None) for p in paths}}
    sha = base_commit(repo, now)
    ref = sha or "main"
    return {"repo": repo, "commit_sha": sha, "commit_state": "ok" if sha else "unavailable", "no_repo": False,
            "files": {p: fetch_file(repo, p, ref, now) for p in paths}}


def unified(base_text: Optional[str], proposed: str) -> Dict[str, Any]:
    """A unified diff as typed lines ({'t': '+' | '-' | ' ' | '@', 'text'}), capped at MAX_DIFF_LINES. Text only: the page shows each line with textContent."""
    a = (base_text or "").split("\n") if base_text else []
    b = proposed.split("\n")
    if a and a[-1] == "":
        a.pop()
    if b and b[-1] == "":
        b.pop()
    lines: List[Dict[str, str]] = []
    added = removed = 0
    for row in difflib.unified_diff(a, b, lineterm="", n=3):
        if row.startswith(("---", "+++")):
            continue
        t = row[0] if row[0] in "+- " else "@"
        added += t == "+"
        removed += t == "-"
        lines.append({"t": t, "text": row if t == "@" else row[1:]})
    return {"lines": lines[:MAX_DIFF_LINES], "truncated": len(lines) > MAX_DIFF_LINES, "added": added, "removed": removed}


def plain_lines(proposed: str) -> Dict[str, Any]:
    """Every line of a file as an add (no repository, a new file, or a current file that could not be read)."""
    body = proposed.split("\n")
    if body and body[-1] == "":
        body.pop()
    return {"lines": [{"t": "+", "text": s} for s in body[:MAX_DIFF_LINES]], "truncated": len(body) > MAX_DIFF_LINES, "added": len(body), "removed": 0}
