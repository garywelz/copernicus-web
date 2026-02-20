"""
MCP Tools for RAG (Retrieval-Augmented Generation)

Provides question-answering capabilities using RAG, combining vector search
with LLM generation to provide grounded answers from the knowledge base.
"""

import logging
from typing import Any, Dict, List, Optional
import json

from services.rag_service import get_rag_service
from mcp_server.config import DEFAULT_QUERY_LIMIT, MAX_QUERY_LIMIT

logger = logging.getLogger(__name__)


async def answer_with_rag(
    question: str,
    max_context_items: int = 5,
    content_types: Optional[List[str]] = None,
    include_sources: bool = True,
    mode: str = "general",
    focus_id: Optional[str] = None,
) -> str:
    """
    Answer a question using RAG (Retrieval-Augmented Generation).
    
    Uses vector search to retrieve relevant content from the knowledge base,
    then generates an answer using an LLM with the retrieved content as context.
    Answers are grounded in actual sources with citations.
    
    Args:
        question: Natural language question to answer
        max_context_items: Maximum number of retrieved items to use as context (default: 5, max: 10)
        content_types: Types of content to search (default: all)
                      Options: ["papers", "podcasts", "glmp"]
        include_sources: Whether to include source citations in response (default: True)
    
    Returns:
        JSON string with answer, citations, sources, and metadata
    """
    try:
        # Validate max_context_items
        max_context_items = min(max(1, max_context_items), 10)
        
        # Get RAG service
        rag_service = get_rag_service()
        
        # Generate answer
        result = await rag_service.answer_question(
            question=question,
            max_context_items=max_context_items,
            content_types=content_types,
            include_sources=include_sources,
            mode=mode,
            focus_id=focus_id,
        )
        
        return json.dumps(result, indent=2)
        
    except Exception as e:
        logger.error(f"Error in RAG answer generation: {e}", exc_info=True)
        return json.dumps({
            "error": f"Failed to generate answer: {str(e)}",
            "question": question,
            "answer": None,
            "citations": [],
            "sources": []
        })


async def explain_concept(
    concept: str,
    depth: str = "intermediate",
    content_types: Optional[List[str]] = None
) -> str:
    """
    Explain a scientific concept using RAG.
    
    Provides a comprehensive explanation of a concept by retrieving relevant
    information from papers, podcasts, and processes, then synthesizing an explanation.
    
    Args:
        concept: Concept to explain (e.g., "ATP synthesis", "DNA replication")
        depth: Explanation depth - "basic", "intermediate", or "advanced" (default: "intermediate")
        content_types: Types of content to search (default: all)
    
    Returns:
        JSON string with explanation, citations, and sources
    """
    try:
        # Format question based on depth
        depth_prompts = {
            "basic": "Explain {concept} in simple terms suitable for beginners.",
            "intermediate": "Explain {concept} in detail, suitable for someone with intermediate knowledge.",
            "advanced": "Provide a comprehensive, technical explanation of {concept} for experts."
        }
        
        question = depth_prompts.get(depth, depth_prompts["intermediate"]).format(concept=concept)
        
        # Use RAG to answer
        rag_service = get_rag_service()
        result = await rag_service.answer_question(
            question=question,
            max_context_items=7,  # More context for explanations
            content_types=content_types,
            include_sources=True
        )
        
        # Add concept and depth to metadata
        result["metadata"]["concept"] = concept
        result["metadata"]["depth"] = depth
        
        return json.dumps(result, indent=2)
        
    except Exception as e:
        logger.error(f"Error explaining concept: {e}", exc_info=True)
        return json.dumps({
            "error": f"Failed to explain concept: {str(e)}",
            "concept": concept,
            "explanation": None,
            "citations": []
        })


async def compare_concepts(
    concept1: str,
    concept2: str,
    content_types: Optional[List[str]] = None
) -> str:
    """
    Compare two scientific concepts using RAG.
    
    Retrieves information about both concepts and generates a comparison
    highlighting similarities, differences, and relationships.
    
    Args:
        concept1: First concept to compare
        concept2: Second concept to compare
        content_types: Types of content to search (default: all)
    
    Returns:
        JSON string with comparison, citations, and sources
    """
    try:
        question = f"Compare and contrast {concept1} and {concept2}. Highlight their similarities, differences, and any relationships between them."
        
        # Use RAG to answer
        rag_service = get_rag_service()
        result = await rag_service.answer_question(
            question=question,
            max_context_items=8,  # More context for comparisons
            content_types=content_types,
            include_sources=True
        )
        
        # Add concepts to metadata
        result["metadata"]["concept1"] = concept1
        result["metadata"]["concept2"] = concept2
        result["metadata"]["task"] = "comparison"
        
        return json.dumps(result, indent=2)
        
    except Exception as e:
        logger.error(f"Error comparing concepts: {e}", exc_info=True)
        return json.dumps({
            "error": f"Failed to compare concepts: {str(e)}",
            "concept1": concept1,
            "concept2": concept2,
            "comparison": None,
            "citations": []
        })


