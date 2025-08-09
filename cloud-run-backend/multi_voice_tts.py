"""
Multi-Voice Google Cloud TTS Integration for Character-Driven Podcasts
Supports Host, Expert, and Questioner roles with different Neural2 voices
"""

import re
import os
import tempfile
from typing import Dict, List, Tuple, Optional
from google.cloud import texttospeech
from copernicus_character import VoiceRole, get_voice_config, format_multi_voice_script
import wave
import audioop

class MultiVoiceTTS:
    """Multi-voice text-to-speech generator using Google Cloud TTS"""
    
    def __init__(self):
        """Initialize multi-voice TTS with Google Cloud TTS client"""
        self.client = texttospeech.TextToSpeechClient()
        self.voice_configs = {
            VoiceRole.HOST: get_voice_config(VoiceRole.HOST),
            VoiceRole.EXPERT: get_voice_config(VoiceRole.EXPERT), 
            VoiceRole.QUESTIONER: get_voice_config(VoiceRole.QUESTIONER)
        }
    
    def preprocess_text_for_tts(self, text: str) -> str:
        """Comprehensive text preprocessing for TTS following established workflow"""
        import re
        
        # Remove JSON formatting if present
        if text.strip().startswith('```json') and text.strip().endswith('```'):
            # Extract content between ```json and ```
            json_match = re.search(r'```json\s*\n(.*)\n```', text, re.DOTALL)
            if json_match:
                import json
                try:
                    json_content = json.loads(json_match.group(1))
                    if 'script' in json_content:
                        text = json_content['script']
                except:
                    pass
        
        lines = text.split('\n')
        processed = []
        
        for line in lines:
            stripped = line.strip()
            if not stripped:
                continue
                
            # Skip speaker labels and formatting markers
            if any(stripped.upper().startswith(label) for label in ['HOST:', 'EXPERT:', 'QUESTIONER:', '**TITLE:**', '**', 'HOST -', 'EXPERT -', 'QUESTIONER -']):
                # Extract text after the speaker label
                for label in ['HOST:', 'EXPERT:', 'QUESTIONER:']:
                    if stripped.upper().startswith(label.upper()):
                        content = stripped[len(label):].strip()
                        if content:
                            processed.append(content)
                        break
                continue
            
            # Remove markdown formatting and other symbols
            clean = stripped.replace('**', '').replace('*', '').replace('```', '')
            clean = clean.replace('json', '').replace('{', '').replace('}', '')
            clean = clean.replace('"title":', '').replace('"script":', '').replace('"description":', '')
            clean = re.sub(r'\\n', ' ', clean)  # Replace \n with space
            clean = re.sub(r'\\', '', clean)    # Remove backslashes
            clean = re.sub(r'[{}\[\]"\\]', '', clean)  # Remove JSON characters
            
            # Remove academic titles and honorifics
            clean = re.sub(r'\bDr\.?\s+', '', clean, flags=re.IGNORECASE)
            clean = re.sub(r'\bProfessor\s+', '', clean, flags=re.IGNORECASE)
            clean = re.sub(r'\bPhD\b', '', clean, flags=re.IGNORECASE)
            clean = re.sub(r'\bMD\b', '', clean, flags=re.IGNORECASE)
            
            # Remove remaining markdown and formatting
            clean = re.sub(r'\*\*', '', clean)  # Bold markdown
            clean = re.sub(r'\*', '', clean)    # Italic markdown
            clean = re.sub(r'`', '', clean)     # Code markdown
            clean = re.sub(r'\\"', '"', clean)  # Escaped quotes
            clean = re.sub(r'\\.', '', clean)   # Other escaped characters
            
            # Skip lines that are mostly formatting
            if len(clean.strip()) > 3 and not clean.strip().startswith('(') and not clean.strip().endswith(')'):
                processed.append(clean.strip())
        
        # Join with proper spacing and clean up
        result = ' '.join(processed)
        result = re.sub(r'\s+', ' ', result)  # Normalize whitespace
        result = result.strip()
        
        return result
    
    def parse_script_segments(self, script: str) -> List[Tuple[VoiceRole, str]]:
        """Parse script into voice role segments"""
        
        # Format script with voice markers if needed
        formatted_script = format_multi_voice_script(script)
        
        segments = []
        current_role = VoiceRole.HOST  # Default role
        
        # Split by voice role markers
        lines = formatted_script.split('\n')
        current_text = []
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
                
            # Check for role markers
            if line.startswith('HOST:'):
                if current_text:
                    segments.append((current_role, ' '.join(current_text)))
                    current_text = []
                current_role = VoiceRole.HOST
                text = line[5:].strip()  # Remove "HOST:" prefix
                if text:
                    current_text.append(text)
                    
            elif line.startswith('EXPERT:'):
                if current_text:
                    segments.append((current_role, ' '.join(current_text)))
                    current_text = []
                current_role = VoiceRole.EXPERT
                text = line[7:].strip()  # Remove "EXPERT:" prefix
                if text:
                    current_text.append(text)
                    
            elif line.startswith('QUESTIONER:'):
                if current_text:
                    segments.append((current_role, ' '.join(current_text)))
                    current_text = []
                current_role = VoiceRole.QUESTIONER
                text = line[11:].strip()  # Remove "QUESTIONER:" prefix
                if text:
                    current_text.append(text)
                    
            else:
                # Continue with current role
                current_text.append(line)
        
        # Add final segment
        if current_text:
            segments.append((current_role, ' '.join(current_text)))
        
        return segments
    
    def generate_voice_segment(self, text: str, role: VoiceRole) -> bytes:
        """Generate audio for a single voice segment"""
        
        voice_config = self.voice_configs[role]
        
        # Comprehensive text preprocessing following established workflow
        clean_text = self.preprocess_text_for_tts(text)
        if len(clean_text.encode('utf-8')) > 4800:  # Google TTS byte limit with buffer
            # Truncate by bytes, then decode back to string
            truncated_bytes = clean_text.encode('utf-8')[:4800]
            while len(truncated_bytes) > 0:
                try:
                    clean_text = truncated_bytes.decode('utf-8') + "..."
                    break
                except UnicodeDecodeError:
                    truncated_bytes = truncated_bytes[:-1]
        
        # Set up the input text
        synthesis_input = texttospeech.SynthesisInput(text=clean_text)
        
        # Build the voice request
        voice = texttospeech.VoiceSelectionParams(
            language_code=voice_config.language_code,
            name=voice_config.name,
            ssml_gender=getattr(texttospeech.SsmlVoiceGender, voice_config.ssml_gender)
        )
        
        # Select the type of audio file
        audio_config = texttospeech.AudioConfig(
            audio_encoding=texttospeech.AudioEncoding.LINEAR16,  # WAV format for concatenation
            speaking_rate=voice_config.speaking_rate,
            pitch=voice_config.pitch
        )
        
        # Perform the text-to-speech request
        response = self.client.synthesize_speech(
            input=synthesis_input,
            voice=voice,
            audio_config=audio_config
        )
        
        return response.audio_content
    
    def concatenate_audio_segments(self, audio_segments: List[bytes]) -> bytes:
        """Concatenate multiple audio segments into a single audio file"""
        
        if not audio_segments:
            return b""
        
        if len(audio_segments) == 1:
            return audio_segments[0]
        
        # Use temporary files for audio processing
        temp_files = []
        
        try:
            # Write each segment to a temporary WAV file
            for i, segment in enumerate(audio_segments):
                temp_file = tempfile.NamedTemporaryFile(suffix=f"_segment_{i}.wav", delete=False)
                temp_file.write(segment)
                temp_file.close()
                temp_files.append(temp_file.name)
            
            # Concatenate using wave module
            output_file = tempfile.NamedTemporaryFile(suffix="_combined.wav", delete=False)
            output_file.close()
            
            with wave.open(output_file.name, 'wb') as output_wave:
                for i, temp_file in enumerate(temp_files):
                    with wave.open(temp_file, 'rb') as input_wave:
                        if i == 0:
                            # Set parameters from first file
                            output_wave.setparams(input_wave.getparams())
                        
                        # Read and write audio data
                        frames = input_wave.readframes(input_wave.getnframes())
                        output_wave.writeframes(frames)
                        
                        # Add small pause between segments (0.5 seconds)
                        if i < len(temp_files) - 1:
                            silence_frames = int(0.5 * input_wave.getframerate())
                            silence = b'\x00' * (silence_frames * input_wave.getnchannels() * input_wave.getsampwidth())
                            output_wave.writeframes(silence)
            
            # Read the combined audio
            with open(output_file.name, 'rb') as f:
                combined_audio = f.read()
            
            # Clean up temporary files
            for temp_file in temp_files:
                try:
                    os.unlink(temp_file)
                except:
                    pass
            
            try:
                os.unlink(output_file.name)
            except:
                pass
            
            return combined_audio
            
        except Exception as e:
            print(f"❌ Error concatenating audio segments: {e}")
            # Fallback: return first segment
            return audio_segments[0] if audio_segments else b""
    
    def convert_wav_to_mp3(self, wav_data: bytes, output_path: str, canonical_filename: str = None) -> str:
        """Convert WAV data and upload to Google Cloud Storage with canonical naming"""
        
        try:
            from google.cloud import storage
            from datetime import datetime
            
            # Initialize GCS client
            storage_client = storage.Client()
            bucket = storage_client.bucket("regal-scholar-453620-r7-podcast-storage")
            
            # Use canonical filename if provided, otherwise fallback to timestamp
            if canonical_filename:
                filename = f"{canonical_filename}.mp3"
            else:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                job_id = output_path.split('_')[-1].replace('.wav', '').replace('.mp3', '')
                filename = f"research-{job_id[:8]}-{timestamp}.mp3"
            
            blob = bucket.blob(f"audio/{filename}")
            
            # Upload audio data to GCS
            blob.upload_from_string(wav_data, content_type="audio/wav")
            
            # Make blob publicly accessible
            blob.make_public()
            
            # Return public URL
            public_url = f"https://storage.googleapis.com/regal-scholar-453620-r7-podcast-storage/audio/{filename}"
            print(f"🎵 Multi-voice audio uploaded to GCS: {public_url}")
            return public_url
            
        except Exception as e:
            print(f"❌ Error uploading to GCS: {e}")
            # Fallback: save locally
            wav_path = output_path.replace('.mp3', '.wav')
            with open(wav_path, 'wb') as f:
                f.write(wav_data)
            print(f"🎵 Multi-voice audio saved locally as fallback: {wav_path}")
            return f"file://{wav_path}"
    
    async def generate_multi_voice_audio(self, script: str, job_id: str, canonical_filename: str = None) -> str:
        """Generate multi-voice audio from script with canonical naming"""
        
        try:
            print(f"🎭 Generating multi-voice audio for job {job_id}")
            
            # Parse script into voice segments
            segments = self.parse_script_segments(script)
            print(f"🎯 Parsed {len(segments)} voice segments")
            
            # Generate audio for each segment
            audio_segments = []
            for i, (role, text) in enumerate(segments):
                print(f"🎙️ Generating {role.value} segment {i+1}/{len(segments)}")
                audio_data = self.generate_voice_segment(text, role)
                audio_segments.append(audio_data)
            
            # Concatenate all segments
            print(f"🔗 Concatenating {len(audio_segments)} audio segments")
            combined_audio = self.concatenate_audio_segments(audio_segments)
            
            # Save to file
            audio_filename = f"/tmp/podcast_multivoice_{job_id[:8]}.mp3"
            audio_url = self.convert_wav_to_mp3(combined_audio, audio_filename, canonical_filename)
            
            print(f"✅ Multi-voice audio generated: {audio_url}")
            return audio_url
            
        except Exception as e:
            print(f"❌ Multi-voice audio generation failed: {e}")
            # Fallback to single voice
            return await self.generate_single_voice_fallback(script, job_id)
    
    async def generate_single_voice_fallback(self, script: str, job_id: str) -> str:
        """Fallback to single voice generation"""
        
        print(f"⚠️ Using single voice fallback for job {job_id}")
        
        # Use HOST voice as fallback
        host_config = self.voice_configs[VoiceRole.HOST]
        
        # Clean script (remove role markers)
        clean_script = re.sub(r'^(HOST|EXPERT|QUESTIONER):\s*', '', script, flags=re.MULTILINE)
        clean_script = clean_script.replace("**", "").replace("*", "").strip()
        
        if len(clean_script) > 5000:
            clean_script = clean_script[:5000] + "..."
        
        # Generate single voice audio
        audio_data = self.generate_voice_segment(clean_script, VoiceRole.HOST)
        
        # Save to file
        audio_filename = f"/tmp/podcast_single_{job_id[:8]}.wav"
        with open(audio_filename, 'wb') as f:
            f.write(audio_data)
        
        print(f"✅ Single voice fallback audio generated: {audio_filename}")
        return f"file://{audio_filename}"

# Global instance
multi_voice_tts = MultiVoiceTTS()
