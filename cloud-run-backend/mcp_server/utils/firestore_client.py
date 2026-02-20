"""
Firestore client utilities for MCP server

Provides reusable functions for querying Firestore collections.
"""

from google.cloud import firestore
from typing import List, Dict, Any, Optional
import logging

logger = logging.getLogger(__name__)

# Global Firestore client (initialized on first use)
_db_client: Optional[firestore.Client] = None


def get_firestore_client() -> firestore.Client:
    """Get or create Firestore client singleton."""
    global _db_client
    if _db_client is None:
        from mcp_server.config import FIRESTORE_DATABASE, GCP_PROJECT_ID
        # Be explicit about project + database to avoid accidentally connecting to "(default)"
        # when the app is using a named Firestore database.
        _db_client = firestore.Client(project=GCP_PROJECT_ID, database=FIRESTORE_DATABASE)
    return _db_client


def query_collection(
    collection_name: str,
    filters: Optional[List[tuple]] = None,
    order_by: Optional[str] = None,
    limit: Optional[int] = None
) -> List[Dict[str, Any]]:
    """
    Query a Firestore collection with optional filters and ordering.
    
    Args:
        collection_name: Name of the Firestore collection
        filters: List of (field, operator, value) tuples for filtering
        order_by: Field name to order by
        limit: Maximum number of documents to return
        
    Returns:
        List of document dictionaries
    """
    try:
        db = get_firestore_client()
        collection_ref = db.collection(collection_name)
        
        # Apply filters
        query = collection_ref
        if filters:
            for field, operator, value in filters:
                query = query.where(field, operator, value)
        
        # Apply ordering
        if order_by:
            query = query.order_by(order_by)
        
        # Apply limit
        if limit:
            query = query.limit(limit)
        
        # Execute query
        docs = query.stream()
        
        # Convert to dictionaries
        results = []
        for doc in docs:
            doc_dict = doc.to_dict()
            doc_dict["id"] = doc.id
            results.append(doc_dict)
        
        return results
        
    except Exception as e:
        logger.error(f"Error querying collection {collection_name}: {e}")
        raise


def get_document(collection_name: str, document_id: str) -> Optional[Dict[str, Any]]:
    """
    Get a single document from Firestore.
    
    Args:
        collection_name: Name of the Firestore collection
        document_id: Document ID
        
    Returns:
        Document dictionary or None if not found
    """
    try:
        db = get_firestore_client()
        doc_ref = db.collection(collection_name).document(document_id)
        doc = doc_ref.get()
        
        if doc.exists:
            doc_dict = doc.to_dict()
            doc_dict["id"] = doc.id
            return doc_dict
        return None
        
    except Exception as e:
        logger.error(f"Error getting document {document_id} from {collection_name}: {e}")
        raise



