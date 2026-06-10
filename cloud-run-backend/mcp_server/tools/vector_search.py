"""
MCP Tools for Vector Search (Semantic Search)

Provides semantic search capabilities using vector embeddings across all
knowledge engine components (papers, podcasts, GLMP processes).
"""

import logging
from typing import Any, Dict, List, Optional
import json
from datetime import datetime
import re
import os

from google.cloud.firestore_v1.base_vector_query import DistanceMeasure
from google.cloud.firestore_v1.vector import Vector
from google.cloud.firestore_v1._helpers import DatetimeWithNanoseconds
from services.embedding_service import get_embedding_service
from mcp_server.utils.firestore_client import get_firestore_client
from mcp_server.config import (
    COLLECTION_PAPERS,
    COLLECTION_PODCASTS,
    COLLECTION_GLMP_PROCESSES,
    COLLECTION_MATH_PROCESSES,
    COLLECTION_CHEMISTRY_PROCESSES,
    COLLECTION_PHYSICS_PROCESSES,
    COLLECTION_COMPUTER_SCIENCE_PROCESSES,
    COLLECTION_BIOLOGY_PROCESSES,
    DEFAULT_QUERY_LIMIT,
    MAX_QUERY_LIMIT
)
from mcp_server.utils.gcs_client import list_glmp_files, get_glmp_file
from mcp_server.config import GCS_BUCKET_NAME, GLMP_BUCKET_PATH

logger = logging.getLogger(__name__)

_STOPWORDS = {
    "a", "an", "and", "are", "as", "at", "be", "by", "for", "from", "how", "i",
    "in", "is", "it", "of", "on", "or", "that", "the", "this", "to", "was", "were",
    "what", "when", "where", "which", "who", "why", "with", "you", "your"
}

def _env_flag(name: str, default: str = "0") -> bool:
    return (os.getenv(name, default) or "").strip().lower() in {"1", "true", "yes", "y", "on"}

VERTEX_AI_DISABLED = _env_flag("DISABLE_VERTEX_AI") or _env_flag("COPERNICUS_DISABLE_VERTEX_AI")


def _serialize_firestore_value(value: Any) -> Any:
    """Convert Firestore-specific types to JSON-serializable values."""
    if isinstance(value, DatetimeWithNanoseconds):
        return value.isoformat()
    elif isinstance(value, datetime):
        return value.isoformat()
    elif isinstance(value, dict):
        return {k: _serialize_firestore_value(v) for k, v in value.items()}
    elif isinstance(value, list):
        return [_serialize_firestore_value(item) for item in value]
    else:
        return value


def _tokenize_query(query: str) -> List[str]:
    tokens = [t for t in re.split(r"[^a-zA-Z0-9]+", (query or "").lower()) if t]
    # Keep short tokens only if they're meaningful (e.g., "ph", "ai" are ambiguous)
    filtered = [t for t in tokens if (t not in _STOPWORDS) and (len(t) >= 3)]
    return filtered or tokens  # fallback to raw tokens if everything was filtered out


def _search_results_total(results: dict) -> int:
    return (
        len(results.get("papers", []))
        + len(results.get("podcasts", []))
        + len(results.get("glmp_processes", []))
        + len(results.get("math_processes", []))
        + len(results.get("chemistry_processes", []))
        + len(results.get("physics_processes", []))
        + len(results.get("computer_science_processes", []))
        + len(results.get("biology_processes", []))
    )


def _score_text(tokens: List[str], title: str, body: str) -> float:
    """
    Lightweight keyword scoring.
    - Title matches count more than body matches
    - Returns 0.0 if no token matches
    """
    if not tokens:
        return 0.0
    t = (title or "").lower()
    b = (body or "").lower()
    title_hits = sum(1 for tok in tokens if tok in t)
    body_hits = sum(1 for tok in tokens if tok in b)
    score = (2.0 * title_hits) + (1.0 * body_hits)
    return float(score)


