"""
Google Cloud Storage client utilities for MCP server

Provides functions for accessing GLMP process files stored in GCS.
"""

from google.cloud import storage
from typing import List, Dict, Any, Optional
import json
import logging

logger = logging.getLogger(__name__)

# Global GCS client (initialized on first use)
_storage_client: Optional[storage.Client] = None


def get_storage_client() -> storage.Client:
    """Get or create GCS client singleton."""
    global _storage_client
    if _storage_client is None:
        _storage_client = storage.Client()
    return _storage_client


def list_glmp_files(bucket_name: str, prefix: str = "glmp-v2/") -> List[str]:
    """
    List all GLMP JSON files in GCS bucket.
    
    Args:
        bucket_name: GCS bucket name
        prefix: Path prefix (default: "glmp-v2/")
        
    Returns:
        List of blob names (file paths)
    """
    try:
        client = get_storage_client()
        bucket = client.bucket(bucket_name)
        blobs = bucket.list_blobs(prefix=prefix)
        
        file_names = []
        for blob in blobs:
            if blob.name.endswith('.json'):
                file_names.append(blob.name)
        
        return sorted(file_names)
        
    except Exception as e:
        logger.error(f"Error listing GLMP files: {e}", exc_info=True)
        raise


def get_glmp_file(bucket_name: str, blob_name: str) -> Optional[Dict[str, Any]]:
    """
    Get and parse a GLMP JSON file from GCS.
    
    Args:
        bucket_name: GCS bucket name
        blob_name: Blob name (file path)
        
    Returns:
        Parsed JSON as dictionary, or None if not found
    """
    try:
        client = get_storage_client()
        bucket = client.bucket(bucket_name)
        blob = bucket.blob(blob_name)
        
        if not blob.exists():
            return None
        
        content = blob.download_as_text()
        return json.loads(content)
        
    except Exception as e:
        logger.error(f"Error getting GLMP file {blob_name}: {e}", exc_info=True)
        return None


def search_glmp_files(
    bucket_name: str,
    prefix: str = "glmp-v2/",
    search_term: Optional[str] = None,
    category: Optional[str] = None
) -> List[Dict[str, Any]]:
    """
    Search GLMP files by name, category, or content.
    
    Args:
        bucket_name: GCS bucket name
        prefix: Path prefix
        search_term: Search term to match in process name or description
        category: Filter by category
        
    Returns:
        List of process dictionaries
    """
    try:
        file_names = list_glmp_files(bucket_name, prefix)
        results = []
        
        for file_name in file_names:
            process = get_glmp_file(bucket_name, file_name)
            if not process:
                continue
            
            # Filter by category
            if category:
                process_category = process.get("category", "").lower()
                if category.lower() not in process_category:
                    continue
            
            # Filter by search term
            if search_term:
                search_lower = search_term.lower()
                name = process.get("title", "").lower()
                description = process.get("description", "").lower() if process.get("description") else ""
                
                if search_lower not in name and search_lower not in description:
                    continue
            
            results.append(process)
        
        return results
        
    except Exception as e:
        logger.error(f"Error searching GLMP files: {e}", exc_info=True)
        return []



