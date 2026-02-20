"""
OpenAI Embedding Service

Provides embeddings using OpenAI's text-embedding-3-small model.
Cost: $0.02 per 1M tokens (87% cheaper than Vertex AI)
Dimension: 1536
"""

import logging
import os
from typing import List

try:
    from openai import OpenAI
    OPENAI_AVAILABLE = True
except ImportError:
    OpenAI = None
    OPENAI_AVAILABLE = False

from services.llm_providers.base import BaseEmbeddingService
from utils.logging import structured_logger

logger = logging.getLogger(__name__)


class OpenAIEmbeddingService(BaseEmbeddingService):
    """Embedding service using OpenAI."""
    
    def __init__(self, model: str = "text-embedding-3-small"):
        """
        Initialize OpenAI embedding service.
        
        Args:
            model: Model name (text-embedding-3-small or text-embedding-3-large)
        """
        if not OPENAI_AVAILABLE:
            raise ImportError(
                "OpenAI dependencies not available. "
                "Install openai package: pip install openai"
            )
        
        # Try to get API key from environment or Secret Manager
        from services.llm_providers.secret_manager_helpers import get_openai_api_key
        api_key = get_openai_api_key()
        if not api_key:
            raise ValueError(
                "OPENAI_API_KEY not found in environment or Secret Manager. "
                "Please set OPENAI_API_KEY environment variable or add 'openai-api-key' to Secret Manager. "
                "Get your API key from https://platform.openai.com/api-keys"
            )
        
        try:
            self._client = OpenAI(api_key=api_key)
            self._model = model
            self._dimension = 1536 if "small" in model else 3072  # text-embedding-3-small = 1536, large = 3072
            
            structured_logger.info(
                "OpenAI embedding service initialized",
                model=model,
                dimension=self._dimension
            )
        except Exception as e:
            structured_logger.error(
                "Failed to initialize OpenAI embedding service",
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
        return "openai"
    
    def embed_text(self, text: str) -> List[float]:
        """Generate embedding for a single text."""
        if not text or not text.strip():
            raise ValueError("Text cannot be empty")
        
        try:
            response = self._client.embeddings.create(
                model=self._model,
                input=text
            )
            
            if not response.data or len(response.data) == 0:
                raise ValueError("No embedding returned from OpenAI")
            
            return response.data[0].embedding
            
        except Exception as e:
            structured_logger.error(
                "Failed to generate OpenAI embedding",
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
            # OpenAI supports batch requests (up to 2048 inputs per request)
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
                response = self._client.embeddings.create(
                    model=self._model,
                    input=valid_texts
                )
                
                # Map embeddings back to original positions
                embedding_dict = {
                    text: item.embedding
                    for text, item in zip(valid_texts, response.data)
                }
                batch_embeddings = []
                for text in batch:
                    if text and text.strip():
                        batch_embeddings.append(embedding_dict[text])
                    else:
                        batch_embeddings.append(None)
                
                all_embeddings.extend(batch_embeddings)
                
                structured_logger.debug(
                    f"Processed OpenAI embedding batch {i // batch_size + 1}/{(len(texts) + batch_size - 1) // batch_size}",
                    batch_size=len(batch),
                    total_processed=i + len(batch)
                )
            
            return all_embeddings
            
        except Exception as e:
            structured_logger.error(
                "Failed to generate OpenAI batch embeddings",
                error=str(e),
                batch_count=len(texts),
                batch_size=batch_size
            )
            raise
