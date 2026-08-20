"""
Paper resolver for the Knowledge Engine -> podcast connector.

Given a query -- a DOI/PMID/arXiv link or bare identifier, a title, or a
free-text description -- finds the matching paper(s) in the `research_papers`
Firestore collection, optionally scoped to a GLMP or ATAP project.

Two resolution paths:

1. Identifier match (DOI/PMID/arXiv). Exact Firestore field lookup, no
   ranking or ambiguity involved. Preferred whenever the caller has an
   actual link -- which is what a paper's title link in the Knowledge
   Engine already resolves to (see lib/knowledge-engine-links.ts's
   paperExternalUrl(): papers have no internal KE detail page, only the
   external doi.org/pubmed/arxiv URL).

2. Free-text match (title or description). Semantic search via the
   existing vector-search service, filtered client-side on
   `citations[].cited_project`.

   Known limitation, accepted for v1 rather than built around: cited_project
   is not a flat, Firestore-queryable field -- it lives inside a citations[]
   array of individual citation events, so it can't be used in a `.where()`
   filter directly. This path can therefore only see whichever papers the
   broad similarity search already returned within `limit`; a real GLMP/ATAP
   match ranked outside that window won't surface. This is the same failure
   mode `question_scope_ids` was built to fix for question-level scoping
   (see mcp_server/tools/vector_search.py's `search_semantic(question=...)`
   path and its comment on GLMP_MASTER_TODO.md item 53) -- reuse that
   pattern (a flat `cited_project` mirror field, queryable directly) if this
   limitation turns out to matter in practice. For now: search broadly
   (`limit` defaults high, not the API's usual default of 20) and document
   the gap rather than hide it. The identifier path above has no such
   limitation and is the one to prefer whenever a real link is available.
"""

import re
import json
from typing import Optional, List, Dict, Any
from urllib.parse import quote

DOI_URL_RE = re.compile(r"^https?://(dx\.)?doi\.org/(.+)$", re.IGNORECASE)
DOI_BARE_RE = re.compile(r"^10\.\d{4,9}/\S+$")
PMID_URL_RE = re.compile(r"^https?://pubmed\.ncbi\.nlm\.nih\.gov/(\d+)/?", re.IGNORECASE)
PMID_BARE_RE = re.compile(r"^\d{4,9}$")
ARXIV_URL_RE = re.compile(r"^https?://arxiv\.org/abs/([\w.\-/]+)$", re.IGNORECASE)
ARXIV_BARE_RE = re.compile(r"^\d{4}\.\d{4,5}(v\d+)?$")

VALID_PROJECTS = {"glmp", "atap"}

DEFAULT_TEXT_SEARCH_LIMIT = 60  # generous on purpose -- see module docstring

# PodcastRequest.category labels (CustomRequestForm / CATEGORY_SLUG_TO_LABEL).
_DISCIPLINE_TO_CATEGORY = {
    "biology": "Biology",
    "bio": "Biology",
    "chemistry": "Chemistry",
    "chem": "Chemistry",
    "physics": "Physics",
    "phys": "Physics",
    "mathematics": "Mathematics",
    "math": "Mathematics",
    "computer_science": "Computer Science",
    "computer science": "Computer Science",
    "compsci": "Computer Science",
    "engineering": "Engineering",
    "medicine": "Medicine",
}


def _firestore_db():
    """Lazy so unit tests can import this module without a live Firestore client."""
    from config.database import db
    return db


def _normalize_doi(raw: str) -> str:
    """Same normalization as ingest_papers_from_metadata_json.py's
    _normalize_doi -- must match how DOIs are stored, or lookups silently
    miss real matches. Crossref (the researcher-cited-intake path) already
    returns DOIs lowercase, so both known ingestion paths agree on this."""
    d = raw.strip().lower()
    d = re.sub(r"^(doi:|https?://(dx\.)?doi\.org/)", "", d).strip()
    return d


def parse_identifier(query: str) -> Optional[Dict[str, str]]:
    """Detect whether `query` is a DOI/PMID/arXiv link or bare identifier.
    Returns a single-entry dict ({"doi": ...} / {"pmid": ...} /
    {"arxiv_id": ...}) or None if it looks like a title/description instead."""
    q = query.strip()
    if not q:
        return None

    m = DOI_URL_RE.match(q)
    if m:
        return {"doi": _normalize_doi(m.group(2))}
    if DOI_BARE_RE.match(q):
        return {"doi": _normalize_doi(q)}

    m = PMID_URL_RE.match(q)
    if m:
        return {"pmid": m.group(1)}
    if PMID_BARE_RE.match(q):
        return {"pmid": q}

    m = ARXIV_URL_RE.match(q)
    if m:
        return {"arxiv_id": m.group(1)}
    if ARXIV_BARE_RE.match(q):
        return {"arxiv_id": q}

    return None


