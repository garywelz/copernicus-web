"""
Research Paper Processor for Google Gemini Integration
Adapted from copernicus_backup/src/services/paperProcessor.ts
"""

import json
import time
import hashlib
from typing import Dict, Any, Optional, List
from dataclasses import dataclass
from datetime import datetime, timedelta
import google.generativeai as genai
import os

# Cache duration in seconds (24 hours)
CACHE_DURATION = 24 * 60 * 60

# Global cache for analysis results
analysis_cache: Dict[str, Dict[str, Any]] = {}

@dataclass
class ResearchPaper:
    """Research paper data structure"""
    title: str
    authors: List[str]
    content: str
    abstract: Optional[str] = None
    doi: Optional[str] = None
    publication_date: Optional[str] = None
    journal: Optional[str] = None
    keywords: Optional[List[str]] = None

@dataclass
class AnalyzeOptions:
    """Analysis options for paper processing"""
    focus_areas: List[str]
    analysis_depth: str = "comprehensive"  # basic, detailed, comprehensive
    include_citations: bool = True
    paradigm_shift_analysis: bool = True
    interdisciplinary_connections: bool = True

@dataclass
class PaperAnalysis:
    """Analysis result structure"""
    summary: str
    key_findings: List[str]
    paradigm_shifts: List[str]
    interdisciplinary_connections: List[str]
    implications: List[str]
    citations: List[str]
    methodology_analysis: str
    future_research_directions: List[str]
    confidence_score: float

def validate_paper(paper: ResearchPaper) -> None:
    """Validates a research paper object"""
    if not paper.title or not isinstance(paper.title, str):
        raise ValueError("Paper must have a valid title")
    if not paper.authors or not isinstance(paper.authors, list) or len(paper.authors) == 0:
        raise ValueError("Paper must have at least one author")
    if not paper.content or not isinstance(paper.content, str):
        raise ValueError("Paper must have content")

def generate_cache_key(paper: ResearchPaper, options: AnalyzeOptions) -> str:
    """Generates a cache key for a paper and options combination"""
    key_data = f"{paper.title}-{json.dumps(options.__dict__, sort_keys=True)}"
    return hashlib.md5(key_data.encode()).hexdigest()

def is_cache_valid(cache_entry: Dict[str, Any]) -> bool:
    """Checks if a cached analysis is still valid"""
    return time.time() - cache_entry["timestamp"] < CACHE_DURATION

def cleanup_cache() -> None:
    """Clears expired entries from the analysis cache"""
    current_time = time.time()
    expired_keys = [
        key for key, entry in analysis_cache.items()
        if current_time - entry["timestamp"] >= CACHE_DURATION
    ]
    for key in expired_keys:
        del analysis_cache[key]
    print(f"🧹 Cleaned up {len(expired_keys)} expired cache entries")

