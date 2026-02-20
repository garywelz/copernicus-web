"""
MCP Tools for GLMP (Genome Logic Modeling Project)

Provides tools for querying biological process diagrams stored in Google Cloud Storage.
"""

import logging
from typing import Any, Dict, List, Optional
import json

from mcp_server.utils.gcs_client import (
    list_glmp_files,
    get_glmp_file,
    search_glmp_files
)
from mcp_server.config import (
    GCS_BUCKET_NAME,
    GLMP_BUCKET_PATH,
    DEFAULT_QUERY_LIMIT,
    MAX_QUERY_LIMIT
)

logger = logging.getLogger(__name__)


async def list_glmp_processes(
    category: Optional[str] = None,
    limit: int = DEFAULT_QUERY_LIMIT
) -> str:
    """
    List GLMP biological processes, optionally filtered by category.
    
    Args:
        category: Filter by category (e.g., "Central Dogma", "Metabolism", "Signaling")
        limit: Maximum number of results (default: 10, max: 100)
        
    Returns:
        JSON string with list of processes
    """
    try:
        # Validate limit
        limit = min(max(1, limit), MAX_QUERY_LIMIT)
        
        # Search for processes
        prefix = GLMP_BUCKET_PATH if GLMP_BUCKET_PATH.endswith("/") else GLMP_BUCKET_PATH + "/"
        processes = search_glmp_files(
            bucket_name=GCS_BUCKET_NAME,
            prefix=prefix,
            category=category
        )
        
        # Format results
        results = []
        for process in processes[:limit]:
            results.append({
                "id": process.get("id"),
                "title": process.get("title", "Untitled"),
                "description": process.get("description"),
                "category": process.get("category"),
                "version": process.get("version"),
                "source": process.get("source"),
                "has_mermaid": "mermaid" in process,
                "entity_count": len(process.get("entities", [])) if process.get("entities") else 0
            })
        
        return json.dumps({
            "processes": results,
            "count": len(results),
            "category": category
        }, indent=2)
        
    except Exception as e:
        logger.error(f"Error listing GLMP processes: {e}", exc_info=True)
        return json.dumps({
            "error": f"Failed to list processes: {str(e)}",
            "processes": [],
            "count": 0
        })


async def get_glmp_process(
    process_id: Optional[str] = None,
    process_name: Optional[str] = None
) -> str:
    """
    Get full GLMP process details including Mermaid diagram.
    
    Args:
        process_id: Process ID
        process_name: Process name (searches for matching title)
        
    Returns:
        JSON string with full process data including Mermaid code
    """
    try:
        if not process_id and not process_name:
            return json.dumps({
                "error": "Either process_id or process_name must be provided",
                "process": None
            })
        
        # List all files to search
        prefix = GLMP_BUCKET_PATH if GLMP_BUCKET_PATH.endswith("/") else GLMP_BUCKET_PATH + "/"
        file_names = list_glmp_files(GCS_BUCKET_NAME, prefix)
        
        # Try to find by ID first
        if process_id:
            for file_name in file_names:
                process = get_glmp_file(GCS_BUCKET_NAME, file_name)
                if process and process.get("id") == process_id:
                    return json.dumps({"process": process}, indent=2)
        
        # Try to find by name
        if process_name:
            name_lower = process_name.lower()
            for file_name in file_names:
                process = get_glmp_file(GCS_BUCKET_NAME, file_name)
                if process:
                    title = process.get("title", "").lower()
                    if name_lower in title or title in name_lower:
                        return json.dumps({"process": process}, indent=2)
        
        return json.dumps({
            "error": "Process not found",
            "process": None,
            "process_id": process_id,
            "process_name": process_name
        })
        
    except Exception as e:
        logger.error(f"Error getting GLMP process: {e}", exc_info=True)
        return json.dumps({
            "error": f"Failed to get process: {str(e)}",
            "process": None
        })


async def search_glmp_by_entity(
    entity: str,
    limit: int = DEFAULT_QUERY_LIMIT
) -> str:
    """
    Search for GLMP processes that involve a specific entity (gene, protein, molecule).
    
    Args:
        entity: Entity name (e.g., "p53", "ATP", "RNA polymerase")
        limit: Maximum number of results (default: 10, max: 100)
        
    Returns:
        JSON string with list of matching processes
    """
    try:
        # Validate limit
        limit = min(max(1, limit), MAX_QUERY_LIMIT)
        
        # Get all processes
        prefix = GLMP_BUCKET_PATH if GLMP_BUCKET_PATH.endswith("/") else GLMP_BUCKET_PATH + "/"
        file_names = list_glmp_files(GCS_BUCKET_NAME, prefix)
        entity_lower = entity.lower()
        matching_processes = []
        
        for file_name in file_names:
            process = get_glmp_file(GCS_BUCKET_NAME, file_name)
            if not process:
                continue
            
            # Search in entities list
            entities = process.get("entities", [])
            if isinstance(entities, list):
                for e in entities:
                    if isinstance(e, str) and entity_lower in e.lower():
                        matching_processes.append({
                            "id": process.get("id"),
                            "title": process.get("title"),
                            "category": process.get("category"),
                            "description": process.get("description"),
                            "matching_entity": e
                        })
                        break
            
            if len(matching_processes) >= limit:
                break
        
        return json.dumps({
            "entity": entity,
            "processes": matching_processes,
            "count": len(matching_processes)
        }, indent=2)
        
    except Exception as e:
        logger.error(f"Error searching GLMP by entity: {e}", exc_info=True)
        return json.dumps({
            "error": f"Failed to search by entity: {str(e)}",
            "processes": [],
            "count": 0
        })


async def get_glmp_categories() -> str:
    """
    Get list of all GLMP categories with process counts.
    
    Counts by unique process IDs to avoid double-counting duplicate files.
    
    Returns:
        JSON string with categories and counts
    """
    try:
        # Get all processes
        prefix = GLMP_BUCKET_PATH if GLMP_BUCKET_PATH.endswith("/") else GLMP_BUCKET_PATH + "/"
        file_names = list_glmp_files(GCS_BUCKET_NAME, prefix)
        
        # Track unique process IDs per category to avoid double-counting
        category_process_ids: Dict[str, set] = {}
        all_process_ids = set()
        
        for file_name in file_names:
            process = get_glmp_file(GCS_BUCKET_NAME, file_name)
            if not process:
                continue
            
            process_id = process.get("id")
            if not process_id:
                # Skip processes without IDs
                continue
            
            # Skip if we've already counted this process ID
            if process_id in all_process_ids:
                continue
            
            all_process_ids.add(process_id)
            category = process.get("category", "Uncategorized")
            
            if category not in category_process_ids:
                category_process_ids[category] = set()
            category_process_ids[category].add(process_id)
        
        # Convert to counts
        categories = [
            {"category": cat, "count": len(process_ids)}
            for cat, process_ids in sorted(category_process_ids.items())
        ]
        
        return json.dumps({
            "categories": categories,
            "total_processes": len(all_process_ids),
            "total_categories": len(categories)
        }, indent=2)
        
    except Exception as e:
        logger.error(f"Error getting GLMP categories: {e}", exc_info=True)
        return json.dumps({
            "error": f"Failed to get categories: {str(e)}",
            "categories": [],
            "total_processes": 0,
            "total_categories": 0
        })

