"""Confirm that candidate papers exist, by identifier, in their registry (arXiv, PubMed, Crossref).

Design: governance/ARCHITECTURE_REVIEW_2026-10-01/phase2_gap3_fix1_extended_design.md, step A (3.1).

Only identifiers that came from a registry record (never from a model) are used. A candidate becomes a
ConfirmedPaper only if its registry record exists, matches the retrieved title, and has an abstract. Titles,
authors, year, venue and abstract on a ConfirmedPaper always come from the registry record, never from the
search result, and for arXiv they belong to the cited version (a later version may be retitled).

Nothing here calls a model. Network access goes through an injectable ``http_get`` so tests run offline.
"""
from __future__ import annotations

import asyncio
import re
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from typing import Any, Awaitable, Callable, Dict, List, Optional, Sequence, Tuple

MAX_PAPERS = 12
TITLE_MATCH_MIN = 0.6
HTTP_TIMEOUT_S = 15
HTTP_RETRIES = 2  # retries after the first attempt

ARXIV_API = "http://export.arxiv.org/api/query"
EUTILS = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/"
CROSSREF = "https://api.crossref.org/works/"

# http_get(url, params) -> (status_code, body_text)
HttpGet = Callable[[str, Dict[str, str]], Awaitable[Tuple[int, str]]]


class RegistryUnavailable(Exception):
    """A registry could not be reached after retries. Distinct from 'too few confirmed papers'."""

    def __init__(self, registries: Sequence[str]):
        self.registries = sorted(set(registries))
        super().__init__(
            "Could not reach the paper registries (" + ", ".join(self.registries) + ") to confirm the research papers, "
            "so no episode was generated. This is usually temporary; please try again later.")


class PaperNotConfirmed(Exception):
    """A paper that must be confirmed (a directly requested paper) could not be."""


class InsufficientConfirmedPapers(Exception):
    """Fewer confirmed papers than the minimum. The message says how many were found, confirmed and dropped, and why."""

    def __init__(self, topic: str, found: int, confirmed: int, needed: int, drop_counts: Dict[str, int], dropped: Optional[List[Dict[str, Any]]] = None):
        self.topic, self.found, self.confirmed, self.needed, self.drop_counts = topic, found, confirmed, needed, dict(drop_counts)
        self.dropped = list(dropped or [])  # the dropped candidates with their identifiers and reasons, for the job record
        why = ", ".join(f"{n} {r.replace('_', ' ')}" for r, n in sorted(drop_counts.items())) or "none"
        super().__init__(
            f"Not enough confirmed research papers for '{topic}': {found} candidate sources were found, {confirmed} were confirmed "
            f"against PubMed, arXiv or Crossref, and at least {needed} are needed. Dropped candidates: {why}. "
            "No episode was generated or published.")


@dataclass
class ConfirmedPaper:
    pid: str
    title: str
    authors: List[str]
    year: Optional[int]
    venue: Optional[str]
    ids: Dict[str, Optional[str]]  # arxiv, arxiv_version, pmid, doi
    url: str
    abstract: str
    registry: str
    confirmed_at: str
    title_match: float

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class Dropped:
    title: str
    reason: str  # no_identifier | not_found | identifier_mismatch | no_abstract | duplicate | over_limit
    ids: Dict[str, Optional[str]] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class ConfirmationResult:
    confirmed: List[ConfirmedPaper]
    dropped: List[Dropped]

    def drop_counts(self) -> Dict[str, int]:
        out: Dict[str, int] = {}
        for d in self.dropped:
            out[d.reason] = out.get(d.reason, 0) + 1
        return out


# ---------------------------------------------------------------- identifiers
_ARXIV_URL = re.compile(r"arxiv\.org/(?:abs|pdf)/(\d{4}\.\d{4,5})(v\d+)?", re.I)
_ARXIV_DOI = re.compile(r"^10\.48550/arxiv\.(\d{4}\.\d{4,5})(v\d+)?$", re.I)
_PMID_URL = re.compile(r"(?:pubmed\.ncbi\.nlm\.nih\.gov/|ncbi\.nlm\.nih\.gov/pubmed/)(\d{5,9})", re.I)
_DOI = re.compile(r"\b(10\.\d{4,9}/[^\s\"'<>\]\[,;]+)", re.I)


def normalize_doi(doi: Optional[str]) -> Optional[str]:
    if not doi:
        return None
    d = doi.strip()
    d = re.sub(r"^(?:https?://(?:dx\.)?doi\.org/|doi:\s*)", "", d, flags=re.I)
    d = d.rstrip(".,;)")
    return d.lower() if d.startswith("10.") else None


