"""
Embedding Service for Vector Search

Generates text embeddings using Vertex AI for semantic search capabilities.
Integrates with existing Vertex AI infrastructure.
"""

import logging
from typing import List, Optional
import os

# Vertex AI imports
try:
    from google.cloud import aiplatform
    from vertexai.preview.language_models import TextEmbeddingModel
    VERTEX_AI_AVAILABLE = True
except ImportError:
    TextEmbeddingModel = None
    aiplatform = None
    VERTEX_AI_AVAILABLE = False

from utils.logging import structured_logger

logger = logging.getLogger(__name__)

# Hard-disable Vertex AI calls (useful when billing is a concern)
def _env_flag(name: str, default: str = "0") -> bool:
    return (os.getenv(name, default) or "").strip().lower() in {"1", "true", "yes", "y", "on"}

VERTEX_AI_DISABLED = _env_flag("DISABLE_VERTEX_AI") or _env_flag("COPERNICUS_DISABLE_VERTEX_AI")

# Configuration
GCP_PROJECT_ID = os.getenv("GCP_PROJECT_ID", "regal-scholar-453620-r7")
GCP_REGION = os.getenv("GCP_REGION", "us-central1")
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "text-embedding-004")
EMBEDDING_DIMENSION = 768  # text-embedding-004 produces 768-dimensional vectors


class EmbeddingService:
    """
    Service for generating text embeddings using Vertex AI.
    
    Uses Vertex AI's text-embedding-004 model to generate 768-dimensional
    vector embeddings for semantic search.
    """
    
    def __init__(self):
        """Initialize the embedding service with Vertex AI."""
        if VERTEX_AI_DISABLED:
            raise RuntimeError("Vertex AI embeddings are disabled via environment flag")
        if not VERTEX_AI_AVAILABLE:
            raise ImportError(
                "Vertex AI dependencies not available. "
                "Install google-cloud-aiplatform and vertexai packages."
            )
        
        try:
            # Initialize Vertex AI (if not already initialized)
            try:
                aiplatform.init(project=GCP_PROJECT_ID, location=GCP_REGION)
            except Exception as e:
                # May already be initialized, that's fine
                logger.debug(f"Vertex AI init (may already be initialized): {e}")
            
            # Load the embedding model
            self.model = TextEmbeddingModel.from_pretrained(EMBEDDING_MODEL)
            self.model_name = EMBEDDING_MODEL
            self.dimension = EMBEDDING_DIMENSION
            
            structured_logger.info(
                "Embedding service initialized",
                model=EMBEDDING_MODEL,
                dimension=EMBEDDING_DIMENSION,
                project=GCP_PROJECT_ID,
                region=GCP_REGION
            )
            
        except Exception as e:
            structured_logger.error(
                "Failed to initialize embedding service",
                error=str(e),
                model=EMBEDDING_MODEL
            )
            raise
    
    def embed_text(self, text: str) -> List[float]:
        """
        Generate embedding for a single text.
        
        Args:
            text: Text to embed (max ~20,000 tokens recommended)
        
        Returns:
            List of floats representing the embedding vector (768 dimensions)
        
        Raises:
            Exception: If embedding generation fails
        """
        if not text or not text.strip():
            raise ValueError("Text cannot be empty")
        
        try:
            # Generate embedding
            embeddings = self.model.get_embeddings([text])
            
            if not embeddings or len(embeddings) == 0:
                raise ValueError("No embedding returned from model")
            
            embedding_vector = embeddings[0].values
            
            # Validate dimension
            if len(embedding_vector) != self.dimension:
                logger.warning(
                    f"Unexpected embedding dimension: {len(embedding_vector)} "
                    f"(expected {self.dimension})"
                )
            
            return embedding_vector
            
        except Exception as e:
            structured_logger.error(
                "Failed to generate embedding",
                error=str(e),
                text_length=len(text) if text else 0
            )
            raise
    
    def embed_batch(
        self,
        texts: List[str],
        batch_size: int = 100
    ) -> List[List[float]]:
        """
        Generate embeddings for a batch of texts.
        
        Args:
            texts: List of texts to embed
            batch_size: Number of texts to process per batch (default 100)
        
        Returns:
            List of embedding vectors, one per input text
        
        Raises:
            Exception: If embedding generation fails
        """
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
                embeddings = self.model.get_embeddings(valid_texts)
                
                # Map embeddings back to original positions
                embedding_dict = {text: emb.values for text, emb in zip(valid_texts, embeddings)}
                batch_embeddings = []
                for text in batch:
                    if text and text.strip():
                        batch_embeddings.append(embedding_dict[text])
                    else:
                        batch_embeddings.append(None)
                
                all_embeddings.extend(batch_embeddings)
                
                structured_logger.debug(
                    f"Processed embedding batch {i // batch_size + 1}/{(len(texts) + batch_size - 1) // batch_size}",
                    batch_size=len(batch),
                    total_processed=i + len(batch)
                )
            
            return all_embeddings
            
        except Exception as e:
            structured_logger.error(
                "Failed to generate batch embeddings",
                error=str(e),
                batch_count=len(texts),
                batch_size=batch_size
            )
            raise
    
    def get_embedding_info(self) -> dict:
        """
        Get information about the embedding service configuration.
        
        Returns:
            Dictionary with embedding service metadata
        """
        return {
            "model": self.model_name,
            "dimension": self.dimension,
            "project": GCP_PROJECT_ID,
            "region": GCP_REGION,
            "available": VERTEX_AI_AVAILABLE
        }


# Singleton instance (lazy initialization)
_embedding_service: Optional[EmbeddingService] = None


def get_embedding_service():
    """
    Get or create the singleton embedding service instance.
    
    Now uses multi-provider factory to automatically select the best available provider:
    - OpenAI (if OPENAI_API_KEY is set) - 87% cheaper than Vertex AI
    - Voyage (if VOYAGE_API_KEY or ANTHROPIC_API_KEY is set) - 33% cheaper
    - Vertex AI (fallback, if not disabled)
    
    Returns:
        BaseEmbeddingService instance (from multi-provider system)
    """
    # Try to use multi-provider factory first
    try:
        from services.llm_providers.embedding_factory import get_embedding_service as factory_get_service
        return factory_get_service()
    except Exception as e:
        # Only fallback to Vertex AI if it's not disabled
        import logging
        logger = logging.getLogger(__name__)
        
        # Check if Vertex AI is disabled
        vertex_disabled = VERTEX_AI_DISABLED
        if vertex_disabled:
            # Vertex AI is disabled, so don't fall back to it
            logger.error(f"Multi-provider factory failed and Vertex AI is disabled: {e}")
            raise RuntimeError(
                f"Failed to initialize embedding service. Multi-provider factory error: {e}\n"
                "Please ensure at least one of the following is configured:\n"
                "- OPENAI_API_KEY (recommended)\n"
                "- VOYAGE_API_KEY or ANTHROPIC_API_KEY\n"
                "Or enable Vertex AI by removing DISABLE_VERTEX_AI flag."
            )
        
        # Fallback to original Vertex AI implementation if factory fails and Vertex AI is enabled
        logger.warning(f"Multi-provider factory unavailable, falling back to Vertex AI: {e}")
        
        global _embedding_service
        if _embedding_service is None:
            _embedding_service = EmbeddingService()
        return _embedding_service

