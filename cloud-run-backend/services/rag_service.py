"""
RAG (Retrieval-Augmented Generation) Service

Provides question-answering capabilities by combining vector search retrieval
with LLM generation, grounding answers in the knowledge base.
"""

import logging
from typing import Dict, List, Any, Optional
import json
from datetime import datetime
import os
import re

from services.embedding_service import get_embedding_service
from mcp_server.tools.vector_search import search_semantic
from utils.logging import structured_logger

logger = logging.getLogger(__name__)

def _env_flag(name: str, default: str = "0") -> bool:
    return (os.getenv(name, default) or "").strip().lower() in {"1", "true", "yes", "y", "on"}

VERTEX_AI_DISABLED = _env_flag("DISABLE_VERTEX_AI") or _env_flag("COPERNICUS_DISABLE_VERTEX_AI")

_STOPWORDS = {
    "a", "an", "and", "are", "as", "at", "be", "by", "for", "from", "how", "i",
    "in", "is", "it", "of", "on", "or", "that", "the", "this", "to", "was", "were",
    "what", "when", "where", "which", "who", "why", "with", "you", "your"
}

def _tokenize(text: str) -> List[str]:
    tokens = [t for t in re.split(r"[^a-zA-Z0-9]+", (text or "").lower()) if t]
    filtered = [t for t in tokens if (t not in _STOPWORDS) and (len(t) >= 3)]
    return filtered or tokens

def _extract_snippet(text: str, tokens: List[str], max_len: int = 320) -> str:
    if not text:
        return ""
    t = " ".join(str(text).split())
    lower = t.lower()
    if not tokens:
        return t[:max_len]
    sentences = re.split(r"(?<=[.!?])\s+", t)
    for s in sentences:
        ls = s.lower()
        if any(tok in ls for tok in tokens):
            return s.strip()[:max_len]
    for tok in tokens:
        idx = lower.find(tok)
        if idx >= 0:
            start = max(0, idx - 120)
            end = min(len(t), idx + max_len)
            return t[start:end].strip()
    return t[:max_len]

# Vertex AI imports
try:
    import google.generativeai as genai
    import vertexai
    VERTEX_AI_AVAILABLE = True
except ImportError:
    genai = None
    vertexai = None
    VERTEX_AI_AVAILABLE = False

# OpenAI chat imports
try:
    from openai import OpenAI
    OPENAI_AVAILABLE = True
except ImportError:
    OpenAI = None
    OPENAI_AVAILABLE = False


