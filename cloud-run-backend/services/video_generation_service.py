"""
Video Generation Service for Copernicus AI Podcasts

Phase 1: Foundation - Basic video composition infrastructure
Future phases will add: visual extraction, animations, YouTube quoting, advanced composition
"""

import asyncio
import os
import tempfile
from pathlib import Path
from typing import Dict, Any, Optional, List
from dataclasses import dataclass
from datetime import datetime

from google.cloud import storage
from utils.logging import structured_logger


@dataclass
class VideoOptions:
    """Configuration options for video generation"""
    resolution: str = "1920x1080"  # 1920x1080, 1280x720, 854x480
    frame_rate: int = 30
    quality: str = "high"  # high, medium, low
    include_subtitles: bool = False  # Phase 4
    include_animations: bool = False  # Phase 3
    include_external_videos: bool = False  # Phase 2


@dataclass
class VideoOutput:
    """Output from video generation"""
    video_url: str
    processing_time: float
    file_size: int
    resolution: str
    duration: float
    metadata: Dict[str, Any]


class VideoGenerationService:
    """
    Service for generating video versions of podcasts.
    
    Phase 1: Basic composition (audio + static thumbnail)
    Future: Multi-source content integration, animations, advanced features
    """
    
    def __init__(self, bucket_name: str = None):
        """
        Initialize video generation service.
        
        Args:
            bucket_name: GCS bucket name for video storage (defaults to podcast storage bucket)
        """
        self.bucket_name = bucket_name or os.getenv(
            "GCP_AUDIO_BUCKET", 
            "regal-scholar-453620-r7-podcast-storage"
        )
        self.storage_client = storage.Client()
        self.bucket = self.storage_client.bucket(self.bucket_name)
        
        # Video storage paths
        self.video_folder = "generated/videos/"
        self.video_assets_folder = "generated/video-assets/"
        
        structured_logger.info("VideoGenerationService initialized",
                              bucket_name=self.bucket_name)
    
    async def generate_podcast_video(
        self,
        audio_url: str,
        thumbnail_url: str,
        canonical_filename: str,
        video_options: Optional[VideoOptions] = None
    ) -> VideoOutput:
        """
        Generate a basic video podcast from audio and thumbnail.
        
        Phase 1: Creates simple video with static thumbnail as background + audio track.
        
        Args:
            audio_url: GCS URL to podcast audio file (MP3)
            thumbnail_url: GCS URL to podcast thumbnail image
            canonical_filename: Unique identifier for the episode
            video_options: Video generation options (defaults used if None)
        
        Returns:
            VideoOutput with video URL and metadata
        """
        if video_options is None:
            video_options = VideoOptions()
        
        start_time = asyncio.get_event_loop().time()
        
        structured_logger.info("Starting video generation",
                              canonical_filename=canonical_filename,
                              resolution=video_options.resolution)
        
        try:
            # Phase 1: Basic composition - static thumbnail + audio
            video_url = await self._compose_basic_video(
                audio_url=audio_url,
                thumbnail_url=thumbnail_url,
                canonical_filename=canonical_filename,
                video_options=video_options
            )
            
            processing_time = asyncio.get_event_loop().time() - start_time
            
            # Get video file metadata
            video_metadata = await self._get_video_metadata(video_url)
            
            structured_logger.info("Video generation completed",
                                  canonical_filename=canonical_filename,
                                  video_url=video_url,
                                  processing_time_seconds=round(processing_time, 2))
            
            return VideoOutput(
                video_url=video_url,
                processing_time=processing_time,
                file_size=video_metadata.get("file_size", 0),
                resolution=video_options.resolution,
                duration=video_metadata.get("duration", 0.0),
                metadata={
                    "canonical_filename": canonical_filename,
                    "generated_at": datetime.utcnow().isoformat(),
                    "options": video_options.__dict__
                }
            )
            
        except Exception as e:
            structured_logger.error("Video generation failed",
                                   canonical_filename=canonical_filename,
                                   error=str(e))
            raise
    
    async def _compose_basic_video(
        self,
        audio_url: str,
        thumbnail_url: str,
        canonical_filename: str,
        video_options: VideoOptions
    ) -> str:
        """
        Compose basic video: static thumbnail as background + audio track.
        
        Uses FFmpeg to create video file.
        Phase 1 implementation - will be enhanced in future phases.
        """
        try:
            import requests
            import subprocess
            
            # Create temporary directory for processing
            with tempfile.TemporaryDirectory() as temp_dir:
                temp_path = Path(temp_dir)
                
                # Download audio and thumbnail
                audio_file = temp_path / "audio.mp3"
                thumbnail_file = temp_path / "thumbnail.jpg"
                output_file = temp_path / f"{canonical_filename}.mp4"
                
                # Download files
                structured_logger.info("Downloading source files",
                                      canonical_filename=canonical_filename)
                
                audio_response = requests.get(audio_url, timeout=60)
                audio_response.raise_for_status()
                audio_file.write_bytes(audio_response.content)
                
                thumbnail_response = requests.get(thumbnail_url, timeout=30)
                thumbnail_response.raise_for_status()
                thumbnail_file.write_bytes(thumbnail_response.content)
                
                # Get audio duration for video length
                audio_duration = await self._get_audio_duration(audio_file)
                
                # Get resolution dimensions
                width, height = map(int, video_options.resolution.split('x'))
                
                # Compose video using FFmpeg
                # Create video with static thumbnail background + audio
                ffmpeg_cmd = [
                    'ffmpeg',
                    '-y',  # Overwrite output file
                    '-loop', '1',  # Loop the image
                    '-i', str(thumbnail_file),  # Input image
                    '-i', str(audio_file),  # Input audio
                    '-c:v', 'libx264',  # Video codec
                    '-tune', 'stillimage',  # Optimize for static image
                    '-c:a', 'aac',  # Audio codec
                    '-b:a', '192k',  # Audio bitrate
                    '-pix_fmt', 'yuv420p',  # Pixel format for compatibility
                    '-shortest',  # Finish encoding when shortest input ends
                    '-vf', f'scale={width}:{height}:force_original_aspect_ratio=decrease,pad={width}:{height}:(ow-iw)/2:(oh-ih)/2',  # Scale and pad to exact resolution
                    '-r', str(video_options.frame_rate),  # Frame rate
                    str(output_file)
                ]
                
                structured_logger.info("Running FFmpeg composition",
                                      canonical_filename=canonical_filename,
                                      command=" ".join(ffmpeg_cmd))
                
                result = subprocess.run(
                    ffmpeg_cmd,
                    capture_output=True,
                    text=True,
                    timeout=600  # 10 minute timeout
                )
                
                if result.returncode != 0:
                    structured_logger.error("FFmpeg composition failed",
                                           canonical_filename=canonical_filename,
                                           stderr=result.stderr)
                    raise Exception(f"FFmpeg failed: {result.stderr}")
                
                # Upload to GCS
                video_blob_name = f"{self.video_folder}{canonical_filename}.mp4"
                blob = self.bucket.blob(video_blob_name)
                
                structured_logger.info("Uploading video to GCS",
                                      canonical_filename=canonical_filename,
                                      blob_name=video_blob_name)
                
                blob.upload_from_filename(str(output_file), content_type="video/mp4")
                blob.make_public()
                
                video_url = f"https://storage.googleapis.com/{self.bucket_name}/{video_blob_name}"
                
                return video_url
                
        except ImportError:
            structured_logger.warning("FFmpeg not available, video generation skipped",
                                     canonical_filename=canonical_filename)
            raise Exception("FFmpeg is required for video generation. Install with: apt-get install ffmpeg")
        except Exception as e:
            structured_logger.error("Video composition error",
                                   canonical_filename=canonical_filename,
                                   error=str(e))
            raise
    
    async def _get_audio_duration(self, audio_file: Path) -> float:
        """Get duration of audio file in seconds using ffprobe."""
        try:
            import subprocess
            
            cmd = [
                'ffprobe',
                '-v', 'error',
                '-show_entries', 'format=duration',
                '-of', 'default=noprint_wrappers=1:nokey=1',
                str(audio_file)
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            if result.returncode == 0:
                return float(result.stdout.strip())
            return 0.0
        except Exception:
            return 0.0
    
    async def _get_video_metadata(self, video_url: str) -> Dict[str, Any]:
        """Get metadata about generated video file."""
        try:
            # Extract blob name from URL
            blob_path = video_url.replace(f"https://storage.googleapis.com/{self.bucket_name}/", "")
            blob = self.bucket.blob(blob_path)
            blob.reload()
            
            return {
                "file_size": blob.size or 0,
                "duration": 0.0,  # Would need ffprobe to get actual duration
                "content_type": blob.content_type or "video/mp4"
            }
        except Exception as e:
            structured_logger.warning("Failed to get video metadata",
                                     video_url=video_url,
                                     error=str(e))
            return {"file_size": 0, "duration": 0.0}


# Future Phase Methods (Placeholders for now):

class VideoGenerationServiceExtended(VideoGenerationService):
    """
    Extended service with future phase capabilities.
    These methods will be implemented in future phases.
    """
    
    async def _extract_visual_content(self, research_context):
        """Phase 2: Extract visuals from research papers, web pages, JSON sources."""
        raise NotImplementedError("Phase 2: Visual extraction")
    
    async def _generate_dynamic_visuals(self, script, research_context):
        """Phase 3: Generate animations and dynamic visualizations."""
        raise NotImplementedError("Phase 3: Dynamic generation")
    
    async def _import_external_videos(self, research_context):
        """Phase 2: Import and quote YouTube/external video segments."""
        raise NotImplementedError("Phase 2: External video import")
    
    async def _generate_subtitles(self, transcript, audio_url):
        """Phase 4: Generate subtitle tracks with timing."""
        raise NotImplementedError("Phase 4: Subtitle generation")
    
    async def _synchronize_content(self, assets, transcript, audio_url):
        """Phase 4: Time-align visual content with audio."""
        raise NotImplementedError("Phase 4: Content synchronization")
    
    async def _compose_video(self, audio_url, timed_assets, subtitle_track, canonical_filename, video_options):
        """Phase 4: Advanced multi-layer video composition."""
        raise NotImplementedError("Phase 4: Advanced composition")


