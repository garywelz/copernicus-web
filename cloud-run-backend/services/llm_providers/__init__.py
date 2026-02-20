"""
Multi-Provider LLM Abstraction Layer

Provides unified interface for embeddings and RAG across multiple providers:
- OpenAI (embeddings + RAG)
- Anthropic/Voyage (embeddings + RAG)
- Vertex AI (embeddings + RAG) - fallback only

Factory functions automatically select the best available provider based on
environment variables and API key availability.
"""

from services.llm_providers.embedding_factory import get_embedding_service
from services.llm_providers.rag_factory import get_rag_service

__all__ = ['get_embedding_service', 'get_rag_service']