class RAGService:
    """
    RAG service for question-answering using knowledge base retrieval.
    
    Combines:
    1. Vector search to retrieve relevant content
    2. Context formatting with citations
    3. LLM generation with grounded context
    """
    
    def __init__(self):
        """Initialize RAG service with embedding and LLM clients."""
        self.embedding_service = None
        try:
            self.embedding_service = get_embedding_service()
        except Exception as e:
            structured_logger.warning(f"Embedding service unavailable for RAG: {e}")

        self.openai_client = None
        self.model = None  # Vertex GenerativeModel when used
        self.model_name = "none"
        self.llm_provider: Optional[str] = None

        rag_provider = os.getenv("RAG_PROVIDER", "").strip().lower()

        # OpenAI chat (preferred when key is available — same provider as embeddings)
        if rag_provider in ("", "openai", "auto") and OPENAI_AVAILABLE:
            from services.llm_providers.secret_manager_helpers import get_openai_api_key
            api_key = get_openai_api_key()
            if api_key:
                try:
                    self.openai_client = OpenAI(api_key=api_key)
                    self.model_name = os.getenv("OPENAI_RAG_MODEL", "gpt-4o-mini")
                    self.llm_provider = "openai"
                    structured_logger.info(
                        "RAG LLM initialized with OpenAI",
                        model=self.model_name,
                    )
                except Exception as e:
                    structured_logger.warning(f"Failed to initialize OpenAI for RAG: {e}")

        # Vertex AI fallback when OpenAI is unavailable
        if (
            self.llm_provider is None
            and rag_provider in ("", "vertex_ai", "vertex", "auto")
            and VERTEX_AI_AVAILABLE
            and not VERTEX_AI_DISABLED
        ):
            try:
                GCP_PROJECT_ID = os.getenv("GCP_PROJECT_ID", "regal-scholar-453620-r7")
                VERTEX_AI_REGION = os.getenv("GCP_REGION", "us-central1")
                vertexai.init(project=GCP_PROJECT_ID, location=VERTEX_AI_REGION)
                from vertexai.generative_models import GenerativeModel
                self.model = GenerativeModel("gemini-2.5-flash")
                self.model_name = "gemini-2.5-flash"
                self.llm_provider = "vertex"
                structured_logger.info("RAG LLM initialized with Vertex AI (fallback)")
            except Exception as e:
                structured_logger.warning(f"Failed to initialize Vertex AI for RAG: {e}")
                self.model = None

        if self.llm_provider is None:
            structured_logger.warning(
                "No LLM available for RAG generation (retrieval-only mode)"
            )

    @property
    def llm_available(self) -> bool:
        return self.openai_client is not None or self.model is not None

    def _generate_answer(self, prompt: str) -> str:
        """Generate an answer using OpenAI chat or Vertex Gemini."""
        if self.openai_client:
            response = self.openai_client.chat.completions.create(
                model=self.model_name,
                messages=[
                    {
                        "role": "system",
                        "content": "You are a helpful scientific research assistant.",
                    },
                    {"role": "user", "content": prompt},
                ],
                temperature=0.2,
                max_tokens=1024,
            )
            return (response.choices[0].message.content or "").strip()

        if self.model:
            response = self.model.generate_content(
                prompt,
                generation_config={
                    "temperature": 0.2,
                    "max_output_tokens": 1024,
                },
            )
            return response.text

        raise RuntimeError("No LLM configured for RAG generation")
    
    async def answer_question(
        self,
        question: str,
        max_context_items: int = 5,
        content_types: Optional[List[str]] = None,
        include_sources: bool = True,
        mode: str = "general",
        focus_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Answer a question using RAG (Retrieval-Augmented Generation).
        
        Args:
            question: User's question
            max_context_items: Maximum number of retrieved items to use as context
            content_types: Types of content to search (default: all)
            include_sources: Whether to include source citations
        
        Returns:
            Dictionary with answer, citations, sources, and metadata
        """
        try:
            # Step 1: Retrieve relevant content using vector search
            structured_logger.info(
                "Retrieving relevant content for RAG",
                question=question[:100],
                max_context=max_context_items,
                mode=mode,
                focus_id=focus_id,
            )
            
            # If we have a focused explanation request (e.g., paper or concept node),
            # bias retrieval toward that specific item while still allowing neighbors.
            search_query = question
            if focus_id and mode in ("paper_explanation", "concept_explanation"):
                search_query = f"{question} {focus_id}"

            if content_types is None:
                content_types = [
                    "papers", "podcasts", "glmp", "math", "chemistry",
                    "physics", "computer_science", "biology",
                ]

            search_result = await search_semantic(
                query=search_query,
                content_types=content_types,
                limit=max_context_items,
                distance_threshold=0.8,  # Slightly more lenient for RAG
            )
            
            search_data = json.loads(search_result)
            retrieval_method = search_data.get("search_method", "vector_semantic")
            
            # Step 2: Format context with citations
            context_parts = []
            citations = []
            citation_number = 1
            
            # Process papers
            for paper in search_data.get("papers", [])[:max_context_items]:
                title = paper.get("title", "Untitled Paper")
                abstract = paper.get("abstract", "")
                paper_id = paper.get("paper_id") or paper.get("id", "")
                doi = paper.get("doi", "")
                similarity = paper.get("similarity_score", 0)
                
                context_parts.append(
                    f"[{citation_number}] {title}\n"
                    f"Abstract: {abstract[:500] if abstract else 'No abstract available'}\n"
                    f"DOI: {doi if doi else 'N/A'}"
                )
                
                citations.append({
                    "number": citation_number,
                    "type": "paper",
                    "title": title,
                    "paper_id": paper_id,
                    "doi": doi,
                    "similarity_score": round(similarity, 3)
                })
                citation_number += 1
            
            # Process podcasts
            for podcast in search_data.get("podcasts", [])[:max_context_items]:
                result = podcast.get("result", {})
                title = result.get("title") or podcast.get("title", "Untitled Podcast")
                description = result.get("description") or podcast.get("description", "")
                job_id = podcast.get("job_id") or podcast.get("id", "")
                similarity = podcast.get("similarity_score", 0)
                
                # Get transcript snippet if available
                script = result.get("script", "")[:300] if result.get("script") else ""
                transcript_text = f"\nTranscript excerpt: {script}" if script else ""
                
                context_parts.append(
                    f"[{citation_number}] {title}\n"
                    f"Description: {description[:500] if description else 'No description available'}{transcript_text}"
                )
                
                citations.append({
                    "number": citation_number,
                    "type": "podcast",
                    "title": title,
                    "job_id": job_id,
                    "similarity_score": round(similarity, 3)
                })
                citation_number += 1
            
            # Process GLMP processes (if available)
            for process in search_data.get("glmp_processes", [])[:max_context_items]:
                title = process.get("title", "Untitled Process")
                description = process.get("description", "")
                process_id = process.get("process_id") or process.get("id", "")
                similarity = process.get("similarity_score", 0)
                
                context_parts.append(
                    f"[{citation_number}] GLMP Process: {title}\n"
                    f"Description: {description[:500] if description else 'No description available'}"
                )
                
                citations.append({
                    "number": citation_number,
                    "type": "glmp_process",
                    "title": title,
                    "process_id": process_id,
                    "similarity_score": round(similarity, 3)
                })
                citation_number += 1
            
            # Process math processes (if available)
            for process in search_data.get("math_processes", [])[:max_context_items]:
                title = process.get("title", "Untitled Process")
                description = process.get("description", "")
                process_id = process.get("process_id") or process.get("id", "")
                similarity = process.get("similarity_score", 0)
                
                context_parts.append(
                    f"[{citation_number}] Math Process: {title}\n"
                    f"Description: {description[:500] if description else 'No description available'}"
                )
                
                citations.append({
                    "number": citation_number,
                    "type": "math_process",
                    "title": title,
                    "process_id": process_id,
                    "similarity_score": round(similarity, 3)
                })
                citation_number += 1
            
            # Process chemistry processes (if available)
            for process in search_data.get("chemistry_processes", [])[:max_context_items]:
                title = process.get("title", "Untitled Process")
                description = process.get("description", "")
                process_id = process.get("process_id") or process.get("id", "")
                similarity = process.get("similarity_score", 0)
                
                context_parts.append(
                    f"[{citation_number}] Chemistry Process: {title}\n"
                    f"Description: {description[:500] if description else 'No description available'}"
                )
                
                citations.append({
                    "number": citation_number,
                    "type": "chemistry_process",
                    "title": title,
                    "process_id": process_id,
                    "similarity_score": round(similarity, 3)
                })
                citation_number += 1

            # Process physics processes (if available)
            for process in search_data.get("physics_processes", [])[:max_context_items]:
                title = process.get("title", "Untitled Process")
                description = process.get("description", "")
                process_id = process.get("process_id") or process.get("id", "")
                similarity = process.get("similarity_score", 0)
                context_parts.append(
                    f"[{citation_number}] Physics Process: {title}\n"
                    f"Description: {description[:500] if description else 'No description available'}"
                )
                citations.append({
                    "number": citation_number,
                    "type": "physics_process",
                    "title": title,
                    "process_id": process_id,
                    "similarity_score": round(similarity, 3)
                })
                citation_number += 1

            # Process CS processes (if available)
            for process in search_data.get("computer_science_processes", [])[:max_context_items]:
                title = process.get("title", "Untitled Process")
                description = process.get("description", "")
                process_id = process.get("process_id") or process.get("id", "")
                similarity = process.get("similarity_score", 0)
                context_parts.append(
                    f"[{citation_number}] Computer Science Process: {title}\n"
                    f"Description: {description[:500] if description else 'No description available'}"
                )
                citations.append({
                    "number": citation_number,
                    "type": "computer_science_process",
                    "title": title,
                    "process_id": process_id,
                    "similarity_score": round(similarity, 3)
                })
                citation_number += 1

            # Process biology processes (if available)
            for process in search_data.get("biology_processes", [])[:max_context_items]:
                title = process.get("title") or process.get("name", "Untitled Process")
                description = process.get("description", "")
                process_id = process.get("process_id") or process.get("id", "")
                similarity = process.get("similarity_score", 0)
                context_parts.append(
                    f"[{citation_number}] Biology Process: {title}\n"
                    f"Description: {description[:500] if description else 'No description available'}"
                )
                citations.append({
                    "number": citation_number,
                    "type": "biology_process",
                    "title": title,
                    "process_id": process_id,
                    "similarity_score": round(similarity, 3)
                })
                citation_number += 1

            sources = citations if include_sources else []

            # No LLM: return retrieval-only response (snippets + citations) instead of failing.
            if not self.llm_available:
                tokens = _tokenize(question)
                if not citations:
                    answer = (
                        "I couldn't find relevant information in the knowledge base to answer this question.\n\n"
                        "Note: No chat model is configured, so the system is running in retrieval-only mode."
                    )
                else:
                    bullets: List[str] = []
                    for c in citations[:max_context_items]:
                        idx = (c.get("number") or 1) - 1
                        chunk = context_parts[idx] if 0 <= idx < len(context_parts) else ""
                        snippet = _extract_snippet(chunk, tokens)
                        bullets.append(f"- [{c.get('number')}] {c.get('title')}: {snippet}")
                    answer = (
                        "No chat model is configured, so I can't generate a synthesized answer.\n"
                        "Here are the most relevant items I found (with excerpts):\n\n"
                        + "\n".join(bullets)
                    )

                return {
                    "question": question,
                    "answer": answer,
                    "citations": citations,
                    "sources": sources,
                    "metadata": {
                        "model": "none",
                        "llm_provider": None,
                        "generated_at": datetime.utcnow().isoformat(),
                        "retrieval_method": retrieval_method,
                        "context_items_used": len(sources),
                    },
                }
            
            if not context_parts:
                return {
                    "question": question,
                    "answer": "I couldn't find relevant information in the knowledge base to answer this question. Please try rephrasing or asking about a different topic.",
                    "citations": [],
                    "sources": [],
                    "counts": search_data.get("counts", {}),
                    "metadata": {
                        "context_items_used": 0,
                        "retrieval_method": retrieval_method,
                        "model": self.model_name
                    }
                }
            
            # Step 3: Format context for LLM
            context = "\n\n".join(context_parts)
            
            # Step 4: Generate answer with context
            prompt = f"""You are a scientific research assistant helping to answer questions based on a knowledge base of research papers, podcasts, and biological processes.

Use ONLY the provided context to answer the question. If the context doesn't contain enough information to fully answer the question, say so explicitly.

When referencing information from the context, cite sources using [1], [2], etc. corresponding to the numbered citations.

Question: {question}

Context from knowledge base:
{context}

Answer (with citations):"""

            structured_logger.info("Generating RAG answer",
                                  question=question[:100],
                                  context_items=len(context_parts))
            
            answer_text = self._generate_answer(prompt)

            # Step 5: Format response
            result = {
                "question": question,
                "answer": answer_text,
                "citations": citations if include_sources else [],
                # Sources should be a list so the API can accurately report context usage.
                "sources": citations if include_sources else [],
                "counts": search_data.get("counts", {}),
                "metadata": {
                    "context_items_used": len(context_parts),
                    "retrieval_method": retrieval_method,
                    "model": self.model_name,
                    "llm_provider": self.llm_provider,
                    "generated_at": datetime.utcnow().isoformat()
                }
            }
            
            structured_logger.info("RAG answer generated successfully",
                                  question=question[:100],
                                  answer_length=len(answer_text),
                                  citations=len(citations))
            
            return result
            
        except Exception as e:
            structured_logger.error("Error in RAG question answering",
                                  question=question[:100] if question else None,
                                  error=str(e))
            return {
                "error": f"Failed to generate answer: {str(e)}",
                "question": question,
                "answer": None,
                "citations": [],
                "sources": []
            }
    
    def format_answer_with_citations(self, answer: str, citations: List[Dict]) -> str:
        """
        Format answer with properly formatted citations.
        
        Args:
            answer: Answer text with [1], [2] citation markers
            citations: List of citation dictionaries
        
        Returns:
            Formatted answer with citation details
        """
        if not citations:
            return answer
        
        # Add citation details at the end
        citation_section = "\n\n**Sources:**\n"
        for citation in citations:
            citation_type = citation.get("type", "unknown")
            title = citation.get("title", "Untitled")
            number = citation.get("number", 0)
            
            if citation_type == "paper":
                doi = citation.get("doi", "")
                citation_section += f"{number}. {title}"
                if doi:
                    citation_section += f" (DOI: {doi})"
                citation_section += "\n"
            elif citation_type == "podcast":
                citation_section += f"{number}. Podcast: {title}\n"
            elif citation_type == "glmp_process":
                citation_section += f"{number}. Process: {title}\n"
        
        return answer + citation_section


# Singleton instance
_rag_service: Optional[RAGService] = None


def get_rag_service():
    """
    Get or create the singleton RAG service instance.

    IMPORTANT:
    The public `/api/rag/answer` endpoint relies on the retrieval orchestration implemented
    by `RAGService` (vector/keyword retrieval + context formatting + optional generation).
    Provider-specific RAG classes (e.g., `OpenAIRAGService`) implement a different interface
    (`answer_question(question, context, ...)`) and cannot be returned here without an
    adapter layer, otherwise the endpoint will 500 at runtime.

    Returns:
        `RAGService` singleton
    """
    global _rag_service
    if _rag_service is None:
        _rag_service = RAGService()
    return _rag_service


