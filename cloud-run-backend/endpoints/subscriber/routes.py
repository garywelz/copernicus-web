"""Subscriber management endpoints"""

from fastapi import APIRouter, BackgroundTasks, HTTPException, Depends, Header, Request
from datetime import datetime
from typing import Optional
from google.api_core.exceptions import AlreadyExists
from google.cloud import firestore

from utils.logging import structured_logger
from utils.auth import (
    require_admin_or_subscriber_owner,
    require_admin_or_podcast_owner,
)
from utils.generation_quota import current_month_key
from utils.rate_limit import check_rate_limit, last_forwarded_ip
from utils.credential_tokens import (
    PASSWORD_MAX_LENGTH,
    PASSWORD_MIN_LENGTH,
    PASSWORD_RESET_PAGE_URL,
    PURPOSE_PASSWORD_RESET,
    PURPOSE_TTL_MINUTES,
    issue_token,
    redeem_password_token,
)
from utils.subscriber_helpers import (
    generate_subscriber_id,
    get_subscriber_by_email,
    verify_password,
    hash_password,
    issue_session_token,
    verify_session_token,
)
from config.database import db
from config.constants import EPISODE_COLLECTION_NAME
import asyncio
import media_store
from email_service import EmailService
from models.subscriber import (
    SubscriberRegistration,
    SubscriberLogin,
    PasswordResetRequest,
    PasswordReset,
    SubscriberProfileUpdate,
    PodcastSubmission
)
from services.rss_service import rss_service
from services.episode_service import episode_service

router = APIRouter()

LOGIN_RATE_LIMIT_PER_HOUR = 10

SUBSCRIBER_EXISTS_DETAIL = "An account with this email already exists. Sign in instead."
RESET_REQUEST_LIMIT_PER_IP_PER_HOUR = 10
RESET_REQUEST_LIMIT_PER_ADDRESS_PER_HOUR = 3
RESET_REDEEM_LIMIT_PER_IP_PER_HOUR = 10
PASSWORD_RESET_REQUEST_MESSAGE = f"If the address belongs to an account, we have emailed a link to it. The link works once and expires in {PURPOSE_TTL_MINUTES[PURPOSE_PASSWORD_RESET]} minutes."
PASSWORD_RESET_TOKEN_INVALID_DETAIL = "This link is invalid or has expired. Request a new one."
PASSWORD_LENGTH_DETAIL = f"Password must be {PASSWORD_MIN_LENGTH} to {PASSWORD_MAX_LENGTH} characters."

email_service = EmailService()


@router.post("/api/subscribers/register")
async def register_subscriber(registration: SubscriberRegistration):
    """Register a new subscriber"""
    if not db:
        raise HTTPException(status_code=503, detail="Firestore service is unavailable")
    
    subscriber_id = generate_subscriber_id(registration.email)

    # An existing account is never modified through this route: no password is written, no field is updated.
    # get_subscriber_by_email also finds accounts stored under the older 16-character ID format.
    try:
        existing_doc = get_subscriber_by_email(registration.email)
    except Exception as e:
        structured_logger.error("Error checking existing subscriber", error=str(e))
        raise HTTPException(status_code=500, detail="Failed to check existing subscriber")
    if existing_doc is not None:
        structured_logger.info("Registration refused: subscriber already exists", subscriber_id=existing_doc.id)
        raise HTTPException(status_code=409, detail=SUBSCRIBER_EXISTS_DETAIL)

    # Create new subscriber
    subscriber_data = {
        'subscriber_id': subscriber_id,
        'email': registration.email,
        'name': registration.name,
        'subscription_tier': registration.subscription_tier,
        'subscription_status': 'active',
        'created_at': datetime.utcnow().isoformat(),
        'last_login': datetime.utcnow().isoformat(),
        'podcasts_generated': 0,
        'podcasts_submitted_to_rss': 0,
        'google_id': registration.google_id,
        'password_hash': hash_password(registration.password) if registration.password else None,
        
        # RSS Attribution fields (Phase 2.1)
        'display_name': registration.display_name,
        'initials': registration.initials,
        'show_attribution': registration.show_attribution
    }
    
    try:
        # create() fails if the document exists, so two concurrent registrations cannot overwrite each other.
        db.collection('subscribers').document(subscriber_id).create(subscriber_data)
        structured_logger.info("New subscriber registered",
                              subscriber_id=subscriber_id)
        
        return {
            "subscriber_id": subscriber_id,
            "email": registration.email,
            "name": registration.name,
            "subscription_tier": registration.subscription_tier,
            "message": "Subscriber registered successfully"
        }
    except AlreadyExists:
        structured_logger.info("Registration refused: subscriber already exists", subscriber_id=subscriber_id)
        raise HTTPException(status_code=409, detail=SUBSCRIBER_EXISTS_DETAIL)
    except Exception as e:
        structured_logger.error("Error registering subscriber",
                               error_type=type(e).__name__)
        raise HTTPException(status_code=500, detail="Failed to register subscriber")


