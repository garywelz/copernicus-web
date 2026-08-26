"""
Content Browser API Endpoints

Provides endpoints for browsing papers, podcasts, and processes.

Copyright (c) 2025 Gary Welz / CopernicusAI
Licensed under MIT License
"""

from fastapi import APIRouter, HTTPException, Query
from typing import Any, Dict, List, Optional
from utils.logging import structured_logger
from config.database import db
from content_browse_filters import (
    PAPER_KEYWORD_SCAN_CAP,
    PAPER_QUESTION_SCAN_CAP,
    VIDEO_SCAN_CAP,
    facet_values,
    paginate,
    paper_matches_discipline,
    paper_matches_keyword,
    video_matches,
    video_question_ids,
)

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
    "math": "atap_graphs",
    "chemistry": "chemistry_processes",
    "physics": "physics_processes",
    "computer_science": "computer_science_processes",
    "biology": "biology_processes",
}


def _paper_item(doc_id: str, paper_data: Dict[str, Any]) -> Dict[str, Any]:
    sources = paper_data.get("sources") or []
    if isinstance(sources, str):
        sources = [sources]
    source = (sources[0] if sources else None) or paper_data.get("source")
    published = paper_data.get("published_at") or paper_data.get("published_date")
    year = None
    if isinstance(published, str) and len(published) >= 4:
        year = published[:4]
    return {
        "id": doc_id,
        "title": paper_data.get("title", "Untitled"),
        "type": "paper",
        "description": paper_data.get("abstract", "")[:200] if paper_data.get("abstract") else "",
        "abstract": paper_data.get("abstract", "") or "",
        "doi": paper_data.get("doi"),
        "pmid": paper_data.get("pmid"),
        "arxiv_id": paper_data.get("arxiv_id"),
        "url": paper_data.get("url"),
        "journal": paper_data.get("journal") or paper_data.get("journal_full"),
        "year": year,
        "source": source,
        "discipline": paper_data.get("discipline"),
        "metadata": {
            "authors": paper_data.get("authors", []),
            "published": published,
            "categories": paper_data.get("categories", []),
            "question_scope_ids": paper_data.get("question_scope_ids") or [],
        },
    }


def _video_item(video_data: Dict[str, Any], doc_id: str) -> Dict[str, Any]:
    return {
        "id": video_data.get("video_id") or doc_id,
        "title": video_data.get("title") or "Untitled",
        "type": "video",
        "description": (video_data.get("description") or "")[:200],
        "url": video_data.get("video_url") or video_data.get("url"),
        "metadata": {
            "youtube_id": video_data.get("source_id")
            if video_data.get("source") == "youtube"
            else video_data.get("youtube_id"),
            "source": video_data.get("source"),
            "channel_name": video_data.get("channel_name"),
            "duration": video_data.get("duration"),
            "disciplines": video_data.get("disciplines") or [],
            "question_scope_ids": video_question_ids(video_data),
        },
    }


