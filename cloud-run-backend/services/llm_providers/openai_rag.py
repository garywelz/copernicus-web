"""
OpenAI RAG Service

Provides RAG capabilities using OpenAI GPT models.
Cost: GPT-3.5-turbo is 85% cheaper than Vertex AI Gemini
"""

import logging
import os
from typing import Dict, Any, List

try:
    from openai import OpenAI
    OPENAI_AVAILABLE = True
except ImportError:
    OpenAI = None
    OPENAI_AVAILABLE = False

from services.llm_providers.base import BaseRAGService
from utils.logging import structured_logger

logger = logging.getLogger(__name__)


class OpenAIRAGService(BaseRAGService):
    """RAG service using OpenAI."""
    
    def __init__(self, model: str = "gpt-4o-mini"):
        """
        Initialize OpenAI RAG service.
        
        Args:
            model: Model name (gpt-4o-mini recommended for cost/quality, gpt-4o for higher quality)
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
            
            structured_logger.info(
                "OpenAI RAG service initialized",
                model=model
            )
        except Exception as e:
            structured_logger.error(
                "Failed to initialize OpenAI RAG service",
                error=str(e),
                model=model
            )
            raise
    
    @property
    def provider(self) -> str:
        return "openai"
    
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

            response = self._client.chat.completions.create(
                model=self._model,
                messages=[
                    {"role": "system", "content": "You are a helpful scientific research assistant."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.1,
                max_tokens=1000
            )
            
            answer = response.choices[0].message.content.strip()
            
            return {
                "answer": answer,
                "sources": [],  # Sources should be extracted from context
                "model": self._model,
                "provider": self.provider
            }
            
        except Exception as e:
            structured_logger.error(
                "Failed to generate OpenAI RAG answer",
                error=str(e),
                question=question[:100]
            )
            raise
