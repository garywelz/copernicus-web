"""General helper functions for podcast operations"""

import re
from typing import Optional, Dict
from datetime import datetime
from email.utils import format_datetime, parsedate_to_datetime
from config.constants import (
    CATEGORY_SLUG_TO_LABEL,
    LEGACY_DESCRIPTION_TAGLINES,
    DEFAULT_ARTWORK_URL,
    EPISODE_BASE_URL
)


def _markdown_to_html(markdown_text: str) -> str:
    """Convert markdown to HTML (basic implementation)"""
    if not markdown_text:
        return ""
    
    html = markdown_text
    # Basic markdown conversions
    html = re.sub(r'\*\*(.*?)\*\*', r'<strong>\1</strong>', html)
    html = re.sub(r'\*(.*?)\*', r'<em>\1</em>', html)
    html = re.sub(r'\n\n', '</p><p>', html)
    html = re.sub(r'\n', '<br>', html)
    
    if not html.startswith('<p>'):
        html = f'<p>{html}'
    if not html.endswith('</p>'):
        html = f'{html}</p>'
    
    return html


def _extract_category_from_filename(canonical: Optional[str], request_category: Optional[str]) -> Dict[str, str]:
    """Extract category information from canonical filename or request."""
    if canonical:
        parts = canonical.split('-')
        if len(parts) >= 2:
            slug = parts[1]
            if slug in CATEGORY_SLUG_TO_LABEL:
                return {"slug": slug, "label": CATEGORY_SLUG_TO_LABEL[slug]}
    
    # Fallback to request category
    if request_category:
        normalized = request_category.strip().lower()
        for slug, label in CATEGORY_SLUG_TO_LABEL.items():
            if normalized == slug or normalized == label.lower():
                return {"slug": slug, "label": label}
    
    return {"slug": "compsci", "label": "Computer Science"}


def _parse_iso_datetime(value: Optional[str]) -> datetime:
    """Parse ISO format datetime string."""
    if not value:
        return datetime.utcnow()
    
    try:
        if isinstance(value, datetime):
            return value
        if 'T' in str(value):
            return datetime.fromisoformat(str(value).replace('Z', '+00:00')[:19])
        return datetime.utcnow()
    except Exception:
        return datetime.utcnow()


def _format_duration(duration_str: Optional[str]) -> str:
    """Format duration string for RSS feed."""
    if not duration_str:
        return "00:00:00"
    
    # If already in HH:MM:SS format, return as-is
    if re.match(r'^\d{2}:\d{2}:\d{2}$', duration_str):
        return duration_str
    
    # Try to parse other formats
    return duration_str


def _extract_blob_name_from_url(url: str) -> Optional[str]:
    """Extract blob name from GCS URL."""
    if not url:
        return None
    
    try:
        parsed = urlparse(url)
        path = parsed.path.lstrip('/')
        # Remove bucket name if present
        if '/' in path:
            return path.split('/', 1)[1]
        return path
    except Exception:
        return None


def _strip_legacy_tagline(markdown_text: Optional[str]) -> str:
    """Remove legacy taglines from markdown text."""
    if not markdown_text:
        return ""
    
    cleaned_lines = []
    for line in markdown_text.splitlines():
        if line.strip() in LEGACY_DESCRIPTION_TAGLINES:
            continue
        cleaned_lines.append(line)
    cleaned = "\n".join(cleaned_lines).strip()
    while "\n\n\n" in cleaned:
        cleaned = cleaned.replace("\n\n\n", "\n\n")
    return cleaned