@router.get("/browse")
async def browse_content(
    content_type: str = Query(..., description="Content type: papers, podcasts, processes, or videos"),
    process_family: Optional[str] = Query(
        None,
        description="For processes: glmp, math, chemistry, physics, computer_science, biology (default glmp)",
    ),
    discipline: Optional[str] = Query(
        None,
        description="Papers or videos: biology, mathematics, physics, chemistry, computer_science, interdisciplinary",
    ),
    question: Optional[str] = Query(
        None,
        description="Declared question id (e.g. glmp-q1, atap-q2). Papers: question_scope_ids. Videos: metadata.question_scope_ids.",
    ),
    keyword: Optional[str] = Query(
        None,
        description="Literal substring filter on title/description (not vector search).",
    ),
    channel: Optional[str] = Query(
        None,
        description="Videos only: exact channel_name.",
    ),
    page: int = Query(1, ge=1, description="Page number"),
    limit: int = Query(20, ge=1, le=100, description="Items per page")
):
    """
    Browse content by type with pagination.

    Optional catalog filters (keyword / question / video channel) slice the
    inventory. They are not semantic search — use /api/vector-search for that.
    """
    try:
        if not db:
            raise HTTPException(status_code=503, detail="Database not available")
        
        items = []
        total = 0
        facets = None
        note = None
        qid = (question or "").strip() or None
        kw = (keyword or "").strip() or None
        chan = (channel or "").strip() or None
        
        if content_type == "papers":
            papers_ref = db.collection('research_papers')
            disc = (discipline or "").strip().lower() or None
            from google.cloud.firestore_v1.base_query import FieldFilter
            from google.cloud import firestore as _fs

            if qid and not kw and not disc:
                scoped = papers_ref.where(
                    filter=FieldFilter("question_scope_ids", "array_contains", qid)
                )
                try:
                    total = _extract_count_value(scoped.count().get())
                except Exception as e:
                    structured_logger.warning("Failed to count question-scoped papers", error=str(e))
                    total = 0
                try:
                    query = scoped.order_by(
                        "__name__", direction=_fs.Query.ASCENDING
                    ).limit(limit).offset((page - 1) * limit)
                    for paper in query.stream():
                        items.append(_paper_item(paper.id, paper.to_dict() or {}))
                except Exception as e:
                    structured_logger.warning(
                        "Question browse pagination failed; falling back to scan",
                        error=str(e),
                    )
                    scanned = []
                    for i, paper in enumerate(scoped.stream()):
                        if i >= PAPER_QUESTION_SCAN_CAP:
                            note = (
                                f"Question slice truncated at {PAPER_QUESTION_SCAN_CAP} documents."
                            )
                            break
                        data = paper.to_dict() or {}
                        data.pop("embedding", None)
                        scanned.append((paper.id, data))
                    page_rows, total = paginate(scanned, page, limit)
                    items = [_paper_item(doc_id, data) for doc_id, data in page_rows]
            elif qid or kw:
                scanned = []
                scan_capped = False
                if qid:
                    scoped = papers_ref.where(
                        filter=FieldFilter("question_scope_ids", "array_contains", qid)
                    )
                    for i, paper in enumerate(scoped.stream()):
                        if i >= PAPER_KEYWORD_SCAN_CAP:
                            scan_capped = True
                            break
                        data = paper.to_dict() or {}
                        data.pop("embedding", None)
                        scanned.append((paper.id, data))
                    if scan_capped:
                        note = (
                            f"Question + extra filters scanned {PAPER_KEYWORD_SCAN_CAP} "
                            "papers in this question, not necessarily the full slice."
                        )
                else:
                    filtered_ref = papers_ref
                    if disc:
                        filtered_ref = papers_ref.where(
                            filter=FieldFilter("discipline", "==", disc)
                        )
                        query = filtered_ref.order_by(
                            "__name__", direction=_fs.Query.ASCENDING
                        ).limit(PAPER_KEYWORD_SCAN_CAP)
                    else:
                        query = papers_ref.order_by(
                            "updated_at", direction=_fs.Query.DESCENDING
                        ).order_by(
                            "__name__", direction=_fs.Query.ASCENDING
                        ).limit(PAPER_KEYWORD_SCAN_CAP)
                    for paper in query.stream():
                        data = paper.to_dict() or {}
                        data.pop("embedding", None)
                        scanned.append((paper.id, data))
                    note = (
                        f"Keyword without a question searches {PAPER_KEYWORD_SCAN_CAP} papers"
                        + (" in this discipline" if disc else " (most recently updated)")
                        + ", not the full corpus. Pick a question for a complete slice."
                    )

                matched = []
                for doc_id, data in scanned:
                    if qid and disc and not paper_matches_discipline(data, disc):
                        continue
                    if kw and not paper_matches_keyword(data, kw):
                        continue
                    matched.append((doc_id, data))
                matched.sort(key=lambda pair: (pair[1].get("title") or "").lower())
                page_rows, total = paginate(matched, page, limit)
                items = [_paper_item(doc_id, data) for doc_id, data in page_rows]
            else:
                filtered_ref = papers_ref
                if disc:
                    filtered_ref = papers_ref.where(filter=FieldFilter('discipline', '==', disc))
                try:
                    count_result = filtered_ref.count().get()
                    total = _extract_count_value(count_result)
                except Exception as e:
                    structured_logger.warning("Failed to count papers", error=str(e))
                    total = 0

                if disc:
                    query = filtered_ref.order_by(
                        '__name__', direction=_fs.Query.ASCENDING
                    ).limit(limit).offset((page - 1) * limit)
                else:
                    query = papers_ref.order_by(
                        'updated_at', direction=_fs.Query.DESCENDING
                    ).order_by(
                        '__name__', direction=_fs.Query.ASCENDING
                    ).limit(limit).offset((page - 1) * limit)
                for paper in query.stream():
                    items.append(_paper_item(paper.id, paper.to_dict() or {}))
        
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
                        'published': podcast_data.get('published_date'),
                        'slug': podcast_data.get('slug') or podcast.id,
                        'episode_link': podcast_data.get('episode_link'),
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
                        "processType": process_data.get("processType") or process_data.get("process_type"),
                    },
                })

        elif content_type == "videos":
            videos_ref = db.collection("science_videos")
            scanned_videos: List[Dict[str, Any]] = []
            video_disc = (discipline or "").strip().lower() or None
            for i, video in enumerate(videos_ref.stream()):
                if i >= VIDEO_SCAN_CAP:
                    note = f"Video catalog truncated at {VIDEO_SCAN_CAP} documents."
                    break
                video_data = video.to_dict() or {}
                video_data.pop("embedding", None)
                video_data.pop("transcript", None)
                video_data["_doc_id"] = video.id
                scanned_videos.append(video_data)

            facets = facet_values(
                scanned_videos,
                discipline=video_disc,
                channel=chan,
                question=qid,
                keyword=kw,
            )
            matched_videos = [
                d
                for d in scanned_videos
                if video_matches(
                    d,
                    discipline=video_disc,
                    channel=chan,
                    question=qid,
                    keyword=kw,
                )
            ]
            matched_videos.sort(key=lambda d: (d.get("title") or "").lower())
            page_rows, total = paginate(matched_videos, page, limit)
            items = [_video_item(d, d.get("_doc_id") or "") for d in page_rows]

        else:
            raise HTTPException(
                status_code=400,
                detail="Invalid content_type. Use: papers, podcasts, processes, videos",
            )
        
        payload = {
            'content_type': content_type,
            'items': items,
            'pagination': {
                'page': page,
                'limit': limit,
                'total': total,
                'pages': (total + limit - 1) // limit if total > 0 else 0
            }
        }
        if facets is not None:
            payload['facets'] = facets
        if note:
            payload['note'] = note
        return payload
    
    except HTTPException:
        raise
    except Exception as e:
        structured_logger.error(f"Content browse error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to browse content: {str(e)}")