def _keyword_fallback_search(
    db,
    query: str,
    content_types: List[str],
    limit: int
) -> Dict[str, Any]:
    """
    Fallback retrieval when vector search returns no results (e.g., embeddings missing).

    Strategy: sample a limited number of docs per collection and rank by keyword overlap.
    This is intentionally simple, predictable, and index-free.
    """
    tokens = _tokenize_query(query)
    # Sample more than 'limit' so we have room to rank.
    #
    # IMPORTANT: Firestore `.limit(N)` without an order will return the "first" N docs
    # in an implementation-defined order (often doc-id order). In a large corpus, this
    # is likely to miss relevant items and produce empty results even for obvious queries.
    #
    # We intentionally scan a larger window and (when possible) prefer recent docs.
    #
    # NOTE: In practice, too-small windows (e.g. 300–1000) cause "obvious" queries to
    # occasionally return empty just because the match isn't in the scanned slice.
    # We bias toward a larger, still-bounded scan to improve recall while remaining
    # Vertex-free.
    candidate_limit = min(20000, max(5000, limit * 2000))

    def _stream_candidates(collection_ref):
        """
        Stream a "best effort" recent window.

        IMPORTANT:
        - Not all content types populate `published_at` (e.g., many PubMed JSONs).
        - Most ingested docs DO have `ingested_at`.

        We prefer `ingested_at` desc so newly ingested content is searchable immediately,
        then fall back to `published_at` desc, then unordered scan.
        """
        try:
            from google.cloud import firestore  # type: ignore
            try:
                # Prefer ingestion-time fields first; these exist for most docs we write.
                return (
                    collection_ref.order_by("updated_at", direction=firestore.Query.DESCENDING)
                    .limit(candidate_limit)
                    .stream()
                )
            except Exception:
                pass
            try:
                return (
                    collection_ref.order_by("created_at", direction=firestore.Query.DESCENDING)
                    .limit(candidate_limit)
                    .stream()
                )
            except Exception:
                pass
            try:
                return (
                    collection_ref.order_by("ingested_at", direction=firestore.Query.DESCENDING)
                    .limit(candidate_limit)
                    .stream()
                )
            except Exception:
                return (
                    collection_ref.order_by("published_at", direction=firestore.Query.DESCENDING)
                    .limit(candidate_limit)
                    .stream()
                )
        except Exception:
            return collection_ref.limit(candidate_limit).stream()

    results: Dict[str, Any] = {
        "papers": [],
        "podcasts": [],
        "glmp_processes": [],
        "math_processes": [],
        "chemistry_processes": [],
        "physics_processes": [],
        "computer_science_processes": [],
        "biology_processes": [],
    }

    def _top_k(scored: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        scored.sort(key=lambda x: x.get("_kw_score", 0.0), reverse=True)
        top = [x for x in scored if x.get("_kw_score", 0.0) > 0.0][:limit]
        for item in top:
            # Turn keyword score into a pseudo "similarity_score" in [0, 1]
            denom = max(1.0, float(len(tokens)) * 2.0)
            sim = min(0.95, float(item.get("_kw_score", 0.0)) / denom)
            item["similarity_score"] = round(sim, 3)
            item.pop("_kw_score", None)
        return top

    # Papers
    if "papers" in content_types:
        scored: List[Dict[str, Any]] = []
        try:
            scanned = 0
            for doc in _stream_candidates(db.collection(COLLECTION_PAPERS)):
                d = doc.to_dict() or {}
                title = d.get("title") or ""
                body = " ".join([
                    d.get("abstract") or "",
                    " ".join(d.get("keywords") or []) if isinstance(d.get("keywords"), list) else str(d.get("keywords") or ""),
                    " ".join(d.get("categories") or []) if isinstance(d.get("categories"), list) else str(d.get("categories") or ""),
                ])
                score = _score_text(tokens, title, body)
                if score <= 0:
                    scanned += 1
                    continue
                d["paper_id"] = doc.id
                d.pop("embedding", None)
                d = _serialize_firestore_value(d)
                d["_kw_score"] = score
                scored.append(d)
                scanned += 1
                # Early exit once we have plenty to rank
                if len(scored) >= (limit * 20) and scanned >= min(candidate_limit, 2000):
                    break
        except Exception as e:
            logger.warning(f"Keyword fallback for papers failed: {e}")
        results["papers"] = _top_k(scored)

    # Podcasts
    if "podcasts" in content_types:
        scored = []
        try:
            scanned = 0
            for doc in _stream_candidates(db.collection(COLLECTION_PODCASTS)):
                d = doc.to_dict() or {}
                title = d.get("title") or (d.get("result", {}) or {}).get("title") or ""
                desc = d.get("description") or (d.get("result", {}) or {}).get("description") or ""
                script = (d.get("result", {}) or {}).get("script") or d.get("transcript") or ""
                body = " ".join([desc, script[:1500]])
                score = _score_text(tokens, title, body)
                if score <= 0:
                    scanned += 1
                    continue
                d["job_id"] = doc.id
                d.pop("embedding", None)
                d = _serialize_firestore_value(d)
                d["_kw_score"] = score
                scored.append(d)
                scanned += 1
                if len(scored) >= (limit * 20) and scanned >= min(candidate_limit, 2000):
                    break
        except Exception as e:
            logger.warning(f"Keyword fallback for podcasts failed: {e}")
        results["podcasts"] = _top_k(scored)

    def _keyword_processes(collection: str, key: str, title_fields: List[str], body_fields: List[str]) -> List[Dict[str, Any]]:
        scored_local: List[Dict[str, Any]] = []
        try:
            scanned = 0
            for doc in _stream_candidates(db.collection(collection)):
                d = doc.to_dict() or {}
                title = ""
                for f in title_fields:
                    if d.get(f):
                        title = str(d.get(f))
                        break
                body_parts: List[str] = []
                for f in body_fields:
                    v = d.get(f)
                    if isinstance(v, list):
                        body_parts.append(" ".join([str(x) for x in v[:50]]))
                    elif v:
                        body_parts.append(str(v)[:2000])
                body = " ".join(body_parts)
                score = _score_text(tokens, title, body)
                if score <= 0:
                    scanned += 1
                    continue
                d["process_id"] = doc.id
                d.pop("embedding", None)
                d = _serialize_firestore_value(d)
                d["_kw_score"] = score
                scored_local.append(d)
                scanned += 1
                if len(scored_local) >= (limit * 20) and scanned >= min(candidate_limit, 2000):
                    break
        except Exception as e:
            logger.warning(f"Keyword fallback for {key} failed: {e}")
        return _top_k(scored_local)

    # GLMP processes
    if "glmp" in content_types:
        results["glmp_processes"] = _keyword_processes(
            COLLECTION_GLMP_PROCESSES,
            "glmp_processes",
            title_fields=["title", "name"],
            body_fields=["description", "category", "entities", "keywords"]
        )

    # Math processes
    if "math" in content_types:
        results["math_processes"] = _keyword_processes(
            COLLECTION_MATH_PROCESSES,
            "math_processes",
            title_fields=["title", "name"],
            body_fields=["description", "category", "subcategory", "entities", "keywords"]
        )

    # Chemistry processes
    if "chemistry" in content_types:
        results["chemistry_processes"] = _keyword_processes(
            COLLECTION_CHEMISTRY_PROCESSES,
            "chemistry_processes",
            title_fields=["title", "name"],
            body_fields=["description", "category", "subcategory", "entities", "keywords"]
        )

    # Physics processes
    if "physics" in content_types:
        results["physics_processes"] = _keyword_processes(
            COLLECTION_PHYSICS_PROCESSES,
            "physics_processes",
            title_fields=["title", "name"],
            body_fields=["description", "category", "subcategory", "entities", "keywords"]
        )

    # CS processes
    if "computer_science" in content_types:
        results["computer_science_processes"] = _keyword_processes(
            COLLECTION_COMPUTER_SCIENCE_PROCESSES,
            "computer_science_processes",
            title_fields=["title", "name"],
            body_fields=["description", "category", "subcategory", "entities", "keywords"]
        )

    # Biology processes
    if "biology" in content_types:
        results["biology_processes"] = _keyword_processes(
            COLLECTION_BIOLOGY_PROCESSES,
            "biology_processes",
            title_fields=["title", "name"],
            body_fields=["description", "category", "subcategory", "entities", "keywords"]
        )

    return results


async def search_semantic(
    query: str,
    content_types: Optional[List[str]] = None,
    limit: int = DEFAULT_QUERY_LIMIT,
    distance_threshold: float = 0.7
) -> str:
    """
    Semantic search across all content using vector embeddings.
    
    Uses vector similarity to find content that is semantically similar
    to the query, even if it doesn't contain exact keywords.
    
    Args:
        query: Natural language search query
        content_types: Filter by type (default: all)
                      Options: ["papers", "podcasts", "glmp", "math", "chemistry", "physics", "computer_science"]
        limit: Maximum results per content type (default: 10, max: 100)
        distance_threshold: Maximum distance for similarity (0.0-1.0, lower = more similar)
                           Default: 0.7 (allows some flexibility)
    
    Returns:
        JSON string with semantically similar content from all specified types
    """
    try:
        # Validate limit
        limit = min(max(1, limit), MAX_QUERY_LIMIT)
        
        # Default to all content types if not specified
        if not content_types:
            content_types = [
                "papers", "podcasts", "glmp", "math", "chemistry",
                "physics", "computer_science", "biology",
            ]
        
        # Initialize services
        db = get_firestore_client()

        # Query embedding: OpenAI (preferred) or Vertex via embedding_factory — not gated on DISABLE_VERTEX_AI.
        query_embedding = None
        try:
            embedding_service = get_embedding_service()
            query_embedding = embedding_service.embed_text(query)
        except Exception as e:
            logger.warning(f"Embedding generation unavailable; using keyword search only: {e}")
            query_embedding = None
        
        results = {
            "query": query,
            "content_types_searched": content_types,
            "papers": [],
            "podcasts": [],
            "glmp_processes": [],
            "math_processes": [],
            "chemistry_processes": [],
            "physics_processes": [],
            "computer_science_processes": [],
            "biology_processes": [],
            "search_method": "vector_semantic" if query_embedding is not None else "keyword_only"
        }

        # Keyword-first mode (no embeddings available)
        if query_embedding is None:
            try:
                fallback = _keyword_fallback_search(
                    db=db,
                    query=query,
                    content_types=content_types,
                    limit=limit
                )
                for k, v in fallback.items():
                    results[k] = v
                results["counts"] = {
                    "papers": len(results["papers"]),
                    "podcasts": len(results["podcasts"]),
                    "glmp_processes": len(results["glmp_processes"]),
                    "math_processes": len(results["math_processes"]),
                    "chemistry_processes": len(results["chemistry_processes"]),
                    "physics_processes": len(results["physics_processes"]),
                    "computer_science_processes": len(results["computer_science_processes"]),
                    "biology_processes": len(results["biology_processes"]),
                    "total": _search_results_total(results),
                }
                return json.dumps(results, indent=2)
            except Exception as e:
                logger.warning(f"Keyword-only search failed: {e}")
                return json.dumps(results, indent=2)
        
        # Search papers using vector search
        if "papers" in content_types:
            try:
                papers_ref = db.collection(COLLECTION_PAPERS)
                
                # Use Firestore vector search (find_nearest)
                # Note: This requires documents to have an 'embedding' field
                vector_query = papers_ref.find_nearest(
                    vector_field="embedding",
                    query_vector=Vector(query_embedding),
                    limit=limit,
                    distance_measure=DistanceMeasure.COSINE,
                    distance_threshold=distance_threshold
                )
                
                paper_docs = vector_query.stream()
                
                for doc in paper_docs:
                    paper_data = doc.to_dict()
                    paper_data["paper_id"] = doc.id
                    paper_data["similarity_score"] = 1.0 - paper_data.get("distance", 1.0)
                    # Remove embedding from response (too large)
                    paper_data.pop("embedding", None)
                    # Convert Firestore types to JSON-serializable
                    paper_data = _serialize_firestore_value(paper_data)
                    results["papers"].append(paper_data)
                
                logger.info(f"Found {len(results['papers'])} papers via vector search")
                
            except Exception as e:
                logger.warning(f"Vector search for papers failed, may not have embeddings: {e}")
                # Fallback: return empty results rather than failing
                results["papers"] = []
        
        # Search podcasts using vector search
        if "podcasts" in content_types:
            try:
                podcasts_ref = db.collection(COLLECTION_PODCASTS)
                
                vector_query = podcasts_ref.find_nearest(
                    vector_field="embedding",
                    query_vector=Vector(query_embedding),
                    limit=limit,
                    distance_measure=DistanceMeasure.COSINE,
                    distance_threshold=distance_threshold
                )
                
                podcast_docs = vector_query.stream()
                
                for doc in podcast_docs:
                    podcast_data = doc.to_dict()
                    podcast_data["job_id"] = doc.id
                    podcast_data["similarity_score"] = 1.0 - podcast_data.get("distance", 1.0)
                    # Remove embedding from response
                    podcast_data.pop("embedding", None)
                    # Convert Firestore types to JSON-serializable
                    podcast_data = _serialize_firestore_value(podcast_data)
                    results["podcasts"].append(podcast_data)
                
                logger.info(f"Found {len(results['podcasts'])} podcasts via vector search")
                
            except Exception as e:
                logger.warning(f"Vector search for podcasts failed, may not have embeddings: {e}")
                results["podcasts"] = []
        
        # Search GLMP processes using vector search
        if "glmp" in content_types:
            try:
                glmp_ref = db.collection(COLLECTION_GLMP_PROCESSES)
                
                # Use Firestore vector search (find_nearest)
                vector_query = glmp_ref.find_nearest(
                    vector_field="embedding",
                    query_vector=Vector(query_embedding),
                    limit=limit,
                    distance_measure=DistanceMeasure.COSINE,
                    distance_threshold=distance_threshold
                )
                
                glmp_docs = vector_query.stream()
                
                for doc in glmp_docs:
                    glmp_data = doc.to_dict()
                    glmp_data["process_id"] = doc.id
                    glmp_data["similarity_score"] = 1.0 - glmp_data.get("distance", 1.0)
                    # Remove embedding from response (too large)
                    glmp_data.pop("embedding", None)
                    # Remove large mermaid_code from response (can be fetched separately if needed)
                    if "mermaid_code" in glmp_data and len(str(glmp_data["mermaid_code"])) > 500:
                        glmp_data["has_mermaid"] = True
                        glmp_data.pop("mermaid_code", None)
                    # Convert Firestore types to JSON-serializable
                    glmp_data = _serialize_firestore_value(glmp_data)
                    results["glmp_processes"].append(glmp_data)
                
                logger.info(f"Found {len(results['glmp_processes'])} GLMP processes via vector search")
                
            except Exception as e:
                logger.warning(f"Vector search for GLMP processes failed: {e}")
                results["glmp_processes"] = []
        
        # Search math processes using vector search
        if "math" in content_types:
            try:
                math_ref = db.collection(COLLECTION_MATH_PROCESSES)
                
                # Use Firestore vector search (find_nearest)
                vector_query = math_ref.find_nearest(
                    vector_field="embedding",
                    query_vector=Vector(query_embedding),
                    limit=limit,
                    distance_measure=DistanceMeasure.COSINE,
                    distance_threshold=distance_threshold
                )
                
                math_docs = vector_query.stream()
                
                for doc in math_docs:
                    math_data = doc.to_dict()
                    math_data["process_id"] = doc.id
                    math_data["similarity_score"] = 1.0 - math_data.get("distance", 1.0)
                    # Remove embedding from response (too large)
                    math_data.pop("embedding", None)
                    # Remove large mermaid_code from response (can be fetched separately if needed)
                    if "mermaid_code" in math_data and len(str(math_data["mermaid_code"])) > 500:
                        math_data["has_mermaid"] = True
                        math_data.pop("mermaid_code", None)
                    # Convert Firestore types to JSON-serializable
                    math_data = _serialize_firestore_value(math_data)
                    results["math_processes"].append(math_data)
                
                logger.info(f"Found {len(results['math_processes'])} math processes via vector search")
                
            except Exception as e:
                logger.warning(f"Vector search for math processes failed: {e}")
                results["math_processes"] = []
        
        # Search chemistry processes using vector search
        if "chemistry" in content_types:
            try:
                chemistry_ref = db.collection(COLLECTION_CHEMISTRY_PROCESSES)
                vector_query = chemistry_ref.find_nearest(
                    vector_field="embedding",
                    query_vector=Vector(query_embedding),
                    limit=limit,
                    distance_measure=DistanceMeasure.COSINE,
                    distance_threshold=distance_threshold
                )
                
                chemistry_docs = vector_query.stream()
                
                for doc in chemistry_docs:
                    chemistry_data = doc.to_dict()
                    chemistry_data["process_id"] = doc.id
                    chemistry_data["similarity_score"] = 1.0 - chemistry_data.get("distance", 1.0)
                    chemistry_data.pop("embedding", None)
                    if "mermaid_code" in chemistry_data and len(str(chemistry_data["mermaid_code"])) > 500:
                        chemistry_data["has_mermaid"] = True
                        chemistry_data.pop("mermaid_code", None)
                    chemistry_data = _serialize_firestore_value(chemistry_data)
                    results["chemistry_processes"].append(chemistry_data)
                
                logger.info(f"Found {len(results['chemistry_processes'])} chemistry processes via vector search")
                
            except Exception as e:
                logger.warning(f"Vector search for chemistry processes failed: {e}")
                results["chemistry_processes"] = []
        
        # Search physics processes using vector search
        if "physics" in content_types:
            try:
                physics_ref = db.collection(COLLECTION_PHYSICS_PROCESSES)
                vector_query = physics_ref.find_nearest(
                    vector_field="embedding",
                    query_vector=Vector(query_embedding),
                    limit=limit,
                    distance_measure=DistanceMeasure.COSINE,
                    distance_threshold=distance_threshold
                )
                
                physics_docs = vector_query.stream()
                
                for doc in physics_docs:
                    physics_data = doc.to_dict()
                    physics_data["process_id"] = doc.id
                    physics_data["similarity_score"] = 1.0 - physics_data.get("distance", 1.0)
                    physics_data.pop("embedding", None)
                    if "mermaid_code" in physics_data and len(str(physics_data["mermaid_code"])) > 500:
                        physics_data["has_mermaid"] = True
                        physics_data.pop("mermaid_code", None)
                    physics_data = _serialize_firestore_value(physics_data)
                    results["physics_processes"].append(physics_data)
                
                logger.info(f"Found {len(results['physics_processes'])} physics processes via vector search")
                
            except Exception as e:
                logger.warning(f"Vector search for physics processes failed: {e}")
                results["physics_processes"] = []
        
        # Search computer science processes using vector search
        if "computer_science" in content_types:
            try:
                cs_ref = db.collection(COLLECTION_COMPUTER_SCIENCE_PROCESSES)
                vector_query = cs_ref.find_nearest(
                    vector_field="embedding",
                    query_vector=Vector(query_embedding),
                    limit=limit,
                    distance_measure=DistanceMeasure.COSINE,
                    distance_threshold=distance_threshold
                )
                
                cs_docs = vector_query.stream()
                
                for doc in cs_docs:
                    cs_data = doc.to_dict()
                    cs_data["process_id"] = doc.id
                    cs_data["similarity_score"] = 1.0 - cs_data.get("distance", 1.0)
                    cs_data.pop("embedding", None)
                    if "mermaid_code" in cs_data and len(str(cs_data["mermaid_code"])) > 500:
                        cs_data["has_mermaid"] = True
                        cs_data.pop("mermaid_code", None)
                    cs_data = _serialize_firestore_value(cs_data)
                    results["computer_science_processes"].append(cs_data)
                
                logger.info(f"Found {len(results['computer_science_processes'])} computer science processes via vector search")
                
            except Exception as e:
                logger.warning(f"Vector search for computer science processes failed: {e}")
                results["computer_science_processes"] = []
        
        # Search biology processes using vector search
        if "biology" in content_types:
            try:
                bio_ref = db.collection(COLLECTION_BIOLOGY_PROCESSES)
                vector_query = bio_ref.find_nearest(
                    vector_field="embedding",
                    query_vector=Vector(query_embedding),
                    limit=limit,
                    distance_measure=DistanceMeasure.COSINE,
                    distance_threshold=distance_threshold
                )
                for doc in vector_query.stream():
                    bio_data = doc.to_dict()
                    bio_data["process_id"] = doc.id
                    bio_data["similarity_score"] = 1.0 - bio_data.get("distance", 1.0)
                    bio_data.pop("embedding", None)
                    if "mermaid_code" in bio_data and len(str(bio_data["mermaid_code"])) > 500:
                        bio_data["has_mermaid"] = True
                        bio_data.pop("mermaid_code", None)
                    bio_data = _serialize_firestore_value(bio_data)
                    results["biology_processes"].append(bio_data)
                logger.info(f"Found {len(results['biology_processes'])} biology processes via vector search")
            except Exception as e:
                logger.warning(f"Vector search for biology processes failed: {e}")
                results["biology_processes"] = []

        # Add summary counts
        results["counts"] = {
            "papers": len(results["papers"]),
            "podcasts": len(results["podcasts"]),
            "glmp_processes": len(results["glmp_processes"]),
            "math_processes": len(results["math_processes"]),
            "chemistry_processes": len(results["chemistry_processes"]),
            "physics_processes": len(results["physics_processes"]),
            "computer_science_processes": len(results["computer_science_processes"]),
            "biology_processes": len(results["biology_processes"]),
            "total": _search_results_total(results),
        }

        # If vector search yields nothing (common when embeddings aren't present),
        # fall back to a lightweight keyword search over a limited sample.
        if results["counts"]["total"] == 0:
            try:
                fallback = _keyword_fallback_search(
                    db=db,
                    query=query,
                    content_types=content_types,
                    limit=limit
                )
                for k, v in fallback.items():
                    results[k] = v
                results["search_method"] = "keyword_fallback"
                results["counts"] = {
                    "papers": len(results["papers"]),
                    "podcasts": len(results["podcasts"]),
                    "glmp_processes": len(results["glmp_processes"]),
                    "math_processes": len(results["math_processes"]),
                    "chemistry_processes": len(results["chemistry_processes"]),
                    "physics_processes": len(results["physics_processes"]),
                    "computer_science_processes": len(results["computer_science_processes"]),
                    "biology_processes": len(results["biology_processes"]),
                    "total": _search_results_total(results),
                }
                logger.info(
                    "Vector search returned 0 results; keyword fallback used",
                    extra={"query": query[:80], "total": results["counts"]["total"]}
                )
            except Exception as e:
                logger.warning(f"Keyword fallback failed: {e}")
        
        return json.dumps(results, indent=2)
        
    except Exception as e:
        logger.error(f"Error in semantic search: {e}", exc_info=True)
        return json.dumps({
            "error": f"Failed to perform semantic search: {str(e)}",
            "query": query,
            "papers": [],
            "podcasts": [],
            "glmp_processes": [],
            "math_processes": [],
            "counts": {"papers": 0, "podcasts": 0, "glmp_processes": 0, "math_processes": 0, "total": 0}
        })


async def find_similar_content(
    content_id: str,
    content_type: str,
    limit: int = DEFAULT_QUERY_LIMIT
) -> str:
    """
    Find content similar to a given paper, podcast, GLMP process, or math process.
    
    Uses the embedding of the specified content to find semantically
    similar items across all components.
    
    Args:
        content_id: ID of the content item (paper_id, job_id, or process_id)
        content_type: Type of content ("paper", "podcast", "glmp", or "math")
        limit: Maximum results to return (default: 10, max: 100)
    
    Returns:
        JSON string with similar content from all components
    """
    try:
        # Validate limit
        limit = min(max(1, limit), MAX_QUERY_LIMIT)
        
        # Initialize services
        embedding_service = get_embedding_service()
        db = get_firestore_client()
        
        # Get the source content and its embedding
        source_embedding = None
        source_info = {}
        
        if content_type == "paper":
            paper_ref = db.collection(COLLECTION_PAPERS).document(content_id)
            paper_doc = paper_ref.get()
            
            if not paper_doc.exists:
                return json.dumps({
                    "error": f"Paper not found: {content_id}",
                    "similar_content": []
                })
            
            paper_data = paper_doc.to_dict()
            source_embedding = paper_data.get("embedding")
            source_info = {
                "type": "paper",
                "id": content_id,
                "title": paper_data.get("title")
            }
            
            # If no embedding, generate one
            if not source_embedding:
                text = create_text_for_paper(paper_data)
                source_embedding = embedding_service.embed_text(text)
        
        elif content_type == "podcast":
            podcast_ref = db.collection(COLLECTION_PODCASTS).document(content_id)
            podcast_doc = podcast_ref.get()
            
            if not podcast_doc.exists:
                return json.dumps({
                    "error": f"Podcast not found: {content_id}",
                    "similar_content": []
                })
            
            podcast_data = podcast_doc.to_dict()
            source_embedding = podcast_data.get("embedding")
            source_info = {
                "type": "podcast",
                "id": content_id,
                "title": podcast_data.get("title")
            }
            
            # If no embedding, generate one
            if not source_embedding:
                text = create_text_for_podcast(podcast_data)
                source_embedding = embedding_service.embed_text(text)
        
        elif content_type == "glmp":
            # Get GLMP process from Firestore
            glmp_doc = db.collection(COLLECTION_GLMP_PROCESSES).document(content_id).get()
            if not glmp_doc.exists:
                return json.dumps({
                    "error": f"GLMP process not found: {content_id}",
                    "similar_content": []
                })
            
            glmp_data = glmp_doc.to_dict()
            source_embedding = glmp_data.get("embedding")
            source_info = {
                "type": "glmp",
                "id": content_id,
                "title": glmp_data.get("title") or glmp_data.get("name")
            }
            
            # If no embedding, generate one
            if not source_embedding:
                text = create_text_for_glmp(glmp_data)
                source_embedding = embedding_service.embed_text(text)
        
        elif content_type == "math":
            # Get math process from Firestore
            math_doc = db.collection(COLLECTION_MATH_PROCESSES).document(content_id).get()
            if not math_doc.exists:
                return json.dumps({
                    "error": f"Math process not found: {content_id}",
                    "similar_content": []
                })
            
            math_data = math_doc.to_dict()
            source_embedding = math_data.get("embedding")
            source_info = {
                "type": "math",
                "id": content_id,
                "title": math_data.get("title")
            }
            
            # If no embedding, generate one
            if not source_embedding:
                text = create_text_for_math(math_data)
                source_embedding = embedding_service.embed_text(text)
        
        elif content_type == "chemistry":
            chemistry_doc = db.collection(COLLECTION_CHEMISTRY_PROCESSES).document(content_id).get()
            if not chemistry_doc.exists:
                return json.dumps({
                    "error": f"Chemistry process not found: {content_id}",
                    "similar_content": []
                })
            
            chemistry_data = chemistry_doc.to_dict()
            source_embedding = chemistry_data.get("embedding")
            source_info = {
                "type": "chemistry",
                "id": content_id,
                "title": chemistry_data.get("title")
            }
            
            if not source_embedding:
                text = create_text_for_chemistry(chemistry_data)
                source_embedding = embedding_service.embed_text(text)
        
        elif content_type == "physics":
            physics_doc = db.collection(COLLECTION_PHYSICS_PROCESSES).document(content_id).get()
            if not physics_doc.exists:
                return json.dumps({
                    "error": f"Physics process not found: {content_id}",
                    "similar_content": []
                })
            
            physics_data = physics_doc.to_dict()
            source_embedding = physics_data.get("embedding")
            source_info = {
                "type": "physics",
                "id": content_id,
                "title": physics_data.get("title")
            }
            
            if not source_embedding:
                text = create_text_for_physics(physics_data)
                source_embedding = embedding_service.embed_text(text)
        
        elif content_type == "computer_science":
            cs_doc = db.collection(COLLECTION_COMPUTER_SCIENCE_PROCESSES).document(content_id).get()
            if not cs_doc.exists:
                return json.dumps({
                    "error": f"Computer science process not found: {content_id}",
                    "similar_content": []
                })
            
            cs_data = cs_doc.to_dict()
            source_embedding = cs_data.get("embedding")
            source_info = {
                "type": "computer_science",
                "id": content_id,
                "title": cs_data.get("title")
            }
            
            if not source_embedding:
                text = create_text_for_computer_science(cs_data)
                source_embedding = embedding_service.embed_text(text)
        
        else:
            return json.dumps({
                "error": f"Unknown content type: {content_type}",
                "similar_content": []
            })
        
        if not source_embedding:
            return json.dumps({
                "error": "Could not generate embedding for source content",
                "similar_content": []
            })
        
        # Search for similar content using the source embedding
        results = {
            "source": source_info,
            "similar_papers": [],
            "similar_podcasts": [],
            "similar_glmp_processes": [],
            "similar_math_processes": [],
            "similar_chemistry_processes": [],
            "similar_physics_processes": [],
            "similar_computer_science_processes": []
        }
        
        # Find similar papers
        try:
            papers_ref = db.collection(COLLECTION_PAPERS)
            vector_query = papers_ref.find_nearest(
                vector_field="embedding",
                query_vector=Vector(source_embedding),
                limit=limit,
                distance_measure=DistanceMeasure.COSINE,
                distance_threshold=0.8  # Slightly more lenient for similarity
            )
            
            for doc in vector_query.stream():
                if doc.id == content_id and content_type == "paper":
                    continue  # Skip the source paper itself
                
                paper_data = doc.to_dict()
                paper_data["paper_id"] = doc.id
                paper_data["similarity_score"] = 1.0 - paper_data.get("distance", 1.0)
                paper_data.pop("embedding", None)
                # Convert Firestore types to JSON-serializable
                paper_data = _serialize_firestore_value(paper_data)
                results["similar_papers"].append(paper_data)
        
        except Exception as e:
            logger.warning(f"Similar papers search failed: {e}")
            results["similar_papers"] = []
        
        # Find similar podcasts
        try:
            podcasts_ref = db.collection(COLLECTION_PODCASTS)
            vector_query = podcasts_ref.find_nearest(
                vector_field="embedding",
                query_vector=Vector(source_embedding),
                limit=limit,
                distance_measure=DistanceMeasure.COSINE,
                distance_threshold=0.8
            )
            
            for doc in vector_query.stream():
                if doc.id == content_id and content_type == "podcast":
                    continue  # Skip the source podcast itself
                
                podcast_data = doc.to_dict()
                podcast_data["job_id"] = doc.id
                podcast_data["similarity_score"] = 1.0 - podcast_data.get("distance", 1.0)
                podcast_data.pop("embedding", None)
                # Convert Firestore types to JSON-serializable
                podcast_data = _serialize_firestore_value(podcast_data)
                results["similar_podcasts"].append(podcast_data)
        
        except Exception as e:
            logger.warning(f"Similar podcasts search failed: {e}")
            results["similar_podcasts"] = []
        
        # Find similar GLMP processes
        try:
            glmp_ref = db.collection(COLLECTION_GLMP_PROCESSES)
            vector_query = glmp_ref.find_nearest(
                vector_field="embedding",
                query_vector=Vector(source_embedding),
                limit=limit,
                distance_measure=DistanceMeasure.COSINE,
                distance_threshold=0.8
            )
            
            for doc in vector_query.stream():
                if doc.id == content_id and content_type == "glmp":
                    continue  # Skip the source GLMP process itself
                
                glmp_data = doc.to_dict()
                glmp_data["process_id"] = doc.id
                glmp_data["similarity_score"] = 1.0 - glmp_data.get("distance", 1.0)
                glmp_data.pop("embedding", None)
                # Remove large mermaid_code from response
                if "mermaid_code" in glmp_data and len(str(glmp_data["mermaid_code"])) > 500:
                    glmp_data["has_mermaid"] = True
                    glmp_data.pop("mermaid_code", None)
                # Convert Firestore types to JSON-serializable
                glmp_data = _serialize_firestore_value(glmp_data)
                results["similar_glmp_processes"].append(glmp_data)
        
        except Exception as e:
            logger.warning(f"Similar GLMP processes search failed: {e}")
            results["similar_glmp_processes"] = []
        
        # Find similar math processes
        try:
            math_ref = db.collection(COLLECTION_MATH_PROCESSES)
            vector_query = math_ref.find_nearest(
                vector_field="embedding",
                query_vector=Vector(source_embedding),
                limit=limit,
                distance_measure=DistanceMeasure.COSINE,
                distance_threshold=0.8
            )
            
            for doc in vector_query.stream():
                if doc.id == content_id and content_type == "math":
                    continue  # Skip the source math process itself
                
                math_data = doc.to_dict()
                math_data["process_id"] = doc.id
                math_data["similarity_score"] = 1.0 - math_data.get("distance", 1.0)
                math_data.pop("embedding", None)
                # Remove large mermaid_code from response
                if "mermaid_code" in math_data and len(str(math_data["mermaid_code"])) > 500:
                    math_data["has_mermaid"] = True
                    math_data.pop("mermaid_code", None)
                # Convert Firestore types to JSON-serializable
                math_data = _serialize_firestore_value(math_data)
                results["similar_math_processes"].append(math_data)
        
        except Exception as e:
            logger.warning(f"Similar math processes search failed: {e}")
            results["similar_math_processes"] = []
        
        # Add counts
        results["counts"] = {
            "papers": len(results["similar_papers"]),
            "podcasts": len(results["similar_podcasts"]),
            "glmp_processes": len(results["similar_glmp_processes"]),
            "math_processes": len(results["similar_math_processes"]),
            "chemistry_processes": len(results["similar_chemistry_processes"]),
            "physics_processes": len(results["similar_physics_processes"]),
            "computer_science_processes": len(results["similar_computer_science_processes"]),
            "total": (len(results["similar_papers"]) + len(results["similar_podcasts"]) + 
                     len(results["similar_glmp_processes"]) + len(results["similar_math_processes"]) +
                     len(results["similar_chemistry_processes"]) + len(results["similar_physics_processes"]) +
                     len(results["similar_computer_science_processes"]))
        }
        
        return json.dumps(results, indent=2)
        
    except Exception as e:
        logger.error(f"Error finding similar content: {e}", exc_info=True)
        return json.dumps({
            "error": f"Failed to find similar content: {str(e)}",
            "similar_content": []
        })


# Helper functions for creating text representations (used by find_similar_content)
def create_text_for_paper(paper: Dict[str, Any]) -> str:
    """Create text representation of paper for embedding."""
    parts = []
    if paper.get('title'):
        parts.append(paper['title'])
    if paper.get('abstract'):
        parts.append(paper['abstract'])
    if paper.get('keywords'):
        if isinstance(paper['keywords'], list):
            parts.append(' '.join(paper['keywords']))
    return '\n'.join(parts)


def create_text_for_podcast(podcast: Dict[str, Any]) -> str:
    """Create text representation of podcast for embedding."""
    parts = []
    if podcast.get('title'):
        parts.append(podcast['title'])
    if podcast.get('description'):
        parts.append(podcast['description'])
    if podcast.get('transcript'):
        parts.append(podcast['transcript'][:1000])
    return '\n'.join(parts)


def create_text_for_glmp(process: Dict[str, Any]) -> str:
    """Create text representation of GLMP process for embedding."""
    parts = []
    if process.get('title'):
        parts.append(process['title'])
    if process.get('description'):
        parts.append(process['description'])
    if process.get('entities'):
        if isinstance(process['entities'], list):
            parts.append(f"Entities: {', '.join(process['entities'])}")
    if process.get('mermaid') or process.get('mermaid_code'):
        mermaid_text = (process.get('mermaid') or process.get('mermaid_code', ''))[:500]
        parts.append(f"Mermaid: {mermaid_text}")
    if process.get('category'):
        parts.append(f"Category: {process['category']}")
    return '\n'.join(parts)


def create_text_for_math(process: Dict[str, Any]) -> str:
    """Create text representation of math process for embedding."""
    parts = []
    if process.get('title'):
        parts.append(process['title'])
    if process.get('description'):
        parts.append(process['description'])
    if process.get('category'):
        parts.append(f"Category: {process['category']}")
    if process.get('subcategory'):
        parts.append(f"Subcategory: {process['subcategory']}")
    if process.get('entities'):
        if isinstance(process['entities'], list):
            parts.append(f"Entities: {', '.join(process['entities'][:20])}")
    if process.get('mermaid_code'):
        mermaid_text = process['mermaid_code'][:500]
        parts.append(f"Mermaid: {mermaid_text}")
    return '\n'.join(parts)


def create_text_for_chemistry(process: Dict[str, Any]) -> str:
    """Create text representation of chemistry process for embedding."""
    parts = []
    if process.get('title'):
        parts.append(process['title'])
    if process.get('description'):
        parts.append(process['description'])
    if process.get('category'):
        parts.append(f"Category: {process['category']}")
    if process.get('subcategory'):
        parts.append(f"Subcategory: {process['subcategory']}")
    if process.get('entities'):
        if isinstance(process['entities'], list):
            parts.append(f"Entities: {', '.join(process['entities'][:20])}")
    if process.get('mermaid_code'):
        mermaid_text = process['mermaid_code'][:500]
        parts.append(f"Mermaid: {mermaid_text}")
    return '\n'.join(parts)


def create_text_for_physics(process: Dict[str, Any]) -> str:
    """Create text representation of physics process for embedding."""
    parts = []
    if process.get('title'):
        parts.append(process['title'])
    if process.get('description'):
        parts.append(process['description'])
    if process.get('category'):
        parts.append(f"Category: {process['category']}")
    if process.get('subcategory'):
        parts.append(f"Subcategory: {process['subcategory']}")
    if process.get('entities'):
        if isinstance(process['entities'], list):
            parts.append(f"Entities: {', '.join(process['entities'][:20])}")
    if process.get('mermaid_code'):
        mermaid_text = process['mermaid_code'][:500]
        parts.append(f"Mermaid: {mermaid_text}")
    return '\n'.join(parts)


def create_text_for_computer_science(process: Dict[str, Any]) -> str:
    """Create text representation of computer science process for embedding."""
    parts = []
    if process.get('title'):
        parts.append(process['title'])
    if process.get('description'):
        parts.append(process['description'])
    if process.get('category'):
        parts.append(f"Category: {process['category']}")
    if process.get('subcategory'):
        parts.append(f"Subcategory: {process['subcategory']}")
    if process.get('entities'):
        if isinstance(process['entities'], list):
            parts.append(f"Entities: {', '.join(process['entities'][:20])}")
    if process.get('mermaid_code'):
        mermaid_text = process['mermaid_code'][:500]
        parts.append(f"Mermaid: {mermaid_text}")
    return '\n'.join(parts)

