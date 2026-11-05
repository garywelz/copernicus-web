"""Admin endpoints router

Handles all admin-related API endpoints including:
- Subscriber management
- Podcast database operations
- RSS feed management
- Episode management
"""

from fastapi import APIRouter, HTTPException, Depends, Query, Request, Header
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime
from google.cloud import firestore

from utils.logging import structured_logger
from utils.auth import verify_admin_api_key
from config.database import db
from config.constants import EPISODE_COLLECTION_NAME
import asyncio
from datetime import timedelta
import media_store

router = APIRouter()


@router.get("/api/admin/subscribers")
async def list_all_subscribers(admin_auth: bool = Depends(verify_admin_api_key)):
    """List all subscribers with podcast counts"""
    if not db:
        raise HTTPException(status_code=503, detail="Firestore service is unavailable")
    
    try:
        subscribers_ref = db.collection('subscribers')
        subscribers = subscribers_ref.stream()
        
        subscriber_list = []
        for sub_doc in subscribers:
            sub_data = sub_doc.to_dict() or {}
            
            # Calculate actual podcast count dynamically
            subscriber_id = sub_doc.id
            podcast_jobs = db.collection('podcast_jobs').where('subscriber_id', '==', subscriber_id).stream()
            episodes = db.collection(EPISODE_COLLECTION_NAME).where('subscriber_id', '==', subscriber_id).stream()
            
            # Use set to track unique canonical filenames
            unique_podcasts = set()
            for job in podcast_jobs:
                job_data = job.to_dict() or {}
                canonical = (job_data.get('result') or {}).get('canonical_filename')
                if canonical:
                    unique_podcasts.add(canonical)
                else:
                    # Fallback: use job ID if no canonical filename
                    unique_podcasts.add(job.id)
            
            for ep in episodes:
                # Episodes use their document ID as the canonical filename
                unique_podcasts.add(ep.id)
            
            actual_count = len(unique_podcasts)
            
            subscriber_list.append({
                'email': sub_data.get('email', ''),
                'subscriber_id': subscriber_id,
                'display_name': sub_data.get('display_name', ''),
                'initials': sub_data.get('initials', ''),
                'show_attribution': sub_data.get('show_attribution', False),
                'created_at': sub_data.get('created_at', ''),
                'last_login': sub_data.get('last_login', ''),
                'podcast_count': actual_count
            })
        
        return {"subscribers": subscriber_list, "total": len(subscriber_list), "total_count": len(subscriber_list)}
        
    except Exception as e:
        structured_logger.error("Error listing subscribers", error=str(e))
        raise HTTPException(status_code=500, detail="Failed to list subscribers")


@router.get("/api/admin/subscribers/{subscriber_id}/podcasts")
async def admin_get_subscriber_podcasts(
    subscriber_id: str,
    admin_auth: bool = Depends(verify_admin_api_key)
):
    """Get all podcasts for a specific subscriber (admin view)"""
    if not db:
        raise HTTPException(status_code=503, detail="Firestore service is unavailable")
    
    try:
        # Similar logic to subscriber endpoint but admin access
        podcasts_list = []
        podcasts_by_id = {}
        
        # Get from podcast_jobs
        jobs = db.collection('podcast_jobs').where('subscriber_id', '==', subscriber_id).stream()
        for job_doc in jobs:
            job_data = job_doc.to_dict() or {}
            result = job_data.get('result', {})
            canonical = result.get('canonical_filename')
            podcast_id = canonical or job_doc.id
            
            if podcast_id and podcast_id not in podcasts_by_id:
                podcasts_by_id[podcast_id] = {
                    'podcast_id': podcast_id,
                    'title': result.get('title') or job_data.get('request', {}).get('topic', 'Untitled'),
                    'submitted_to_rss': job_data.get('submitted_to_rss', False),
                    'created_at': job_data.get('created_at', ''),
                    'source': 'podcast_jobs'
                }
        
        return {"subscriber_id": subscriber_id, "podcasts": list(podcasts_by_id.values())}
        
    except Exception as e:
        structured_logger.error("Error fetching subscriber podcasts", error=str(e))
        raise HTTPException(status_code=500, detail="Failed to fetch podcasts")