async def analyze_paper_with_gemini(paper: ResearchPaper, options: AnalyzeOptions, api_key: str) -> PaperAnalysis:
    """Analyze research paper using Google Gemini"""
    
    # Configure Gemini
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel('gemini-pro')
    
    # Create comprehensive analysis prompt
    prompt = f"""
You are Copernicus, a scientific knowledge curator who specializes in identifying paradigm-shifting research across all fields. 

Analyze this research paper with a focus on revolutionary 'delta' thinking that challenges conventional understanding:

**Paper Title:** {paper.title}
**Authors:** {', '.join(paper.authors)}
**Abstract:** {paper.abstract or 'Not provided'}
**Content:** {paper.content[:8000]}  # Limit content for API

**Analysis Focus Areas:** {', '.join(options.focus_areas)}

Please provide a comprehensive analysis in the following JSON format:

{{
    "summary": "Concise summary highlighting the revolutionary aspects",
    "key_findings": ["List of 3-5 most significant findings"],
    "paradigm_shifts": ["Identify paradigm-shifting implications"],
    "interdisciplinary_connections": ["Connections to other scientific fields"],
    "implications": ["Broader implications for science and society"],
    "citations": ["Properly formatted academic citations with DOIs where possible"],
    "methodology_analysis": "Analysis of research methodology and its innovations",
    "future_research_directions": ["Suggested future research directions"],
    "confidence_score": 0.85
}}

Focus on:
1. Revolutionary changes in scientific understanding
2. Interdisciplinary connections and implications  
3. Evidence-based speculation about future developments
4. Practical applications of breakthrough discoveries
5. How this research challenges existing paradigms

Maintain academic rigor while highlighting transformative potential.
"""

    try:
        print(f"🔄 Analyzing paper with Google Gemini: {paper.title[:50]}...")
        
        response = model.generate_content(prompt)
        
        if not response.text:
            raise Exception("Empty response from Gemini")
            
        # Parse JSON response
        try:
            analysis_data = json.loads(response.text)
        except json.JSONDecodeError:
            # If JSON parsing fails, create structured response from text
            analysis_data = {
                "summary": response.text[:500],
                "key_findings": ["Analysis generated but not in expected JSON format"],
                "paradigm_shifts": ["See full analysis in summary"],
                "interdisciplinary_connections": [],
                "implications": [],
                "citations": [],
                "methodology_analysis": "See summary for methodology analysis",
                "future_research_directions": [],
                "confidence_score": 0.7
            }
        
        # Create PaperAnalysis object
        analysis = PaperAnalysis(
            summary=analysis_data.get("summary", ""),
            key_findings=analysis_data.get("key_findings", []),
            paradigm_shifts=analysis_data.get("paradigm_shifts", []),
            interdisciplinary_connections=analysis_data.get("interdisciplinary_connections", []),
            implications=analysis_data.get("implications", []),
            citations=analysis_data.get("citations", []),
            methodology_analysis=analysis_data.get("methodology_analysis", ""),
            future_research_directions=analysis_data.get("future_research_directions", []),
            confidence_score=analysis_data.get("confidence_score", 0.8)
        )
        
        print(f"✅ Paper analysis completed with confidence: {analysis.confidence_score}")
        return analysis
        
    except Exception as e:
        print(f"❌ Error analyzing paper with Gemini: {e}")
        raise Exception(f"Paper analysis failed: {str(e)}")

async def process_paper(paper: ResearchPaper, options: AnalyzeOptions, api_key: str) -> PaperAnalysis:
    """
    Main paper processing function with caching
    Adapted from copernicus_backup paperProcessor.ts
    """
    try:
        # Validate input
        validate_paper(paper)
        
        # Check cache first
        cache_key = generate_cache_key(paper, options)
        cached_result = analysis_cache.get(cache_key)
        
        if cached_result and is_cache_valid(cached_result):
            print("📋 Using cached analysis")
            return PaperAnalysis(**cached_result["analysis"])
        
        # Clean up expired cache entries
        cleanup_cache()
        
        # Perform new analysis
        print("🔬 Starting new paper analysis with Google Gemini")
        analysis = await analyze_paper_with_gemini(paper, options, api_key)
        
        # Cache the result
        analysis_cache[cache_key] = {
            "analysis": analysis.__dict__,
            "timestamp": time.time()
        }
        
        print("💾 Analysis cached successfully")
        return analysis
        
    except Exception as e:
        print(f"❌ Error processing paper: {e}")
        raise Exception(f"Paper processing failed: {str(e)}")

def format_citation(paper: ResearchPaper, style: str = "APA") -> str:
    """Format citation for the research paper"""
    if style.upper() == "APA":
        authors_str = ", ".join(paper.authors[:3])  # Limit to first 3 authors
        if len(paper.authors) > 3:
            authors_str += " et al."
        
        year = paper.publication_date[:4] if paper.publication_date else "n.d."
        
        citation = f"{authors_str} ({year}). {paper.title}."
        
        if paper.journal:
            citation += f" {paper.journal}."
        
        if paper.doi:
            citation += f" https://doi.org/{paper.doi}"
        
        return citation
    
    # Default to simple format
    return f"{', '.join(paper.authors)} - {paper.title}"

# Initialize cache cleanup (run periodically in production)
def start_cache_cleanup():
    """Start periodic cache cleanup - call this in production"""
    import threading
    import time
    
    def cleanup_worker():
        while True:
            time.sleep(CACHE_DURATION)
            cleanup_cache()
    
    cleanup_thread = threading.Thread(target=cleanup_worker, daemon=True)
    cleanup_thread.start()
    print("🧹 Started cache cleanup worker")
