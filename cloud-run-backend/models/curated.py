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


class AddCompanyRelease(BaseModel):
    """A company release at a stable https address (a PDF or a page) that is not in github.com/openai/math. The address is fetched, the title and the
    company's name must occur in what is fetched, and the item is pinned by the SHA-256 of the bytes (design: curated_web_release)."""
    url: str = Field(..., min_length=10, max_length=500)
    title: str = Field(..., min_length=1, max_length=300)
    company: str = Field(..., min_length=1, max_length=60)
    date: str = Field(..., max_length=10)
    authors: List[str] = Field(default_factory=list, max_length=5)


class AddPaperWithSuppliedAbstract(BaseModel):
    """A peer-reviewed paper whose Crossref record has no abstract: its DOI, the paper's own published abstract as copied from the publisher's page,
    and that page's https address. Stored with its SHA-256 and labelled "abstract supplied by the producer"."""
    doi: str = Field(..., min_length=7, max_length=200)
    abstract: str = Field(..., min_length=1, max_length=6000)
    abstract_url: str = Field(..., min_length=10, max_length=500)


class AddPaperWithPassage(BaseModel):
    """A peer-reviewed journal article whose Crossref record has no abstract and that was printed without one: its DOI and a passage the
    producer transcribed from the article, which must contain the article's title. The passage is private: it is stored apart from the list
    and never returned by any list route; the item is labelled "passage transcribed by the producer"."""
    doi: str = Field(..., min_length=7, max_length=200)
    passage: str = Field(..., min_length=1, max_length=40000)
    source_note: Optional[str] = Field(None, max_length=300)        # where the passage came from: pages, the copy read


class AttachPassage(BaseModel):
    """A passage the producer transcribed from an item that already has its abstract (a preprint, a journal article with a registry
    abstract), which must contain the item's title. Private, like every transcribed passage; the item keeps its class and abstract."""
    passage: str = Field(..., min_length=1, max_length=40000)
    source_note: Optional[str] = Field(None, max_length=300)


class OverrideItemClass(BaseModel):
    # "class" is a Python keyword, so the body field is named source_class
    source_class: str = Field(..., max_length=40)


class GenerateCuratedEpisode(BaseModel):
    list_id: str = Field(..., min_length=1, max_length=64)
    topic: Optional[str] = Field(None, max_length=300)       # default: the list's own topic, else its title
    title: Optional[str] = Field(None, max_length=200)       # the producer's own episode title; otherwise the model writes one
    category: str = Field("Mathematics", max_length=60)
    duration: str = Field("15-20 minutes", max_length=40)
    expertise_level: str = Field("intermediate", max_length=40)
    format_type: str = Field("interview", max_length=40)
    host_voice_id: Optional[str] = Field(None, max_length=64)
    expert_voice_id: Optional[str] = Field(None, max_length=64)
    thumbnail_title: Optional[str] = Field(None, max_length=120)       # what the series thumbnail draws instead of the title (whole, no colon split); optional
    thumbnail_subtitle: Optional[str] = Field(None, max_length=160)


class CheckSuppliedScript(BaseModel):
    """An episode script written by an editor, to be checked exactly as a generated one and, only if every check passes and `generate` is true,
    voiced into a private episode."""
    list_id: str = Field(..., min_length=1, max_length=64)
    script: str = Field(..., min_length=1, max_length=40000)       # HOST:/EXPERT: lines
    title: str = Field(..., min_length=1, max_length=200)
    topic: Optional[str] = Field(None, max_length=300)
    category: str = Field("Mathematics", max_length=60)
    duration: str = Field("15-20 minutes", max_length=40)
    expertise_level: str = Field("intermediate", max_length=40)
    format_type: str = Field("interview", max_length=40)
    host_voice_id: Optional[str] = Field(None, max_length=64)
    expert_voice_id: Optional[str] = Field(None, max_length=64)
    thumbnail_title: Optional[str] = Field(None, max_length=120)       # what the series thumbnail draws instead of the title (whole, no colon split); optional
    thumbnail_subtitle: Optional[str] = Field(None, max_length=160)
    generate: bool = False


class AttachReleaseText(BaseModel):
    """More of a company release's OWN text, attached to that release's item: the manuscript's statement of its result, its introduction, or
    the summary of its reasoning trace, copied from the pinned commit. It is not a separate source and has no title of its own, so the naming
    check cannot tie two items against one mention, and attaching it does not make the list hold commentary."""
    text: str = Field(..., min_length=1, max_length=20000)
    source_path: str = Field(..., min_length=1, max_length=400)      # the path inside the pinned repository the text was copied from
    note: Optional[str] = Field(None, max_length=200)                # what the passage is ("statement of the main result")


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


class AddScholarlyChapter(BaseModel):
    """A chapter in a scholarly book, identified by something that will still resolve years from now and evidenced by the passage the
    producer transcribed. The passage is private: it is stored apart from the list and never returned by any list route."""
    identifier: str = Field(..., min_length=1, max_length=500)      # a JSTOR stable address, a handle, or isbn:<number>
    title: str = Field(..., min_length=1, max_length=300)           # the chapter's title, which must occur in the passage
    excerpt: str = Field(..., min_length=1, max_length=40000)
    book_title: Optional[str] = Field(None, max_length=300)
    authors: Optional[str] = Field(None, max_length=300)
    year: Optional[str] = Field(None, max_length=10)
    source_note: Optional[str] = Field(None, max_length=300)        # where the passage came from: edition, pages


class SetCheckedBy(BaseModel):
    """Record that a cited commentary source says a manuscript was checked by experts, with the sentence that says so."""
    commentary_item_id: str = Field(..., min_length=1, max_length=64)
    quote: str = Field(..., min_length=20, max_length=400)
