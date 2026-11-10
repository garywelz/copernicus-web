"""Third-party lookups for the onboarding form (PR 4b-1; docs/design/ENGINE_ONBOARDING_FORM.md 2.4, 5.5).

THE SERVER, never the browser, asks four public scholarly registries about a paper: Crossref, OpenAlex, arXiv and Semantic Scholar. Nothing else is ever
contacted: every URL is built here from one of four fixed hosts, redirects are not followed, and NO CREDENTIAL and no address is sent (the User-Agent is a
generic client name). A PubMed id is resolved through OpenAlex and then Semantic Scholar; NCBI is not called (decided by Gary, 2026-11-10).

LIMITS: each call has a timeout (TIMEOUT_SECONDS), one lookup has a total budget (TOTAL_BUDGET_SECONDS), and at most MAX_BYTES of any answer is read; a longer
answer is treated as no answer. The per-person and per-engine rate limits and the consent check are in the route (endpoints/onboarding/routes.py): this
module is never reached for a person who has not agreed to lookups.

THREE OUTCOMES, never two. `found`: a registry returned a record. `not_found`: every registry that was asked answered, and none has it. `unavailable`: a
registry timed out, refused, rate-limited, answered too much or answered something unreadable, and no other one had the paper. An empty result is an
instrument question first (governance/ENGINE_ONBOARDING.md section 6), so `not_found` is worded "not found in <registries> just now" and says outright that this
does not mean the paper does not exist; the page never says that a paper does not exist.

RESULTS ARE SUGGESTIONS WITH PROVENANCE: each record says which registry each of its fields came from. Text from a registry is stored and shown as plain
text (tags and control characters removed, lengths capped).

CACHE: a `found` result is kept for CACHE_HOURS in `onboarding_lookup_cache`, keyed by a hash of the normalised query (the query itself is not stored). Only
public registry data is cached. `not_found` and `unavailable` are never cached, so a registry's bad minute is not remembered. A cache failure is a miss.
"""
import hashlib
import html
import json
import re
import time
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta, timezone
from typing import Any, Callable, Dict, List, Optional, Tuple
from urllib.parse import quote, urlencode

import requests

from utils import onboarding_ids as ids

HOSTS = {"crossref": "https://api.crossref.org", "openalex": "https://api.openalex.org", "arxiv": "https://export.arxiv.org", "s2": "https://api.semanticscholar.org"}
NAMES = {"crossref": "Crossref", "openalex": "OpenAlex", "arxiv": "arXiv", "s2": "Semantic Scholar"}
USER_AGENT = "onboarding-lookup/1.0"         # a generic client name: no address, no project, no person
TIMEOUT_SECONDS = 8
TOTAL_BUDGET_SECONDS = 15
MAX_BYTES = 512_000
CACHE = "onboarding_lookup_cache"
CACHE_HOURS = 24
TITLE_RESULTS = 5
TITLE_CAP, ABSTRACT_CAP, AUTHOR_CAP, AUTHORS_MAX = 600, 5000, 120, 20
S2_FIELDS = "title,year,authors,abstract,externalIds"
_TAG = re.compile(r"<[^>]{0,200}>")
_CONTROL = re.compile(r"[\x00-\x1f\x7f]")


def _http_get(url: str, timeout: float) -> Tuple[int, bytes]:
    """The only network call. Tests replace it. No credential, no redirect; reads at most MAX_BYTES + 1."""
    r = requests.get(url, headers={"User-Agent": USER_AGENT, "Accept": "application/json, application/atom+xml;q=0.9"}, timeout=timeout, stream=True, allow_redirects=False)
    try:
        return r.status_code, r.raw.read(MAX_BYTES + 1, decode_content=True)
    finally:
        r.close()


def _url(registry: str, path: str, params: Optional[Dict[str, str]] = None) -> str:
    return HOSTS[registry] + path + ("?" + urlencode(params) if params else "")


