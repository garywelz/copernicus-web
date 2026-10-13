"""
Canonical Filename Service

Handles canonical filename generation and validation for podcasts.
Canonical filenames follow patterns:
- Feature (evergreen): ever-{category}-{YY}{NNNN}
  YY = last two digits of the creation year, NNNN = 1-based sequence in that
  category for that year (ever-bio-260001 is the first Biology evergreen of 2026).
- News: news-{category}-{YYYYMMDD}-{4-digit-serial} (YY + MMDD + serial; e.g., news-bio-20250328-0001)
"""

import asyncio
import re
import os
from typing import Optional, List, Tuple
from datetime import datetime

from utils.logging import structured_logger
from config.database import db
from config.constants import GCP_PROJECT_ID


EVERGREEN_CATEGORIES = {"bio", "chem", "compsci", "math", "phys", "eng", "med", "psych"}

CATEGORY_TO_SLUG = {
    "Physics": "phys",
    "Computer Science": "compsci",
    "Biology": "bio",
    "Chemistry": "chem",
    "Mathematics": "math",
    "Engineering": "eng",
    "Medicine": "med",
    "Psychology": "psych",
}

EVERGREEN_NAME_RE = re.compile(
    r"^ever-(bio|chem|compsci|math|phys|eng|med|psych)-(\d{2})(\d{4})$"
)


def category_to_slug(category: Optional[str]) -> str:
    if category and category in CATEGORY_TO_SLUG:
        return CATEGORY_TO_SLUG[category]
    text = str(category or "")
    if "Physics" in text:
        return "phys"
    if "Computer Science" in text:
        return "compsci"
    if "Biology" in text:
        return "bio"
    if "Chemistry" in text:
        return "chem"
    if "Mathematics" in text:
        return "math"
    lowered = text.strip().lower()
    if lowered in EVERGREEN_CATEGORIES:
        return lowered
    return "phys"


def evergreen_year_yy(now: Optional[datetime] = None) -> str:
    return f"{(now or datetime.now()).year % 100:02d}"


def parse_evergreen_filename(filename: Optional[str]) -> Optional[Tuple[str, str, int]]:
    """Parse ever-{cat}-{YY}{NNNN}. Returns (category, yy, sequence) or None."""
    if not filename:
        return None
    name = filename.split("/")[-1].replace(".mp3", "").strip()
    m = EVERGREEN_NAME_RE.match(name)
    if not m:
        return None
    return m.group(1), m.group(2), int(m.group(3))


def highest_evergreen_sequence(existing_names: List[str], category_slug: str, yy: str) -> int:
    top = 0
    for name in existing_names:
        parsed = parse_evergreen_filename(name)
        if parsed and parsed[0] == category_slug and parsed[1] == yy:
            top = max(top, parsed[2])
    return top


def next_evergreen_filename(
    existing_names: List[str],
    category_slug: str,
    year: Optional[int] = None,
) -> str:
    """Next ever-{cat}-{YY}{NNNN} for this category in `year`.

    Names from other years (e.g. ever-bio-250045 in 2026) are ignored, so a
    2026 Biology episode is 260001 even if 2025-style numbers already exist.
    """
    yy = f"{(year if year is not None else datetime.now().year) % 100:02d}"
    max_seq = 0
    for name in existing_names:
        parsed = parse_evergreen_filename(name)
        if not parsed:
            continue
        cat, file_yy, seq = parsed
        if cat == category_slug and file_yy == yy:
            max_seq = max(max_seq, seq)
    return f"ever-{category_slug}-{yy}{max_seq + 1:04d}"


COUNTER_COLLECTION = "canonical_counters"


class CanonicalAllocationError(Exception):
    """No episode ID could be reserved. The episode must fail rather than take a guessed or reused name."""


def counter_key(kind: str, category_slug: str, period: str) -> str:
    """'ever-math-26' for evergreen episodes of 2026, 'news-bio-20260101' for news of one day."""
    return f"{kind}-{category_slug}-{period}"


def reserve_sequence(database, key: str, floor: int) -> int:
    """Atomically hand out the next number for `key` and remember it. The stored counter only ever goes up, so a number
    that was issued once (even to an episode that was later deleted) is never issued again. `floor` is the highest number
    seen among live episodes and files; it only matters when the counter is missing or behind (first use, or a restore)."""
    from google.cloud import firestore

    ref = database.collection(COUNTER_COLLECTION).document(key)

    @firestore.transactional
    def take(transaction):
        snap = ref.get(transaction=transaction)
        last = int((snap.to_dict() or {}).get("last_seq") or 0) if snap.exists else 0
        seq = max(last, floor) + 1
        transaction.set(ref, {"last_seq": seq, "updated_at": datetime.utcnow().isoformat() + "Z"}, merge=True)
        return seq

    return take(database.transaction())


