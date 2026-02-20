"""
Auto-Embedding Utility

Automatically generates and stores embeddings when content is created or updated.
Integrates with content creation pipelines.
"""

import logging
from typing import Dict, Any, Optional
from datetime import datetime

from services.embedding_service import get_embedding_service
from utils.logging import structured_logger

logger = logging.getLogger(__name__)


def create_text_for_paper(paper_data: Dict[str, Any]) -> str:
    """Create text representation of paper for embedding."""
    parts = []
    
    if paper_data.get('title'):
        parts.append(paper_data['title'])
    
    if paper_data.get('abstract'):
        parts.append(paper_data['abstract'])
    
    if paper_data.get('keywords'):
        if isinstance(paper_data['keywords'], list):
            parts.append(' '.join(paper_data['keywords']))
        else:
            parts.append(str(paper_data['keywords']))
    
    # Add entities if available
    preprocessing = paper_data.get('preprocessing', {})
    if preprocessing:
        entities = preprocessing.get('entities_extracted', {})
        if entities and isinstance(entities, dict):
            for entity_type, entity_list in entities.items():
                if isinstance(entity_list, list):
                    parts.append(' '.join(str(e) for e in entity_list[:10]))  # First 10 entities
    
    return '\n'.join(parts)


def create_text_for_podcast(podcast_data: Dict[str, Any]) -> str:
    """Create text representation of podcast for embedding."""
    parts = []
    
    # Get title from result or top level
    result = podcast_data.get('result', {})
    title = result.get('title') or podcast_data.get('title')
    if title:
        parts.append(title)
    
    # Get description
    description = result.get('description') or podcast_data.get('description')
    if description:
        parts.append(description)
    
    # Get transcript (first 1000 chars)
    transcript = result.get('script') or podcast_data.get('transcript') or podcast_data.get('script')
    if transcript:
        parts.append(str(transcript)[:1000])
    
    # Add topic
    topic = result.get('topic') or podcast_data.get('topic')
    if topic:
        parts.append(f"Topic: {topic}")
    
    return '\n'.join(parts)


async def generate_and_store_embedding(
    collection_name: str,
    document_id: str,
    content_data: Dict[str, Any],
    content_type: str = "auto"
) -> Optional[list]:
    """
    Generate embedding for content and store it in Firestore.
    
    Args:
        collection_name: Firestore collection name
        document_id: Document ID
        content_data: Content data dictionary
        content_type: Type of content ("paper", "podcast", or "auto" to detect)
    
    Returns:
        Embedding vector if successful, None otherwise
    """
    try:
        # Skip if already has embedding
        if content_data.get('embedding'):
            structured_logger.debug(
                f"Document {document_id} already has embedding, skipping",
                collection=collection_name
            )
            return content_data.get('embedding')
        
        # Determine content type if auto
        if content_type == "auto":
            if 'abstract' in content_data or 'doi' in content_data:
                content_type = "paper"
            elif 'result' in content_data or 'script' in content_data:
                content_type = "podcast"
            else:
                content_type = "paper"  # Default
        
        # Create text for embedding
        if content_type == "paper":
            text = create_text_for_paper(content_data)
        elif content_type == "podcast":
            text = create_text_for_podcast(content_data)
        else:
            structured_logger.warning(
                f"Unknown content type: {content_type}, skipping embedding",
                document_id=document_id
            )
            return None
        
        if not text or not text.strip():
            structured_logger.warning(
                f"No text content to embed for {document_id}",
                content_type=content_type
            )
            return None
        
        # Generate embedding
        embedding_service = get_embedding_service()
        embedding = embedding_service.embed_text(text)
        
        # Store embedding in Firestore (as Vector type for vector search)
        from mcp_server.utils.firestore_client import get_firestore_client
        from google.cloud.firestore_v1.vector import Vector
        db = get_firestore_client()
        doc_ref = db.collection(collection_name).document(document_id)
        
        doc_ref.update({
            'embedding': Vector(embedding),  # Convert to Vector type for Firestore
            'embedding_model': 'text-embedding-004',
            'embedding_updated': datetime.utcnow().isoformat()
        })
        
        structured_logger.info(
            f"Embedding generated and stored for {content_type}",
            document_id=document_id,
            collection=collection_name,
            embedding_dimension=len(embedding)
        )
        
        return embedding
        
    except Exception as e:
        structured_logger.error(
            f"Failed to generate embedding for {document_id}",
            error=str(e),
            content_type=content_type,
            collection=collection_name
        )
        # Don't raise - embedding generation failure shouldn't break content creation
        return None


def add_embedding_to_paper_data(paper_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Add embedding to paper data dictionary (for batch operations).
    
    This generates the embedding but doesn't store it - caller must store the data.
    """
    try:
        # Skip if already has embedding
        if paper_data.get('embedding'):
            return paper_data
        
        text = create_text_for_paper(paper_data)
        if not text or not text.strip():
            return paper_data
        
        embedding_service = get_embedding_service()
        embedding = embedding_service.embed_text(text)
        
        # Store as Vector type for Firestore vector search
        from google.cloud.firestore_v1.vector import Vector
        paper_data['embedding'] = Vector(embedding)
        paper_data['embedding_model'] = 'text-embedding-004'
        paper_data['embedding_updated'] = datetime.utcnow().isoformat()
        
        return paper_data
        
    except Exception as e:
        structured_logger.warning(
            f"Failed to generate embedding for paper (non-blocking)",
            error=str(e)
        )
        return paper_data  # Return original data if embedding fails


def add_embedding_to_podcast_data(podcast_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Add embedding to podcast data dictionary (for batch operations).
    
    This generates the embedding but doesn't store it - caller must store the data.
    """
    try:
        # Skip if already has embedding
        if podcast_data.get('embedding'):
            return podcast_data
        
        text = create_text_for_podcast(podcast_data)
        if not text or not text.strip():
            return podcast_data
        
        embedding_service = get_embedding_service()
        embedding = embedding_service.embed_text(text)
        
        # Store as Vector type for Firestore vector search
        from google.cloud.firestore_v1.vector import Vector
        podcast_data['embedding'] = Vector(embedding)
        podcast_data['embedding_model'] = 'text-embedding-004'
        podcast_data['embedding_updated'] = datetime.utcnow().isoformat()
        
        return podcast_data
        
    except Exception as e:
        structured_logger.warning(
            f"Failed to generate embedding for podcast (non-blocking)",
            error=str(e)
        )
        return podcast_data  # Return original data if embedding fails