@router.post("/api/admin/podcasts/fix-missing-titles")
async def fix_missing_titles(
    request: Request,
    subscriber_id: Optional[str] = Query(None),
    x_admin_api_key: Optional[str] = Header(None, alias="X-Admin-API-Key"),
    x_subscriber_token: Optional[str] = Header(None, alias="X-Subscriber-Token"),
):
    """Fix missing titles for podcasts.

    Who is fixed comes from the credential, never from an email address in the URL (onboarding PR 1): the admin key may name a `subscriber_id` (the
    opaque id, not an address) or omit it to fix every job; a subscriber session token may fix only that subscriber's own jobs, and `subscriber_id` must be
    the token's owner. An email-shaped value, or the old `subscriber_email` parameter, is refused with 400 before anything is read."""
    if "subscriber_email" in request.query_params or (subscriber_id and "@" in subscriber_id):
        raise HTTPException(status_code=400, detail="Email addresses are not accepted in the URL; use subscriber_id")
    from utils.auth import _admin_key_matches
    if _admin_key_matches(x_admin_api_key):
        scope_id = subscriber_id
    else:
        from utils.subscriber_helpers import verify_session_token
        if not subscriber_id or not x_subscriber_token:
            raise HTTPException(status_code=401, detail="Admin key, or a subscriber_id with a valid X-Subscriber-Token, required")
        if not db:
            raise HTTPException(status_code=503, detail="Firestore service is unavailable")
        sub = db.collection('subscribers').document(subscriber_id).get()
        if not sub.exists or not verify_session_token(sub.to_dict() or {}, x_subscriber_token):
            raise HTTPException(status_code=401, detail="Missing or invalid session token")
        scope_id = subscriber_id
    if not db:
        raise HTTPException(status_code=503, detail="Firestore service is unavailable")

    try:
        fixed_count = 0
        if scope_id:
            jobs = db.collection('podcast_jobs').where('subscriber_id', '==', scope_id).stream()
        else:
            jobs = db.collection('podcast_jobs').stream()

        for job_doc in jobs:
            job_data = job_doc.to_dict() or {}
            result = job_data.get('result', {})

            # Fix title if missing
            if not result.get('title'):
                topic = job_data.get('request', {}).get('topic', 'Untitled')
                result['title'] = topic
                job_data['result'] = result
                job_doc.reference.update({'result': result})
                fixed_count += 1

        return {"fixed_count": fixed_count, "message": f"Fixed {fixed_count} missing titles"}

    except Exception as e:
        structured_logger.error("Error fixing titles", error=str(e))
        raise HTTPException(status_code=500, detail="Failed to fix titles")


@router.get("/api/admin/podcasts/catalog")
async def get_podcast_catalog(admin_auth: bool = Depends(verify_admin_api_key)):
    """Get comprehensive podcast catalog"""
    if not db:
        raise HTTPException(status_code=503, detail="Firestore service is unavailable")
    
    try:
        podcasts = []
        podcasts_by_id = {}
        
        # Get from podcast_jobs
        jobs = db.collection('podcast_jobs').stream()
        for job_doc in jobs:
            job_data = job_doc.to_dict() or {}
            result = job_data.get('result', {})
            canonical = result.get('canonical_filename')
            
            if canonical and canonical not in podcasts_by_id:
                podcasts_by_id[canonical] = {
                    'canonical_filename': canonical,
                    'title': result.get('title') or job_data.get('request', {}).get('topic', 'Untitled'),
                    'submitted_to_rss': job_data.get('submitted_to_rss', False),
                    'created_at': job_data.get('created_at', '')
                }
        
        return {"podcasts": list(podcasts_by_id.values()), "total": len(podcasts_by_id)}
        
    except Exception as e:
        structured_logger.error("Error getting catalog", error=str(e))
        raise HTTPException(status_code=500, detail="Failed to get catalog")


