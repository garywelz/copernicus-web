"""
Canonical Filename Service

Handles canonical filename generation and validation for podcasts.
Canonical filenames follow patterns:
- Feature (evergreen): ever-{category}-{YY}{NNNN}
  YY = last two digits of the creation year, NNNN = 1-based sequence in that
  category for that year (ever-bio-260001 is the first Biology evergreen of 2026).
- News: news-{category}-{YYYYMMDD}-{4-digit-serial} (YY + MMDD + serial; e.g., news-bio-20250328-0001)
"""

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
            except Exception as e:
                structured_logger.warning(
                    "Could not query Firestore for episode numbers",
                    error=str(e),
                )

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
                        
                        # Count existing files for this date/category
                        serial_number = len(existing_files) + 1
                        serial_str = str(serial_number).zfill(4)  # Pad to 4 digits (0001, 0002, etc.)
                        
                        canonical_filename = f"news-{request_category}-{date_str}-{serial_str}"
                        structured_logger.debug("Determined NEWS filename",
                                              filename=canonical_filename,
                                              category=request_category,
                                              date=date_str,
                                              serial=serial_str)
                    else:
                        # Fallback if GCS check fails
                        canonical_filename = f"news-{request_category}-{date_str}-0001"
                        structured_logger.debug("Determined NEWS filename (fallback)", filename=canonical_filename)
                except Exception as e:
                    structured_logger.warning("Could not check GCS for news serial numbering",
                                             error=str(e))
                    canonical_filename = f"news-{request_category}-{date_str}-0001"
                    structured_logger.debug("Determined NEWS filename (error fallback)", filename=canonical_filename)
            else:
                canonical_filename = next_evergreen_filename(
                    existing_names, request_category, datetime.now().year
                )
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
            # Fallback to timestamp-based naming
            timestamp = datetime.now().strftime("%y%m%d")
            return f"research-fallback-{timestamp}"
    
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

