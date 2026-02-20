"""Admin endpoints router

Handles all admin-related API endpoints including:
- Subscriber management
- Podcast database operations
- RSS feed management
- Episode management
"""

from fastapi import APIRouter, HTTPException, Depends, Query
from typing import Optional, List, Dict, Any
from datetime import datetime
from google.cloud import firestore

from utils.logging import structured_logger
from utils.auth import verify_admin_api_key
from config.database import db
from config.constants import EPISODE_COLLECTION_NAME

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
    subscriber_email: Optional[str] = Query(None),
    admin_auth: bool = Depends(verify_admin_api_key)
):
    """Fix missing titles for podcasts"""
    if not db:
        raise HTTPException(status_code=503, detail="Firestore service is unavailable")
    
    try:
        from utils.subscriber_helpers import generate_subscriber_id
        
        fixed_count = 0
        
        if subscriber_email:
            subscriber_id = generate_subscriber_id(subscriber_email)
            jobs = db.collection('podcast_jobs').where('subscriber_id', '==', subscriber_id).stream()
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