def ids_from_fields(url: Optional[str], doi: Optional[str]) -> Dict[str, Optional[str]]:
    """Identifiers from a search record's own url and doi fields. Only registry-given fields are read."""
    ids: Dict[str, Optional[str]] = {"arxiv": None, "arxiv_version": None, "pmid": None, "doi": None}
    u = url or ""
    m = _ARXIV_URL.search(u)
    if m:
        ids["arxiv"], ids["arxiv_version"] = m.group(1), (m.group(2) or None)
    m = _PMID_URL.search(u)
    if m:
        ids["pmid"] = m.group(1)
    d = normalize_doi(doi)
    if not d and u:
        mu = re.search(r"doi\.org/(10\.[^\s?#]+)", u, re.I)
        d = normalize_doi(mu.group(1)) if mu else None
    if d:
        ma = _ARXIV_DOI.match(d)
        if ma and not ids["arxiv"]:
            ids["arxiv"], ids["arxiv_version"] = ma.group(1), (ma.group(2) or None)
        elif not ma:
            ids["doi"] = d
    return ids


def discover_identifiers_in_page(url: str, text: str) -> Dict[str, Optional[str]]:
    """Find identifiers for a user-supplied link without a model: the URL itself first, then standard page
    metadata (citation_doi, citation_pmid, dc.identifier), then a bare DOI in the page. Returns ids (maybe empty)."""
    ids = ids_from_fields(url, None)
    if any(ids.values()):
        return ids
    t = text or ""
    for meta in (r'name=["\']citation_doi["\']\s+content=["\']([^"\']+)',
                 r'content=["\']([^"\']+)["\']\s+name=["\']citation_doi["\']',
                 r'name=["\']dc\.identifier["\']\s+content=["\'](?:doi:)?([^"\']+)',
                 r'name=["\']citation_arxiv_id["\']\s+content=["\']([^"\']+)'):
        m = re.search(meta, t, re.I)
        if m:
            cand = m.group(1).strip()
            if re.match(r"^\d{4}\.\d{4,5}(v\d+)?$", cand):
                ids["arxiv"] = cand.split("v")[0]
                ids["arxiv_version"] = ("v" + cand.split("v")[1]) if "v" in cand else None
                return ids
            r = ids_from_fields(None, cand)
            if any(r.values()):
                return r
    m = re.search(r'name=["\']citation_pmid["\']\s+content=["\'](\d{5,9})', t, re.I)
    if m:
        ids["pmid"] = m.group(1)
        return ids
    m = _DOI.search(t)
    if m:
        return ids_from_fields(None, m.group(1))
    return ids


# ---------------------------------------------------------------- matching
def _words(s: str) -> set:
    return set(re.findall(r"[a-z0-9]{3,}", (s or "").lower()))


def title_match(a: str, b: str) -> float:
    """Jaccard overlap of the words (3+ characters) of two titles."""
    wa, wb = _words(a), _words(b)
    if not wa or not wb:
        return 0.0
    return len(wa & wb) / len(wa | wb)


def _year(s: Optional[str]) -> Optional[int]:
    m = re.match(r"\s*(\d{4})", s or "")
    return int(m.group(1)) if m else None


# ---------------------------------------------------------------- registry lookups
async def _default_http_get(url: str, params: Dict[str, str]) -> Tuple[int, str]:
    import aiohttp  # imported lazily so unit tests need no network stack
    timeout = aiohttp.ClientTimeout(total=HTTP_TIMEOUT_S)
    async with aiohttp.ClientSession(timeout=timeout, headers={"User-Agent": "copernicus-podcast-api/paper-confirmation"}) as s:
        async with s.get(url, params=params) as r:
            return r.status, await r.text()


async def _get(http_get: HttpGet, url: str, params: Dict[str, str], registry: str, bad: List[str]) -> Optional[str]:
    """GET with retries. Returns the body, or None for a definite 404; records the registry in ``bad`` if unreachable."""
    last = None
    for attempt in range(HTTP_RETRIES + 1):
        try:
            status, body = await http_get(url, params)
            if status == 200:
                return body
            if status == 404:
                return None
            last = f"HTTP {status}"
        except Exception as e:  # network error, timeout
            last = type(e).__name__
        # arXiv asks for about 3 seconds between requests and answers 429 when it is exceeded: wait longer for that
        await asyncio.sleep(0 if attempt == HTTP_RETRIES else (3.0 if last == "HTTP 429" else 0.5) * (attempt + 1))
    bad.append(registry)
    return None


