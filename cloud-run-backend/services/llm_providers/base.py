"""
Base Classes for Multi-Provider LLM Services

Defines abstract interfaces for embedding and RAG services that all providers must implement.
"""

from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional


class BaseEmbeddingService(ABC):
    """Abstract base class for embedding services."""
    
    @property
    @abstractmethod
    def model_name(self) -> str:
        """Name of the embedding model being used."""
        pass
    
    @property
    @abstractmethod
    def dimension(self) -> int:
        """Dimension of the embedding vectors."""
        pass
    
    @property
    @abstractmethod
    def provider(self) -> str:
        """Name of the provider (e.g., 'openai', 'voyage', 'vertex_ai')."""
        pass
    
    @abstractmethod
    def embed_text(self, text: str) -> List[float]:
        """Generate embedding for a single text."""
        pass
    
    @abstractmethod
    def embed_batch(
        self,
        texts: List[str],
        batch_size: int = 100
    ) -> List[List[float]]:
        """Generate embeddings for a batch of texts."""
        pass
    
    def get_embedding_info(self) -> Dict[str, Any]:
        """Get information about the embedding service configuration."""
        return {
            "provider": self.provider,
            "model": self.model_name,
            "dimension": self.dimension
        }


class BaseRAGService(ABC):
    """Abstract base class for RAG (Retrieval-Augmented Generation) services."""
    
    @property
    @abstractmethod
    def provider(self) -> str:
        """Name of the provider (e.g., 'openai', 'anthropic', 'vertex_ai')."""
        pass
    
    @abstractmethod
    async def answer_question(
        self,
        question: str,
        context: str,
        include_sources: bool = True
    ) -> Dict[str, Any]:
        """
        Answer a question using provided context.
        
        Args:
            question: User's question
            context: Retrieved context to ground the answer
            include_sources: Whether to include source citations
        
        Returns:
            Dictionary with answer, sources, and metadata
        """
        pass
    
    def format_answer_with_citations(
        self,
        answer: str,
        sources: List[Dict[str, Any]]
    ) -> str:
        """
        Format answer with citations.
        
        Args:
            answer: The generated answer
            sources: List of source documents
        
        Returns:
            Formatted answer with citations
        """
        if not sources:
            return answer
        
        citation_text = "\n\nSources:\n"
        for i, source in enumerate(sources, 1):
            title = source.get('title', 'Unknown')
            citation_text += f"[{i}] {title}\n"
        
        return answer + citation_text