@router.get("/api/admin/podcasts/database")
async def get_podcast_database(admin_auth: bool = Depends(verify_admin_api_key)):
    """Get comprehensive podcast database with all episodes - ordered by newest first"""
    if not db:
        raise HTTPException(status_code=503, detail="Firestore service is unavailable")
    
    try:
        from google.cloud import storage
        from config.constants import EPISODE_BASE_URL
        from urllib.parse import urlparse
        
        podcasts_by_id = {}
        
        # First, get all episodes (ordered by created_at DESCENDING - newest first)
        episodes_query = db.collection(EPISODE_COLLECTION_NAME).order_by('created_at', direction=firestore.Query.DESCENDING).stream()
        
        for episode_doc in episodes_query:
            episode_data = episode_doc.to_dict() or {}
            canonical = episode_doc.id
            
            if canonical and canonical not in podcasts_by_id:
                # Get subscriber info
                subscriber_id = episode_data.get('subscriber_id', '')
                subscriber_email = episode_data.get('subscriber_email', 'Unknown')
                if subscriber_id and subscriber_email == 'Unknown':
                    subscriber_doc = db.collection('subscribers').document(subscriber_id).get()
                    if subscriber_doc.exists:
                        subscriber_email = subscriber_doc.to_dict().get('email', 'Unknown')
                
                # Extract duration
                duration = episode_data.get('duration') or 'Unknown'
                audio_url = episode_data.get('audio_url', '')
                
                # Get file size from GCS if possible
                file_size_display = 'Unknown'
                if audio_url:
                    try:
                        storage_client = storage.Client()
                        bucket_name = 'regal-scholar-453620-r7-podcast-storage'
                        bucket = storage_client.bucket(bucket_name)
                        
                        # Extract blob name from URL
                        parsed_url = urlparse(audio_url)
                        blob_name = parsed_url.path.lstrip('/')
                        if blob_name.startswith(bucket_name + '/'):
                            blob_name = blob_name[len(bucket_name) + 1:]
                        
                        blob = bucket.blob(blob_name)
                        if blob.exists():
                            size_bytes = blob.size or 0
                            if size_bytes > 0:
                                size_mb = size_bytes / (1024 * 1024)
                                file_size_display = f"{size_mb:.1f} MB"
                    except Exception:
                        pass  # Keep as Unknown if we can't get size
                
                # Get created_at (prioritize episode's created_at)
                created_at = episode_data.get('created_at') or episode_data.get('generated_at') or ''
                
                # Get category from episode or extract from canonical
                category = episode_data.get('category', '')
                if not category and canonical:
                    parts = canonical.split('-')
                    if len(parts) >= 2:
                        cat_map = {'bio': 'Biology', 'chem': 'Chemistry', 'compsci': 'Computer Science', 
                                  'math': 'Mathematics', 'phys': 'Physics'}
                        cat_slug = parts[1] if len(parts) > 1 else ''
                        category = cat_map.get(cat_slug, '')
                
                podcasts_by_id[canonical] = {
                    'canonical_filename': canonical,
                    'podcast_id': canonical,  # For compatibility
                    'id': canonical,  # For compatibility
                    'title': episode_data.get('title', 'Untitled'),
                    'subscriber_email': subscriber_email,
                    'subscriber_id': subscriber_id,
                    'duration': duration,
                    'file_size_display': file_size_display,
                    'created_at': created_at,
                    'submitted_to_rss': episode_data.get('submitted_to_rss', False),
                    'in_rss': episode_data.get('submitted_to_rss', False),  # Alias
                    'category': category,
                    'episode_page_url': f"{EPISODE_BASE_URL}/{canonical}",
                    'episode_json_url': f"{EPISODE_BASE_URL}/{canonical}.json",
                    'source': 'episodes'
                }
        
        # Also check podcast_jobs for any missing podcasts (backup)
        jobs_query = db.collection('podcast_jobs').stream()
        for job_doc in jobs_query:
            job_data = job_doc.to_dict() or {}
            result = job_data.get('result', {})
            canonical = result.get('canonical_filename')
            
            if canonical and canonical not in podcasts_by_id:
                # This podcast exists in jobs but not episodes - include it
                subscriber_id = job_data.get('subscriber_id', '')
                subscriber_email = 'Unknown'
                if subscriber_id:
                    subscriber_doc = db.collection('subscribers').document(subscriber_id).get()
                    if subscriber_doc.exists:
                        subscriber_email = subscriber_doc.to_dict().get('email', 'Unknown')
                
                podcasts_by_id[canonical] = {
                    'canonical_filename': canonical,
                    'podcast_id': canonical,
                    'id': canonical,
                    'title': result.get('title') or job_data.get('request', {}).get('topic', 'Untitled'),
                    'subscriber_email': subscriber_email,
                    'subscriber_id': subscriber_id,
                    'duration': result.get('duration') or job_data.get('request', {}).get('duration', 'Unknown'),
                    'file_size_display': 'Unknown',
                    'created_at': job_data.get('created_at') or job_data.get('updated_at') or '',
                    'submitted_to_rss': job_data.get('submitted_to_rss', False),
                    'in_rss': job_data.get('submitted_to_rss', False),
                    'category': job_data.get('request', {}).get('category', ''),
                    'episode_page_url': f"{EPISODE_BASE_URL}/{canonical}",
                    'episode_json_url': f"{EPISODE_BASE_URL}/{canonical}.json",
                    'source': 'podcast_jobs'
                }
        
        # Convert to list and sort by created_at (newest first)
        podcasts_list = list(podcasts_by_id.values())
        
        # Sort with proper date handling - newest podcasts first
        def get_sort_key(podcast):
            timestamp = (
                podcast.get('created_at') or 
                ''
            )
            
            if not timestamp:
                return ''  # Will sort last
            
            if isinstance(timestamp, str):
                timestamp = timestamp.replace('+00:00', '').replace('Z', '')
                return timestamp
            
            if hasattr(timestamp, 'isoformat'):
                return timestamp.isoformat()
            return str(timestamp)
        
        podcasts_list.sort(key=get_sort_key, reverse=True)
        
        structured_logger.info("Podcast database retrieved",
                              total_count=len(podcasts_list),
                              from_episodes=sum(1 for p in podcasts_list if p.get('source') == 'episodes'),
                              from_jobs=sum(1 for p in podcasts_list if p.get('source') == 'podcast_jobs'))
        
        return {
            "podcasts": podcasts_list,
            "total_count": len(podcasts_list)
        }
        
    except Exception as e:
        structured_logger.error("Error getting podcast database", error=str(e))
        raise HTTPException(status_code=500, detail="Failed to get podcast database")


