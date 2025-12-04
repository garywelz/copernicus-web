"""
Admin Endpoints Router

All admin-related API endpoints organized by domain:
- Subscriber management
- Podcast database operations
- RSS feed management
- Episode management
"""

from fastapi import APIRouter, HTTPException, Depends, Query, Header
from typing import Optional

from utils.auth import verify_admin_api_key
from utils.logging import structured_logger
from config.database import db
from config.constants import EPISODE_COLLECTION_NAME, RSS_BUCKET_NAME, RSS_FEED_BLOB_NAME, DEFAULT_ARTWORK_URL
from services.rss_service import rss_service
from services.episode_service import episode_service

router = APIRouter(prefix="/api/admin", tags=["admin"])

# ============================================================================
# SUBSCRIBER MANAGEMENT ENDPOINTS
# ============================================================================

@router.get("/subscribers")
async def list_all_subscribers(admin_auth: bool = Depends(verify_admin_api_key)):
    """List all registered subscribers - Admin endpoint"""
    if not db:
        raise HTTPException(status_code=503, detail="Firestore service is unavailable")
    
    try:
        from datetime import datetime
        subscribers_list = []
        
        subscribers_ref = db.collection('subscribers')
        subscribers = subscribers_ref.stream()
        
        for subscriber_doc in subscribers:
            subscriber_data = subscriber_doc.to_dict() or {}
            subscriber_id = subscriber_doc.id
            
            # Dynamically calculate podcast count
            podcast_count = 0
            try:
                # Count from podcast_jobs
                jobs_query = db.collection('podcast_jobs').where('subscriber_id', '==', subscriber_id).stream()
                jobs_count = len(list(jobs_query))
                
                # Count from episodes
                episodes_query = db.collection(EPISODE_COLLECTION_NAME).where('subscriber_id', '==', subscriber_id).stream()
                episodes_count = len(list(episodes_query))
                
                # Use the maximum (they should match, but this handles edge cases)
                podcast_count = max(jobs_count, episodes_count)
            except Exception as e:
                structured_logger.warning("Could not calculate podcast count for subscriber",
                                         subscriber_id=subscriber_id,
                                         error=str(e))
            
            subscribers_list.append({
                'subscriber_id': subscriber_id,
                'email': subscriber_data.get('email', 'N/A'),
                'name': subscriber_data.get('name'),
                'podcasts_generated': podcast_count,
                'created_at': subscriber_data.get('created_at'),
                'last_login': subscriber_data.get('last_login')
            })
        
        structured_logger.info("Listed all subscribers",
                              total_count=len(subscribers_list))
        
        return {
            "subscribers": subscribers_list,
            "total_count": len(subscribers_list)
        }
        
    except Exception as e:
        structured_logger.error("Failed to list subscribers",
                               error=str(e),
                               error_type=type(e).__name__)
        raise HTTPException(status_code=500, detail=f"Failed to list subscribers: {str(e)}")

@router.get("/subscribers/{subscriber_id}/podcasts")
async def admin_get_subscriber_podcasts(
    subscriber_id: str,
    admin_auth: bool = Depends(verify_admin_api_key)
):
    """Get all podcasts for a specific subscriber - Admin endpoint"""
    if not db:
        raise HTTPException(status_code=503, detail="Firestore service is unavailable")
    
    try:
        podcasts_list = []
        
        # Get podcasts from episodes collection (filtered by subscriber_id)
        episodes_query = db.collection(EPISODE_COLLECTION_NAME).where('subscriber_id', '==', subscriber_id).stream()
        
        for episode_doc in episodes_query:
            episode_data = episode_doc.to_dict() or {}
            canonical = episode_doc.id
            
            podcasts_list.append({
                'canonical_filename': canonical,
                'title': episode_data.get('title', 'Untitled'),
                'topic': episode_data.get('topic', ''),
                'category': episode_data.get('category', ''),
                'subscriber_id': subscriber_id,
                'submitted_to_rss': episode_data.get('submitted_to_rss', False),
                'created_at': episode_data.get('created_at') or episode_data.get('generated_at'),
                'audio_url': episode_data.get('audio_url'),
                'thumbnail_url': episode_data.get('thumbnail_url')
            })
        
        # Sort by created_at descending
        podcasts_list.sort(key=lambda x: x.get('created_at', ''), reverse=True)
        
        structured_logger.info("Retrieved subscriber podcasts",
                              subscriber_id=subscriber_id,
                              podcast_count=len(podcasts_list))
        
        return {
            "subscriber_id": subscriber_id,
            "podcasts": podcasts_list,
            "total_count": len(podcasts_list)
        }
        
    except Exception as e:
        structured_logger.error("Failed to get subscriber podcasts",
                               subscriber_id=subscriber_id,
                               error=str(e),
                               error_type=type(e).__name__)
        raise HTTPException(status_code=500, detail=f"Failed to get subscriber podcasts: {str(e)}")

@router.delete("/subscribers/{subscriber_id}")
async def delete_subscriber(
    subscriber_id: str,
    admin_auth: bool = Depends(verify_admin_api_key)
):
    """Delete a subscriber account - Admin endpoint"""
    if not db:
        raise HTTPException(status_code=503, detail="Firestore service is unavailable")
    
    try:
        subscriber_ref = db.collection('subscribers').document(subscriber_id)
        subscriber_doc = subscriber_ref.get()
        
        if not subscriber_doc.exists:
            raise HTTPException(status_code=404, detail=f"Subscriber not found: {subscriber_id}")
        
        subscriber_data = subscriber_doc.to_dict() or {}
        email = subscriber_data.get('email', subscriber_id)
        
        # Delete subscriber document
        subscriber_ref.delete()
        
        structured_logger.info("Deleted subscriber account",
                              subscriber_id=subscriber_id,
                              email=email)
        
        return {
            "message": f"Subscriber {email} deleted successfully",
            "subscriber_id": subscriber_id
        }
        
    except HTTPException:
        raise
    except Exception as e:
        structured_logger.error("Failed to delete subscriber",
                               subscriber_id=subscriber_id,
                               error=str(e),
                               error_type=type(e).__name__)
        raise HTTPException(status_code=500, detail=f"Failed to delete subscriber: {str(e)}")

# ============================================================================
# PODCAST DATABASE OPERATIONS
# ============================================================================

@router.get("/podcasts")
async def admin_get_all_podcasts(admin_auth: bool = Depends(verify_admin_api_key)):
    """Get all podcasts with RSS status - Admin endpoint"""
    if not db:
        raise HTTPException(status_code=503, detail="Firestore service is unavailable")
    
    try:
        podcasts_list = []
        
        # Get all episodes
        episodes = db.collection(EPISODE_COLLECTION_NAME).stream()
        for episode_doc in episodes:
            episode_data = episode_doc.to_dict() or {}
            canonical = episode_doc.id
            
            podcasts_list.append({
                'canonical_filename': canonical,
                'title': episode_data.get('title', 'Untitled'),
                'topic': episode_data.get('topic', ''),
                'category': episode_data.get('category', ''),
                'subscriber_id': episode_data.get('subscriber_id'),
                'submitted_to_rss': episode_data.get('submitted_to_rss', False),
                'created_at': episode_data.get('created_at') or episode_data.get('generated_at'),
                'audio_url': episode_data.get('audio_url'),
                'thumbnail_url': episode_data.get('thumbnail_url')
            })
        
        # Sort by created_at descending
        podcasts_list.sort(key=lambda x: x.get('created_at', ''), reverse=True)
        
        structured_logger.info("Retrieved all podcasts",
                              total_count=len(podcasts_list))
        
        return {
            "podcasts": podcasts_list,
            "total_count": len(podcasts_list)
        }
        
    except Exception as e:
        structured_logger.error("Failed to get all podcasts",
                               error=str(e),
                               error_type=type(e).__name__)
        raise HTTPException(status_code=500, detail=f"Failed to get all podcasts: {str(e)}")