def _clean(s: Optional[str]) -> str:
    return re.sub(r"\s+", " ", s or "").strip()


def parse_arxiv(xml: str) -> Dict[str, Dict[str, Any]]:
    """Atom feed -> {'2603.28944v1': record}. Keys are 'id' + version as returned by the registry."""
    out: Dict[str, Dict[str, Any]] = {}
    ns = {"a": "http://www.w3.org/2005/Atom"}
    root = ET.fromstring(xml)
    for e in root.findall("a:entry", ns):
        idel = e.find("a:id", ns)
        titel = e.find("a:title", ns)
        if idel is None or titel is None:
            continue
        m = _ARXIV_URL.search(idel.text or "")
        if not m or "Error" in (titel.text or "")[:8]:
            continue
        key = m.group(1) + (m.group(2) or "")
        summ = e.find("a:summary", ns)
        pub = e.find("a:published", ns)
        out[key] = {
            "title": _clean(titel.text), "abstract": _clean(summ.text if summ is not None else ""),
            "authors": [_clean(n.text) for n in e.findall("a:author/a:name", ns)],
            "year": _year(pub.text if pub is not None else None), "venue": None,
            "ids": {"arxiv": m.group(1), "arxiv_version": m.group(2) or None, "pmid": None, "doi": None},
            "url": f"https://arxiv.org/abs/{key}",
        }
    return out


def parse_pubmed(xml: str) -> Dict[str, Dict[str, Any]]:
    """efetch XML -> {pmid: record}."""
    out: Dict[str, Dict[str, Any]] = {}
    root = ET.fromstring(xml)
    for art in root.findall(".//PubmedArticle"):
        pm = art.find(".//MedlineCitation/PMID")
        if pm is None or not pm.text:
            continue
        t = art.find(".//ArticleTitle")
        title = _clean("".join(t.itertext())) if t is not None else ""
        abstract = _clean(" ".join("".join(a.itertext()) for a in art.findall(".//Abstract/AbstractText")))
        authors = []
        for au in art.findall(".//AuthorList/Author"):
            ln, fn = au.find("LastName"), au.find("ForeName")
            if ln is not None and ln.text:
                authors.append(_clean(f"{fn.text if fn is not None and fn.text else ''} {ln.text}"))
        year = None
        y = art.find(".//JournalIssue/PubDate/Year")
        if y is not None and y.text:
            year = _year(y.text)
        else:
            md = art.find(".//JournalIssue/PubDate/MedlineDate")
            year = _year(md.text if md is not None else None)
        j = art.find(".//Journal/Title")
        doi_el = art.find(".//ArticleIdList/ArticleId[@IdType='doi']")
        pmid = pm.text.strip()
        out[pmid] = {
            "title": title, "abstract": abstract, "authors": authors, "year": year,
            "venue": _clean(j.text) if j is not None and j.text else None,
            "ids": {"arxiv": None, "arxiv_version": None, "pmid": pmid, "doi": normalize_doi(doi_el.text) if doi_el is not None else None},
            "url": f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/",
        }
    return out


def parse_crossref(body: str, doi: str) -> Optional[Dict[str, Any]]:
    import json
    m = (json.loads(body) or {}).get("message") or {}
    titles = m.get("title") or []
    if not titles:
        return None
    issued = ((m.get("issued") or {}).get("date-parts") or [[None]])[0]
    authors = [_clean(f"{a.get('given', '')} {a.get('family', '')}") for a in (m.get("author") or []) if a.get("family") or a.get("name")]
    abstract = _clean(re.sub(r"<[^>]+>", " ", m.get("abstract") or ""))
    return {
        "title": _clean(titles[0]), "abstract": abstract, "authors": authors,
        "year": issued[0] if issued and isinstance(issued[0], int) else None,
        "venue": _clean((m.get("container-title") or [None])[0]) or None,
        "ids": {"arxiv": None, "arxiv_version": None, "pmid": None, "doi": normalize_doi(m.get("DOI")) or doi},
        "url": f"https://doi.org/{doi}",
    }


async def fetch_arxiv(items: List[Tuple[str, Optional[str]]], http_get: HttpGet, bad: List[str]) -> Dict[str, Dict[str, Any]]:
    """One batched request for all arXiv ids; a version is requested when the source gave one."""
    if not items:
        return {}
    id_list = ",".join(i + (v or "") for i, v in items)
    body = await _get(http_get, ARXIV_API, {"id_list": id_list, "max_results": str(len(items))}, "arxiv", bad)
    return parse_arxiv(body) if body else {}


