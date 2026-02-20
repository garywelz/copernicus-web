"""
Anthropic Claude RAG Service

Provides RAG capabilities using Anthropic Claude models.
Cost: Claude Haiku is 50% cheaper than Vertex AI Gemini
"""

import logging
import os
from typing import Dict, Any, List

try:
    from anthropic import Anthropic
    ANTHROPIC_AVAILABLE = True
except ImportError:
    Anthropic = None
    ANTHROPIC_AVAILABLE = False

from services.llm_providers.base import BaseRAGService
from utils.logging import structured_logger

logger = logging.getLogger(__name__)


class ClaudeRAGService(BaseRAGService):
    """RAG service using Anthropic Claude."""
    
    def __init__(self, model: str = "claude-3-5-haiku-20241022"):
        """
        Initialize Claude RAG service.
        
        Args:
            model: Model name (claude-3-5-haiku recommended for cost, claude-3-5-sonnet for quality)
        """
        if not ANTHROPIC_AVAILABLE:
            raise ImportError(
                "Anthropic dependencies not available. "
                "Install anthropic package: pip install anthropic"
            )
        
        # Try to get API key from environment or Secret Manager
        from services.llm_providers.secret_manager_helpers import get_anthropic_api_key
        api_key = get_anthropic_api_key()
        if not api_key:
            raise ValueError(
                "ANTHROPIC_API_KEY not found in environment or Secret Manager. "
                "Please set ANTHROPIC_API_KEY environment variable or add 'anthropic-api-key' to Secret Manager. "
                "Get your API key from https://console.anthropic.com/"
            )
        
        try:
            self._client = Anthropic(api_key=api_key)
            self._model = model
            
            structured_logger.info(
                "Claude RAG service initialized",
                model=model
            )
        except Exception as e:
            structured_logger.error(
                "Failed to initialize Claude RAG service",
                error=str(e),
                model=model
            )
            raise
    
    @property
    def provider(self) -> str:
        return "anthropic"
    
    async def answer_question(
        self,
        question: str,
        context: str,
        include_sources: bool = True
    ) -> Dict[str, Any]:
        """Answer a question using provided context."""
        try:
            prompt = f"""You are a scientific research assistant with access to a knowledge base.

Use the following context to answer the question. Cite specific sources when possible.

Context:
{context}

Question: {question}

Answer the question based on the provided context. If the context doesn't contain enough information, say so."""

            message = self._client.messages.create(
                model=self._model,
                max_tokens=1000,
                temperature=0.1,
                messages=[
                    {
                        "role": "user",
                        "content": prompt
                    }
                ]
            )
            
            answer = message.content[0].text.strip()
            
            return {
                "answer": answer,
                "sources": [],  # Sources should be extracted from context
                "model": self._model,
                "provider": self.provider
            }
            
        except Exception as e:
            structured_logger.error(
                "Failed to generate Claude RAG answer",
                error=str(e),
                question=question[:100]
            )
            raise