@router.get("/podcasts/missing-canonical")
async def list_podcasts_missing_canonical(admin_auth: bool = Depends(verify_admin_api_key)):
    """List podcasts that are missing canonical filenames - Admin endpoint"""
    if not db:
        raise HTTPException(status_code=503, detail="Firestore service is unavailable")
    
    try:
        import re
        
        # Pattern for canonical filenames: ever-{category}-{6 digits} or news-{category}-{YYYYMMDD}-{4 digits}
        canonical_pattern = re.compile(r'^(ever|news)-(bio|chem|compsci|math|phys)-\d{6}(-\d{4})?$')
        
        missing_canonical = []
        
        # Check podcast_jobs collection
        podcast_jobs = db.collection('podcast_jobs').stream()
        for job_doc in podcast_jobs:
            job_data = job_doc.to_dict() or {}
            result = job_data.get('result', {})
            canonical = result.get('canonical_filename')
            job_id = job_doc.id
            
            # Check if canonical filename is missing or doesn't match pattern
            is_canonical = False
            if canonical:
                is_canonical = bool(canonical_pattern.match(canonical))
            
            if not is_canonical:
                missing_canonical.append({
                    'job_id': job_id,
                    'current_identifier': canonical or job_id,
                    'title': result.get('title', 'Untitled'),
                    'topic': job_data.get('request', {}).get('topic', ''),
                    'category': job_data.get('request', {}).get('category', ''),
                    'format_type': job_data.get('request', {}).get('format_type', 'feature'),
                    'status': job_data.get('status', 'unknown'),
                    'created_at': job_data.get('created_at')
                })
        
        # Check episodes collection
        episodes = db.collection(EPISODE_COLLECTION_NAME).stream()
        for episode_doc in episodes:
            episode_data = episode_doc.to_dict() or {}
            canonical = episode_doc.id
            
            # Check if canonical filename matches pattern
            is_canonical = bool(canonical_pattern.match(canonical))
            
            if not is_canonical:
                # Check if already in missing list
                if not any(m.get('canonical_filename') == canonical for m in missing_canonical):
                    missing_canonical.append({
                        'canonical_filename': canonical,
                        'current_identifier': canonical,
                        'title': episode_data.get('title', 'Untitled'),
                        'topic': episode_data.get('topic', ''),
                        'category': episode_data.get('category', ''),
                        'format_type': episode_data.get('format_type', 'feature'),
                        'created_at': episode_data.get('created_at') or episode_data.get('generated_at')
                    })
        
        structured_logger.info("Listed podcasts missing canonical filenames",
                              missing_count=len(missing_canonical))
        
        return {
            "podcasts_missing_canonical": missing_canonical,
            "total_count": len(missing_canonical)
        }
        
    except Exception as e:
        structured_logger.error("Failed to list podcasts missing canonical filenames",
                               error=str(e),
                               error_type=type(e).__name__)
        raise HTTPException(status_code=500, detail=f"Failed to list podcasts: {str(e)}")

@router.get("/podcasts/database")
async def get_podcast_database(
    subscriber_email: Optional[str] = Query(None, description="Filter by subscriber email"),
    admin_auth: bool = Depends(verify_admin_api_key)
):
    """Get comprehensive podcast database table - Admin endpoint
    
    Optional query parameter:
    - subscriber_email: Filter podcasts by subscriber email
    """
    if not db:
        raise HTTPException(status_code=503, detail="Firestore service is unavailable")
    
    try:
        podcasts_list = []
        subscriber_id = None
        
        # If subscriber_email provided, find subscriber_id
        if subscriber_email:
            subscribers_query = db.collection('subscribers').where('email', '==', subscriber_email).limit(1).stream()
            for sub_doc in subscribers_query:
                subscriber_id = sub_doc.id
                break
            
            if not subscriber_id:
                return {
                    "podcasts": [],
                    "total_count": 0,
                    "message": f"No subscriber found with email: {subscriber_email}"
                }
        
        # Get all episodes (filtered by subscriber if provided)
        if subscriber_id:
            episodes_query = db.collection(EPISODE_COLLECTION_NAME).where('subscriber_id', '==', subscriber_id).stream()
        else:
            episodes_query = db.collection(EPISODE_COLLECTION_NAME).stream()
        
        for episode_doc in episodes_query:
            episode_data = episode_doc.to_dict() or {}
            canonical = episode_doc.id
            ep_subscriber_id = episode_data.get('subscriber_id')
            
            # Get subscriber email
            subscriber_email_found = 'N/A'
            if ep_subscriber_id:
                try:
                    subscriber_doc = db.collection('subscribers').document(ep_subscriber_id).get()
                    if subscriber_doc.exists:
                        subscriber_email_found = subscriber_doc.to_dict().get('email', 'N/A')
                except:
                    pass
            
            # Check RSS status using rss_service
            in_rss = rss_service.is_episode_in_rss_feed(canonical)
            
            podcasts_list.append({
                'canonical_filename': canonical,
                'title': episode_data.get('title', 'Untitled'),
                'topic': episode_data.get('topic', ''),
                'category': episode_data.get('category', ''),
                'subscriber_email': subscriber_email_found,
                'subscriber_id': ep_subscriber_id,
                'in_rss': in_rss,
                'submitted_to_rss': episode_data.get('submitted_to_rss', False),
                'created_at': episode_data.get('created_at') or episode_data.get('generated_at'),
                'audio_url': episode_data.get('audio_url'),
                'thumbnail_url': episode_data.get('thumbnail_url')
            })
        
        # Sort by created_at descending
        podcasts_list.sort(key=lambda x: x.get('created_at', ''), reverse=True)
        
        structured_logger.info("Retrieved podcast database",
                              total_count=len(podcasts_list),
                              subscriber_filter=subscriber_email)
        
        return {
            "podcasts": podcasts_list,
            "total_count": len(podcasts_list),
            "subscriber_filter": subscriber_email
        }
        
    except Exception as e:
        structured_logger.error("Failed to get podcast database",
                               error=str(e),
                               error_type=type(e).__name__)
        raise HTTPException(status_code=500, detail=f"Failed to get podcast database: {str(e)}")

@router.delete("/podcasts/{podcast_id}/rss")
async def admin_remove_podcast_from_rss(
    podcast_id: str,
    admin_auth: bool = Depends(verify_admin_api_key)
):
    """Remove podcast from RSS feed - Admin endpoint"""
    if not db:
        raise HTTPException(status_code=503, detail="Firestore service is unavailable")
    
    try:
        # Use rss_service to remove from RSS
        success = await rss_service.remove_episode_from_rss_feed(podcast_id)
        
        if success:
            structured_logger.info("Removed podcast from RSS feed",
                                  podcast_id=podcast_id)
            return {
                "message": f"Podcast {podcast_id} removed from RSS feed",
                "podcast_id": podcast_id
            }
        else:
            raise HTTPException(status_code=404, detail=f"Podcast {podcast_id} not found in RSS feed")
        
    except HTTPException:
        raise
    except Exception as e:
        structured_logger.error("Failed to remove podcast from RSS feed",
                               podcast_id=podcast_id,
                               error=str(e),
                               error_type=type(e).__name__)
        raise HTTPException(status_code=500, detail=f"Failed to remove podcast from RSS: {str(e)}")

@router.post("/podcasts/{podcast_id}/rss")
async def admin_add_podcast_to_rss(
    podcast_id: str,
    admin_auth: bool = Depends(verify_admin_api_key)
):
    """Add podcast to RSS feed - Admin endpoint"""
    if not db:
        raise HTTPException(status_code=503, detail="Firestore service is unavailable")
    
    try:
        # Get episode data
        episode_doc = db.collection(EPISODE_COLLECTION_NAME).document(podcast_id).get()
        
        if not episode_doc.exists:
            raise HTTPException(status_code=404, detail=f"Podcast {podcast_id} not found")
        
        episode_data = episode_doc.to_dict() or {}
        
        # Use rss_service to add to RSS
        success = await rss_service.add_episode_to_rss_feed(podcast_id, episode_data)
        
        if success:
            # Update submitted_to_rss flag
            episode_doc.reference.update({
                'submitted_to_rss': True
            })
            
            structured_logger.info("Added podcast to RSS feed",
                                  podcast_id=podcast_id)
            return {
                "message": f"Podcast {podcast_id} added to RSS feed",
                "podcast_id": podcast_id
            }
        else:
            raise HTTPException(status_code=500, detail=f"Failed to add podcast {podcast_id} to RSS feed")
        
    except HTTPException:
        raise
    except Exception as e:
        structured_logger.error("Failed to add podcast to RSS feed",
                               podcast_id=podcast_id,
                               error=str(e),
                               error_type=type(e).__name__)
        raise HTTPException(status_code=500, detail=f"Failed to add podcast to RSS: {str(e)}")

