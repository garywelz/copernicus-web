"""
MCP Tools for CopernicusAI Podcasts

Provides tools for querying podcast metadata stored in Firestore.
"""

import logging
from typing import Any, Dict, List, Optional
import json

from mcp_server.utils.firestore_client import (
    query_collection,
    get_document
)
from mcp_server.config import (
    COLLECTION_PODCASTS,
    COLLECTION_EPISODES,
    DEFAULT_QUERY_LIMIT,
    MAX_QUERY_LIMIT
)

logger = logging.getLogger(__name__)


async def list_podcasts(
    discipline: Optional[str] = None,
    subscriber_id: Optional[str] = None,
    limit: int = DEFAULT_QUERY_LIMIT
) -> str:
    """
    List podcasts, optionally filtered by discipline or subscriber.
    
    Args:
        discipline: Filter by discipline (e.g., "biology", "chemistry", "physics")
        subscriber_id: Filter by subscriber ID
        limit: Maximum number of results (default: 10, max: 100)
        
    Returns:
        JSON string with list of podcasts
    """
    try:
        # Validate limit
        limit = min(max(1, limit), MAX_QUERY_LIMIT)
        
        # Build filters
        filters = []
        if subscriber_id:
            filters.append(("subscriber_id", "==", subscriber_id))
        
        # Query podcast_jobs collection
        podcasts = query_collection(
            collection_name=COLLECTION_PODCASTS,
            filters=filters if filters else None,
            order_by="created_at",
            limit=limit
        )
        
        # Filter by discipline if provided (client-side filtering)
        if discipline:
            discipline_lower = discipline.lower()
            filtered_podcasts = []
            for podcast in podcasts:
                request = podcast.get("request", {})
                category = request.get("category", "").lower()
                if discipline_lower in category:
                    filtered_podcasts.append(podcast)
            podcasts = filtered_podcasts[:limit]
        
        # Format results
        results = []
        for podcast in podcasts:
            request = podcast.get("request", {})
            result = podcast.get("result", {})
            results.append({
                "job_id": podcast.get("job_id") or podcast.get("id"),
                "title": result.get("title") or request.get("topic", "Untitled"),
                "category": request.get("category"),
                "expertise_level": request.get("expertise_level"),
                "duration": result.get("duration") or request.get("duration"),
                "status": podcast.get("status"),
                "created_at": podcast.get("created_at"),
                "subscriber_id": podcast.get("subscriber_id"),
                "has_audio": bool(result.get("audio_url")),
                "submitted_to_rss": podcast.get("submitted_to_rss", False)
            })
        
        return json.dumps({
            "podcasts": results,
            "count": len(results),
            "discipline": discipline,
            "subscriber_id": subscriber_id
        }, indent=2)
        
    except Exception as e:
        logger.error(f"Error listing podcasts: {e}", exc_info=True)
        return json.dumps({
            "error": f"Failed to list podcasts: {str(e)}",
            "podcasts": [],
            "count": 0
        })


async def get_podcast_details(podcast_id: str) -> str:
    """
    Get full podcast metadata including source papers, transcript link, etc.
    
    Args:
        podcast_id: Job ID or canonical filename
        
    Returns:
        JSON string with full podcast data
    """
    try:
        # Try to get from podcast_jobs first
        podcast = get_document(COLLECTION_PODCASTS, podcast_id)
        
        if not podcast:
            # Try episodes collection
            podcast = get_document(COLLECTION_EPISODES, podcast_id)
        
        if not podcast:
            # Try searching by canonical filename
            podcasts = query_collection(
                collection_name=COLLECTION_PODCASTS,
                limit=MAX_QUERY_LIMIT
            )
            for p in podcasts:
                result = p.get("result", {})
                if result.get("canonical_filename") == podcast_id:
                    podcast = p
                    break
        
        if not podcast:
            return json.dumps({
                "error": "Podcast not found",
                "podcast": None,
                "podcast_id": podcast_id
            })
        
        # Format full details
        request = podcast.get("request", {})
        result = podcast.get("result", {})
        
        details = {
            "job_id": podcast.get("job_id") or podcast.get("id"),
            "title": result.get("title") or request.get("topic", "Untitled"),
            "category": request.get("category"),
            "expertise_level": request.get("expertise_level"),
            "duration": result.get("duration") or request.get("duration"),
            "status": podcast.get("status"),
            "created_at": podcast.get("created_at"),
            "updated_at": podcast.get("updated_at"),
            "subscriber_id": podcast.get("subscriber_id"),
            "audio_url": result.get("audio_url"),
            "transcript_url": result.get("transcript_url"),
            "description_url": result.get("description_url"),
            "thumbnail_url": result.get("thumbnail_url"),
            "canonical_filename": result.get("canonical_filename"),
            "source_papers": request.get("source_links", []),
            "paper_doi": request.get("paper_doi"),
            "paper_title": request.get("paper_title"),
            "submitted_to_rss": podcast.get("submitted_to_rss", False),
            "promoted_to_episodes": podcast.get("promoted_to_episodes", False)
        }
        
        return json.dumps({"podcast": details}, indent=2)
        
    except Exception as e:
        logger.error(f"Error getting podcast details: {e}", exc_info=True)
        return json.dumps({
            "error": f"Failed to get podcast: {str(e)}",
            "podcast": None
        })