def _call(registry: str, path: str, params: Optional[Dict[str, str]], deadline: float) -> Tuple[str, Optional[bytes]]:
    """('ok', body) | ('not_found', None) | ('unavailable', None). Anything but a plain 200 or 404 inside the limits is `unavailable`."""
    left = deadline - time.monotonic()
    if left <= 0:
        return "unavailable", None
    try:
        status, body = _http_get(_url(registry, path, params), min(TIMEOUT_SECONDS, max(1.0, left)))
    except Exception:                                            # noqa: BLE001 - a timeout, a refused connection, a DNS failure: all "unavailable"
        return "unavailable", None
    if status == 404:
        return "not_found", None
    if status != 200 or body is None or len(body) > MAX_BYTES:
        return "unavailable", None
    return "ok", body


# ---- registry text is plain text ----------------------------------------------------------------------------------------------------------------------
def _text(value: Any, cap: int) -> str:
    if not isinstance(value, str):
        return ""
    return " ".join(_CONTROL.sub(" ", html.unescape(_TAG.sub(" ", value))).split())[:cap]


def _year(value: Any) -> Optional[int]:
    try:
        y = int(str(value)[:4])
    except (TypeError, ValueError):
        return None
    return y if 1000 <= y <= 2200 else None


def _record(registry: str, title: Any, authors: List[Any], year: Any, abstract: Any, found: Dict[str, Optional[str]]) -> Optional[Dict[str, Any]]:
    """One registry's record in the form's shape, or None when it has no title (a record without a title cannot be confirmed by a person)."""
    title = _text(title, TITLE_CAP)
    if not title:
        return None
    authors = [a for a in (_text(x, AUTHOR_CAP) for x in authors[:AUTHORS_MAX]) if a]
    year, abstract = _year(year), _text(abstract, ABSTRACT_CAP)
    return {"title": title, "authors": authors, "year": year, "abstract": abstract, "identifiers": {k: v for k, v in found.items() if v},
            "sources": {"title": registry, "authors": registry if authors else None, "year": registry if year else None, "abstract": registry if abstract else None}}


def _crossref_record(m: Any) -> Optional[Dict[str, Any]]:
    if not isinstance(m, dict):
        return None
    authors = [f"{a.get('given') or ''} {a.get('family') or ''}".strip() or (a.get("name") or "") for a in (m.get("author") or []) if isinstance(a, dict)]
    parts = (((m.get("issued") or {}).get("date-parts") or [[None]])[0] or [None])
    return _record("crossref", ((m.get("title") or [""]) or [""])[0], authors, parts[0], m.get("abstract"), {"doi": ids.normalise_identifier("doi", m.get("DOI"))})


def parse_crossref(body: bytes) -> Optional[Dict[str, Any]]:
    return _crossref_record((json.loads(body.decode("utf-8")) or {}).get("message"))


def parse_crossref_list(body: bytes) -> List[Dict[str, Any]]:
    items = (((json.loads(body.decode("utf-8")) or {}).get("message") or {}).get("items")) or []
    return [r for r in (_crossref_record(m) for m in items[:TITLE_RESULTS]) if r]


def _openalex_abstract(index: Any) -> str:
    if not isinstance(index, dict):
        return ""
    words: Dict[int, str] = {}
    for word, places in index.items():
        if isinstance(word, str) and isinstance(places, list):
            for p in places[:50]:
                if isinstance(p, int) and 0 <= p < 3000:
                    words[p] = word
    return " ".join(words[p] for p in sorted(words))


def _openalex_record(w: Any) -> Optional[Dict[str, Any]]:
    if not isinstance(w, dict):
        return None
    authors = [((a.get("author") or {}).get("display_name") or "") for a in (w.get("authorships") or []) if isinstance(a, dict)]
    known = w.get("ids") if isinstance(w.get("ids"), dict) else {}
    return _record("openalex", w.get("title") or w.get("display_name"), authors, w.get("publication_year"), _openalex_abstract(w.get("abstract_inverted_index")),
                   {"doi": ids.normalise_identifier("doi", w.get("doi") or known.get("doi")), "pmid": ids.normalise_identifier("pmid", known.get("pmid"))})


def parse_openalex(body: bytes) -> Optional[Dict[str, Any]]:
    return _openalex_record(json.loads(body.decode("utf-8")))


def parse_openalex_list(body: bytes) -> List[Dict[str, Any]]:
    items = ((json.loads(body.decode("utf-8")) or {}).get("results")) or []
    return [r for r in (_openalex_record(w) for w in items[:TITLE_RESULTS]) if r]