@router.delete("/podcasts/{podcast_id}")
async def admin_delete_podcast(
    podcast_id: str,
    admin_auth: bool = Depends(verify_admin_api_key)
):
    """Delete a podcast - Admin endpoint"""
    if not db:
        raise HTTPException(status_code=503, detail="Firestore service is unavailable")
    
    try:
        # Remove from RSS feed first
        try:
            await rss_service.remove_episode_from_rss_feed(podcast_id)
        except Exception as rss_error:
            structured_logger.warning("Could not remove from RSS feed before deletion",
                                     podcast_id=podcast_id,
                                     error=str(rss_error))
        
        # Delete from episodes collection
        episode_ref = db.collection(EPISODE_COLLECTION_NAME).document(podcast_id)
        episode_doc = episode_ref.get()
        
        if not episode_doc.exists:
            raise HTTPException(status_code=404, detail=f"Podcast {podcast_id} not found")
        
        episode_ref.delete()
        
        structured_logger.info("Deleted podcast",
                              podcast_id=podcast_id)
        
        return {
            "message": f"Podcast {podcast_id} deleted successfully",
            "podcast_id": podcast_id
        }
        
    except HTTPException:
        raise
    except Exception as e:
        structured_logger.error("Failed to delete podcast",
                               podcast_id=podcast_id,
                               error=str(e),
                               error_type=type(e).__name__)
        raise HTTPException(status_code=500, detail=f"Failed to delete podcast: {str(e)}")

@router.post("/episodes/backfill")
async def backfill_episode_catalog(admin_auth: bool = Depends(verify_admin_api_key)):
    """Backfill episode catalog from podcast_jobs - Admin endpoint"""
    if not db:
        raise HTTPException(status_code=503, detail="Firestore service is unavailable")
    
    try:
        from datetime import datetime
        
        backfilled_count = 0
        skipped_count = 0
        errors = []
        
        # Get all completed podcast jobs
        podcast_jobs = db.collection('podcast_jobs').where('status', '==', 'completed').stream()
        
        for job_doc in podcast_jobs:
            try:
                job_data = job_doc.to_dict() or {}
                job_id = job_doc.id
                result = job_data.get('result', {})
                
                canonical_filename = result.get('canonical_filename')
                if not canonical_filename:
                    skipped_count += 1
                    continue
                
                # Check if episode already exists
                episode_doc = db.collection(EPISODE_COLLECTION_NAME).document(canonical_filename).get()
                if episode_doc.exists:
                    skipped_count += 1
                    continue
                
                # Create episode document
                episode_service.ensure_episode_document_from_job(job_id, job_data)
                backfilled_count += 1
                
            except Exception as e:
                errors.append(f"Job {job_doc.id}: {str(e)}")
                structured_logger.warning("Failed to backfill episode from job",
                                         job_id=job_doc.id,
                                         error=str(e))
        
        structured_logger.info("Backfill episode catalog completed",
                              backfilled=backfilled_count,
                              skipped=skipped_count,
                              errors=len(errors))
        
        return {
            "message": f"Backfilled {backfilled_count} episodes",
            "backfilled_count": backfilled_count,
            "skipped_count": skipped_count,
            "errors": errors[:10]  # Limit to first 10 errors
        }
        
    except Exception as e:
        structured_logger.error("Failed to backfill episode catalog",
                               error=str(e),
                               error_type=type(e).__name__)
        raise HTTPException(status_code=500, detail=f"Failed to backfill catalog: {str(e)}")

@router.post("/podcasts/cleanup-stuck")
async def cleanup_stuck_podcasts(admin_auth: bool = Depends(verify_admin_api_key)):
    """Clean up stuck podcasts in pending/generating states - Admin endpoint"""
    if not db:
        raise HTTPException(status_code=503, detail="Firestore service is unavailable")
    
    try:
        from datetime import datetime, timedelta
        
        # Find stuck jobs (pending or generating for more than 2 hours)
        cutoff_time = (datetime.utcnow() - timedelta(hours=2)).isoformat()
        
        stuck_jobs = []
        
        # Check pending jobs
        pending_jobs = db.collection('podcast_jobs').where('status', '==', 'pending').stream()
        for job_doc in pending_jobs:
            job_data = job_doc.to_dict() or {}
            updated_at = job_data.get('updated_at') or job_data.get('created_at')
            if updated_at and updated_at < cutoff_time:
                stuck_jobs.append({
                    'job_id': job_doc.id,
                    'status': 'pending',
                    'updated_at': updated_at
                })
        
        # Check generating jobs
        generating_jobs = db.collection('podcast_jobs').where('status', '==', 'generating_content').stream()
        for job_doc in generating_jobs:
            job_data = job_doc.to_dict() or {}
            updated_at = job_data.get('updated_at') or job_data.get('created_at')
            if updated_at and updated_at < cutoff_time:
                stuck_jobs.append({
                    'job_id': job_doc.id,
                    'status': 'generating_content',
                    'updated_at': updated_at
                })
        
        # Mark stuck jobs as failed
        for stuck_job in stuck_jobs:
            job_ref = db.collection('podcast_jobs').document(stuck_job['job_id'])
            job_ref.update({
                'status': 'failed',
                'error': 'Job stuck in intermediate state - marked as failed by cleanup',
                'updated_at': datetime.utcnow().isoformat()
            })
        
        structured_logger.info("Cleaned up stuck podcasts",
                              stuck_count=len(stuck_jobs))
        
        return {
            "message": f"Cleaned up {len(stuck_jobs)} stuck podcasts",
            "stuck_jobs": stuck_jobs
        }
        
    except Exception as e:
        structured_logger.error("Failed to cleanup stuck podcasts",
                               error=str(e),
                               error_type=type(e).__name__)
        raise HTTPException(status_code=500, detail=f"Failed to cleanup stuck podcasts: {str(e)}")

@router.post("/episodes/sync-rss-status")
async def sync_rss_status(admin_auth: bool = Depends(verify_admin_api_key)):
    """Sync RSS status for all episodes - Admin endpoint"""
    if not db:
        raise HTTPException(status_code=503, detail="Firestore service is unavailable")
    
    try:
        synced_count = 0
        updated_count = 0
        
        # Get all episodes
        episodes = db.collection(EPISODE_COLLECTION_NAME).stream()
        
        for episode_doc in episodes:
            canonical = episode_doc.id
            episode_data = episode_doc.to_dict() or {}
            
            # Check RSS status
            in_rss = rss_service.is_episode_in_rss_feed(canonical)
            current_status = episode_data.get('submitted_to_rss', False)
            
            # Update if status differs
            if in_rss != current_status:
                episode_doc.reference.update({
                    'submitted_to_rss': in_rss
                })
                updated_count += 1
            
            synced_count += 1
        
        structured_logger.info("Synced RSS status for all episodes",
                              synced=synced_count,
                              updated=updated_count)
        
        return {
            "message": f"Synced RSS status for {synced_count} episodes",
            "synced_count": synced_count,
            "updated_count": updated_count
        }
        
    except Exception as e:
        structured_logger.error("Failed to sync RSS status",
                               error=str(e),
                               error_type=type(e).__name__)
        raise HTTPException(status_code=500, detail=f"Failed to sync RSS status: {str(e)}")

@router.get("/podcasts/legacy")
async def admin_get_legacy_podcasts(admin_auth: bool = Depends(verify_admin_api_key)):
    """Get legacy podcasts (from podcast_jobs but not in episodes) - Admin endpoint"""
    if not db:
        raise HTTPException(status_code=503, detail="Firestore service is unavailable")
    
    try:
        legacy_podcasts = []
        
        # Get all completed podcast jobs
        podcast_jobs = db.collection('podcast_jobs').where('status', '==', 'completed').stream()
        
        for job_doc in podcast_jobs:
            job_data = job_doc.to_dict() or {}
            result = job_data.get('result', {})
            canonical = result.get('canonical_filename')
            
            if canonical:
                # Check if episode exists
                episode_doc = db.collection(EPISODE_COLLECTION_NAME).document(canonical).get()
                if not episode_doc.exists:
                    legacy_podcasts.append({
                        'job_id': job_doc.id,
                        'canonical_filename': canonical,
                        'title': result.get('title', 'Untitled'),
                        'topic': job_data.get('request', {}).get('topic', ''),
                        'category': job_data.get('request', {}).get('category', ''),
                        'created_at': job_data.get('created_at'),
                        'result': result
                    })
        
        structured_logger.info("Retrieved legacy podcasts",
                              total_count=len(legacy_podcasts))
        
        return {
            "legacy_podcasts": legacy_podcasts,
            "total_count": len(legacy_podcasts)
        }
        
    except Exception as e:
        structured_logger.error("Failed to get legacy podcasts",
                               error=str(e),
                               error_type=type(e).__name__)
        raise HTTPException(status_code=500, detail=f"Failed to get legacy podcasts: {str(e)}")

