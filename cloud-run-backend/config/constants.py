"""Configuration constants for Copernicus Podcast API"""

import os
import xml.etree.ElementTree as ET
from typing import Optional

# Google Cloud Project Configuration
GCP_PROJECT_ID = "regal-scholar-453620-r7"
VERTEX_AI_REGION = "us-central1"
SECRET_ID = "vertex-ai-service-account-key"
SECRET_VERSION_ID = "latest"

# 2-SPEAKER VOICE CONFIGURATION
COPERNICUS_VOICES = {
    "matilda": {
        "voice_id": "XrExE9yKIg1WjnnlVkGX",
        "role": "host",
        "gender": "female",
        "description": "Professional host, warm and engaging interviewer"
    },
    "adam": {
        "voice_id": "pNInz6obpgDQGcFmaJgB",
        "role": "expert",
        "gender": "male",
        "description": "Expert researcher, authoritative but approachable"
    }
}

def get_speaker_labels():
    """Return the 2 speaker labels used in podcast scripts"""
    return ["MATILDA", "ADAM"]

# RSS Feed Configuration
RSS_BUCKET_NAME = os.getenv("GCP_AUDIO_BUCKET", "regal-scholar-453620-r7-podcast-storage")
RSS_FEED_BLOB_NAME = os.getenv("COPERNICUS_RSS_FEED_BLOB", "feeds/copernicus-mvp-rss-feed.xml")
EPISODE_BASE_URL = os.getenv("COPERNICUS_EPISODE_BASE_URL", "https://copernicusai.fyi/episodes")
DEFAULT_ARTWORK_URL = os.getenv(
    "COPERNICUS_DEFAULT_ARTWORK",
    "https://storage.googleapis.com/regal-scholar-453620-r7-podcast-storage/images/copernicus-original-portrait-optimized.jpg"
)

# Category Configuration
CATEGORY_SLUG_TO_LABEL = {
    "bio": "Biology",
    "chem": "Chemistry",
    "compsci": "Computer Science",
    "math": "Mathematics",
    "phys": "Physics",
}

EPISODE_COLLECTION_NAME = os.getenv("COPERNICUS_EPISODE_COLLECTION", "episodes")

# Notification Configuration
ERROR_NOTIFICATION_EMAIL = os.getenv("ERROR_NOTIFICATION_EMAIL", os.getenv("NOTIFICATION_EMAIL", "garywelz@gmail.com"))
DEFAULT_SUBSCRIBER_EMAIL = os.getenv("DEFAULT_SUBSCRIBER_EMAIL", "garywelz@gmail.com")

# RSS Namespaces
RSS_NAMESPACES = {
    "itunes": "http://www.itunes.com/dtds/podcast-1.0.dtd",
    "atom": "http://www.w3.org/2005/Atom",
    "podcast": "https://podcastindex.org/namespace/1.0",
    "content": "http://purl.org/rss/1.0/modules/content/",
    "media": "http://search.yahoo.com/mrss/",
}

# Register RSS namespaces
for prefix, uri in RSS_NAMESPACES.items():
    ET.register_namespace(prefix, uri)

# Legacy Description Taglines
LEGACY_DESCRIPTION_TAGLINES = {
    "Follow Copernicus AI for more cutting-edge science discussions and research explorations.",
    "**Follow Copernicus AI for more cutting-edge science discussions and research explorations.**",
}


def _category_value_to_slug(category_value: Optional[str]) -> Optional[str]:
    """Normalize category input (slug or label) to canonical slug."""
    if not category_value:
        return None
    normalized = category_value.strip().lower()
    for slug, label in CATEGORY_SLUG_TO_LABEL.items():
        if normalized == slug or normalized == label.lower():
            return slug
    return None