def parse_arxiv(body: bytes) -> Optional[Dict[str, Any]]:
    if b"<!DOCTYPE" in body or b"<!ENTITY" in body:              # an Atom feed declares neither; refuse rather than expand anything
        raise ValueError("unexpected XML declaration")
    ns = {"a": "http://www.w3.org/2005/Atom", "x": "http://arxiv.org/schemas/atom"}
    for e in ET.fromstring(body).findall("a:entry", ns):
        m = re.search(r"arxiv\.org/abs/(.+?)(?:v\d+)?$", (e.findtext("a:id", "", ns) or "").strip())
        title = e.findtext("a:title", "", ns) or ""
        if not m or title.strip().lower().startswith("error"):
            continue
        return _record("arxiv", title, [n.text or "" for n in e.findall("a:author/a:name", ns)], e.findtext("a:published", "", ns), e.findtext("a:summary", "", ns),
                       {"arxiv": ids.normalise_identifier("arxiv", m.group(1)), "doi": ids.normalise_identifier("doi", e.findtext("x:doi", "", ns))})
    return None


def parse_s2(body: bytes) -> Optional[Dict[str, Any]]:
    p = json.loads(body.decode("utf-8"))
    if not isinstance(p, dict):
        return None
    ext = p.get("externalIds") if isinstance(p.get("externalIds"), dict) else {}
    return _record("s2", p.get("title"), [(a.get("name") or "") for a in (p.get("authors") or []) if isinstance(a, dict)], p.get("year"), p.get("abstract"),
                   {"doi": ids.normalise_identifier("doi", ext.get("DOI")), "arxiv": ids.normalise_identifier("arxiv", ext.get("ArXiv")),
                    "pmid": ids.normalise_identifier("pmid", str(ext.get("PubMed") or ""))})