@router.post("/podcasts/reassign")
async def admin_reassign_podcasts(
    request: dict,
    admin_auth: bool = Depends(verify_admin_api_key)
):
    """Admin endpoint: Reassign podcasts from one subscriber to another
    
    Request body:
    {
        "from_subscriber_id": "subscriber_id_to_move_from",
        "to_subscriber_id": "subscriber_id_to_move_to",
        "podcast_ids": ["podcast_id1", "podcast_id2"]  # Optional: specific podcasts. If omitted, moves all.
    }
    """
    if not db:
        raise HTTPException(status_code=503, detail="Firestore service is unavailable")
    
    try:
        from_subscriber_id = request.get('from_subscriber_id')
        to_subscriber_id = request.get('to_subscriber_id')
        podcast_ids = request.get('podcast_ids')
        
        if not from_subscriber_id or not to_subscriber_id:
            raise HTTPException(status_code=400, detail="Both from_subscriber_id and to_subscriber_id are required")
        
        # Verify both subscribers exist
        from_subscriber_doc = db.collection('subscribers').document(from_subscriber_id).get()
        to_subscriber_doc = db.collection('subscribers').document(to_subscriber_id).get()
        
        if not from_subscriber_doc.exists:
            raise HTTPException(status_code=404, detail=f"Source subscriber not found: {from_subscriber_id}")
        if not to_subscriber_doc.exists:
            raise HTTPException(status_code=404, detail=f"Target subscriber not found: {to_subscriber_id}")
        
        from_email = from_subscriber_doc.to_dict().get('email', from_subscriber_id)
        to_email = to_subscriber_doc.to_dict().get('email', to_subscriber_id)
        
        # Find podcasts to reassign
        if podcast_ids:
            podcasts_to_reassign = podcast_ids
        else:
            # Get all podcasts from the source subscriber
            podcasts_query = db.collection('podcast_jobs').where('subscriber_id', '==', from_subscriber_id)
            podcasts_to_reassign = [podcast.id for podcast in podcasts_query.stream()]
        
        if not podcasts_to_reassign:
            return {
                "message": f"No podcasts found to reassign from {from_email}",
                "reassigned_count": 0
            }
        
        # Reassign podcasts
        reassigned_count = 0
        for podcast_id in podcasts_to_reassign:
            try:
                # Update podcast_jobs
                job_ref = db.collection('podcast_jobs').document(podcast_id)
                job_doc = job_ref.get()
                if job_doc.exists:
                    job_ref.update({
                        'subscriber_id': to_subscriber_id,
                        'updated_at': datetime.utcnow().isoformat()
                    })
                
                # Update episodes collection
                episode_ref = db.collection(EPISODE_COLLECTION_NAME).document(podcast_id)
                episode_doc = episode_ref.get()
                if episode_doc.exists:
                    episode_ref.update({
                        'subscriber_id': to_subscriber_id,
                        'updated_at': datetime.utcnow().isoformat()
                    })
                
                reassigned_count += 1
            except Exception as e:
                structured_logger.warning("Failed to reassign podcast",
                                         podcast_id=podcast_id,
                                         error=str(e))
        
        # Update subscriber podcast counts
        try:
            # Update source subscriber count
            from_count_query = db.collection('podcast_jobs').where('subscriber_id', '==', from_subscriber_id).stream()
            from_new_count = len(list(from_count_query))
            db.collection('subscribers').document(from_subscriber_id).update({
                'podcasts_generated': from_new_count
            })
            
            # Update target subscriber count
            to_count_query = db.collection('podcast_jobs').where('subscriber_id', '==', to_subscriber_id).stream()
            to_new_count = len(list(to_count_query))
            db.collection('subscribers').document(to_subscriber_id).update({
                'podcasts_generated': to_new_count
            })
        except Exception as e:
            structured_logger.warning("Could not update subscriber podcast counts",
                                     error=str(e))
        
        structured_logger.info("Reassigned podcasts",
                              from_subscriber=from_email,
                              to_subscriber=to_email,
                              reassigned_count=reassigned_count)
        
        return {
            "message": f"Reassigned {reassigned_count} podcasts from {from_email} to {to_email}",
            "from_subscriber_id": from_subscriber_id,
            "to_subscriber_id": to_subscriber_id,
            "reassigned_count": reassigned_count
        }
        
    except HTTPException:
        raise
    except Exception as e:
        structured_logger.error("Failed to reassign podcasts",
                               error=str(e),
                               error_type=type(e).__name__)
        raise HTTPException(status_code=500, detail=f"Failed to reassign podcasts: {str(e)}")

@router.post("/podcasts/assign-subscriber/{subscriber_id}")
async def admin_assign_podcasts_to_subscriber(
    subscriber_id: str,
    request: dict,
    admin_auth: bool = Depends(verify_admin_api_key)
):
    """Assign podcasts to a subscriber - Admin endpoint
    
    Request body:
    {
        "podcast_ids": ["podcast_id1", "podcast_id2", ...]
    }
    """
    if not db:
        raise HTTPException(status_code=503, detail="Firestore service is unavailable")
    
    try:
        from datetime import datetime
        
        podcast_ids = request.get('podcast_ids', [])
        
        if not podcast_ids:
            raise HTTPException(status_code=400, detail="podcast_ids array is required")
        
        # Verify subscriber exists
        subscriber_doc = db.collection('subscribers').document(subscriber_id).get()
        if not subscriber_doc.exists:
            raise HTTPException(status_code=404, detail=f"Subscriber not found: {subscriber_id}")
        
        assigned_count = 0
        errors = []
        
        for podcast_id in podcast_ids:
            try:
                # Update podcast_jobs
                job_ref = db.collection('podcast_jobs').document(podcast_id)
                job_doc = job_ref.get()
                if job_doc.exists:
                    job_ref.update({
                        'subscriber_id': subscriber_id,
                        'updated_at': datetime.utcnow().isoformat()
                    })
                
                # Update episodes collection
                episode_ref = db.collection(EPISODE_COLLECTION_NAME).document(podcast_id)
                episode_doc = episode_ref.get()
                if episode_doc.exists:
                    episode_ref.update({
                        'subscriber_id': subscriber_id,
                        'updated_at': datetime.utcnow().isoformat()
                    })
                
                assigned_count += 1
            except Exception as e:
                errors.append(f"Podcast {podcast_id}: {str(e)}")
                structured_logger.warning("Failed to assign podcast to subscriber",
                                         podcast_id=podcast_id,
                                         subscriber_id=subscriber_id,
                                         error=str(e))
        
        structured_logger.info("Assigned podcasts to subscriber",
                              subscriber_id=subscriber_id,
                              assigned_count=assigned_count,
                              errors=len(errors))
        
        return {
            "message": f"Assigned {assigned_count} podcasts to subscriber {subscriber_id}",
            "subscriber_id": subscriber_id,
            "assigned_count": assigned_count,
            "errors": errors[:10]  # Limit to first 10 errors
        }
        
    except HTTPException:
        raise
    except Exception as e:
        structured_logger.error("Failed to assign podcasts to subscriber",
                               subscriber_id=subscriber_id,
                               error=str(e),
                               error_type=type(e).__name__)
        raise HTTPException(status_code=500, detail=f"Failed to assign podcasts: {str(e)}")

# ============================================================================
# RSS MAINTENANCE ENDPOINTS
# ============================================================================

