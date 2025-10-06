#!/usr/bin/env python3
"""
ElevenLabs Voice Service for Legacy Podcast Generation
Addresses voice quality, speed, variety, and natural speaker names
"""

import asyncio
import aiohttp
import logging
from typing import List, Dict, Optional
from dataclasses import dataclass
import io
import json
import time
from google.cloud import secretmanager

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class ElevenLabsVoiceConfig:
    """ElevenLabs voice configuration with natural speaker names"""
    voice_id: str
    speaker_name: str  # Natural first name (Tom, Mary, Susan, Bob)
    voice_description: str
    stability: float = 0.6  # Lower for more expressive speech
    similarity_boost: float = 0.8  # Higher for voice consistency
    style: float = 0.4  # Moderate style for natural conversation
    use_speaker_boost: bool = True

@dataclass
class AudioSegment:
    """Audio segment with speaker metadata"""
    audio_data: bytes
    duration_seconds: float
    speaker_name: str  # Natural first name
    content: str
    voice_config: ElevenLabsVoiceConfig

@dataclass
class SynthesisResult:
    """Complete synthesis result"""
    audio_data: bytes
    total_duration: float
    segments: List[AudioSegment]
    speakers_used: List[str]
    quality_metrics: Dict[str, any]

class ElevenLabsVoiceService:
    """
    Enhanced voice service using ElevenLabs for natural, varied speech
    """
    
    def __init__(self):
        self.api_key = self._get_api_key()
        self.base_url = "https://api.elevenlabs.io/v1"
        
        # Natural speaker configurations with distinct voices using specific voice IDs
        self.voice_configs = {
            "host": ElevenLabsVoiceConfig(
                voice_id="XrExE9yKIg1WjnnlVkGX",  # Matilda - Professional female
                speaker_name="Matilda",
                voice_description="Professional host, warm and engaging",
                stability=0.6,  # Lower for more expressive speech
                similarity_boost=0.8,
                style=0.4,  # Higher for more dynamic delivery
                use_speaker_boost=True
            ),
            "expert": ElevenLabsVoiceConfig(
                voice_id="pNInz6obpgDQGcFmaJgB",  # Adam - Knowledgeable male
                speaker_name="Adam",
                voice_description="Expert researcher, authoritative but approachable",
                stability=0.5,  # Lower for more natural pace
                similarity_boost=0.9,
                style=0.6,  # Higher for more engaging delivery
                use_speaker_boost=True
            ),
            "questioner": ElevenLabsVoiceConfig(
                voice_id="iiidtqDt9FBdT1vfBluA",  # Bill L. Oxley - Curious male
                speaker_name="Bill",
                voice_description="Curious questioner, engaging and thoughtful",
                stability=0.4,  # Lower for more natural pace
                similarity_boost=0.7,
                style=0.7,  # Higher for more dynamic delivery
                use_speaker_boost=True
            ),
            "correspondent": ElevenLabsVoiceConfig(
                voice_id="Pt5YrLNyu6d2s3s4CVMg",  # Lily - Versatile female
                speaker_name="Lily",
                voice_description="Field correspondent, dynamic and informative",
                stability=0.6,
                similarity_boost=0.8,
                style=0.4,
                use_speaker_boost=True
            )
        }
        
        logger.info("✅ ElevenLabs Voice Service initialized with natural speaker names")
    
    def _get_api_key(self) -> str:
        """Get ElevenLabs API key from Secret Manager"""
        try:
            client = secretmanager.SecretManagerServiceClient()
            name = "projects/regal-scholar-453620-r7/secrets/elevenlabs-api-key/versions/latest"
            response = client.access_secret_version(request={"name": name})
            return response.payload.data.decode("UTF-8")
        except Exception as e:
            logger.warning(f"Could not get ElevenLabs API key from Secret Manager: {e}")
            import os
            return os.getenv("ELEVENLABS_API_KEY", "")
    
    async def synthesize_script_segments(
        self, 
        script_segments: List[Dict[str, str]], 
        target_duration_seconds: int = None,
        voice_style: str = "conversational"
    ) -> SynthesisResult:
        """
        Synthesize script segments using ElevenLabs with natural speaker names
        """
        logger.info(f"🎙️ Starting ElevenLabs synthesis for {len(script_segments)} segments")
        
        if not self.api_key:
            raise Exception("ElevenLabs API key not available")
        
        # Fallback: if no segments parsed, treat entire script as a single HOST segment
        if not script_segments:
            logger.warning("⚠️ No segments parsed; falling back to single HOST segment")
            # Attempt to use the raw script from context if available
            # This function receives already-parsed segments, so we create a default empty list
            # The caller should handle parsing; however, for robustness we synthesize an empty placeholder here
            # and let upstream caller provide the full script bytes. To ensure audio is not empty, we return empty combined
            # which will be caught by upstream logic. If upstream passes raw script instead of segments, prefer that.
            script_segments = [{"speaker": "host", "content": ""}]
        
        audio_segments = []
        total_duration = 0.0
        speakers_used = set()
        
        # Speaker name mapping from script names to voice roles
        speaker_mapping = {
            'matilda': 'host',      # Matilda (female) - HOST
            'adam': 'expert',       # Adam (male) - EXPERT
            'bill': 'questioner',   # Bill (male) - QUESTIONER
            'lily': 'correspondent', # Lily (female) - CORRESPONDENT
            # Legacy mappings for backward compatibility
            'sarah': 'host',
            'tom': 'expert', 
            'mary': 'questioner',
            'bob': 'correspondent',
            # Fallback mappings for old format
            'host': 'host',
            'expert': 'expert',
            'questioner': 'questioner',
            'correspondent': 'correspondent'
        }
        
        # Process each segment
        for i, segment in enumerate(script_segments):
            speaker_name = segment.get('speaker', 'host').lower()
            content = segment.get('content', '').strip()
            
            # Map speaker name to voice role
            speaker_role = speaker_mapping.get(speaker_name, 'host')
            
            if not content:
                continue
            
            # Get voice configuration
            voice_config = self.voice_configs.get(speaker_role, self.voice_configs['host'])
            speakers_used.add(voice_config.speaker_name)
            
            logger.info(f"🔊 Synthesizing segment {i+1}/{len(script_segments)} ({voice_config.speaker_name})")
            
            # Clean content for natural speech
            clean_content = self._preprocess_text_for_natural_speech(content)
            
            # Synthesize audio
            try:
                audio_data, duration = await self._synthesize_segment(clean_content, voice_config)
                
                audio_segment = AudioSegment(
                    audio_data=audio_data,
                    duration_seconds=duration,
                    speaker_name=voice_config.speaker_name,
                    content=clean_content,
                    voice_config=voice_config
                )
                
                audio_segments.append(audio_segment)
                total_duration += duration
                
                logger.info(f"✅ Segment complete: {duration:.1f}s ({voice_config.speaker_name})")
                
            except Exception as e:
                logger.error(f"❌ Failed to synthesize segment {i+1}: {e}")
                continue
        
        # Combine audio segments
        logger.info("🔗 Combining audio segments...")
        # Extract audio data from AudioSegment objects
        audio_data_list = [segment.audio_data for segment in audio_segments]
        combined_audio = await self._combine_audio_segments(audio_data_list)
        
        # Quality metrics
        quality_metrics = {
            "total_segments": len(audio_segments),
            "speakers_count": len(speakers_used),
            "average_segment_duration": total_duration / len(audio_segments) if audio_segments else 0,
            "synthesis_method": "elevenlabs",
            "voice_variety_score": len(speakers_used) / 4.0  # Out of 4 possible voices
        }
        
        logger.info(f"🎯 ElevenLabs synthesis complete:")
        logger.info(f"   Total duration: {total_duration:.1f}s")
        logger.info(f"   Speakers used: {', '.join(sorted(speakers_used))}")
        logger.info(f"   Voice variety: {quality_metrics['voice_variety_score']:.1%}")
        
        return SynthesisResult(
            audio_data=combined_audio,
            total_duration=total_duration,
            segments=audio_segments,
            speakers_used=list(speakers_used),
            quality_metrics=quality_metrics
        )
    
    def _preprocess_text_for_natural_speech(self, text: str) -> str:
        """
        Preprocess text for natural speech synthesis
        Remove any remaining markup and ensure conversational flow
        """
        import re
        
        # Remove any speaker labels that might have leaked through
        text = re.sub(r'^(HOST|EXPERT|QUESTIONER|CORRESPONDENT):\s*', '', text, flags=re.IGNORECASE)
        text = re.sub(r'^(Matilda|Gary|Bill|Lily|Sarah|Tom|Mary|Bob):\s*', '', text, flags=re.IGNORECASE)
        
        # Remove markdown formatting
        text = re.sub(r'\*\*(.*?)\*\*', r'\1', text)
        text = re.sub(r'\*(.*?)\*', r'\1', text)
        text = re.sub(r'__(.*?)__', r'\1', text)
        
        # Remove academic titles and formal language
        text = re.sub(r'\b(Dr\.|Professor|PhD|Ph\.D\.)\s+', '', text)
        text = re.sub(r'\b(according to|as stated by|research shows that)\b', '', text, flags=re.IGNORECASE)
        
        # Clean up JSON artifacts and special characters
        text = re.sub(r'[{}"\[\]]', '', text)
        text = re.sub(r'&[a-zA-Z]+;', '', text)  # Remove HTML entities
        
        # Normalize whitespace and ensure proper sentence flow
        text = re.sub(r'\s+', ' ', text).strip()
        
        # Add natural pauses for better speech flow
        text = re.sub(r'([.!?])\s+([A-Z])', r'\1 \2', text)
        
        return text
    
    def _parse_script_segments(self, script: str) -> List[Dict[str, str]]:
        """Parse script into [{speaker, content}] segments"""
        import re
        
        # Debug: Log the first 500 characters of the script
        logger.info(f"🔍 Parsing script (first 500 chars): {script[:500]}...")
        
        # Debug: Check for common formatting issues
        if "**HOST:**" in script or "**EXPERT:**" in script:
            logger.warning("⚠️ Script contains markdown formatting (**HOST:**) instead of plain labels (HOST:)")
            # Fix markdown formatting
            script = re.sub(r'\*\*(HOST|EXPERT|QUESTIONER|CORRESPONDENT):\*\*', r'\1:', script)
            logger.info("🔧 Fixed markdown formatting in script")
        
        if "HOST:" not in script and "EXPERT:" not in script:
            logger.warning("⚠️ Script doesn't contain any speaker labels (HOST:, EXPERT:, etc.)")
        
        # Count potential speaker label occurrences
        host_count = len(re.findall(r'\bHOST:', script, re.IGNORECASE))
        expert_count = len(re.findall(r'\bEXPERT:', script, re.IGNORECASE))
        questioner_count = len(re.findall(r'\bQUESTIONER:', script, re.IGNORECASE))
        logger.info(f"🔍 Speaker label counts: HOST:{host_count}, EXPERT:{expert_count}, QUESTIONER:{questioner_count}")
        
        segments: List[Dict[str, str]] = []
        lines = script.split('\n')
        
        current_speaker = None
        current_content = []
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
                
            # Look for speaker labels (roles or first names)
            # Accept role labels: HOST:, EXPERT:, QUESTIONER:, CORRESPONDENT:
            role_match = re.match(r'^(HOST|EXPERT|QUESTIONER|CORRESPONDENT):\s*(.*)', line, re.IGNORECASE)
            # Accept common first-name labels: Sarah:, Tom:, Mary:, Bob:, Maya:, etc. (single capitalized word followed by colon)
            name_match = re.match(r'^([A-Z][a-zA-Z]+):\s*(.*)', line)
            
            # Also look for variations like "HOST -", "EXPERT -", etc.
            role_dash_match = re.match(r'^(HOST|EXPERT|QUESTIONER|CORRESPONDENT)\s*-\s*(.*)', line, re.IGNORECASE)

            if role_match:
                # Save previous speaker's content if any
                if current_speaker and current_content:
                    clean_text = self._preprocess_text_for_natural_speech(' '.join(current_content))
                    if clean_text:
                        segments.append({"speaker": current_speaker, "content": clean_text})
                
                # Start new speaker
                current_speaker = role_match.group(1).lower()
                current_content = [role_match.group(2).strip()] if role_match.group(2).strip() else []
                
            elif role_dash_match:
                # Save previous speaker's content if any
                if current_speaker and current_content:
                    clean_text = self._preprocess_text_for_natural_speech(' '.join(current_content))
                    if clean_text:
                        segments.append({"speaker": current_speaker, "content": clean_text})
                
                # Start new speaker
                current_speaker = role_dash_match.group(1).lower()
                current_content = [role_dash_match.group(2).strip()] if role_dash_match.group(2).strip() else []
                
            elif name_match:
                # Save previous speaker's content if any
                if current_speaker and current_content:
                    clean_text = self._preprocess_text_for_natural_speech(' '.join(current_content))
                    if clean_text:
                        segments.append({"speaker": current_speaker, "content": clean_text})
                
                # Start new speaker
                first_name = name_match.group(1).strip().lower()
                text = name_match.group(2).strip()
                
                # Map common speaker first names to voice roles with gender-appropriate assignments
                name_to_role = {
                    # Primary voice names (from ElevenLabs voice IDs)
                    "matilda": "host",      # Matilda (female) - XrExE9yKIg1WjnnlVkGX
                    "adam": "expert",       # Adam (male) - pNInz6obpgDQGcFmaJgB
                    "bill": "questioner",   # Bill (male) - iiidtqDt9FBdT1vfBluA
                    "lily": "correspondent", # Lily (female) - Pt5YrLNyu6d2s3s4CVMg
                    
                    # Legacy female names -> Female voices
                    "sarah": "host",        # Sarah (female)
                    "mary": "questioner",   # Mary (female)
                    "susan": "host",        # Susan (female)
                    "maya": "host",         # Maya (female)
                    "elena": "correspondent", # Elena (female)
                    "anna": "questioner",   # Anna (female)
                    "emma": "host",         # Emma (female)
                    
                    # Legacy male names -> Male voices
                    "gary": "expert",       # Gary (male)
                    "tom": "expert",        # Tom (male)
                    "bob": "correspondent", # Bob (male)
                    "james": "expert",      # James (male)
                    "marcus": "expert",    # Marcus (male)
                    "david": "questioner", # David (male)
                    "john": "correspondent", # John (male)
                    "michael": "expert",   # Michael (male)
                }
                current_speaker = name_to_role.get(first_name, "host")
                current_content = [text] if text else []
                
            else:
                # This is content for the current speaker
                if current_speaker:
                    current_content.append(line)
        
        # Don't forget the last speaker's content
        if current_speaker and current_content:
            clean_text = self._preprocess_text_for_natural_speech(' '.join(current_content))
            if clean_text:
                segments.append({"speaker": current_speaker, "content": clean_text})
        
        # If no segments found, try to create multi-voice content from the script
        if not segments:
            logger.warning("⚠️ No speaker segments found, attempting to create multi-voice content from script")
            segments = self._create_multi_voice_from_script(script)
        
        logger.info(f"📝 Parsed {len(segments)} script segments")
        for i, segment in enumerate(segments):
            logger.info(f"   Segment {i+1}: {segment['speaker']} - {segment['content'][:100]}...")
        
        return segments
    
    def _create_multi_voice_from_script(self, script: str) -> List[Dict[str, str]]:
        """Create multi-voice segments from a script without speaker labels"""
        import re
        
        # Split script into paragraphs
        paragraphs = re.split(r'\n\s*\n', script)
        segments = []
        
        # Define speaker rotation
        speakers = ["host", "expert", "questioner"]
        speaker_index = 0
        
        for paragraph in paragraphs:
            paragraph = paragraph.strip()
            if not paragraph:
                continue
                
            # Clean the paragraph
            clean_text = self._preprocess_text_for_natural_speech(paragraph)
            if clean_text and len(clean_text) > 20:  # Only add substantial content
                speaker = speakers[speaker_index % len(speakers)]
                segments.append({
                    "speaker": speaker,
                    "content": clean_text
                })
                speaker_index += 1
        
        logger.info(f"🔄 Created {len(segments)} multi-voice segments from script")
        return segments
    
    async def _synthesize_segment(self, text: str, voice_config: ElevenLabsVoiceConfig) -> tuple[bytes, float]:
        """Synthesize a single text segment using ElevenLabs"""
        
        # Prepare request data
        data = {
            "text": text,
            "model_id": "eleven_multilingual_v2",  # Latest model for best quality
            "voice_settings": {
                "stability": voice_config.stability,
                "similarity_boost": voice_config.similarity_boost,
                "style": voice_config.style,
                "use_speaker_boost": voice_config.use_speaker_boost
            }
        }
        
        headers = {
            "Accept": "audio/mpeg",
            "Content-Type": "application/json",
            "xi-api-key": self.api_key
        }
        
        url = f"{self.base_url}/text-to-speech/{voice_config.voice_id}"
        
        async with aiohttp.ClientSession() as session:
            async with session.post(url, json=data, headers=headers) as response:
                if response.status == 200:
                    audio_data = await response.read()
                    
                    # Estimate duration (rough calculation for MP3)
                    # More accurate would require audio analysis, but this is sufficient
                    estimated_duration = len(text.split()) * 0.6  # ~0.6 seconds per word
                    
                    return audio_data, estimated_duration
                else:
                    error_text = await response.text()
                    raise Exception(f"ElevenLabs API error {response.status}: {error_text}")
    
    async def _combine_audio_segments(self, segments: List[bytes]) -> bytes:
        """Combine audio segments into a single audio file using streaming ffmpeg"""
        if not segments:
            return b""
        
        if len(segments) == 1:
            return segments[0]
        
        try:
            # Use streaming ffmpeg approach for better memory efficiency
            return await asyncio.wait_for(
                self._combine_audio_segments_streaming(segments),
                timeout=600  # 10 minute timeout for streaming approach
            )
        except asyncio.TimeoutError:
            logger.error("❌ Audio combination timed out after 10 minutes")
            # Return first segment as fallback
            return segments[0] if segments else b""
        except Exception as e:
            logger.error(f"❌ Audio combination failed: {e}")
            # Fallback to old method if streaming fails
            logger.info("🔄 Falling back to pydub method")
            return await self._combine_audio_segments_internal(segments)
    
    async def _combine_audio_segments_streaming(self, segments: List[bytes]) -> bytes:
        """Combine audio segments using streaming ffmpeg with temporary files (memory efficient)"""
        from google.cloud import storage
        import tempfile
        import subprocess
        import os
        import psutil
        import gc
        from datetime import timedelta
        
        logger.info(f"🌊 Starting streaming ffmpeg combination for {len(segments)} segments")
        logger.info(f"💾 Initial memory usage: {psutil.virtual_memory().percent:.1f}%")
        
        bucket_name = "regal-scholar-453620-r7-podcast-storage"
        client = storage.Client()
        bucket = client.bucket(bucket_name)
        
        # Upload segments to GCS first
        segment_paths = []
        temp_files = []
        
        try:
            # Upload each segment to GCS
            for i, segment_data in enumerate(segments):
                segment_blob_name = f"temp_segments/segment_{i:04d}.mp3"
                blob = bucket.blob(segment_blob_name)
                
                # Upload segment
                blob.upload_from_string(segment_data, content_type="audio/mpeg")
                segment_paths.append(segment_blob_name)
                
                if (i + 1) % 10 == 0:
                    memory_percent = psutil.virtual_memory().percent
                    logger.info(f"📤 Uploaded {i+1} segments. Memory: {memory_percent:.1f}%")
            
            logger.info(f"✅ All {len(segments)} segments uploaded to GCS")
            
            # Create ffconcat file with signed URLs
            concat_file = tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.txt')
            concat_file.write("ffconcat version 1.0\n")
            
            for segment_path in segment_paths:
                # Generate signed URL for the segment
                blob = bucket.blob(segment_path)
                signed_url = blob.generate_signed_url(
                    expiration=timedelta(minutes=120),
                    method='GET'
                )
                concat_file.write(f"file '{signed_url}'\n")
            
            concat_file.close()
            concat_file_path = concat_file.name
            
            logger.info(f"📝 Created ffconcat file: {concat_file_path}")
            
            # Create temporary output file
            output_file = tempfile.NamedTemporaryFile(delete=False, suffix=".mp3")
            output_file.close()
            output_path = output_file.name
            
            # Run ffmpeg with streaming and enhanced debugging
            ffmpeg_cmd = [
                "ffmpeg",
                "-v", "debug",  # Maximum verbosity for debugging
                "-hide_banner",
                "-f", "concat",
                "-safe", "0",
                "-protocol_whitelist", "file,https,tls,tcp",
                "-i", concat_file_path,
                "-c", "copy",  # Stream copy for speed
                "-movflags", "+faststart",
                output_path
            ]
            
            logger.info(f"🎬 Starting ffmpeg with enhanced debugging")
            logger.info(f"🎬 FFMPEG Command: {' '.join(ffmpeg_cmd)}")
            logger.info(f"🎬 Concat file path: {concat_file_path}")
            logger.info(f"🎬 Output path: {output_path}")
            logger.info(f"🎬 Number of segments: {len(segment_paths)}")
            
            # Log system resources before ffmpeg
            memory_before = psutil.virtual_memory()
            cpu_before = psutil.cpu_percent()
            logger.info(f"💾 System resources before ffmpeg:")
            logger.info(f"   Memory: {memory_before.percent:.1f}% ({memory_before.used / 1024**3:.2f}GB / {memory_before.total / 1024**3:.2f}GB)")
            logger.info(f"   CPU: {cpu_before:.1f}%")
            
            # Log concat file contents for debugging
            try:
                with open(concat_file_path, 'r') as f:
                    concat_contents = f.read()
                logger.info(f"📝 Concat file contents (first 1000 chars): {concat_contents[:1000]}")
                logger.info(f"📝 Concat file total length: {len(concat_contents)} characters")
            except Exception as e:
                logger.error(f"❌ Failed to read concat file for debugging: {e}")
            
            # Execute ffmpeg with detailed output capture
            ffmpeg_start_time = time.time()
            logger.info(f"⏰ FFMPEG start time: {ffmpeg_start_time}")
            
            try:
                result = subprocess.run(
                    ffmpeg_cmd,
                    capture_output=True,
                    text=True,
                    timeout=480,  # 8 minute timeout for ffmpeg
                    bufsize=1,  # Line buffered
                    universal_newlines=True
                )
                
                ffmpeg_end_time = time.time()
                ffmpeg_duration = ffmpeg_end_time - ffmpeg_start_time
                
                logger.info(f"⏰ FFMPEG completed in {ffmpeg_duration:.2f} seconds")
                logger.info(f"🎬 FFMPEG return code: {result.returncode}")
                logger.info(f"🎬 FFMPEG stdout length: {len(result.stdout)} characters")
                logger.info(f"🎬 FFMPEG stderr length: {len(result.stderr)} characters")
                
                # Log ffmpeg output for debugging
                if result.stdout:
                    logger.info(f"📤 FFMPEG stdout (last 500 chars): {result.stdout[-500:]}")
                if result.stderr:
                    logger.info(f"📤 FFMPEG stderr (last 500 chars): {result.stderr[-500:]}")
                
            except subprocess.TimeoutExpired as timeout_error:
                ffmpeg_end_time = time.time()
                ffmpeg_duration = ffmpeg_end_time - ffmpeg_start_time
                logger.error(f"⏰ FFMPEG TIMEOUT after {ffmpeg_duration:.2f} seconds")
                logger.error(f"❌ FFMPEG timeout error: {timeout_error}")
                if hasattr(timeout_error, 'stdout') and timeout_error.stdout:
                    logger.error(f"📤 FFMPEG stdout at timeout: {timeout_error.stdout[-500:]}")
                if hasattr(timeout_error, 'stderr') and timeout_error.stderr:
                    logger.error(f"📤 FFMPEG stderr at timeout: {timeout_error.stderr[-500:]}")
                raise
            
            if result.returncode != 0:
                logger.error(f"❌ ffmpeg failed with return code {result.returncode}")
                logger.error(f"❌ ffmpeg stderr: {result.stderr}")
                raise Exception(f"ffmpeg failed: {result.stderr}")
            
            # Log system resources after ffmpeg
            memory_after = psutil.virtual_memory()
            cpu_after = psutil.cpu_percent()
            logger.info(f"✅ ffmpeg completed successfully")
            logger.info(f"💾 System resources after ffmpeg:")
            logger.info(f"   Memory: {memory_after.percent:.1f}% ({memory_after.used / 1024**3:.2f}GB / {memory_after.total / 1024**3:.2f}GB)")
            logger.info(f"   CPU: {cpu_after:.1f}%")
            logger.info(f"   Memory change: {memory_after.percent - memory_before.percent:+.1f}%")
            logger.info(f"   CPU change: {cpu_after - cpu_before:+.1f}%")
            
            # Read the output file
            with open(output_path, 'rb') as f:
                combined_audio = f.read()
            
            logger.info(f"✅ Streaming combination complete: {len(combined_audio)} bytes")
            logger.info(f"💾 Final memory: {psutil.virtual_memory().percent:.1f}%")
            
            return combined_audio
            
        except subprocess.TimeoutExpired:
            logger.error("❌ ffmpeg timed out after 8 minutes")
            raise Exception("ffmpeg processing timed out")
        except Exception as e:
            logger.error(f"❌ Streaming ffmpeg combination failed: {e}")
            raise e
        finally:
            # Clean up temporary files
            for temp_file in [concat_file_path, output_path]:
                try:
                    if temp_file and os.path.exists(temp_file):
                        os.unlink(temp_file)
                except Exception as e:
                    logger.warning(f"⚠️ Failed to clean up temp file {temp_file}: {e}")
            
            # Clean up GCS temp segments
            for segment_path in segment_paths:
                try:
                    blob = bucket.blob(segment_path)
                    blob.delete()
                except Exception as e:
                    logger.warning(f"⚠️ Failed to delete temp segment {segment_path}: {e}")
            
            # Force garbage collection
            gc.collect()
            logger.info(f"🗑️ Cleanup completed. Memory: {psutil.virtual_memory().percent:.1f}%")
    
    async def _combine_audio_segments_internal(self, segments: List[bytes]) -> bytes:
        """Internal method for combining audio segments"""
        try:
            # Use pydub for proper audio concatenation
            from pydub import AudioSegment
            import io
            import tempfile
            import os
            
            logger.info(f"🔗 Combining {len(segments)} audio segments with pydub")
            
            # For large numbers of segments, use temporary files to avoid memory issues
            if len(segments) > 20:
                logger.info("📁 Using temporary file approach for large segment count")
                try:
                    return await self._combine_audio_segments_with_temp_files(segments)
                except Exception as temp_error:
                    logger.error(f"❌ Temp file approach failed: {temp_error}")
                    logger.info("🔄 Falling back to in-memory approach with smaller batches")
                    return await self._combine_audio_segments_in_batches(segments, batch_size=10)
            
            # Convert each segment to AudioSegment
            audio_segments = []
            for i, segment_data in enumerate(segments):
                try:
                    # Create AudioSegment from MP3 bytes
                    audio_segment = AudioSegment.from_mp3(io.BytesIO(segment_data))
                    audio_segments.append(audio_segment)
                    logger.info(f"✅ Segment {i+1} loaded: {len(audio_segment)}ms")
                except Exception as e:
                    logger.error(f"❌ Failed to load segment {i+1}: {e}")
                    continue
            
            if not audio_segments:
                raise Exception("No valid audio segments could be loaded")
            
            # Concatenate all segments
            combined_audio = audio_segments[0]
            for i, segment in enumerate(audio_segments[1:], 1):
                combined_audio += segment
                logger.info(f"✅ Added segment {i+1}: total duration {len(combined_audio)}ms")
            
            # Export as MP3 with optimized settings and timeout protection
            output_buffer = io.BytesIO()
            try:
                combined_audio.export(
                    output_buffer, 
                    format="mp3", 
                    bitrate="128k",
                    parameters=["-q:a", "2"]  # Lower quality for faster processing
                )
                output_buffer.seek(0)
            except Exception as export_error:
                logger.error(f"❌ Export failed, trying fallback: {export_error}")
                # Fallback to simpler export without quality parameters
                output_buffer = io.BytesIO()
                combined_audio.export(output_buffer, format="mp3")
                output_buffer.seek(0)
            
            logger.info(f"✅ Successfully combined {len(audio_segments)} segments: {len(combined_audio)}ms total")
            return output_buffer.getvalue()
            
        except ImportError:
            logger.warning("⚠️ pydub not available, using fallback concatenation")
            # Fallback to simple concatenation (may not work properly)
            combined = b""
            for segment in segments:
                combined += segment
            return combined
        except Exception as e:
            logger.error(f"❌ Failed to combine audio segments: {e}")
            raise e  # Re-raise to be caught by timeout wrapper
    
    async def _combine_audio_segments_with_temp_files(self, segments: List[bytes]) -> bytes:
        """Combine audio segments using temporary files to avoid memory issues"""
        from pydub import AudioSegment
        import io
        import tempfile
        import os
        import psutil
        import gc
        
        logger.info(f"🔧 Starting temp file audio combination for {len(segments)} segments")
        logger.info(f"💾 Initial memory usage: {psutil.virtual_memory().percent:.1f}%")
        
        temp_files = []
        try:
            # Create temporary files for each segment
            for i, segment_data in enumerate(segments):
                temp_file = tempfile.NamedTemporaryFile(suffix=f"_segment_{i}.mp3", delete=False)
                temp_file.write(segment_data)
                temp_file.close()
                temp_files.append(temp_file.name)
                logger.info(f"✅ Created temp file for segment {i+1}: {temp_file.name}")
                
                # Log memory usage every 10 segments
                if (i + 1) % 10 == 0:
                    memory_percent = psutil.virtual_memory().percent
                    logger.info(f"📊 Memory usage after {i+1} temp files: {memory_percent:.1f}%")
            
            logger.info(f"📁 All {len(temp_files)} temp files created successfully")
            
            # Load first segment with detailed logging
            logger.info(f"🎵 Loading base segment from: {temp_files[0]}")
            combined_audio = AudioSegment.from_mp3(temp_files[0])
            logger.info(f"✅ Loaded base segment: {len(combined_audio)}ms ({len(combined_audio)} samples)")
            logger.info(f"💾 Memory after loading base: {psutil.virtual_memory().percent:.1f}%")
            
            # Add remaining segments one by one with detailed logging
            for i, temp_file in enumerate(temp_files[1:], 1):
                logger.info(f"🎵 Loading segment {i+1} from: {temp_file}")
                segment = AudioSegment.from_mp3(temp_file)
                logger.info(f"✅ Loaded segment {i+1}: {len(segment)}ms ({len(segment)} samples)")
                
                # Perform the concatenation
                logger.info(f"🔗 Concatenating segment {i+1} to combined audio...")
                combined_audio += segment
                logger.info(f"✅ Added segment {i+1}: total duration {len(combined_audio)}ms ({len(combined_audio)} samples)")
                
                # Log memory usage every 5 segments
                if i % 5 == 0:
                    memory_percent = psutil.virtual_memory().percent
                    logger.info(f"📊 Memory usage after segment {i+1}: {memory_percent:.1f}%")
                
                # Clean up the temp file immediately to free memory
                logger.info(f"🗑️ Cleaning up temp file: {temp_file}")
                os.unlink(temp_file)
                logger.info(f"✅ Cleaned up segment {i+1} temp file")
            
            # Export final result with detailed logging and error handling
            logger.info(f"🎯 Starting final export of {len(combined_audio)}ms audio")
            logger.info(f"💾 Memory before export: {psutil.virtual_memory().percent:.1f}%")
            
            output_buffer = io.BytesIO()
            try:
                logger.info("📤 Exporting to MP3 with optimized settings...")
                combined_audio.export(
                    output_buffer, 
                    format="mp3", 
                    bitrate="128k",
                    parameters=["-q:a", "2"]
                )
                output_buffer.seek(0)
                logger.info(f"✅ Export successful: {len(output_buffer.getvalue())} bytes")
            except Exception as export_error:
                logger.error(f"❌ Export failed in temp file approach, trying fallback: {export_error}")
                logger.error(f"🔍 Export error type: {type(export_error).__name__}")
                logger.error(f"🔍 Export error details: {str(export_error)}")
                
                # Fallback to simpler export
                logger.info("🔄 Attempting fallback export without quality parameters...")
                output_buffer = io.BytesIO()
                combined_audio.export(output_buffer, format="mp3")
                output_buffer.seek(0)
                logger.info(f"✅ Fallback export successful: {len(output_buffer.getvalue())} bytes")
            
            logger.info(f"💾 Memory after export: {psutil.virtual_memory().percent:.1f}%")
            logger.info(f"✅ Successfully combined {len(segments)} segments using temp files: {len(combined_audio)}ms total")
            
            # Force garbage collection to free memory
            gc.collect()
            logger.info(f"🗑️ Garbage collection completed. Memory: {psutil.virtual_memory().percent:.1f}%")
            
            return output_buffer.getvalue()
            
        finally:
            # Clean up any remaining temp files
            for temp_file in temp_files:
                try:
                    if os.path.exists(temp_file):
                        os.unlink(temp_file)
                except Exception as e:
                    logger.warning(f"⚠️ Failed to clean up temp file {temp_file}: {e}")
    
    async def _combine_audio_segments_in_batches(self, segments: List[bytes], batch_size: int = 10) -> bytes:
        """Combine audio segments in smaller batches to avoid memory issues"""
        from pydub import AudioSegment
        import io
        import psutil
        import gc
        
        logger.info(f"🔄 Starting batch processing for {len(segments)} segments (batch size: {batch_size})")
        logger.info(f"💾 Initial memory: {psutil.virtual_memory().percent:.1f}%")
        
        # Process segments in batches
        batch_results = []
        
        for i in range(0, len(segments), batch_size):
            batch = segments[i:i + batch_size]
            batch_num = (i // batch_size) + 1
            total_batches = (len(segments) + batch_size - 1) // batch_size
            
            logger.info(f"📦 Processing batch {batch_num}/{total_batches} ({len(batch)} segments)")
            
            # Combine this batch in memory
            batch_audio_segments = []
            for j, segment_data in enumerate(batch):
                try:
                    audio_segment = AudioSegment.from_mp3(io.BytesIO(segment_data))
                    batch_audio_segments.append(audio_segment)
                    logger.info(f"✅ Batch {batch_num} segment {j+1} loaded: {len(audio_segment)}ms")
                except Exception as e:
                    logger.error(f"❌ Failed to load batch {batch_num} segment {j+1}: {e}")
                    continue
            
            if batch_audio_segments:
                # Combine batch
                batch_combined = batch_audio_segments[0]
                for segment in batch_audio_segments[1:]:
                    batch_combined += segment
                
                # Export batch to bytes
                batch_buffer = io.BytesIO()
                batch_combined.export(batch_buffer, format="mp3")
                batch_results.append(batch_buffer.getvalue())
                
                logger.info(f"✅ Batch {batch_num} combined: {len(batch_combined)}ms")
                logger.info(f"💾 Memory after batch {batch_num}: {psutil.virtual_memory().percent:.1f}%")
                
                # Clean up batch memory
                del batch_audio_segments, batch_combined, batch_buffer
                gc.collect()
        
        # Combine all batch results
        logger.info(f"🔗 Combining {len(batch_results)} batch results")
        
        if not batch_results:
            raise Exception("No valid batches were created")
        
        if len(batch_results) == 1:
            logger.info("✅ Only one batch, returning directly")
            return batch_results[0]
        
        # Load first batch as base
        final_combined = AudioSegment.from_mp3(io.BytesIO(batch_results[0]))
        logger.info(f"✅ Loaded base batch: {len(final_combined)}ms")
        
        # Add remaining batches
        for i, batch_data in enumerate(batch_results[1:], 1):
            batch_segment = AudioSegment.from_mp3(io.BytesIO(batch_data))
            final_combined += batch_segment
            logger.info(f"✅ Added batch {i+1}: total {len(final_combined)}ms")
            logger.info(f"💾 Memory after batch {i+1}: {psutil.virtual_memory().percent:.1f}%")
        
        # Export final result
        logger.info("📤 Exporting final combined audio")
        final_buffer = io.BytesIO()
        final_combined.export(final_buffer, format="mp3")
        final_buffer.seek(0)
        
        logger.info(f"✅ Batch processing complete: {len(final_combined)}ms total")
        logger.info(f"💾 Final memory: {psutil.virtual_memory().percent:.1f}%")
        
        return final_buffer.getvalue()
    
    async def add_audio_bumpers(self, main_audio: bytes, intro_path: str, outro_path: str) -> bytes:
        """
        Add intro and outro bumpers to the main audio content
        """
        logger.info("🎵 Adding audio bumpers (intro and outro)")
        
        # Validate main audio
        if not main_audio or len(main_audio) == 0:
            logger.error("❌ Main audio is empty, cannot add bumpers")
            raise ValueError("Main audio is empty")
        
        logger.info(f"📊 Main audio size: {len(main_audio)} bytes")
        
        try:
            # Read bumper files
            logger.info(f"📁 Reading intro bumper: {intro_path}")
            with open(intro_path, 'rb') as f:
                intro_audio = f.read()
            logger.info(f"📊 Intro bumper size: {len(intro_audio)} bytes")
            
            logger.info(f"📁 Reading outro bumper: {outro_path}")
            with open(outro_path, 'rb') as f:
                outro_audio = f.read()
            logger.info(f"📊 Outro bumper size: {len(outro_audio)} bytes")
            
            # Use pydub for proper audio combining
            try:
                from pydub import AudioSegment
                import io
                
                # Convert bytes to AudioSegment objects
                intro_segment = AudioSegment.from_mp3(io.BytesIO(intro_audio))
                main_segment = AudioSegment.from_mp3(io.BytesIO(main_audio))
                outro_segment = AudioSegment.from_mp3(io.BytesIO(outro_audio))
                
                # Combine: intro + main + outro
                final_audio_segment = intro_segment + main_segment + outro_segment
                
                # Export as MP3
                output_buffer = io.BytesIO()
                final_audio_segment.export(output_buffer, format="mp3", bitrate="128k")
                output_buffer.seek(0)
                final_audio = output_buffer.getvalue()
                
                logger.info(f"📊 Final audio size: {len(final_audio)} bytes")
                logger.info(f"📊 Final audio duration: {len(final_audio_segment)}ms")
                logger.info("✅ Audio bumpers added successfully with pydub")
                return final_audio
                
            except ImportError:
                logger.warning("⚠️ pydub not available for bumpers, using fallback concatenation")
                # Fallback to simple concatenation (may not work properly)
                final_audio = intro_audio + main_audio + outro_audio
                logger.info(f"📊 Final audio size: {len(final_audio)} bytes")
                logger.info("✅ Audio bumpers added successfully (fallback)")
                return final_audio
            
        except FileNotFoundError as e:
            logger.error(f"❌ Bumper file not found: {e}")
            logger.warning("⚠️ Returning audio without bumpers")
            return main_audio  # Return original audio if bumpers fail
        except Exception as e:
            logger.error(f"❌ Failed to add audio bumpers: {e}")
            logger.warning("⚠️ Returning audio without bumpers")
            return main_audio  # Return original audio if bumpers fail
    
    async def generate_multi_voice_audio_with_bumpers(self, script: str, job_id: str, canonical_filename: str, intro_path: str, outro_path: str) -> str:
        """Generate multi-voice audio with bumpers and upload to GCS"""
        from google.cloud import storage
        import tempfile
        import os

        # --- Start of Edit: Add script validation ---
        if not script or not script.strip():
            raise ValueError("Input script is empty or contains only whitespace. Cannot generate audio.")
        # --- End of Edit ---
        
        logger.info(f"🎵 Generating multi-voice audio with bumpers for {canonical_filename}")
        
        # Parse script into segments with different speakers
        segments = self._parse_script_segments(script)
        logger.info(f"📝 Parsed {len(segments)} script segments")
        
        if not segments:
            logger.warning("⚠️ No valid segments found, using single voice for entire script")
            # Fallback to single voice
            clean_script = self._preprocess_text_for_natural_speech(script)
            voice_config = self.voice_configs['host']
            audio_data, duration = await self._synthesize_segment(clean_script, voice_config)
        else:
            # Generate audio for each segment with appropriate voice
            audio_segments = []
            total_duration = 0.0
            
            for i, segment in enumerate(segments):
                speaker_role = segment['speaker']
                content = segment['content']
                
                # Get voice config for this speaker
                voice_config = self.voice_configs.get(speaker_role, self.voice_configs['host'])
                logger.info(f"🔊 Segment {i+1}: {voice_config.speaker_name} ({speaker_role}) - {len(content)} chars")
                
                try:
                    audio_data, duration = await self._synthesize_segment(content, voice_config)
                    audio_segments.append(audio_data)
                    total_duration += duration
                    logger.info(f"✅ Segment {i+1} generated: {duration:.1f}s")
                except Exception as e:
                    logger.error(f"❌ Failed to generate segment {i+1}: {e}")
                    # Continue with other segments
                    continue
            
            if not audio_segments:
                raise Exception("No audio segments were generated successfully")
            
            # Combine all audio segments
            audio_data = await self._combine_audio_segments(audio_segments)
            logger.info(f"✅ Combined {len(audio_segments)} segments: {total_duration:.1f}s total")
        
        # Add bumpers to the audio
        audio_with_bumpers = await self.add_audio_bumpers(
            audio_data, intro_path, outro_path
        )
        
        # Upload to GCS
        client = storage.Client()
        bucket = client.bucket("regal-scholar-453620-r7-podcast-storage")
        
        # Create temporary file
        with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as temp_file:
            temp_file.write(audio_with_bumpers)
            temp_path = temp_file.name
        
        try:
            # Upload to GCS
            blob_name = f"audio/{canonical_filename}.mp3"
            blob = bucket.blob(blob_name)
            blob.upload_from_filename(temp_path, content_type="audio/mpeg")
            blob.make_public()
            
            logger.info(f"✅ Multi-voice audio with bumpers uploaded: {blob.public_url}")
            return blob.public_url
            
        finally:
            # Clean up temp file
            if os.path.exists(temp_path):
                os.unlink(temp_path)
