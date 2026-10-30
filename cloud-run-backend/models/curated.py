"""Request models for curated source lists (admin only)."""

from typing import List, Optional

from pydantic import BaseModel, Field


class CreateSourceList(BaseModel):
    title: str = Field(..., min_length=1, max_length=200)
    topic: Optional[str] = Field(None, max_length=300)
    # The pinned commit of github.com/openai/math. Omitted: the design's default pin. Fixed when the list is created.
    pin_commit: Optional[str] = Field(None, max_length=40)


class AddSourceItems(BaseModel):
    items: List[str] = Field(..., min_length=1, max_length=40)


class OverrideItemClass(BaseModel):
    # "class" is a Python keyword, so the body field is named source_class
    source_class: str = Field(..., max_length=40)


class GenerateCuratedEpisode(BaseModel):
    list_id: str = Field(..., min_length=1, max_length=64)
    topic: Optional[str] = Field(None, max_length=300)       # default: the list's own topic, else its title
    category: str = Field("Mathematics", max_length=60)
    duration: str = Field("15-20 minutes", max_length=40)
    expertise_level: str = Field("intermediate", max_length=40)
    format_type: str = Field("interview", max_length=40)
    host_voice_id: Optional[str] = Field(None, max_length=64)
    expert_voice_id: Optional[str] = Field(None, max_length=64)


class AddCommentary(BaseModel):
    """Commentary the producer pasted (journalism, a blog, a statement). The text is private: it is stored apart from the list and never returned
    by any list route."""
    title: str = Field(..., min_length=1, max_length=300)
    outlet: str = Field(..., min_length=1, max_length=120)
    authors: List[str] = Field(default_factory=list, max_length=5)
    date: str = Field(..., max_length=10)
    url: Optional[str] = Field(None, max_length=500)
    text: str = Field(..., min_length=1, max_length=20000)
    fetch_refused: Optional[str] = Field(None, max_length=30)     # why the site could not be read automatically, if that is why the text is pasted
    approved_quotes: List[str] = Field(default_factory=list, max_length=5)


class SetCheckedBy(BaseModel):
    """Record that a cited commentary source says a manuscript was checked by experts, with the sentence that says so."""
    commentary_item_id: str = Field(..., min_length=1, max_length=64)
    quote: str = Field(..., min_length=20, max_length=400)