@router.post("/rss/fix-untitled-episodes")
async def fix_untitled_episodes_in_rss(admin_auth: bool = Depends(verify_admin_api_key)):
    """Fix existing 'Untitled Episode' entries in RSS feed by looking up titles from Firestore.
    
    This scans the RSS feed for items with 'Untitled Episode' titles, looks them up in
    Firestore (episodes collection or podcast_jobs), and updates the RSS feed with correct titles.
    """
    if not db:
        raise HTTPException(status_code=503, detail="Firestore service is unavailable")
    
    try:
        from google.cloud import storage
        from google.api_core.exceptions import PreconditionFailed
        import xml.etree.ElementTree as ET
        import re
        
        structured_logger.info("Starting fix of untitled episodes in RSS feed")
        
        # Read RSS feed from GCS
        storage_client = storage.Client()
        bucket = storage_client.bucket(RSS_BUCKET_NAME)
        blob = bucket.blob(RSS_FEED_BLOB_NAME)
        
        if not blob.exists():
            raise HTTPException(status_code=404, detail="RSS feed file not found in storage")
        
        blob.reload()
        current_generation = blob.generation
        xml_bytes = blob.download_as_bytes()
        root = ET.fromstring(xml_bytes)
        channel = root.find("channel")
        
        if channel is None:
            raise HTTPException(status_code=500, detail="RSS feed missing channel element")
        
        # Find all items with "Untitled Episode" titles
        untitled_items = []
        items = channel.findall("item")
        for item in items:
            title_elem = item.find("title")
            if title_elem is not None:
                title_text = title_elem.text or ""
                # Remove CDATA markers if present
                title_text = re.sub(r'<!\[CDATA\[(.*?)\]\]>', r'\1', title_text, flags=re.DOTALL)
                if "Untitled Episode" in title_text or title_text.strip() == "":
                    guid_elem = item.find("guid")
                    guid = guid_elem.text if guid_elem is not None else None
                    if guid:
                        untitled_items.append((item, guid.strip()))
        
        structured_logger.info("Found untitled episodes in RSS feed",
                              untitled_count=len(untitled_items))
        
        if not untitled_items:
            return {
                "message": "No untitled episodes found in RSS feed",
                "fixed_count": 0,
                "not_found_count": 0
            }
        
        # Look up titles in Firestore and update RSS items
        fixed_count = 0
        not_found_count = 0
        updates_made = False
        
        for item, guid in untitled_items:
            title_found = None
            topic_found = None
            
            # Try to find in episodes collection first (by canonical_filename or episode_id)
            episode_doc = db.collection(EPISODE_COLLECTION_NAME).document(guid).get()
            if not episode_doc.exists:
                # Try finding by canonical_filename field
                episodes_query = db.collection(EPISODE_COLLECTION_NAME).where('canonical_filename', '==', guid).limit(1).stream()
                for ep_doc in episodes_query:
                    episode_doc = ep_doc
                    break
            
            if episode_doc.exists:
                episode_data = episode_doc.to_dict() or {}
                title_found = episode_data.get("title")
                if not title_found:
                    topic_found = episode_data.get("topic")
            else:
                # Try to find in podcast_jobs collection using canonical_filename
                podcast_jobs = db.collection('podcast_jobs').where('result.canonical_filename', '==', guid).limit(1).stream()
                for job_doc in podcast_jobs:
                    job_data = job_doc.to_dict() or {}
                    result_data = job_data.get("result", {})
                    title_found = result_data.get("title")
                    if not title_found:
                        request_data = job_data.get("request", {})
                        topic_found = request_data.get("topic") or result_data.get("topic")
                    break
                
                # If still not found, try searching by job_id
                if not title_found and not topic_found:
                    job_doc = db.collection('podcast_jobs').document(guid).get()
                    if job_doc.exists:
                        job_data = job_doc.to_dict() or {}
                        result_data = job_data.get("result", {})
                        title_found = result_data.get("title")
                        if not title_found:
                            request_data = job_data.get("request", {})
                            topic_found = request_data.get("topic") or result_data.get("topic")
            
            # Use topic as fallback if title not found
            new_title = title_found or topic_found
            if new_title and new_title.strip():
                # Update title element (handle CDATA)
                title_elem = item.find("title")
                if title_elem is None:
                    title_elem = ET.SubElement(item, "title")
                title_elem.text = f"<![CDATA[{new_title.strip()}]]>"
                
                # Also update iTunes title if present
                itunes_ns = "{http://www.itunes.com/dtds/podcast-1.0.dtd}"
                itunes_title_elem = item.find(f"{itunes_ns}title")
                if itunes_title_elem is None:
                    itunes_title_elem = ET.SubElement(item, f"{itunes_ns}title")
                itunes_title_elem.text = f"<![CDATA[{new_title.strip()}]]>"
                
                fixed_count += 1
                updates_made = True
                structured_logger.info("Fixed untitled episode in RSS feed",
                                      guid=guid,
                                      new_title=new_title.strip()[:60])
            else:
                not_found_count += 1
                structured_logger.warning("Could not find title or topic for untitled episode",
                                         guid=guid)
        
        # Save updated RSS feed if changes were made
        if updates_made:
            new_xml_bytes = ET.tostring(root, encoding="utf-8", xml_declaration=True)
            # Restore CDATA markers (ElementTree escapes them by default)
            xml_text = new_xml_bytes.decode("utf-8")
            xml_text = xml_text.replace("&lt;![CDATA[", "<![CDATA[").replace("]]&gt;", "]]>")
            new_xml_bytes = xml_text.encode("utf-8")
            
            try:
                blob.upload_from_string(
                    new_xml_bytes,
                    content_type="application/rss+xml",
                    if_generation_match=current_generation,
                )
                structured_logger.info("Updated RSS feed with fixed titles",
                                      fixed_count=fixed_count,
                                      not_found_count=not_found_count)
            except PreconditionFailed:
                raise HTTPException(status_code=409, detail="RSS feed was updated concurrently. Please retry.")
        
        return {
            "message": f"Fixed {fixed_count} untitled episodes in RSS feed",
            "fixed_count": fixed_count,
            "not_found_count": not_found_count,
            "total_untitled": len(untitled_items)
        }
        
    except HTTPException:
        raise
    except Exception as e:
        structured_logger.error("Failed to fix untitled episodes in RSS feed",
                               error=str(e),
                               error_type=type(e).__name__)
        raise HTTPException(status_code=500, detail=f"Failed to fix untitled episodes: {str(e)}")

