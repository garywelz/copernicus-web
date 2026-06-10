"""
RAG Service Factory

Automatically selects the best available RAG provider based on:
1. RAG_PROVIDER environment variable (if set)
2. API key availability (prioritizes OpenAI > Claude > Vertex AI)
"""

import os
import logging

from utils.logging import structured_logger

logger = logging.getLogger(__name__)


def get_rag_service():
    """
    Get RAG service instance, automatically selecting the best available provider.
    
    Priority order:
    1. OpenAI (if OPENAI_API_KEY is set) - matches embedding provider
    2. Anthropic Claude (if ANTHROPIC_API_KEY is set) - alternative
    3. Vertex AI (if available and not disabled) - fallback
    
    Returns:
        BaseRAGService instance
    
    Raises:
        RuntimeError: If no provider is available
    """
    # Check for explicit provider selection
    provider = os.getenv("RAG_PROVIDER", "").strip().lower()
    
    # Try OpenAI first (same provider as embeddings)
    if provider in ("", "openai", "auto"):
        from services.llm_providers.secret_manager_helpers import get_openai_api_key
        if get_openai_api_key():
            try:
                from services.llm_providers.openai_rag import OpenAIRAGService
                service = OpenAIRAGService()
                structured_logger.info("Using OpenAI RAG service")
                return service
            except Exception as e:
                logger.warning(f"Failed to initialize OpenAI RAG: {e}")

    # Try Anthropic Claude second
    if provider in ("", "anthropic", "claude", "auto"):
        from services.llm_providers.secret_manager_helpers import get_anthropic_api_key
        if get_anthropic_api_key():
            try:
                from services.llm_providers.claude_rag import ClaudeRAGService
                service = ClaudeRAGService()
                structured_logger.info("Using Claude RAG service")
                return service
            except Exception as e:
                logger.warning(f"Failed to initialize Claude RAG: {e}")
    
    # Fallback to Vertex AI (if not disabled)
    if provider in ("", "vertex_ai", "vertex", "auto"):
        vertex_disabled = os.getenv("DISABLE_VERTEX_AI", "").strip().lower() in {"1", "true", "yes", "y", "on"}
        if not vertex_disabled:
            try:
                # Import the existing Vertex AI RAG service
                from services.rag_service import RAGService
                service = RAGService()
                structured_logger.info("Using Vertex AI RAG service (fallback)")
                return service
            except Exception as e:
                logger.warning(f"Failed to initialize Vertex AI RAG: {e}")
    
    # No provider available
    raise RuntimeError(
        "No RAG service available. Please set one of:\n"
        "- ANTHROPIC_API_KEY (recommended - good quality/cost)\n"
        "- OPENAI_API_KEY (cheaper option)\n"
        "- Or enable Vertex AI (not recommended due to cost)"
    )
