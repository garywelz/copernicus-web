"""
Canonical Filename Service

Handles canonical filename generation and validation for podcasts.
Canonical filenames follow patterns:
- Feature format: ever-{category}-{6-digit-number} (e.g., ever-bio-250032)
- News format: news-{category}-{YYYYMMDD}-{4-digit-serial} (e.g., news-bio-20250328-0001)
"""

import re
import os
from typing import Optional
from datetime import datetime

from utils.logging import structured_logger
from config.database import db
from config.constants import GCP_PROJECT_ID


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
            
            # Query Firestore for highest episode numbers by category to avoid overwrites
            category_episodes = {
                "bio": 250007,       # Start from current max
                "chem": 0, 
                "compsci": 0,
                "math": 0,
                "phys": 0
            }
            
            try:
                # Query all completed podcasts from Firestore
                if db:
                    podcasts_ref = db.collection('podcast_jobs').where('status', '==', 'completed').stream()
                    
                    for podcast_doc in podcasts_ref:
                        podcast_data = podcast_doc.to_dict()
                        result = podcast_data.get('result', {})
                        audio_url = result.get('audio_url', '')
                        
                        # Extract filename from audio URL
                        if 'ever-' in audio_url:
                            filename = audio_url.split('/')[-1].replace('.mp3', '')
                            parts = filename.split('-')
                            if len(parts) >= 3:
                                cat = parts[1]
                                try:
                                    episode_num = int(parts[2])
                                    if cat in category_episodes:
                                        category_episodes[cat] = max(category_episodes[cat], episode_num)
                                except ValueError:
                                    continue
                
                structured_logger.debug("Current max episodes by category",
                                       category_episodes=category_episodes)
                
            except Exception as e:
                structured_logger.warning("Could not query Firestore for episode numbers, using defaults",
                                         error=str(e))
            
            # Use the category from the request instead of re-classifying
            # Map the request category to the canonical format
            category_mapping = {
                "Physics": "phys",
                "Computer Science": "compsci", 
                "Biology": "bio",
                "Chemistry": "chem",
                "Mathematics": "math",
                "Engineering": "eng",
                "Medicine": "med",
                "Psychology": "psych"
            }
            
            # Use the category from the request directly
            if category and category in category_mapping:
                request_category = category_mapping[category]
            else:
                # Direct mapping from common categories
                if "Physics" in str(category):
                    request_category = "phys"
                elif "Computer Science" in str(category):
                    request_category = "compsci"
                elif "Biology" in str(category):
                    request_category = "bio"
                elif "Chemistry" in str(category):
                    request_category = "chem"
                elif "Mathematics" in str(category):
                    request_category = "math"
                else:
                    request_category = "phys"  # Default to physics
            
            # Get the next episode number for this category
            next_episode = category_episodes[request_category] + 1
            next_episode_str = str(next_episode).zfill(6)  # Pad to 6 digits like 250032
            
            # Double-check we're not overwriting by checking GCS directly
            try:
                gcs_list_url = f"https://storage.googleapis.com/storage/v1/b/{self.gcs_bucket}/o?prefix=audio/ever-{request_category}-{next_episode_str}"
                gcs_response = requests.get(gcs_list_url, timeout=10)
                if gcs_response.status_code == 200:
                    gcs_data = gcs_response.json()
                    if gcs_data.get('items'):
                        # File already exists, increment further
                        next_episode += 1
                        next_episode_str = str(next_episode).zfill(6)
                        structured_logger.debug("File already exists, incrementing episode number",
                                               category=request_category,
                                               new_episode=next_episode_str)
            except Exception as e:
                structured_logger.warning("Could not verify GCS for episode number",
                                         episode_str=next_episode_str,
                                         error=str(e))
            
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
                # Feature format: ever-{category}-{episode}
                canonical_filename = f"ever-{request_category}-{next_episode_str}"
                structured_logger.debug("Determined FEATURE filename",
                                      filename=canonical_filename,
                                      category=request_category,
                                      episode=next_episode)
            
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

