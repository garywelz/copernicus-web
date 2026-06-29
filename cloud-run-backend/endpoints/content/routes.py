"""
Content Browser API Endpoints

Provides endpoints for browsing papers, podcasts, and processes.

Copyright (c) 2025 Gary Welz / CopernicusAI
Licensed under MIT License
"""

from fastapi import APIRouter, HTTPException, Query
from typing import Optional
from utils.logging import structured_logger
from config.database import db

router = APIRouter(prefix="/api/content", tags=["content"])

def _extract_count_value(count_result) -> int:
    """
    Firestore aggregation count() result shape can be nested:
    QueryResultsList([ [Aggregation(...)] ])
    """
    try:
        if not count_result:
            return 0
        first = count_result[0]
        # Common: first is a list of Aggregation objects
        if isinstance(first, list) and first:
            agg = first[0]
            v = getattr(agg, "value", None)
            return int(v) if v is not None else 0
        # Sometimes first itself may be an Aggregation
        v = getattr(first, "value", None)
        return int(v) if v is not None else 0
    except Exception:
        return 0


@router.get("/stats")
async def content_stats():
    """
    Public totals plus how many `research_papers` documents have a text embedding
    (uses `embedding_model` set by the auto-embedding pipeline; see utils/auto_embedding.py).
    """
    if not db:
        raise HTTPException(status_code=503, detail="Database not available")

    papers_ref = db.collection("research_papers")
    try:
        count_result = papers_ref.count().get()
        papers_total = _extract_count_value(count_result)
    except Exception as e:
        structured_logger.warning("content_stats: failed total count", error=str(e))
        papers_total = 0

    papers_with_embedding = 0
    count_note = None
    try:
        from google.cloud.firestore_v1.base_query import FieldFilter  # type: ignore

        # String field written whenever Vector(embedding) is stored (avoids vector inequality quirks).
        q = papers_ref.where(filter=FieldFilter("embedding_model", ">", ""))
        emb_res = q.count().get()
        papers_with_embedding = _extract_count_value(emb_res)
    except Exception as e:
        count_note = (
            "Could not count papers with embeddings (index or permissions). "
            f"Error: {str(e)[:200]}"
        )
        structured_logger.warning("content_stats: embedding count failed", error=str(e))

    coverage = None
    if papers_total and papers_with_embedding is not None:
        try:
            coverage = round(100.0 * float(papers_with_embedding) / float(papers_total), 2)
        except Exception:
            coverage = None

    return {
        "papers_total": papers_total,
        "papers_with_embedding": papers_with_embedding,
        "papers_embedding_coverage_percent": coverage,
        "count_method": "Documents with non-empty embedding_model in research_papers (see auto_embedding).",
        "note": count_note,
    }


PROCESS_FAMILY_COLLECTIONS = {
    "glmp": "glmp_processes",
    "math": "math_processes",
    "chemistry": "chemistry_processes",
    "physics": "physics_processes",
    "computer_science": "computer_science_processes",
    "biology": "biology_processes",
}


