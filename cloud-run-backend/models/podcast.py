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
    focus_areas: Optional[List[str]] = None
    include_citations: bool = True
    paradigm_shift_analysis: bool = True
    source_links: Optional[List[str]] = None
    additional_instructions: Optional[str] = None

