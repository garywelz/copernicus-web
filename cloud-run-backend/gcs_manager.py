import asyncio
import os
from typing import Dict, Optional
from pathlib import Path
from google.cloud import storage
from datetime import datetime
import json
import tempfile

class GCSManager:
    """
    Google Cloud Storage manager for podcast assets
    """
    
    def __init__(self):
        # GCS configuration from environment
        self.project_id = os.getenv("GOOGLE_CLOUD_PROJECT", "regal-scholar-453620-r7")
        self.audio_bucket = os.getenv("GCP_AUDIO_BUCKET", "regal-scholar-453620-r7-podcast-storage")
        self.region = os.getenv("GCP_REGION", "us-central1")
        
        # Initialize GCS client
        self.client = storage.Client(project=self.project_id)
        self.bucket = self.client.bucket(self.audio_bucket)
        
        # Folder structure
        self.folders = {
            "generated_audio": "generated/audio/",
            "generated_thumbnails": "generated/thumbnails/", 
            "generated_transcripts": "generated/transcripts/",
            "generated_descriptions": "generated/descriptions/",
            "generated_rss": "generated/rss/"
        }

    async def health_check(self) -> Dict[str, str]:
        """Check GCS connectivity and permissions"""
        try:
            # Test bucket access
            bucket_exists = self.bucket.exists()
            if bucket_exists:
                # Test write permissions
                test_blob = self.bucket.blob("health_check_test.txt")
                test_blob.upload_from_string("health check")
                test_blob.delete()
                return {"status": "healthy", "bucket": self.audio_bucket}
            else:
                return {"status": "error", "message": "Bucket not found"}
        
        except Exception as e:
            return {"status": "error", "message": str(e)}

    async def upload_episode_assets(
        self,
        job_id: str,
        audio_file: str,
        thumbnail: str,
        transcript: str,
        description: str,
        metadata: Dict
    ) -> Dict[str, str]:
        """
        Upload all episode assets to GCS and return public URLs
        """
        
        urls = {}
        
        try:
            # Upload audio file
            if os.path.exists(audio_file):
                audio_blob_name = f"{self.folders['generated_audio']}{job_id}.mp3"
                audio_url = await self._upload_file(audio_file, audio_blob_name, "audio/mpeg")
                urls["audio"] = audio_url
            
            # Upload thumbnail
            if os.path.exists(thumbnail):
                thumbnail_blob_name = f"{self.folders['generated_thumbnails']}{job_id}-thumb.jpg"
                thumbnail_url = await self._upload_file(thumbnail, thumbnail_blob_name, "image/jpeg")
                urls["thumbnail"] = thumbnail_url
            
            # Upload transcript
            transcript_blob_name = f"{self.folders['generated_transcripts']}{job_id}.md"
            transcript_url = await self._upload_text_content(
                transcript, transcript_blob_name, "text/markdown"
            )
            urls["transcript"] = transcript_url
            
            # Upload description
            description_blob_name = f"{self.folders['generated_descriptions']}{job_id}.md"
            description_url = await self._upload_text_content(
                description, description_blob_name, "text/markdown"
            )
            urls["description"] = description_url
            
            # Create and upload RSS entry
            rss_entry = await self._create_rss_entry(job_id, metadata, urls)
            rss_blob_name = f"{self.folders['generated_rss']}{job_id}.xml"
            rss_url = await self._upload_text_content(
                rss_entry, rss_blob_name, "application/rss+xml"
            )
            urls["rss_entry"] = rss_url
            
            # Clean up temporary files
            await self._cleanup_temp_files([audio_file, thumbnail])
            
            return urls
        
        except Exception as e:
            print(f"Error uploading assets for job {job_id}: {e}")
            raise

    async def _upload_file(self, local_path: str, blob_name: str, content_type: str) -> str:
        """Upload a file to GCS and return public URL"""
        
        try:
            blob = self.bucket.blob(blob_name)
            
            # Upload file
            with open(local_path, 'rb') as file_data:
                blob.upload_from_file(file_data, content_type=content_type)
            
            # Make blob publicly readable
            blob.make_public()
            
            # Return public URL
            return blob.public_url
        
        except Exception as e:
            print(f"Error uploading file {local_path}: {e}")
            raise

    async def _upload_text_content(self, content: str, blob_name: str, content_type: str) -> str:
        """Upload text content to GCS and return public URL"""
        
        try:
            blob = self.bucket.blob(blob_name)
            
            # Upload content
            blob.upload_from_string(content, content_type=content_type)
            
            # Make blob publicly readable
            blob.make_public()
            
            # Return public URL
            return blob.public_url
        
        except Exception as e:
            print(f"Error uploading text content to {blob_name}: {e}")
            raise

    async def _create_rss_entry(self, job_id: str, metadata: Dict, urls: Dict) -> str:
        """Create RSS entry XML for the generated episode"""
        
        # Generate RFC 2822 date
        pub_date = datetime.utcnow().strftime("%a, %d %b %Y %H:%M:%S +0000")
        
        # Get audio file size (estimate if not available)
        audio_size = await self._get_file_size(urls.get("audio", ""))
        
        # Create RSS item XML
        rss_entry = f"""<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0" 
     xmlns:itunes="http://www.itunes.com/dtds/podcast-1.0.dtd"
     xmlns:content="http://purl.org/rss/1.0/modules/content/"
     xmlns:atom="http://www.w3.org/2005/Atom">
  <channel>
    <item>
      <title><![CDATA[{metadata.get('title', 'Generated Episode')}]]></title>
      <description><![CDATA[{metadata.get('subtitle', '')}]]></description>
      <link>{urls.get('description', '')}</link>
      <guid isPermaLink="false">{job_id}</guid>
      <pubDate>{pub_date}</pubDate>
      <enclosure url="{urls.get('audio', '')}" length="{audio_size}" type="audio/mpeg"/>
      
      <!-- iTunes tags -->
      <itunes:title><![CDATA[{metadata.get('title', 'Generated Episode')}]]></itunes:title>
      <itunes:summary><![CDATA[{metadata.get('subtitle', '')}]]></itunes:summary>
      <itunes:author>CopernicusAI</itunes:author>
      <itunes:duration>{metadata.get('estimated_duration', 10)}:00</itunes:duration>
      <itunes:image href="{urls.get('thumbnail', '')}"/>
      <itunes:explicit>false</itunes:explicit>
      
      <!-- Content -->
      <content:encoded><![CDATA[
        <p>{metadata.get('subtitle', '')}</p>
        <p><strong>Key Concepts:</strong> {', '.join(metadata.get('key_concepts', []))}</p>
        <p><strong>Research Areas:</strong> {', '.join(metadata.get('research_areas', []))}</p>
        <p><strong>Difficulty Level:</strong> {metadata.get('difficulty_level', 'intermediate')}</p>
        <p><a href="{urls.get('transcript', '')}">View Full Transcript</a></p>
      ]]></content:encoded>
      
      <!-- Categories -->
      <category>{metadata.get('category', 'Science')}</category>
      {self._format_categories(metadata.get('subcategories', []))}
      
      <!-- Custom metadata -->
      <copernicus:jobId>{job_id}</copernicus:jobId>
      <copernicus:generatedAt>{metadata.get('generated_at', '')}</copernicus:generatedAt>
      <copernicus:researchSources>{metadata.get('research_sources_count', 0)}</copernicus:researchSources>
    </item>
  </channel>
</rss>"""
        
        return rss_entry

    def _format_categories(self, subcategories: list) -> str:
        """Format subcategories as XML"""
        if not subcategories:
            return ""
        
        category_xml = []
        for subcat in subcategories:
            category_xml.append(f"      <category>{subcat}</category>")
        
        return "\n".join(category_xml)

    async def _get_file_size(self, url: str) -> int:
        """Get file size from GCS blob (estimate if not available)"""
        try:
            if not url:
                return 5000000  # 5MB estimate
            
            # Extract blob name from URL
            blob_name = url.split(f"{self.audio_bucket}/")[-1]
            blob = self.bucket.blob(blob_name)
            
            if blob.exists():
                blob.reload()
                return blob.size
            else:
                return 5000000  # 5MB estimate
        
        except Exception:
            return 5000000  # 5MB estimate

    async def _cleanup_temp_files(self, file_paths: list):
        """Clean up temporary files"""
        for file_path in file_paths:
            try:
                if file_path and os.path.exists(file_path):
                    os.remove(file_path)
            except Exception as e:
                print(f"Warning: Could not delete temp file {file_path}: {e}")

    async def list_generated_episodes(self, limit: int = 50) -> list:
        """List recently generated episodes"""
        try:
            blobs = self.client.list_blobs(
                self.bucket, 
                prefix=self.folders["generated_audio"],
                max_results=limit
            )
            
            episodes = []
            for blob in blobs:
                if blob.name.endswith('.mp3'):
                    job_id = Path(blob.name).stem
                    episodes.append({
                        "job_id": job_id,
                        "audio_url": blob.public_url,
                        "created": blob.time_created.isoformat() if blob.time_created else None,
                        "size": blob.size
                    })
            
            return sorted(episodes, key=lambda x: x["created"] or "", reverse=True)
        
        except Exception as e:
            print(f"Error listing episodes: {e}")
            return []

    async def get_episode_assets(self, job_id: str) -> Dict[str, Optional[str]]:
        """Get all asset URLs for a specific episode"""
        assets = {}
        
        # Check each asset type
        asset_types = {
            "audio": (self.folders["generated_audio"], ".mp3"),
            "thumbnail": (self.folders["generated_thumbnails"], "-thumb.jpg"),
            "transcript": (self.folders["generated_transcripts"], ".md"),
            "description": (self.folders["generated_descriptions"], ".md"),
            "rss_entry": (self.folders["generated_rss"], ".xml")
        }
        
        for asset_type, (folder, suffix) in asset_types.items():
            blob_name = f"{folder}{job_id}{suffix}"
            blob = self.bucket.blob(blob_name)
            
            if blob.exists():
                assets[asset_type] = blob.public_url
            else:
                assets[asset_type] = None
        
        return assets

    async def delete_episode_assets(self, job_id: str) -> bool:
        """Delete all assets for a specific episode"""
        try:
            asset_types = {
                "audio": (self.folders["generated_audio"], ".mp3"),
                "thumbnail": (self.folders["generated_thumbnails"], "-thumb.jpg"), 
                "transcript": (self.folders["generated_transcripts"], ".md"),
                "description": (self.folders["generated_descriptions"], ".md"),
                "rss_entry": (self.folders["generated_rss"], ".xml")
            }
            
            deleted_count = 0
            for asset_type, (folder, suffix) in asset_types.items():
                blob_name = f"{folder}{job_id}{suffix}"
                blob = self.bucket.blob(blob_name)
                
                if blob.exists():
                    blob.delete()
                    deleted_count += 1
            
            return deleted_count > 0
        
        except Exception as e:
            print(f"Error deleting assets for job {job_id}: {e}")
            return False

    def get_public_url(self, blob_name: str) -> str:
        """Get public URL for a blob"""
        return f"https://storage.googleapis.com/{self.audio_bucket}/{blob_name}"

    async def ensure_folders_exist(self):
        """Ensure all required folders exist in GCS (create placeholder files if needed)"""
        try:
            for folder_name, folder_path in self.folders.items():
                placeholder_name = f"{folder_path}.placeholder"
                blob = self.bucket.blob(placeholder_name)
                
                if not blob.exists():
                    blob.upload_from_string(
                        f"Placeholder file for {folder_name} folder",
                        content_type="text/plain"
                    )
        
        except Exception as e:
            print(f"Error ensuring folders exist: {e}")

    async def get_storage_stats(self) -> Dict[str, int]:
        """Get storage statistics"""
        try:
            stats = {}
            
            for folder_name, folder_path in self.folders.items():
                blobs = list(self.client.list_blobs(self.bucket, prefix=folder_path))
                stats[folder_name] = len([b for b in blobs if not b.name.endswith('.placeholder')])
            
            return stats
        
        except Exception as e:
            print(f"Error getting storage stats: {e}")
            return {}
