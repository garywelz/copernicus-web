import asyncio
import aiohttp
import json
import os
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime
import tempfile
import base64
from pathlib import Path

from research_pipeline import ResearchSource

class EnhancedPodcastGenerator:
    """
    Enhanced podcast generator with multi-LLM support and comprehensive research integration
    """
    
    def __init__(self):
        # API keys
        self.openai_api_key = os.getenv("OPENAI_API_KEY")
        self.openrouter_api_key = os.getenv("OPENROUTER_API_KEY")
        self.elevenlabs_api_key = os.getenv("ELEVENLABS_API_KEY")
        self.google_api_key = os.getenv("GOOGLE_API_KEY")
        
        # API endpoints
        self.endpoints = {
            "openai": "https://api.openai.com/v1/chat/completions",
            "openrouter": "https://openrouter.ai/api/v1/chat/completions",
            "elevenlabs": "https://api.elevenlabs.io/v1/text-to-speech",
            "dalle": "https://api.openai.com/v1/images/generations"
        }
        
        # LLM model configurations
        self.models = {
            "openai": {
                "gpt-4": "gpt-4-turbo-preview",
                "gpt-3.5": "gpt-3.5-turbo"
            },
            "claude": {
                "sonnet": "anthropic/claude-3-sonnet-20240229",
                "haiku": "anthropic/claude-3-haiku-20240307"
            },
            "gemini": {
                "pro": "google/gemini-pro",
                "flash": "google/gemini-1.5-flash"
            }
        }
        
        # Voice configurations for multi-speaker podcasts
        self.voices = {
            "host": "EXAVITQu4vr4xnSDxMaL",  # Sarah - Main host
            "expert": "21m00Tcm4TlvDq8ikWAM",  # Rachel - Expert voice
            "questioner": "AZnzlk1XvdvUeBnXmlld",  # Domi - Curious questioner
            "narrator": "pNInz6obpgDQGcFmaJgB",  # Adam - Narrator
        }
        
        # Copernicus character configuration
        self.character_config = {
            "name": "Copernicus AI",
            "personality": "Revolutionary scientific thinker focused on paradigm-shifting research",
            "approach": "Bridge cutting-edge discoveries with practical understanding",
            "style": "Engaging, authoritative, accessible yet rigorous",
            "focus": "Interdisciplinary connections and transformative implications"
        }

    async def health_check(self) -> Dict[str, str]:
        """Check health of generation services"""
        health_status = {}
        
        # Check OpenAI
        try:
            async with aiohttp.ClientSession() as session:
                headers = {"Authorization": f"Bearer {self.openai_api_key}"}
                async with session.get("https://api.openai.com/v1/models", 
                                     headers=headers, timeout=5) as response:
                    health_status["openai"] = "healthy" if response.status == 200 else "degraded"
        except:
            health_status["openai"] = "unavailable"
        
        # Check ElevenLabs
        try:
            async with aiohttp.ClientSession() as session:
                headers = {"xi-api-key": self.elevenlabs_api_key}
                async with session.get("https://api.elevenlabs.io/v1/voices", 
                                     headers=headers, timeout=5) as response:
                    health_status["elevenlabs"] = "healthy" if response.status == 200 else "degraded"
        except:
            health_status["elevenlabs"] = "unavailable"
        
        # Check OpenRouter
        try:
            async with aiohttp.ClientSession() as session:
                headers = {"Authorization": f"Bearer {self.openrouter_api_key}"}
                async with session.get("https://openrouter.ai/api/v1/models", 
                                     headers=headers, timeout=5) as response:
                    health_status["openrouter"] = "healthy" if response.status == 200 else "degraded"
        except:
            health_status["openrouter"] = "unavailable"
        
        return health_status

    async def generate_comprehensive_content(
        self,
        research_data: List[ResearchSource],
        subject: str,
        duration: str,
        difficulty: str,
        speakers: str,
        llm_provider: str = "auto"
    ) -> Dict[str, Any]:
        """
        Generate comprehensive podcast content using research data and multi-LLM approach
        """
        
        # Step 1: Analyze research and create content outline
        content_outline = await self._create_content_outline(
            research_data, subject, difficulty, llm_provider
        )
        
        # Step 2: Generate detailed script
        script = await self._generate_script(
            content_outline, duration, speakers, difficulty, llm_provider
        )
        
        # Step 3: Create episode metadata
        metadata = await self._generate_metadata(
            research_data, subject, script, llm_provider
        )
        
        # Step 4: Generate description and transcript
        description = await self._generate_description(
            content_outline, research_data, subject, llm_provider
        )
        
        transcript = await self._create_transcript(script, speakers)
        
        return {
            "script": script,
            "title": metadata["title"],
            "description": description,
            "transcript": transcript,
            "metadata": metadata,
            "content_outline": content_outline,
            "research_sources": len(research_data)
        }

    async def _create_content_outline(
        self, 
        research_data: List[ResearchSource], 
        subject: str, 
        difficulty: str,
        llm_provider: str
    ) -> Dict[str, Any]:
        """Create comprehensive content outline from research data"""
        
        # Prepare research summary
        research_summary = self._prepare_research_summary(research_data)
        
        # Select best LLM for content analysis
        model = await self._select_optimal_model("content_analysis", llm_provider)
        
        prompt = f"""
        As Copernicus AI, analyze this research data and create a comprehensive podcast content outline.

        SUBJECT: {subject}
        DIFFICULTY LEVEL: {difficulty}
        
        RESEARCH DATA:
        {research_summary}
        
        Create a detailed content outline that:
        1. Identifies the most paradigm-shifting discoveries
        2. Explains complex concepts at {difficulty} level
        3. Highlights interdisciplinary connections
        4. Emphasizes transformative implications
        5. Grounds speculation in rigorous evidence
        
        Structure the outline with:
        - Hook: Revolutionary opening that captures attention
        - Context: Background and current understanding
        - Discovery: Key findings and breakthroughs
        - Analysis: Deep dive into implications
        - Connections: Links to other fields and applications
        - Future: Evidence-based speculation about developments
        - Conclusion: Transformative takeaways
        
        Return a detailed JSON outline with sections, key points, and supporting evidence.
        """
        
        response = await self._call_llm(model, prompt)
        
        try:
            return json.loads(response)
        except json.JSONDecodeError:
            # Fallback structure if JSON parsing fails
            return {
                "hook": "Revolutionary discoveries in " + subject,
                "sections": [
                    {"title": "Context", "content": "Background information"},
                    {"title": "Discovery", "content": "Key findings"},
                    {"title": "Analysis", "content": "Deep analysis"},
                    {"title": "Implications", "content": "Future implications"}
                ],
                "research_sources": len(research_data)
            }

    async def _generate_script(
        self,
        content_outline: Dict[str, Any],
        duration: str,
        speakers: str,
        difficulty: str,
        llm_provider: str
    ) -> str:
        """Generate detailed podcast script"""
        
        # Calculate target word count based on duration
        duration_minutes = self._parse_duration(duration)
        target_words = duration_minutes * 150  # ~150 words per minute for podcasts
        
        # Select best LLM for script writing
        model = await self._select_optimal_model("script_writing", llm_provider)
        
        if speakers == "multi-voice":
            return await self._generate_multi_voice_script(
                content_outline, target_words, difficulty, model
            )
        else:
            return await self._generate_single_voice_script(
                content_outline, target_words, difficulty, model
            )

    async def _generate_single_voice_script(
        self,
        content_outline: Dict[str, Any],
        target_words: int,
        difficulty: str,
        model: str
    ) -> str:
        """Generate single-voice podcast script"""
        
        prompt = f"""
        As Copernicus AI, write a compelling {target_words}-word podcast script based on this outline.

        CONTENT OUTLINE:
        {json.dumps(content_outline, indent=2)}
        
        DIFFICULTY LEVEL: {difficulty}
        TARGET LENGTH: ~{target_words} words
        
        Write in the Copernicus AI voice:
        - Revolutionary scientific thinker
        - Paradigm-shifting focus
        - Bridge complex concepts with practical understanding
        - Engaging yet rigorous
        - Emphasize interdisciplinary connections
        
        Script requirements:
        1. Compelling hook that immediately captures attention
        2. Clear explanations appropriate for {difficulty} audience
        3. Smooth transitions between concepts
        4. Specific examples and evidence from research
        5. Thought-provoking conclusions
        6. Natural speech patterns (contractions, conversational flow)
        7. Strategic pauses and emphasis markers
        
        Format: Write as natural speech, not formal text. Include [PAUSE] markers for dramatic effect.
        """
        
        return await self._call_llm(model, prompt)

    async def _generate_multi_voice_script(
        self,
        content_outline: Dict[str, Any],
        target_words: int,
        difficulty: str,
        model: str
    ) -> str:
        """Generate multi-voice conversational script"""
        
        prompt = f"""
        Create a dynamic multi-voice podcast script based on this outline.

        CONTENT OUTLINE:
        {json.dumps(content_outline, indent=2)}
        
        CHARACTERS:
        - HOST: Main narrator, guides discussion (Copernicus AI persona)
        - EXPERT: Deep technical knowledge, provides detailed explanations
        - QUESTIONER: Represents curious audience, asks clarifying questions
        
        TARGET LENGTH: ~{target_words} words
        DIFFICULTY: {difficulty}
        
        Script format:
        HOST: [dialogue]
        EXPERT: [dialogue]
        QUESTIONER: [dialogue]
        
        Requirements:
        1. Natural conversation flow with interruptions and reactions
        2. HOST introduces topics and guides transitions
        3. EXPERT provides technical depth and evidence
        4. QUESTIONER asks questions audience would have
        5. Include [PAUSE], [EMPHASIS], [EXCITED] markers for audio production
        6. Balance technical accuracy with accessibility
        7. Build excitement about discoveries and implications
        
        Make it feel like an engaging conversation between passionate scientists.
        """
        
        return await self._call_llm(model, prompt)

    async def _generate_metadata(
        self,
        research_data: List[ResearchSource],
        subject: str,
        script: str,
        llm_provider: str
    ) -> Dict[str, Any]:
        """Generate episode metadata"""
        
        model = await self._select_optimal_model("metadata_generation", llm_provider)
        
        prompt = f"""
        Generate podcast episode metadata based on this content:
        
        SUBJECT: {subject}
        SCRIPT EXCERPT: {script[:1000]}...
        RESEARCH SOURCES: {len(research_data)} academic sources
        
        Create metadata JSON with:
        - title: Compelling episode title (max 60 chars)
        - subtitle: Descriptive subtitle (max 100 chars)
        - keywords: Array of relevant keywords for discovery
        - category: Primary category (Science, Technology, Education, etc.)
        - subcategories: Array of specific subcategories
        - estimated_duration: Duration estimate in minutes
        - difficulty_level: beginner/intermediate/advanced
        - key_concepts: Array of main concepts covered
        - research_areas: Array of research fields involved
        
        Make the title intriguing and clickable while being accurate.
        """
        
        response = await self._call_llm(model, prompt)
        
        try:
            metadata = json.loads(response)
            # Add generation timestamp and source info
            metadata.update({
                "generated_at": datetime.utcnow().isoformat(),
                "research_sources_count": len(research_data),
                "generation_model": model,
                "character": "Copernicus AI"
            })
            return metadata
        except json.JSONDecodeError:
            # Fallback metadata
            return {
                "title": f"Revolutionary Insights: {subject}",
                "subtitle": "Paradigm-shifting research explained",
                "keywords": [subject.lower(), "science", "research", "discovery"],
                "category": "Science",
                "difficulty_level": "intermediate",
                "generated_at": datetime.utcnow().isoformat()
            }

    async def _generate_description(
        self,
        content_outline: Dict[str, Any],
        research_data: List[ResearchSource],
        subject: str,
        llm_provider: str
    ) -> str:
        """Generate comprehensive episode description"""
        
        model = await self._select_optimal_model("description_writing", llm_provider)
        
        # Prepare source citations
        citations = self._format_research_citations(research_data[:10])  # Top 10 sources
        
        prompt = f"""
        Write a compelling podcast episode description based on this content:
        
        SUBJECT: {subject}
        CONTENT OUTLINE: {json.dumps(content_outline, indent=2)}
        
        Write a description that:
        1. Hooks readers with the revolutionary nature of the discoveries
        2. Explains what listeners will learn (3-4 key takeaways)
        3. Emphasizes the paradigm-shifting implications
        4. Mentions the rigorous research foundation
        5. Includes a call-to-action for engagement
        
        Format as markdown with:
        - Compelling opening paragraph
        - "What You'll Discover:" section with bullet points
        - "Research Foundation:" section mentioning source count
        - "Join the Revolution:" call-to-action
        
        Keep it engaging, informative, and under 500 words.
        """
        
        description = await self._call_llm(model, prompt)
        
        # Add research citations
        description += f"\n\n## Research Sources\n\nThis episode is based on {len(research_data)} peer-reviewed sources:\n\n{citations}"
        
        return description

    async def produce_media(
        self,
        script: str,
        title: str,
        description: str,
        speakers: str,
        job_id: str
    ) -> Dict[str, str]:
        """Produce audio and visual media assets"""
        
        media_assets = {}
        
        # Generate audio
        if speakers == "multi-voice":
            audio_file = await self._generate_multi_voice_audio(script, job_id)
        else:
            audio_file = await self._generate_single_voice_audio(script, job_id)
        
        media_assets["audio"] = audio_file
        
        # Generate thumbnail
        thumbnail_file = await self._generate_thumbnail(title, description, job_id)
        media_assets["thumbnail"] = thumbnail_file
        
        return media_assets

    async def _generate_single_voice_audio(self, script: str, job_id: str) -> str:
        """Generate single-voice audio using ElevenLabs"""
        
        # Clean script for TTS
        clean_script = self._clean_script_for_tts(script)
        
        try:
            async with aiohttp.ClientSession() as session:
                headers = {
                    "xi-api-key": self.elevenlabs_api_key,
                    "Content-Type": "application/json"
                }
                
                data = {
                    "text": clean_script,
                    "voice_settings": {
                        "stability": 0.5,
                        "similarity_boost": 0.8,
                        "style": 0.2,
                        "use_speaker_boost": True
                    },
                    "model_id": "eleven_multilingual_v2"
                }
                
                voice_id = self.voices["host"]
                url = f"{self.endpoints['elevenlabs']}/{voice_id}"
                
                async with session.post(url, headers=headers, json=data) as response:
                    if response.status == 200:
                        audio_data = await response.read()
                        
                        # Save to temporary file
                        temp_dir = Path(tempfile.gettempdir())
                        audio_file = temp_dir / f"{job_id}_audio.mp3"
                        
                        with open(audio_file, "wb") as f:
                            f.write(audio_data)
                        
                        return str(audio_file)
                    else:
                        raise Exception(f"ElevenLabs API error: {response.status}")
        
        except Exception as e:
            print(f"Audio generation error: {e}")
            raise

    async def _generate_multi_voice_audio(self, script: str, job_id: str) -> str:
        """Generate multi-voice audio by combining separate voice segments"""
        
        # Parse script into speaker segments
        segments = self._parse_multi_voice_script(script)
        
        # Generate audio for each segment
        audio_segments = []
        
        for i, (speaker, text) in enumerate(segments):
            voice_id = self.voices.get(speaker.lower(), self.voices["host"])
            
            try:
                async with aiohttp.ClientSession() as session:
                    headers = {
                        "xi-api-key": self.elevenlabs_api_key,
                        "Content-Type": "application/json"
                    }
                    
                    data = {
                        "text": self._clean_script_for_tts(text),
                        "voice_settings": {
                            "stability": 0.5,
                            "similarity_boost": 0.8,
                            "style": 0.2
                        },
                        "model_id": "eleven_multilingual_v2"
                    }
                    
                    url = f"{self.endpoints['elevenlabs']}/{voice_id}"
                    
                    async with session.post(url, headers=headers, json=data) as response:
                        if response.status == 200:
                            audio_data = await response.read()
                            
                            # Save segment
                            temp_dir = Path(tempfile.gettempdir())
                            segment_file = temp_dir / f"{job_id}_segment_{i}.mp3"
                            
                            with open(segment_file, "wb") as f:
                                f.write(audio_data)
                            
                            audio_segments.append(str(segment_file))
            
            except Exception as e:
                print(f"Error generating segment {i}: {e}")
        
        # Combine audio segments (simplified - in production, use ffmpeg)
        if audio_segments:
            # For now, return the first segment
            # TODO: Implement proper audio concatenation with ffmpeg
            return audio_segments[0]
        else:
            raise Exception("No audio segments generated")

    async def _generate_thumbnail(self, title: str, description: str, job_id: str) -> str:
        """Generate episode thumbnail using DALL-E"""
        
        # Create thumbnail prompt
        prompt = f"""
        Create a professional podcast thumbnail for an episode titled "{title}".
        
        Style: Modern, scientific, visually striking
        Elements: Abstract scientific imagery, clean typography space, professional color scheme
        Mood: Innovative, authoritative, accessible
        Format: Square (1024x1024), suitable for podcast platforms
        
        The image should convey cutting-edge scientific discovery and paradigm-shifting research.
        Include visual metaphors for breakthrough thinking and revolutionary science.
        """
        
        try:
            async with aiohttp.ClientSession() as session:
                headers = {
                    "Authorization": f"Bearer {self.openai_api_key}",
                    "Content-Type": "application/json"
                }
                
                data = {
                    "model": "dall-e-3",
                    "prompt": prompt,
                    "n": 1,
                    "size": "1024x1024",
                    "quality": "standard"
                }
                
                async with session.post(self.endpoints["dalle"], 
                                      headers=headers, json=data) as response:
                    if response.status == 200:
                        result = await response.json()
                        image_url = result["data"][0]["url"]
                        
                        # Download image
                        async with session.get(image_url) as img_response:
                            if img_response.status == 200:
                                image_data = await img_response.read()
                                
                                # Save to temporary file
                                temp_dir = Path(tempfile.gettempdir())
                                thumbnail_file = temp_dir / f"{job_id}_thumbnail.jpg"
                                
                                with open(thumbnail_file, "wb") as f:
                                    f.write(image_data)
                                
                                return str(thumbnail_file)
        
        except Exception as e:
            print(f"Thumbnail generation error: {e}")
            # Return placeholder thumbnail path
            return "placeholder_thumbnail.jpg"

    # Helper methods
    
    async def _select_optimal_model(self, task_type: str, provider_preference: str) -> str:
        """Select optimal LLM model for specific task"""
        
        if provider_preference == "auto":
            # Auto-select based on task type
            task_models = {
                "content_analysis": self.models["claude"]["sonnet"],
                "script_writing": self.models["openai"]["gpt-4"],
                "metadata_generation": self.models["gemini"]["pro"],
                "description_writing": self.models["claude"]["haiku"]
            }
            return task_models.get(task_type, self.models["openai"]["gpt-4"])
        
        elif provider_preference == "openai":
            return self.models["openai"]["gpt-4"]
        elif provider_preference == "claude":
            return self.models["claude"]["sonnet"]
        elif provider_preference == "gemini":
            return self.models["gemini"]["pro"]
        else:
            return self.models["openai"]["gpt-4"]

    async def _call_llm(self, model: str, prompt: str) -> str:
        """Call appropriate LLM API"""
        
        if model.startswith("gpt"):
            return await self._call_openai(model, prompt)
        else:
            return await self._call_openrouter(model, prompt)

    async def _call_openai(self, model: str, prompt: str) -> str:
        """Call OpenAI API"""
        
        async with aiohttp.ClientSession() as session:
            headers = {
                "Authorization": f"Bearer {self.openai_api_key}",
                "Content-Type": "application/json"
            }
            
            data = {
                "model": model,
                "messages": [{"role": "user", "content": prompt}],
                "max_tokens": 4000,
                "temperature": 0.7
            }
            
            async with session.post(self.endpoints["openai"], 
                                  headers=headers, json=data) as response:
                if response.status == 200:
                    result = await response.json()
                    return result["choices"][0]["message"]["content"]
                else:
                    raise Exception(f"OpenAI API error: {response.status}")

    async def _call_openrouter(self, model: str, prompt: str) -> str:
        """Call OpenRouter API for Claude/Gemini models"""
        
        async with aiohttp.ClientSession() as session:
            headers = {
                "Authorization": f"Bearer {self.openrouter_api_key}",
                "Content-Type": "application/json"
            }
            
            data = {
                "model": model,
                "messages": [{"role": "user", "content": prompt}],
                "max_tokens": 4000,
                "temperature": 0.7
            }
            
            async with session.post(self.endpoints["openrouter"], 
                                  headers=headers, json=data) as response:
                if response.status == 200:
                    result = await response.json()
                    return result["choices"][0]["message"]["content"]
                else:
                    raise Exception(f"OpenRouter API error: {response.status}")

    def _prepare_research_summary(self, research_data: List[ResearchSource]) -> str:
        """Prepare concise research summary for LLM processing"""
        
        summary_parts = []
        
        for i, source in enumerate(research_data[:15], 1):  # Limit to top 15 sources
            summary_parts.append(f"""
            {i}. {source.title}
            Authors: {', '.join(source.authors[:3])}  # Limit authors
            Source: {source.source}
            Abstract: {source.abstract[:300]}...  # Truncate abstract
            URL: {source.url}
            """)
        
        return "\n".join(summary_parts)

    def _format_research_citations(self, research_data: List[ResearchSource]) -> str:
        """Format research citations for description"""
        
        citations = []
        for i, source in enumerate(research_data, 1):
            authors = ", ".join(source.authors[:2])  # First 2 authors
            if len(source.authors) > 2:
                authors += " et al."
            
            citation = f"{i}. {authors} - {source.title}"
            if source.doi:
                citation += f" (DOI: {source.doi})"
            
            citations.append(citation)
        
        return "\n".join(citations)

    def _parse_duration(self, duration_str: str) -> int:
        """Parse duration string to minutes"""
        
        # Extract numbers from duration string
        import re
        numbers = re.findall(r'\d+', duration_str)
        
        if numbers:
            # Take the first number or average if range
            if len(numbers) == 1:
                return int(numbers[0])
            else:
                return sum(int(n) for n in numbers) // len(numbers)
        
        return 10  # Default 10 minutes

    def _clean_script_for_tts(self, script: str) -> str:
        """Clean script for text-to-speech"""
        
        # Remove stage directions and markers
        import re
        
        # Remove markers like [PAUSE], [EMPHASIS], etc.
        script = re.sub(r'\[.*?\]', '', script)
        
        # Remove speaker labels for single voice
        script = re.sub(r'^(HOST|EXPERT|QUESTIONER):\s*', '', script, flags=re.MULTILINE)
        
        # Clean up extra whitespace
        script = re.sub(r'\n\s*\n', '\n\n', script)
        script = script.strip()
        
        return script

    def _parse_multi_voice_script(self, script: str) -> List[Tuple[str, str]]:
        """Parse multi-voice script into speaker segments"""
        
        segments = []
        current_speaker = None
        current_text = []
        
        for line in script.split('\n'):
            line = line.strip()
            if not line:
                continue
            
            # Check if line starts with speaker label
            if line.startswith(('HOST:', 'EXPERT:', 'QUESTIONER:')):
                # Save previous segment
                if current_speaker and current_text:
                    segments.append((current_speaker, ' '.join(current_text)))
                
                # Start new segment
                parts = line.split(':', 1)
                current_speaker = parts[0].strip()
                current_text = [parts[1].strip()] if len(parts) > 1 else []
            
            elif current_speaker:
                current_text.append(line)
        
        # Save final segment
        if current_speaker and current_text:
            segments.append((current_speaker, ' '.join(current_text)))
        
        return segments

    async def _create_transcript(self, script: str, speakers: str) -> str:
        """Create formatted transcript"""
        
        if speakers == "multi-voice":
            # Script is already formatted with speaker labels
            return script
        else:
            # Add timestamp markers for single voice
            lines = script.split('\n')
            transcript_lines = []
            
            for i, line in enumerate(lines):
                if line.strip():
                    # Add timestamp every few lines (simplified)
                    if i % 10 == 0:
                        minutes = i // 10
                        transcript_lines.append(f"\n[{minutes:02d}:00]")
                    transcript_lines.append(line)
            
            return '\n'.join(transcript_lines)