def _merge(a: Optional[Dict[str, Any]], b: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    """`a` with its empty fields filled from `b` (the same paper, asked for by the same identifier). Each field keeps the registry it came from."""
    if a is None or b is None:
        return a or b
    out = {**a, "identifiers": {**b["identifiers"], **a["identifiers"]}, "sources": dict(a["sources"])}
    for field in ("authors", "year", "abstract"):
        if not a[field] and b[field]:
            out[field], out["sources"][field] = b[field], b["sources"][field]
    return out


# ---- asking -------------------------------------------------------------------------------------------------------------------------------------------
class _Asker:
    def __init__(self, deadline: float):
        self.deadline, self.checked = deadline, []

    def ask(self, registry: str, path: str, parser: Callable, params: Optional[Dict[str, str]] = None):
        state, body = _call(registry, path, params, self.deadline)
        got = None
        if state == "ok":
            try:
                got = parser(body)
            except Exception:                                    # noqa: BLE001 - an answer that cannot be read is the registry's problem, not the paper's
                state = "unavailable"
            else:
                state = "found" if got else "not_found"
        self.checked.append({"registry": registry, "name": NAMES[registry], "state": state})
        return got or None

    def state(self, found: bool) -> str:
        if found:
            return "found"
        return "not_found" if self.checked and all(c["state"] == "not_found" for c in self.checked) else "unavailable"


def _by_identifier(kind: str, value: str, asker: _Asker) -> Optional[Dict[str, Any]]:
    if kind == "doi":
        rec = asker.ask("crossref", "/works/" + quote(value, safe=""), parse_crossref)
        if rec is None or not rec["abstract"]:
            rec = _merge(rec, asker.ask("openalex", "/works/doi:" + quote(value, safe="/"), parse_openalex))
        if rec is None or not rec["abstract"]:
            rec = _merge(rec, asker.ask("s2", "/graph/v1/paper/DOI:" + quote(value, safe="/"), parse_s2, {"fields": S2_FIELDS}))
    elif kind == "arxiv":
        rec = asker.ask("arxiv", "/api/query", parse_arxiv, {"id_list": value, "max_results": "1"})
    else:                                                        # pmid: OpenAlex, then Semantic Scholar. NCBI is not called.
        rec = asker.ask("openalex", "/works/pmid:" + quote(value, safe=""), parse_openalex)
        if rec is None or not rec["abstract"]:
            rec = _merge(rec, asker.ask("s2", "/graph/v1/paper/PMID:" + quote(value, safe=""), parse_s2, {"fields": S2_FIELDS}))
    if rec is not None:
        rec["identifiers"][kind] = f"{kind}:{value}"             # the identifier that was asked for is the one the record answers to
    return rec


def _by_title(title: str, asker: _Asker) -> List[Dict[str, Any]]:
    """Up to TITLE_RESULTS possible matches, each with a DOI (a paper with no public identifier cannot be a seed). A person picks one; nothing is picked for them."""
    out: List[Dict[str, Any]] = []
    for registry, path, parser, params in (("crossref", "/works", parse_crossref_list, {"query.bibliographic": title, "rows": str(TITLE_RESULTS), "select": "DOI,title,author,issued,abstract"}),
                                           ("openalex", "/works", parse_openalex_list, {"search": title, "per-page": str(TITLE_RESULTS)})):
        for rec in asker.ask(registry, path, parser, params) or []:
            doi = rec["identifiers"].get("doi")
            if doi and all(doi != r["identifiers"].get("doi") for r in out):
                out.append(rec)
    return out[:TITLE_RESULTS]


def message(state: str, checked: List[Dict[str, str]]) -> str:
    if state == "found":
        return ""
    if state == "not_found":
        return (f"Not found in {_names(checked)} just now. This does not mean the paper does not exist: please check what you entered, try its DOI or arXiv id, "
                "or try again later.")
    down = [c for c in checked if c["state"] == "unavailable"] or checked
    return (f"The lookup could not be completed just now ({_names(down)} did not give a usable answer). This says nothing about the paper. Please try again in a "
            "few minutes.")


def _names(checked: List[Dict[str, str]]) -> str:
    names = [c["name"] for c in checked] or ["the registries"]
    return names[0] if len(names) == 1 else ", ".join(names[:-1]) + " and " + names[-1]


def _path_safe(value: str) -> bool:
    return not any(seg in (".", "..") for seg in value.split("/")) and "\\" not in value


# ---- the cache ----------------------------------------------------------------------------------------------------------------------------------------
def cache_key(kind: str, value: str) -> str:
    return hashlib.sha256(f"{kind}\n{value.casefold()}".encode("utf-8")).hexdigest()


def _cache_get(db, key: str, now: datetime) -> Optional[Dict[str, Any]]:
    try:
        snap = db.collection(CACHE).document(key).get()
        doc = snap.to_dict() if snap.exists else None
        if doc and datetime.fromisoformat(doc["fetched_at"]) > now - timedelta(hours=CACHE_HOURS) and doc.get("result", {}).get("state") == "found":
            return doc["result"]
    except Exception:                                            # noqa: BLE001 - a cache that cannot be read is a miss
        pass
    return None


def _cache_put(db, key: str, result: Dict[str, Any], now: datetime) -> None:
    try:
        db.collection(CACHE).document(key).set({"query_sha256": key, "result": result, "fetched_at": now.isoformat()})
    except Exception:                                            # noqa: BLE001
        pass


def lookup(db, kind: str, value: str, now: Optional[datetime] = None) -> Dict[str, Any]:
    """Resolve one query. `kind` and `value` come from onboarding_ids.classify: ('doi' | 'arxiv' | 'pmid', 'kind:identifier') or ('title', text).
    Returns {state, results: [record], checked: [{registry, name, state}], message, fetched_at, cached}. Never raises for anything a registry does."""
    now = now or datetime.now(timezone.utc)
    bare = value.split(":", 1)[1] if kind != "title" else value
    if kind not in ("doi", "arxiv", "pmid", "title") or (kind != "title" and not _path_safe(bare)):
        raise ValueError("not a query the lookup accepts")
    key = cache_key(kind, bare)
    hit = _cache_get(db, key, now) if db is not None else None
    if hit:
        return {**hit, "cached": True}
    asker = _Asker(time.monotonic() + TOTAL_BUDGET_SECONDS)
    if kind == "title":
        results = _by_title(bare, asker)
    else:
        rec = _by_identifier(kind, bare, asker)
        results = [rec] if rec else []
    state = asker.state(bool(results))
    result = {"state": state, "results": results, "checked": asker.checked, "message": message(state, asker.checked), "fetched_at": now.isoformat()}
    if state == "found" and db is not None:
        _cache_put(db, key, result, now)
    return {**result, "cached": False}
