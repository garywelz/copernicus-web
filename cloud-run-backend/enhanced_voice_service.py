"""
Enhanced Voice Service - Production Quality
Integrates sophisticated voice management patterns from legacy architecture:
- Per-speaker voice configurations with speed/stability control
- Duration targeting and pause management
- Multi-voice synthesis with character consistency
- Audio segment assembly and timing control
"""

import asyncio
import os
import tempfile
import wave
import io
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass
from google.cloud import texttospeech
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class VoiceConfig:
    """Voice configuration following legacy architecture patterns"""
    voice_id: str
    language_code: str = "en-US"
    speed: float = 1.0
    pitch: float = 0.0
    volume_gain_db: float = 0.0
    stability: float = 0.7  # Legacy ElevenLabs compatibility
    similarity_boost: float = 0.7  # Legacy ElevenLabs compatibility
    style: float = 0.5  # Legacy ElevenLabs compatibility
    use_speaker_boost: bool = True  # Legacy ElevenLabs compatibility

@dataclass
class AudioSegment:
    """Audio segment with metadata"""
    audio_data: bytes
    duration_seconds: float
    speaker: str
    content: str
    voice_config: VoiceConfig

@dataclass
class SynthesisResult:
    """Complete synthesis result with metadata"""
    audio_data: bytes
    total_duration: float
    segments: List[AudioSegment]
    speakers_used: List[str]
    estimated_vs_actual_duration: Dict[str, float]

