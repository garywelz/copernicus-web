"""
Knowledge Map Service

Builds and manages a knowledge graph of mathematics papers, concepts, and relationships.

Copyright (c) 2025 Gary Welz / CopernicusAI
Licensed under MIT License
"""

import logging
from typing import Dict, List, Any, Optional, Set, Tuple
from datetime import datetime
from collections import defaultdict
import re

from google.cloud import firestore
from google.cloud.firestore_v1.vector import Vector
from google.cloud.firestore_v1.base_vector_query import DistanceMeasure

from services.embedding_service import get_embedding_service
from mcp_server.config import GCP_PROJECT_ID
from config.database import db
from utils.logging import structured_logger

logger = logging.getLogger(__name__)

_STOPWORDS = {
    # Generic stopwords
    "a", "an", "and", "are", "as", "at", "be", "by", "for", "from", "how", "in", "is", "it",
    "of", "on", "or", "that", "the", "this", "to", "was", "were", "what", "when", "where",
    "which", "who", "why", "with", "we", "our", "their", "its",
    # Common scientific filler
    "using", "use", "used", "method", "methods", "result", "results", "analysis", "data",
    "study", "studies", "model", "models", "approach", "based", "new", "novel",
    "paper", "research", "article", "report",
}


def _tokenize_text(text: str) -> List[str]:
    tokens = [t for t in re.split(r"[^a-zA-Z0-9]+", (text or "").lower()) if t]
    out: List[str] = []
    for t in tokens:
        if t in _STOPWORDS:
            continue
        if t.isdigit():
            continue
        if len(t) < 4:
            continue
        if len(t) > 28:
            continue
        out.append(t)
    return out