@router.get("/browse")
async def browse_content(
    content_type: str = Query(..., description="Content type: papers, podcasts, processes, or videos"),
    process_family: Optional[str] = Query(
        None,
        description="For processes: glmp, math, chemistry, physics, computer_science, biology (default glmp)",
    ),
    page: int = Query(1, ge=1, description="Page number"),
    limit: int = Query(20, ge=1, le=100, description="Items per page")
):
    """
    Browse content by type with pagination.
    """
    try:
        if not db:
            raise HTTPException(status_code=503, detail="Database not available")
        
        items = []
        total = 0
        
        if content_type == "papers":
            # Get papers from Firestore
            papers_ref = db.collection('research_papers')
            # Get total count (approximate for performance)
            try:
                count_result = papers_ref.count().get()
                total = _extract_count_value(count_result)
            except Exception as e:
                # Fallback: estimate from query
                structured_logger.warning("Failed to count papers", error=str(e))
                total = 0
            
            from google.cloud import firestore as _fs
            query = papers_ref.order_by(
                'updated_at', direction=_fs.Query.DESCENDING
            ).order_by(
                '__name__', direction=_fs.Query.ASCENDING
            ).limit(limit).offset((page - 1) * limit)
            papers = query.stream()
            
            for paper in papers:
                paper_data = paper.to_dict()
                sources = paper_data.get('sources') or []
                if isinstance(sources, str):
                    sources = [sources]
                source = (sources[0] if sources else None) or paper_data.get('source')
                published = paper_data.get('published_at') or paper_data.get('published_date')
                year = None
                if isinstance(published, str) and len(published) >= 4:
                    year = published[:4]
                items.append({
                    'id': paper.id,
                    'title': paper_data.get('title', 'Untitled'),
                    'type': 'paper',
                    'description': paper_data.get('abstract', '')[:200] if paper_data.get('abstract') else '',
                    # Extra fields for static table UIs (papers-database-table.html)
                    'abstract': paper_data.get('abstract', '') or '',
                    'doi': paper_data.get('doi'),
                    'pmid': paper_data.get('pmid'),
                    'arxiv_id': paper_data.get('arxiv_id'),
                    'url': paper_data.get('url'),
                    'journal': paper_data.get('journal') or paper_data.get('journal_full'),
                    'year': year,
                    'source': source,
                    'discipline': paper_data.get('discipline'),
                    'metadata': {
                        'authors': paper_data.get('authors', []),
                        'published': published,
                        'categories': paper_data.get('categories', [])
                    }
                })
        
        elif content_type == "podcasts":
            # Get podcasts from Firestore
            podcasts_ref = db.collection('episodes')
            try:
                count_result = podcasts_ref.count().get()
                total = _extract_count_value(count_result)
            except Exception as e:
                structured_logger.warning("Failed to count podcasts", error=str(e))
                total = 0
            
            # Avoid composite-index requirements in the public browse endpoint.
            # If we later want filtering (e.g. submitted_to_rss), we can add an index or a separate endpoint.
            query = podcasts_ref.order_by('title').limit(limit).offset((page - 1) * limit)
            podcasts = query.stream()
            
            for podcast in podcasts:
                podcast_data = podcast.to_dict()
                items.append({
                    'id': podcast.id,
                    'title': podcast_data.get('title', 'Untitled'),
                    'type': 'podcast',
                    'description': podcast_data.get('description', '')[:200] if podcast_data.get('description') else '',
                    'metadata': {
                        'duration': podcast_data.get('duration'),
                        'category': podcast_data.get('category'),
                        'published': podcast_data.get('published_date')
                    }
                })
        
        elif content_type == "processes":
            family = (process_family or "glmp").strip().lower()
            collection = PROCESS_FAMILY_COLLECTIONS.get(family)
            if not collection:
                raise HTTPException(
                    status_code=400,
                    detail=f"Invalid process_family: {family}. Use: {', '.join(PROCESS_FAMILY_COLLECTIONS)}",
                )
            processes_ref = db.collection(collection)
            try:
                count_result = processes_ref.count().get()
                total = _extract_count_value(count_result)
            except Exception as e:
                structured_logger.warning("Failed to count processes", error=str(e))
                total = 0

            try:
                from google.cloud import firestore  # type: ignore
                query = processes_ref.order_by("name", direction=firestore.Query.ASCENDING)
            except Exception:
                query = processes_ref.order_by("title")
            query = query.limit(limit).offset((page - 1) * limit)

            for process in query.stream():
                process_data = process.to_dict() or {}
                title = process_data.get("name") or process_data.get("title") or "Untitled"
                items.append({
                    "id": process.id,
                    "title": title,
                    "type": "process",
                    "description": (process_data.get("description") or "")[:200],
                    "metadata": {
                        "process_family": family,
                        "category": process_data.get("category"),
                        "subcategory": process_data.get("subcategory"),
                    },
                })

        elif content_type == "videos":
            raise HTTPException(
                status_code=501,
                detail="Video browse uses GCS catalog: videos-catalog.json (753 videos). Firestore sync pending.",
            )

        else:
            raise HTTPException(
                status_code=400,
                detail="Invalid content_type. Use: papers, podcasts, processes, videos",
            )
        
        return {
            'content_type': content_type,
            'items': items,
            'pagination': {
                'page': page,
                'limit': limit,
                'total': total,
                'pages': (total + limit - 1) // limit if total > 0 else 0
            }
        }
    
    except HTTPException:
        raise
    except Exception as e:
        structured_logger.error(f"Content browse error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to browse content: {str(e)}")