async def get_podcast_source_papers(podcast_id: str) -> str:
    """
    Get list of source papers used in a podcast.
    
    Args:
        podcast_id: Job ID or canonical filename
        
    Returns:
        JSON string with list of source papers
    """
    try:
        # Get podcast
        podcast = get_document(COLLECTION_PODCASTS, podcast_id)
        
        if not podcast:
            # Try episodes
            podcast = get_document(COLLECTION_EPISODES, podcast_id)
        
        if not podcast:
            return json.dumps({
                "error": "Podcast not found",
                "source_papers": [],
                "count": 0
            })
        
        request = podcast.get("request", {})
        source_links = request.get("source_links", [])
        paper_doi = request.get("paper_doi")
        paper_title = request.get("paper_title")
        paper_authors = request.get("paper_authors", [])
        
        source_papers = []
        
        # Add main paper if available
        if paper_doi or paper_title:
            source_papers.append({
                "doi": paper_doi,
                "title": paper_title,
                "authors": paper_authors,
                "abstract": request.get("paper_abstract")
            })
        
        # Add additional source links
        for link in source_links:
            if isinstance(link, str):
                source_papers.append({
                    "url": link,
                    "type": "url"
                })
        
        return json.dumps({
            "podcast_id": podcast_id,
            "podcast_title": podcast.get("result", {}).get("title") or podcast.get("request", {}).get("topic"),
            "source_papers": source_papers,
            "count": len(source_papers)
        }, indent=2)
        
    except Exception as e:
        logger.error(f"Error getting podcast source papers: {e}", exc_info=True)
        return json.dumps({
            "error": f"Failed to get source papers: {str(e)}",
            "source_papers": [],
            "count": 0
        })


async def search_podcasts_by_topic(
    topic: str,
    limit: int = DEFAULT_QUERY_LIMIT
) -> str:
    """
    Search for podcasts matching a topic.
    
    Args:
        topic: Search topic (searches in title, topic, description)
        limit: Maximum number of results (default: 10, max: 100)
        
    Returns:
        JSON string with matching podcasts
    """
    try:
        # Validate limit
        limit = min(max(1, limit), MAX_QUERY_LIMIT)
        
        # Get all podcasts
        podcasts = query_collection(
            collection_name=COLLECTION_PODCASTS,
            limit=MAX_QUERY_LIMIT
        )
        
        topic_lower = topic.lower()
        matching_podcasts = []
        
        for podcast in podcasts:
            request = podcast.get("request", {})
            result = podcast.get("result", {})
            
            # Search in topic, title, and description
            topic_text = request.get("topic", "").lower()
            title = result.get("title", "").lower()
            description = result.get("description", "").lower() if result.get("description") else ""
            
            if (topic_lower in topic_text or 
                topic_lower in title or 
                topic_lower in description):
                matching_podcasts.append({
                    "job_id": podcast.get("job_id") or podcast.get("id"),
                    "title": result.get("title") or request.get("topic", "Untitled"),
                    "category": request.get("category"),
                    "expertise_level": request.get("expertise_level"),
                    "created_at": podcast.get("created_at")
                })
                
                if len(matching_podcasts) >= limit:
                    break
        
        return json.dumps({
            "topic": topic,
            "podcasts": matching_podcasts,
            "count": len(matching_podcasts)
        }, indent=2)
        
    except Exception as e:
        logger.error(f"Error searching podcasts by topic: {e}", exc_info=True)
        return json.dumps({
            "error": f"Failed to search podcasts: {str(e)}",
            "podcasts": [],
            "count": 0
        })