class KnowledgeMapService:
    """
    Service for building and querying the mathematics knowledge map.
    
    The knowledge map consists of:
    - Nodes: Papers, Concepts, Processes, Authors
    - Edges: Citations, Concept mentions, Similarity, Category relationships
    """
    
    def __init__(self):
        """Initialize the knowledge map service."""
        # Use the same Firestore client as the rest of the app
        if db is None:
            # Fallback if db not initialized
            self.db = firestore.Client(project=GCP_PROJECT_ID, database="copernicusai")
        else:
            self.db = db
        
        # Embedding service is NOT required for the interactive knowledge map.
        # The map uses embeddings that were precomputed and stored in Firestore.
        # To avoid any accidental Vertex AI initialization (and billing),
        # we explicitly disable embedding service usage here.
        self.embedding_service = None
        
        # Graph structure (in-memory for now, can be persisted to Firestore later)
        self.nodes: Dict[str, Dict[str, Any]] = {}
        self.edges: List[Dict[str, Any]] = []
        
        structured_logger.info("Knowledge map service initialized")
    
    def clear_cache(self):
        """Clear the cached graph data."""
        self.nodes = {}
        self.edges = []
        structured_logger.info("Cleared knowledge map cache")
    
    async def extract_citation_relationships(
        self,
        papers: List[Dict[str, Any]],
        use_semantic_scholar: bool = False,
        max_papers_for_citations: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """
        Extract citation relationships from papers.
        
        Uses:
        1. Semantic Scholar API (if enabled)
        2. DOI references if available
        3. Similar papers (via vector similarity)
        4. Category-based relationships
        """
        relationships = []
        paper_ids = {p.get('paper_id') or p.get('id'): p for p in papers}
        paper_id_to_arxiv = {p.get('paper_id') or p.get('id'): p.get('arxiv_id') for p in papers}
        paper_id_to_doi = {p.get('paper_id') or p.get('id'): p.get('doi') for p in papers}
        
        # Use Semantic Scholar if enabled
        if use_semantic_scholar:
            try:
                from services.semantic_scholar_service import get_semantic_scholar_service
                ss_service = get_semantic_scholar_service()
                
                papers_to_fetch = papers
                if max_papers_for_citations:
                    papers_to_fetch = papers[:max_papers_for_citations]
                
                citation_data = await ss_service.get_citations_batch(papers_to_fetch)
                
                # Create citation relationships from Semantic Scholar data
                for paper_id, citations_info in citation_data.items():
                    # Add citation edges (this paper cites others)
                    for ref in citations_info.get('references', []):
                        ref_paper_id = ref.get('paper_id')
                        # Try to find paper in our database by Semantic Scholar ID
                        # For now, we'll store the relationship with the Semantic Scholar ID
                        # and match later if we have that paper
                        relationships.append({
                            'type': 'cites',
                            'source': paper_id,
                            'target': f'ss:{ref_paper_id}',  # Mark as Semantic Scholar ID
                            'weight': 1.0,
                            'metadata': {
                                'method': 'semantic_scholar',
                                'cited_title': ref.get('title')
                            }
                        })
                    
                    # Add cited-by edges (other papers cite this one)
                    for cit in citations_info.get('citations', []):
                        cit_paper_id = cit.get('paper_id')
                        relationships.append({
                            'type': 'cited_by',
                            'source': f'ss:{cit_paper_id}',
                            'target': paper_id,
                            'weight': 1.0,
                            'metadata': {
                                'method': 'semantic_scholar',
                                'citer_title': cit.get('title')
                            }
                        })
                
                await ss_service.close()
                structured_logger.info(f"Extracted {len([r for r in relationships if r['type'] == 'cites'])} citations from Semantic Scholar")
            
            except Exception as e:
                logger.warning(f"Failed to fetch Semantic Scholar citations: {e}")
        
        # Extract DOI-based citations (if papers have citation data)
        for paper in papers:
            paper_id = paper.get('paper_id') or paper.get('id')
            cited_dois = paper.get('cited_dois', []) or paper.get('references', [])
            
            for doi in cited_dois:
                # Find paper with matching DOI
                cited_paper = next(
                    (p for p in papers if p.get('doi') == doi),
                    None
                )
                
                if cited_paper:
                    cited_id = cited_paper.get('paper_id') or cited_paper.get('id')
                    relationships.append({
                        'type': 'cites',
                        'source': paper_id,
                        'target': cited_id,
                        'weight': 1.0,
                        'metadata': {'method': 'doi_reference'}
                    })
        
        return relationships
    
    def extract_concept_relationships(
        self,
        papers: List[Dict[str, Any]],
        similarity_threshold: float = 0.7
    ) -> List[Dict[str, Any]]:
        """
        Extract concept-based relationships using vector similarity.
        
        Papers with similar embeddings are likely related.
        """
        relationships = []
        
        # Group papers by category for efficiency
        papers_by_category = defaultdict(list)
        for paper in papers:
            categories = paper.get('categories', [])
            for cat in categories:
                papers_by_category[cat].append(paper)
        
        # Find similar papers within categories
        for category, category_papers in papers_by_category.items():
            if len(category_papers) < 2:
                continue
            
            # Use vector search to find similar papers
            for paper in category_papers[:100]:  # Limit for performance
                paper_id = paper.get('paper_id') or paper.get('id')
                paper_embedding = paper.get('embedding')
                
                if not paper_embedding:
                    continue
                
                # Find similar papers using Firestore vector search
                try:
                    papers_ref = self.db.collection('research_papers')
                    vector_query = papers_ref.find_nearest(
                        vector_field='embedding',
                        query_vector=Vector(paper_embedding.values if hasattr(paper_embedding, 'values') else paper_embedding),
                        limit=5,
                        distance_measure=DistanceMeasure.COSINE,
                        distance_threshold=1.0 - similarity_threshold
                    )
                    
                    for similar_doc in vector_query.stream():
                        similar_data = similar_doc.to_dict()
                        similar_id = similar_doc.id
                        
                        if similar_id != paper_id:
                            relationships.append({
                                'type': 'similar_to',
                                'source': paper_id,
                                'target': similar_id,
                                'weight': 1.0 - similar_data.get('distance', 0.5),
                                'metadata': {
                                    'method': 'vector_similarity',
                                    'category': category
                                }
                            })
                except Exception as e:
                    logger.warning(f"Failed to find similar papers for {paper_id}: {e}")
                    continue
        
        return relationships

    def extract_keyword_similarity_relationships(
        self,
        papers: List[Dict[str, Any]],
        top_k: int = 2,
        min_jaccard: float = 0.12,
        min_overlap_tokens: int = 2,
    ) -> List[Dict[str, Any]]:
        """
        Fallback similarity edges when embeddings are missing/disabled.

        Computes simple Jaccard overlap over tokenized title/abstract/keywords and connects
        each paper to its top-k neighbors above thresholds.
        """
        token_sets: List[Tuple[str, Set[str]]] = []
        for p in papers:
            pid = p.get("paper_id") or p.get("id")
            if not pid:
                continue
            title = p.get("title") or ""
            abstract = p.get("abstract") or ""
            kws = p.get("keywords") or []
            if isinstance(kws, list):
                kw_text = " ".join([str(x) for x in kws if x])
            else:
                kw_text = str(kws)
            toks = set(_tokenize_text(f"{title} {abstract} {kw_text}"))
            if toks:
                token_sets.append((pid, toks))

        if len(token_sets) < 2:
            return []

        edges: List[Dict[str, Any]] = []
        seen_pairs: Set[Tuple[str, str]] = set()

        for i, (pid, toks) in enumerate(token_sets):
            candidates: List[Tuple[float, int, str]] = []  # (jaccard, overlap, other_id)
            for j, (oid, otoks) in enumerate(token_sets):
                if i == j:
                    continue
                inter = toks.intersection(otoks)
                overlap = len(inter)
                if overlap < min_overlap_tokens:
                    continue
                union = len(toks.union(otoks)) or 1
                jacc = overlap / union
                if jacc < min_jaccard:
                    continue
                candidates.append((jacc, overlap, oid))

            candidates.sort(reverse=True)
            for jacc, overlap, oid in candidates[: max(0, int(top_k))]:
                a, b = (pid, oid) if pid < oid else (oid, pid)
                if (a, b) in seen_pairs:
                    continue
                seen_pairs.add((a, b))
                edges.append({
                    "type": "similar_to",
                    "source": pid,
                    "target": oid,
                    "weight": float(jacc),
                    "metadata": {
                        "method": "keyword_overlap",
                        "overlap_tokens": int(overlap),
                    }
                })

        return edges
    
    def extract_author_relationships(self, papers: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Extract author co-authorship relationships.
        
        Papers with shared authors are connected.
        """
        relationships = []
        
        # Build author-to-papers mapping
        author_to_papers = defaultdict(list)
        for paper in papers:
            paper_id = paper.get('paper_id') or paper.get('id')
            authors = paper.get('authors', [])
            
            for author in authors:
                if author:  # Skip empty authors
                    author_to_papers[author].append(paper_id)
        
        # Create relationships between papers with shared authors
        for author, paper_ids in author_to_papers.items():
            if len(paper_ids) < 2:
                continue
            
            # Connect papers by the same author (limit to avoid too many edges)
            for i, paper_id1 in enumerate(paper_ids[:20]):  # Limit for performance
                for paper_id2 in paper_ids[i+1:min(i+6, len(paper_ids))]:  # Connect to next 5 papers
                    relationships.append({
                        'type': 'co_author',
                        'source': paper_id1,
                        'target': paper_id2,
                        'weight': 0.7,
                        'metadata': {'author': author}
                    })
        
        return relationships
    
    def extract_category_relationships(self, papers: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Extract relationships based on shared categories.
        
        Papers in the same category are related.
        """
        relationships = []
        
        # Group papers by category
        papers_by_category = defaultdict(list)
        for paper in papers:
            paper_id = paper.get('paper_id') or paper.get('id')
            categories = paper.get('categories', [])
            
            for cat in categories:
                papers_by_category[cat].append(paper_id)
        
        # Create relationships between papers in the same category
        for category, paper_ids in papers_by_category.items():
            if len(paper_ids) < 2:
                continue
            
            # Connect papers in the same category (limit to avoid too many edges)
            for i, paper_id1 in enumerate(paper_ids[:50]):  # Limit for performance
                for paper_id2 in paper_ids[i+1:min(i+6, len(paper_ids))]:  # Connect to next 5 papers
                    relationships.append({
                        'type': 'same_category',
                        'source': paper_id1,
                        'target': paper_id2,
                        'weight': 0.5,
                        'metadata': {'category': category}
                    })
        
        return relationships
    
    async def extract_concepts_from_papers(
        self,
        papers: List[Dict[str, Any]],
        use_llm: bool = False,
        max_papers_for_llm: Optional[int] = 100,
        keyword: Optional[str] = None,
    ) -> Dict[str, List[str]]:
        """
        Extract mathematical concepts from papers.
        
        Uses:
        1. LLM extraction (if enabled) - more detailed concepts
        2. Keywords from paper metadata
        3. Category names as concepts
        """
        concepts = defaultdict(list)
        
        # LLM-based concept extraction
        if use_llm:
            try:
                from vertexai.generative_models import GenerativeModel
                import vertexai
                import os
                
                # Initialize Vertex AI
                project_id = os.getenv("GCP_PROJECT_ID", "regal-scholar-453620-r7")
                region = os.getenv("GCP_REGION", "us-central1")
                
                if not vertexai.is_initialized():
                    vertexai.init(project=project_id, location=region)
                
                model = GenerativeModel("gemini-2.0-flash-exp")
                
                papers_to_extract = papers
                if max_papers_for_llm:
                    papers_to_extract = papers[:max_papers_for_llm]
                
                structured_logger.info(f"Extracting concepts with LLM for {len(papers_to_extract)} papers")
                
                for i, paper in enumerate(papers_to_extract, 1):
                    paper_id = paper.get('paper_id') or paper.get('id')
                    title = paper.get('title', '')
                    abstract = paper.get('abstract', '')[:1000]  # Limit abstract length
                    
                    if not title and not abstract:
                        continue
                    
                    try:
                        prompt = f"""Extract the main mathematical concepts from this research paper.

Title: {title}
Abstract: {abstract[:500]}

Return a JSON list of 3-5 key mathematical concepts, theorems, or methods mentioned in this paper.
Format: ["concept1", "concept2", "concept3"]
Only return the JSON array, no other text."""

                        response = model.generate_content(prompt)
                        concepts_text = response.text.strip()
                        
                        # Parse JSON
                        import json
                        # Remove markdown code blocks if present
                        if concepts_text.startswith('```'):
                            concepts_text = concepts_text.split('```')[1]
                            if concepts_text.startswith('json'):
                                concepts_text = concepts_text[4:]
                        concepts_text = concepts_text.strip()
                        
                        extracted_concepts = json.loads(concepts_text)
                        
                        for concept in extracted_concepts:
                            if isinstance(concept, str) and len(concept) > 2:
                                concepts[concept.lower()].append(paper_id)
                        
                        if i % 10 == 0:
                            structured_logger.info(f"LLM concept extraction progress: {i}/{len(papers_to_extract)}")
                    
                    except Exception as e:
                        logger.warning(f"Failed to extract concepts with LLM for paper {paper_id}: {e}")
                        continue
                
                structured_logger.info(f"Extracted {len(concepts)} concepts using LLM")
            
            except Exception as e:
                logger.warning(f"LLM concept extraction not available: {e}")
        
        # Fallback: Extract from categories, keywords, and lightweight title/abstract tokens
        paper_tokens: Dict[str, List[str]] = {}
        token_counts = defaultdict(int)

        for paper in papers:
            paper_id = paper.get('paper_id') or paper.get('id')
            if not paper_id:
                continue

            # Extract from categories
            paper_categories = paper.get('categories', [])
            for cat in paper_categories:
                concept_name = self._category_to_concept(cat)
                concepts[concept_name].append(paper_id)

            # Extract from keywords if available
            kws = paper.get('keywords', [])
            if isinstance(kws, list):
                for kw in kws[:10]:
                    if isinstance(kw, str) and kw.strip():
                        concepts[kw.strip().lower()].append(paper_id)
            elif isinstance(kws, str) and kws.strip():
                concepts[kws.strip().lower()].append(paper_id)

            # Extract lightweight concepts from title/abstract tokens.
            title = paper.get("title") or ""
            abstract = paper.get("abstract") or ""
            toks = _tokenize_text(f"{title} {abstract}")
            if toks:
                paper_tokens[paper_id] = toks
                for t in set(toks):
                    token_counts[t] += 1

        # If a keyword filter was used for this map, add it as a concept connected to all papers
        # in the filtered set (so the graph is guaranteed to have at least one concept hub).
        if keyword and keyword.strip():
            kw = keyword.strip().lower()
            concepts[kw].extend([p.get("paper_id") or p.get("id") for p in papers if (p.get("paper_id") or p.get("id"))])

        # Add token concepts that occur in >=2 papers (avoid noisy one-offs)
        for pid, toks in paper_tokens.items():
            ranked = sorted(set(toks), key=lambda t: token_counts.get(t, 0), reverse=True)
            added = 0
            for t in ranked:
                if token_counts.get(t, 0) < 2:
                    continue
                concepts[t].append(pid)
                added += 1
                if added >= 8:
                    break

        return dict(concepts)
    
    def _category_to_concept(self, category: str) -> str:
        """Convert arXiv category code to concept name."""
        category_map = {
            'math.AG': 'Algebraic Geometry',
            'math.AT': 'Algebraic Topology',
            'math.CA': 'Classical Analysis',
            'math.CO': 'Combinatorics',
            'math.CT': 'Category Theory',
            'math.DG': 'Differential Geometry',
            'math.DS': 'Dynamical Systems',
            'math.GT': 'Geometric Topology',
            'math.LO': 'Logic',
            'math.NT': 'Number Theory',
            'math.OA': 'Operator Algebras',
            'math.PR': 'Probability',
            'math.RA': 'Rings and Algebras',
            'math.RT': 'Representation Theory',
            'math.SG': 'Symplectic Geometry',
            'math.ST': 'Statistics Theory',
            'math.AP': 'Analysis of PDEs',
            'math.NA': 'Numerical Analysis',
            'math.OC': 'Optimization and Control',
            'math.AC': 'Commutative Algebra',
            'math.FA': 'Functional Analysis',
            'math.GR': 'Group Theory',
            'math.MP': 'Mathematical Physics',
            'math.MG': 'Metric Geometry',
        }
        return category_map.get(category, category.replace('math.', '').upper())
    
    async def build_graph(
        self,
        max_papers: Optional[int] = None,
        include_concepts: bool = True,
        include_similarity: bool = True,
        include_categories: bool = True,
        include_authors: bool = False,
        use_semantic_scholar: bool = False,
        use_llm_concepts: bool = False,
        max_papers_for_citations: Optional[int] = None,
        content_types: Optional[List[str]] = None,
        disciplines: Optional[List[str]] = None,
        sources: Optional[List[str]] = None,
        date_start: Optional[str] = None,
        date_end: Optional[str] = None,
        keyword: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Build the knowledge graph from papers in Firestore.
        
        Args:
            max_papers: Maximum number of papers to include (None for all)
            include_concepts: Extract and include concept nodes
            include_similarity: Include similarity-based relationships
            include_categories: Include category-based relationships
            include_authors: Include author co-authorship relationships
            use_semantic_scholar: Use Semantic Scholar API for citations
            use_llm_concepts: Use LLM for concept extraction
            max_papers_for_citations: Limit papers for citation/LLM extraction
            content_types: Filter by content types (papers, processes, videos, podcasts)
            disciplines: Filter by disciplines (biology, chemistry, physics, mathematics, computer_science, interdisciplinary)
            sources: Filter by sources (pubmed, arxiv, nasa_ads, crossref, youtube, rss)
            date_start: Start date filter (YYYY-MM-DD)
            date_end: End date filter (YYYY-MM-DD)
            keyword: Keyword search in title/abstract
        
        Returns:
            Dictionary with nodes and edges
        """
        structured_logger.info("Building knowledge graph", 
                             max_papers=max_papers,
                             content_types=content_types,
                             disciplines=disciplines,
                             sources=sources,
                             date_start=date_start,
                             date_end=date_end,
                             keyword=keyword)
        
        # Fetch papers from Firestore
        # Note: To avoid composite index requirements, we fetch first and filter in memory.
        # However, when filters are present, we must sample a MUCH larger window; otherwise
        # we might fetch an arbitrary small subset that contains zero matching papers.
        papers_ref = self.db.collection('research_papers')
        
        # We intentionally do NOT apply Firestore where() filters here (even when a single source
        # is requested) to avoid composite index requirements, since we want to order by recency.
        single_source_filter = False

        has_filters = any([disciplines, sources, date_start, date_end, keyword])
        # Heuristic: when any filter is present, sample a large window so the user doesn't get 0
        # just because the first N documents didn't match.
        candidate_limit = None
        if max_papers:
            candidate_limit = 20000 if has_filters else max_papers
        else:
            candidate_limit = 20000 if has_filters else 1000

        # Prefer a deterministic, recent-first sample.
        # If ordering fails due to inconsistent field types, fall back to unordered sampling.
        try:
            papers_query = papers_ref.order_by('updated_at', direction=firestore.Query.DESCENDING)
        except Exception:
            papers_query = papers_ref

        if candidate_limit:
            papers_query = papers_query.limit(candidate_limit)

        structured_logger.info(
            "Sampling papers for knowledge map build",
            candidate_limit=candidate_limit,
            ordered_by_updated_at=isinstance(getattr(papers_query, "_orders", None), list)  # best-effort debug
        )
        
        papers = []
        filter_stats = {
            'total_fetched': 0,
            'after_source': 0,
            'after_discipline': 0,
            'after_date': 0,
            'after_keyword': 0,
            'final': 0
        }

        distinct_sources_set: Set[str] = set()
        distinct_disciplines_set: Set[str] = set()
        sample_fetched: List[Dict[str, Any]] = []
        
        # Stream and filter in one pass to avoid loading huge docs into memory.
        try:
            stream_iter = papers_query.stream()
        except Exception as e:
            structured_logger.warning("Paper sampling query failed; falling back to unordered sampling", error=str(e))
            stream_iter = papers_ref.limit(candidate_limit).stream() if candidate_limit else papers_ref.stream()

        for doc in stream_iter:
            paper_data = doc.to_dict()
            paper_data['paper_id'] = doc.id
            filter_stats['total_fetched'] += 1

            # Collect some debug signals
            sources_list = paper_data.get('sources') or []
            if isinstance(sources_list, list):
                distinct_sources_set.update([str(s) for s in sources_list if s])
            elif sources_list:
                distinct_sources_set.add(str(sources_list))

            disc = paper_data.get('discipline')
            if isinstance(disc, str) and disc:
                distinct_disciplines_set.add(disc)

            if len(sample_fetched) < 3:
                sample_fetched.append({
                    "id": paper_data.get("paper_id") or paper_data.get("id"),
                    "sources": paper_data.get("sources"),
                    "discipline": paper_data.get("discipline"),
                    "published_at": str(paper_data.get("published_at"))[:50] if paper_data.get("published_at") else None,
                    "title": (paper_data.get("title") or "")[:80],
                })

            # Apply all filters in memory (avoids composite index requirements)
            # Source filter - database has 'sources' as array
            if sources and (len(sources) > 1 or not single_source_filter):
                paper_sources = paper_data.get('sources') or []
                if not isinstance(paper_sources, list):
                    paper_sources = [paper_sources] if paper_sources else []
                # Check if any of the requested sources is in the paper's sources array
                if not any(req_source in paper_sources for req_source in sources):
                    continue
            filter_stats['after_source'] += 1
            
            # Discipline filter - database has 'discipline' as singular field
            if disciplines:
                paper_discipline = paper_data.get('discipline')
                # Normalize to lowercase for comparison
                if paper_discipline and isinstance(paper_discipline, str):
                    paper_discipline_lower = paper_discipline.lower()
                    if not any(disc.lower() == paper_discipline_lower for disc in disciplines):
                        continue
                elif not paper_discipline:
                    # Skip papers without discipline if filter is set
                    continue
            filter_stats['after_discipline'] += 1
            
            # Date filters - database has 'published_at' as timestamp
            date_passed = True
            if date_start:
                paper_date = paper_data.get('published_at') or paper_data.get('published_date') or paper_data.get('year')
                if paper_date:
                    # Try to parse date properly
                    try:
                        # Handle Firestore Timestamp
                        if hasattr(paper_date, 'timestamp'):
                            paper_dt = datetime.fromtimestamp(paper_date.timestamp())
                            start_dt = datetime.fromisoformat(date_start)
                            if paper_dt.date() < start_dt.date():
                                date_passed = False
                        elif isinstance(paper_date, datetime):
                            start_dt = datetime.fromisoformat(date_start)
                            if paper_date.date() < start_dt.date():
                                date_passed = False
                        elif isinstance(paper_date, str):
                            # Handle ISO format (YYYY-MM-DD or YYYY-MM-DDTHH:MM:SS)
                            date_str = paper_date.split('T')[0]  # Remove time if present
                            paper_dt = datetime.fromisoformat(date_str)
                            start_dt = datetime.fromisoformat(date_start)
                            if paper_dt < start_dt:
                                date_passed = False
                        elif isinstance(paper_date, int):
                            # Year only or timestamp
                            if paper_date > 2000:  # Assume year
                                start_year = int(date_start.split('-')[0])
                                if paper_date < start_year:
                                    date_passed = False
                    except (ValueError, AttributeError, TypeError) as e:
                        structured_logger.debug(f"Date parsing error for {paper_date}: {e}")
                        # Skip date filter if we can't parse
                        pass
                if not date_passed:
                    continue
            
            if date_end:
                paper_date = paper_data.get('published_at') or paper_data.get('published_date') or paper_data.get('year')
                if paper_date:
                    try:
                        # Handle Firestore Timestamp
                        if hasattr(paper_date, 'timestamp'):
                            paper_dt = datetime.fromtimestamp(paper_date.timestamp())
                            end_dt = datetime.fromisoformat(date_end)
                            if paper_dt.date() > end_dt.date():
                                date_passed = False
                        elif isinstance(paper_date, datetime):
                            end_dt = datetime.fromisoformat(date_end)
                            if paper_date.date() > end_dt.date():
                                date_passed = False
                        elif isinstance(paper_date, str):
                            date_str = paper_date.split('T')[0]
                            paper_dt = datetime.fromisoformat(date_str)
                            end_dt = datetime.fromisoformat(date_end)
                            if paper_dt > end_dt:
                                date_passed = False
                        elif isinstance(paper_date, int):
                            if paper_date > 2000:  # Assume year
                                end_year = int(date_end.split('-')[0])
                                if paper_date > end_year:
                                    date_passed = False
                    except (ValueError, AttributeError, TypeError) as e:
                        structured_logger.debug(f"Date parsing error for {paper_date}: {e}")
                        # Skip date filter if we can't parse
                        pass
                if not date_passed:
                    continue
            filter_stats['after_date'] += 1
            
            # Keyword search (improved - tokenize and handle variations)
            if keyword:
                keyword_lower = keyword.lower().strip()
                # Tokenize keyword (split on spaces/hyphens)
                keyword_tokens = keyword_lower.replace('-', ' ').split()
                keyword_joined = ''.join(keyword_tokens)  # For "corona virus" -> "coronavirus"
                
                title = (paper_data.get('title') or '').lower()
                abstract = (paper_data.get('abstract') or '').lower()
                keywords_list = ' '.join(paper_data.get('keywords', [])).lower()
                all_text = f"{title} {abstract} {keywords_list}"
                
                # Check for exact match, tokenized match, and common variations
                keyword_matched = (
                    keyword_lower in all_text or  # "corona virus"
                    keyword_joined in all_text or  # "coronavirus"
                    any(token in all_text for token in keyword_tokens if len(token) > 3)  # Any significant token
                )
                
                # Handle common COVID-19 variations
                if 'covid' in keyword_lower or 'corona' in keyword_lower:
                    covid_variants = ['covid', 'covid-19', 'coronavirus', 'corona virus', 'sars-cov']
                    keyword_matched = keyword_matched or any(var in all_text for var in covid_variants)
                
                if not keyword_matched:
                    continue
            filter_stats['after_keyword'] += 1
            
            papers.append(paper_data)
            filter_stats['final'] += 1
            
            # Apply max_papers limit after filtering
            if max_papers and len(papers) >= max_papers:
                break

        structured_logger.info(f"Distinct sources in sampled papers: {sorted(distinct_sources_set)}")
        structured_logger.info(f"Distinct disciplines in sampled papers: {sorted(distinct_disciplines_set)}")
        structured_logger.info(f"Filtering results: {filter_stats}")
        if sample_fetched:
            structured_logger.info(f"Sample fetched papers: {sample_fetched}")
        
        if papers:
            sample_final = [
                {
                    "id": p.get("paper_id") or p.get("id"),
                    "sources": p.get("sources"),
                    "discipline": p.get("discipline"),
                    "published_at": str(p.get("published_at"))[:50] if p.get("published_at") else None,
                    "title": (p.get("title") or "")[:80],
                }
                for p in papers[:3]
            ]
            structured_logger.info(f"Sample final filtered papers: {sample_final}")
        
        structured_logger.info(f"Final filtered papers: {len(papers)}")
        
        # Build nodes
        nodes = []
        for paper in papers:
            paper_id = paper.get('paper_id')
            nodes.append({
                'id': paper_id,
                'type': 'paper',
                'label': paper.get('title', 'Untitled')[:100],
                'data': {
                    'title': paper.get('title'),
                    'categories': paper.get('categories', []),
                    'arxiv_id': paper.get('arxiv_id'),
                    'doi': paper.get('doi'),
                }
            })
        
        # Build edges
        edges = []
        
        # Extract relationships
        if include_categories:
            category_rels = self.extract_category_relationships(papers)
            edges.extend(category_rels)
            structured_logger.info(f"Extracted {len(category_rels)} category relationships")
        
        if include_authors:
            author_rels = self.extract_author_relationships(papers)
            edges.extend(author_rels)
            structured_logger.info(f"Extracted {len(author_rels)} author co-authorship relationships")
        
        if include_similarity:
            similarity_rels = self.extract_concept_relationships(papers)
            edges.extend(similarity_rels)
            structured_logger.info(f"Extracted {len(similarity_rels)} similarity relationships")
            if not similarity_rels:
                kw_sim_rels = self.extract_keyword_similarity_relationships(papers)
                edges.extend(kw_sim_rels)
                structured_logger.info(f"Extracted {len(kw_sim_rels)} keyword-overlap similarity relationships")
        
        # Extract citation relationships (including Semantic Scholar if enabled)
        citation_rels = await self.extract_citation_relationships(
            papers,
            use_semantic_scholar=use_semantic_scholar,
            max_papers_for_citations=max_papers_for_citations
        )
        edges.extend(citation_rels)
        structured_logger.info(f"Extracted {len(citation_rels)} citation relationships")
        
        # Extract concepts if requested
        if include_concepts:
            concepts = await self.extract_concepts_from_papers(
                papers,
                use_llm=use_llm_concepts,
                max_papers_for_llm=max_papers_for_citations,
                keyword=keyword,
            )
            
            # Add concept nodes
            for concept_name, paper_ids in concepts.items():
                if len(paper_ids) >= 2:  # Only include concepts mentioned in 2+ papers
                    nodes.append({
                        'id': f'concept:{concept_name}',
                        'type': 'concept',
                        'label': concept_name,
                        'data': {'paper_count': len(paper_ids)}
                    })
                    
                    # Add concept-paper edges
                    for paper_id in paper_ids[:20]:  # Limit edges per concept
                        edges.append({
                            'type': 'mentions',
                            'source': paper_id,
                            'target': f'concept:{concept_name}',
                            'weight': 1.0,
                            'metadata': {}
                        })
            
            structured_logger.info(f"Extracted {len(concepts)} concepts")
        
        # Store graph
        self.nodes = {node['id']: node for node in nodes}
        self.edges = edges
        
        structured_logger.info(
            "Knowledge graph built",
            nodes=len(nodes),
            edges=len(edges)
        )
        
        return {
            'nodes': nodes,
            'edges': edges,
            'metadata': {
                'papers': len([n for n in nodes if n['type'] == 'paper']),
                'concepts': len([n for n in nodes if n['type'] == 'concept']),
                'relationships': len(edges),
                'built_at': datetime.utcnow().isoformat()
            }
        }
    
    def get_subgraph(
        self,
        paper_id: str,
        depth: int = 2,
        max_nodes: int = 50
    ) -> Dict[str, Any]:
        """
        Get a subgraph centered on a specific paper.
        
        Args:
            paper_id: ID of the center paper
            depth: How many relationship hops to include
            max_nodes: Maximum number of nodes to return
        
        Returns:
            Subgraph with nodes and edges
        """
        if not self.nodes or not self.edges:
            raise ValueError("Graph not built. Call build_graph() first.")
        
        # BFS to find connected nodes
        visited = set([paper_id])
        queue = [(paper_id, 0)]
        selected_nodes = set([paper_id])
        selected_edges = []
        
        while queue and len(selected_nodes) < max_nodes:
            current_id, current_depth = queue.pop(0)
            
            if current_depth >= depth:
                continue
            
            # Find edges connected to current node
            for edge in self.edges:
                source = edge.get('source')
                target = edge.get('target')
                
                if source == current_id and target not in visited:
                    visited.add(target)
                    selected_nodes.add(target)
                    selected_edges.append(edge)
                    queue.append((target, current_depth + 1))
                
                elif target == current_id and source not in visited:
                    visited.add(source)
                    selected_nodes.add(source)
                    selected_edges.append(edge)
                    queue.append((source, current_depth + 1))
        
        # Filter nodes and edges
        subgraph_nodes = [self.nodes[nid] for nid in selected_nodes if nid in self.nodes]
        subgraph_edges = selected_edges
        
        return {
            'nodes': subgraph_nodes,
            'edges': subgraph_edges,
            'center': paper_id,
            'depth': depth
        }
    
    def export_for_visualization(self, format: str = 'cytoscape') -> Dict[str, Any]:
        """
        Export graph in format suitable for visualization libraries.
        
        Formats:
        - 'cytoscape': Cytoscape.js format
        - 'd3': D3.js format
        - 'vis': vis.js format
        """
        if format == 'cytoscape':
            elements = {
                'nodes': [
                    {
                        'data': {
                            'id': node['id'],
                            'label': node['label'],
                            'type': node['type'],
                            **node.get('data', {})
                        }
                    }
                    for node in self.nodes.values()
                ],
                'edges': [
                    {
                        'data': {
                            'id': f"{edge['source']}-{edge['target']}",
                            'source': edge['source'],
                            'target': edge['target'],
                            'type': edge['type'],
                            'weight': edge.get('weight', 1.0)
                        }
                    }
                    for edge in self.edges
                ]
            }
            return elements
        
        elif format == 'd3':
            return {
                'nodes': list(self.nodes.values()),
                'links': [
                    {
                        'source': edge['source'],
                        'target': edge['target'],
                        'type': edge['type'],
                        'value': edge.get('weight', 1.0)
                    }
                    for edge in self.edges
                ]
            }
        
        else:
            raise ValueError(f"Unknown format: {format}")


def get_knowledge_map_service() -> KnowledgeMapService:
    """Get or create knowledge map service instance."""
    return KnowledgeMapService()