@router.get("/api/admin/episodes/{episode_id}/media-links")
async def episode_media_links(episode_id: str, hours: int = Query(1, ge=1, le=168), admin_auth: bool = Depends(verify_admin_api_key)):
    """Short-lived signed links to a private episode's files (public addresses for files that are already public). For review before publishing."""
    if not db:
        raise HTTPException(status_code=503, detail="Firestore service is unavailable")
    if not db.collection(EPISODE_COLLECTION_NAME).document(episode_id).get().exists:
        raise HTTPException(status_code=404, detail="Episode not found")
    try:
        return await asyncio.to_thread(media_store.signed_links, episode_id, timedelta(hours=hours))
    except Exception as e:
        structured_logger.error("Could not build media links", episode_id=episode_id, error=str(e))
        raise HTTPException(status_code=500, detail="Could not build media links")


class RevoiceRequest(BaseModel):
    expected_script_sha256: str = Field(..., min_length=64, max_length=64)      # the SHA-256 of the script somebody has read; a different stored script is refused


@router.post("/api/admin/episodes/{episode_id}/revoice")
async def revoice_episode(episode_id: str, body: RevoiceRequest, admin_auth: bool = Depends(verify_admin_api_key)):
    """New audio for a PRIVATE episode, from the script stored on its job, through the existing text-to-speech path (audio only: the script, description,
    thumbnail and artwork are not touched). The current audio is kept first under audio/previous/ in the private bucket, and is replaced only after the new
    audio is checked. Refused for a published episode. See episode_revoice.py for the order and every refusal."""
    if not db:
        raise HTTPException(status_code=503, detail="Firestore service is unavailable")
    import sys
    from google.cloud import storage
    import episode_revoice
    from audio_length import mp3_seconds
    main_module = sys.modules.get("main")
    service = getattr(main_module, "podcast_generation_service", None) if main_module else None
    voice_service = getattr(service, "elevenlabs_voice_service", None)
    if voice_service is None:
        raise HTTPException(status_code=503, detail="The voice service is not available")
    try:
        result = await episode_revoice.revoice_private_episode(episode_id, body.expected_script_sha256, db=db, client=storage.Client(),
                                                              voice_service=voice_service, seconds_of=mp3_seconds)
    except episode_revoice.RevoiceError as e:
        structured_logger.warning("Re-voice refused", episode_id=episode_id, status=e.status, reason=e.message)
        raise HTTPException(status_code=e.status, detail=e.message)
    structured_logger.info("Episode re-voiced", episode_id=episode_id, tts_characters=result.get("tts_characters"), new_seconds=result.get("new_seconds"))
    return result


@router.post("/api/admin/episodes/{episode_id}/publish-site")
async def publish_episode_to_site(episode_id: str, admin_auth: bool = Depends(verify_admin_api_key)):
    """Show an episode on the website without putting it in the podcast feed: copy its files to the public bucket (verified), then set visible_on_web."""
    if not db:
        raise HTTPException(status_code=503, detail="Firestore service is unavailable")
    ref = db.collection(EPISODE_COLLECTION_NAME).document(episode_id)
    if not ref.get().exists:
        raise HTTPException(status_code=404, detail="Episode not found")
    try:
        promotion = await asyncio.to_thread(media_store.promote, episode_id)
    except media_store.MediaError as e:
        structured_logger.error("Media promotion failed; episode not published to the site", episode_id=episode_id, error=str(e))
        raise HTTPException(status_code=500, detail="Could not publish the episode's files; nothing was changed")
    try:
        ref.set({"visible_on_web": True, "visibility": "public", "media_state": "public", "updated_at": datetime.utcnow().isoformat()}, merge=True)
    except Exception:
        await asyncio.to_thread(media_store.demote, promotion.get("objects", []))
        raise
    return {"episode_id": episode_id, "visible_on_web": True, "promoted_files": promotion.get("promoted", 0), "already_public": promotion.get("already_public", False)}