@router.post("/rss/fix-thumbnails")
async def fix_thumbnails_in_rss(admin_auth: bool = Depends(verify_admin_api_key)):
    """Fix thumbnail URLs in RSS feed by checking if thumbnails exist in GCS.
    
    This scans all episodes in the RSS feed and:
    1. Checks if thumbnails exist in GCS at the expected location
    2. Updates RSS feed and Firestore with correct thumbnail URLs if found
    3. Reports episodes with missing thumbnails
    """
    if not db:
        raise HTTPException(status_code=503, detail="Firestore service is unavailable")
    
    try:
        from google.cloud import storage
        from google.api_core.exceptions import PreconditionFailed
        import xml.etree.ElementTree as ET
        import re
        import requests
        
        structured_logger.info("Starting fix of thumbnail URLs in RSS feed")
        
        # Read RSS feed from GCS
        storage_client = storage.Client()
        bucket = storage_client.bucket(RSS_BUCKET_NAME)
        blob = bucket.blob(RSS_FEED_BLOB_NAME)
        
        if not blob.exists():
            raise HTTPException(status_code=404, detail="RSS feed file not found in storage")
        
        blob.reload()
        current_generation = blob.generation
        xml_bytes = blob.download_as_bytes()
        root = ET.fromstring(xml_bytes)
        channel = root.find("channel")
        
        if channel is None:
            raise HTTPException(status_code=500, detail="RSS feed missing channel element")
        
        # GCS bucket for thumbnails
        podcast_storage_bucket = storage_client.bucket("regal-scholar-453620-r7-podcast-storage")
        
        items = channel.findall("item")
        itunes_ns = "{http://www.itunes.com/dtds/podcast-1.0.dtd}"
        media_ns = "{http://search.yahoo.com/mrss/}"
        
        fixed_count = 0
        missing_count = 0
        already_correct_count = 0
        updates_made = False
        
        for item in items:
            guid_elem = item.find("guid")
            guid = guid_elem.text.strip() if guid_elem is not None and guid_elem.text else None
            
            if not guid:
                continue
            
            # Get current thumbnail URL from RSS feed
            itunes_image_elem = item.find(f"{itunes_ns}image")
            current_thumbnail_url = None
            if itunes_image_elem is not None:
                current_thumbnail_url = itunes_image_elem.get("href", "")
            
            # Expected thumbnail location in GCS
            expected_thumbnail_blob_name = f"thumbnails/{guid}-thumb.jpg"
            expected_thumbnail_url = f"https://storage.googleapis.com/regal-scholar-453620-r7-podcast-storage/{expected_thumbnail_blob_name}"
            
            # Check if thumbnail exists in GCS
            thumbnail_blob = podcast_storage_bucket.blob(expected_thumbnail_blob_name)
            thumbnail_exists = thumbnail_blob.exists()
            
            # Also check if thumbnail is publicly accessible by trying to access the URL
            thumbnail_accessible = False
            if thumbnail_exists:
                try:
                    response = requests.head(expected_thumbnail_url, timeout=5)
                    thumbnail_accessible = response.status_code == 200
                except:
                    pass
            
            if thumbnail_exists and thumbnail_accessible:
                # Thumbnail exists and is accessible
                if current_thumbnail_url != expected_thumbnail_url:
                    # Update RSS feed with correct thumbnail URL
                    if itunes_image_elem is None:
                        itunes_image_elem = ET.SubElement(item, f"{itunes_ns}image")
                    itunes_image_elem.set("href", expected_thumbnail_url)
                    
                    # Also update media:thumbnail if present
                    media_thumb_elem = item.find(f"{media_ns}thumbnail")
                    if media_thumb_elem is not None:
                        media_thumb_elem.set("url", expected_thumbnail_url)
                    
                    # Update Firestore episodes collection
                    try:
                        episode_doc = db.collection(EPISODE_COLLECTION_NAME).document(guid).get()
                        if episode_doc.exists:
                            episode_doc.reference.update({
                                'thumbnail_url': expected_thumbnail_url
                            })
                        
                        # Also update podcast_jobs if exists
                        podcast_jobs = db.collection('podcast_jobs').where('result.canonical_filename', '==', guid).limit(1).stream()
                        for job_doc in podcast_jobs:
                            job_data = job_doc.to_dict() or {}
                            result = job_data.get('result', {})
                            if result.get('thumbnail_url') != expected_thumbnail_url:
                                job_doc.reference.update({
                                    'result.thumbnail_url': expected_thumbnail_url
                                })
                            break
                    except Exception as e:
                        structured_logger.warning("Could not update Firestore with thumbnail URL",
                                                 guid=guid,
                                                 error=str(e))
                    
                    fixed_count += 1
                    updates_made = True
                    structured_logger.info("Fixed thumbnail URL in RSS feed",
                                          guid=guid,
                                          thumbnail_url=expected_thumbnail_url)
                else:
                    already_correct_count += 1
            else:
                # Thumbnail doesn't exist or isn't accessible
                missing_count += 1
                structured_logger.warning("Thumbnail missing or inaccessible for episode",
                                         guid=guid,
                                         exists=thumbnail_exists,
                                         accessible=thumbnail_accessible)
        
        # Save updated RSS feed if changes were made
        if updates_made:
            new_xml_bytes = ET.tostring(root, encoding="utf-8", xml_declaration=True)
            # Restore CDATA markers (ElementTree escapes them by default)
            xml_text = new_xml_bytes.decode("utf-8")
            xml_text = xml_text.replace("&lt;![CDATA[", "<![CDATA[").replace("]]&gt;", "]]>")
            new_xml_bytes = xml_text.encode("utf-8")
            
            try:
                blob.upload_from_string(
                    new_xml_bytes,
                    content_type="application/rss+xml",
                    if_generation_match=current_generation,
                )
                structured_logger.info("Updated RSS feed with fixed thumbnail URLs",
                                      fixed_count=fixed_count,
                                      missing_count=missing_count)
            except PreconditionFailed:
                raise HTTPException(status_code=409, detail="RSS feed was updated concurrently. Please retry.")
        
        return {
            "message": f"Thumbnail fix completed: {fixed_count} fixed, {already_correct_count} already correct, {missing_count} missing",
            "fixed_count": fixed_count,
            "already_correct_count": already_correct_count,
            "missing_count": missing_count,
            "total_episodes": len(items),
            "rss_feed_updated": updates_made
        }
        
    except HTTPException:
        raise
    except Exception as e:
        structured_logger.error("Failed to fix thumbnails in RSS feed",
                               error=str(e),
                               error_type=type(e).__name__)
        raise HTTPException(status_code=500, detail=f"Failed to fix thumbnails: {str(e)}")

@router.get("/rss/diagnose-thumbnails")
async def diagnose_thumbnails(admin_auth: bool = Depends(verify_admin_api_key)):
    """Diagnose thumbnail issues: identify missing thumbnails and episodes using default artwork.
    
    This endpoint:
    1. Scans all episodes in RSS feed
    2. Checks if thumbnails exist in GCS
    3. Identifies episodes using default artwork instead of custom thumbnails
    4. Returns detailed report of all thumbnail issues
    """
    if not db:
        raise HTTPException(status_code=503, detail="Firestore service is unavailable")
    
    try:
        from google.cloud import storage
        import xml.etree.ElementTree as ET
        import re
        import requests
        
        structured_logger.info("Starting thumbnail diagnosis")
        
        # Read RSS feed from GCS
        storage_client = storage.Client()
        bucket = storage_client.bucket(RSS_BUCKET_NAME)
        blob = bucket.blob(RSS_FEED_BLOB_NAME)
        
        if not blob.exists():
            raise HTTPException(status_code=404, detail="RSS feed file not found in storage")
        
        xml_bytes = blob.download_as_bytes()
        root = ET.fromstring(xml_bytes)
        channel = root.find("channel")
        
        if channel is None:
            raise HTTPException(status_code=500, detail="RSS feed missing channel element")
        
        # GCS bucket for thumbnails
        podcast_storage_bucket = storage_client.bucket("regal-scholar-453620-r7-podcast-storage")
        
        items = channel.findall("item")
        itunes_ns = "{http://www.itunes.com/dtds/podcast-1.0.dtd}"
        
        missing_thumbnails = []  # Episodes with no thumbnail file in GCS
        using_default_artwork = []  # Episodes using DEFAULT_ARTWORK_URL
        correct_thumbnails = []  # Episodes with correct custom thumbnails
        inaccessible_thumbnails = []  # Thumbnails exist but not accessible
        
        for item in items:
            guid_elem = item.find("guid")
            guid = guid_elem.text.strip() if guid_elem is not None and guid_elem.text else None
            
            if not guid:
                continue
            
            # Get title from RSS feed
            title_elem = item.find("title")
            title = title_elem.text if title_elem is not None else "Unknown"
            # Remove CDATA markers
            if title and "<![CDATA[" in title:
                title = title.split("<![CDATA[")[1].split("]]>")[0] if "]]>" in title else title
            
            # Get thumbnail URL from RSS feed
            itunes_image_elem = item.find(f"{itunes_ns}image")
            rss_thumbnail_url = None
            if itunes_image_elem is not None:
                rss_thumbnail_url = itunes_image_elem.get("href", "")
            
            # Check if using default artwork
            is_using_default = rss_thumbnail_url == DEFAULT_ARTWORK_URL or not rss_thumbnail_url
            
            # Expected thumbnail location in GCS
            expected_thumbnail_blob_name = f"thumbnails/{guid}-thumb.jpg"
            expected_thumbnail_url = f"https://storage.googleapis.com/regal-scholar-453620-r7-podcast-storage/{expected_thumbnail_blob_name}"
            
            # Check if thumbnail exists in GCS
            thumbnail_blob = podcast_storage_bucket.blob(expected_thumbnail_blob_name)
            thumbnail_exists = thumbnail_blob.exists()
            
            # Check if thumbnail is publicly accessible
            thumbnail_accessible = False
            if thumbnail_exists:
                try:
                    response = requests.head(expected_thumbnail_url, timeout=5)
                    thumbnail_accessible = response.status_code == 200
                except:
                    pass
            
            # Get episode info from Firestore for more details
            episode_info = {
                'guid': guid,
                'title': title[:100] if title else 'Unknown',
                'rss_thumbnail_url': rss_thumbnail_url,
                'expected_thumbnail_url': expected_thumbnail_url,
                'thumbnail_exists_in_gcs': thumbnail_exists,
                'thumbnail_accessible': thumbnail_accessible,
                'is_using_default_artwork': is_using_default
            }
            
            # Try to get more details from Firestore
            try:
                episode_doc = db.collection(EPISODE_COLLECTION_NAME).document(guid).get()
                if episode_doc.exists:
                    episode_data = episode_doc.to_dict() or {}
                    episode_info['firestore_thumbnail_url'] = episode_data.get('thumbnail_url')
                    episode_info['created_at'] = episode_data.get('created_at') or episode_data.get('generated_at')
                    episode_info['subscriber_email'] = 'Unknown'
                    subscriber_id = episode_data.get('subscriber_id')
                    if subscriber_id:
                        subscriber_doc = db.collection('subscribers').document(subscriber_id).get()
                        if subscriber_doc.exists:
                            subscriber_data = subscriber_doc.to_dict() or {}
                            episode_info['subscriber_email'] = subscriber_data.get('email', 'Unknown')
            except Exception as e:
                structured_logger.debug("Could not get Firestore data for episode",
                                       guid=guid,
                                       error=str(e))
            
            # Categorize the episode
            if not thumbnail_exists:
                missing_thumbnails.append(episode_info)
            elif not thumbnail_accessible:
                inaccessible_thumbnails.append(episode_info)
            elif is_using_default:
                using_default_artwork.append(episode_info)
            else:
                correct_thumbnails.append(episode_info)
        
        # Also check all episodes in Firestore (not just RSS feed) for completeness
        all_episodes_missing_thumbnails = []
        try:
            all_episodes = db.collection(EPISODE_COLLECTION_NAME).stream()
            for episode_doc in all_episodes:
                episode_data = episode_doc.to_dict() or {}
                canonical = episode_doc.id
                thumbnail_url = episode_data.get('thumbnail_url', '')
                
                # Skip if already in RSS feed (we already checked it)
                if canonical in [ep['guid'] for ep in missing_thumbnails + using_default_artwork + correct_thumbnails + inaccessible_thumbnails]:
                    continue
                
                # Check if using default artwork
                is_using_default = thumbnail_url == DEFAULT_ARTWORK_URL or not thumbnail_url
                
                # Check if thumbnail exists
                expected_thumbnail_blob_name = f"thumbnails/{canonical}-thumb.jpg"
                thumbnail_blob = podcast_storage_bucket.blob(expected_thumbnail_blob_name)
                thumbnail_exists = thumbnail_blob.exists()
                
                if not thumbnail_exists or is_using_default:
                    all_episodes_missing_thumbnails.append({
                        'guid': canonical,
                        'title': episode_data.get('title', 'Unknown')[:100],
                        'thumbnail_url': thumbnail_url,
                        'thumbnail_exists_in_gcs': thumbnail_exists,
                        'is_using_default_artwork': is_using_default,
                        'submitted_to_rss': episode_data.get('submitted_to_rss', False),
                        'created_at': episode_data.get('created_at') or episode_data.get('generated_at')
                    })
        except Exception as e:
            structured_logger.warning("Could not check all episodes for missing thumbnails",
                                     error=str(e))
        
        result = {
            "rss_feed_episodes": {
                "total": len(items),
                "correct_thumbnails": len(correct_thumbnails),
                "missing_thumbnails": len(missing_thumbnails),
                "using_default_artwork": len(using_default_artwork),
                "inaccessible_thumbnails": len(inaccessible_thumbnails)
            },
            "missing_thumbnails_in_rss": missing_thumbnails,
            "using_default_artwork_in_rss": using_default_artwork,
            "inaccessible_thumbnails_in_rss": inaccessible_thumbnails,
            "all_episodes_missing_thumbnails": all_episodes_missing_thumbnails,
            "summary": {
                "total_rss_episodes": len(items),
                "rss_episodes_with_correct_thumbnails": len(correct_thumbnails),
                "rss_episodes_missing_thumbnails": len(missing_thumbnails),
                "rss_episodes_using_default": len(using_default_artwork),
                "rss_episodes_inaccessible": len(inaccessible_thumbnails),
                "other_episodes_missing_thumbnails": len(all_episodes_missing_thumbnails)
            }
        }
        
        structured_logger.info("Thumbnail diagnosis complete",
                              total_rss_episodes=len(items),
                              missing=len(missing_thumbnails),
                              using_default=len(using_default_artwork),
                              correct=len(correct_thumbnails))
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        structured_logger.error("Failed to diagnose thumbnails",
                               error=str(e),
                               error_type=type(e).__name__)
        raise HTTPException(status_code=500, detail=f"Failed to diagnose thumbnails: {str(e)}")

