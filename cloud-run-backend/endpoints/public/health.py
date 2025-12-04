"""Public health and status endpoints"""

from fastapi import APIRouter, HTTPException
from datetime import datetime
from utils.logging import structured_logger
from config.database import db
from utils.api_keys import get_google_api_key, check_vertex_ai_available

# Create router for public endpoints
router = APIRouter()


@router.get("/health")
async def health_check():
    """Health check endpoint for Cloud Run"""
    # Check ElevenLabs API key availability
    try:
        from elevenlabs_voice_service import ElevenLabsVoiceService
        voice_service = ElevenLabsVoiceService()
        elevenlabs_available = bool(voice_service.api_key)
    except Exception as e:
        structured_logger.warning("ElevenLabs check failed", error=str(e))
        elevenlabs_available = False

    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "service": "copernicus-podcast-api",
        "vertex_ai_available": check_vertex_ai_available(),
        "google_api_key_available": bool(get_google_api_key()),
        "elevenlabs_available": elevenlabs_available
    }


@router.get("/test-frontend")
async def test_frontend():
    """Test endpoint for frontend connectivity"""
    return {
        "message": "Frontend connectivity test successful",
        "timestamp": datetime.utcnow().isoformat(),
        "backend_url": "https://copernicus-podcast-api-204731194849.us-central1.run.app"
    }


@router.get("/status/{job_id}")
async def get_job_status(job_id: str):
    """Get status of a podcast generation job"""
    if not db:
        raise HTTPException(status_code=503, detail="Firestore service is unavailable")

    try:
        job_ref = db.collection('podcast_jobs').document(job_id)
        job_doc = job_ref.get()

        if not job_doc.exists:
            raise HTTPException(status_code=404, detail=f"Job '{job_id}' not found in Firestore.")
        
        return job_doc.to_dict()
    except HTTPException:
        raise
    except Exception as e:
        structured_logger.error("Error fetching job from Firestore",
                               job_id=job_id,
                               error=str(e))
        raise HTTPException(status_code=500, detail="Failed to retrieve job status")