@router.post("/api/subscribers/login")
async def login_subscriber(login: SubscriberLogin, request: Request):
    """Authenticate a subscriber"""
    client_ip = last_forwarded_ip(request.headers.get("x-forwarded-for"))
    check_rate_limit(db, client_ip, "subscriber_login", limit=LOGIN_RATE_LIMIT_PER_HOUR, window_seconds=3600)

    if not db:
        raise HTTPException(status_code=503, detail="Firestore service is unavailable")

    structured_logger.info("Login attempt")
    
    try:
        subscriber_doc = get_subscriber_by_email(login.email)
        if not subscriber_doc:
            raise HTTPException(status_code=404, detail="Subscriber not found")
        
        # Get the actual document ID (could be old or new format)
        subscriber_id = subscriber_doc.id
        structured_logger.info("Found subscriber",
                              subscriber_id=subscriber_id)
        
        subscriber_data = subscriber_doc.to_dict()

        # Verify authentication method
        update_fields = {}
        if login.google_id and subscriber_data.get('google_id') == login.google_id:
            # Google OAuth authentication
            pass  # Google ID matches
        elif login.password and subscriber_data.get('password_hash'):
            # Email/password authentication
            matched, was_legacy = verify_password(login.password, subscriber_data['password_hash'])
            if not matched:
                raise HTTPException(status_code=401, detail="Invalid password")
            if was_legacy:
                # Security lockdown Step 2: migrate off the old reversible
                # hex "hash" the moment we see a correct legacy password.
                update_fields['password_hash'] = hash_password(login.password)
        else:
            raise HTTPException(status_code=401, detail="Invalid authentication method")

        # Issue a fresh session token. Only its sha256 and an expiry are
        # stored; the raw token is returned once, here, and never persisted.
        raw_token, token_hash, token_expires = issue_session_token()
        update_fields['last_login'] = datetime.utcnow().isoformat()
        update_fields['session_token_hash'] = token_hash
        update_fields['session_token_expires'] = token_expires
        db.collection('subscribers').document(subscriber_id).update(update_fields)

        structured_logger.info("Subscriber login successful",
                              subscriber_id=subscriber_id)

        return {
            "subscriber_id": subscriber_id,
            "email": subscriber_data['email'],
            "name": subscriber_data['name'],
            "subscription_tier": subscriber_data['subscription_tier'],
            "session_token": raw_token,
            "session_token_expires": token_expires,
            "can_generate": subscriber_data.get('can_generate', False),
            "monthly_quota": subscriber_data.get('monthly_quota'),
            "generations_this_month": subscriber_data.get('generations_this_month', 0)
                if subscriber_data.get('generation_month') == current_month_key() else 0,
            "message": "Login successful"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        structured_logger.error("Error during login",
                               error_type=type(e).__name__)
        raise HTTPException(status_code=500, detail="Login failed")


@router.get("/api/subscribers/profile/{subscriber_id}")
async def get_subscriber_profile(subscriber_id: str, auth: dict = Depends(require_admin_or_subscriber_owner)):
    """Get subscriber profile information"""
    if not db:
        raise HTTPException(status_code=503, detail="Firestore service is unavailable")
    
    try:
        subscriber_doc = db.collection('subscribers').document(subscriber_id).get()
        if not subscriber_doc.exists:
            raise HTTPException(status_code=404, detail="Subscriber not found")
        
        subscriber_data = subscriber_doc.to_dict()
        
        # Remove sensitive data
        subscriber_data.pop('password_hash', None)
        
        # Calculate actual podcast count - use UNION counting (podcast_jobs + episodes) to match what's shown in "View Podcasts"
        # This ensures the count matches what users see when they view their podcast list
        try:
            unique_podcasts = set()
            
            # Count from podcast_jobs
            jobs_query = db.collection('podcast_jobs').where('subscriber_id', '==', subscriber_id).stream()
            for job_doc in jobs_query:
                job_data = job_doc.to_dict() or {}
                result = job_data.get('result', {})
                canonical = result.get('canonical_filename')
                if canonical:
                    unique_podcasts.add(canonical)
                else:
                    unique_podcasts.add(job_doc.id)
            
            # Count from episodes
            episodes_query = db.collection(EPISODE_COLLECTION_NAME).where('subscriber_id', '==', subscriber_id).stream()
            for episode_doc in episodes_query:
                unique_podcasts.add(episode_doc.id)
            
            actual_podcast_count = len(unique_podcasts)
        except Exception as e:
            structured_logger.debug("Could not count podcasts for subscriber profile",
                                   subscriber_id=subscriber_id,
                                   error=str(e))
            actual_podcast_count = 0
        subscriber_data['podcasts_generated'] = actual_podcast_count
        
        # Calculate RSS submission count dynamically
        rss_count = 0
        try:
            # Count episodes that are submitted to RSS
            episodes_query = db.collection(EPISODE_COLLECTION_NAME).where('subscriber_id', '==', subscriber_id).stream()
            for episode_doc in episodes_query:
                episode_data = episode_doc.to_dict() or {}
                if episode_data.get('submitted_to_rss', False):
                    rss_count += 1
        except Exception as e:
            structured_logger.debug("Could not count RSS submissions for subscriber profile",
                                   subscriber_id=subscriber_id,
                                   error=str(e))
        
        # Override stored RSS count with actual calculated count
        subscriber_data['podcasts_submitted_to_rss'] = rss_count
        
        return subscriber_data
        
    except HTTPException:
        raise
    except Exception as e:
        structured_logger.error("Error fetching subscriber profile",
                               subscriber_id=subscriber_id,
                               error=str(e))
        raise HTTPException(status_code=500, detail="Failed to fetch profile")


@router.put("/api/subscribers/profile/{subscriber_id}")
async def update_subscriber_profile(subscriber_id: str, updates: SubscriberProfileUpdate, auth: dict = Depends(require_admin_or_subscriber_owner)):
    """Update subscriber profile information"""
    if not db:
        raise HTTPException(status_code=503, detail="Firestore service is unavailable")
    
    try:
        subscriber_doc = db.collection('subscribers').document(subscriber_id).get()
        if not subscriber_doc.exists:
            raise HTTPException(status_code=404, detail="Subscriber not found")
        
        # Build update dictionary only with provided fields
        update_data = {}
        if updates.name is not None:
            update_data['name'] = updates.name
        if updates.display_name is not None:
            update_data['display_name'] = updates.display_name
        if updates.initials is not None:
            update_data['initials'] = updates.initials
        if updates.show_attribution is not None:
            update_data['show_attribution'] = updates.show_attribution
        
        if not update_data:
            raise HTTPException(status_code=400, detail="No fields to update")
        
        # Update the document
        db.collection('subscribers').document(subscriber_id).update(update_data)
        
        structured_logger.info("Updated subscriber profile",
                              subscriber_id=subscriber_id)
        
        # Return updated data
        updated_doc = db.collection('subscribers').document(subscriber_id).get()
        updated_data = updated_doc.to_dict()
        updated_data.pop('password_hash', None)
        
        return updated_data
        
    except HTTPException:
        raise
    except Exception as e:
        structured_logger.error("Error updating subscriber profile",
                               subscriber_id=subscriber_id,
                               error=str(e))
        raise HTTPException(status_code=500, detail="Failed to update profile")


@router.get("/api/subscribers/podcasts/{subscriber_id}")
async def get_subscriber_podcasts(subscriber_id: str, auth: dict = Depends(require_admin_or_subscriber_owner)):
    """Get all podcasts generated by a subscriber - queries both podcast_jobs and episodes collections"""
    if not db:
        raise HTTPException(status_code=503, detail="Firestore service is unavailable")
    
    try:
        from google.cloud import firestore
        
        podcasts_list = []
        podcasts_by_id = {}  # Track by podcast_id/canonical to avoid duplicates
        
        # Get podcasts from podcast_jobs collection
        try:
            jobs_query = db.collection('podcast_jobs').where('subscriber_id', '==', subscriber_id).order_by('created_at', direction=firestore.Query.DESCENDING)
            jobs = jobs_query.stream()
            
            for job_doc in jobs:
                job_data = job_doc.to_dict() or {}
                result = job_data.get('result', {})
                canonical = result.get('canonical_filename')
                podcast_id = canonical or job_doc.id
                
                if podcast_id and podcast_id not in podcasts_by_id:
                    # Get title from multiple sources
                    title = (
                        result.get('title') or 
                        job_data.get('request', {}).get('topic') or 
                        'Untitled'
                    )
                    
                    podcasts_by_id[podcast_id] = {
                        'podcast_id': podcast_id,
                        'id': podcast_id,
                        'canonical_filename': canonical,
                        'title': title,
                        'topic': job_data.get('request', {}).get('topic', ''),
                        'category': job_data.get('request', {}).get('category', ''),
                        'subscriber_id': subscriber_id,
                        'submitted_to_rss': job_data.get('submitted_to_rss', False),
                        'created_at': job_data.get('created_at') or job_data.get('updated_at'),
                        'request': job_data.get('request', {}),
                        'result': result,
                        'status': job_data.get('status', 'unknown'),
                        'source': 'podcast_jobs'
                    }
        except Exception as e:
            structured_logger.warning("Could not load podcasts from podcast_jobs",
                                     subscriber_id=subscriber_id,
                                     error=str(e))
        
        # Get podcasts from episodes collection and merge/update with episode data
        try:
            # IMPORTANT: Order episodes by created_at DESCENDING to get newest first
            episodes_query = db.collection(EPISODE_COLLECTION_NAME).where('subscriber_id', '==', subscriber_id).order_by('created_at', direction=firestore.Query.DESCENDING).stream()
            
            for episode_doc in episodes_query:
                episode_data = episode_doc.to_dict() or {}
                canonical = episode_doc.id
                
                if canonical in podcasts_by_id:
                    # Update existing podcast with episode data
                    existing_podcast = podcasts_by_id[canonical]
                    
                    # ALWAYS prioritize episode title - match admin endpoint logic exactly
                    episode_title = episode_data.get('title')
                    
                    # Always prefer episode title if it exists and is valid (same as admin endpoint)
                    if episode_title and episode_title.strip() and episode_title != 'Untitled':
                        final_title = episode_title
                    else:
                        # Fallback: use existing title from podcast_jobs if it's valid
                        final_title = existing_podcast.get('title', 'Untitled')
                    
                    # Update result object with all URLs from episodes (frontend expects podcast.result.*)
                    result_obj = existing_podcast.get('result', {}).copy()
                    result_obj.update({
                        'audio_url': episode_data.get('audio_url') or result_obj.get('audio_url'),
                        'thumbnail_url': episode_data.get('thumbnail_url') or result_obj.get('thumbnail_url'),
                        'transcript_url': episode_data.get('transcript_url') or result_obj.get('transcript_url'),
                    })
                    
                    # Prioritize episode created_at for sorting (episodes are the source of truth)
                    episode_created_at = episode_data.get('created_at') or episode_data.get('generated_at')
                    
                    podcasts_by_id[canonical].update({
                        'title': final_title,
                        'submitted_to_rss': episode_data.get('submitted_to_rss', podcasts_by_id[canonical].get('submitted_to_rss', False)),
                        'audio_url': episode_data.get('audio_url') or result_obj.get('audio_url'),
                        'thumbnail_url': episode_data.get('thumbnail_url') or result_obj.get('thumbnail_url'),
                        'result': result_obj,  # Ensure result object has all URLs for frontend
                        # Update created_at with episode timestamp if available (more accurate for sorting)
                        'created_at': episode_created_at or podcasts_by_id[canonical].get('created_at')
                    })
                else:
                    # New podcast only in episodes - need to create request object for frontend compatibility
                    request_obj = {
                        'topic': episode_data.get('title') or episode_data.get('topic', ''),
                        'category': episode_data.get('category', ''),
                        'expertise_level': episode_data.get('expertise_level', ''),
                        'duration': episode_data.get('duration', '')
                    }
                    
                    # Create result object with all URLs from episodes (frontend expects podcast.result.*)
                    result_obj_episodes = {
                        'audio_url': episode_data.get('audio_url'),
                        'thumbnail_url': episode_data.get('thumbnail_url'),
                        'transcript_url': episode_data.get('transcript_url'),
                    }
                    
                    # Use episode created_at or generated_at for accurate sorting
                    episode_timestamp = episode_data.get('created_at') or episode_data.get('generated_at') or ''
                    
                    podcasts_by_id[canonical] = {
                        'podcast_id': canonical,
                        'id': canonical,
                        'canonical_filename': canonical,
                        'title': episode_data.get('title') or episode_data.get('topic') or request_obj.get('topic') or 'Untitled',
                        'topic': episode_data.get('topic', ''),
                        'category': episode_data.get('category', ''),
                        'subscriber_id': subscriber_id,
                        'submitted_to_rss': episode_data.get('submitted_to_rss', False),
                        'created_at': episode_timestamp,  # Use episode timestamp for accurate sorting
                        'audio_url': episode_data.get('audio_url'),
                        'thumbnail_url': episode_data.get('thumbnail_url'),
                        'request': request_obj,  # Add request object for frontend compatibility
                        'result': result_obj_episodes,  # Add result object with URLs for frontend
                        'status': 'completed',
                        'source': 'episodes'
                    }
        except Exception as e:
            structured_logger.warning("Could not load podcasts from episodes",
                                     subscriber_id=subscriber_id,
                                     error=str(e))
        
        # Convert dict to list and sort by created_at (newest first)
        podcasts_list = list(podcasts_by_id.values())
        
        # Sort with proper date handling - newest podcasts first
        # Use updated_at as fallback if created_at is missing
        def get_sort_key(podcast):
            # Try created_at first, then updated_at, then generated_at
            timestamp = (
                podcast.get('created_at') or 
                podcast.get('updated_at') or 
                podcast.get('generated_at') or
                podcast.get('result', {}).get('generated_at') or
                ''
            )
            
            # Handle ISO format timestamps (string comparison works for ISO8601)
            # Empty strings sort to the end
            if not timestamp:
                return ''  # Will sort last
            # Ensure we have a string for comparison
            if isinstance(timestamp, str):
                # Normalize timestamp format for comparison
                # Remove timezone info if present for consistent sorting
                timestamp = timestamp.replace('+00:00', '').replace('Z', '')
                return timestamp
            # If it's a datetime object, convert to ISO string
            if hasattr(timestamp, 'isoformat'):
                return timestamp.isoformat()
            return str(timestamp)
        
        podcasts_list.sort(key=get_sort_key, reverse=True)
        
        # Log first few podcasts for debugging
        if podcasts_list:
            structured_logger.debug("Podcasts sorted - first 3 timestamps",
                                  first_timestamp=podcasts_list[0].get('created_at'),
                                  second_timestamp=podcasts_list[1].get('created_at') if len(podcasts_list) > 1 else None,
                                  third_timestamp=podcasts_list[2].get('created_at') if len(podcasts_list) > 2 else None)
        
        structured_logger.info("Found podcasts for subscriber",
                              subscriber_id=subscriber_id,
                              podcast_count=len(podcasts_list))
        
        return {
            "subscriber_id": subscriber_id,
            "podcasts": podcasts_list,
            "total_count": len(podcasts_list)
        }
        
    except Exception as e:
        structured_logger.error("Error fetching subscriber podcasts",
                               subscriber_id=subscriber_id,
                               error=str(e))
        raise HTTPException(status_code=500, detail="Failed to fetch podcasts")


@router.post("/api/subscribers/podcasts/submit-to-rss")
async def submit_podcast_to_rss(
    submission: PodcastSubmission,
    x_admin_api_key: Optional[str] = Header(None, alias="X-Admin-API-Key"),
    x_subscriber_token: Optional[str] = Header(None, alias="X-Subscriber-Token"),
):
    """Submit a podcast to the RSS feed"""
    if not db:
        raise HTTPException(status_code=503, detail="Firestore service is unavailable")
    
    try:
        # The podcast_id might be either a job ID or a canonical filename
        # Try to find by document ID first (if it's a job ID)
        podcast_doc = db.collection('podcast_jobs').document(submission.podcast_id).get()
        podcast_data = None
        job_id = None
        
        if podcast_doc.exists:
            # Found by job ID
            podcast_data = podcast_doc.to_dict()
            job_id = submission.podcast_id
            structured_logger.info("Found podcast by job ID",
                                  job_id=job_id,
                                  podcast_id=submission.podcast_id)
        else:
            # Not found by job ID - try searching by canonical filename
            # Search in podcast_jobs where canonical_filename matches
            jobs_query = db.collection('podcast_jobs').where('result.canonical_filename', '==', submission.podcast_id).limit(1).stream()
            job_found = False
            for job_doc in jobs_query:
                podcast_data = job_doc.to_dict()
                job_id = job_doc.id
                job_found = True
                structured_logger.info("Found podcast by canonical filename",
                                      canonical=submission.podcast_id,
                                      job_id=job_id)
                break
            
            if not job_found:
                # Also check episodes collection (canonical filename is the document ID there)
                episode_doc = db.collection(EPISODE_COLLECTION_NAME).document(submission.podcast_id).get()
                if episode_doc.exists:
                    # Found in episodes - need to find corresponding job
                    episode_data = episode_doc.to_dict()
                    subscriber_id_from_ep = episode_data.get('subscriber_id')
                    if subscriber_id_from_ep:
                        # Search for job with this canonical and subscriber
                        jobs_query = db.collection('podcast_jobs').where(
                            'subscriber_id', '==', subscriber_id_from_ep
                        ).where(
                            'result.canonical_filename', '==', submission.podcast_id
                        ).limit(1).stream()
                        for job_doc in jobs_query:
                            podcast_data = job_doc.to_dict()
                            job_id = job_doc.id
                            structured_logger.info("Found podcast via episode collection",
                                                  canonical=submission.podcast_id,
                                                  job_id=job_id)
                            break
        
        if not podcast_data or not job_id:
            raise HTTPException(status_code=404, detail=f"Podcast not found: {submission.podcast_id}")
        
        subscriber_id = podcast_data.get('subscriber_id')

        if not subscriber_id:
            raise HTTPException(status_code=400, detail="Podcast not associated with a subscriber")

        require_admin_or_podcast_owner(subscriber_id, x_admin_api_key, x_subscriber_token)

        # Ensure episode document exists (use job_id for this)
        episode_service.ensure_episode_document_from_job(job_id, podcast_data)
        canonical = (podcast_data.get('result') or {}).get('canonical_filename') or submission.podcast_id
        
        # Update podcast to mark as submitted to RSS
        if submission.submit_to_rss:
            # Get subscriber attribution info if they opted in
            subscriber_doc = db.collection('subscribers').document(subscriber_id).get()
            creator_attribution = None
            subscriber_payload = subscriber_doc.to_dict() if subscriber_doc.exists else None
            
            if subscriber_doc.exists:
                subscriber_data = subscriber_payload
                # Check if user wants attribution
                if subscriber_data.get('show_attribution', False):
                    initials = subscriber_data.get('initials')
                    if initials:
                        creator_attribution = initials
                    elif subscriber_data.get('display_name'):
                        display_name = subscriber_data['display_name']
                        creator_attribution = "".join(part[0].upper() for part in display_name.split() if part).strip() or None

            # Update RSS feed with new entry before committing Firestore changes
            # A new episode's files are private: copy them to the public bucket (every copy verified) BEFORE the feed write. Fail closed.
            try:
                promotion = await asyncio.to_thread(media_store.promote, canonical)
            except media_store.MediaError as media_error:
                structured_logger.error("Media promotion failed; nothing was published", canonical=canonical, error=str(media_error))
                raise HTTPException(status_code=500, detail="Could not publish the episode's files; nothing was changed")
            try:
                await rss_service.update_rss_feed(podcast_data, subscriber_payload, True, creator_attribution)
            except Exception:
                # The feed was not written: take the public copies made a moment ago back out, so a private episode is not left exposed
                await asyncio.to_thread(media_store.demote, promotion.get("objects", []))
                raise
                
            # Update subscriber's RSS submission count
            if subscriber_payload is not None:
                new_count = subscriber_payload.get('podcasts_submitted_to_rss', 0) + 1
                db.collection('subscribers').document(subscriber_id).update({
                    'podcasts_submitted_to_rss': new_count
                })
            
            # Update podcast with RSS info and attribution
            update_data = {
                'submitted_to_rss': True,
                'media_state': 'public',
                'rss_submitted_at': datetime.utcnow().isoformat()
            }
            
            if creator_attribution:
                update_data['creator_attribution'] = creator_attribution
            
            # Use job_id (not submission.podcast_id which might be canonical)
            db.collection('podcast_jobs').document(job_id).update(update_data)
            rss_service.update_episode_submission_state(canonical, True, creator_attribution)
            
            structured_logger.info("Podcast submitted to RSS feed",
                                  podcast_id=submission.podcast_id,
                                  job_id=job_id,
                                  canonical=canonical,
                                  creator_attribution=creator_attribution if creator_attribution else None)
            
            return {
                "podcast_id": submission.podcast_id,
                "submitted_to_rss": True,
                "creator_attribution": creator_attribution,
                "message": "Podcast successfully submitted to RSS feed"
            }
        else:
            # Remove from RSS feed
            subscriber_doc = db.collection('subscribers').document(subscriber_id).get()
            await rss_service.update_rss_feed(podcast_data, subscriber_doc.to_dict() if subscriber_doc.exists else None, False, None)

            # Use job_id (not submission.podcast_id which might be canonical)
            db.collection('podcast_jobs').document(job_id).update({
                'submitted_to_rss': False,
                'rss_removed_at': datetime.utcnow().isoformat()
            })
            rss_service.update_episode_submission_state(canonical, False, None)

            if subscriber_doc.exists:
                subscriber_data = subscriber_doc.to_dict()
                current_count = subscriber_data.get('podcasts_submitted_to_rss', 0)
                db.collection('subscribers').document(subscriber_id).update({
                    'podcasts_submitted_to_rss': max(current_count - 1, 0)
                })
            
            structured_logger.info("Podcast removed from RSS feed",
                                  podcast_id=submission.podcast_id)
            
            return {
                "podcast_id": submission.podcast_id,
                "submitted_to_rss": False,
                "message": "Podcast removed from RSS feed"
            }
        
    except HTTPException:
        raise
    except Exception as e:
        structured_logger.error("Error submitting podcast to RSS",
                               podcast_id=submission.podcast_id if hasattr(submission, 'podcast_id') else None,
                               error=str(e))
        raise HTTPException(status_code=500, detail="Failed to submit podcast to RSS")


async def _send_password_reset_link(email: str):
    """Runs after the response is sent, so the caller sees the same answer and timing whether or not the address has an
    account. Writes no address and no token to any log."""
    try:
        email = (email or "").strip()
        if not email or len(email) > 254:
            return
        try:
            check_rate_limit(db, email.lower(), "password_reset_request_address",
                             limit=RESET_REQUEST_LIMIT_PER_ADDRESS_PER_HOUR, window_seconds=3600, fail_closed=True)
        except HTTPException:
            return  # over the per-address limit (or the limiter is down): send nothing, say nothing
        subscriber_doc = None
        for candidate in dict.fromkeys([email, email.lower()]):
            subscriber_doc = get_subscriber_by_email(candidate)
            if subscriber_doc:
                break
        if not subscriber_doc:
            return
        stored_address = (subscriber_doc.to_dict() or {}).get('email')
        if not stored_address:
            return
        raw_token = issue_token(db, subscriber_doc.id, PURPOSE_PASSWORD_RESET)
        await email_service.send_credential_link_email(
            stored_address, f"{PASSWORD_RESET_PAGE_URL}#token={raw_token}", PURPOSE_TTL_MINUTES[PURPOSE_PASSWORD_RESET])
    except Exception as e:
        structured_logger.error("Password reset request could not be completed", error_type=type(e).__name__)


@router.post("/api/subscribers/password-reset-request")
async def request_password_reset(reset_request: PasswordResetRequest, request: Request, background_tasks: BackgroundTasks):
    """Email a single-use, expiring link to the address on an account. The answer is identical for every address."""
    client_ip = last_forwarded_ip(request.headers.get("x-forwarded-for"))
    check_rate_limit(db, client_ip, "password_reset_request", limit=RESET_REQUEST_LIMIT_PER_IP_PER_HOUR,
                     window_seconds=3600, fail_closed=True)
    background_tasks.add_task(_send_password_reset_link, reset_request.email)
    return {"message": PASSWORD_RESET_REQUEST_MESSAGE}


@router.post("/api/subscribers/password-reset")
async def reset_password(reset: PasswordReset, request: Request):
    """Set a new password with the single-use token from the emailed link. The token alone identifies the account; the
    request carries no address. An unknown, used or expired token gets one and the same refusal."""
    client_ip = last_forwarded_ip(request.headers.get("x-forwarded-for"))
    check_rate_limit(db, client_ip, "password_reset_redeem", limit=RESET_REDEEM_LIMIT_PER_IP_PER_HOUR,
                     window_seconds=3600, fail_closed=True)
    if not (PASSWORD_MIN_LENGTH <= len(reset.new_password) <= PASSWORD_MAX_LENGTH):
        raise HTTPException(status_code=400, detail=PASSWORD_LENGTH_DETAIL)  # the token is not spent
    if not db:
        raise HTTPException(status_code=503, detail="Firestore service is unavailable")
    try:
        subscriber_id = redeem_password_token(db, reset.token, hash_password(reset.new_password))
    except Exception as e:
        structured_logger.error("Password reset could not be completed", error_type=type(e).__name__)
        raise HTTPException(status_code=500, detail="Failed to reset password")
    if not subscriber_id:
        raise HTTPException(status_code=400, detail=PASSWORD_RESET_TOKEN_INVALID_DETAIL)
    return {"message": "Password updated. You can now sign in."}


@router.delete("/api/subscribers/podcasts/{podcast_id}")
async def delete_subscriber_podcast(
    podcast_id: str,
    x_admin_api_key: Optional[str] = Header(None, alias="X-Admin-API-Key"),
    x_subscriber_token: Optional[str] = Header(None, alias="X-Subscriber-Token"),
):
    """Delete a podcast generated by a subscriber"""
    if not db:
        raise HTTPException(status_code=503, detail="Firestore service is unavailable")

    try:
        # Get podcast details to verify it exists
        podcast_doc = db.collection('podcast_jobs').document(podcast_id).get()
        if not podcast_doc.exists:
            raise HTTPException(status_code=404, detail="Podcast not found")

        podcast_data = podcast_doc.to_dict()
        subscriber_id = podcast_data.get('subscriber_id')
        canonical = (podcast_data.get('result') or {}).get('canonical_filename')

        if not subscriber_id:
            raise HTTPException(status_code=400, detail="Podcast not associated with a subscriber")

        require_admin_or_podcast_owner(subscriber_id, x_admin_api_key, x_subscriber_token)

        # Delete the podcast
        db.collection('podcast_jobs').document(podcast_id).delete()
        if canonical:
            db.collection(EPISODE_COLLECTION_NAME).document(canonical).delete()
        
        # Update subscriber's podcast count
        subscriber_doc = db.collection('subscribers').document(subscriber_id).get()
        if subscriber_doc.exists:
            subscriber_data = subscriber_doc.to_dict()
            current_count = subscriber_data.get('podcasts_generated', 0)
            if current_count > 0:
                db.collection('subscribers').document(subscriber_id).update({
                    'podcasts_generated': current_count - 1
                })
        
        structured_logger.info("Podcast deleted successfully",
                              podcast_id=podcast_id,
                              subscriber_id=subscriber_id)
        
        return {"message": "Podcast deleted successfully"}
        
    except Exception as e:
        structured_logger.error("Error deleting podcast",
                               podcast_id=podcast_id,
                               subscriber_id=subscriber_id,
                               error=str(e))
        raise HTTPException(status_code=500, detail="Failed to delete podcast")

