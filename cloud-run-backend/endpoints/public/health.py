"""Public health and status endpoints"""

from typing import Optional

from fastapi import APIRouter, Header
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
async def get_job_status(
    job_id: str,
    x_admin_api_key: Optional[str] = Header(None, alias="X-Admin-API-Key"),
    x_subscriber_token: Optional[str] = Header(None, alias="X-Subscriber-Token"),
):
    """Status of a podcast generation job. Job-status access tightened (change 8, 2026-11): only the job's owner or the admin key may ask, anyone else gets 404, and
    the answer is the minimal view the owner's dashboard uses (the same one as /api/subscribers/jobs/{job_id}/status), not the stored job document."""
    from endpoints.subscriber.episode_access import job_status_response
    return job_status_response(job_id, x_admin_api_key, x_subscriber_token)
