"""Podcast generation endpoints"""

from fastapi import APIRouter, HTTPException, Query
from typing import Optional
import uuid
from datetime import datetime

from utils.logging import structured_logger
from config.database import db
from models.podcast import PodcastRequest, ResolvePaperRequest, GeneratePodcastFromPaperRequest
from services.paper_resolver import (
    resolve_paper,
    get_paper_by_id,
    paper_abstract_text,
    paper_external_url,
    podcast_category_for_paper,
    is_unambiguous_generation_match,
)

router = APIRouter()


def _get_service():
    """Get podcast generation service from main module"""
    # Lazy import to avoid circular dependencies
    # Service is initialized in main.py before routers are registered
    import sys
    main_module = sys.modules.get('main')
    if main_module:
        return getattr(main_module, 'podcast_generation_service', None)
    return None


@router.post("/generate-podcast")
async def generate_podcast(request: PodcastRequest):
    """Generate a new podcast episode"""
    job_id = str(uuid.uuid4())
    
    # Enhanced logging for research-driven requests
    paper_info = f" + Paper: {request.paper_title[:30]}..." if request.paper_content else ""
    structured_logger.info("New research podcast request", 
                          job_id=job_id,
                          topic=request.topic,
                          duration=request.duration,
                          expertise_level=request.expertise_level,
                          has_paper=bool(request.paper_content))
    
    if not db:
        raise HTTPException(status_code=503, detail="Firestore service is unavailable. Cannot create job.")

    job_data = {
        'job_id': job_id,
        'status': 'pending',
        'created_at': datetime.utcnow().isoformat(),
        'updated_at': datetime.utcnow().isoformat(),
        'request': request.model_dump(),
    }
    
    try:
        db.collection('podcast_jobs').document(job_id).set(job_data)
        structured_logger.info("Job created in Firestore",
                              job_id=job_id,
                              topic=request.topic)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create job in Firestore: {e}")
    
    # Run podcast generation synchronously (not as background task)
    # This fixes the issue where background tasks don't execute in Cloud Run
    try:
        structured_logger.info("Starting synchronous podcast generation", 
                              job_id=job_id,
                              topic=request.topic)
        
        service = _get_service()
        if not service:
            raise HTTPException(status_code=503, detail="Podcast generation service is not available")
        
        await service.run_podcast_generation_job(job_id, request, subscriber_id=None)
        
        # Get final status
        job_doc = db.collection('podcast_jobs').document(job_id).get()
        if job_doc.exists:
            job_data = job_doc.to_dict()
            return {
                "job_id": job_id, 
                "status": job_data.get('status', 'completed'),
                "result": job_data.get('result')
            }
        
        return {"job_id": job_id, "status": "completed"}
        
    except Exception as e:
        structured_logger.error("Podcast generation failed", 
                              job_id=job_id,
                              error=str(e))
        
        # Update job status to failed
        job_ref = db.collection('podcast_jobs').document(job_id)
        job_ref.update({
            'status': 'failed',
            'error': str(e),
            'updated_at': datetime.utcnow().isoformat()
        })
        
        raise HTTPException(status_code=500, detail=f"Podcast generation failed: {str(e)}")