class EnhancedVoiceService:
    """
    Production-quality voice service with sophisticated voice management
    """
    
    def __init__(self):
        # Initialize Google Cloud TTS client
        try:
            self.tts_client = texttospeech.TextToSpeechClient()
            logger.info("✅ Google Cloud TTS client initialized")
        except Exception as e:
            logger.error(f"❌ Failed to initialize Google Cloud TTS: {e}")
            self.tts_client = None
        
        # Production voice configurations (legacy architecture pattern)
        self.voice_configs = {
            "host": VoiceConfig(
                voice_id="en-US-Neural2-J",  # Professional female
                speed=1.0,
                pitch=0.0,
                volume_gain_db=2.0,
                stability=0.8,
                similarity_boost=0.7,
                style=0.6
            ),
            "expert": VoiceConfig(
                voice_id="en-US-Neural2-D",  # Authoritative male
                speed=0.95,
                pitch=-2.0,
                volume_gain_db=1.0,
                stability=0.75,
                similarity_boost=0.8,
                style=0.7
            ),
            "questioner": VoiceConfig(
                voice_id="en-US-Neural2-A",  # Curious female
                speed=1.05,
                pitch=1.0,
                volume_gain_db=0.0,
                stability=0.7,
                similarity_boost=0.75,
                style=0.5
            ),
            "narrator": VoiceConfig(
                voice_id="en-US-Neural2-C",  # Neutral male narrator
                speed=0.9,
                pitch=-1.0,
                volume_gain_db=1.5,
                stability=0.85,
                similarity_boost=0.8,
                style=0.8
            )
        }
        
        # Audio processing settings
        self.sample_rate = 24000
        self.audio_encoding = texttospeech.AudioEncoding.LINEAR16
        
        # Duration estimation (words per minute by speaker type)
        self.wpm_by_speaker = {
            "host": 160,  # Professional pace
            "expert": 140,  # Thoughtful pace
            "questioner": 170,  # Curious pace
            "narrator": 150   # Steady pace
        }

    async def synthesize_script_segments(
        self, 
        script_segments: List[Dict[str, str]], 
        target_duration_seconds: int = None,
        voice_style: str = "professional"
    ) -> SynthesisResult:
        """
        Synthesize pre-segmented script with proper multi-voice handling
        """
        logger.info(f"🎙️ Starting multi-voice synthesis with {len(script_segments)} segments")
        
        # Apply duration targeting if specified
        if target_duration_seconds:
            script_segments = self._apply_duration_targeting_to_segments(script_segments, target_duration_seconds)
        
        # Process segments directly (no parsing needed)
        audio_segments = []
        total_duration = 0.0
        estimated_vs_actual = {"estimated": 0.0, "actual": 0.0}
        
        for i, segment in enumerate(script_segments):
            logger.info(f"🔊 Synthesizing segment {i+1}/{len(script_segments)} ({segment['speaker']})")
            
            # Get voice config for speaker
            voice_config = self.voice_configs.get(segment["speaker"], self.voice_configs["host"])
            
            # Estimate duration
            estimated_duration = self._estimate_segment_duration(segment["content"], segment["speaker"])
            estimated_vs_actual["estimated"] += estimated_duration
            
            # Synthesize audio (content is already clean, no speaker labels)
            audio_data, actual_duration = await self._synthesize_segment(
                segment["content"], 
                voice_config,
                segment.get("pause_after", False)
            )
            
            # Create audio segment object
            audio_segment = AudioSegment(
                audio_data=audio_data,
                duration_seconds=actual_duration,
                speaker=segment["speaker"],
                content=segment["content"],
                voice_config=voice_config
            )
            
            audio_segments.append(audio_segment)
            total_duration += actual_duration
            estimated_vs_actual["actual"] += actual_duration
            
            logger.info(f"✅ Segment complete: {actual_duration:.1f}s (estimated: {estimated_duration:.1f}s)")
        
        # Combine all audio segments
        logger.info("🔗 Combining audio segments...")
        combined_audio = await self._combine_audio_segments(audio_segments)
        
        # Log final results
        speakers_used = list(set(seg.speaker for seg in audio_segments))
        logger.info(f"🎯 Synthesis complete:")
        logger.info(f"   Total duration: {total_duration:.1f}s")
        logger.info(f"   Speakers used: {', '.join(speakers_used)}")
        logger.info(f"   Accuracy: {(estimated_vs_actual['actual']/estimated_vs_actual['estimated']*100):.1f}%")
        
        return SynthesisResult(
            audio_data=combined_audio,
            total_duration=total_duration,
            segments=audio_segments,
            speakers_used=speakers_used,
            estimated_vs_actual_duration=estimated_vs_actual
        )

    async def synthesize_multi_voice_script(
        self, 
        script_content: str, 
        target_duration_seconds: int = None,
        voice_style: str = "professional"
    ) -> SynthesisResult:
        """
        Synthesize multi-voice script with duration targeting (legacy pattern)
        """
        logger.info(f"🎙️ Starting multi-voice synthesis...")
        logger.info(f"📝 Script length: {len(script_content)} characters")
        
        if not self.tts_client:
            raise Exception("Google Cloud TTS client not available")
        
        # Parse script into segments
        segments = self._parse_script_to_segments(script_content)
        logger.info(f"🗣️ Parsed {len(segments)} voice segments")
        
        # Apply duration targeting if specified
        if target_duration_seconds:
            segments = self._apply_duration_targeting(segments, target_duration_seconds)
        
        # Synthesize each segment
        audio_segments = []
        total_duration = 0.0
        estimated_vs_actual = {"estimated": 0.0, "actual": 0.0}
        
        for i, segment in enumerate(segments):
            logger.info(f"🔊 Synthesizing segment {i+1}/{len(segments)} ({segment['speaker']})")
            
            # Get voice config for speaker
            voice_config = self.voice_configs.get(segment["speaker"], self.voice_configs["host"])
            
            # Estimate duration
            estimated_duration = self._estimate_segment_duration(segment["content"], segment["speaker"])
            estimated_vs_actual["estimated"] += estimated_duration
            
            # Synthesize audio
            audio_data, actual_duration = await self._synthesize_segment(
                segment["content"], 
                voice_config,
                segment.get("pause_after", False)
            )
            
            # Create audio segment object
            audio_segment = AudioSegment(
                audio_data=audio_data,
                duration_seconds=actual_duration,
                speaker=segment["speaker"],
                content=segment["content"],
                voice_config=voice_config
            )
            
            audio_segments.append(audio_segment)
            total_duration += actual_duration
            estimated_vs_actual["actual"] += actual_duration
            
            logger.info(f"✅ Segment complete: {actual_duration:.1f}s (estimated: {estimated_duration:.1f}s)")
        
        # Combine all audio segments
        logger.info("🔗 Combining audio segments...")
        combined_audio = await self._combine_audio_segments(audio_segments)
        
        # Log final results
        speakers_used = list(set(seg.speaker for seg in audio_segments))
        logger.info(f"🎯 Synthesis complete:")
        logger.info(f"   Total duration: {total_duration:.1f}s")
        logger.info(f"   Speakers used: {', '.join(speakers_used)}")
        logger.info(f"   Accuracy: {(estimated_vs_actual['actual']/estimated_vs_actual['estimated']*100):.1f}%")
        
        return SynthesisResult(
            audio_data=combined_audio,
            total_duration=total_duration,
            segments=audio_segments,
            speakers_used=speakers_used,
            estimated_vs_actual_duration=estimated_vs_actual
        )

    def _parse_script_to_segments(self, script_content: str) -> List[Dict[str, Any]]:
        """
        Parse script into speaker segments (legacy pattern)
        """
        segments = []
        lines = script_content.split('\n')
        
        current_speaker = "host"  # Default speaker
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
            
            # Check for speaker labels (HOST:, EXPERT:, etc.)
            if ':' in line and len(line.split(':', 1)[0].strip()) < 20:
                speaker_part, content = line.split(':', 1)
                speaker_label = speaker_part.strip().upper()
                content = content.strip()
                
                # Map speaker labels to voice configs
                speaker_mapping = {
                    'HOST': 'host',
                    'INTERVIEWER': 'host',
                    'MODERATOR': 'host',
                    'EXPERT': 'expert',
                    'RESEARCHER': 'expert',
                    'SCIENTIST': 'expert',
                    'PROFESSOR': 'expert',
                    'QUESTIONER': 'questioner',
                    'STUDENT': 'questioner',
                    'CURIOUS': 'questioner',
                    'NARRATOR': 'narrator',
                    'VOICE': 'narrator'
                }
                
                current_speaker = speaker_mapping.get(speaker_label, 'host')
                
                if content:  # Only add if there's actual content
                    segments.append({
                        "speaker": current_speaker,
                        "content": content,
                        "pause_after": False
                    })
            else:
                # Continue with current speaker
                segments.append({
                    "speaker": current_speaker,
                    "content": line,
                    "pause_after": False
                })
        
        # Add strategic pauses (legacy pattern)
        for i, segment in enumerate(segments):
            # Add pause after questions
            if '?' in segment["content"]:
                segment["pause_after"] = True
            
            # Add pause between different speakers
            if i < len(segments) - 1 and segments[i+1]["speaker"] != segment["speaker"]:
                segment["pause_after"] = True
        
        return segments

    def _apply_duration_targeting(
        self, 
        segments: List[Dict[str, Any]], 
        target_duration: int
    ) -> List[Dict[str, Any]]:
        """
        Apply duration targeting by adjusting speech speed (legacy pattern)
        """
        # Estimate total duration with current settings
        total_estimated = sum(
            self._estimate_segment_duration(seg["content"], seg["speaker"]) 
            for seg in segments
        )
        
        # Calculate speed adjustment factor
        speed_factor = total_estimated / target_duration
        
        # Clamp speed factor to reasonable range (0.7x to 1.3x)
        speed_factor = max(0.7, min(1.3, speed_factor))
        
        logger.info(f"🎯 Duration targeting: {total_estimated:.1f}s → {target_duration}s (speed: {speed_factor:.2f}x)")
        
        # Apply speed adjustment to voice configs
        for speaker in self.voice_configs:
            original_speed = self.voice_configs[speaker].speed
            self.voice_configs[speaker].speed = original_speed * speed_factor
        
        return segments

    def _apply_duration_targeting_to_segments(
        self, 
        segments: List[Dict[str, str]], 
        target_duration: int
    ) -> List[Dict[str, str]]:
        """
        Apply duration targeting by adjusting speech speed for segments
        """
        # Estimate total duration with current settings
        total_estimated = sum(
            self._estimate_segment_duration(seg["content"], seg["speaker"]) 
            for seg in segments
        )
        
        # Calculate speed adjustment factor
        speed_factor = total_estimated / target_duration
        
        # Clamp speed factor to reasonable range (0.7x to 1.3x)
        speed_factor = max(0.7, min(1.3, speed_factor))
        
        logger.info(f"🎯 Duration targeting: {total_estimated:.1f}s → {target_duration}s (speed: {speed_factor:.2f}x)")
        
        # Apply speed adjustment to voice configs
        for speaker in self.voice_configs:
            original_speed = self.voice_configs[speaker].speed
            self.voice_configs[speaker].speed = original_speed * speed_factor
        
        return segments

    def _estimate_segment_duration(self, content: str, speaker: str) -> float:
        """
        Estimate segment duration based on content and speaker (legacy pattern)
        """
        word_count = len(content.split())
        wpm = self.wpm_by_speaker.get(speaker, 150)
        
        # Adjust for punctuation (pauses)
        pause_count = content.count('.') + content.count(',') + content.count('?') + content.count('!')
        pause_time = pause_count * 0.3  # 300ms per punctuation mark
        
        base_duration = (word_count / wpm) * 60  # Convert to seconds
        return base_duration + pause_time

    async def _synthesize_segment(
        self,
        content: str,
        voice_config: VoiceConfig,
        add_pause: bool = False
    ) -> Tuple[bytes, float]:
        """
        Synthesize individual segment with voice configuration
        """
        # Preprocess text for TTS (remove markup, clean formatting)
        clean_content = self._preprocess_text_for_tts(content)
        
        # Configure synthesis input
        synthesis_input = texttospeech.SynthesisInput(text=clean_content)
        
        # Configure voice
        voice = texttospeech.VoiceSelectionParams(
            language_code=voice_config.language_code,
            name=voice_config.voice_id
        )
        
        # Configure audio with voice-specific settings
        audio_config = texttospeech.AudioConfig(
            audio_encoding=self.audio_encoding,
            sample_rate_hertz=self.sample_rate,
            speaking_rate=voice_config.speed,
            pitch=voice_config.pitch,
            volume_gain_db=voice_config.volume_gain_db
        )
        
        try:
            # Perform synthesis
            response = self.tts_client.synthesize_speech(
                input=synthesis_input,
                voice=voice,
                audio_config=audio_config
            )
            
            audio_data = response.audio_content
            
            # Calculate actual duration from audio data
            duration = self._calculate_audio_duration(audio_data)
            
            # Add pause if requested
            if add_pause:
                pause_audio = self._generate_silence(0.5)  # 500ms pause
                audio_data += pause_audio
                duration += 0.5
            
            return audio_data, duration
            
        except Exception as e:
            logger.error(f"❌ TTS synthesis error: {e}")
            # Return silence as fallback
            silence_duration = 2.0
            silence_audio = self._generate_silence(silence_duration)
            return silence_audio, silence_duration

    def _preprocess_text_for_tts(self, text: str) -> str:
        """
        Preprocess text for TTS to avoid reading markup aloud (legacy fix)
        """
        # Remove speaker labels that might have been missed
        text = text.strip()
        
        # Remove common markup patterns
        import re
        
        # Remove markdown formatting
        text = re.sub(r'\*\*(.*?)\*\*', r'\1', text)  # **bold**
        text = re.sub(r'\*(.*?)\*', r'\1', text)      # *italic*
        text = re.sub(r'__(.*?)__', r'\1', text)      # __underline__
        
        # Remove academic titles and formal designations
        text = re.sub(r'\b(Dr\.|Professor|PhD|Ph\.D\.)\s+', '', text)
        
        # Remove JSON artifacts
        text = re.sub(r'[{}"\[\]]', '', text)
        
        # Clean up extra whitespace
        text = re.sub(r'\s+', ' ', text).strip()
        
        return text

    def _calculate_audio_duration(self, audio_data: bytes) -> float:
        """
        Calculate duration of audio data
        """
        try:
            # For LINEAR16 encoding at 24kHz
            bytes_per_sample = 2  # 16-bit = 2 bytes
            samples = len(audio_data) // bytes_per_sample
            duration = samples / self.sample_rate
            return duration
        except:
            # Fallback estimation
            return len(audio_data) / (self.sample_rate * 2)  # Rough estimate

    def _generate_silence(self, duration_seconds: float) -> bytes:
        """
        Generate silence audio data
        """
        num_samples = int(duration_seconds * self.sample_rate)
        silence_data = b'\x00' * (num_samples * 2)  # 2 bytes per sample for 16-bit
        return silence_data

    async def _combine_audio_segments(self, segments: List[AudioSegment]) -> bytes:
        """
        Combine multiple audio segments into single audio file
        """
        if not segments:
            return b''
        
        # Simply concatenate audio data for LINEAR16 format
        combined_audio = b''
        for segment in segments:
            combined_audio += segment.audio_data
        
        return combined_audio

    def get_voice_info(self) -> Dict[str, Any]:
        """
        Get information about available voices and configurations
        """
        return {
            "available_speakers": list(self.voice_configs.keys()),
            "voice_configs": {
                speaker: {
                    "voice_id": config.voice_id,
                    "language": config.language_code,
                    "speed": config.speed,
                    "pitch": config.pitch,
                    "characteristics": self._get_voice_characteristics(speaker)
                }
                for speaker, config in self.voice_configs.items()
            },
            "audio_settings": {
                "sample_rate": self.sample_rate,
                "encoding": "LINEAR16",
                "quality": "Neural2 (High Quality)"
            }
        }

    def _get_voice_characteristics(self, speaker: str) -> str:
        """
        Get human-readable voice characteristics
        """
        characteristics = {
            "host": "Professional, warm, engaging female voice",
            "expert": "Authoritative, confident male voice with technical expertise",
            "questioner": "Curious, energetic female voice with inquisitive tone",
            "narrator": "Neutral, clear male voice for explanations and transitions"
        }
        return characteristics.get(speaker, "Standard conversational voice")

    def update_voice_config(self, speaker: str, config_updates: Dict[str, Any]) -> bool:
        """
        Update voice configuration for a speaker
        """
        if speaker not in self.voice_configs:
            return False
        
        config = self.voice_configs[speaker]
        
        # Update allowed parameters
        if "speed" in config_updates:
            config.speed = max(0.5, min(2.0, config_updates["speed"]))
        if "pitch" in config_updates:
            config.pitch = max(-20.0, min(20.0, config_updates["pitch"]))
        if "volume_gain_db" in config_updates:
            config.volume_gain_db = max(-10.0, min(10.0, config_updates["volume_gain_db"]))
        
        logger.info(f"✅ Updated voice config for {speaker}")
        return True

    async def test_voice_synthesis(self, speaker: str = "host") -> Dict[str, Any]:
        """
        Test voice synthesis for a specific speaker
        """
        test_text = f"Hello, this is a test of the {speaker} voice configuration for Copernicus AI podcasts."
        
        try:
            voice_config = self.voice_configs.get(speaker, self.voice_configs["host"])
            audio_data, duration = await self._synthesize_segment(test_text, voice_config)
            
            return {
                "success": True,
                "speaker": speaker,
                "duration": duration,
                "audio_size": len(audio_data),
                "voice_config": {
                    "voice_id": voice_config.voice_id,
                    "speed": voice_config.speed,
                    "pitch": voice_config.pitch
                }
            }
        except Exception as e:
            return {
                "success": False,
                "speaker": speaker,
                "error": str(e)
            }
