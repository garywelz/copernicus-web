"""Debug endpoints for development and testing"""

from fastapi import APIRouter, Depends, HTTPException
from datetime import datetime, timedelta
import asyncio
import uuid
from typing import Optional
from pydantic import BaseModel

from utils.logging import structured_logger
from utils.auth import verify_admin_api_key
from utils.step_tracking import with_step
from config.database import db

# Import the PodcastRequest model and functions we need
# TODO: Move these to appropriate service modules later
from main import PodcastRequest, generate_research_driven_content

router = APIRouter()


@router.post("/debug/run-content")
async def debug_content_generation(
    request: PodcastRequest,
    admin_auth: bool = Depends(verify_admin_api_key)
):
    """Debug endpoint to test content generation in isolation (Admin only)"""
    job_id = f"debug-{uuid.uuid4()}"
    
    structured_logger.info("Debug content generation started", 
                          job_id=job_id,
                          topic=request.topic,
                          category=request.category,
                          duration=request.duration)
    
    try:
        async with with_step("debug_content_generation", job_id, 
                           topic=request.topic, category=request.category):
            
            # Test content generation with timeout and detailed logging
            structured_logger.info("Calling generate_research_driven_content", 
                                  job_id=job_id)
            
            content = await asyncio.wait_for(
                generate_research_driven_content(request),
                timeout=300  # 5 minute timeout
            )
            
            structured_logger.info("Content generation completed", 
                                  job_id=job_id,
                                  content_keys=list(content.keys()) if isinstance(content, dict) else "not_dict",
                                  content_length=len(str(content)) if content else 0)
            
            return {
                "job_id": job_id,
                "status": "success",
                "content": content,
                "timestamp": datetime.utcnow().isoformat()
            }
            
    except asyncio.TimeoutError:
        structured_logger.error("Content generation timed out", 
                               job_id=job_id,
                               timeout_seconds=300)
        return {
            "job_id": job_id,
            "status": "timeout",
            "error": "Content generation timed out after 5 minutes",
            "timestamp": datetime.utcnow().isoformat()
        }
    except Exception as e:
        structured_logger.error("Content generation failed", 
                               job_id=job_id,
                               error=str(e),
                               error_type=type(e).__name__)
        return {
            "job_id": job_id,
            "status": "error",
            "error": str(e),
            "error_type": type(e).__name__,
            "timestamp": datetime.utcnow().isoformat()
        }


@router.post("/debug/watchdog")
async def debug_watchdog(admin_auth: bool = Depends(verify_admin_api_key)):
    """Watchdog endpoint to check for stuck jobs and mark them as failed (Admin only)"""
    try:
        if not db:
            return {"status": "error", "message": "Firestore not available"}
        
        # Find jobs stuck in generating_content for more than 15 minutes
        cutoff_time = datetime.utcnow() - timedelta(minutes=15)
        
        stuck_jobs = db.collection('podcast_jobs').where(
            'status', '==', 'generating_content'
        ).where(
            'updated_at', '<', cutoff_time.isoformat()
        ).get()
        
        results = []
        for job in stuck_jobs:
            job_id = job.id
            job_data = job.to_dict()
            
            structured_logger.warning("Found stuck job, marking as failed", 
                                     job_id=job_id,
                                     status=job_data.get('status'),
                                     updated_at=job_data.get('updated_at'))
            
            # Mark job as failed
            db.collection('podcast_jobs').document(job_id).update({
                'status': 'failed',
                'error': 'Job stuck in generating_content for more than 15 minutes - marked as failed by watchdog',
                'error_code': 'WATCHDOG_TIMEOUT',
                'updated_at': datetime.utcnow().isoformat()
            })
            
            results.append({
                "job_id": job_id,
                "previous_status": job_data.get('status'),
                "updated_at": job_data.get('updated_at'),
                "action": "marked_failed"
            })
        
        return {
            "status": "success",
            "stuck_jobs_found": len(results),
            "jobs": results,
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        structured_logger.error("Watchdog failed", error=str(e))
        return {"status": "error", "message": str(e)}

