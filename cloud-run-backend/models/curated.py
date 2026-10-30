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