@router.post("/podcasts/assign-canonical-filenames")
async def assign_canonical_filenames(request: dict, admin_auth: bool = Depends(verify_admin_api_key)):
    """Assign canonical filenames to episodes that are missing them.
    
    This endpoint:
    1. Finds episodes/podcasts using UUID GUIDs instead of canonical filenames
    2. Generates appropriate canonical filenames based on category and next available number
    3. Updates Firestore and RSS feed with canonical filenames
    
    Request body:
    {
        "episode_guids": ["guid1", "guid2", ...]  # Optional: specific GUIDs to fix
        OR
        "fix_all_missing": true  # Fix all episodes missing canonical filenames
    }
    """
    if not db:
        raise HTTPException(status_code=503, detail="Firestore service is unavailable")
    
    try:
        from services.canonical_service import canonical_service
        from datetime import datetime
        import re
        
        episode_guids = request.get('episode_guids', [])
        fix_all_missing = request.get('fix_all_missing', False)
        
        if fix_all_missing:
            # Pattern for canonical filenames: ever-{category}-{6 digits} or news-{category}-{YYYYMMDD}-{4 digits}
            canonical_pattern = re.compile(r'^(ever|news)-(bio|chem|compsci|math|phys)-\d{6}(-\d{4})?$')
            
            episode_guids = []
            identifiers_to_fix = []
            
            # Check podcast_jobs collection
            podcast_jobs = db.collection('podcast_jobs').stream()
            for job_doc in podcast_jobs:
                job_data = job_doc.to_dict() or {}
                result = job_data.get('result', {})
                canonical = result.get('canonical_filename')
                job_id = job_doc.id
                
                # Check if canonical filename is missing or doesn't match pattern
                is_canonical = False
                if canonical:
                    is_canonical = bool(canonical_pattern.match(canonical))
                
                if not is_canonical:
                    identifiers_to_fix.append({
                        'identifier': canonical or job_id,
                        'job_id': job_id,
                        'topic': job_data.get('request', {}).get('topic', ''),
                        'category': job_data.get('request', {}).get('category', ''),
                        'format_type': job_data.get('request', {}).get('format_type', 'feature'),
                        'title': result.get('title', ''),
                        'type': 'podcast_jobs'
                    })
            
            episode_guids = [item['identifier'] for item in identifiers_to_fix]
        
        if not episode_guids:
            return {
                "message": "No episodes to fix",
                "fixed_count": 0
            }
        
        fixed_count = 0
        errors = []
        
        for guid in episode_guids:
            try:
                # Try to find in episodes collection
                episode_doc = db.collection(EPISODE_COLLECTION_NAME).document(guid).get()
                if episode_doc.exists:
                    episode_data = episode_doc.to_dict() or {}
                    topic = episode_data.get('topic', '')
                    title = episode_data.get('title', topic)
                    category = episode_data.get('category', '')
                    format_type = episode_data.get('format_type', 'feature')
                    
                    # Generate canonical filename
                    new_canonical = await canonical_service.determine_canonical_filename(
                        topic=topic,
                        title=title,
                        category=category,
                        format_type=format_type
                    )
                    
                    if new_canonical != guid:
                        # Update episode document with new canonical
                        # Note: This is a complex operation - may need to handle document ID change
                        # For now, update the canonical_filename field
                        episode_doc.reference.update({
                            'canonical_filename': new_canonical,
                            'updated_at': datetime.utcnow().isoformat()
                        })
                        
                        fixed_count += 1
                else:
                    # Try to find in podcast_jobs
                    job_doc = db.collection('podcast_jobs').document(guid).get()
                    if job_doc.exists:
                        job_data = job_doc.to_dict() or {}
                        request_data = job_data.get('request', {})
                        result = job_data.get('result', {})
                        
                        topic = request_data.get('topic', '') or result.get('topic', '')
                        title = result.get('title', topic)
                        category = request_data.get('category', '')
                        format_type = request_data.get('format_type', 'feature')
                        
                        # Generate canonical filename
                        new_canonical = await canonical_service.determine_canonical_filename(
                            topic=topic,
                            title=title,
                            category=category,
                            format_type=format_type
                        )
                        
                        # Update job with canonical filename
                        job_doc.reference.update({
                            'result.canonical_filename': new_canonical,
                            'updated_at': datetime.utcnow().isoformat()
                        })
                        
                        fixed_count += 1
                    else:
                        errors.append(f"Episode {guid} not found")
            except Exception as e:
                errors.append(f"Episode {guid}: {str(e)}")
                structured_logger.warning("Failed to assign canonical filename",
                                         guid=guid,
                                         error=str(e))
        
        structured_logger.info("Assigned canonical filenames",
                              fixed_count=fixed_count,
                              errors=len(errors))
        
        return {
            "message": f"Assigned canonical filenames to {fixed_count} episodes",
            "fixed_count": fixed_count,
            "errors": errors[:10]  # Limit to first 10 errors
        }
        
    except Exception as e:
        structured_logger.error("Failed to assign canonical filenames",
                               error=str(e),
                               error_type=type(e).__name__)
        raise HTTPException(status_code=500, detail=f"Failed to assign canonical filenames: {str(e)}")

