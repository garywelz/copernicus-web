"""
Embedding Service Factory

Automatically selects the best available embedding provider based on:
1. EMBEDDING_PROVIDER environment variable (if set)
2. API key availability (prioritizes OpenAI > Voyage > Vertex AI)
"""

import os
import logging
from typing import Optional

from utils.logging import structured_logger

logger = logging.getLogger(__name__)


def get_embedding_service():
    """
    Get embedding service instance, automatically selecting the best available provider.
    
    Priority order:
    1. OpenAI (if OPENAI_API_KEY is set) - cheapest
    2. Voyage (if VOYAGE_API_KEY or ANTHROPIC_API_KEY is set) - good balance
    3. Vertex AI (if available and not disabled) - fallback
    
    Returns:
        BaseEmbeddingService instance
    
    Raises:
        RuntimeError: If no provider is available
    """
    # Check for explicit provider selection
    provider = os.getenv("EMBEDDING_PROVIDER", "").strip().lower()
    
    # Try OpenAI first (cheapest)
    if provider in ("", "openai", "auto"):
        # Check environment or Secret Manager
        from services.llm_providers.secret_manager_helpers import get_openai_api_key
        if get_openai_api_key():
            try:
                from services.llm_providers.openai_embedding import OpenAIEmbeddingService
                service = OpenAIEmbeddingService()
                structured_logger.info("Using OpenAI embedding service")
                return service
            except Exception as e:
                logger.warning(f"Failed to initialize OpenAI embeddings: {e}")
    
    # Try Voyage/Anthropic second (good balance)
    if provider in ("", "voyage", "anthropic", "auto"):
        # Check environment or Secret Manager
        from services.llm_providers.secret_manager_helpers import get_voyage_api_key
        if get_voyage_api_key():
            try:
                from services.llm_providers.voyage_embedding import VoyageEmbeddingService
                service = VoyageEmbeddingService()
                structured_logger.info("Using Voyage embedding service")
                return service
            except Exception as e:
                logger.warning(f"Failed to initialize Voyage embeddings: {e}")
    
    # Fallback to Vertex AI (if not disabled)
    if provider in ("", "vertex_ai", "vertex", "auto"):
        # Check both DISABLE_VERTEX_AI and COPERNICUS_DISABLE_VERTEX_AI flags
        vertex_disabled = (
            os.getenv("DISABLE_VERTEX_AI", "").strip().lower() in {"1", "true", "yes", "y", "on"} or
            os.getenv("COPERNICUS_DISABLE_VERTEX_AI", "").strip().lower() in {"1", "true", "yes", "y", "on"}
        )
        if vertex_disabled:
            logger.debug("Vertex AI embeddings are disabled, skipping fallback")
        else:
            try:
                # Import the existing Vertex AI embedding service
                # Note: EmbeddingService.__init__() will also check if Vertex AI is disabled
                from services.embedding_service import EmbeddingService
                service = EmbeddingService()
                structured_logger.info("Using Vertex AI embedding service (fallback)")
                return service
            except RuntimeError as e:
                # If Vertex AI is disabled, EmbeddingService will raise RuntimeError
                if "disabled" in str(e).lower():
                    logger.debug(f"Vertex AI embeddings are disabled: {e}")
                else:
                    logger.warning(f"Failed to initialize Vertex AI embeddings: {e}")
            except Exception as e:
                logger.warning(f"Failed to initialize Vertex AI embeddings: {e}")
    
    # No provider available
    raise RuntimeError(
        "No embedding service available. Please set one of:\n"
        "- OPENAI_API_KEY (recommended - cheapest)\n"
        "- VOYAGE_API_KEY or ANTHROPIC_API_KEY\n"
        "- Or enable Vertex AI (not recommended due to cost)"
    )
