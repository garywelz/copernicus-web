"""Podcast-related data models"""

from pydantic import BaseModel
from typing import Optional, List


class PodcastRequest(BaseModel):
    topic: str
    category: str = "Computer Science"  # Category from web form
    expertise_level: str = "intermediate"
    format_type: str = "interview"
    duration: str = "5-10 minutes"
    voice_style: str = "professional"
    # Voice selection (Phase 2.2)
    host_voice_id: Optional[str] = None  # Matilda (default)
    expert_voice_id: Optional[str] = None  # Adam (default)
    # Research paper processing fields
    paper_content: Optional[str] = None
    paper_title: Optional[str] = None
    paper_authors: Optional[List[str]] = None
    paper_abstract: Optional[str] = None
    paper_doi: Optional[str] = None
    paper_journal: Optional[str] = None
    paper_year: Optional[str] = None
    focus_areas: Optional[List[str]] = None
    include_citations: bool = True
    paradigm_shift_analysis: bool = True
    source_links: Optional[List[str]] = None
    additional_instructions: Optional[str] = None


class ResolvePaperRequest(BaseModel):
    """Preview/lookup step for the Knowledge Engine -> podcast connector.
    No side effects -- safe to call repeatedly while narrowing a query."""
    query: str
    cited_project: Optional[str] = None  # "glmp" or "atap"; None = unscoped
    limit: int = 60


class GeneratePodcastFromPaperRequest(BaseModel):
    """Generation step. Either `paper_id` (from a prior /resolve-paper call)
    or a `query` that resolves unambiguously as a DOI/PMID/arXiv identifier
    -- a free-text query here is rejected; call /resolve-paper first and
    pass the paper_id of whichever candidate was actually meant."""
    paper_id: Optional[str] = None
    query: Optional[str] = None
    cited_project: Optional[str] = None
    category: Optional[str] = None  # inferred from the paper when omitted
    expertise_level: str = "intermediate"
    format_type: str = "interview"
    duration: str = "5-10 minutes"
    voice_style: str = "professional"
    host_voice_id: Optional[str] = None
    expert_voice_id: Optional[str] = None
    focus_areas: Optional[List[str]] = None
    include_citations: bool = True
    paradigm_shift_analysis: bool = True
    additional_instructions: Optional[str] = None
    subscriber_id: Optional[str] = None  # defaults to admin gwelz@gc.cuny.edu

