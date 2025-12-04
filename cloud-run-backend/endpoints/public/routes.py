"""Public and episode endpoints"""

from fastapi import APIRouter, HTTPException, Query
from typing import Optional
from datetime import datetime
import re
import traceback

from google.cloud import firestore
from google.cloud import storage

from utils.logging import structured_logger
from config.database import db
from config.constants import (
    EPISODE_COLLECTION_NAME,
    EPISODE_BASE_URL,
    RSS_BUCKET_NAME,
    _category_value_to_slug
)

router = APIRouter()


@router.get("/api/public/podcasts")
async def get_public_podcasts(category: Optional[str] = None, limit: int = 500):
    """Get all published podcasts (submitted to RSS) - Public API"""
    if not db:
        raise HTTPException(status_code=503, detail="Firestore service is unavailable")
    
    try:
        query = db.collection(EPISODE_COLLECTION_NAME).where('submitted_to_rss', '==', True)
        category_slug = _category_value_to_slug(category) if category else None
        if category_slug:
            query = query.where('category_slug', '==', category_slug)
        
        # Cap limit at 1000 to prevent excessive queries
        limit = min(limit, 1000)
        
        # Get episodes without ordering (Firestore requires index for filtered + ordered queries)
        # We'll sort in Python instead
        podcasts_query = query.limit(limit * 2)  # Get extra to account for missing fields
        podcasts = podcasts_query.stream()
        
        podcast_list = []
        for episode in podcasts:
            data = episode.to_dict() or {}
            data['episode_id'] = episode.id
            public_podcast = {
                'episode_id': episode.id,
                'title': data.get('title', 'Untitled'),
                'category': data.get('category', 'Unknown'),
                'category_slug': data.get('category_slug'),
                'expertise_level': data.get('request', {}).get('expertise_level', 'intermediate'),
                'duration': data.get('duration', '5-10 minutes'),
                'created_at': data.get('generated_at', data.get('created_at', '')),
                'status': 'published',
                'creator_attribution': data.get('creator_attribution'),
                'summary': data.get('summary'),
                'audio_url': data.get('audio_url'),
                'thumbnail_url': data.get('thumbnail_url'),
                'episode_link': data.get('episode_link'),
            }
            podcast_list.append(public_podcast)
        
        # Sort by generated_at in Python (descending - newest first)
        def get_sort_key(ep):
            gen_at = ep.get('created_at', '')
            # Handle datetime objects
            if isinstance(gen_at, datetime):
                return gen_at
            # Convert string dates to datetime for proper comparison
            if isinstance(gen_at, str):
                try:
                    # Try parsing common formats
                    for fmt in ['%Y-%m-%dT%H:%M:%S', '%a, %d %b %Y %H:%M:%S %Z', '%Y-%m-%d']:
                        try:
                            if 'T' in gen_at:
                                # ISO format with time
                                return datetime.fromisoformat(gen_at.replace('Z', '+00:00')[:19])
                            else:
                                # Try format string
                                return datetime.strptime(gen_at[:19], fmt)
                        except:
                            continue
                except:
                    pass
            # Fallback: use string comparison or very old date
            return datetime.min if isinstance(gen_at, str) and gen_at else datetime.min
        
        podcast_list.sort(key=get_sort_key, reverse=True)
        # Limit after sorting
        podcast_list = podcast_list[:limit]
        
        structured_logger.info("Found published podcasts from episode catalog",
                              podcast_count=len(podcast_list),
                              category=category_slug or category)
        
        return {
            "podcasts": podcast_list,
            "total_count": len(podcast_list),
            "category_filter": category_slug or category
        }
        
    except Exception as e:
        error_trace = traceback.format_exc()
        structured_logger.error("Error fetching public podcasts",
                               category=category,
                               error=str(e),
                               error_trace=error_trace)
        raise HTTPException(status_code=500, detail=f"Failed to fetch published podcasts: {str(e)}")


@router.get("/api/episodes")
async def list_episode_catalog(
    category: Optional[str] = Query(None),
    submitted: Optional[bool] = Query(None),
    limit: int = Query(500)
):
    """List episodes from the canonical catalog (includes drafts + published)."""
    if not db:
        raise HTTPException(status_code=503, detail="Firestore service is unavailable")
    try:
        # Cap limit at 1000 to prevent excessive queries
        limit = min(limit, 1000)
        query = db.collection(EPISODE_COLLECTION_NAME)
        if submitted is not None:
            query = query.where('submitted_to_rss', '==', submitted)
        category_slug = _category_value_to_slug(category) if category else None
        if category_slug:
            query = query.where('category_slug', '==', category_slug)
        episodes_query = query.order_by('generated_at', direction=firestore.Query.DESCENDING).limit(limit)
        episodes = []
        for doc in episodes_query.stream():
            payload = doc.to_dict() or {}
            payload['episode_id'] = doc.id
            episodes.append(payload)
        return {
            "episodes": episodes,
            "total_count": len(episodes),
            "category_filter": category_slug or category,
            "submitted_filter": submitted,
        }
    except Exception as e:
        structured_logger.error("Error listing episode catalog",
                               category=category,
                               submitted=submitted,
                               error=str(e))
        raise HTTPException(status_code=500, detail="Failed to list episodes")


