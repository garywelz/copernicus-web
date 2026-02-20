"""
Utility functions for extracting actual audio durations from MP3 files
"""

from typing import Optional
from urllib.parse import urlparse
from google.cloud import storage

try:
    from pydub import AudioSegment
    PYDUB_AVAILABLE = True
except ImportError:
    PYDUB_AVAILABLE = False

def extract_blob_name_from_url(url: str, bucket_name: str) -> Optional[str]:
    """Extract the blob name within the bucket from a public GCS URL."""
    if not url:
        return None
    parsed = urlparse(url)
    path = parsed.path.lstrip("/")
    if not path:
        return None
    if path.startswith(f"{bucket_name}/"):
        return path[len(bucket_name) + 1:]
    return path

def get_mp3_duration_from_gcs(audio_url: str, bucket_name: str) -> Optional[str]:
    """
    Extract actual duration from MP3 file in GCS.
    Returns duration in MM:SS format, or None if extraction fails.
    Uses ffprobe (faster) if available, falls back to pydub.
    """
    if not audio_url:
        return None
    
    try:
        import subprocess
        import json
        
        # Try ffprobe first (much faster, reads metadata without full download)
        try:
            # Use ffprobe to get duration from URL directly (if publicly accessible)
            # or download a small chunk
            result = subprocess.run(
                ['ffprobe', '-v', 'quiet', '-print_format', 'json', '-show_format', audio_url],
                capture_output=True,
                timeout=10,
                text=True
            )
            
            if result.returncode == 0:
                data = json.loads(result.stdout)
                duration_float = float(data.get('format', {}).get('duration', 0))
                if duration_float > 0:
                    minutes = int(duration_float // 60)
                    seconds = int(duration_float % 60)
                    return f"{minutes}:{seconds:02d}"
        except (subprocess.TimeoutExpired, FileNotFoundError, json.JSONDecodeError, ValueError):
            pass  # Fall back to pydub method
        
        # Fallback to pydub method
        if not PYDUB_AVAILABLE:
            return None
        
        storage_client = storage.Client()
        bucket = storage_client.bucket(bucket_name)
        
        # Extract blob name
        blob_name = extract_blob_name_from_url(audio_url, bucket_name)
        
        if not blob_name:
            # Try to extract canonical from URL and try common paths
            canonical = audio_url.split('/')[-1].replace('.mp3', '').split('-audio')[0]
            alt_paths = [
                f"audio/{canonical}.mp3",
                f"generated/audio/{canonical}.mp3",
                f"audio/{canonical}-audio.mp3",
            ]
            
            for alt_path in alt_paths:
                alt_blob = bucket.blob(alt_path)
                if alt_blob.exists():
                    blob_name = alt_path
                    break
        
        if not blob_name:
            return None
        
        blob = bucket.blob(blob_name)
        if not blob.exists():
            return None
        
        # Download to temp file and extract duration
        import tempfile
        import os
        
        with tempfile.NamedTemporaryFile(suffix='.mp3', delete=False) as temp_file:
            blob.download_to_filename(temp_file.name)
            temp_path = temp_file.name
        
        try:
            # Extract duration using pydub
            audio = AudioSegment.from_mp3(temp_path)
            duration_ms = len(audio)
            duration_sec = duration_ms / 1000.0
            
            # Format as MM:SS
            minutes = int(duration_sec // 60)
            seconds = int(duration_sec % 60)
            duration_str = f"{minutes}:{seconds:02d}"
            
            return duration_str
        finally:
            # Clean up temp file
            if os.path.exists(temp_path):
                try:
                    os.unlink(temp_path)
                except:
                    pass
                    
    except Exception:
        return None

def is_estimated_duration(duration: Optional[str]) -> bool:
    """Check if a duration string is an estimated/prompted duration rather than actual."""
    if not duration:
        return True
    
    duration_lower = duration.lower()
    
    # Check for common estimated formats
    return (
        duration == 'Unknown' or
        ('-' in duration and 'minute' in duration_lower) or
        (duration_lower.endswith('minutes') and ':' not in duration) or
        (duration_lower.endswith('minute') and ':' not in duration and duration != '1 minute') or
        duration.startswith('5-10') or 
        duration.startswith('10-15') or
        (duration_lower.startswith('5 minute') or duration_lower.startswith('10 minute'))
    )