def paper_year_text(paper: Dict[str, Any]) -> Optional[str]:
    """Four-digit publication year from KE paper fields, or None."""
    y = str(paper.get("year") or "").strip()
    if re.fullmatch(r"\d{4}", y):
        return y
    for key in ("published_date", "publication_date"):
        m = re.match(r"(\d{4})", str(paper.get(key) or ""))
        if m:
            return m.group(1)
    return None


def paper_abstract_text(paper: Dict[str, Any]) -> str:
    """Stripped abstract, or empty string if missing. Generation requires this
    to be non-empty -- KE papers typically store title+abstract, not full text,
    and an empty abstract would otherwise fall through to the topic-research path."""
    return str(paper.get("abstract") or "").strip()


def paper_external_url(paper: Dict[str, Any]) -> Optional[str]:
    """Same priority as lib/knowledge-engine-links.ts paperExternalUrl():
    doi.org, then PubMed, then arXiv, then an http(s) `url` field."""
    doi = _normalize_doi(str(paper.get("doi") or ""))
    if doi:
        return f"https://doi.org/{quote(doi, safe='/')}"
    pmid = str(paper.get("pmid") or "").strip()
    if pmid:
        return f"https://pubmed.ncbi.nlm.nih.gov/{quote(pmid, safe='')}"
    arxiv_id = str(paper.get("arxiv_id") or "").strip()
    if arxiv_id:
        arxiv_id = re.sub(r"^arxiv:", "", arxiv_id, flags=re.IGNORECASE)
        return f"https://arxiv.org/abs/{quote(arxiv_id, safe='')}"
    url = str(paper.get("url") or "").strip()
    if url.lower().startswith("http://") or url.lower().startswith("https://"):
        return url
    return None


def podcast_category_for_paper(
    paper: Dict[str, Any],
    cited_project: Optional[str] = None,
) -> str:
    """Map a KE paper to a podcast category label. Discipline on the paper
    wins; GLMP-scoped papers with no discipline default to Biology rather
    than the web-form leftover 'Computer Science'."""
    raw = str(paper.get("discipline") or paper.get("category") or "").strip().lower()
    mapped = _DISCIPLINE_TO_CATEGORY.get(raw)
    if mapped:
        return mapped
    if (cited_project or "").lower() == "glmp":
        return "Biology"
    return "Computer Science"


def is_unambiguous_generation_match(match_type: str, papers: List[Dict[str, Any]]) -> bool:
    """True only when /generate-podcast-from-paper may proceed from a query.
    text_search is never enough, even with a single candidate -- the caller
    must confirm via paper_id. identifier_wrong_project / identifier_not_found
    are also rejected."""
    if match_type == "identifier":
        return bool(papers)
    if match_type == "exact_title":
        return len(papers) == 1
    return False


def _paper_matches_project(paper: Dict[str, Any], cited_project: str) -> bool:
    citations = paper.get("citations") or []
    for event in citations:
        if isinstance(event, dict) and (event.get("cited_project") or "").lower() == cited_project:
            return True
    return False


def resolve_by_identifier(ident: Dict[str, str]) -> Optional[Dict[str, Any]]:
    """Exact Firestore lookup by doi/pmid/arxiv_id. Returns the matching
    document (with `paper_id` set to the doc id), or None."""
    db = _firestore_db()
    if not db:
        return None
    from google.cloud.firestore_v1.base_query import FieldFilter
    field, value = next(iter(ident.items()))
    query = db.collection("research_papers").where(filter=FieldFilter(field, "==", value)).limit(1)
    docs = list(query.stream())
    if not docs:
        return None
    data = docs[0].to_dict()
    data["paper_id"] = docs[0].id
    return data