@router.post("/generate-podcast-with-subscriber")
async def generate_podcast_with_subscriber(
    request: PodcastRequest,
    subscriber_id: Optional[str] = Query(None)
):
    """Generate podcast with optional subscriber association"""
    job_id = str(uuid.uuid4())
    
    # Enhanced logging for research-driven requests
    paper_info = f" + Paper: {request.paper_title[:30]}..." if request.paper_content else ""
    subscriber_info = f" (Subscriber: {subscriber_id})" if subscriber_id else " (Anonymous)"
    structured_logger.info("New research podcast request with subscriber",
                          job_id=job_id,
                          topic=request.topic,
                          duration=request.duration,
                          expertise_level=request.expertise_level,
                          has_paper=bool(request.paper_content),
                          subscriber_id=subscriber_id)
    
    if not db:
        raise HTTPException(status_code=503, detail="Firestore service is unavailable. Cannot create job.")

    job_data = {
        'job_id': job_id,
        'status': 'pending',
        'created_at': datetime.utcnow().isoformat(),
        'updated_at': datetime.utcnow().isoformat(),
        'request': request.model_dump(),
        'subscriber_id': subscriber_id,  # Associate with subscriber
        'submitted_to_rss': False,  # Default to not submitted
    }
    
    try:
        db.collection('podcast_jobs').document(job_id).set(job_data)
        structured_logger.info("Job created in Firestore",
                              job_id=job_id,
                              topic=request.topic)
        
        # Update subscriber's podcast count if they're logged in
        if subscriber_id:
            subscriber_doc = db.collection('subscribers').document(subscriber_id).get()
            if subscriber_doc.exists:
                subscriber_data = subscriber_doc.to_dict()
                new_count = subscriber_data.get('podcasts_generated', 0) + 1
                db.collection('subscribers').document(subscriber_id).update({
                    'podcasts_generated': new_count
                })
                structured_logger.info("Updated subscriber podcast count",
                                     subscriber_id=subscriber_id,
                                     new_count=new_count)
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create job in Firestore: {e}")
    
    # Run the same podcast generation logic as the original endpoint
    try:
        structured_logger.info("Starting synchronous podcast generation with subscriber", 
                              job_id=job_id,
                              subscriber_id=subscriber_id,
                              topic=request.topic)
        
        service = _get_service()
        if not service:
            raise HTTPException(status_code=503, detail="Podcast generation service is not available")
        
        await service.run_podcast_generation_job(job_id, request, subscriber_id)
        
        # Get final status
        job_doc = db.collection('podcast_jobs').document(job_id).get()
        if job_doc.exists:
            job_data = job_doc.to_dict()
            return {
                "job_id": job_id, 
                "status": job_data.get('status', 'completed'),
                "result": job_data.get('result'),
                "subscriber_id": subscriber_id
            }
        
        return {"job_id": job_id, "status": "completed", "subscriber_id": subscriber_id}
        
    except Exception as e:
        structured_logger.error("Podcast generation failed",
                              job_id=job_id,
                              subscriber_id=subscriber_id,
                              error=str(e))

        # Update job status to failed
        job_ref = db.collection('podcast_jobs').document(job_id)
        job_ref.update({
            'status': 'failed',
            'error': str(e),
            'updated_at': datetime.utcnow().isoformat()
        })

        raise HTTPException(status_code=500, detail=f"Podcast generation failed: {str(e)}")


def _paper_preview(paper: dict) -> dict:
    """Trim a Firestore paper doc to what a caller needs to pick a candidate,
    without shipping the full abstract/embedding/citations payload."""
    return {
        "paper_id": paper.get("paper_id"),
        "title": paper.get("title"),
        "authors": paper.get("authors"),
        "doi": paper.get("doi"),
        "pmid": paper.get("pmid"),
        "arxiv_id": paper.get("arxiv_id"),
        "abstract_preview": (paper.get("abstract") or "")[:280],
    }


