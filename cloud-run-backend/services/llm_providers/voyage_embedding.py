"""
Voyage AI Embedding Service (Anthropic)

Provides embeddings using Voyage AI models (used by Anthropic/Claude).
Cost: ~$0.10 per 1M tokens (33% cheaper than Vertex AI)
Dimension: 1024
"""

import logging
import os
from typing import List

try:
    import voyageai
    VOYAGE_AVAILABLE = True
except ImportError:
    voyageai = None
    VOYAGE_AVAILABLE = False

from services.llm_providers.base import BaseEmbeddingService
from utils.logging import structured_logger

logger = logging.getLogger(__name__)


class VoyageEmbeddingService(BaseEmbeddingService):
    """Embedding service using Voyage AI (Anthropic)."""
    
    def __init__(self, model: str = "voyage-3.5"):
        """
        Initialize Voyage embedding service.
        
        Args:
            model: Model name (voyage-3.5 recommended)
        """
        if not VOYAGE_AVAILABLE:
            raise ImportError(
                "Voyage AI dependencies not available. "
                "Install voyageai package: pip install voyageai"
            )
        
        # Try to get API key from environment or Secret Manager
        from services.llm_providers.secret_manager_helpers import get_voyage_api_key
        api_key = get_voyage_api_key()
        if not api_key:
            raise ValueError(
                "VOYAGE_API_KEY or ANTHROPIC_API_KEY not found in environment or Secret Manager. "
                "Please set VOYAGE_API_KEY/ANTHROPIC_API_KEY environment variable or add 'voyage-api-key'/'anthropic-api-key' to Secret Manager. "
                "Get your API key from https://www.voyageai.com/ or https://console.anthropic.com/"
            )
        
        try:
            self._client = voyageai.Client(api_key=api_key)
            self._model = model
            self._dimension = 1024  # voyage-3.5 produces 1024-dimensional vectors
            
            structured_logger.info(
                "Voyage embedding service initialized",
                model=model,
                dimension=self._dimension
            )
        except Exception as e:
            structured_logger.error(
                "Failed to initialize Voyage embedding service",
                error=str(e),
                model=model
            )
            raise
    
    @property
    def model_name(self) -> str:
        return self._model
    
    @property
    def dimension(self) -> int:
        return self._dimension
    
    @property
    def provider(self) -> str:
        return "voyage"
    
    def embed_text(self, text: str) -> List[float]:
        """Generate embedding for a single text."""
        if not text or not text.strip():
            raise ValueError("Text cannot be empty")
        
        try:
            result = self._client.embed([text], model=self._model)
            
            if not result.embeddings or len(result.embeddings) == 0:
                raise ValueError("No embedding returned from Voyage")
            
            return result.embeddings[0]
            
        except Exception as e:
            structured_logger.error(
                "Failed to generate Voyage embedding",
                error=str(e),
                text_length=len(text) if text else 0
            )
            raise
    
    def embed_batch(
        self,
        texts: List[str],
        batch_size: int = 100
    ) -> List[List[float]]:
        """Generate embeddings for a batch of texts."""
        if not texts:
            return []
        
        all_embeddings = []
        
        try:
            # Process in batches
            for i in range(0, len(texts), batch_size):
                batch = texts[i:i + batch_size]
                
                # Filter out empty texts
                valid_texts = [t for t in batch if t and t.strip()]
                if not valid_texts:
                    # Add None placeholders for empty texts
                    all_embeddings.extend([None] * len(batch))
                    continue
                
                # Generate embeddings for batch
                result = self._client.embed(valid_texts, model=self._model)
                
                # Map embeddings back to original positions
                embedding_dict = {
                    text: emb
                    for text, emb in zip(valid_texts, result.embeddings)
                }
                batch_embeddings = []
                for text in batch:
                    if text and text.strip():
                        batch_embeddings.append(embedding_dict[text])
                    else:
                        batch_embeddings.append(None)
                
                all_embeddings.extend(batch_embeddings)
                
                structured_logger.debug(
                    f"Processed Voyage embedding batch {i // batch_size + 1}/{(len(texts) + batch_size - 1) // batch_size}",
                    batch_size=len(batch),
                    total_processed=i + len(batch)
                )
            
            return all_embeddings
            
        except Exception as e:
            structured_logger.error(
                "Failed to generate Voyage batch embeddings",
                error=str(e),
                batch_count=len(texts),
                batch_size=batch_size
            )
            raise
