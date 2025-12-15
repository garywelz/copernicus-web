"""
Podcast Generation Service

This service handles all podcast generation logic including:
- Research-driven content generation
- Multi-voice audio synthesis
- File uploads (transcripts, descriptions, thumbnails)
- Canonical filename generation
- Job orchestration
"""

import asyncio
import json
import re
import time
import psutil
import gc
import os
from datetime import datetime
from typing import Optional, Dict, Any, List
from functools import wraps

# External dependencies
from paper_processor import process_paper, ResearchPaper, AnalyzeOptions, PaperAnalysis, format_citation
from copernicus_character import get_copernicus_character, get_character_prompt
from elevenlabs_voice_service import ElevenLabsVoiceService
from email_service import EmailService
from content_fixes import (
    apply_content_fixes,
    fix_script_format_for_multi_voice,
    limit_description_length,
    extract_itunes_summary,
    generate_relevant_hashtags,
    validate_academic_references
)
from podcast_research_integrator import PodcastResearchIntegrator, PodcastResearchContext

# Vertex AI imports
try:
    from google import genai as google_genai_client
    VERTEX_AI_AVAILABLE = True
except ImportError:
    google_genai_client = None
    VERTEX_AI_AVAILABLE = False

# Internal imports
from models.podcast import PodcastRequest
from utils.logging import structured_logger
from utils.step_tracking import with_step
from utils.api_keys import get_google_api_key
from config.constants import (
    GCP_PROJECT_ID,
    DEFAULT_SUBSCRIBER_EMAIL,
    ERROR_NOTIFICATION_EMAIL,
)
from config.database import db
from services.episode_service import episode_service
from services.canonical_service import canonical_service
from utils.script_validation import validate_script_length, calculate_minimum_words_for_duration

# Retry decorator for upload operations
def retry_upload(max_retries=3, delay=2):
    """Decorator for retrying upload operations with exponential backoff"""
    def decorator(func):
        async def wrapper(*args, **kwargs):
            last_exception = None
            for attempt in range(max_retries):
                try:
                    return await func(*args, **kwargs)
                except Exception as e:
                    last_exception = e
                    if attempt < max_retries - 1:
                        wait_time = delay * (2 ** attempt)
                        structured_logger.warning("Upload attempt failed, retrying",
                                                 attempt=attempt + 1,
                                                 max_retries=max_retries,
                                                 wait_time=wait_time,
                                                 error=str(e))
                        await asyncio.sleep(wait_time)
                    else:
                        structured_logger.error("Upload failed after all retries",
                                               max_retries=max_retries,
                                               error=str(e))
            raise last_exception
        return wrapper
    return decorator


def _extract_json_from_response(text: str) -> dict:
    """Extracts a JSON object from a string, even if it's embedded in other text."""
    # Regex to find a JSON object, potentially wrapped in markdown ```json ... ```
    json_match = re.search(r'```json\s*(\{.*?\})\s*```|(\{.*?\})', text, re.DOTALL)
    
    if not json_match:
        raise ValueError("No JSON object found in the AI's response.")
        
    # The regex has two capturing groups, one for the markdown case, one for the raw case.
    json_str = json_match.group(1) or json_match.group(2)
    
    # Enhanced cleaning function for JSON strings
    def clean_json_string(s):
        """Clean JSON string by removing or replacing invalid control characters"""
        import string
        
        # First pass: Remove all control characters except newlines, tabs, and carriage returns
        cleaned = ""
        for char in s:
            if char in string.printable or char in '\n\t\r':
                cleaned += char
            else:
                # Replace control characters with spaces
                cleaned += ' '
        
        # Second pass: Fix common JSON issues
        # Remove any null bytes
        cleaned = cleaned.replace('\x00', '')
        
        # Fix escaped quotes that might be broken
        cleaned = re.sub(r'\\"([^"]*?)\\""', r'\\"\1\\"', cleaned)
        
        # Remove any trailing commas before closing braces/brackets
        cleaned = re.sub(r',(\s*[}\]])', r'\1', cleaned)
        
        # Fix any broken escape sequences
        cleaned = re.sub(r'\\([^"\\/bfnrtu])', r'\1', cleaned)
        
        return cleaned
    
    def _extract_essential_json(json_str: str) -> dict:
        """Last resort: Try to extract essential JSON structure even if malformed"""
        # Try to find title and script even in malformed JSON
        title_match = re.search(r'"title"\s*:\s*"([^"]+)"', json_str)
        script_match = re.search(r'"script"\s*:\s*"([^"]*)"', json_str, re.DOTALL)
        
        if title_match and script_match:
            title = title_match.group(1)
            script = script_match.group(1)
            
            # Clean up the script
            script = re.sub(r'[\x00-\x08\x0B\x0C\x0E-\x1F\x7F]', '', script)
            script = script.replace('\\n', '\n').replace('\\t', '\t').replace('\\"', '"')
            
            return {
                "title": title,
                "script": script
            }
        else:
            raise ValueError("Could not extract essential JSON structure")
    
    # Multiple parsing attempts with different cleaning strategies
    parsing_attempts = [
        # Attempt 1: Original JSON
        lambda: json.loads(json_str),
        
        # Attempt 2: Basic cleaning
        lambda: json.loads(clean_json_string(json_str)),
        
        # Attempt 3: Remove all control characters
        lambda: json.loads(re.sub(r'[\x00-\x08\x0B\x0C\x0E-\x1F\x7F]', '', json_str)),
        
        # Attempt 4: More aggressive cleaning
        lambda: json.loads(re.sub(r'[^\x20-\x7E\n\t\r]', '', json_str)),
        
        # Attempt 5: Try to fix common JSON structure issues
        lambda: json.loads(re.sub(r',(\s*[}\]])', r'\1', clean_json_string(json_str))),
        
        # Attempt 6: Last resort - try to extract just the essential parts
        lambda: _extract_essential_json(json_str)
    ]
    
    for i, attempt in enumerate(parsing_attempts, 1):
        try:
            result = attempt()
            structured_logger.debug("JSON parsing succeeded",
                                   attempt=i,
                                   total_attempts=len(parsing_attempts))
            return result
        except json.JSONDecodeError as e:
            structured_logger.debug("JSON parsing attempt failed",
                                   attempt=i,
                                   total_attempts=len(parsing_attempts),
                                   error=str(e))
            if i == len(parsing_attempts):
                # Last attempt failed, show detailed error
                structured_logger.error("All JSON parsing attempts failed",
                                       total_attempts=len(parsing_attempts),
                                       original_text_snippet=json_str[:300] if json_str else None)
                raise ValueError(f"Failed to decode extracted JSON after {len(parsing_attempts)} attempts: {e}\nOriginal text snippet: {json_str[:200]}...")
        except Exception as e:
            structured_logger.warning("JSON parsing attempt failed with unexpected error",
                                     attempt=i,
                                     total_attempts=len(parsing_attempts),
                                     error=str(e))
            if i == len(parsing_attempts):
                raise


