"""
Vector Search API Endpoints

Provides semantic search capabilities using vector embeddings.

Copyright (c) 2025 Gary Welz / CopernicusAI
Licensed under MIT License
"""

from fastapi import APIRouter, HTTPException, Query
from typing import Optional, List
import json
from utils.logging import structured_logger

from mcp_server.tools.vector_search import search_semantic

router = APIRouter(prefix="/api/vector-search", tags=["vector-search"])


@router.get("/semantic")
async def semantic_search(
    query: str = Query(..., description="Search query"),
    content_types: Optional[str] = Query(
        None,
        description="Comma-separated: papers,podcasts,glmp,math,chemistry,physics,computer_science,biology",
    ),
    limit: int = Query(20, ge=1, le=100, description="Maximum results per content type"),
    distance_threshold: float = Query(0.7, ge=0.0, le=1.0, description="Similarity threshold (lower = more similar)")
):
    """
    Semantic search across all content types using vector embeddings.
    
    Uses vector similarity to find content that is semantically similar
    to the query, even if it doesn't contain exact keywords.
    """
    try:
        # Parse content types if provided
        content_types_list = None
        if content_types:
            content_types_list = [ct.strip() for ct in content_types.split(',')]
        
        # Call the MCP tool function
        result_json = await search_semantic(
            query=query,
            content_types=content_types_list,
            limit=limit,
            distance_threshold=distance_threshold
        )
        
        # Parse the JSON result
        result = json.loads(result_json)
        
        # Return in format expected by frontend
        return {
            'query': query,
            'papers': result.get('papers', []),
            'podcasts': result.get('podcasts', []),
            'glmp_processes': result.get('glmp_processes', []),
            'math_processes': result.get('math_processes', []),
            'chemistry_processes': result.get('chemistry_processes', []),
            'physics_processes': result.get('physics_processes', []),
            'computer_science_processes': result.get('computer_science_processes', []),
            'biology_processes': result.get('biology_processes', []),
            'content_types_searched': result.get('content_types_searched', []),
            'search_method': result.get('search_method', 'vector_semantic')
        }
    
    except Exception as e:
        structured_logger.error(f"Vector search error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to perform semantic search: {str(e)}")