@router.post("/resolve-paper")
async def resolve_paper_endpoint(request: ResolvePaperRequest):
    """Look up a paper in the Knowledge Engine corpus by DOI/PMID/arXiv link,
    bare identifier, title, or free-text description. No side effects --
    preview step before /generate-podcast-from-paper. See
    services/paper_resolver.py for match_type semantics and the known
    scoping limitation on the free-text path."""
    try:
        result = await resolve_paper(
            request.query, cited_project=request.cited_project, limit=request.limit
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    return {
        "match_type": result["match_type"],
        "papers": [_paper_preview(p) for p in result["papers"]],
    }


@router.post("/generate-podcast-from-paper")
async def generate_podcast_from_paper(request: GeneratePodcastFromPaperRequest):
    """Generate a podcast episode from a specific Knowledge Engine paper.
    Requires either `paper_id` (from a prior /resolve-paper call) or a
    `query` that resolves unambiguously as a DOI/PMID/arXiv identifier --
    a free-text query is rejected here on purpose, to avoid ever generating
    an episode about a paper the caller didn't explicitly confirm."""
    if not db:
        raise HTTPException(status_code=503, detail="Firestore service is unavailable. Cannot create job.")

    paper = None
    if request.paper_id:
        paper = get_paper_by_id(request.paper_id)
        if not paper:
            raise HTTPException(status_code=404, detail=f"No paper with id {request.paper_id!r}")
    elif request.query:
        try:
            result = await resolve_paper(request.query, cited_project=request.cited_project)
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))
        if not is_unambiguous_generation_match(result["match_type"], result["papers"]):
            raise HTTPException(
                status_code=400,
                detail=(
                    f"query did not resolve to a single confirmed paper (match_type="
                    f"{result['match_type']!r}, {len(result['papers'])} candidate(s)). "
                    f"Call /resolve-paper first and pass paper_id for the intended candidate."
                ),
            )
        paper = result["papers"][0]
    else:
        raise HTTPException(status_code=400, detail="Must supply paper_id or query.")

    abstract = paper_abstract_text(paper)
    if not abstract:
        raise HTTPException(
            status_code=400,
            detail=(
                "Paper has no abstract in the Knowledge Engine, so the paper-analysis "
                "pipeline cannot run. Pick another paper, or supply paper_content via "
                "/generate-podcast."
            ),
        )

    source_url = paper_external_url(paper)
    category = (request.category or "").strip() or podcast_category_for_paper(
        paper, cited_project=request.cited_project
    )

    podcast_request = PodcastRequest(
        topic=paper.get("title") or "",
        category=category,
        expertise_level=request.expertise_level,
        format_type=request.format_type,
        duration=request.duration,
        voice_style=request.voice_style,
        host_voice_id=request.host_voice_id,
        expert_voice_id=request.expert_voice_id,
        paper_content=abstract,
        paper_title=paper.get("title"),
        paper_authors=paper.get("authors"),
        paper_abstract=abstract,
        paper_doi=paper.get("doi"),
        focus_areas=request.focus_areas,
        include_citations=request.include_citations,
        paradigm_shift_analysis=request.paradigm_shift_analysis,
        source_links=[source_url] if source_url else None,
        additional_instructions=request.additional_instructions,
    )

    job_id = str(uuid.uuid4())
    structured_logger.info(
        "New paper-sourced podcast request",
        job_id=job_id,
        paper_id=paper.get("paper_id"),
        paper_title=(paper.get("title") or "")[:50],
    )

    job_data = {
        "job_id": job_id,
        "status": "pending",
        "created_at": datetime.utcnow().isoformat(),
        "updated_at": datetime.utcnow().isoformat(),
        "request": podcast_request.model_dump(),
        "source_paper_id": paper.get("paper_id"),
    }

    try:
        db.collection("podcast_jobs").document(job_id).set(job_data)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create job in Firestore: {e}")

    try:
        service = _get_service()
        if not service:
            raise HTTPException(status_code=503, detail="Podcast generation service is not available")

        await service.run_podcast_generation_job(job_id, podcast_request, subscriber_id=None)

        job_doc = db.collection("podcast_jobs").document(job_id).get()
        if job_doc.exists:
            job_data = job_doc.to_dict()
            return {
                "job_id": job_id,
                "status": job_data.get("status", "completed"),
                "result": job_data.get("result"),
                "source_paper_id": paper.get("paper_id"),
            }
        return {"job_id": job_id, "status": "completed", "source_paper_id": paper.get("paper_id")}

    except Exception as e:
        structured_logger.error("Paper-sourced podcast generation failed", job_id=job_id, error=str(e))
        db.collection("podcast_jobs").document(job_id).update({
            "status": "failed",
            "error": str(e),
            "updated_at": datetime.utcnow().isoformat(),
        })
        raise HTTPException(status_code=500, detail=f"Podcast generation failed: {str(e)}")
