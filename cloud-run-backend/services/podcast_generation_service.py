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
from typing import Optional, Dict, Any
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
from utils.script_validation import validate_script_length

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
- ALL speakers must be FICTIONAL with first names ONLY (e.g., "Matilda", "Adam", "Bill")
- NO titles (Dr., Professor, PhD), NO surnames, NO real person identification
- When introducing speakers, use only first names (e.g., "Let's bring in Adam, our expert...")
- NEVER use "Dr." or any academic titles in the script

**ROLE CONSISTENCY REQUIREMENTS:**
- **HOST**: Guides the conversation, asks introductory questions, provides context
- **EXPERT**: Provides detailed technical explanations, research insights, and expert analysis
- **QUESTIONER**: Asks clarifying questions, expresses curiosity, seeks deeper understanding
- **NEVER mix roles**: Expert explains, Questioner asks, Host guides
- **Maintain character consistency** throughout the entire dialogue

**Script Format Requirements:**
- Create natural dialogue without speaker labels in the final script
- Write as continuous narrative with clear speaker transitions
- Use phrases like "Sarah explains" or "Marcus adds" instead of "EXPERT:" labels
- Make the conversation flow naturally without technical markers
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
    "script": "Multi-voice podcast script with HOST:, EXPERT:, QUESTIONER: markers and natural dialogue",
    "description": "Comprehensive episode description following established format"
}}

**CRITICAL: Generate a comprehensive description using this EXACT format:**

## Episode Overview
[2-3 engaging paragraphs introducing the research paper and its significance]

## Key Concepts Explored
- [Key Finding 1]: [Explanation with implications]
- [Key Finding 2]: [Explanation with applications]
- [Paradigm Shift]: [How this changes the field]
- [Future Direction]: [What this enables next]