async def fetch_pubmed(pmids: List[str], http_get: HttpGet, bad: List[str]) -> Dict[str, Dict[str, Any]]:
    if not pmids:
        return {}
    body = await _get(http_get, EUTILS + "efetch.fcgi", {"db": "pubmed", "id": ",".join(pmids), "retmode": "xml"}, "pubmed", bad)
    return parse_pubmed(body) if body else {}


async def fetch_crossref(doi: str, http_get: HttpGet, bad: List[str]) -> Optional[Dict[str, Any]]:
    body = await _get(http_get, CROSSREF + doi, {}, "crossref", bad)
    return parse_crossref(body, doi) if body else None


async def _pubmed_by_doi(doi: str, http_get: HttpGet, bad: List[str]) -> Optional[Dict[str, Any]]:
    body = await _get(http_get, EUTILS + "esearch.fcgi", {"db": "pubmed", "term": f"{doi}[AID]", "retmode": "json"}, "pubmed", bad)
    if not body:
        return None
    import json
    ids = ((json.loads(body) or {}).get("esearchresult") or {}).get("idlist") or []
    if not ids:
        return None
    recs = await fetch_pubmed([ids[0]], http_get, bad)
    return recs.get(ids[0])


# ---------------------------------------------------------------- confirmation
def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _dedupe_key(ids: Dict[str, Optional[str]]) -> List[str]:
    keys = []
    if ids.get("arxiv"):
        keys.append("arxiv:" + ids["arxiv"])
    if ids.get("pmid"):
        keys.append("pmid:" + ids["pmid"])
    if ids.get("doi"):
        keys.append("doi:" + ids["doi"])
    return keys


async def confirm_sources(sources: Sequence[Any], http_get: Optional[HttpGet] = None, max_papers: int = MAX_PAPERS,
                          required_first: Optional["ConfirmedPaper"] = None) -> ConfirmationResult:
    """Confirm ranked ResearchSource-like objects (need .title, .url, .doi, .publication_date).

    Returns ConfirmationResult; raises RegistryUnavailable if any registry could not be reached after retries.
    Order follows the input (rank) order; P numbers are assigned in that order, up to ``max_papers``.
    ``required_first`` (an already confirmed, directly requested paper) becomes P1 and any duplicate of it is dropped.
    """
    http_get = http_get or _default_http_get
    bad: List[str] = []
    dropped: List[Dropped] = []
    cands: List[Dict[str, Any]] = []
    for s in sources:
        ids = ids_from_fields(getattr(s, "url", None), getattr(s, "doi", None))
        if not any(ids.values()):
            dropped.append(Dropped(getattr(s, "title", "") or "", "no_identifier", ids))
            continue
        cands.append({"src": s, "ids": ids})

    # batched lookups
    ax_items, seen_ax = [], set()
    pm_ids, seen_pm = [], set()
    for c in cands:
        i = c["ids"]
        if i["arxiv"]:
            k = (i["arxiv"], i["arxiv_version"])
            if k not in seen_ax:
                seen_ax.add(k); ax_items.append(k)
        elif i["pmid"] and i["pmid"] not in seen_pm:
            seen_pm.add(i["pmid"]); pm_ids.append(i["pmid"])
    ax_task = fetch_arxiv(ax_items, http_get, bad)
    pm_task = fetch_pubmed(pm_ids, http_get, bad)
    sem = asyncio.Semaphore(4)

    async def one_doi(doi: str):
        async with sem:
            return doi, await fetch_crossref(doi, http_get, bad)

    dois = sorted({c["ids"]["doi"] for c in cands if not c["ids"]["arxiv"] and not c["ids"]["pmid"] and c["ids"]["doi"]})
    ax, pm, cr = await asyncio.gather(ax_task, pm_task, asyncio.gather(*[one_doi(d) for d in dois]))
    crd = dict(cr)

    confirmed: List[ConfirmedPaper] = []
    seen_keys: set = set()
    if required_first is not None:
        required_first = ConfirmedPaper(**{**asdict(required_first), "pid": "P1"})
        confirmed.append(required_first)
        seen_keys.update(_dedupe_key(required_first.ids))
    for c in cands:
        s, ids = c["src"], c["ids"]
        title = getattr(s, "title", "") or ""
        rec, registry = None, None
        if ids["arxiv"]:
            key = ids["arxiv"] + (ids["arxiv_version"] or "")
            rec = ax.get(key) or next((r for k, r in ax.items() if k.startswith(ids["arxiv"])), None)
            registry = "arxiv"
        elif ids["pmid"]:
            rec, registry = pm.get(ids["pmid"]), "pubmed"
        elif ids["doi"]:
            rec, registry = crd.get(ids["doi"]), "crossref"
            if rec is not None and not rec["abstract"]:
                alt = await _pubmed_by_doi(ids["doi"], http_get, bad)
                if alt is not None and alt["abstract"]:
                    rec, registry = alt, "pubmed"
        if rec is None:
            if not bad:
                dropped.append(Dropped(title, "not_found", ids))
            continue
        tm = title_match(title, rec["title"]) if title else 1.0
        sy, ry = _year(getattr(s, "publication_date", None)), rec.get("year")
        if (title and tm < TITLE_MATCH_MIN) or (sy and ry and abs(sy - ry) > 1):
            dropped.append(Dropped(title, "identifier_mismatch", ids))
            continue
        if not rec["abstract"]:
            dropped.append(Dropped(title, "no_abstract", ids))
            continue
        merged = {k: (rec["ids"].get(k) or ids.get(k)) for k in ("arxiv", "arxiv_version", "pmid", "doi")}
        keys = _dedupe_key(merged)
        if any(k in seen_keys for k in keys):
            dropped.append(Dropped(title, "duplicate", merged))
            continue
        if len(confirmed) >= max_papers:
            dropped.append(Dropped(title, "over_limit", merged))
            continue
        seen_keys.update(keys)
        confirmed.append(ConfirmedPaper(
            pid=f"P{len(confirmed) + 1}", title=rec["title"], authors=rec["authors"], year=rec["year"], venue=rec["venue"],
            ids=merged, url=rec["url"], abstract=rec["abstract"], registry=registry, confirmed_at=_now(), title_match=round(tm, 2)))
    if bad:
        raise RegistryUnavailable(bad)
    return ConfirmationResult(confirmed=confirmed, dropped=dropped)


