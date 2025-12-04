"""Subscriber management endpoints"""

from fastapi import APIRouter, HTTPException
from datetime import datetime
from typing import Optional
from google.cloud import firestore

from utils.logging import structured_logger
from utils.subscriber_helpers import (
    generate_subscriber_id,
    get_subscriber_by_email,
    verify_password,
    hash_password
)
from config.database import db
from config.constants import EPISODE_COLLECTION_NAME
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


@router.post("/api/subscribers/register")
async def register_subscriber(registration: SubscriberRegistration):
    """Register a new subscriber"""
    if not db:
        raise HTTPException(status_code=503, detail="Firestore service is unavailable")
    
    subscriber_id = generate_subscriber_id(registration.email)
    structured_logger.info("Generated subscriber_id for registration",
                          email=registration.email,
                          subscriber_id=subscriber_id)
    
    # Check if subscriber already exists
    try:
        existing_doc = db.collection('subscribers').document(subscriber_id).get()
        if existing_doc.exists:
            structured_logger.info("Subscriber already exists, updating",
                                  email=registration.email,
                                  subscriber_id=subscriber_id)
            # Update existing subscriber with new password if provided
            existing_data = existing_doc.to_dict()
            if registration.password:
                existing_data['password_hash'] = hash_password(registration.password)
                existing_data['last_login'] = datetime.utcnow().isoformat()
                db.collection('subscribers').document(subscriber_id).update(existing_data)
                structured_logger.info("Updated existing subscriber password",
                                      email=registration.email)
            
            return {
                "subscriber_id": subscriber_id,
                "email": registration.email,
                "name": existing_data.get('name', registration.name),
                "subscription_tier": existing_data.get('subscription_tier', 'free'),
                "message": "Existing subscriber updated"
            }
    except Exception as e:
        structured_logger.error("Error checking existing subscriber",
                               email=registration.email,
                               error=str(e))
        raise HTTPException(status_code=500, detail="Failed to check existing subscriber")
    
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
        db.collection('subscribers').document(subscriber_id).set(subscriber_data)
        structured_logger.info("New subscriber registered",
                              email=registration.email,
                              subscriber_id=subscriber_id)
        
        return {
            "subscriber_id": subscriber_id,
            "email": registration.email,
            "name": registration.name,
            "subscription_tier": registration.subscription_tier,
            "message": "Subscriber registered successfully"
        }
    except Exception as e:
        structured_logger.error("Error registering subscriber",
                               email=registration.email,
                               error=str(e))
        raise HTTPException(status_code=500, detail="Failed to register subscriber")


