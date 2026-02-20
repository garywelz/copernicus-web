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


@router.get("/browse")
async def browse_content(
    content_type: str = Query(..., description="Content type: papers, podcasts, or processes"),
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
            
            # Prefer a stable "newest-ish" ordering so newly ingested content appears early.
            # Fall back to title ordering if updated_at is missing/unindexed.
            try:
                from google.cloud import firestore  # type: ignore
                query = papers_ref.order_by('updated_at', direction=firestore.Query.DESCENDING)
            except Exception:
                query = papers_ref.order_by('title')
            query = query.limit(limit).offset((page - 1) * limit)
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
            # Get GLMP processes from Firestore
            processes_ref = db.collection('glmp_processes')
            try:
                count_result = processes_ref.count().get()
                total = _extract_count_value(count_result)
            except Exception as e:
                structured_logger.warning("Failed to count processes", error=str(e))
                total = 0
            
            query = processes_ref.order_by('name').limit(limit).offset((page - 1) * limit)
            processes = query.stream()
            
            for process in processes:
                process_data = process.to_dict()
                items.append({
                    'id': process.id,
                    'title': process_data.get('name', 'Untitled'),
                    'type': 'process',
                    'description': process_data.get('description', '')[:200] if process_data.get('description') else '',
                    'metadata': {
                        'discipline': process_data.get('discipline'),
                        'category': process_data.get('category')
                    }
                })
        
        else:
            raise HTTPException(status_code=400, detail=f"Invalid content type: {content_type}. Must be papers, podcasts, or processes")
        
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

