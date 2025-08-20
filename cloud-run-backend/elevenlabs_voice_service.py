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
        
        # Natural speaker configurations with distinct voices
        self.voice_configs = {
            "host": ElevenLabsVoiceConfig(
                voice_id="21m00Tcm4TlvDq8ikWAM",  # Rachel - Professional female
                speaker_name="Sarah",
                voice_description="Professional host, warm and engaging",
                stability=0.7,
                similarity_boost=0.8,
                style=0.3,
                use_speaker_boost=True
            ),
            "expert": ElevenLabsVoiceConfig(
                voice_id="AZnzlk1XvdvUeBnXmlld",  # Domi - Knowledgeable male
                speaker_name="Tom",
                voice_description="Expert researcher, authoritative but approachable",
                stability=0.6,
                similarity_boost=0.9,
                style=0.5,
                use_speaker_boost=True
            ),
            "questioner": ElevenLabsVoiceConfig(
                voice_id="EXAVITQu4vr4xnSDxMaL",  # Bella - Curious female
                speaker_name="Mary",
                voice_description="Curious questioner, engaging and thoughtful",
                stability=0.5,
                similarity_boost=0.7,
                style=0.6,
                use_speaker_boost=True
            ),
            "correspondent": ElevenLabsVoiceConfig(
                voice_id="ErXwobaYiN019PkySvjV",  # Antoni - Versatile male
                speaker_name="Bob",
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
        combined_audio = await self._combine_audio_segments(audio_segments)
        
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
        text = re.sub(r'^(Sarah|Tom|Mary|Bob):\s*', '', text, flags=re.IGNORECASE)
        
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
        
        segments: List[Dict[str, str]] = []
        lines = script.split('\n')
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
                
            # Look for speaker labels (roles or first names)
            # Accept role labels: HOST:, EXPERT:, QUESTIONER:, CORRESPONDENT:
            role_match = re.match(r'^(HOST|EXPERT|QUESTIONER|CORRESPONDENT):\s*(.*)', line, re.IGNORECASE)
            # Accept common first-name labels: Sarah:, Tom:, Mary:, Bob:, Maya:, etc. (single capitalized word followed by colon)
            name_match = re.match(r'^([A-Z][a-zA-Z]+):\s*(.*)', line)

            mapped_role = None
            text = None

            if role_match:
                mapped_role = role_match.group(1).lower()
                text = role_match.group(2).strip()
            elif name_match:
                first_name = name_match.group(1).strip().lower()
                text = name_match.group(2).strip()
                # Map common speaker first names to voice roles
                name_to_role = {
                    "sarah": "host",
                    "tom": "expert",
                    "mary": "questioner",
                    "bob": "correspondent",
                    "maya": "questioner",
                    "james": "expert",
                    "susan": "host",
                }
                mapped_role = name_to_role.get(first_name, "host")

            if mapped_role and text:
                # Clean the text for natural speech
                clean_text = self._preprocess_text_for_natural_speech(text)
                if clean_text:
                    segments.append({"speaker": mapped_role, "content": clean_text})
        
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
    
    async def _combine_audio_segments(self, segments: List[AudioSegment]) -> bytes:
        """Combine audio segments into a single audio file"""
        if not segments:
            return b""
        
        if len(segments) == 1:
            return segments[0].audio_data
        
        # For now, return concatenated audio data
        # In production, you might want to use pydub or similar for proper audio mixing
        combined = b""
        for segment in segments:
            combined += segment.audio_data
        
        return combined
    
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
            
            # Combine: intro + main + outro
            final_audio = intro_audio + main_audio + outro_audio
            logger.info(f"📊 Final audio size: {len(final_audio)} bytes")
            
            logger.info("✅ Audio bumpers added successfully")
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
        """Generate single-voice audio with bumpers and upload to GCS"""
        from google.cloud import storage
        import tempfile
        import os

        # --- Start of Edit: Add script validation ---
        if not script or not script.strip():
            raise ValueError("Input script is empty or contains only whitespace. Cannot generate audio.")
        # --- End of Edit ---
        
        logger.info(f"🎵 Generating single-voice audio with bumpers for {canonical_filename}")
        
        # Clean and preprocess the entire script for natural speech
        clean_script = self._preprocess_text_for_natural_speech(script)
        
        # Generate single audio file using host voice
        logger.info(f"🔊 Generating audio for script ({len(clean_script)} characters)")
        voice_config = self.voice_configs['host']  # Use host voice for entire script
        
        try:
            audio_data, duration = await self._synthesize_segment(clean_script, voice_config)
            logger.info(f"✅ Audio generated successfully: {duration:.1f}s")
        except Exception as e:
            logger.error(f"❌ Failed to generate audio: {e}")
            raise Exception(f"TTS generation failed: {e}")
        
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
            
            logger.info(f"✅ Audio with bumpers uploaded: {blob.public_url}")
            return blob.public_url
            
        finally:
            # Clean up temp file
            if os.path.exists(temp_path):
                os.unlink(temp_path)