class UnpublishRequest(BaseModel):
    reason: str = Field(..., min_length=3, max_length=500)   # why; kept in the audit record


@router.post("/api/admin/episodes/{episode_id}/unpublish")
async def unpublish_episode(episode_id: str, body: UnpublishRequest, admin_auth: bool = Depends(verify_admin_api_key)):
    """Return a PUBLIC episode to private: the inverse of `publish-site` and the only way an episode goes back (an owner cannot).

    Order: (1) refuse if the episode is in the podcast feed (the feed is a separate, editor-controlled step and is not touched here) or if any public
    file has no identical private copy (removing it would destroy the media); (2) clear visible_on_web; (3) remove the public copies; (4) write the audit
    record (episode, actor, time, reason, files removed). The private copies and the feed are never touched. Safe to run again after a partial failure."""
    if not db:
        raise HTTPException(status_code=503, detail="Firestore service is unavailable")
    from utils.owner_access import write_audit
    ref = db.collection(EPISODE_COLLECTION_NAME).document(episode_id)
    snap = ref.get()
    if not snap.exists:
        raise HTTPException(status_code=404, detail="Episode not found")
    record = snap.to_dict() or {}
    if record.get("submitted_to_rss"):
        raise HTTPException(status_code=409, detail="The episode is in the podcast feed. Remove it from the feed first (an editor step); unpublish does not touch the feed")

    was_visible = bool(record.get("visible_on_web"))

    def _flip_record():
        if not was_visible:
            return      # already private: leave the record alone
        ref.set({"visible_on_web": False, "visibility": "private", "media_state": "private", "unpublished_at": datetime.utcnow().isoformat(),
                 "updated_at": datetime.utcnow().isoformat()}, merge=True)

    try:
        result = await asyncio.to_thread(media_store.unpublish, episode_id, None, _flip_record)
    except media_store.MediaError as e:
        structured_logger.error("Unpublish refused; nothing changed", episode_id=episode_id, error_type=type(e).__name__)
        raise HTTPException(status_code=409, detail=str(e))
    if not was_visible and not result["removed"] and not result["failed"]:
        return {"episode_id": episode_id, "visible_on_web": False, "already_private": True, "files_removed": 0, "private_copies_untouched": True, "feed_untouched": True}
    write_audit(db, "unpublish", episode_id, "admin-key", reason=body.reason, files_removed=len(result["removed"]), files_failed=len(result["failed"]))
    if result["failed"]:
        raise HTTPException(status_code=500, detail=f"The episode is hidden, but {len(result['failed'])} public file(s) could not be removed; run unpublish again")
    return {"episode_id": episode_id, "visible_on_web": False, "files_removed": len(result["removed"]), "private_copies_untouched": True, "feed_untouched": True}


class QuotaRequest(BaseModel):
    monthly_quota: Optional[Any] = Field(...)   # required; an integer 0..200, or null for unlimited


@router.get("/api/admin/subscribers/{subscriber_id}/quota")
async def get_subscriber_quota(subscriber_id: str, admin_auth: bool = Depends(verify_admin_api_key)):
    if not db:
        raise HTTPException(status_code=503, detail="Firestore service is unavailable")
    from utils.generation_quota import read_quota
    state = read_quota(db, subscriber_id)
    if state is None:
        raise HTTPException(status_code=404, detail="Subscriber not found")
    return state


@router.put("/api/admin/subscribers/{subscriber_id}/quota")
async def set_subscriber_quota(subscriber_id: str, body: QuotaRequest, admin_auth: bool = Depends(verify_admin_api_key)):
    """Set a subscriber's monthly generation quota: an integer 0..200, or null for unlimited. Audited. Does not change can_generate or the month's count."""
    if not db:
        raise HTTPException(status_code=503, detail="Firestore service is unavailable")
    from utils.generation_quota import set_quota, validate_quota_value
    from utils.owner_access import write_audit
    try:
        value = validate_quota_value(body.monthly_quota)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    changed = set_quota(db, subscriber_id, value)
    if changed is None:
        raise HTTPException(status_code=404, detail="Subscriber not found")
    write_audit(db, "quota_set", None, "admin-key", subscriber_id=subscriber_id, previous=changed["previous"], current=changed["current"])
    return {"subscriber_id": subscriber_id, "monthly_quota": value, "previous": changed["previous"]}
