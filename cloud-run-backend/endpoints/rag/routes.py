"""
RAG (Retrieval-Augmented Generation) API Endpoints

Provides question-answering capabilities using RAG.

Copyright (c) 2025 Gary Welz / CopernicusAI
Licensed under MIT License
"""

from fastapi import APIRouter, HTTPException, Query
from typing import Optional, List, Literal
from utils.logging import structured_logger

from services.rag_service import get_rag_service

router = APIRouter(prefix="/api/rag", tags=["rag"])


@router.get("/answer")
async def answer_question(
    question: str = Query(..., description="Question to answer"),
    max_context_items: int = Query(5, ge=1, le=20, description="Maximum context items to retrieve"),
    content_types: Optional[str] = Query(None, description="Comma-separated content types: papers,podcasts,glmp"),
    mode: Literal["general", "paper_explanation", "concept_explanation"] = Query(
        "general",
        description="RAG mode: general question, paper_explanation, or concept_explanation"
    ),
    focus_id: Optional[str] = Query(
        None,
        description="Optional focus identifier (e.g., paper_id or concept name/id) for explanation modes"
    ),
):
    """
    Answer a question using RAG (Retrieval-Augmented Generation).
    
    Uses vector search to retrieve relevant content, then generates an answer
    using an LLM with the retrieved content as context.
    """
    try:
        rag_service = get_rag_service()
        
        # Parse content types if provided
        content_types_list = None
        if content_types:
            content_types_list = [ct.strip() for ct in content_types.split(',')]
        
        # Generate answer with optional mode and focus
        result = await rag_service.answer_question(
            question=question,
            max_context_items=max_context_items,
            content_types=content_types_list,
            include_sources=True,
            mode=mode,
            focus_id=focus_id,
        )
        
        # Format response for frontend
        if result.get('error'):
            raise HTTPException(status_code=500, detail=result['error'])
        
        # Convert citations to frontend format
        citations = []
        if result.get('citations'):
            for i, citation in enumerate(result['citations'], 1):
                citations.append({
                    'number': i,
                    'type': citation.get('type', 'unknown'),
                    'title': citation.get('title', citation.get('source', 'Unknown')),
                    'similarity_score': citation.get('similarity_score', citation.get('similarity', citation.get('score')))
                })
        
        return {
            'question': question,
            'answer': result.get('answer', ''),
            'citations': citations,
            'sources': result.get('sources', []),
            'metadata': {
                'context_items_used': result.get('metadata', {}).get('context_items_used', len(result.get('sources', []))),
                'model': result.get('metadata', {}).get('model', 'N/A'),
                'retrieval_method': result.get('metadata', {}).get('retrieval_method'),
                'generated_at': result.get('metadata', {}).get('generated_at')
            }
        }
    
    except HTTPException:
        raise
    except Exception as e:
        structured_logger.error(f"RAG error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to generate answer: {str(e)}")