@router.post("/api/subscribers/login")
async def login_subscriber(login: SubscriberLogin):
    """Authenticate a subscriber"""
    if not db:
        raise HTTPException(status_code=503, detail="Firestore service is unavailable")
    
    structured_logger.info("Login attempt",
                          email=login.email)
    
    try:
        subscriber_doc = get_subscriber_by_email(login.email)
        if not subscriber_doc:
            raise HTTPException(status_code=404, detail="Subscriber not found")
        
        # Get the actual document ID (could be old or new format)
        subscriber_id = subscriber_doc.id
        structured_logger.info("Found subscriber",
                              email=login.email,
                              subscriber_id=subscriber_id)
        
        subscriber_data = subscriber_doc.to_dict()
        
        # Verify authentication method
        if login.google_id and subscriber_data.get('google_id') == login.google_id:
            # Google OAuth authentication
            pass  # Google ID matches
        elif login.password and subscriber_data.get('password_hash'):
            # Email/password authentication
            if not verify_password(login.password, subscriber_data['password_hash']):
                raise HTTPException(status_code=401, detail="Invalid password")
        else:
            raise HTTPException(status_code=401, detail="Invalid authentication method")
        
        # Update last login
        db.collection('subscribers').document(subscriber_id).update({
            'last_login': datetime.utcnow().isoformat()
        })
        
        structured_logger.info("Subscriber login successful",
                              email=login.email,
                              subscriber_id=subscriber_id)
        
        return {
            "subscriber_id": subscriber_id,
            "email": subscriber_data['email'],
            "name": subscriber_data['name'],
            "subscription_tier": subscriber_data['subscription_tier'],
            "message": "Login successful"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        structured_logger.error("Error during login",
                               email=login.email,
                               error=str(e))
        raise HTTPException(status_code=500, detail="Login failed")


@router.get("/api/subscribers/profile/{subscriber_id}")
async def get_subscriber_profile(subscriber_id: str):
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
        
        # Calculate actual podcast count dynamically
        all_canonical_filenames = set()
        
        # Count from podcast_jobs
        try:
            jobs_query = db.collection('podcast_jobs').where('subscriber_id', '==', subscriber_id).stream()
            for job_doc in jobs_query:
                job_data = job_doc.to_dict() or {}
                result = job_data.get('result', {})
                canonical = result.get('canonical_filename')
                if canonical:
                    all_canonical_filenames.add(canonical)
                else:
                    # If no canonical, use job_id as identifier
                    all_canonical_filenames.add(job_doc.id)
        except Exception as e:
            structured_logger.debug("Could not count podcasts from jobs for subscriber profile",
                                   subscriber_id=subscriber_id,
                                   error=str(e))
        
        # Count from episodes
        try:
            episodes_query = db.collection(EPISODE_COLLECTION_NAME).where('subscriber_id', '==', subscriber_id).stream()
            for episode_doc in episodes_query:
                canonical = episode_doc.id  # Episode ID is canonical filename
                all_canonical_filenames.add(canonical)
        except Exception as e:
            structured_logger.debug("Could not count podcasts from episodes for subscriber profile",
                                   subscriber_id=subscriber_id,
                                   error=str(e))
        
        # Override stored count with actual calculated count
        actual_podcast_count = len(all_canonical_filenames)
        subscriber_data['podcasts_generated'] = actual_podcast_count
        
        return subscriber_data
        
    except HTTPException:
        raise
    except Exception as e:
        structured_logger.error("Error fetching subscriber profile",
                               subscriber_id=subscriber_id,
                               error=str(e))
        raise HTTPException(status_code=500, detail="Failed to fetch profile")


@router.put("/api/subscribers/profile/{subscriber_id}")
async def update_subscriber_profile(subscriber_id: str, updates: SubscriberProfileUpdate):
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
async def get_subscriber_podcasts(subscriber_id: str):
    """Get all podcasts generated by a subscriber"""
    if not db:
        raise HTTPException(status_code=503, detail="Firestore service is unavailable")
    
    try:
        # Query podcast_jobs collection for this subscriber
        podcasts_query = db.collection('podcast_jobs').where('subscriber_id', '==', subscriber_id).order_by('created_at', direction=firestore.Query.DESCENDING)
        podcasts = podcasts_query.stream()
        
        podcast_list = []
        # First, get all episodes to check RSS status
        episodes_by_slug = {}
        try:
            episodes_query = db.collection(EPISODE_COLLECTION_NAME).stream()
            for episode in episodes_query:
                episode_data = episode.to_dict() or {}
                slug = episode.id  # Episode ID is the canonical filename
                episodes_by_slug[slug] = {
                    'submitted_to_rss': episode_data.get('submitted_to_rss', False),
                    'title': episode_data.get('title'),
                }
        except Exception as e:
            structured_logger.warning("Could not load episodes for RSS status check",
                                     subscriber_id=subscriber_id,
                                     error=str(e))
        
        for podcast in podcasts:
            podcast_data = podcast.to_dict()
            # Add podcast ID from document ID
            podcast_data['podcast_id'] = podcast.id
            podcast_data['source'] = 'podcast_jobs'
            
            # Check RSS status from episodes collection if not set in podcast_jobs
            if not podcast_data.get('submitted_to_rss'):
                canonical = (podcast_data.get('result') or {}).get('canonical_filename')
                if canonical and canonical in episodes_by_slug:
                    podcast_data['submitted_to_rss'] = episodes_by_slug[canonical]['submitted_to_rss']
                    structured_logger.debug("Updated RSS status from episodes collection",
                                          canonical=canonical,
                                          submitted_to_rss=podcast_data['submitted_to_rss'])
            
            podcast_list.append(podcast_data)
        
        structured_logger.info("Found podcasts for subscriber",
                              subscriber_id=subscriber_id,
                              podcast_count=len(podcast_list))
        
        return {
            "subscriber_id": subscriber_id,
            "podcasts": podcast_list,
            "total_count": len(podcast_list)
        }
        
    except Exception as e:
        structured_logger.error("Error fetching subscriber podcasts",
                               subscriber_id=subscriber_id,
                               error=str(e))
        raise HTTPException(status_code=500, detail="Failed to fetch podcasts")


@router.post("/api/subscribers/podcasts/submit-to-rss")
async def submit_podcast_to_rss(submission: PodcastSubmission):
    """Submit a podcast to the RSS feed"""
    if not db:
        raise HTTPException(status_code=503, detail="Firestore service is unavailable")
    
    try:
        # Get podcast details
        podcast_doc = db.collection('podcast_jobs').document(submission.podcast_id).get()
        if not podcast_doc.exists:
            raise HTTPException(status_code=404, detail="Podcast not found")
        
        podcast_data = podcast_doc.to_dict()
        subscriber_id = podcast_data.get('subscriber_id')
        
        if not subscriber_id:
            raise HTTPException(status_code=400, detail="Podcast not associated with a subscriber")
        
        episode_service.ensure_episode_document_from_job(submission.podcast_id, podcast_data)
        canonical = (podcast_data.get('result') or {}).get('canonical_filename')
        
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
            await rss_service.update_rss_feed(podcast_data, subscriber_payload, True, creator_attribution)
                
            # Update subscriber's RSS submission count
            if subscriber_payload is not None:
                new_count = subscriber_payload.get('podcasts_submitted_to_rss', 0) + 1
                db.collection('subscribers').document(subscriber_id).update({
                    'podcasts_submitted_to_rss': new_count
                })
            
            # Update podcast with RSS info and attribution
            update_data = {
                'submitted_to_rss': True,
                'rss_submitted_at': datetime.utcnow().isoformat()
            }
            
            if creator_attribution:
                update_data['creator_attribution'] = creator_attribution
            
            db.collection('podcast_jobs').document(submission.podcast_id).update(update_data)
            rss_service.update_episode_submission_state(canonical, True, creator_attribution)
            
            structured_logger.info("Podcast submitted to RSS feed",
                                  podcast_id=submission.podcast_id,
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

            db.collection('podcast_jobs').document(submission.podcast_id).update({
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


@router.post("/api/subscribers/password-reset-request")
async def request_password_reset(reset_request: PasswordResetRequest):
    """Request a password reset for a subscriber"""
    if not db:
        raise HTTPException(status_code=503, detail="Firestore service is unavailable")
    
    subscriber_id = generate_subscriber_id(reset_request.email)
    
    try:
        subscriber_doc = db.collection('subscribers').document(subscriber_id).get()
        if not subscriber_doc.exists:
            # Don't reveal if email exists or not for security
            return {"message": "If the email exists, a password reset link has been sent"}
        
        subscriber_data = subscriber_doc.to_dict()
        
        # For now, just return success - in production, send email
        structured_logger.info("Password reset requested",
                              email=reset_request.email,
                              subscriber_id=subscriber_id)
        
        return {"message": "If the email exists, a password reset link has been sent"}
        
    except Exception as e:
        structured_logger.error("Error processing password reset request",
                               email=reset_request.email,
                               error=str(e))
        raise HTTPException(status_code=500, detail="Failed to process password reset request")


@router.post("/api/subscribers/password-reset")
async def reset_password(reset_data: PasswordReset):
    """Reset a subscriber's password"""
    if not db:
        raise HTTPException(status_code=503, detail="Firestore service is unavailable")
    
    subscriber_id = generate_subscriber_id(reset_data.email)
    
    try:
        subscriber_doc = db.collection('subscribers').document(subscriber_id).get()
        if not subscriber_doc.exists:
            raise HTTPException(status_code=404, detail="Subscriber not found")
        
        # Update password
        db.collection('subscribers').document(subscriber_id).update({
            'password_hash': hash_password(reset_data.new_password),
            'last_login': datetime.utcnow().isoformat()
        })
        
        structured_logger.info("Password reset successful",
                              email=reset_data.email,
                              subscriber_id=subscriber_id)
        
        return {"message": "Password reset successfully"}
        
    except Exception as e:
        structured_logger.error("Error resetting password",
                               email=reset_data.email,
                               error=str(e))
        raise HTTPException(status_code=500, detail="Failed to reset password")


@router.delete("/api/subscribers/podcasts/{podcast_id}")
async def delete_subscriber_podcast(podcast_id: str):
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