async def confirm_requested_paper(doi: Optional[str], title: str, http_get: Optional[HttpGet] = None) -> ConfirmedPaper:
    """A directly requested paper must itself be confirmed by its DOI (or arXiv/PubMed id found in the DOI field).

    Raises PaperNotConfirmed with a message that says what failed; RegistryUnavailable if a registry is down."""
    ids = ids_from_fields(None, doi)
    if not any(ids.values()):
        raise PaperNotConfirmed("the requested paper has no usable DOI, arXiv id or PubMed id, so it cannot be confirmed")

    class _S:  # minimal source-like object
        pass
    s = _S()
    s.title, s.url, s.doi, s.publication_date = title, "", doi, None
    res = await confirm_sources([s], http_get=http_get, max_papers=1)
    if not res.confirmed:
        reason = res.dropped[0].reason if res.dropped else "not_found"
        raise PaperNotConfirmed(f"the requested paper could not be confirmed ({reason})")
    return res.confirmed[0]


def as_research_source(c: ConfirmedPaper):
    """A ResearchSource carrying a confirmed paper's registry fields and its P number, for the rest of the pipeline."""
    from research_pipeline import ResearchSource  # lazy: keeps this module importable on its own
    return ResearchSource(
        title=c.title, authors=list(c.authors), abstract=c.abstract, url=c.url, publication_date=str(c.year or ""),
        source=c.registry, doi=c.ids.get("doi"), journal=c.venue, pid=c.pid,
    )


def format_citation_line(c: ConfirmedPaper) -> str:
    """One reference line built by code from registry fields only: authors (year). Title. Venue. identifier."""
    authors = c.authors
    names = ", ".join(authors[:3]) + (" et al." if len(authors) > 3 else "")
    parts = [f"{names} ({c.year})." if names and c.year else f"{names}." if names else (f"({c.year})." if c.year else "")]
    parts.append(c.title.rstrip(".") + ".")
    if c.venue:
        parts.append(c.venue.rstrip(".") + ".")
    if c.ids.get("arxiv"):
        parts.append(f"arXiv:{c.ids['arxiv']}{c.ids.get('arxiv_version') or ''}.")
    if c.ids.get("pmid"):
        parts.append(f"PMID {c.ids['pmid']}.")
    if c.ids.get("doi"):
        parts.append(f"DOI: {c.ids['doi']}.")
    parts.append(c.url)
    return " ".join(p for p in parts if p)