class CanonicalService:
    """Service for generating and validating canonical filenames"""
    
    def __init__(self):
        self.gcs_bucket = "regal-scholar-453620-r7-podcast-storage"
    
    async def determine_canonical_filename(
        self, 
        topic: str, 
        title: str, 
        category: str = None, 
        format_type: str = "feature"
    ) -> str:
        """Determine canonical filename based on topic category, format type, and next available episode number"""
        
        # Debug: Log the input parameters
        structured_logger.debug("determine_canonical_filename called",
                               topic=topic,
                               title=title,
                               category=category,
                               format_type=format_type)
        
        try:
            import requests

            request_category = category_to_slug(category)
            year_yy = evergreen_year_yy()

            existing_names: List[str] = []
            try:
                if not db:
                    raise CanonicalAllocationError("Firestore is not available, so no episode ID can be reserved")
                if db:
                    for collection_name in ("podcast_jobs", "episodes"):
                        for doc in db.collection(collection_name).stream():
                            data = doc.to_dict() or {}
                            result = data.get("result") or {}
                            for candidate in (
                                result.get("canonical_filename"),
                                data.get("canonical_filename"),
                                (result.get("audio_url") or "").split("/")[-1],
                            ):
                                if candidate:
                                    existing_names.append(str(candidate))
                structured_logger.debug(
                    "Collected existing canonical names",
                    count=len(existing_names),
                    category=request_category,
                    year_yy=year_yy,
                )
            except CanonicalAllocationError:
                raise
            except Exception as e:
                # Fail closed: an ID chosen without knowing what exists could repeat one that was used.
                raise CanonicalAllocationError(f"Could not read existing episodes to reserve an ID: {type(e).__name__}") from e

            try:
                gcs_list_url = (
                    f"https://storage.googleapis.com/storage/v1/b/{self.gcs_bucket}/o"
                    f"?prefix=audio/ever-{request_category}-{year_yy}"
                )
                gcs_response = requests.get(gcs_list_url, timeout=10)
                if gcs_response.status_code == 200:
                    for item in gcs_response.json().get("items") or []:
                        name = (item.get("name") or "").split("/")[-1]
                        if name:
                            existing_names.append(name)
            except Exception as e:
                structured_logger.warning(
                    "Could not list GCS for evergreen episode numbers",
                    error=str(e),
                )
            
            # Generate filename based on format type
            if format_type == "news":
                # News format: news-{category}-{date}-{serial_number}
                date_str = datetime.now().strftime("%Y%m%d")
                
                # Check for existing news files with same date and category to determine serial number
                try:
                    gcs_list_url = f"https://storage.googleapis.com/storage/v1/b/{self.gcs_bucket}/o?prefix=audio/news-{request_category}-{date_str}"
                    gcs_response = requests.get(gcs_list_url, timeout=10)
                    if gcs_response.status_code == 200:
                        gcs_data = gcs_response.json()
                        existing_files = gcs_data.get('items', [])
                        
                        # Highest serial seen (by count or by name), then the stored counter, which never goes down
                        seen = [int(n.rsplit("-", 1)[-1].split(".")[0]) for n in
                                [(i.get("name") or "").split("/")[-1] for i in existing_files]
                                if n.rsplit("-", 1)[-1].split(".")[0].isdigit()]
                        floor = max([len(existing_files)] + seen)
                        serial_number = await asyncio.to_thread(
                            reserve_sequence, db, counter_key("news", request_category, date_str), floor)
                        serial_str = str(serial_number).zfill(4)  # Pad to 4 digits (0001, 0002, etc.)
                        
                        canonical_filename = f"news-{request_category}-{date_str}-{serial_str}"
                        structured_logger.debug("Determined NEWS filename",
                                              filename=canonical_filename,
                                              category=request_category,
                                              date=date_str,
                                              serial=serial_str)
                    else:
                        # GCS list unavailable: the stored counter alone still never repeats a serial
                        serial_number = await asyncio.to_thread(
                            reserve_sequence, db, counter_key("news", request_category, date_str), 0)
                        canonical_filename = f"news-{request_category}-{date_str}-{str(serial_number).zfill(4)}"
                        structured_logger.debug("Determined NEWS filename (GCS list unavailable)", filename=canonical_filename)
                except CanonicalAllocationError:
                    raise
                except Exception as e:
                    raise CanonicalAllocationError(f"Could not reserve a news serial: {type(e).__name__}") from e
            else:
                floor = highest_evergreen_sequence(existing_names, request_category, year_yy)
                seq = await asyncio.to_thread(
                    reserve_sequence, db, counter_key("ever", request_category, year_yy), floor)
                canonical_filename = f"ever-{request_category}-{year_yy}{seq:04d}"
                structured_logger.debug(
                    "Determined FEATURE filename",
                    filename=canonical_filename,
                    category=request_category,
                    year_yy=year_yy,
                )
            
            return canonical_filename
            
        except Exception as e:
            structured_logger.error("Error determining canonical filename",
                                   error=str(e),
                                   topic=topic,
                                   title=title,
                                   category=category)
            # No guessed name: a timestamp name repeats within a day. The episode fails instead.
            if isinstance(e, CanonicalAllocationError):
                raise
            raise CanonicalAllocationError(f"Could not determine an episode ID: {type(e).__name__}: {e}") from e
    
    def is_canonical_filename(self, filename: str) -> bool:
        """Check if a filename follows canonical naming conventions"""
        if not filename:
            return False
        
        # Pattern for feature format: ever-{category}-{6 digits}
        feature_pattern = re.compile(r'^ever-(bio|chem|compsci|math|phys|eng|med|psych)-\d{6}$')
        
        # Pattern for news format: news-{category}-{8 digits}-{4 digits}
        news_pattern = re.compile(r'^news-(bio|chem|compsci|math|phys|eng|med|psych)-\d{8}-\d{4}$')
        
        return bool(feature_pattern.match(filename) or news_pattern.match(filename))
    
    def extract_category_from_canonical(self, canonical: str) -> Optional[str]:
        """Extract category slug from canonical filename"""
        if not canonical:
            return None
        
        parts = canonical.split('-')
        if len(parts) >= 2:
            return parts[1]
        return None


# Create singleton instance
canonical_service = CanonicalService()