@router.post("/rss/regenerate-thumbnails")
async def regenerate_thumbnails_in_rss(admin_auth: bool = Depends(verify_admin_api_key)):
    """Regenerate thumbnails for episodes in RSS feed - Admin endpoint"""
    if not db:
        raise HTTPException(status_code=503, detail="Firestore service is unavailable")
    
    try:
        from services.podcast_generation_service import podcast_generation_service
        
        structured_logger.info("Starting thumbnail regeneration for RSS episodes")
        
        # Get all episodes in RSS feed
        episodes_in_rss = rss_service.get_all_episodes_in_rss()
        
        regenerated_count = 0
        errors = []
        
        for canonical in episodes_in_rss:
            try:
                # Get episode data
                episode_doc = db.collection(EPISODE_COLLECTION_NAME).document(canonical).get()
                if not episode_doc.exists:
                    continue
                
                episode_data = episode_doc.to_dict() or {}
                title = episode_data.get('title', '')
                topic = episode_data.get('topic', '')
                
                if title and topic:
                    # Regenerate thumbnail
                    thumbnail_url = await podcast_generation_service.generate_and_upload_thumbnail(
                        title=title,
                        topic=topic,
                        canonical_filename=canonical
                    )
                    
                    # Update episode document
                    episode_doc.reference.update({
                        'thumbnail_url': thumbnail_url,
                        'updated_at': datetime.utcnow().isoformat()
                    })
                    
                    # Update RSS feed
                    await rss_service.update_episode_thumbnail_in_rss(canonical, thumbnail_url)
                    
                    regenerated_count += 1
            except Exception as e:
                errors.append(f"Episode {canonical}: {str(e)}")
                structured_logger.warning("Failed to regenerate thumbnail",
                                         canonical=canonical,
                                         error=str(e))
        
        structured_logger.info("Thumbnail regeneration completed",
                              regenerated=regenerated_count,
                              errors=len(errors))
        
        return {
            "message": f"Regenerated thumbnails for {regenerated_count} episodes",
            "regenerated_count": regenerated_count,
            "errors": errors[:10]
        }
        
    except Exception as e:
        structured_logger.error("Failed to regenerate thumbnails",
                               error=str(e),
                               error_type=type(e).__name__)
        raise HTTPException(status_code=500, detail=f"Failed to regenerate thumbnails: {str(e)}")

@router.post("/podcasts/fix-all-issues")
async def fix_all_podcast_issues(admin_auth: bool = Depends(verify_admin_api_key)):
    """Comprehensive endpoint to fix all podcast issues:
    1. Revert 5 news podcasts from ever- format back to news- format
    2. Fix podcast titles to remove 'Copernicus AI: Frontiers of Science - ' prefix
    3. Update Firestore and RSS feed accordingly
    """
    if not db:
        raise HTTPException(status_code=503, detail="Firestore service is unavailable")
    
    try:
        from google.cloud import storage
        from google.api_core.exceptions import PreconditionFailed
        import xml.etree.ElementTree as ET
        import re
        from datetime import datetime
        
        structured_logger.info("Starting comprehensive fix for all podcast issues")
        
        # Mapping of current (wrong) canonical to original (correct) canonical for news podcasts
        news_reversions = {
            "ever-bio-250041": "news-bio-28032025",
            "ever-chem-250022": "news-chem-28032025",
            "ever-compsci-250031": "news-compsci-28032025",
            "ever-math-250041": "news-math-28032025",
            "ever-phys-250043": "news-phys-28032025",
        }
        
        title_prefix = "Copernicus AI: Frontiers of Science - "
        
        reverted_news = []
        title_fixes = []
        errors = []
        
        # Step 1: Revert news podcasts
        for current_canonical, original_canonical in news_reversions.items():
            try:
                # Update podcast_jobs
                jobs_query = db.collection('podcast_jobs').where('result.canonical_filename', '==', current_canonical).stream()
                for job_doc in jobs_query:
                    job_data = job_doc.to_dict() or {}
                    result = job_data.get('result', {})
                    
                    # Update canonical filename
                    job_doc.reference.update({
                        'result.canonical_filename': original_canonical,
                        'updated_at': datetime.utcnow().isoformat()
                    })
                    
                    # Update episodes collection
                    episode_doc = db.collection(EPISODE_COLLECTION_NAME).document(current_canonical).get()
                    if episode_doc.exists:
                        # Create new document with original canonical
                        episode_data = episode_doc.to_dict() or {}
                        episode_data['canonical_filename'] = original_canonical
                        
                        # Delete old document and create new one
                        db.collection(EPISODE_COLLECTION_NAME).document(original_canonical).set(episode_data)
                        episode_doc.reference.delete()
                    
                    reverted_news.append({
                        'old_canonical': current_canonical,
                        'new_canonical': original_canonical
                    })
                    break
            except Exception as e:
                errors.append(f"Failed to revert {current_canonical}: {str(e)}")
        
        # Step 2: Fix titles (remove prefix)
        all_podcasts = []
        podcast_jobs = db.collection('podcast_jobs').stream()
        for job_doc in podcast_jobs:
            job_data = job_doc.to_dict() or {}
            result = job_data.get('result', {})
            title = result.get('title', '')
            canonical = result.get('canonical_filename')
            
            if title.startswith(title_prefix):
                all_podcasts.append({
                    'type': 'podcast_jobs',
                    'doc_id': job_doc.id,
                    'canonical': canonical,
                    'old_title': title,
                    'new_title': title.replace(title_prefix, '', 1)
                })
        
        episodes = db.collection(EPISODE_COLLECTION_NAME).stream()
        for episode_doc in episodes:
            episode_data = episode_doc.to_dict() or {}
            title = episode_data.get('title', '')
            canonical = episode_doc.id
            
            if title.startswith(title_prefix):
                if not any(p.get('canonical') == canonical for p in all_podcasts):
                    all_podcasts.append({
                        'type': 'episodes',
                        'doc_id': canonical,
                        'canonical': canonical,
                        'old_title': title,
                        'new_title': title.replace(title_prefix, '', 1)
                    })
        
        # Update titles
        for podcast in all_podcasts:
            try:
                if podcast['type'] == 'podcast_jobs':
                    db.collection('podcast_jobs').document(podcast['doc_id']).update({
                        'result.title': podcast['new_title'],
                        'updated_at': datetime.utcnow().isoformat()
                    })
                elif podcast['type'] == 'episodes':
                    db.collection(EPISODE_COLLECTION_NAME).document(podcast['doc_id']).update({
                        'title': podcast['new_title'],
                        'updated_at': datetime.utcnow().isoformat()
                    })
                
                # Update RSS feed
                await rss_service.update_episode_title_in_rss(podcast['canonical'], podcast['new_title'])
                
                title_fixes.append(podcast)
            except Exception as e:
                errors.append(f"Failed to fix title for {podcast['canonical']}: {str(e)}")
        
        structured_logger.info("Fixed all podcast issues",
                              reverted_news=len(reverted_news),
                              title_fixes=len(title_fixes),
                              errors=len(errors))
        
        return {
            "message": f"Fixed all podcast issues: {len(reverted_news)} news podcasts reverted, {len(title_fixes)} titles fixed",
            "reverted_news_podcasts": reverted_news,
            "fixed_titles": title_fixes,
            "errors": errors[:10]
        }
        
    except Exception as e:
        structured_logger.error("Failed to fix all podcast issues",
                               error=str(e),
                               error_type=type(e).__name__)
        raise HTTPException(status_code=500, detail=f"Failed to fix all issues: {str(e)}")