def resolve_by_exact_title(title: str, cited_project: Optional[str] = None) -> List[Dict[str, Any]]:
    """Exact Firestore equality match on the `title` field, tried before the
    semantic-search fallback. Confirmed necessary, not speculative: searching
    for a real GLMP paper using its own verbatim title still failed to
    surface it within a 60-candidate semantic search (2026-08-20 live test)
    -- the corpus has enough near-neighbor papers on the same general method
    that embedding similarity alone doesn't reliably rank the exact-title
    paper anywhere near the top. This catches the case that matters most in
    practice: a title copy-pasted verbatim from the Knowledge Engine.

    Necessarily case-sensitive and whitespace-exact (Firestore has no
    lowercased mirror field for title, unlike question_scope_ids) -- typos
    or partial titles still fall through to resolve_by_text. Cheap either
    way: a single indexed equality query, not a collection scan, so this is
    safe to try unconditionally rather than only as an opt-in."""
    db = _firestore_db()
    if not db:
        return []
    t = title.strip()
    if not t:
        return []
    from google.cloud.firestore_v1.base_query import FieldFilter
    docs = list(db.collection("research_papers").where(filter=FieldFilter("title", "==", t)).stream())
    papers = []
    for doc in docs:
        data = doc.to_dict()
        data["paper_id"] = doc.id
        papers.append(data)
    if cited_project:
        papers = [p for p in papers if _paper_matches_project(p, cited_project)]
    return papers


def get_paper_by_id(paper_id: str) -> Optional[Dict[str, Any]]:
    """Direct doc-id fetch, for the confirm-then-generate step once a
    candidate has already been picked (from resolve_paper's results)."""
    db = _firestore_db()
    if not db:
        return None
    doc = db.collection("research_papers").document(paper_id).get()
    if not doc.exists:
        return None
    data = doc.to_dict()
    data["paper_id"] = doc.id
    return data


async def resolve_by_text(
    query: str,
    cited_project: Optional[str] = None,
    limit: int = DEFAULT_TEXT_SEARCH_LIMIT,
) -> List[Dict[str, Any]]:
    """Semantic search, optionally filtered to a GLMP/ATAP project. See
    module docstring for the known scoping limitation of this path."""
    from mcp_server.tools.vector_search import search_semantic
    result_json = await search_semantic(query=query, content_types=["papers"], limit=limit)
    result = json.loads(result_json)
    papers = result.get("papers", [])
    if cited_project:
        papers = [p for p in papers if _paper_matches_project(p, cited_project)]
    return papers


async def resolve_paper(
    query: str,
    cited_project: Optional[str] = None,
    limit: int = DEFAULT_TEXT_SEARCH_LIMIT,
) -> Dict[str, Any]:
    """Top-level entry point.

    Tries, in order: (1) an identifier match (exact, unambiguous), (2) an
    exact `title` match (also exact, but case/whitespace-sensitive -- see
    resolve_by_exact_title), (3) free-text/title semantic search (candidates,
    may need disambiguation). Each step only runs if the previous one found
    nothing to work with -- an identifier always wins if the query parses as
    one; an exact title match always wins over falling back to semantic
    search.

    Returns {"match_type": ..., "papers": [...]}. match_type is one of:
      "identifier"               -- exact id match, single paper, right project (or none requested)
      "identifier_wrong_project" -- exact id match, but not tagged to the requested cited_project
      "identifier_not_found"     -- looked like an identifier, no such paper in Firestore
      "exact_title"              -- exact title match(es), right project (or none requested)
      "exact_title_wrong_project" -- exact title match(es), but none tagged to the requested project
      "text_search"              -- free-text query; 0, 1, or many candidates
    """
    if cited_project and cited_project not in VALID_PROJECTS:
        raise ValueError(f"cited_project must be one of {sorted(VALID_PROJECTS)}, got {cited_project!r}")

    ident = parse_identifier(query)
    if ident:
        paper = resolve_by_identifier(ident)
        if not paper:
            return {"match_type": "identifier_not_found", "papers": []}
        if cited_project and not _paper_matches_project(paper, cited_project):
            return {"match_type": "identifier_wrong_project", "papers": [paper]}
        return {"match_type": "identifier", "papers": [paper]}

    title_matches = resolve_by_exact_title(query)
    if title_matches:
        if cited_project:
            scoped = [p for p in title_matches if _paper_matches_project(p, cited_project)]
            if scoped:
                return {"match_type": "exact_title", "papers": scoped}
            return {"match_type": "exact_title_wrong_project", "papers": title_matches}
        return {"match_type": "exact_title", "papers": title_matches}

    papers = await resolve_by_text(query, cited_project=cited_project, limit=limit)
    return {"match_type": "text_search", "papers": papers}