class PodcastGenerationService:
    """Service for generating podcasts with research-driven content"""
    
    def __init__(self, vertex_ai_model=None):
        """Initialize the podcast generation service"""
        self.vertex_ai_model = vertex_ai_model
        self.bucket_name = os.getenv("GCP_AUDIO_BUCKET", "regal-scholar-453620-r7-podcast-storage")
        self.email_service = EmailService()
        self.elevenlabs_voice_service = ElevenLabsVoiceService()
    
    async def generate_research_driven_content(self, request: PodcastRequest) -> dict:
        """Generate research-driven content using proper research methodology"""
        
        # Use the working research-driven approach directly
        structured_logger.info("Using research-driven content generation with proper methodology",
                              topic=request.topic)
        
        # Try Vertex AI first, then fall back to Google AI API
        if self.vertex_ai_model:
            structured_logger.info("Using Vertex AI Gemini for content generation")
            try:
                return await self.generate_content_vertex_ai(request)
            except Exception as e:
                structured_logger.warning("Vertex AI failed, falling back to Google AI API",
                                         error=str(e),
                                         topic=request.topic)
                google_key = get_google_api_key()
                if not google_key:
                    structured_logger.error("No Google AI API key available",
                                           topic=request.topic)
                    raise ValueError("Both Vertex AI and Google AI API are unavailable.")
                return await self.generate_content_google_api(request, google_key)
        else:
            structured_logger.info("Using Google AI API for research-driven content")
            google_key = get_google_api_key()
            if not google_key:
                structured_logger.error("No Google AI API key - cannot generate content",
                                       topic=request.topic)
                raise ValueError("Google AI API key is not available.")
            return await self.generate_content_google_api(request, google_key)
    
    async def generate_content_vertex_ai(self, request: PodcastRequest) -> dict:
        """Generate content using Vertex AI Gemini. This function will now raise exceptions on failure."""
        # Check if we have research paper content to analyze
        if request.paper_content and request.paper_title:
            structured_logger.info("Processing research paper with Vertex AI",
                                  paper_title=request.paper_title[:50] if request.paper_title else None)
            
            # Create ResearchPaper object
            paper = ResearchPaper(
                title=request.paper_title,
                authors=request.paper_authors or ["Unknown Author"],
                content=request.paper_content,
                abstract=request.paper_abstract,
                doi=request.paper_doi
            )
            
            # Create analysis options
            options = AnalyzeOptions(
                focus_areas=request.focus_areas or ["methodology", "implications", "future_research"],
                include_citations=request.include_citations,
                paradigm_shift_analysis=request.paradigm_shift_analysis
            )
            
            # Process paper
            analysis = await process_paper(paper, options)
            return await self.generate_podcast_from_analysis_vertex(paper, analysis, request)
        else:
            structured_logger.info("Generating topic-based research content with Vertex AI",
                                  topic=request.topic)
            return await self.generate_topic_research_content_vertex(request)
    
    async def generate_content_google_api(self, request: PodcastRequest, google_key: str) -> dict:
        """Generate content using Google AI API. This function will now raise exceptions on failure."""
        # Check if we have research paper content to analyze
        if request.paper_content and request.paper_title:
            structured_logger.info("Processing research paper with Google AI API",
                                  paper_title=request.paper_title[:50] if request.paper_title else None)
            
            # Create ResearchPaper object
            paper = ResearchPaper(
                title=request.paper_title,
                authors=request.paper_authors or ["Unknown Author"],
                content=request.paper_content,
                abstract=request.paper_abstract,
                doi=request.paper_doi
            )
            
            # Create analysis options
            options = AnalyzeOptions(
                focus_areas=request.focus_areas or ["methodology", "implications", "future_research"],
                analysis_depth="comprehensive",
                include_citations=request.include_citations,
                paradigm_shift_analysis=request.paradigm_shift_analysis,
                interdisciplinary_connections=True
            )
            
            # Analyze the paper
            analysis = await process_paper(paper, options, google_key)
            
            # Generate podcast content based on analysis
            return await self.generate_podcast_from_analysis(paper, analysis, request, google_key)
            
        else:
            # No paper provided - generate topic-based research content
            structured_logger.info("Generating research-driven content for topic",
                                  topic=request.topic)
            return await self.generate_topic_research_content(request, google_key)
    
    async def generate_podcast_from_analysis(
        self, 
        paper: ResearchPaper, 
        analysis: PaperAnalysis, 
        request: PodcastRequest, 
        api_key: str
    ) -> dict:
        """Generate character-driven podcast content from research paper analysis"""
        if not google_genai_client:
            raise Exception("Google GenAI client not available")
        
        client = google_genai_client.Client(api_key=api_key)
        
        # Get Copernicus character configuration
        character = get_copernicus_character()
        
        # Format citations
        citation = format_citation(paper)
        
        # Create character-driven prompt with paper analysis
        paper_analysis_dict = {
            'title': paper.title,
            'key_findings': analysis.key_findings,
            'paradigm_shifts': analysis.paradigm_shifts,
            'interdisciplinary_connections': analysis.interdisciplinary_connections,
            'future_research_directions': analysis.future_research_directions
        }
        
        character_prompt = get_character_prompt(character, paper_analysis_dict)
        
        # Map voice IDs to names for script generation
        VOICE_ID_TO_NAME = {
            "XrExE9yKIg1WjnnlVkGX": "Matilda",
            "EXAVITQu4vr4xnSDxMaL": "Bella",
            "JBFqnCBsd6RMkjVDRZzb": "Sam",
            "pNInz6obpgDQGcFmaJgB": "Adam",
            "pqHfZKP75CvOlQylNhV4": "Bryan",
            "onwK4e9ZLuTAKqWW03F9": "Daniel"
        }
        
        # Determine actual speaker names from selected voice IDs
        host_name = VOICE_ID_TO_NAME.get(request.host_voice_id, "Matilda") if request.host_voice_id else "Matilda"
        expert_name = VOICE_ID_TO_NAME.get(request.expert_voice_id, "Adam") if request.expert_voice_id else "Adam"
        
        structured_logger.info("Using selected voices for script generation",
                              host_voice_id=request.host_voice_id,
                              expert_voice_id=request.expert_voice_id,
                              host_name=host_name,
                              expert_name=expert_name)
        
        # Enhanced prompt with multi-voice structure
        prompt = f"""{character_prompt}

Create a compelling {request.duration} research podcast script based on this paper analysis:

**Paper:** {paper.title}
**Authors:** {', '.join(paper.authors)}
**Citation:** {citation}

**Key Analysis:**
- Summary: {analysis.summary}
- Key Findings: {'; '.join(analysis.key_findings)}
- Paradigm Shifts: {'; '.join(analysis.paradigm_shifts)}
- Interdisciplinary Connections: {'; '.join(analysis.interdisciplinary_connections)}
- Future Directions: {'; '.join(analysis.future_research_directions)}

**Multi-Voice Script Requirements:**
Create a natural dialogue between HOST, EXPERT, and QUESTIONER that follows this structure:
{chr(10).join([f"- {step}" for step in character.structure])}

**CRITICAL SPEAKER POLICY:**
- The HOST speaker must be named "{host_name}" (use this exact name for all HOST lines)
- The EXPERT speaker must be named "{expert_name}" (use this exact name for all EXPERT lines)
- ALL speakers must be FICTIONAL with first names ONLY - NO titles (Dr., Professor, PhD), NO surnames, NO real person identification
- When introducing speakers, use only first names (e.g., "Let's bring in {expert_name}, our expert...")
- NEVER use "Dr." or any academic titles in the script
- IMPORTANT: Use "{host_name}" for HOST and "{expert_name}" for EXPERT consistently throughout the script

**ROLE CONSISTENCY REQUIREMENTS:**
- **HOST**: Guides the conversation, asks introductory questions, provides context
- **EXPERT**: Provides detailed technical explanations, research insights, and expert analysis
- **QUESTIONER**: Asks clarifying questions, expresses curiosity, seeks deeper understanding
- **NEVER mix roles**: Expert explains, Questioner asks, Host guides
- **Maintain character consistency** throughout the entire dialogue

**Script Format Requirements:**
- **MUST** use speaker labels: "{host_name.upper()}:", "{expert_name.upper()}:", "QUESTIONER:"
- Use "{host_name}" for all HOST lines and "{expert_name}" for all EXPERT lines consistently
- Write as a conversation between speakers with clear speaker labels at the start of each dialogue block
- Make the conversation flow naturally with proper speaker transitions
- **Include academic references naturally in conversation** (e.g., "As shown in the Nature Neuroscience study..." or "Research published in NeuroImage demonstrates...")
- **AVOID speaking DOI numbers, publication dates, or technical citation details** - keep references conversational
- Focus on paradigm-shifting implications and research insights
- Duration: {request.duration}
- Expertise Level: {request.expertise_level}

**CONTENT LENGTH REQUIREMENTS:**
- **Standard Duration: 5 minutes** - Generate AT LEAST 750-1000 words of dialogue
- Ensure substantial depth and multiple discussion points
- Include detailed explanations, examples, and implications
- Cover multiple aspects of the research topic thoroughly

**FORMAT-SPECIFIC REQUIREMENTS:**
- **NEWS Format**: Focus on current developments, breaking research, immediate impact, recent papers and announcements
- **FEATURE Format**: Focus on comprehensive overview, historical context, methodology, paradigm shifts, and future directions

**Content Quality Standards:**
- Follow established podcast quality patterns from existing episodes
- Include deep technical analysis with accessible explanations
- Provide interdisciplinary connections and future research directions
- Use engaging storytelling while maintaining scientific accuracy

Return JSON with:
{{
    "title": "Engaging podcast title highlighting paradigm shift",
    "script": "Multi-voice podcast script with {host_name.upper()}:, {expert_name.upper()}:, QUESTIONER: markers and natural dialogue using these exact speaker names",
    "description": "Comprehensive episode description following established format"
}}

**CRITICAL: Generate a CONCISE description using this EXACT format:**

**LENGTH REQUIREMENT: The description content (excluding References, Episode Details, and Hashtags) MUST be under 2000-2500 characters total. This leaves room for complete References and Hashtags sections which will be added separately. Be concise and focused.**

IMPORTANT: Do NOT include a "## Episode Overview" header. Start directly with 1-2 engaging paragraphs (CONCISE) introducing the research paper and its significance. Begin the description immediately without any section header for the opening content.

## Key Concepts Explored
- [Key Finding 1]: [Brief explanation with implications - keep to 1-2 sentences]
- [Key Finding 2]: [Brief explanation with applications - keep to 1-2 sentences]
- [Paradigm Shift]: [How this changes the field - keep to 1-2 sentences]
- [Future Direction]: [What this enables next - keep to 1-2 sentences]

## Research Insights
[1 paragraph (CONCISE) about the paper's methodology, breakthrough findings, and contribution to the field. Keep it brief and focused.]

## Practical Applications
[1 paragraph (CONCISE) about real-world applications and potential uses of this research. Be specific but brief.]

## Future Directions
[1 paragraph (CONCISE) about future research directions enabled by this work and long-term implications. Keep it brief.]

## References
- {citation}
- [Additional relevant citations in DOI format - include 3-5 key references with complete DOIs/URLs]

## Episode Details
- **Duration**: {request.duration}
- **Expertise Level**: {request.expertise_level}
- **Paper**: {paper.title}
- **Authors**: {', '.join(paper.authors)}

---

**NOTE: Hashtags will be added automatically after generation. Do NOT include hashtags in your response.**

"""
        
        try:
            structured_logger.info("Generating podcast script from research analysis",
                                  paper_title=paper.title[:50] if paper and paper.title else None)
            # Try Gemini 3.0 first, fallback to 2.5 if not available
            model_name = 'models/gemini-3.0-flash'
            try:
                response_obj = client.models.generate_content(
                    model=model_name,
                    contents=prompt
                )
            except Exception as e:
                error_msg = str(e).lower()
                if "not found" in error_msg or "does not exist" in error_msg:
                    structured_logger.info("Gemini 3.0 not available, falling back to 2.5")
                    model_name = 'models/gemini-2.5-flash'
                    response_obj = client.models.generate_content(
                        model=model_name,
                        contents=prompt
                    )
                else:
                    raise
            
            if response_obj and response_obj.text:
                content = _extract_json_from_response(response_obj.text)
                structured_logger.info("Research-driven podcast content generated successfully",
                                      model=model_name)
                return content
            else:
                raise Exception("Empty response from Gemini")
                
        except Exception as e:
            structured_logger.error("Error generating podcast from analysis",
                                   error=str(e),
                                   error_type=type(e).__name__,
                                   paper_title=paper.title[:50] if paper and paper.title else None)
            raise
    
    async def generate_podcast_from_analysis_vertex(
        self, 
        paper: ResearchPaper, 
        analysis: PaperAnalysis, 
        request: PodcastRequest
    ) -> dict:
        """Generate character-driven podcast content from research paper analysis using Vertex AI"""
        if not self.vertex_ai_model:
            raise Exception("Vertex AI model not available")
            
        # Get Copernicus character configuration
        character = get_copernicus_character()
        character_prompt = get_character_prompt(character)
        citation = format_citation(paper)
        
        # Map voice IDs to names for script generation
        VOICE_ID_TO_NAME = {
            "XrExE9yKIg1WjnnlVkGX": "Matilda",
            "EXAVITQu4vr4xnSDxMaL": "Bella",
            "JBFqnCBsd6RMkjVDRZzb": "Sam",
            "pNInz6obpgDQGcFmaJgB": "Adam",
            "pqHfZKP75CvOlQylNhV4": "Bryan",
            "onwK4e9ZLuTAKqWW03F9": "Daniel"
        }
        
        # Determine actual speaker names from selected voice IDs
        host_name = VOICE_ID_TO_NAME.get(request.host_voice_id, "Matilda") if request.host_voice_id else "Matilda"
        expert_name = VOICE_ID_TO_NAME.get(request.expert_voice_id, "Adam") if request.expert_voice_id else "Adam"
        
        structured_logger.info("Using selected voices for Vertex AI script generation",
                              host_voice_id=request.host_voice_id,
                              expert_voice_id=request.expert_voice_id,
                              host_name=host_name,
                              expert_name=expert_name)
        
        prompt = f"""{character_prompt}

Create a compelling {request.duration} research podcast script analyzing this groundbreaking paper for {request.expertise_level} audience.

**Research Paper Analysis:**
{paper.title}
Authors: {', '.join(paper.authors)}

**Key Analysis:**
- Summary: {analysis.summary}
- Key Findings: {'; '.join(analysis.key_findings)}
- Paradigm Shifts: {'; '.join(analysis.paradigm_shifts)}
- Interdisciplinary Connections: {'; '.join(analysis.interdisciplinary_connections)}
- Future Directions: {'; '.join(analysis.future_research_directions)}

**Multi-Voice Script Requirements:**
Create a natural dialogue between HOST, EXPERT, and QUESTIONER that follows this structure:
{chr(10).join([f"- {step}" for step in character.structure])}

**CRITICAL SPEAKER POLICY:**
- The HOST speaker must be named "{host_name}" (use this exact name for all HOST lines)
- The EXPERT speaker must be named "{expert_name}" (use this exact name for all EXPERT lines)
- ALL speakers must be FICTIONAL with first names ONLY - NO titles (Dr., Professor, PhD), NO surnames, NO real person identification
- When introducing speakers, use only first names (e.g., "Let's bring in {expert_name}, our expert...")
- NEVER use "Dr." or any academic titles in the script
- IMPORTANT: Use "{host_name}" for HOST and "{expert_name}" for EXPERT consistently throughout the script

**Script Format Requirements:**
- Use "{host_name.upper()}:", "{expert_name.upper()}:", and "QUESTIONER:" to mark each speaker clearly
- The HOST speaker is "{host_name}" - use this exact name for all HOST speaker labels
- The EXPERT speaker is "{expert_name}" - use this exact name for all EXPERT speaker labels
- Write natural dialogue that flows between speakers
- Include proper academic citations with DOIs where relevant
- Focus on paradigm-shifting implications and research insights
- Duration: {request.duration}
- Expertise Level: {request.expertise_level}

Return JSON with:
{{
    "title": "Engaging podcast title highlighting paradigm shift",
    "script": "Multi-voice podcast script with {host_name.upper()}:, {expert_name.upper()}:, QUESTIONER: markers and natural dialogue using these exact speaker names",
    "description": "Comprehensive episode description following established format"
}}

**CRITICAL: Generate a CONCISE description using this EXACT format:**

**LENGTH REQUIREMENT: The description content (excluding References, Episode Details, and Hashtags) MUST be under 2000-2500 characters total. This leaves room for complete References and Hashtags sections which will be added separately. Be concise and focused.**

IMPORTANT: Do NOT include a "## Episode Overview" header. Start directly with 1-2 engaging paragraphs (CONCISE) introducing the research paper and its significance. Begin the description immediately without any section header for the opening content.

## Key Concepts Explored
- [Key Finding 1]: [Brief explanation with implications - keep to 1-2 sentences]
- [Key Finding 2]: [Brief explanation with applications - keep to 1-2 sentences]
- [Paradigm Shift]: [How this changes the field - keep to 1-2 sentences]
- [Future Direction]: [What this enables next - keep to 1-2 sentences]

## Research Insights
[1 paragraph (CONCISE) about the paper's methodology, breakthrough findings, and contribution to the field. Keep it brief and focused.]

## Practical Applications
[1 paragraph (CONCISE) about real-world applications and potential uses of this research. Be specific but brief.]

## Future Directions
[1 paragraph (CONCISE) about future research directions enabled by this work and long-term implications. Keep it brief.]

## References
- {citation}
- [Additional relevant citations in DOI format - include 3-5 key references with complete DOIs/URLs]

## Episode Details
- **Duration**: {request.duration}
- **Expertise Level**: {request.expertise_level}
- **Paper**: {paper.title}
- **Authors**: {', '.join(paper.authors)}

---

**NOTE: Hashtags will be added automatically after generation. Do NOT include hashtags in your response.**

"""
        
        try:
            structured_logger.info("Generating podcast script from research analysis using Vertex AI",
                                  paper_title=paper.title[:50] if paper and paper.title else None)
            # Try Gemini 3.0 first, fallback to 2.5 if not available
            model_name = 'models/gemini-3.0-flash'
            try:
                response = self.vertex_ai_model.models.generate_content(
                    model=model_name,
                    contents=prompt
                )
            except Exception as e:
                error_msg = str(e).lower()
                if "not found" in error_msg or "does not exist" in error_msg:
                    structured_logger.info("Gemini 3.0 not available, falling back to 2.5")
                    model_name = 'models/gemini-2.5-flash'
                    response = self.vertex_ai_model.models.generate_content(
                        model=model_name,
                        contents=prompt
                    )
                else:
                    raise
            
            if response and response.text:
                content = _extract_json_from_response(response.text)
                structured_logger.info("Vertex AI research-driven podcast content generated successfully",
                                      model=model_name)
                return content
            else:
                raise Exception("Empty response from Vertex AI")
                
        except Exception as e:
            structured_logger.error("Error generating podcast from analysis with Vertex AI",
                                   error=str(e),
                                   error_type=type(e).__name__,
                                   paper_title=paper.title[:50] if paper and paper.title else None)
            raise
    
    async def generate_topic_research_content(
        self, 
        request: PodcastRequest, 
        api_key: str
    ) -> dict:
        """Generate character-driven research content for a topic without specific paper"""
        if not google_genai_client:
            raise Exception("Google GenAI client not available")
        
        client = google_genai_client.Client(api_key=api_key)
        
        # Get Copernicus character configuration
        character = get_copernicus_character()
        character_prompt = get_character_prompt(character)
        
        # Calculate minimum word count for explicit requirement
        min_words = calculate_minimum_words_for_duration(request.duration)
        target_words = int(min_words / 0.9)  # Target for full duration
        
        # Map voice IDs to names for script generation
        VOICE_ID_TO_NAME = {
            "XrExE9yKIg1WjnnlVkGX": "Matilda",
            "EXAVITQu4vr4xnSDxMaL": "Bella",
            "JBFqnCBsd6RMkjVDRZzb": "Sam",
            "pNInz6obpgDQGcFmaJgB": "Adam",
            "pqHfZKP75CvOlQylNhV4": "Bryan",
            "onwK4e9ZLuTAKqWW03F9": "Daniel"
        }
        
        # Determine actual speaker names from selected voice IDs
        host_name = VOICE_ID_TO_NAME.get(request.host_voice_id, "Matilda") if request.host_voice_id else "Matilda"
        expert_name = VOICE_ID_TO_NAME.get(request.expert_voice_id, "Adam") if request.expert_voice_id else "Adam"
        
        structured_logger.info("Using selected voices for topic-based script generation",
                              host_voice_id=request.host_voice_id,
                              expert_voice_id=request.expert_voice_id,
                              host_name=host_name,
                              expert_name=expert_name)
        
        prompt = f"""{character_prompt}

Create a compelling {request.duration} research podcast script about "{request.topic}" for {request.expertise_level} audience.

**Focus Areas:** {', '.join(request.focus_areas) if request.focus_areas else 'recent breakthroughs, methodology, implications'}

**CRITICAL SHOW REQUIREMENTS:**
- The show name is ALWAYS "Copernicus AI: Frontiers of Science" - never use any other title
- HOST must introduce the show as "Welcome to Copernicus AI: Frontiers of Science"
- The HOST speaker must be named "{host_name}" (use this exact name for all HOST lines)
- The EXPERT speaker must be named "{expert_name}" (use this exact name for all EXPERT lines)
- All speakers use FIRST NAMES ONLY - NO surnames, titles, or honorifics
- Speakers are clearly fictional characters, not real people
- IMPORTANT: Use "{host_name}" for HOST and "{expert_name}" for EXPERT consistently throughout the script

**Multi-Voice Script Requirements:**
Create a natural dialogue between HOST, EXPERT, and QUESTIONER that follows this structure:
{chr(10).join([f"- {step}" for step in character.structure])}

**Content Length Requirements - CRITICAL:**
- Target duration: {request.duration}
- **MINIMUM REQUIRED: {min_words} words** (based on 150 words per minute)
- **TARGET: {target_words} words** for full duration coverage
- Each speaker should have 8-12 substantial dialogue segments
- Include detailed technical explanations and comprehensive coverage
- **FAILURE WARNING: Scripts under {min_words} words will be REJECTED and generation will fail - ensure you meet or exceed this minimum**

**CRITICAL FORMAT REQUIREMENTS - THIS IS MANDATORY:**
- **MUST** use speaker labels at the beginning of each line: "{host_name.upper()}:", "{expert_name.upper()}:", "QUESTIONER:"
- **CRITICAL: Use the exact names "{host_name}" for HOST and "{expert_name}" for EXPERT in all speaker labels**
- **DO NOT** write in narrative format - write as a conversation between speakers
- **NEVER** start with "Welcome to Copernicus AI" without a speaker label
- **NEVER** use phrases like "{host_name} explains" or "{expert_name} adds" - use speaker labels instead
- **EXAMPLE FORMAT:**
  {host_name.upper()}: Welcome to Copernicus AI: Frontiers of Science. Today we're discussing {request.topic}.
  {expert_name.upper()}: Thank you for having me. This is a fascinating area of research.
  QUESTIONER: Can you explain what makes this topic so significant?
  {host_name.upper()}: That's a great question. Let's dive into the details.

**MANDATORY:** Every line of dialogue must start with a speaker label. Do not write any narrative text without speaker labels. The script must be a pure dialogue format with {host_name.upper()}:, {expert_name.upper()}:, QUESTIONER: labels. Use "{host_name}" for all HOST lines and "{expert_name}" for all EXPERT lines.

**Format Guidelines:**
- Use "{host_name.upper()}:", "{expert_name.upper()}:", and "QUESTIONER:" to mark each speaker clearly
- The HOST speaker is "{host_name}" - use this name in all HOST speaker labels
- The EXPERT speaker is "{expert_name}" - use this name in all EXPERT speaker labels
- HOST introduces the topic and guides the conversation for "Copernicus AI: Frontiers of Science"
- EXPERT provides technical analysis and research insights about {request.topic}
- QUESTIONER asks clarifying questions and represents audience curiosity
- Include evidence-based insights from recent research
- Mention specific studies with proper academic citations when possible
- Focus on paradigm shifts and interdisciplinary connections
- Explore practical implications and future research directions
- Duration: {request.duration}
- Expertise Level: {request.expertise_level}

Create natural dialogue that explores:
1. Revolutionary discoveries in {request.topic}
2. How recent research challenges existing paradigms
3. Interdisciplinary connections and implications
4. Future research directions and practical applications
5. Evidence-based speculation about breakthrough potential

Return JSON with:
{{
    "title": "Engaging podcast title highlighting paradigm shifts in {request.topic}",
    "script": "Multi-voice podcast script with {host_name.upper()}:, {expert_name.upper()}:, QUESTIONER: markers and natural dialogue using these exact speaker names",
    "description": "Comprehensive episode description following established format"
}}

**CRITICAL: Generate a separate comprehensive description using this EXACT format:**

After generating the main content, create a detailed description following this structure. Generate a detailed, engaging episode description (aim for 2500-3500 characters to maximize discoverability). Be thorough and informative while remaining accessible.

IMPORTANT: Do NOT include a "## Episode Overview" header. Start directly with 3-4 engaging paragraphs introducing the topic, its significance in the field, and why this research area matters. Explain the broader context, historical background, and implications. Make it compelling and informative. Begin the description immediately without any section header for the opening content.

## Key Concepts Explored
- [Concept 1]: [Detailed explanation with technical depth, implications, and connections to broader field]
- [Concept 2]: [Detailed explanation with practical applications and real-world relevance]
- [Concept 3]: [Detailed explanation with future implications and emerging possibilities]
- [Concept 4]: [Detailed explanation with interdisciplinary connections and cross-field impact]
- [Concept 5]: [Additional important concept or methodology with context]

## Research Insights
[2-3 paragraphs about current research developments, recent breakthroughs, methodological advances, experimental techniques, and what makes this area of research exciting. Discuss cutting-edge findings and their significance.]

## Practical Applications
[2-3 paragraphs about real-world applications, industry impact, technological implementations, and potential uses. Be specific about how this research could be applied in practice, including examples from different sectors.]

## Future Directions
[2-3 paragraphs about emerging research directions, potential breakthroughs on the horizon, long-term implications, unanswered questions, and where this field is heading. Discuss both near-term and long-term possibilities.]

## References
- [Author et al. (Year). Title. Journal. DOI: 10.xxxx/xxxx]
- [Author et al. (Year). Title. Journal. DOI: 10.xxxx/xxxx]
- [Add 3-5 relevant academic references with proper DOI format]

## Episode Details
- **Duration**: {request.duration}
- **Expertise Level**: {request.expertise_level}
- **Category**: {request.topic.split()[0] if request.topic else 'Science'}

---

#CopernicusAI #SciencePodcast #{request.topic.replace(' ', '')}Research #AcademicDiscussion #ResearchInsights

"""
        
        try:
            structured_logger.info("Generating topic-based research content with Gemini",
                                  topic=request.topic)
            # Try Gemini 3.0 first, fallback to 2.5 if not available
            model_name = 'models/gemini-3.0-flash'
            try:
                response_obj = client.models.generate_content(
                    model=model_name,
                    contents=prompt
                )
            except Exception as e:
                error_msg = str(e).lower()
                if "not found" in error_msg or "does not exist" in error_msg:
                    structured_logger.info("Gemini 3.0 not available, falling back to 2.5",
                                          topic=request.topic)
                    model_name = 'models/gemini-2.5-flash'
                    response_obj = client.models.generate_content(
                        model=model_name,
                        contents=prompt
                    )
                else:
                    raise
            
            if response_obj and response_obj.text:
                content = _extract_json_from_response(response_obj.text)
                
                # Apply content fixes
                if 'script' in content:
                    content['script'] = apply_content_fixes(content['script'], request.topic)
                    # Fix script format for multi-voice if needed
                    content['script'] = fix_script_format_for_multi_voice(content['script'])
                
                # Limit description length and extract iTunes summary
                if 'description' in content:
                    content['description'] = limit_description_length(content['description'], 4000)
                    content['itunes_summary'] = extract_itunes_summary(content['description'])
                    
                    # Generate relevant hashtags
                    content['hashtags'] = generate_relevant_hashtags(
                        request.topic, 
                        request.category, 
                        content.get('title', ''), 
                        content['description']
                    )
                    
                    # Validate academic references in description
                    if '## References' in content['description']:
                        # Extract references section
                        desc_parts = content['description'].split('## References')
                        if len(desc_parts) > 1:
                            ref_section = desc_parts[1].split('##')[0]
                            validated_refs = validate_academic_references(ref_section)
                            content['description'] = desc_parts[0] + '## References\n' + validated_refs + '\n' + '##'.join(desc_parts[1].split('##')[1:])
                
                structured_logger.info("Topic-based research content generated successfully",
                                      topic=request.topic,
                                      model=model_name)
                return content
            else:
                raise Exception("Empty response from Gemini")
                
        except Exception as e:
            structured_logger.error("Error generating topic research content",
                                   topic=request.topic,
                                   error=str(e),
                                   error_type=type(e).__name__)
            raise
    
    async def generate_topic_research_content_vertex(
        self, 
        request: PodcastRequest
    ) -> dict:
        """Generate character-driven research content for a topic without specific paper using Vertex AI"""
        if not self.vertex_ai_model:
            raise Exception("Vertex AI model not available")
            
        # Get Copernicus character configuration
        character = get_copernicus_character()
        character_prompt = get_character_prompt(character)
        
        prompt = f"""{character_prompt}

Create a compelling {request.duration} research podcast script about "{request.topic}" for {request.expertise_level} audience.

**Focus Areas:** {', '.join(request.focus_areas) if request.focus_areas else 'recent breakthroughs, methodology, implications'}

**Multi-Voice Script Requirements:**
Create a natural dialogue between HOST, EXPERT, and QUESTIONER that follows this structure:
{chr(10).join([f"- {step}" for step in character.structure])}

**CRITICAL SPEAKER POLICY:**
- ALL speakers must be FICTIONAL with first names ONLY (e.g., "Matilda", "Adam", "Bill")
- NO titles (Dr., Professor, PhD), NO surnames, NO real person identification
- When introducing speakers, use only first names (e.g., "Let's bring in Adam, our expert...")
- NEVER use "Dr." or any academic titles in the script

**Format Guidelines:**
- Use "HOST:", "EXPERT:", and "QUESTIONER:" to mark each speaker
- HOST introduces the topic and guides the conversation
- EXPERT provides technical analysis and research insights about {request.topic}
- QUESTIONER asks clarifying questions and represents audience curiosity
- Include evidence-based insights from recent research
- Mention specific studies with proper academic citations when possible
- Focus on paradigm shifts and interdisciplinary connections
- Explore practical implications and future research directions
- Duration: {request.duration}
- Expertise Level: {request.expertise_level}

Create natural dialogue that explores:
1. Revolutionary discoveries in {request.topic}
2. How recent research challenges existing paradigms
3. Interdisciplinary connections and implications
4. Future research directions and practical applications
5. Evidence-based speculation about breakthrough potential

Return JSON with:
{{
    "title": "Engaging podcast title highlighting paradigm shifts in {request.topic}",
    "script": "Multi-voice podcast script with {host_name.upper()}:, {expert_name.upper()}:, QUESTIONER: markers and natural dialogue using these exact speaker names",
    "description": "Comprehensive episode description following established format"
}}

**CRITICAL: Generate a comprehensive description using this EXACT format:**

IMPORTANT: Do NOT include a "## Episode Overview" header. Start directly with 2-3 engaging paragraphs introducing the topic and its significance in the field. Begin the description immediately without any section header for the opening content.

## Key Concepts Explored
- [Concept 1]: [Brief explanation with technical depth]
- [Concept 2]: [Brief explanation with practical applications]
- [Concept 3]: [Brief explanation with future implications]
- [Concept 4]: [Brief explanation with interdisciplinary connections]

## Research Insights
[Paragraph about current research developments, recent breakthroughs, and methodological advances]

## Practical Applications
[Paragraph about real-world applications, industry impact, and technological implementations]

## Future Directions
[Paragraph about emerging research directions, potential breakthroughs, and long-term implications]

## References
- [Author et al. (Year). Title. Journal. DOI: 10.xxxx/xxxx]
- [Author et al. (Year). Title. Journal. DOI: 10.xxxx/xxxx]
- [Add 3-5 relevant academic references with proper DOI format]

## Episode Details
- **Duration**: {request.duration}
- **Expertise Level**: {request.expertise_level}
- **Category**: {request.topic.split()[0] if request.topic else 'Science'}

---

#CopernicusAI #SciencePodcast #{request.topic.replace(' ', '')}Research #AcademicDiscussion #ResearchInsights

"""
        
        try:
            structured_logger.info("Generating topic-based research content with Vertex AI Gemini",
                                  topic=request.topic)
            # Try Gemini 3.0 first, fallback to 2.5 if not available
            model_name = 'models/gemini-3.0-flash'
            try:
                response = self.vertex_ai_model.models.generate_content(
                    model=model_name,
                    contents=prompt
                )
            except Exception as e:
                error_msg = str(e).lower()
                if "not found" in error_msg or "does not exist" in error_msg:
                    structured_logger.info("Gemini 3.0 not available, falling back to 2.5",
                                          topic=request.topic)
                    model_name = 'models/gemini-2.5-flash'
                    response = self.vertex_ai_model.models.generate_content(
                        model=model_name,
                        contents=prompt
                    )
                else:
                    raise
            
            if response and response.text:
                content = _extract_json_from_response(response.text)
                
                # Apply content fixes
                if 'script' in content:
                    content['script'] = apply_content_fixes(content['script'], request.topic)
                
                structured_logger.info("Vertex AI topic-based podcast content generated successfully",
                                      topic=request.topic,
                                      model=model_name)
                return content
            else:
                raise Exception("Empty response from Vertex AI")
                
        except Exception as e:
            structured_logger.error("Error generating topic research content with Vertex AI",
                                   topic=request.topic,
                                   error=str(e),
                                   error_type=type(e).__name__)
            raise
    
    async def generate_content_from_research_context(
        self,
        request: PodcastRequest,
        research_context: PodcastResearchContext,
        google_key: str,
        retry_attempt: int = 0
    ) -> dict:
        """
        Generate 2-speaker podcast content from research context
        Uses the research integrator to create Copernicus-spirit content
        
        Args:
            retry_attempt: Attempt number (0 = first attempt, 1+ = retries)
                          Used to strengthen prompt on retries
        """
        structured_logger.info("Generating 2-speaker content from research sources",
                              research_sources_count=len(research_context.research_sources),
                              topic=request.topic,
                              retry_attempt=retry_attempt)
        
        research_integrator = PodcastResearchIntegrator(google_key)
        
        # Strengthen instructions on retries if script was too short
        min_words = calculate_minimum_words_for_duration(request.duration)
        additional_instructions = request.additional_instructions or ""
        
        if retry_attempt > 0:
            additional_instructions += f"""

**⚠️ RETRY ATTEMPT - PREVIOUS SCRIPT WAS TOO SHORT ⚠️**
- Your previous script was REJECTED because it was too short (under {min_words} words)
- **YOU MUST generate a script with AT LEAST {min_words} words - this is mandatory**
- Expand the dialogue significantly - add more examples, explanations, discussion points
- Increase dialogue segments to 15-20 turns per speaker (not 10-15)
- Add more technical depth, examples, implications, and future directions
- The script MUST be substantially longer to pass validation
- DO NOT generate a short script again - make it longer this time
"""
        
        prompt = research_integrator.build_2_speaker_research_prompt(
            research_context=research_context,
            duration=request.duration,
            format_type=request.format_type,
            additional_instructions=additional_instructions,
            host_voice_id=request.host_voice_id,
            expert_voice_id=request.expert_voice_id
        )
        
        structured_logger.debug("Sending prompt to LLM",
                               prompt_length=len(prompt),
                               topic=request.topic)
        
        # Call Vertex AI or Google AI API
        if VERTEX_AI_AVAILABLE and google_genai_client and self.vertex_ai_model:
            structured_logger.info("Using Vertex AI Gemini (via google-genai client)")
            try:
                from google.genai import types
                model_name = 'models/gemini-3.0-flash'
                try:
                    response = self.vertex_ai_model.models.generate_content(
                        model=model_name,
                        contents=prompt,
                        config=types.GenerateContentConfig(
                            max_output_tokens=16384,  # Increased for longer scripts
                            temperature=0.8,
                            top_p=0.95
                        )
                    )
                except Exception as e:
                    error_msg = str(e).lower()
                    if "not found" in error_msg or "does not exist" in error_msg or "404" in error_msg:
                        structured_logger.warning("Gemini 3.0 not available, trying fallbacks")
                        fallback_models = ['models/gemini-3.0-pro', 'models/gemini-2.5-flash', 'models/gemini-2.0-flash-exp']
                        response = None
                        last_error = e
                        
                        for fallback_model in fallback_models:
                            try:
                                structured_logger.info("Trying Vertex AI fallback model",
                                                     model=fallback_model)
                                model_name = fallback_model
                                response = self.vertex_ai_model.models.generate_content(
                                    model=fallback_model,
                                    contents=prompt,
                                    config=types.GenerateContentConfig(
                                        max_output_tokens=16384,  # Increased for longer scripts
                                        temperature=0.8,
                                        top_p=0.95
                                    )
                                )
                                structured_logger.info("Vertex AI fallback successful",
                                                     model=fallback_model)
                                break
                            except Exception as fallback_err:
                                last_error = fallback_err
                                structured_logger.warning("Vertex AI fallback model failed",
                                                         model=fallback_model,
                                                         error=str(fallback_err))
                                continue
                        
                        if not response:
                            raise last_error
                    else:
                        raise
            except Exception as e:
                structured_logger.warning("Vertex AI generation failed, falling back to Google AI API",
                                         error=str(e))
                try:
                    import google.generativeai as genai
                    genai.configure(api_key=google_key)
                    fallback_models = ['gemini-3.0-flash', 'gemini-3.0-pro', 'gemini-2.0-flash-exp', 'gemini-1.5-pro']
                    response = None
                    last_error = None
                    
                    for model_name in fallback_models:
                        try:
                            structured_logger.info("Trying Google AI API model",
                                                 model=model_name)
                            model = genai.GenerativeModel(model_name)
                            generation_config = genai.types.GenerationConfig(
                                max_output_tokens=16384,  # Increased for longer scripts
                                temperature=0.8,
                                top_p=0.95
                            )
                            response = model.generate_content(prompt, generation_config=generation_config)
                            structured_logger.info("Google AI API successful",
                                                 model=model_name)
                            break
                        except Exception as model_error:
                            last_error = model_error
                            structured_logger.warning("Google AI API model failed, trying next",
                                                     model=model_name,
                                                     error=str(model_error))
                            continue
                    
                    if not response:
                        raise last_error or Exception("All Google AI API models failed")
                        
                except Exception as fallback_error:
                    structured_logger.error("Google AI API also failed",
                                           vertex_error=str(e),
                                           google_error=str(fallback_error))
                    raise Exception(f"Both Vertex AI and Google AI API failed. Vertex: {e}, Google: {fallback_error}")
            
            response_text = response.text
            structured_logger.debug("Received response from LLM",
                                   response_length=len(response_text),
                                   topic=request.topic)
            
            content = _extract_json_from_response(response_text)
            
        else:
            structured_logger.info("Using Google AI API (fallback)",
                                 topic=request.topic)
            import google.generativeai as genai
            genai.configure(api_key=google_key)
            model = genai.GenerativeModel('gemini-pro')
            
            response = model.generate_content(prompt)
            response_text = response.text
            
            content = _extract_json_from_response(response_text)
        
        structured_logger.info("Content generated successfully",
                              content_keys=list(content.keys()) if isinstance(content, dict) else None,
                              title=content.get('title', 'N/A')[:60] if isinstance(content, dict) else None,
                              script_length=len(content.get('script', '')) if isinstance(content, dict) else 0,
                              description_length=len(content.get('description', '')) if isinstance(content, dict) else 0,
                              topic=request.topic)
        
        # CRITICAL: If description is missing, create comprehensive fallback
        if not content.get('description'):
            structured_logger.warning("LLM did not generate description field, creating comprehensive fallback",
                                     topic=request.topic)
            
            # Build comprehensive fallback description (2500-3500 characters target)
            topic = research_context.topic
            
            # Opening paragraphs (3-4 paragraphs, no header)
            opening = f"""This episode delves deep into {topic}, a rapidly evolving field that stands at the intersection of cutting-edge research and transformative applications. Recent breakthroughs in this area have revealed fundamental insights that challenge our conventional understanding and open new pathways for scientific discovery and technological innovation.

The significance of {topic} extends far beyond its immediate domain, with implications that span multiple disciplines and industries. As researchers continue to push the boundaries of knowledge, we're witnessing paradigm shifts that reshape how we approach complex problems and understand the underlying mechanisms at play.

What makes this research area particularly compelling is its ability to bridge theoretical foundations with practical applications, creating opportunities for real-world impact while advancing our fundamental understanding. The interdisciplinary nature of this work means that discoveries in one field can catalyze breakthroughs in others, creating a rich ecosystem of innovation and discovery.

In this comprehensive exploration, we'll examine the latest research developments, analyze breakthrough findings, and discuss the far-reaching implications for both science and society. Through detailed analysis of recent publications and cutting-edge methodologies, we'll uncover the revolutionary potential of this field and its capacity to transform our approach to complex challenges."""
            
            # Key Concepts section
            key_concepts = "## Key Concepts Explored\n\n"
            if research_context.key_findings:
                for i, finding in enumerate(research_context.key_findings[:5], 1):
                    key_concepts += f"- **{finding}**: This finding represents a significant advancement in our understanding, with implications that extend across multiple domains and applications.\n"
            else:
                key_concepts += f"- **Recent research developments in {topic}**: Current studies are revealing new insights into fundamental mechanisms and processes that were previously poorly understood.\n"
                key_concepts += f"- **Paradigm shifts and revolutionary findings**: The field is experiencing transformative changes that challenge existing models and open new research directions.\n"
                key_concepts += f"- **Interdisciplinary connections**: Research in {topic} is creating bridges between traditionally separate fields, enabling novel approaches and insights.\n"
                key_concepts += f"- **Practical applications and future directions**: The theoretical advances are finding applications in diverse areas, from technology to medicine to fundamental science.\n"
            
            # Research Insights section (2-3 paragraphs)
            insights = "## Research Insights\n\n"
            if research_context.paradigm_shifts:
                insights += f"Recent research in {topic} has identified several paradigm shifts that fundamentally alter our understanding of the field. "
                insights += f"{research_context.paradigm_shifts[0] if research_context.paradigm_shifts else 'These shifts represent transformative changes in how we conceptualize and approach key problems.'} "
                insights += f"The methodological advances driving these discoveries combine rigorous theoretical frameworks with innovative experimental approaches, enabling researchers to probe deeper into complex systems and uncover previously hidden patterns and mechanisms.\n\n"
            else:
                insights += f"Current research in {topic} is characterized by methodological innovations that enable unprecedented precision and depth of analysis. "
                insights += f"Researchers are employing cutting-edge techniques that combine computational modeling, experimental validation, and theoretical frameworks to address fundamental questions. "
                insights += f"These approaches are revealing new layers of complexity and providing insights that challenge existing paradigms while opening new avenues for investigation.\n\n"
            
            insights += f"The significance of these findings extends beyond their immediate domain, with implications for understanding fundamental processes, developing new technologies, and addressing pressing challenges. "
            insights += f"As the field continues to evolve, we're seeing convergence between different research approaches and the emergence of unified frameworks that can accommodate diverse phenomena and applications."
            
            # Practical Applications section (2-3 paragraphs)
            applications = "## Practical Applications\n\n"
            applications += f"The research developments in {topic} are finding applications across multiple sectors, demonstrating the practical value of fundamental scientific inquiry. "
            applications += f"In technology, these advances are enabling new capabilities and improving performance in systems that rely on understanding complex processes and interactions. "
            applications += f"The insights gained from this research are informing the design of more efficient algorithms, more robust systems, and more effective solutions to real-world problems.\n\n"
            applications += f"Beyond technology, applications are emerging in fields ranging from healthcare to environmental science to industrial processes. "
            applications += f"The interdisciplinary nature of this research means that discoveries can be rapidly translated into practical tools and approaches that address pressing societal needs. "
            applications += f"As our understanding deepens, we can expect to see even more innovative applications that leverage these fundamental insights."
            
            # Future Directions section (2-3 paragraphs)
            future = "## Future Directions\n\n"
            # Extract future_research_directions from paper_analyses
            future_directions = []
            for analysis in research_context.paper_analyses:
                if hasattr(analysis, 'future_research_directions') and analysis.future_research_directions:
                    future_directions.extend(analysis.future_research_directions)
            
            if future_directions:
                future += f"Looking ahead, research in {topic} is poised to explore several exciting directions. "
                future += f"{future_directions[0] if future_directions else 'Future work will likely focus on addressing remaining questions and extending current findings to new contexts.'} "
                future += f"These directions represent both near-term opportunities for immediate impact and long-term trajectories that could fundamentally reshape the field.\n\n"
            else:
                future += f"The future of {topic} research holds tremendous promise, with several emerging directions that could yield transformative insights. "
                future += f"Researchers are beginning to explore connections between previously separate areas, developing unified frameworks that can accommodate diverse phenomena. "
                future += f"These efforts are likely to reveal new principles and mechanisms that will guide future research and applications.\n\n"
            
            future += f"Long-term implications include the potential for paradigm-shifting discoveries that could open entirely new research areas and applications. "
            future += f"As methodological capabilities continue to advance and interdisciplinary collaborations deepen, we can expect to see accelerated progress in understanding fundamental mechanisms and developing practical solutions. "
            future += f"The field is positioned to make significant contributions to both scientific knowledge and societal challenges in the coming years."
            
            # References section
            references = "## References\n\n"
            for i, source in enumerate(research_context.research_sources[:5], 1):
                authors = ', '.join(source.authors[:2]) + (' et al.' if len(source.authors) > 2 else '')
                references += f"- {authors}. {source.title}. {source.source}. "
                if source.doi:
                    references += f"DOI: {source.doi}"
                elif source.url:
                    references += f"Available: {source.url}"
                references += "\n"
            
            # Combine all sections
            fallback_desc = f"""{opening}

{key_concepts}

{insights}

{applications}

{future}

{references}"""
            
            content['description'] = fallback_desc
            structured_logger.info("Created comprehensive fallback description",
                                  description_length=len(fallback_desc),
                                  topic=request.topic)
        
        if not content.get('title') or not content.get('title', '').strip():
            structured_logger.warning("LLM did not generate title field, using topic as fallback",
                                     topic=request.topic)
            content['title'] = request.topic
        elif request.topic and request.topic.lower() not in content.get('title', '').lower():
            structured_logger.info("Generated title doesn't clearly match topic, but keeping LLM-generated title",
                                  generated_title=content.get('title', '')[:60],
                                  topic=request.topic)
        
        content['research_quality_score'] = research_context.research_quality_score
        content['research_sources_used'] = len(research_context.research_sources)
        content['paradigm_shifts'] = research_context.paradigm_shifts
        
        return content
    
    async def determine_canonical_filename(
        self, 
        topic: str, 
        title: str, 
        category: str = None, 
        format_type: str = "feature"
    ) -> str:
        """Determine canonical filename - delegates to canonical service"""
        return await canonical_service.determine_canonical_filename(
            topic=topic,
            title=title,
            category=category,
            format_type=format_type
        )
    
    @retry_upload(max_retries=3, delay=2)
    @retry_upload(max_retries=3, delay=2)
    async def upload_description_to_gcs(self, description: str, canonical_filename: str, title: str = "", topic: str = "", job_id: str = None) -> str:
        """Upload episode description to GCS descriptions folder with hashtags and references"""
        try:
            from google.cloud import storage
            from google.cloud import firestore
            from content_fixes import generate_relevant_hashtags, validate_academic_references
            
            # Initialize GCS client
            storage_client = storage.Client()
            bucket = storage_client.bucket("regal-scholar-453620-r7-podcast-storage")
            
            # CRITICAL: Ensure references section exists - add from job metadata if missing
            if '## References' not in description and job_id:
                structured_logger.warning("References missing in upload_description_to_gcs, adding from job metadata",
                                         job_id=job_id,
                                         canonical_filename=canonical_filename)
                try:
                    db = firestore.Client(project='regal-scholar-453620-r7', database='copernicusai')
                    job_doc = db.collection('podcast_jobs').document(job_id).get()
                    if job_doc.exists:
                        job_data = job_doc.to_dict()
                        references_text = "\n\n## References\n\n"
                        
                        # Try real_citations first
                        real_citations = job_data.get('real_citations', [])
                        if real_citations:
                            for citation in real_citations[:5]:
                                references_text += f"- {citation}\n"
                        else:
                            # Fall back to research_sources_summary
                            research_summary = job_data.get('research_sources_summary', [])
                            if research_summary:
                                for source_info in research_summary[:5]:
                                    title = source_info.get('title', '')
                                    source_type = source_info.get('source', '')
                                    doi = source_info.get('doi', '')
                                    authors_list = source_info.get('authors', [])
                                    authors = ', '.join(authors_list[:2]) + (' et al.' if len(authors_list) > 2 else '') if authors_list else ''
                                    if title:
                                        if authors:
                                            references_text += f"- {authors}. {title}. {source_type}. "
                                        else:
                                            references_text += f"- {title}. {source_type}. "
                                        if doi:
                                            references_text += f"DOI: {doi}"
                                        elif source_info.get('url'):
                                            references_text += f"Available: {source_info.get('url')}"
                                        references_text += "\n"
                        
                        # Insert references before hashtags if they exist, otherwise at the end
                        if '## Hashtags' in description:
                            desc_parts = description.split('## Hashtags')
                            description = desc_parts[0].rstrip() + references_text.rstrip() + '\n\n## Hashtags' + ('## Hashtags'.join(desc_parts[1:]) if len(desc_parts) > 1 else '')
                        else:
                            description = description.rstrip() + references_text.rstrip()
                except Exception as e:
                    structured_logger.error("Could not add references in upload_description_to_gcs",
                                           job_id=job_id,
                                           error=str(e))
                    # Continue without references rather than failing
            
            # Extract topic from canonical filename for hashtag generation
            filename_parts = canonical_filename.split('-')
            if len(filename_parts) >= 2:
                category = filename_parts[1].upper()
                if category == 'BIO':
                    category = 'Biology'
                elif category == 'COMPSCI':
                    category = 'Computer Science'
                elif category == 'PHYS':
                    category = 'Physics'
                elif category == 'MATH':
                    category = 'Mathematics'
                elif category == 'CHEM':
                    category = 'Chemistry'
                else:
                    category = 'Science'
            else:
                category = 'Science'
            
            # Check if hashtags already exist in description
            if "## Hashtags" in description or "#CopernicusAI" in description:
                # Hashtags already added, don't duplicate
                enhanced_description = description
            else:
                # Extract topic from description for better hashtag generation if not provided
                if not topic:
                    topic_match = re.search(r'^#\s*(.+)', description, re.MULTILINE)
                    topic_for_hashtags = topic_match.group(1) if topic_match else ""
                else:
                    topic_for_hashtags = topic
                
                # Generate context-aware hashtags using title, topic, and description
                hashtags = generate_relevant_hashtags(topic_for_hashtags, category, title or "", description)
                
                # Add hashtags section
                enhanced_description = f"{description}\n\n## Hashtags\n{hashtags}"
            
            # Ensure total description doesn't exceed 4000 characters (podcast description limit)
            MAX_DESCRIPTION_LENGTH = 4000
            if len(enhanced_description) > MAX_DESCRIPTION_LENGTH:
                structured_logger.debug("Description too long, trimming",
                                       original_length=len(enhanced_description),
                                       max_length=MAX_DESCRIPTION_LENGTH,
                                       canonical_filename=canonical_filename)
                
                # Try to preserve references and hashtags by trimming the middle content first
                # First, extract References section more precisely
                references_text = ""
                hashtags_text = ""
                main_content = enhanced_description
                
                # Extract References section (look for ## References header)
                if '## References' in enhanced_description:
                    ref_parts = enhanced_description.split('## References', 1)
                    main_content = ref_parts[0]
                    ref_remainder = ref_parts[1]
                    # Get everything until next ## header or end
                    if '##' in ref_remainder:
                        ref_section = ref_remainder.split('##')[0]
                        references_text = '## References' + ref_section
                        # Check if there's a Hashtags section after References
                        if 'Hashtags' in ref_remainder:
                            hashtag_parts = ref_remainder.split('## Hashtags', 1)
                            hashtags_text = '## Hashtags' + hashtag_parts[1] if len(hashtag_parts) > 1 else ""
                    else:
                        # References section goes to end
                        references_text = '## References' + ref_remainder
                elif '## Hashtags' in enhanced_description:
                    # No References but Hashtags exist
                    hashtag_parts = enhanced_description.split('## Hashtags', 1)
                    main_content = hashtag_parts[0]
                    hashtags_text = '## Hashtags' + hashtag_parts[1] if len(hashtag_parts) > 1 else ""
                
                # Split main content into sections for trimming
                sections = main_content.split('\n\n')
                other_sections = [s for s in sections if s.strip()]
                
                # Reserve space for references and hashtags
                reserved_space = len(references_text) + len(hashtags_text) + 100
                
                # Trim other sections to fit
                available_space = MAX_DESCRIPTION_LENGTH - reserved_space
                trimmed_other = []
                current_length = 0
                
                for section in other_sections:
                    if current_length + len(section) + 2 < available_space:
                        trimmed_other.append(section)
                        current_length += len(section) + 2
                    elif current_length < available_space:
                        remaining = available_space - current_length - 20
                        if remaining > 50:
                            trimmed_other.append(section[:remaining] + "...")
                        break
                
                # Rebuild description with full references and hashtags
                main_content_trimmed = '\n\n'.join(trimmed_other)
                if references_text:
                    enhanced_description = main_content_trimmed + '\n\n' + references_text
                else:
                    enhanced_description = main_content_trimmed
                
                if hashtags_text:
                    enhanced_description += '\n\n' + hashtags_text
                elif not hashtags_text and not ("## Hashtags" in enhanced_description or "#CopernicusAI" in enhanced_description):
                    # If hashtags were somehow lost, regenerate them
                    hashtags = generate_relevant_hashtags(topic_for_hashtags, category, title or "", description)
                    enhanced_description += f"\n\n## Hashtags\n{hashtags}"
                
                # Final check - if still too long, trim hashtags section more carefully
                if len(enhanced_description) > MAX_DESCRIPTION_LENGTH:
                    # Keep main content and references, trim hashtags if needed
                    desc_with_refs = main_content_trimmed
                    if references_text:
                        desc_with_refs += '\n\n' + references_text
                    
                    hashtags_available_space = MAX_DESCRIPTION_LENGTH - len(desc_with_refs) - len("\n\n## Hashtags\n")
                    if hashtags_available_space > 50:
                        if hashtags_text:
                            # Extract hashtag content (remove ## Hashtags header)
                            hashtag_content = hashtags_text.replace('## Hashtags', '').strip()
                            if len(hashtag_content) > hashtags_available_space:
                                hashtag_lines = hashtag_content.split('\n')
                                trimmed_hashtags = []
                                current_len = 0
                                for line in hashtag_lines:
                                    if current_len + len(line) + 1 <= hashtags_available_space:
                                        trimmed_hashtags.append(line)
                                        current_len += len(line) + 1
                                    else:
                                        break
                                hashtag_content = '\n'.join(trimmed_hashtags)
                            enhanced_description = desc_with_refs + f"\n\n## Hashtags\n{hashtag_content}"
                        else:
                            # Regenerate hashtags if missing
                            hashtags = generate_relevant_hashtags(topic_for_hashtags, category, title or "", description)
                            hashtag_content = hashtags[:hashtags_available_space] if len(hashtags) > hashtags_available_space else hashtags
                            enhanced_description = desc_with_refs + f"\n\n## Hashtags\n{hashtag_content}"
                    else:
                        enhanced_description = desc_with_refs
            
            # Create description filename
            description_filename = f"{canonical_filename}.md"
            blob = bucket.blob(f"descriptions/{description_filename}")
            
            # Upload enhanced description as markdown
            blob.upload_from_string(enhanced_description, content_type="text/markdown")
            blob.make_public()
            
            # Return public URL
            public_url = f"https://storage.googleapis.com/regal-scholar-453620-r7-podcast-storage/descriptions/{description_filename}"
            structured_logger.info("Enhanced description with hashtags uploaded to GCS",
                                  canonical_filename=canonical_filename,
                                  public_url=public_url)
            return public_url
            
        except Exception as e:
            structured_logger.error("Error uploading description to GCS",
                                   canonical_filename=canonical_filename,
                                   error=str(e))
            return None
    
    @retry_upload(max_retries=3, delay=2)
    async def generate_and_upload_transcript(self, script: str, canonical_filename: str) -> str:
        """Generate and upload transcript to GCS transcripts folder"""
        try:
            from google.cloud import storage
            
            # Initialize GCS client
            storage_client = storage.Client()
            bucket = storage_client.bucket("regal-scholar-453620-r7-podcast-storage")
            
            # Create clean transcript from script
            transcript_lines = []
            transcript_lines.append(f"# {canonical_filename.upper()} - Transcript\n")
            transcript_lines.append(f"**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            transcript_lines.append(f"**Show:** Copernicus AI: Frontiers of Science\n\n")
            
            # Parse script into clean transcript format
            lines = script.split('\n')
            for line in lines:
                line = line.strip()
                if not line:
                    continue
                    
                # Look for speaker labels and format nicely
                speaker_match = re.match(r'^(HOST|EXPERT|QUESTIONER|CORRESPONDENT):\s*(.*)', line, re.IGNORECASE)
                if speaker_match:
                    speaker = speaker_match.group(1).upper()
                    text = speaker_match.group(2).strip()
                    if text:
                        # Clean text for transcript
                        clean_text = re.sub(r'\*\*(.*?)\*\*', r'\1', text)  # Remove bold
                        clean_text = re.sub(r'\*(.*?)\*', r'\1', clean_text)  # Remove italic
                        clean_text = re.sub(r'[{}"\[\]]', '', clean_text)  # Remove JSON chars
                        clean_text = re.sub(r'\s+', ' ', clean_text).strip()  # Normalize spaces
                        
                        transcript_lines.append(f"**{speaker}:** {clean_text}\n\n")
                else:
                    # Handle non-speaker lines
                    if len(line) > 10 and not line.startswith('```'):
                        clean_line = re.sub(r'[{}"\[\]]', '', line)
                        transcript_lines.append(f"{clean_line}\n\n")
            
            # Join all lines
            transcript_content = ''.join(transcript_lines)
            
            # Create transcript filename
            transcript_filename = f"{canonical_filename}-transcript.md"
            blob = bucket.blob(f"transcripts/{transcript_filename}")
            
            # Upload transcript as markdown
            blob.upload_from_string(transcript_content, content_type="text/markdown")
            blob.make_public()
            
            # Return public URL
            public_url = f"https://storage.googleapis.com/regal-scholar-453620-r7-podcast-storage/transcripts/{transcript_filename}"
            structured_logger.info("Transcript uploaded to GCS",
                                  canonical_filename=canonical_filename,
                                  public_url=public_url)
            return public_url
            
        except Exception as e:
            structured_logger.error("Error generating/uploading transcript",
                                   canonical_filename=canonical_filename,
                                   error=str(e))
            return None
    
    async def get_openai_api_key_from_secret_manager(self) -> str:
        """Get OpenAI API key from Secret Manager"""
        try:
            from google.cloud import secretmanager
            client = secretmanager.SecretManagerServiceClient()
            name = f"projects/{GCP_PROJECT_ID}/secrets/openai-api-key/versions/latest"
            response = client.access_secret_version(request={"name": name})
            return response.payload.data.decode("UTF-8").strip()
        except Exception as e:
            structured_logger.warning("Could not get OpenAI API key from Secret Manager",
                                      error=str(e))
            import os
            return os.getenv("OPENAI_API_KEY", "")
    
    async def generate_fallback_thumbnail(self, canonical_filename: str, topic: str) -> str:
        """Generate fallback thumbnail when DALL-E is not available"""
        try:
            from PIL import Image, ImageDraw, ImageFilter
            from google.cloud import storage
            import random
            import math
            import io
            
            structured_logger.info("Generating fallback thumbnail",
                                  canonical_filename=canonical_filename,
                                  topic=topic)
            
            # Create sophisticated visual thumbnail (1792x1792)
            img = Image.new('RGB', (1792, 1792), color='#0a0a1a')
            draw = ImageDraw.Draw(img)
            
            # Create gradient background
            for y in range(1792):
                color_intensity = int(20 + (y / 1792) * 60)
                color = (color_intensity, color_intensity // 2, min(255, color_intensity * 2))
                draw.line([(0, y), (1792, y)], fill=color)
            
            # Add dynamic scientific visualization
            center_x, center_y = 896, 896
            
            # Create interconnected particle system
            particles = []
            for i in range(40):
                angle = (i / 40) * 2 * math.pi
                radius = 200 + random.randint(-100, 200)
                x = center_x + int(radius * math.cos(angle))
                y = center_y + int(radius * math.sin(angle))
                size = random.randint(6, 25)
                particles.append((x, y, size))
            
            # Draw connections
            for i, (x1, y1, _) in enumerate(particles):
                for j, (x2, y2, _) in enumerate(particles[i+1:], i+1):
                    if random.random() < 0.3:  # 30% chance of connection
                        alpha = max(0, 255 - int(((x1-x2)**2 + (y1-y2)**2)**0.5 / 3))
                        if alpha > 50:
                            color = (alpha//3, alpha//2, alpha)
                            draw.line([(x1, y1), (x2, y2)], fill=color, width=2)
            
            # Draw particles
            for x, y, size in particles:
                color = (random.randint(100, 255), random.randint(150, 255), 255)
                draw.ellipse([x-size, y-size, x+size, y+size], fill=color)
                # Add glow effect
                glow_size = size + 5
                glow_color = (color[0]//3, color[1]//3, color[2]//3)
                draw.ellipse([x-glow_size, y-glow_size, x+glow_size, y+glow_size], fill=glow_color)
            
            # Apply subtle blur for professional look
            img = img.filter(ImageFilter.GaussianBlur(radius=1.5))
            
            # Upload to GCS
            storage_client = storage.Client()
            bucket = storage_client.bucket(self.bucket_name)
            
            # Save image to bytes
            img_bytes = io.BytesIO()
            img.save(img_bytes, format='JPEG', quality=95)
            img_bytes.seek(0)
            
            # Upload to GCS
            thumbnail_filename = f"{canonical_filename}-fallback-thumb.jpg"
            blob = bucket.blob(f"thumbnails/{thumbnail_filename}")
            blob.upload_from_file(img_bytes, content_type="image/jpeg")
            blob.make_public()
            
            public_url = f"https://storage.googleapis.com/{self.bucket_name}/thumbnails/{thumbnail_filename}"
            structured_logger.info("Fallback thumbnail uploaded",
                                  canonical_filename=canonical_filename,
                                  public_url=public_url)
            return public_url
            
        except Exception as e:
            structured_logger.error("Error generating fallback thumbnail",
                                   canonical_filename=canonical_filename,
                                   error=str(e))
            # Return a default thumbnail URL
            return "https://storage.googleapis.com/regal-scholar-453620-r7-podcast-storage/images/copernicus-original-portrait.jpg"
    
    @retry_upload(max_retries=3, delay=2)
    async def generate_and_upload_thumbnail(
        self, 
        title: str, 
        topic: str, 
        canonical_filename: str
    ) -> str:
        """Generate AI thumbnail using DALL-E 3 with maximum resolution for podcast platforms"""
        try:
            import requests
            from google.cloud import storage
            import io
            import re
            
            # Initialize GCS client
            storage_client = storage.Client()
            bucket = storage_client.bucket(self.bucket_name)
            
            # Get OpenAI API key from Secret Manager for DALL-E
            openai_api_key = await self.get_openai_api_key_from_secret_manager()
            if not openai_api_key:
                structured_logger.warning("No OpenAI API key available for DALL-E thumbnail generation, using fallback",
                                         canonical_filename=canonical_filename)
                return await self.generate_fallback_thumbnail(canonical_filename, topic)
            
            # Extract category from canonical filename for more specific visuals
            # Each discipline has a DISTINCT visual style and color palette
            category_styles = {
                "bio": {
                    "visual_elements": "intricate biological structures, cellular networks, DNA double helices, protein complexes, neural pathways, microscopic organisms, organic cellular membranes, biomolecular interactions, living tissue patterns",
                    "color_palette": "vibrant greens and blues (nature's palette), with accents of soft purple and warm yellows. Organic, life-affirming colors. Rich emerald greens transitioning to deep ocean blues, with biological purple accents",
                    "style": "organic and flowing, biomorphic shapes, natural biological patterns, cellular textures, living tissue aesthetics, microscopic world visualization",
                    "mood": "vital, dynamic, life-sustaining, biological complexity, natural organization"
                },
                "chem": {
                    "visual_elements": "molecular structures, chemical bonds, crystal lattices, reaction pathways, atomic orbitals, electron clouds, molecular models, chemical formulas visualized, periodic table patterns, bond formations",
                    "color_palette": "cool blues and purples with bright accent colors (reaction energies). Atomic blues, molecular purples, with vibrant orange and yellow energy bursts for reactions. Clean, precise color schemes",
                    "style": "geometric and precise, molecular symmetry, crystalline structures, atomic precision, clean lines and structured forms, laboratory aesthetics",
                    "mood": "precise, transformative, energetic reactions, molecular precision, structured complexity"
                },
                "compsci": {
                    "visual_elements": "neural networks, data streams, algorithmic patterns, binary code, circuit patterns, digital networks, code visualizations, data flow diagrams, network topologies, computational graphs, binary matrices",
                    "color_palette": "digital blues and cyans with electric accents. Neon blues, electric cyan, digital greens, with bright white and electric purple highlights. High-tech, digital aesthetics",
                    "style": "digital and algorithmic, pixel-perfect, network diagrams, data visualization aesthetics, circuit board patterns, tech-forward design",
                    "mood": "innovative, computational, data-driven, high-tech, algorithmic precision"
                },
                "math": {
                    "visual_elements": "geometric patterns, fractal structures, mathematical equations visualized, abstract symmetries, topological surfaces, geometric transformations, mathematical proofs visualized, abstract mathematical spaces, geometric constructions, symmetry patterns",
                    "color_palette": "elegant monochromatic with mathematical accents. Deep purples, rich blues, elegant grays, with precise white and gold mathematical symbols. Clean, abstract, elegant",
                    "style": "geometric and abstract, perfect symmetry, mathematical elegance, topological beauty, abstract geometric forms, precise mathematical visualization",
                    "mood": "elegant, abstract, perfectly structured, mathematical beauty, timeless precision"
                },
                "phys": {
                    "visual_elements": "quantum fields, particle interactions, wave functions, electromagnetic fields, cosmic structures, energy patterns, particle accelerations, wave interferences, quantum probability clouds, cosmic phenomena, energy transformations",
                    "color_palette": "cosmic purples and deep space blues with energetic highlights. Deep space purples, cosmic blues, with bright white energy bursts and golden particle trails. Cosmic and energetic",
                    "style": "energetic and cosmic, particle effects, wave patterns, quantum field visualizations, cosmic phenomena, energy flows, dynamic motion",
                    "mood": "energetic, cosmic, fundamental forces, quantum mysteries, universal scale"
                }
            }
            
            category = None
            if canonical_filename:
                parts = canonical_filename.split("-")
                if len(parts) >= 2:
                    cat_match = parts[1] if len(parts) > 1 else None
                    if cat_match in category_styles:
                        category = cat_match
            
            # Get category-specific style
            if category and category in category_styles:
                style_config = category_styles[category]
                visual_elements = style_config["visual_elements"]
                color_palette = style_config["color_palette"]
                style_description = style_config["style"]
                mood_description = style_config["mood"]
            else:
                # Default fallback
                visual_elements = "abstract scientific structures, flowing data streams, particle effects, neural networks, quantum field representations"
                color_palette = "deep cosmic blues transitioning to vibrant cyan and electric blue, with accents of luminous white and subtle purple"
                style_description = "modern scientific illustration"
                mood_description = "cutting-edge scientific discovery"
            
            # Extract specific visual concepts from title for more targeted imagery
            title_keywords = []
            title_lower = title.lower()
            
            # Map title keywords to specific visual concepts
            visual_keyword_mapping = {
                "supramolecular": "supramolecular assemblies, molecular self-organization, host-guest complexes, intricate molecular networks",
                "self-assembly": "self-assembling structures, dynamic molecular organization, spontaneous pattern formation, hierarchical structures",
                "metalloenzyme": "metallic enzyme active sites, metal-ion coordination complexes, catalytic metal centers, biomolecular metal clusters",
                "bioinspired": "nature-inspired structures, biomimetic designs, biological patterns, evolutionary design principles",
                "catalysis": "catalytic reaction mechanisms, active site interactions, molecular transformations, reaction pathways",
                "graph neural": "neural network graphs, interconnected nodes, data flow patterns, network topology visualizations",
                "federated learning": "distributed computational networks, privacy-preserving data flows, decentralized learning systems",
                "quantum sensing": "quantum measurement devices, precision sensors, quantum field detectors, metrology instruments",
                "topological": "topological structures, geometric transformations, shape classifications, persistent homology representations",
                "epigenetic": "epigenetic modifications, DNA methylation patterns, chromatin structures, gene expression networks",
                "immunotherapy": "immune cell interactions, T-cell activation, antibody structures, cancer cell targeting mechanisms",
                "optimization": "algorithmic optimization paths, gradient flows, search space visualizations, convergence patterns",
                "persistent homology": "topological persistence diagrams, barcode representations, shape analysis, multi-scale structures"
            }
            
            # Find matching visual concepts from title
            title_specific_visuals = []
            for keyword, visuals in visual_keyword_mapping.items():
                if keyword in title_lower:
                    title_specific_visuals.append(visuals)
                    title_keywords.append(keyword)
            
            # Combine category visuals with title-specific visuals
            if title_specific_visuals:
                specific_visuals = ", ".join(title_specific_visuals[:3])  # Limit to 3 most relevant
                enhanced_visual_elements = f"{specific_visuals}. Additionally include {visual_elements}"
            else:
                enhanced_visual_elements = visual_elements
            
            # Create enhanced DALL-E prompt with title-specific details
            dalle_prompt = f"""Create a breathtaking scientific visualization for a research podcast episode titled "{title}".

The podcast explores: {topic}

Visual Style: Ultra-modern scientific illustration, photorealistic 3D rendering with depth and dimension. Professional digital art with cinematic lighting and dramatic composition.

Key Visual Elements: {enhanced_visual_elements} specifically related to "{title}". Focus on the most distinctive and recognizable visual concepts from the title. Dynamic, flowing compositions that suggest motion and discovery. Include subtle abstract patterns that represent breakthrough thinking and paradigm shifts.

Color Palette: Rich, sophisticated gradients - deep cosmic blues transitioning to vibrant cyan and electric blue, with accents of luminous white and subtle purple. High contrast for maximum visual impact. Professional color grading.

Composition: Square format optimized for podcast platforms. Centered focal point with surrounding elements creating visual flow. Balanced negative space. Depth-of-field effect with foreground elements sharp and background slightly blurred for dimension.

Technical Quality: Ultra-high resolution, crystal-clear detail, professional photography quality. No pixelation or artifacts. Suitable for high-DPI displays and large format printing.

Important: Absolutely NO text, NO words, NO titles, NO labels. Pure visual scientific concept art that tells a story through imagery alone.

Mood and Atmosphere: Cutting-edge scientific discovery, innovation, breakthrough research, future technology, paradigm-shifting insights. Convey the excitement and importance of scientific advancement."""
            
            # Generate image with DALL-E 3
            structured_logger.info("Generating DALL-E 3 thumbnail",
                                  canonical_filename=canonical_filename,
                                  topic=topic,
                                  category=category or "generic")
            
            headers = {
                "Authorization": f"Bearer {openai_api_key}",
                "Content-Type": "application/json"
            }
            
            payload = {
                "model": "dall-e-3",
                "prompt": dalle_prompt,
                "n": 1,
                "size": "1024x1024",  # Square format required for podcast platforms (DALL-E 3 max square)
                "quality": "hd",
                "style": "vivid"
            }
            
            response = requests.post(
                "https://api.openai.com/v1/images/generations",
                headers=headers,
                json=payload,
                timeout=60
            )
            
            if response.status_code == 200:
                result = response.json()
                image_url = result['data'][0]['url']
                
                # Download the generated image
                img_response = requests.get(image_url, timeout=30)
                if img_response.status_code == 200:
                    # Upload to GCS
                    thumbnail_filename = f"{canonical_filename}-thumb.jpg"
                    blob = bucket.blob(f"thumbnails/{thumbnail_filename}")
                    blob.upload_from_string(img_response.content, content_type="image/jpeg")
                    blob.make_public()
                    
                    public_url = f"https://storage.googleapis.com/{self.bucket_name}/thumbnails/{thumbnail_filename}"
                    structured_logger.info("DALL-E thumbnail uploaded",
                                         canonical_filename=canonical_filename,
                                         public_url=public_url)
                    return public_url
                else:
                    structured_logger.warning("Failed to download DALL-E image, using fallback",
                                             canonical_filename=canonical_filename,
                                             status_code=img_response.status_code)
                    return await self.generate_fallback_thumbnail(canonical_filename, topic)
            else:
                structured_logger.warning("DALL-E API error, using fallback",
                                         canonical_filename=canonical_filename,
                                         status_code=response.status_code,
                                         error_text=response.text[:200] if response.text else None)
                return await self.generate_fallback_thumbnail(canonical_filename, topic)
        
        except Exception as e:
            structured_logger.error("Error generating/uploading thumbnail, using fallback",
                                   canonical_filename=canonical_filename,
                                   error=str(e))
            return await self.generate_fallback_thumbnail(canonical_filename, topic)
    
    async def generate_episode_images(
        self,
        title: str,
        topic: str,
        canonical_filename: str,
        description: str = "",
        num_images: int = 2
    ) -> List[str]:
        """
        Generate 1-2 additional images for the episode (beyond the thumbnail).
        These are still images that can be displayed during audio playback.
        
        Args:
            title: Episode title
            topic: Episode topic
            canonical_filename: Canonical filename for the episode
            description: Episode description (optional, for context)
            num_images: Number of images to generate (1-2, default 2)
        
        Returns:
            List of public image URLs
        """
        image_urls = []
        
        try:
            import requests
            from google.cloud import storage
            
            # Limit to 1-2 images
            num_images = max(1, min(2, num_images))
            
            # Initialize GCS client
            storage_client = storage.Client()
            bucket = storage_client.bucket(self.bucket_name)
            
            # Get OpenAI API key
            openai_api_key = await self.get_openai_api_key_from_secret_manager()
            if not openai_api_key:
                structured_logger.warning("No OpenAI API key for episode images, skipping",
                                         canonical_filename=canonical_filename)
                return []
            
            # Extract category for style consistency
            category = None
            if canonical_filename:
                parts = canonical_filename.split("-")
                if len(parts) >= 2:
                    category = parts[1] if len(parts) > 1 else None
            
            # Generate images with different visual focuses
            image_prompts = []
            
            if num_images == 1:
                # Single image: comprehensive overview
                image_prompts.append(
                    f"""Create a detailed scientific visualization for a research podcast episode titled "{title}".

The podcast explores: {topic}

Visual Style: Professional scientific illustration, photorealistic 3D rendering. High-quality digital art with cinematic lighting.

Key Visual Elements: Abstract scientific concepts related to "{title}". Dynamic composition showing breakthrough research and paradigm-shifting discoveries. Include visual metaphors for innovation and scientific advancement.

Color Palette: Rich, sophisticated gradients - deep blues transitioning to vibrant cyan, with accents of white and purple. High contrast for visual impact.

Composition: Landscape format (16:9 ratio), optimized for display during audio playback. Centered focal point with surrounding elements creating visual flow.

Technical Quality: Ultra-high resolution, crystal-clear detail. No text, words, titles, or labels. Pure visual scientific concept art."""
                )
            else:
                # Two images: different aspects
                # Image 1: Conceptual overview
                image_prompts.append(
                    f"""Create a conceptual scientific visualization for a research podcast episode titled "{title}".

The podcast explores: {topic}

Visual Style: Abstract scientific illustration, modern 3D rendering. Professional digital art.

Key Visual Elements: High-level conceptual representation of "{title}". Abstract patterns representing breakthrough thinking, paradigm shifts, and revolutionary discoveries.

Color Palette: Deep cosmic blues with vibrant cyan accents and subtle purple highlights.

Composition: Landscape format (16:9), wide view. Balanced composition with visual flow.

Technical Quality: Ultra-high resolution. No text, words, or labels. Pure visual concept art."""
                )
                
                # Image 2: Detailed technical view
                image_prompts.append(
                    f"""Create a detailed technical scientific visualization for a research podcast episode titled "{title}".

The podcast explores: {topic}

Visual Style: Detailed technical illustration, precise scientific rendering. Professional digital art with technical accuracy.

Key Visual Elements: Technical details and specific mechanisms related to "{title}". Focus on the intricate scientific processes, molecular structures, or computational patterns that make this research significant.

Color Palette: Rich technical blues with precise white highlights and electric cyan details.

Composition: Landscape format (16:9), detailed view. Technical precision with visual appeal.

Technical Quality: Ultra-high resolution. No text, words, or labels. Pure visual technical concept art."""
                )
            
            # Generate each image
            for i, prompt in enumerate(image_prompts):
                try:
                    structured_logger.info("Generating episode image",
                                         canonical_filename=canonical_filename,
                                         image_number=i+1,
                                         total_images=num_images)
                    
                    headers = {
                        "Authorization": f"Bearer {openai_api_key}",
                        "Content-Type": "application/json"
                    }
                    
                    payload = {
                        "model": "dall-e-3",
                        "prompt": prompt,
                        "n": 1,
                        "size": "1792x1024",  # Landscape format for display during playback
                        "quality": "hd",
                        "style": "vivid"
                    }
                    
                    response = requests.post(
                        "https://api.openai.com/v1/images/generations",
                        headers=headers,
                        json=payload,
                        timeout=60
                    )
                    
                    if response.status_code == 200:
                        result = response.json()
                        image_url = result['data'][0]['url']
                        
                        # Download and upload to GCS
                        img_response = requests.get(image_url, timeout=30)
                        if img_response.status_code == 200:
                            image_filename = f"{canonical_filename}-image-{i+1}.jpg"
                            blob = bucket.blob(f"episode-images/{image_filename}")
                            blob.upload_from_string(img_response.content, content_type="image/jpeg")
                            blob.make_public()
                            
                            public_url = f"https://storage.googleapis.com/{self.bucket_name}/episode-images/{image_filename}"
                            image_urls.append(public_url)
                            
                            structured_logger.info("Episode image uploaded",
                                                 canonical_filename=canonical_filename,
                                                 image_number=i+1,
                                                 public_url=public_url)
                        else:
                            structured_logger.warning("Failed to download episode image",
                                                     canonical_filename=canonical_filename,
                                                     image_number=i+1,
                                                     status_code=img_response.status_code)
                    else:
                        structured_logger.warning("DALL-E API error for episode image",
                                                 canonical_filename=canonical_filename,
                                                 image_number=i+1,
                                                 status_code=response.status_code)
                
                except Exception as e:
                    structured_logger.error("Error generating episode image",
                                          canonical_filename=canonical_filename,
                                          image_number=i+1,
                                          error=str(e))
                    # Continue with other images even if one fails
            
            structured_logger.info("Episode images generation complete",
                                 canonical_filename=canonical_filename,
                                 images_generated=len(image_urls),
                                 requested=num_images)
            
            return image_urls
        
        except Exception as e:
            structured_logger.error("Error in generate_episode_images",
                                 canonical_filename=canonical_filename,
                                 error=str(e))
            return []
    
    async def run_podcast_generation_job(
        self, 
        job_id: str, 
        request: PodcastRequest, 
        subscriber_id: Optional[str] = None
    ):
        """
        Process research-driven podcast generation with comprehensive research integration
        
        This is the main orchestrator function that coordinates the entire podcast generation pipeline:
        1. Comprehensive Research Discovery
        2. Research-Driven Content Generation (2-Speaker Format)
        3. Content Validation
        4. Audio Synthesis with ElevenLabs
        5. [VIDEO EXTENSION POINT] - Future video generation phase
        6. File Uploads (transcript, description, thumbnail)
        7. Episode Catalog Creation
        8. Email Notifications
        
        Architecture supports future video expansion:
        - Video generation can be inserted after audio generation (Phase 5)
        - All existing functionality remains intact
        - Audio-first approach maintained
        """
        # Comprehensive logging setup
        start_time = time.time()
        initial_memory = psutil.virtual_memory().percent
        
        structured_logger.info("Starting COPERNICUS RESEARCH-DRIVEN podcast generation pipeline",
                              job_id=job_id,
                              initial_memory_percent=round(initial_memory, 1),
                              topic=request.topic,
                              category=request.category,
                              format_type=request.format_type,
                              duration=request.duration,
                              host_voice_id=request.host_voice_id or "default",
                              expert_voice_id=request.expert_voice_id or "default")
        
        # Get subscriber email for notifications
        subscriber_email = DEFAULT_SUBSCRIBER_EMAIL  # Default fallback
        if subscriber_id and db:
            try:
                subscriber_doc = db.collection('subscribers').document(subscriber_id).get()
                if subscriber_doc.exists:
                    subscriber_data = subscriber_doc.to_dict()
                    subscriber_email = subscriber_data.get('email', subscriber_email)
                    structured_logger.info("Subscriber email retrieved",
                                          job_id=job_id,
                                          subscriber_email=subscriber_email)
            except Exception as e:
                structured_logger.warning("Could not get subscriber email, using default",
                                         job_id=job_id,
                                         error=str(e),
                                         default_email=subscriber_email)
        
        if not db:
            structured_logger.error("Firestore not available, cannot update job",
                                   job_id=job_id)
            return
        
        job_ref = db.collection('podcast_jobs').document(job_id)
        request_snapshot = request.model_dump()
        
        try:
            # ═════════════════════════════════════════════════════════════════
            # 🔬 PHASE 1: COMPREHENSIVE RESEARCH (NEW - Copernicus Spirit!)
            # ═════════════════════════════════════════════════════════════════
            structured_logger.info("PHASE 1: Starting comprehensive research discovery", job_id=job_id)
            
            job_ref.update({'status': 'researching', 'updated_at': datetime.utcnow().isoformat()})
            
            # Initialize research integrator
            google_key = get_google_api_key()
            if not google_key:
                raise Exception("Google API key not available for research")
            
            research_integrator = PodcastResearchIntegrator(google_key)
            
            try:
                # Perform comprehensive research
                research_context = await asyncio.wait_for(
                    research_integrator.comprehensive_research_for_podcast(
                        topic=request.topic,
                        additional_context=request.additional_instructions or "",
                        source_links=request.source_links or [],
                        expertise_level=request.expertise_level,
                        require_minimum_sources=3  # FAIL FAST if insufficient research
                    ),
                    timeout=300  # 5 minute timeout for research
                )
                
                structured_logger.info("Research completed successfully",
                                      job_id=job_id,
                                      quality_score=round(research_context.research_quality_score, 1),
                                      sources_count=len(research_context.research_sources),
                                      paradigm_shifts_count=len(research_context.paradigm_shifts))
                
                # Store research metadata in job (including sources for references)
                research_sources_summary = []
                for source in research_context.research_sources[:10]:
                    research_sources_summary.append({
                        'title': source.title,
                        'source': source.source,
                        'doi': source.doi,
                        'url': source.url,
                        'authors': source.authors[:3]  # Store first 3 authors
                    })
                
                job_ref.update({
                    'research_sources_count': len(research_context.research_sources),
                    'research_quality_score': research_context.research_quality_score,
                    'paradigm_shifts_count': len(research_context.paradigm_shifts),
                    'research_sources_summary': research_sources_summary,
                    'real_citations': research_context.real_citations[:10],  # Store citations for references
                    'updated_at': datetime.utcnow().isoformat()
                })
                
            except Exception as e:
                error_msg = str(e)
                structured_logger.error("Research phase failed",
                                      job_id=job_id,
                                      error=error_msg)
                
                # Update job with failure
                job_ref.update({
                    'status': 'failed',
                    'error': f"Research failed: {error_msg}",
                    'error_type': 'insufficient_research',
                    'updated_at': datetime.utcnow().isoformat()
                })
                
                # Send failure email
                if self.email_service:
                    await self.email_service.send_podcast_ready_email(
                        to_email=subscriber_email,
                        podcast_title=f"Research Failed: {request.topic}",
                        description=f"Unable to find sufficient research sources for '{request.topic}'. {error_msg}",
                        audio_url="",
                        error_message=error_msg
                    )
                
                return  # EXIT - Cannot proceed without research
            
            # ═════════════════════════════════════════════════════════════════
            # 🎙️ PHASE 2: RESEARCH-DRIVEN CONTENT GENERATION (2-Speaker Format)
            # ═════════════════════════════════════════════════════════════════
            structured_logger.info("PHASE 2: Generating 2-speaker podcast from research", job_id=job_id)
            
            job_ref.update({'status': 'generating_content', 'updated_at': datetime.utcnow().isoformat()})
            
            async with with_step("content_generation", job_id, 
                               topic=request.topic, 
                               category=request.category,
                               duration=request.duration):
                
                content_memory_before = psutil.virtual_memory().percent
                structured_logger.info("Starting research-driven content generation", 
                                      job_id=job_id,
                                      topic=request.topic,
                                      research_quality=research_context.research_quality_score,
                                      memory_before=content_memory_before)
                
                # Retry loop for content generation - regenerate if script is too short
                max_retries = 2
                content = None
                min_words = calculate_minimum_words_for_duration(request.duration)
                
                for attempt in range(max_retries + 1):
                    try:
                        # Generate 2-speaker podcast from research
                        generated_content = await asyncio.wait_for(
                            self.generate_content_from_research_context(request, research_context, google_key, retry_attempt=attempt),
                            timeout=600  # 10 minute timeout for content generation
                        )
                        
                        # Check if script is long enough
                        script = generated_content.get('script', '') if isinstance(generated_content, dict) else ''
                        word_count = len(script.split()) if script else 0
                        
                        if word_count >= min_words:
                            content = generated_content
                            structured_logger.info(f"Content generation succeeded on attempt {attempt + 1}",
                                                  job_id=job_id,
                                                  word_count=word_count,
                                                  min_required=min_words)
                            break
                        else:
                            if attempt < max_retries:
                                structured_logger.warning(f"Script too short on attempt {attempt + 1}, retrying with stronger prompt",
                                                         job_id=job_id,
                                                         word_count=word_count,
                                                         min_required=min_words,
                                                         attempt=attempt + 1,
                                                         max_retries=max_retries + 1)
                                await asyncio.sleep(2)  # Brief delay before retry
                            else:
                                # Last attempt - use what we have and let validation catch it
                                content = generated_content
                                structured_logger.warning("Script too short after all retries, proceeding to validation",
                                                         job_id=job_id,
                                                         word_count=word_count,
                                                         min_required=min_words)
                    
                    except asyncio.TimeoutError:
                        if attempt < max_retries:
                            structured_logger.warning(f"Content generation timed out on attempt {attempt + 1}, retrying",
                                                     job_id=job_id,
                                                     attempt=attempt + 1)
                            await asyncio.sleep(2)
                            continue
                        else:
                            structured_logger.error("Content generation timed out after all retries", 
                                                   job_id=job_id,
                                                   timeout_seconds=600)
                            raise Exception("Content generation timed out after 10 minutes")
                    except Exception as e:
                        if attempt < max_retries:
                            structured_logger.warning(f"Content generation failed on attempt {attempt + 1}, retrying",
                                                     job_id=job_id,
                                                     error=str(e),
                                                     attempt=attempt + 1)
                            await asyncio.sleep(2)
                            continue
                        else:
                            structured_logger.error("Content generation failed after all retries", 
                                                   job_id=job_id,
                                                   error=str(e),
                                                   error_type=type(e).__name__)
                            raise
                
                if not content:
                    raise Exception("Failed to generate content after all retry attempts")
                
                content_memory_after = psutil.virtual_memory().percent
                
                # CRITICAL: Ensure title exists - use topic as fallback if missing
                if isinstance(content, dict):
                    if not content.get('title') or not content.get('title', '').strip():
                        structured_logger.warning("LLM did not generate valid title, using topic as fallback",
                                                 topic=request.topic)
                        content['title'] = request.topic
                
                structured_logger.info("Content generation completed successfully", 
                                      job_id=job_id,
                                      memory_before=content_memory_before,
                                      memory_after=content_memory_after,
                                      memory_delta=content_memory_after - content_memory_before,
                                      content_type=type(content).__name__,
                                      content_keys=list(content.keys()) if isinstance(content, dict) else None,
                                      title=content.get('title', 'N/A')[:60] if isinstance(content, dict) else 'N/A',
                                      script_word_count=len(content.get('script', '').split()) if isinstance(content, dict) else 0)
            
            # ═════════════════════════════════════════════════════════════════
            # ✅ PHASE 3: VALIDATE CONTENT (NO FAKE FALLBACKS!)
            # ═════════════════════════════════════════════════════════════════
            structured_logger.info("PHASE 3: Validating content quality", job_id=job_id)
            
            # CRITICAL: Validate that content was actually generated
            if not content or not isinstance(content, dict):
                raise Exception("Content generation returned invalid data structure")
            
            if 'description' not in content or not content.get('description'):
                raise Exception("Content generation failed - no description produced. Cannot use fake template.")
            
            if 'script' not in content or not content.get('script'):
                raise Exception("Content generation failed - no script produced. Cannot use fake template.")
            
            if 'title' not in content or not content.get('title'):
                raise Exception("Content generation failed - no title produced. Cannot use fake template.")
            
            # Generate relevant hashtags
            content['hashtags'] = generate_relevant_hashtags(
                request.topic, 
                request.category, 
                content.get('title', ''), 
                content['description']
            )
            
            # Check if description already has hashtags and references, if not add them
            if '## Hashtags' not in content['description'] and '---' not in content['description']:
                # Add hashtags and closing message
                content['description'] += f"""

## Hashtags
{content['hashtags']}

"""
            
            # CRITICAL: Ensure references section exists - add from research_context if missing
            if '## References' not in content['description']:
                # References are missing - add them from research_context
                structured_logger.warning("LLM did not include References section, adding from research context",
                                         job_id=job_id,
                                         topic=request.topic)
                
                # Build references from research_context (available from research phase)
                references_text = "\n\n## References\n\n"
                references_added = False
                
                # Try to use research_context directly (it should be in scope)
                try:
                    # research_context is defined in the outer scope above
                    if research_context:
                        # Use real_citations first (already formatted)
                        if research_context.real_citations:
                            for citation in research_context.real_citations[:5]:
                                references_text += f"- {citation}\n"
                            references_added = True
                        elif research_context.research_sources:
                            # Build from research_sources
                            for source in research_context.research_sources[:5]:
                                authors = ', '.join(source.authors[:2]) + (' et al.' if len(source.authors) > 2 else '')
                                references_text += f"- {authors}. {source.title}. {source.source}. "
                                if source.doi:
                                    references_text += f"DOI: {source.doi}"
                                elif source.url:
                                    references_text += f"Available: {source.url}"
                                references_text += "\n"
                            references_added = True
                except NameError:
                    # research_context not in scope, use fallback
                    structured_logger.warning("research_context not in scope, using job metadata",
                                             job_id=job_id)
                    pass
                except Exception as e:
                    structured_logger.warning("Error accessing research_context, using job metadata",
                                             job_id=job_id,
                                             error=str(e))
                    pass
                
                # Fallback: get from job metadata if research_context wasn't accessible
                if not references_added:
                    try:
                        job_doc = db.collection('podcast_jobs').document(job_id).get()
                        if job_doc.exists:
                            job_data = job_doc.to_dict()
                            # Try real_citations first
                            real_citations = job_data.get('real_citations', [])
                            if real_citations:
                                for citation in real_citations[:5]:
                                    references_text += f"- {citation}\n"
                                references_added = True
                            else:
                                # Fall back to research_sources_summary
                                research_summary = job_data.get('research_sources_summary', [])
                                if research_summary:
                                    for source_info in research_summary[:5]:
                                        title = source_info.get('title', '')
                                        source_type = source_info.get('source', '')
                                        doi = source_info.get('doi', '')
                                        authors_list = source_info.get('authors', [])
                                        authors = ', '.join(authors_list[:2]) + (' et al.' if len(authors_list) > 2 else '') if authors_list else ''
                                        if title:
                                            if authors:
                                                references_text += f"- {authors}. {title}. {source_type}. "
                                            else:
                                                references_text += f"- {title}. {source_type}. "
                                            if doi:
                                                references_text += f"DOI: {doi}"
                                            elif source_info.get('url'):
                                                references_text += f"Available: {source_info.get('url')}"
                                            references_text += "\n"
                                    references_added = True
                    except Exception as e:
                        structured_logger.error("Could not retrieve research sources from job metadata",
                                               job_id=job_id,
                                               error=str(e))
                
                # Last resort: add warning message
                if not references_added:
                    structured_logger.error("CRITICAL: Could not add references - no research data available",
                                           job_id=job_id)
                    references_text += "Research references from the sources used for this episode.\n"
                
                # Insert references before hashtags if they exist, otherwise at the end
                if '## Hashtags' in content['description']:
                    desc_parts = content['description'].split('## Hashtags')
                    content['description'] = desc_parts[0].rstrip() + references_text.rstrip() + '\n\n## Hashtags' + ('## Hashtags'.join(desc_parts[1:]) if len(desc_parts) > 1 else '')
                else:
                    content['description'] = content['description'].rstrip() + references_text.rstrip()
            
            # Validate academic references in description if they exist
            if '## References' in content['description']:
                # Extract references section
                desc_parts = content['description'].split('## References')
                if len(desc_parts) > 1:
                    ref_section = desc_parts[1].split('##')[0]  # Get content until next section
                    validated_refs = validate_academic_references(ref_section)
                    content['description'] = desc_parts[0] + '## References\n' + validated_refs + '\n' + '##'.join(desc_parts[1].split('##')[1:])
            
            # Limit description length and extract iTunes summary
            content['description'] = limit_description_length(content['description'], 4000)
            content['itunes_summary'] = extract_itunes_summary(content['description'])
            
            # Robust validation added here:
            if (not content or 
                not isinstance(content, dict) or
                not all(k in content for k in ['title', 'script', 'description']) or
                not content.get('title') or len(str(content.get('title', '')).strip()) < 5 or
                not content.get('script') or len(str(content.get('script', '')).strip()) < 50 or
                not content.get('description') or len(str(content.get('description', '')).strip()) < 20):
                
                error_detail = f"Invalid content received: {str(content)[:200]}..."
                raise ValueError(f"Content generation returned empty, incomplete, or placeholder data. Details: {error_detail}")
            
            # Validate script length matches duration requirement
            script = content.get('script', '')
            is_valid, error_msg = validate_script_length(script, request.duration)
            if not is_valid:
                word_count = len(script.split())
                structured_logger.error("Script length validation failed",
                                       job_id=job_id,
                                       duration=request.duration,
                                       script_word_count=word_count,
                                       error=error_msg)
                raise ValueError(f"Script does not meet duration requirement. {error_msg}")
            
            structured_logger.info("Content validation passed",
                                  job_id=job_id,
                                  script_word_count=len(script.split()),
                                  duration=request.duration)
            # --- End of Robust Content Validation ---       
            # Determine canonical filename based on topic category, format type, and next available episode number
            canonical_filename = await self.determine_canonical_filename(request.topic, content["title"], request.category, request.format_type)
            
            # Generate multi-voice audio with ElevenLabs and bumpers
            audio_start_time = time.time()
            audio_memory_before = psutil.virtual_memory().percent
            structured_logger.info("Starting multi-voice ElevenLabs audio generation",
                                  job_id=job_id,
                                  memory_before_percent=round(audio_memory_before, 1),
                                  script_length=len(content['script']),
                                  canonical_filename=canonical_filename,
                                  host_voice_id=request.host_voice_id or "XrExE9yKIg1WjnnlVkGX (Matilda - default)",
                                  expert_voice_id=request.expert_voice_id or "pNInz6obpgDQGcFmaJgB (Adam - default)")
            
            audio_url = await self.elevenlabs_voice_service.generate_multi_voice_audio_with_bumpers(
                content["script"], 
                job_id, 
                canonical_filename,
                intro_path="bumpers/copernicus-intro.mp3",
                outro_path="bumpers/copernicus-outro.mp3",
                host_voice_id=request.host_voice_id,
                expert_voice_id=request.expert_voice_id
            )
            
            audio_generation_time = time.time() - audio_start_time
            audio_memory_after = psutil.virtual_memory().percent
            structured_logger.info("Audio generation completed",
                                  job_id=job_id,
                                  generation_time_seconds=round(audio_generation_time, 2),
                                  memory_after_percent=round(audio_memory_after, 1),
                                  memory_delta=round(audio_memory_after - audio_memory_before, 1),
                                  audio_url=audio_url)
            
            # Force garbage collection after audio generation
            gc.collect()
            gc_memory_after = psutil.virtual_memory().percent
            structured_logger.debug("Garbage collection completed",
                                   job_id=job_id,
                                   memory_after_gc_percent=round(gc_memory_after, 1))
            
            # ═════════════════════════════════════════════════════════════════
            # 🎬 PHASE 4: OPTIONAL VIDEO GENERATION (Future Enhancement)
            # ═════════════════════════════════════════════════════════════════
            # VIDEO EXTENSION POINT: Future video generation can be inserted here
            # if request.format_type == "video" or request.include_video:
            #     video_url = await video_service.generate_video_podcast(
            #         audio_url=audio_url,
            #         script=content["script"],
            #         canonical_filename=canonical_filename,
            #         images=...,  # Still images
            #         animations=...,  # Python animations
            #         subtitles=...  # Subtitle tracks
            #     )
            
            # Generate and upload transcript to GCS
            transcript_start_time = time.time()
            transcript_memory_before = psutil.virtual_memory().percent
            structured_logger.info("Generating and uploading transcript",
                                  job_id=job_id,
                                  memory_before_percent=round(transcript_memory_before, 1))
            transcript_url = await self.generate_and_upload_transcript(content["script"], canonical_filename)
            transcript_time = time.time() - transcript_start_time
            structured_logger.info("Transcript completed",
                                  job_id=job_id,
                                  transcript_time_seconds=round(transcript_time, 2),
                                  transcript_url=transcript_url)
            
            # Upload description to GCS
            description_start_time = time.time()
            description_memory_before = psutil.virtual_memory().percent
            structured_logger.info("Uploading episode description to GCS",
                                  job_id=job_id,
                                  memory_before_percent=round(description_memory_before, 1))
            description_url = await self.upload_description_to_gcs(
                content["description"], 
                canonical_filename,
                title=content.get("title", ""),
                topic=request.topic,
                job_id=job_id
            )
            description_time = time.time() - description_start_time
            structured_logger.info("Description completed",
                                  job_id=job_id,
                                  description_time_seconds=round(description_time, 2),
                                  description_url=description_url)
            
            # Generate and upload thumbnail
            thumbnail_start_time = time.time()
            thumbnail_memory_before = psutil.virtual_memory().percent
            structured_logger.info("Generating AI thumbnail",
                                  job_id=job_id,
                                  memory_before_percent=round(thumbnail_memory_before, 1))
            
            async with with_step("thumbnail_generation", job_id):
                thumbnail_url = await self.generate_and_upload_thumbnail(
                    content["title"], 
                    request.topic, 
                    canonical_filename
                )
            
            thumbnail_time = time.time() - thumbnail_start_time
            structured_logger.info("Thumbnail completed",
                                  job_id=job_id,
                                  thumbnail_time_seconds=round(thumbnail_time, 2),
                                  thumbnail_url=thumbnail_url)
            
            # Generate episode images (1-2 still images for display during audio playback)
            episode_images = []
            try:
                images_start_time = time.time()
                structured_logger.info("Generating episode images",
                                     job_id=job_id,
                                     memory_before_percent=round(psutil.virtual_memory().percent, 1))
                
                episode_images = await self.generate_episode_images(
                    content["title"],
                    request.topic,
                    canonical_filename,
                    description=content.get("description", ""),
                    num_images=2  # Generate 2 images by default
                )
                
                images_time = time.time() - images_start_time
                structured_logger.info("Episode images completed",
                                     job_id=job_id,
                                     images_time_seconds=round(images_time, 2),
                                     images_generated=len(episode_images))
            except Exception as e:
                structured_logger.warning("Failed to generate episode images, continuing without them",
                                       job_id=job_id,
                                       error=str(e))
                episode_images = []
            
            # Extract keywords from content for search/discovery
            keywords_indexed = []
            if 'keywords' in content:
                keywords_indexed = content['keywords']
            elif 'description' in content:
                # Extract from hashtags in description
                hashtags = re.findall(r'#(\w+)', content['description'])
                keywords_indexed = hashtags[:10]  # Limit to 10
            
            # Prepare metadata_extended with source papers
            metadata_extended = {
                'source_papers': [],
                'references_extracted': [],
                'keywords_indexed': keywords_indexed,
                'glmp_visualizations': [],
                'quality_scores': {
                    'content_accuracy': 0.0,
                    'audio_quality': 0.0,
                    'user_rating': 0.0,
                    'reference_quality': 0.0
                }
            }
            
            # Add paper DOI/URL if provided
            if request.paper_doi:
                metadata_extended['source_papers'].append(request.paper_doi)
            elif request.source_links:
                metadata_extended['source_papers'].extend(request.source_links[:5])  # Limit to 5
            
            # Prepare engagement metrics
            engagement_metrics = {
                'play_count': 0,
                'completion_rate': 0.0,
                'user_ratings': [],
                'shares': 0,
                'feedback_comments': []
            }
            
            # Complete job with enhanced metadata
            generated_timestamp = datetime.utcnow().isoformat()
            job_ref.update({
                'status': 'completed',
                'updated_at': datetime.utcnow().isoformat(),
                'result': {
                    'title': content.get('title') or request.topic or 'Untitled Podcast',
                    'script': content.get('script', ''),
                    'description': content.get('description', ''),
                    'audio_url': audio_url,
                    'thumbnail_url': thumbnail_url,
                    'episode_images': episode_images,  # Array of 1-2 image URLs
                    'transcript_url': transcript_url,
                    'description_url': description_url,
                    'duration': request.duration,
                    'topic': request.topic,
                    'expertise_level': request.expertise_level,
                    'format_type': request.format_type,
                    'has_research_paper': bool(request.paper_content),
                    'paper_title': request.paper_title,
                    'tts_provider': 'elevenlabs_multi_voice',
                    'content_provider': 'gemini_research_enhanced',
                    'canonical_filename': canonical_filename,
                    'generated_at': generated_timestamp,
                    'itunes_summary': content.get('itunes_summary'),
                },
                'metadata_extended': metadata_extended,
                'engagement_metrics': engagement_metrics
            })
            
            # NOTE: Option A Architecture - episodes as single source of truth for RSS
            # AUTO-PROMOTE by default (YouTube-style): All podcasts are automatically promoted to episodes
            # This gives users immediate publication ability without waiting for admin approval.
            # Admin can still unpromote/remove if needed (moderation after the fact).
            # - podcast_jobs: Complete generation history (all podcasts ever created)
            # - episodes: Public catalog (auto-promoted, can be unpromoted if needed)
            try:
                episode_service.upsert_episode_document(
                    job_id,
                    subscriber_id,
                    request_snapshot,
                    {
                        **content,
                        "audio_url": audio_url,
                        "thumbnail_url": thumbnail_url,
                        "episode_images": episode_images,  # Array of 1-2 image URLs
                        "transcript_url": transcript_url,
                        "description_url": description_url,
                        "duration": request.duration,
                        "canonical_filename": canonical_filename,
                        "generated_at": generated_timestamp,
                    },
                    metadata_extended,
                    engagement_metrics,
                    submitted_to_rss=False,  # Not in RSS by default - user can add to RSS themselves
                )
                
                # Mark as promoted in podcast_jobs
                db.collection('podcast_jobs').document(job_id).update({
                    'promoted_to_episodes': True,
                    'promoted_at': generated_timestamp,
                    'auto_promoted': True
                })
                
                structured_logger.info("Podcast auto-promoted to episodes collection",
                                      job_id=job_id,
                                      message="ready for RSS")
            except Exception as catalog_error:
                structured_logger.warning("Failed to auto-promote episode",
                                         job_id=job_id,
                                         error=str(catalog_error))
                # Continue anyway - podcast is still in podcast_jobs
            
            # Send email notification
            email_start_time = time.time()
            email_memory_before = psutil.virtual_memory().percent
            structured_logger.info("Sending completion email notification",
                                  job_id=job_id,
                                  recipient_email=subscriber_email,
                                  memory_before_percent=round(email_memory_before, 1))
            
            await self.email_service.send_podcast_completion_email(
                recipient_email=subscriber_email,
                job_id=job_id,
                podcast_title=content.get('title', 'Untitled Podcast'),
                topic=request.topic,
                audio_url=audio_url,
                duration=request.duration,
                canonical_filename=canonical_filename
            )
            
            email_time = time.time() - email_start_time
            structured_logger.info("Email notification sent",
                                  job_id=job_id,
                                  email_time_seconds=round(email_time, 2))
            
            # Final pipeline summary
            total_time = time.time() - start_time
            final_memory = psutil.virtual_memory().percent
            structured_logger.info("Pipeline completed successfully",
                                  job_id=job_id,
                                  total_time_seconds=round(total_time, 2),
                                  initial_memory_percent=round(initial_memory, 1),
                                  final_memory_percent=round(final_memory, 1),
                                  memory_delta=round(final_memory - initial_memory, 1),
                                  audio_url=audio_url,
                                  transcript_url=transcript_url,
                                  description_url=description_url,
                                  thumbnail_url=thumbnail_url)
            
        except Exception as e:
            job_ref.update({
                'status': 'failed',
                'error': str(e),
                'updated_at': datetime.utcnow().isoformat()
            })
            structured_logger.error("Podcast generation failed",
                                   job_id=job_id,
                                   error=str(e),
                                   error_type=type(e).__name__,
                                   topic=request.topic if request else None)
            
            # Send failure email notification
            try:
                await self.email_service.send_podcast_failure_email(
                    recipient_email=ERROR_NOTIFICATION_EMAIL,
                    job_id=job_id,
                    topic=request.topic if request else "Unknown",
                    error_message=str(e)
                )
            except Exception as email_error:
                structured_logger.error("Failed to send failure email notification",
                                       job_id=job_id,
                                       email_error=str(email_error))


# Create singleton instance
# Note: vertex_ai_model will be injected when the service is used
podcast_generation_service = PodcastGenerationService()

