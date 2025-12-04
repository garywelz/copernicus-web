"""Podcast generation endpoints"""

from fastapi import APIRouter, HTTPException, Query
from typing import Optional
import uuid
from datetime import datetime

from utils.logging import structured_logger
from config.database import db
from models.podcast import PodcastRequest

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