## Research Insights
[Paragraph about the paper's methodology, breakthrough findings, and contribution to the field]

## Practical Applications
[Paragraph about real-world applications and technological implementations of this research]

## Future Directions
[Paragraph about future research directions enabled by this work and long-term implications]

## References
- {citation}
- [Additional relevant citations in DOI format]

## Episode Details
- **Duration**: {request.duration}
- **Expertise Level**: {request.expertise_level}
- **Paper**: {paper.title}
- **Authors**: {', '.join(paper.authors)}

---

#CopernicusAI #SciencePodcast #ResearchPaper #AcademicDiscussion #ResearchInsights

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
- ALL speakers must be FICTIONAL with first names ONLY (e.g., "Matilda", "Adam", "Bill")
- NO titles (Dr., Professor, PhD), NO surnames, NO real person identification
- When introducing speakers, use only first names (e.g., "Let's bring in Adam, our expert...")
- NEVER use "Dr." or any academic titles in the script

**Script Format Requirements:**
- Use "HOST:", "EXPERT:", and "QUESTIONER:" to mark each speaker clearly
- Write natural dialogue that flows between speakers
- Include proper academic citations with DOIs where relevant
- Focus on paradigm-shifting implications and research insights
- Duration: {request.duration}
- Expertise Level: {request.expertise_level}

Return JSON with:
{{
    "title": "Engaging podcast title highlighting paradigm shift",
    "script": "Multi-voice podcast script with HOST:, EXPERT:, QUESTIONER: markers and natural dialogue",
    "description": "Comprehensive episode description following established format"
}}

**CRITICAL: Generate a comprehensive description using this EXACT format:**

## Episode Overview
[2-3 engaging paragraphs introducing the research paper and its significance]

## Key Concepts Explored
- [Key Finding 1]: [Explanation with implications]
- [Key Finding 2]: [Explanation with applications]
- [Paradigm Shift]: [How this changes the field]
- [Future Direction]: [What this enables next]

## Research Insights
[Paragraph about the paper's methodology, breakthrough findings, and contribution to the field]

## Practical Applications
[Paragraph about real-world applications and technological implementations of this research]

## Future Directions
[Paragraph about future research directions enabled by this work and long-term implications]

## References
- {citation}
- [Additional relevant citations in DOI format]

## Episode Details
- **Duration**: {request.duration}
- **Expertise Level**: {request.expertise_level}
- **Paper**: {paper.title}
- **Authors**: {', '.join(paper.authors)}

---

#CopernicusAI #SciencePodcast #ResearchPaper #AcademicDiscussion #ResearchInsights

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
        
        prompt = f"""{character_prompt}

Create a compelling {request.duration} research podcast script about "{request.topic}" for {request.expertise_level} audience.

**Focus Areas:** {', '.join(request.focus_areas) if request.focus_areas else 'recent breakthroughs, methodology, implications'}

**CRITICAL SHOW REQUIREMENTS:**
- The show name is ALWAYS "Copernicus AI: Frontiers of Science" - never use any other title
- HOST must introduce the show as "Welcome to Copernicus AI: Frontiers of Science"
- All speakers use FIRST NAMES ONLY (e.g., Matilda, Adam, Bill) - NO surnames, titles, or honorifics
- Speakers are clearly fictional characters, not real people

**Multi-Voice Script Requirements:**
Create a natural dialogue between HOST, EXPERT, and QUESTIONER that follows this structure:
{chr(10).join([f"- {step}" for step in character.structure])}

**Content Length Requirements:**
- Target duration: {request.duration} (approximately 1500-2000 words for 10 minutes)
- Each speaker should have 8-12 substantial dialogue segments
- Include detailed technical explanations and comprehensive coverage
- Ensure the script is long enough to fill the full {request.duration}

**CRITICAL FORMAT REQUIREMENTS - THIS IS MANDATORY:**
- **MUST** use speaker labels at the beginning of each line: "HOST:", "EXPERT:", "QUESTIONER:"
- **DO NOT** write in narrative format - write as a conversation between speakers
- **NEVER** start with "Welcome to Copernicus AI" without a speaker label
- **NEVER** use phrases like "Matilda explains" or "Adam adds" - use speaker labels instead
- **EXAMPLE FORMAT:**
  HOST: Welcome to Copernicus AI: Frontiers of Science. Today we're discussing {request.topic}.
  EXPERT: Thank you for having me. This is a fascinating area of research.
  QUESTIONER: Can you explain what makes this topic so significant?
  HOST: That's a great question. Let's dive into the details.

**MANDATORY:** Every line of dialogue must start with a speaker label. Do not write any narrative text without speaker labels. The script must be a pure dialogue format with HOST:, EXPERT:, QUESTIONER: labels.

**Format Guidelines:**
- Use "HOST:", "EXPERT:", and "QUESTIONER:" to mark each speaker clearly
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
    "script": "Multi-voice podcast script with HOST:, EXPERT:, QUESTIONER: markers and natural dialogue",
    "description": "Comprehensive episode description following established format"
}}

**CRITICAL: Generate a separate comprehensive description using this EXACT format:**

After generating the main content, create a detailed description following this structure:

## Episode Overview
[2-3 engaging paragraphs introducing the topic and its significance in the field]

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
    "script": "Multi-voice podcast script with HOST:, EXPERT:, QUESTIONER: markers and natural dialogue",
    "description": "Comprehensive episode description following established format"
}}

**CRITICAL: Generate a comprehensive description using this EXACT format:**

## Episode Overview
[2-3 engaging paragraphs introducing the topic and its significance in the field]

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
        google_key: str
    ) -> dict:
        """
        Generate 2-speaker podcast content from research context
        Uses the research integrator to create Copernicus-spirit content
        """
        structured_logger.info("Generating 2-speaker content from research sources",
                              research_sources_count=len(research_context.research_sources),
                              topic=request.topic)
        
        research_integrator = PodcastResearchIntegrator(google_key)
        
        prompt = research_integrator.build_2_speaker_research_prompt(
            research_context=research_context,
            duration=request.duration,
            format_type=request.format_type,
            additional_instructions=request.additional_instructions or "",
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
                            max_output_tokens=8192,
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
                                        max_output_tokens=8192,
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
                                max_output_tokens=8192,
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
        
        # CRITICAL: If description is missing, create fallback
        if not content.get('description'):
            structured_logger.warning("LLM did not generate description field, creating fallback",
                                     topic=request.topic)
            
            fallback_desc = f"""## Episode Overview

This episode explores {research_context.topic}, examining recent breakthroughs and their implications.

## Key Concepts Explored

- Recent research developments in {research_context.topic}
- Paradigm shifts and revolutionary findings
- Practical applications and future directions

## Research Insights

{research_context.key_findings[0] if research_context.key_findings else 'Cutting-edge research findings from leading scientists.'}

## References

"""
            for i, source in enumerate(research_context.research_sources[:5], 1):
                authors = ', '.join(source.authors[:2]) + (' et al.' if len(source.authors) > 2 else '')
                fallback_desc += f"- {authors}. {source.title}. {source.source}. "
                if source.doi:
                    fallback_desc += f"DOI: {source.doi}"
                elif source.url:
                    fallback_desc += f"Available: {source.url}"
                fallback_desc += "\n"
            
            content['description'] = fallback_desc
            structured_logger.info("Created fallback description",
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
    async def upload_description_to_gcs(self, description: str, canonical_filename: str) -> str:
        """Upload episode description to GCS descriptions folder with hashtags"""
        try:
            from google.cloud import storage
            from content_fixes import generate_relevant_hashtags, validate_academic_references
            
            # Initialize GCS client
            storage_client = storage.Client()
            bucket = storage_client.bucket("regal-scholar-453620-r7-podcast-storage")
            
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
                # Extract topic from description for better hashtag generation
                topic_match = re.search(r'^#\s*(.+)', description, re.MULTILINE)
                topic_for_hashtags = topic_match.group(1) if topic_match else ""
                
                # Generate context-aware hashtags based on description content
                hashtags = generate_relevant_hashtags(topic_for_hashtags, category, "", description)
                
                # Add hashtags section
                enhanced_description = f"{description}\n\n## Hashtags\n{hashtags}"
            
            # Ensure total description doesn't exceed 4000 characters (podcast description limit)
            MAX_DESCRIPTION_LENGTH = 4000
            if len(enhanced_description) > MAX_DESCRIPTION_LENGTH:
                structured_logger.debug("Description too long, trimming",
                                       original_length=len(enhanced_description),
                                       max_length=MAX_DESCRIPTION_LENGTH,
                                       canonical_filename=canonical_filename)
                
                # Try to preserve references by trimming the middle content first
                sections = enhanced_description.split('\n\n')
                references_sections = [s for s in sections if 'References' in s or s.strip().startswith('- ') or 'DOI:' in s or 'http' in s]
                other_sections = [s for s in sections if s not in references_sections]
                hashtag_sections = [s for s in sections if s.strip().startswith('#')]
                
                # Reserve space for references and hashtags
                references_text = '\n\n'.join(references_sections)
                hashtags_text = '\n\n'.join(hashtag_sections)
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
                enhanced_description = '\n\n'.join(trimmed_other + references_sections + hashtag_sections)
            
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
        """Generate AI thumbnail using DALL-E 3 with 1792x1792 dimensions for podcast platforms"""
        try:
            import requests
            from google.cloud import storage
            import io
            
            # Initialize GCS client
            storage_client = storage.Client()
            bucket = storage_client.bucket(self.bucket_name)
            
            # Get OpenAI API key from Secret Manager for DALL-E
            openai_api_key = await self.get_openai_api_key_from_secret_manager()
            if not openai_api_key:
                structured_logger.warning("No OpenAI API key available for DALL-E thumbnail generation, using fallback",
                                         canonical_filename=canonical_filename)
                return await self.generate_fallback_thumbnail(canonical_filename, topic)
            
            # Create sophisticated DALL-E prompt based on episode content
            dalle_prompt = f"""A stunning scientific visualization representing {topic} research. 
            Style: Modern digital art, professional scientific illustration, high-tech aesthetic.
            Visual elements: Abstract molecular structures, flowing data streams, particle physics effects, neural networks, or quantum field representations related to {topic}.
            Color palette: Deep space blues and purples with bright cyan, electric blue, and white accents. Gradient backgrounds.
            Composition: Centered, balanced, visually striking for podcast thumbnail.
            Quality: Ultra-high resolution, clean, sophisticated, suitable for Spotify/iTunes/YouTube.
            NO TEXT, NO WORDS, NO TITLES - pure visual scientific concept art.
            Mood: Cutting-edge research, discovery, innovation, future technology."""
            
            # Generate image with DALL-E 3
            structured_logger.info("Generating DALL-E 3 thumbnail",
                                  canonical_filename=canonical_filename,
                                  topic=topic)
            
            headers = {
                "Authorization": f"Bearer {openai_api_key}",
                "Content-Type": "application/json"
            }
            
            payload = {
                "model": "dall-e-3",
                "prompt": dalle_prompt,
                "n": 1,
                "size": "1024x1024",  # Standard square format for podcast platforms
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
                
                # Store research metadata in job
                job_ref.update({
                    'research_sources_count': len(research_context.research_sources),
                    'research_quality_score': research_context.research_quality_score,
                    'paradigm_shifts_count': len(research_context.paradigm_shifts),
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
                
                try:
                    # Generate 2-speaker podcast from research
                    content = await asyncio.wait_for(
                        self.generate_content_from_research_context(request, research_context, google_key),
                        timeout=600  # 10 minute timeout for content generation
                    )
                    
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
                                          title=content.get('title', 'N/A')[:60] if isinstance(content, dict) else 'N/A')
                    
                except asyncio.TimeoutError:
                    structured_logger.error("Content generation timed out", 
                                           job_id=job_id,
                                           timeout_seconds=600)
                    raise Exception("Content generation timed out after 10 minutes")
                except Exception as e:
                    structured_logger.error("Content generation failed", 
                                           job_id=job_id,
                                           error=str(e),
                                           error_type=type(e).__name__)
                    raise
            
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
            description_url = await self.upload_description_to_gcs(content["description"], canonical_filename)
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

