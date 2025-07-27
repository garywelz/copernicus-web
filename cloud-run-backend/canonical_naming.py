"""
Canonical Naming Service for Copernicus AI Podcast Platform
Handles canonical filename generation, numbering, and GCS integration
"""

import csv
import io
from typing import Dict, Tuple, Optional
from datetime import datetime
from google.cloud import storage
import re

class CanonicalNamingService:
    """Service for managing canonical podcast naming and numbering"""
    
    def __init__(self):
        self.bucket_name = "regal-scholar-453620-r7-podcast-storage"
        self.canonical_csv_path = "canonical/Copernicus AI Canonical List 071825.csv"
        self.storage_client = storage.Client()
        self.bucket = self.storage_client.bucket(self.bucket_name)
        
        # Category mapping for canonical naming
        self.category_mapping = {
            "biology": "bio",
            "chemistry": "chem", 
            "computer-science": "compsci",
            "mathematics": "math",
            "physics": "phys"
        }
        
        # Category display names
        self.category_display = {
            "biology": "Biology",
            "chemistry": "Chemistry",
            "computer-science": "Computer Science", 
            "mathematics": "Mathematics",
            "physics": "Physics"
        }
    
    async def get_next_canonical_number(self, category: str) -> int:
        """Get the next available canonical number for a category"""
        try:
            # Download current canonical CSV from GCS
            blob = self.bucket.blob(self.canonical_csv_path)
            csv_content = blob.download_as_text()
            
            # Parse CSV to find highest number for category
            csv_reader = csv.DictReader(io.StringIO(csv_content))
            highest_number = 0
            
            category_prefix = self.category_mapping.get(category, category)
            pattern = f"ever-{category_prefix}-(\d+)"
            
            for row in csv_reader:
                filename = row.get("File Name", "").strip('"')
                match = re.match(pattern, filename)
                if match:
                    number = int(match.group(1))
                    highest_number = max(highest_number, number)
            
            return highest_number + 1
            
        except Exception as e:
            print(f"Error getting next canonical number: {e}")
            # Fallback: use timestamp-based number
            return int(datetime.now().strftime("%y%m%d"))
    
    async def generate_canonical_filename(self, category: str, title: str) -> Tuple[str, int]:
        """Generate canonical filename for a podcast"""
        category_abbrev = self.category_mapping.get(category, category)
        next_number = await self.get_next_canonical_number(category)
        canonical_filename = f"ever-{category_abbrev}-{next_number:06d}"
        
        print(f"🏷️ Generated canonical filename: {canonical_filename} for category: {category}")
        return canonical_filename, next_number
    
    def get_asset_urls(self, canonical_filename: str) -> Dict[str, str]:
        """Generate all asset URLs for a canonical filename"""
        base_url = f"https://storage.googleapis.com/{self.bucket_name}"
        
        return {
            "audio_url": f"{base_url}/audio/{canonical_filename}.mp3",
            "thumbnail_url": f"{base_url}/thumbnails/{canonical_filename}-thumb.jpg", 
            "description_url": f"{base_url}/descriptions/{canonical_filename}.md"
        }
    
    async def add_to_canonical_list(self, canonical_filename: str, title: str, 
                                  duration: str, file_size: int, category: str) -> bool:
        """Add new episode to canonical list in GCS"""
        try:
            # Download current CSV
            blob = self.bucket.blob(self.canonical_csv_path)
            csv_content = blob.download_as_text()
            
            # Parse existing CSV
            lines = csv_content.strip().split('\n')
            header = lines[0]
            rows = lines[1:]
            
            # Find next episode number
            max_episode = 0
            for row in rows:
                if row.strip():
                    parts = row.split(',')
                    if len(parts) >= 6:
                        try:
                            episode_num = int(parts[5])
                            max_episode = max(max_episode, episode_num)
                        except:
                            pass
            
            next_episode = max_episode + 1
            
            # Create new row
            new_row = f'"{canonical_filename}","{title}","{duration}","{file_size}",1,{next_episode}'
            
            # Add to CSV
            updated_csv = header + '\n' + '\n'.join(rows) + '\n' + new_row
            
            # Upload updated CSV back to GCS
            blob.upload_from_string(updated_csv, content_type='text/csv')
            
            print(f"✅ Added {canonical_filename} to canonical list as episode {next_episode}")
            return True
            
        except Exception as e:
            print(f"❌ Error adding to canonical list: {e}")
            return False
    
    def format_description_with_citations(self, description: str, citations: list = None, 
                                        topic: str = "", category: str = "") -> str:
        """Format description with proper citations and hashtags"""
        
        # Start with the main description
        formatted_desc = description.strip()
        
        # Add citations section if provided
        if citations:
            formatted_desc += "\n\n## References\n\n"
            for i, citation in enumerate(citations, 1):
                formatted_desc += f"{i}. {citation}\n"
        
        # Add hashtags section
        formatted_desc += "\n\n## Tags\n\n"
        
        # Generate hashtags based on category and topic
        category_display = self.category_display.get(category, category.title())
        hashtags = [
            "#CopernicusAI",
            "#ResearchPodcast", 
            "#Science",
            f"#{category_display.replace(' ', '')}",
            "#AI",
            "#Research"
        ]
        
        # Add topic-specific hashtags
        if topic:
            # Extract key terms from topic for hashtags
            topic_words = re.findall(r'\b[A-Za-z]+\b', topic)
            for word in topic_words[:3]:  # Max 3 topic hashtags
                if len(word) > 3:  # Only meaningful words
                    hashtags.append(f"#{word.title()}")
        
        formatted_desc += " ".join(hashtags)
        
        return formatted_desc
    
    async def upload_description_to_gcs(self, canonical_filename: str, description: str) -> str:
        """Upload formatted description to GCS"""
        try:
            # Upload description as markdown file
            desc_blob = self.bucket.blob(f"descriptions/{canonical_filename}.md")
            desc_blob.upload_from_string(description, content_type='text/markdown')
            desc_blob.make_public()
            
            desc_url = f"https://storage.googleapis.com/{self.bucket_name}/descriptions/{canonical_filename}.md"
            print(f"📝 Description uploaded: {desc_url}")
            return desc_url
            
        except Exception as e:
            print(f"❌ Error uploading description: {e}")
            return ""
    
    async def upload_audio_to_gcs(self, canonical_filename: str, audio_data: bytes, 
                                format: str = "mp3") -> str:
        """Upload audio file to GCS with canonical naming"""
        try:
            # Ensure mp3 format for canonical naming
            audio_filename = f"{canonical_filename}.mp3"
            audio_blob = self.bucket.blob(f"audio/{audio_filename}")
            
            content_type = "audio/mpeg" if format == "mp3" else "audio/wav"
            audio_blob.upload_from_string(audio_data, content_type=content_type)
            audio_blob.make_public()
            
            audio_url = f"https://storage.googleapis.com/{self.bucket_name}/audio/{audio_filename}"
            print(f"🎵 Audio uploaded: {audio_url}")
            return audio_url
            
        except Exception as e:
            print(f"❌ Error uploading audio: {e}")
            return ""
    
    async def upload_thumbnail_to_gcs(self, canonical_filename: str, thumbnail_data: bytes) -> str:
        """Upload thumbnail to GCS with canonical naming"""
        try:
            # Ensure jpg format for canonical naming
            thumbnail_filename = f"{canonical_filename}-thumb.jpg"
            thumb_blob = self.bucket.blob(f"thumbnails/{thumbnail_filename}")
            
            thumb_blob.upload_from_string(thumbnail_data, content_type="image/jpeg")
            thumb_blob.make_public()
            
            thumb_url = f"https://storage.googleapis.com/{self.bucket_name}/thumbnails/{thumbnail_filename}"
            print(f"🖼️ Thumbnail uploaded: {thumb_url}")
            return thumb_url
            
        except Exception as e:
            print(f"❌ Error uploading thumbnail: {e}")
            return ""

# Global instance
canonical_service = CanonicalNamingService()