@router.get("/api/episodes/search")
async def search_episodes(
    q: str = Query(...),
    limit: int = Query(100),
    search_transcripts: bool = Query(False)
):
    """Search episodes by title, description, or transcript.
    
    Args:
        q: Search query string
        limit: Maximum number of results (default 100, max 500)
        search_transcripts: If True, also search transcript content (slower, requires GCS access)
    """
    if not db:
        raise HTTPException(status_code=503, detail="Firestore service is unavailable")
    
    if not q or not q.strip():
        raise HTTPException(status_code=400, detail="Search query is required")
    
    try:
        search_terms = q.strip().lower().split()
        limit = min(limit, 500)
        
        # Fetch all episodes (or a large subset)
        # We'll filter in Python since Firestore doesn't have full-text search
        query = db.collection(EPISODE_COLLECTION_NAME)
        episodes_query = query.order_by('generated_at', direction=firestore.Query.DESCENDING).limit(1000)
        
        matching_episodes = []
        transcript_matches = set() if search_transcripts else None
        
        # First pass: search title and description
        for doc in episodes_query.stream():
            data = doc.to_dict() or {}
            episode_id = doc.id  # Fix: define episode_id here
            
            # Extract searchable text
            title = (data.get('title') or '').lower()
            description = (data.get('description_markdown') or data.get('description_html') or '').lower()
            summary = (data.get('summary') or '').lower()
            
            # Strip HTML tags from description for better matching
            description_plain = re.sub(r'<[^>]+>', '', description)
            
            # Check if all search terms match
            matches = all(term in title or term in description_plain or term in summary for term in search_terms)
            
            if matches:
                payload = data.copy()
                payload['episode_id'] = episode_id
                
                # Ensure episode_link is set (construct if missing)
                if not payload.get('episode_link') and payload.get('slug'):
                    payload['episode_link'] = f"{EPISODE_BASE_URL}/{payload.get('slug')}"
                elif not payload.get('episode_link') and payload.get('episode_id'):
                    payload['episode_link'] = f"{EPISODE_BASE_URL}/{payload.get('episode_id')}"
                
                # Ensure audio_url is included (use audio_url field)
                if not payload.get('audio_url'):
                    # Try alternative field names
                    payload['audio_url'] = data.get('audioUrl') or data.get('audio_url') or ''
                
                # Ensure slug is always included for category detection
                if not payload.get('slug') and payload.get('episode_id'):
                    payload['slug'] = payload.get('episode_id')
                
                # Debug logging
                structured_logger.debug("Search result",
                                      episode_id=episode_id,
                                      title=payload.get('title', 'No title'),
                                      slug=payload.get('slug'),
                                      has_audio_url=bool(payload.get('audio_url')),
                                      has_episode_link=bool(payload.get('episode_link')))
                
                # Add match context for highlighting
                payload['match_score'] = (
                    sum(1 for term in search_terms if term in title) * 3 +
                    sum(1 for term in search_terms if term in description_plain) * 2 +
                    sum(1 for term in search_terms if term in summary) * 2
                )
                matching_episodes.append(payload)
                if search_transcripts and data.get('transcript_url'):
                    transcript_matches.add(episode_id)
        
        # Second pass: search transcripts if requested
        if search_transcripts and transcript_matches:
            storage_client = storage.Client()
            bucket = storage_client.bucket(RSS_BUCKET_NAME)
            
            # Re-check episodes with transcripts
            for episode_id in list(transcript_matches):
                episode = next((e for e in matching_episodes if e.get('episode_id') == episode_id), None)
                if not episode:
                    continue
                
                transcript_url = episode.get('transcript_url')
                if not transcript_url:
                    continue
                
                try:
                    # Extract blob name from GCS URL
                    blob_name = transcript_url.replace('https://storage.googleapis.com/', '').split('/', 1)[1]
                    blob = bucket.blob(blob_name)
                    
                    if blob.exists():
                        transcript_content = blob.download_as_text()
                        transcript_lower = transcript_content.lower()
                        
                        # Check if all terms match in transcript
                        if all(term in transcript_lower for term in search_terms):
                            # Boost match score for transcript matches
                            episode['match_score'] = episode.get('match_score', 0) + 1
                            episode['transcript_match'] = True
                            
                            # Find first occurrence of search terms in transcript
                            first_match_position = len(transcript_content)  # Initialize to end
                            first_match_term = None
                            
                            # Find the earliest position where any search term appears
                            for term in search_terms:
                                pattern = re.compile(re.escape(term), re.IGNORECASE)
                                match = pattern.search(transcript_content)
                                if match and match.start() < first_match_position:
                                    first_match_position = match.start()
                                    first_match_term = term
                            
                            # Estimate timestamp based on position in transcript
                            # Average speaking rate: ~150 words per minute = 2.5 words per second
                            # We'll count words from the beginning to the match position
                            text_before_match = transcript_content[:first_match_position]
                            
                            # Clean text to count words accurately (remove markdown, speaker labels)
                            clean_text = re.sub(r'\*\*([^*]+)\*\*', r'\1', text_before_match)  # Remove bold
                            clean_text = re.sub(r'\*([^*]+)\*', r'\1', clean_text)  # Remove italic
                            clean_text = re.sub(r'#+\s*', '', clean_text)  # Remove headers
                            clean_text = re.sub(r'\[([^\]]+)\]\([^\)]+\)', r'\1', clean_text)  # Remove links
                            clean_text = re.sub(r'\*\*(HOST|EXPERT|QUESTIONER|CORRESPONDENT):\s*\*\*', '', clean_text, flags=re.IGNORECASE)  # Remove speaker labels
                            clean_text = re.sub(r'(HOST|EXPERT|QUESTIONER|CORRESPONDENT):\s*', '', clean_text, flags=re.IGNORECASE)  # Remove speaker labels
                            
                            # Count words
                            word_count = len(re.findall(r'\b\w+\b', clean_text))
                            
                            # Estimate timestamp (150 words/min = 2.5 words/sec, with buffer)
                            # Using 2.5 words/second as a conservative estimate
                            estimated_seconds = max(0, int(word_count / 2.5))
                            episode['transcript_timestamp'] = estimated_seconds
                            
                            # Extract snippet with context around first match
                            snippet_length = 250  # characters before and after match
                            start = max(0, first_match_position - snippet_length)
                            end = min(len(transcript_content), first_match_position + len(first_match_term) + snippet_length)
                            
                            snippet = transcript_content[start:end]
                            
                            # Clean up: remove markdown formatting for preview
                            snippet = re.sub(r'\*\*([^*]+)\*\*', r'\1', snippet)  # Remove bold
                            snippet = re.sub(r'\*([^*]+)\*', r'\1', snippet)  # Remove italic
                            snippet = re.sub(r'#+\s*', '', snippet)  # Remove headers
                            snippet = re.sub(r'\[([^\]]+)\]\([^\)]+\)', r'\1', snippet)  # Remove links
                            snippet = snippet.replace('\n\n', ' ').replace('\n', ' ').strip()
                            
                            # Add ellipsis if truncated
                            if start > 0:
                                snippet = '...' + snippet
                            if end < len(transcript_content):
                                snippet = snippet + '...'
                            
                            episode['transcript_snippet'] = snippet
                            
                except Exception as e:
                    structured_logger.warning("Could not search transcript",
                                            episode_id=episode_id,
                                            error=str(e))
        
        # Sort by match score (highest first)
        matching_episodes.sort(key=lambda x: x.get('match_score', 0), reverse=True)
        
        # Limit results
        matching_episodes = matching_episodes[:limit]
        
        return {
            "query": q,
            "episodes": matching_episodes,
            "total_count": len(matching_episodes),
            "searched_transcripts": search_transcripts,
        }
    except Exception as e:
        error_trace = traceback.format_exc()
        structured_logger.error("Error searching episodes",
                               query=q,
                               error=str(e),
                               error_trace=error_trace)
        raise HTTPException(status_code=500, detail="Failed to search episodes")


@router.get("/api/episodes/{episode_id}")
async def get_episode_record(episode_id: str):
    """Fetch a single episode from the catalog."""
    if not db:
        raise HTTPException(status_code=503, detail="Firestore service is unavailable")
    try:
        doc = db.collection(EPISODE_COLLECTION_NAME).document(episode_id).get()
        if not doc.exists:
            raise HTTPException(status_code=404, detail="Episode not found")
        payload = doc.to_dict() or {}
        payload['episode_id'] = doc.id
        return payload
    except HTTPException:
        raise
    except Exception as e:
        structured_logger.error("Error fetching episode",
                               episode_id=episode_id,
                               error=str(e))
        raise HTTPException(status_code=500, detail="Failed to load episode")
