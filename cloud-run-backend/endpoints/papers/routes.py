"""Research papers endpoints"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
import uuid
from datetime import datetime
import json

from utils.logging import structured_logger
from config.database import db

router = APIRouter()


# Models inferred from usage
class ResearchPaperPreprocessing(BaseModel):
    """Paper preprocessing result"""
    key_findings: List[str] = []
    llm_summary: str = ""
    entities_extracted: Dict[str, Any] = {}
    processed_by_model: Optional[str] = None
    processed_at: Optional[str] = None


class ResearchPaperModel(BaseModel):
    """Research paper model for storage"""
    paper_id: str
    doi: Optional[str] = None
    title: str
    authors: List[str] = []
    abstract: Optional[str] = None
    url: Optional[str] = None
    discipline: Optional[str] = None
    created_at: str
    updated_at: str
    preprocessing: Optional[ResearchPaperPreprocessing] = None


class PaperUploadRequest(BaseModel):
    """Request model for uploading a paper"""
    doi: Optional[str] = None
    title: Optional[str] = None
    authors: Optional[List[str]] = None
    abstract: Optional[str] = None
    url: Optional[str] = None
    discipline: Optional[str] = None
    preprocess: bool = False


class PaperQueryRequest(BaseModel):
    """Request model for querying papers"""
    discipline: Optional[str] = None
    keywords: Optional[List[str]] = None
    min_citation_count: Optional[int] = None
    limit: int = 100


# Helper function - will access from main
def _get_preprocess_helper():
    """Get preprocess_paper_with_llm function from main"""
    import sys
    main = sys.modules.get('main')
    if main:
        return getattr(main, 'preprocess_paper_with_llm', None)
    return None


@router.post("/api/papers/upload")
async def upload_research_paper(paper_request: PaperUploadRequest):
    """Upload and optionally preprocess a research paper"""
    if not db:
        raise HTTPException(status_code=503, detail="Firestore service is unavailable")
    
    try:
        # Generate paper ID
        paper_id = str(uuid.uuid4())
        
        # Create paper model
        paper = ResearchPaperModel(
            paper_id=paper_id,
            doi=paper_request.doi,
            title=paper_request.title or "Untitled",
            authors=paper_request.authors or [],
            abstract=paper_request.abstract,
            url=paper_request.url,
            discipline=paper_request.discipline,
            created_at=datetime.utcnow().isoformat(),
            updated_at=datetime.utcnow().isoformat()
        )
        
        # Preprocess if requested
        if paper_request.preprocess and paper.abstract:
            structured_logger.info("Preprocessing paper",
                                  paper_id=paper_id,
                                  paper_title=paper.title)
            preprocess_func = _get_preprocess_helper()
            if preprocess_func:
                paper.preprocessing = await preprocess_func(paper)
        
        # Store in Firestore
        db.collection('research_papers').document(paper_id).set(paper.dict())
        
        structured_logger.info("Paper uploaded",
                              paper_id=paper_id,
                              paper_title=paper.title)
        
        return {"paper_id": paper_id, "message": "Paper uploaded successfully", "paper": paper.dict()}
        
    except Exception as e:
        structured_logger.error("Error uploading paper",
                               paper_title=paper_request.title if paper_request else None,
                               error=str(e))
        raise HTTPException(status_code=500, detail=f"Failed to upload paper: {str(e)}")


@router.get("/api/papers/{paper_id}")
async def get_research_paper(paper_id: str):
    """Get a specific research paper by ID"""
    if not db:
        raise HTTPException(status_code=503, detail="Firestore service is unavailable")
    
    try:
        paper_doc = db.collection('research_papers').document(paper_id).get()
        if not paper_doc.exists:
            raise HTTPException(status_code=404, detail="Paper not found")
        
        return paper_doc.to_dict()
        
    except HTTPException:
        raise
    except Exception as e:
        structured_logger.error("Error fetching paper",
                               paper_id=paper_id,
                               error=str(e))
        raise HTTPException(status_code=500, detail="Failed to fetch paper")


@router.post("/api/papers/query")
async def query_research_papers(query: PaperQueryRequest):
    """Query research papers by discipline, keywords, etc."""
    if not db:
        raise HTTPException(status_code=503, detail="Firestore service is unavailable")
    
    try:
        # Build Firestore query
        papers_ref = db.collection('research_papers')
        
        # Apply filters
        if query.discipline:
            papers_ref = papers_ref.where('discipline', '==', query.discipline)
        
        if query.min_citation_count:
            papers_ref = papers_ref.where('citation_count', '>=', query.min_citation_count)
        
        # Limit results
        papers_ref = papers_ref.limit(query.limit)
        
        # Execute query
        papers = papers_ref.stream()
        results = []
        
        for paper in papers:
            paper_data = paper.to_dict()
            
            # Filter by keywords if provided
            if query.keywords:
                paper_keywords = set(paper_data.get('keywords', []))
                if not any(kw.lower() in ' '.join(paper_keywords).lower() for kw in query.keywords):
                    continue
            
            results.append(paper_data)
        
        return {"papers": results, "count": len(results)}
        
    except Exception as e:
        structured_logger.error("Error querying papers",
                               query_keywords=query.keywords if query else None,
                               error=str(e))
        raise HTTPException(status_code=500, detail="Failed to query papers")


@router.post("/api/papers/{paper_id}/link-podcast/{podcast_id}")
async def link_paper_to_podcast(paper_id: str, podcast_id: str):
    """Link a research paper to a podcast"""
    if not db:
        raise HTTPException(status_code=503, detail="Firestore service is unavailable")
    
    try:
        # Update paper's used_in_podcasts array
        paper_ref = db.collection('research_papers').document(paper_id)
        paper_doc = paper_ref.get()
        
        if not paper_doc.exists:
            raise HTTPException(status_code=404, detail="Paper not found")
        
        paper_data = paper_doc.to_dict()
        used_in_podcasts = paper_data.get('used_in_podcasts', [])
        
        if podcast_id not in used_in_podcasts:
            used_in_podcasts.append(podcast_id)
            paper_ref.update({
                'used_in_podcasts': used_in_podcasts,
                'citation_count': len(used_in_podcasts),
                'updated_at': datetime.utcnow().isoformat()
            })
        
        # Update podcast's metadata_extended.source_papers
        podcast_ref = db.collection('podcast_jobs').document(podcast_id)
        podcast_doc = podcast_ref.get()
        
        if podcast_doc.exists:
            podcast_data = podcast_doc.to_dict()
            metadata = podcast_data.get('metadata_extended', {})
            source_papers = metadata.get('source_papers', [])
            
            if paper_id not in source_papers:
                source_papers.append(paper_id)
                metadata['source_papers'] = source_papers
                podcast_ref.update({'metadata_extended': metadata})
        
        structured_logger.info("Linked paper to podcast",
                              paper_id=paper_id,
                              podcast_id=podcast_id)
        
        return {"message": "Paper linked to podcast successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        structured_logger.error("Error linking paper to podcast",
                               paper_id=paper_id,
                               podcast_id=podcast_id,
                               error=str(e))
        raise HTTPException(status_code=500, detail="Failed to link paper to podcast")

