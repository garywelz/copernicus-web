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
import media_store
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
from tts_usage import TtsUsage
import curated_checks as _cc
import curated_mode as _curated
from email_service import EmailService
from content_fixes import (
    apply_content_fixes,
    fix_script_format_for_multi_voice,
    limit_description_length,
    extract_itunes_summary,
    generate_relevant_hashtags,
    validate_academic_references,
    clean_placeholder_text_from_description,
    sanitize_reference_placeholders,
    join_description_sections,
    rewrite_index_venues,
    ensure_source_paper_reference,
    format_research_source_line,
    dalle_thumbnail_attempts,
    validate_description_before_publish,
    DescriptionValidationError,
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


_CITATION_GROUNDING = """
**Citation and venue rules (do not violate):**
- Use the provided source-paper citation as given. Never write DOI: 10.xxxx/xxxx, (Recent), or (Year).
- If the year is unknown, omit it. Do not invent "Recent".
- PubMed and arXiv are indexes, not journals. If a journal name is in the citation, say that journal. Never say "published in PubMed" or "published in arXiv".
- Additional references must include a real DOI (starting with 10.) or a real URL. If you do not have one, omit the DOI field entirely.
- Do not mention CRISPR, cancer therapy, gene editing, or drug design unless those subjects appear in the source paper itself.
"""


# Gap 3 fix 1: research-phase failures get their own job error_type (keyed by exception class name) so an unreachable
# registry, an unconfirmable requested paper and a thin topic can be told apart in the job record and the failure email.
RESEARCH_FAILURE_TYPES = {
    'InsufficientConfirmedPapers': 'insufficient_confirmed_papers',
    'RegistryUnavailable': 'registry_unavailable',
    'PaperNotConfirmed': 'requested_paper_not_confirmed',
}


def _research_paper_from_request(request: PodcastRequest) -> ResearchPaper:
    authors = request.paper_authors or ["Unknown Author"]
    if isinstance(authors, str):
        authors = [authors]
    return ResearchPaper(
        title=request.paper_title,
        authors=authors,
        content=request.paper_content,
        abstract=request.paper_abstract,
        doi=request.paper_doi,
        journal=request.paper_journal,
        publication_date=request.paper_year,
    )
from utils.api_keys import get_google_api_key
from config.constants import (
    GCP_PROJECT_ID,
    DEFAULT_SUBSCRIBER_EMAIL,
    ERROR_NOTIFICATION_EMAIL,
)
from config.database import db
from services.episode_service import episode_service
from services.canonical_service import canonical_service
from utils.script_validation import (validate_script_length, calculate_minimum_words_for_duration, calculate_maximum_words_for_duration,
                                     length_feedback, short_feedback, ScriptTooLongError, ScriptTooShortError, check_model_reply)
from named_work_check import check_naming, feedback_text, make_gemini_llm_call, NamingViolationError
from failure_notice import describe_failure
from reference_sections import apply_reference_sections, BUILT_BY as REFERENCES_BUILT_BY
from speech_text import strip_pn_markers_counted, speak_text, notation_problems, notation_feedback, UnspeakableNotationError
from script_style import banned_phrase_hits, banned_feedback, BannedPhraseError, FinalTextCheckError
from topic_checks import (uncovered_named_things, missing_coverage_statements, coverage_feedback, read_aloud_sentences, read_aloud_feedback,
                          CoverageStatementError, TopicReadAloudError)
from attribution_check import check_attributions, attribution_feedback, AttributionError
import rejection_log

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
            paper = _research_paper_from_request(request)
            
            # Create analysis options
            options = AnalyzeOptions(
                focus_areas=request.focus_areas or ["methodology", "implications", "future_research"],
                include_citations=request.include_citations,
                significance_analysis=request.paradigm_shift_analysis
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
            paper = _research_paper_from_request(request)
            
            # Create analysis options
            options = AnalyzeOptions(
                focus_areas=request.focus_areas or ["methodology", "implications", "future_research"],
                analysis_depth="comprehensive",
                include_citations=request.include_citations,
                significance_analysis=request.paradigm_shift_analysis,
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
        # Use google.generativeai directly for Google AI API (not the unified client)
        import google.generativeai as genai
        genai.configure(api_key=api_key)
        
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
{_CITATION_GROUNDING}

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
- **When naming THIS paper's venue, use the journal in the citation — never "published in PubMed" or "published in arXiv"**
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
- Additional citations only when you have a real DOI (10....) or URL. Never write 10.xxxx/xxxx. Never use (Recent) or (Year).

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
            # Use Google AI API format (without models/ prefix) with fallback chain
            # Only use stable 2.5 models - gemini-1.5-flash may not be available
            fallback_models = ['gemini-2.5-flash', 'gemini-2.5-pro']
            response_obj = None
            model_name = None
            last_error = None
            
            for model in fallback_models:
                try:
                    structured_logger.info("Trying Google AI API model", model=model, paper_title=paper.title[:50] if paper and paper.title else None)
                    model_name = model
                    # Use google.generativeai.GenerativeModel (not client.models.generate_content)
                    generative_model = genai.GenerativeModel(model)
                    response_obj = generative_model.generate_content(prompt)
                    structured_logger.info("Google AI API successful", model=model, paper_title=paper.title[:50] if paper and paper.title else None)
                    break
                except Exception as e:
                    last_error = e
                    error_msg = str(e).lower()
                    structured_logger.warning("Google AI API model failed, trying next",
                                            model=model,
                                            error=str(e),
                                            paper_title=paper.title[:50] if paper and paper.title else None)
                    if "not found" in error_msg or "does not exist" in error_msg or "404" in error_msg:
                        continue  # Try next model
                    else:
                        raise  # Re-raise if it's not a "model not found" error
            
            if not response_obj:
                raise last_error or Exception("All Google AI API models failed")
            
            # Extract text from response (google.generativeai returns response with .text attribute)
            response_text = response_obj.text if hasattr(response_obj, 'text') else str(response_obj)
            if response_text:
                content = _extract_json_from_response(response_text)
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
Citation: {citation}
{_CITATION_GROUNDING}

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
- Cite the source paper by journal name from the citation, never as "published in PubMed"
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
- Additional citations only when you have a real DOI (10....) or URL. Never write 10.xxxx/xxxx. Never use (Recent) or (Year).

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
        # Use google.generativeai directly for Google AI API (not the unified client)
        import google.generativeai as genai
        genai.configure(api_key=api_key)
        
        # Get Copernicus character configuration
        character = get_copernicus_character()
        character_prompt = get_character_prompt(character)
        
        # Calculate minimum word count for explicit requirement
        min_words = calculate_minimum_words_for_duration(request.duration)
        target_words = int(min_words / 0.8)  # Target for full duration (minimum is 80% of target)
        
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

**CRITICAL**: Each key concept MUST be unique and specific to {request.topic}. DO NOT use placeholder text like "Research findings require further analysis" or generic statements. Each concept should have a distinct title and detailed explanation based on actual research in this field. Generate 4-5 different, specific concepts with unique explanations.

## Research Insights
[2-3 paragraphs about current research developments, recent breakthroughs, methodological advances, experimental techniques, and what makes this area of research exciting. Discuss cutting-edge findings and their significance.]

## Practical Applications
[2-3 paragraphs about real-world applications, industry impact, technological implementations, and potential uses. Be specific about how this research could be applied in practice, including examples from different sectors.]

## Future Directions
[2-3 paragraphs about emerging research directions, potential breakthroughs on the horizon, long-term implications, unanswered questions, and where this field is heading. Discuss both near-term and long-term possibilities.]

## References
- [Author et al. (Year). Title. Journal. DOI: 10.1234/real-doi-only-if-known]
- Omit the DOI field if you do not have a real DOI. Never write 10.xxxx/xxxx or (Recent).

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
            # Use Google AI API format (without models/ prefix) with fallback chain
            # Only use stable 2.5 models - gemini-1.5-flash may not be available
            fallback_models = ['gemini-2.5-flash', 'gemini-2.5-pro']
            response_obj = None
            model_name = None
            last_error = None
            
            for model in fallback_models:
                try:
                    structured_logger.info("Trying Google AI API model", model=model, topic=request.topic)
                    model_name = model
                    # Use google.generativeai.GenerativeModel (not client.models.generate_content)
                    generative_model = genai.GenerativeModel(model)
                    response_obj = generative_model.generate_content(prompt)
                    structured_logger.info("Google AI API successful", model=model, topic=request.topic)
                    break
                except Exception as e:
                    last_error = e
                    error_msg = str(e).lower()
                    structured_logger.warning("Google AI API model failed, trying next",
                                            model=model,
                                            error=str(e),
                                            topic=request.topic)
                    if "not found" in error_msg or "does not exist" in error_msg or "404" in error_msg:
                        continue  # Try next model
                    else:
                        raise  # Re-raise if it's not a "model not found" error
            
            if not response_obj:
                raise last_error or Exception("All Google AI API models failed")
            
            # Extract text from response (google.generativeai returns response with .text attribute)
            response_text = response_obj.text if hasattr(response_obj, 'text') else str(response_obj)
            if response_text:
                content = _extract_json_from_response(response_text)
                
                # Apply content fixes
                if 'script' in content:
                    content['script'] = apply_content_fixes(content['script'], request.topic)
                    # Fix script format for multi-voice if needed
                    content['script'] = fix_script_format_for_multi_voice(content['script'])
                
                # Limit description length and extract iTunes summary
                if 'description' in content:
                    # Clean placeholder text before processing
                    content['description'] = clean_placeholder_text_from_description(content['description'])
                    content['description'] = limit_description_length(content['description'], 4000)
                    content['itunes_summary'] = extract_itunes_summary(content['description'])
                    
                    # Generate relevant hashtags
                    content['hashtags'] = generate_relevant_hashtags(
                        request.topic, 
                        request.category, 
                        content.get('title', ''), 
                        ""
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
- [Author et al. (Year). Title. Journal. DOI: 10.1234/real-doi-only-if-known]
- Omit the DOI field if you do not have a real DOI. Never write 10.xxxx/xxxx or (Recent).

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
        retry_attempt: int = 0,
        naming_feedback: str = ""
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
        source_citation = ""
        if request.paper_title:
            # (venue line is added below from the confirmed registry record)
            # Gap 3 fix 1 (C3/C4): the requested paper was confirmed in the research phase and is P1 in the confirmed list,
            # so there is nothing to inject here; its venue line comes from the registry record, not from the request.
            requested = next((c for c in research_context.confirmed_papers if c.pid == research_context.requested_pid), None)
            if requested is not None:
                source_citation = format_citation(ResearchPaper(
                    title=requested.title, authors=list(requested.authors), content="", abstract=requested.abstract,
                    doi=requested.ids.get("doi"), publication_date=str(requested.year or ""), journal=requested.venue))
                additional_instructions = additional_instructions.split("**SOURCE PAPER VENUE:**")[0] + f"""

**SOURCE PAPER VENUE:** This episode is about [P1]:
{source_citation}
Say that journal name in dialogue. Never say "published in PubMed" or "published in arXiv".
"""

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
        
        if naming_feedback:
            # Gap 3 fix 1 (C5): the previous attempt named works that are not on the confirmed list.
            additional_instructions += naming_feedback

        curated = getattr(research_context, "curated", None)
        if curated is not None:
            additional_instructions += curated.prompt_block()
        prompt = research_integrator.build_2_speaker_research_prompt(
            research_context=research_context,
            duration=request.duration,
            format_type=request.format_type,
            additional_instructions=additional_instructions,
            host_voice_id=request.host_voice_id,
            expert_voice_id=request.expert_voice_id,
            source_paper_citation=source_citation,
            neutral_labels=curated is not None,
        )
        
        structured_logger.debug("Sending prompt to LLM",
                               prompt_length=len(prompt),
                               topic=request.topic)
        
        # Call Vertex AI or Google AI API
        # Skip Vertex AI if disabled via environment variable
        vertex_ai_disabled = (os.getenv("DISABLE_VERTEX_AI", "0") or "").strip().lower() in {"1", "true", "yes", "y", "on"} or (
            (os.getenv("COPERNICUS_DISABLE_VERTEX_AI", "0") or "").strip().lower() in {"1", "true", "yes", "y", "on"}
        )
        if not vertex_ai_disabled and VERTEX_AI_AVAILABLE and google_genai_client and self.vertex_ai_model:
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
                        # Updated: Removed gemini-2.0 models (deprecated June 1, 2026)
                        fallback_models = ['models/gemini-3.0-pro', 'models/gemini-2.5-flash', 'models/gemini-2.5-pro']
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
                    # Use current Google AI API models (without models/ prefix)
                    # Only use stable 2.5 models - gemini-1.5-flash may not be available
                    fallback_models = ['gemini-2.5-flash', 'gemini-2.5-pro']
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
            # Fix 6: an explicit call (gemini_generate): temperature 0.8, JSON mode with a schema that requires every field, an output limit
            # and a thinking budget. Before, this branch passed no generation config at all.
            from gemini_generate import (generate_json_reply, GENERATOR_MODEL, FALLBACK_MODEL, TEMPERATURE, MAX_OUTPUT_TOKENS, THINKING_BUDGET)
            content = None
            last_error = None
            for model_name in (GENERATOR_MODEL, FALLBACK_MODEL):
                try:
                    structured_logger.info("Trying Google AI API model", model=model_name, temperature=TEMPERATURE,
                                          max_output_tokens=MAX_OUTPUT_TOKENS, thinking_budget=THINKING_BUDGET)
                    reply = await asyncio.to_thread(generate_json_reply, prompt, google_key, model_name)
                    content = json.loads(reply)
                    structured_logger.info("Google AI API successful", model=model_name, reply_chars=len(reply))
                    break
                except Exception as model_error:
                    last_error = model_error
                    structured_logger.warning("Google AI API model failed, trying next", model=model_name, error=str(model_error))
                    continue
            if content is None:
                raise last_error or Exception("All Google AI API models failed")

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
            
            fallback_desc = self._build_fallback_description(research_context)
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
        content['significance'] = research_context.significance
        
        return content
    
    @staticmethod
    def _build_fallback_description(research_context) -> str:
        """Description used when the model returned none. Built only from what the research phase found, with no template prose
        (an older version was a page of promotional filler); it must pass validate_description_before_publish (tested)."""
        topic = research_context.topic
        n = len(research_context.research_sources)
        opening = (f"This episode looks at {topic}, drawing on {n} research paper{'s' if n != 1 else ''} reviewed for it. "
                   "The papers are listed under References.")

        placeholder_texts = [
            "research findings require further analysis",
            "methodology analysis pending",
            "implications to be determined",
            "analysis pending",
            "further analysis required"
        ]
        meaningful_findings = [
            f for f in research_context.key_findings
            if f and not any(placeholder.lower() in f.lower() for placeholder in placeholder_texts)
        ]
        key_concepts = "## Key Concepts Explored\n\n"
        if meaningful_findings:
            for finding in meaningful_findings[:5]:
                key_concepts += f"- {finding}\n"
        else:
            key_concepts += "- The papers reviewed for this episode, listed under References.\n"

        sections = []
        # What the analyses say the papers change in how we see the question (a note that still looks like a placeholder is skipped)
        notes = [x for x in (getattr(research_context, "significance", None) or []) if not re.search(r':\s*unknown\b', x, re.IGNORECASE)]
        if notes:
            sections.append("## Research Insights\n\n" + "\n".join(f"- {x}" for x in notes[:3]))

        future_directions = []
        for analysis in research_context.paper_analyses:
            if hasattr(analysis, 'future_research_directions') and analysis.future_research_directions:
                future_directions.extend(analysis.future_research_directions)
        if future_directions:
            sections.append("## Future Directions\n\n" + "\n".join(f"- {x}" for x in future_directions[:3]))

        references = "## References\n\n"
        for source in research_context.research_sources[:5]:
            references += format_research_source_line(source) + "\n"

        return "\n\n".join([opening, key_concepts.rstrip("\n")] + sections + [references.rstrip("\n")])

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
    async def generate_and_upload_transcript(self, script: str, canonical_filename: str) -> str:
        """Generate and upload transcript to GCS transcripts folder"""
        try:
            from google.cloud import storage
            
            # Initialize GCS client
            storage_client = storage.Client()
            bucket = storage_client.bucket(media_store.PRIVATE_BUCKET)
            
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
            blob.upload_from_string(transcript_content, content_type="text/markdown; charset=utf-8")
            
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
            bucket = storage_client.bucket(media_store.PRIVATE_BUCKET)
            
            # Save image to bytes
            img_bytes = io.BytesIO()
            img.save(img_bytes, format='JPEG', quality=95)
            img_bytes.seek(0)
            
            # Upload to GCS
            thumbnail_filename = f"{canonical_filename}-fallback-thumb.jpg"
            blob = bucket.blob(f"thumbnails/{thumbnail_filename}")
            blob.upload_from_file(img_bytes, content_type="image/jpeg")
            
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
            bucket = storage_client.bucket(media_store.PRIVATE_BUCKET)
            
            # Get OpenAI API key from Secret Manager for DALL-E
            openai_api_key = await self.get_openai_api_key_from_secret_manager()
            if not openai_api_key:
                structured_logger.warning("No OpenAI API key available for DALL-E thumbnail generation, using fallback",
                                         canonical_filename=canonical_filename)
                return await self.generate_fallback_thumbnail(canonical_filename, topic)
            
            headers = {
                "Authorization": f"Bearer {openai_api_key}",
                "Content-Type": "application/json"
            }

            last_error = None
            for attempt in dalle_thumbnail_attempts(title, topic):
                structured_logger.info(
                    "Generating DALL-E 3 thumbnail",
                    canonical_filename=canonical_filename,
                    model=attempt.get("model"),
                    quality=attempt["quality"],
                    prompt_len=len(attempt["prompt"]),
                )
                payload = {
                    "model": attempt.get("model", "gpt-image-1"),
                    "prompt": attempt["prompt"],
                    "n": 1,
                    "size": "1024x1024",
                    "quality": attempt["quality"],
                }
                try:
                    response = requests.post(
                        "https://api.openai.com/v1/images/generations",
                        headers=headers,
                        json=payload,
                        timeout=90,
                    )
                except Exception as e:
                    last_error = str(e)
                    structured_logger.warning(
                        "DALL-E request failed",
                        canonical_filename=canonical_filename,
                        error=last_error,
                    )
                    continue
                if response.status_code != 200:
                    last_error = (response.text or "")[:400]
                    structured_logger.warning(
                        "DALL-E API error, trying next prompt",
                        canonical_filename=canonical_filename,
                        status_code=response.status_code,
                        error_text=last_error,
                    )
                    continue
                item = (response.json().get("data") or [{}])[0]
                image_bytes = None
                if item.get("url"):
                    img_response = requests.get(item["url"], timeout=30)
                    if img_response.status_code == 200:
                        image_bytes = img_response.content
                    else:
                        last_error = f"download {img_response.status_code}"
                elif item.get("b64_json"):
                    import base64
                    image_bytes = base64.b64decode(item["b64_json"])
                if not image_bytes:
                    last_error = last_error or "image response missing url and b64_json"
                    continue
                thumbnail_filename = f"{canonical_filename}-thumb.jpg"
                blob = bucket.blob(f"thumbnails/{thumbnail_filename}")
                blob.upload_from_string(image_bytes, content_type="image/jpeg")
                public_url = f"https://storage.googleapis.com/{self.bucket_name}/thumbnails/{thumbnail_filename}"
                structured_logger.info(
                    "DALL-E thumbnail uploaded",
                    canonical_filename=canonical_filename,
                    public_url=public_url,
                )
                return public_url

            structured_logger.warning(
                "DALL-E thumbnail exhausted attempts, using fallback",
                canonical_filename=canonical_filename,
                error=last_error,
            )
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
            bucket = storage_client.bucket(media_store.PRIVATE_BUCKET)
            
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
                        "model": "gpt-image-1",
                        "prompt": prompt,
                        "n": 1,
                        "size": "1536x1024",
                        "quality": "medium",
                    }
                    
                    response = requests.post(
                        "https://api.openai.com/v1/images/generations",
                        headers=headers,
                        json=payload,
                        timeout=60
                    )
                    
                    if response.status_code == 200:
                        import base64
                        item = (response.json().get("data") or [{}])[0]
                        image_bytes = None
                        if item.get("url"):
                            img_response = requests.get(item["url"], timeout=30)
                            if img_response.status_code == 200:
                                image_bytes = img_response.content
                        elif item.get("b64_json"):
                            image_bytes = base64.b64decode(item["b64_json"])
                        if image_bytes:
                            image_filename = f"{canonical_filename}-image-{i+1}.jpg"
                            blob = bucket.blob(f"episode-images/{image_filename}")
                            blob.upload_from_string(image_bytes, content_type="image/jpeg")
                            
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
                                                     status_code=response.status_code)
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
    
    async def _notify_failure(self, exc: BaseException, job_id: str, topic: str, subscriber_email: Optional[str]) -> None:
        """Gap 3 fix 1 (C8): tell the requester, in plain language and without internals, why no episode was made, and
        tell the administrator the raw error. One email per distinct address; each send is isolated so a failing
        email can never mask the job's real failure."""
        notice = describe_failure(exc)
        raw = f"{type(exc).__name__}: {exc}"
        targets = []
        if subscriber_email:
            targets.append((subscriber_email, notice["summary"], notice["what_to_do"]))
        if ERROR_NOTIFICATION_EMAIL and ERROR_NOTIFICATION_EMAIL.lower() != (subscriber_email or "").lower():
            targets.append((ERROR_NOTIFICATION_EMAIL, raw, notice["what_to_do"]))
        elif ERROR_NOTIFICATION_EMAIL and targets:
            # requester and administrator are the same address: send the administrator's detail once
            targets[0] = (subscriber_email, f"{notice['summary']} [{raw}]", notice["what_to_do"])
        for address, message, what_to_do in targets:
            try:
                await self.email_service.send_podcast_failure_email(
                    recipient_email=address, job_id=job_id, topic=topic, error_message=message, what_to_do=what_to_do)
            except Exception as email_error:
                structured_logger.error("Failed to send failure email notification",
                                       job_id=job_id, error_type=type(email_error).__name__)

    @staticmethod
    def _description_body(description: str) -> str:
        """The description text before its first code-built or closing section (References, Further reading, Hashtags, Episode Details)."""
        cut = len(description)
        for marker in ("\n## References", "\n## Further reading", "\n## Hashtags", "\n## Episode Details"):
            i = description.find(marker)
            if i != -1:
                cut = min(cut, i)
        return description[:cut]

    def _finalize_content(self, content: dict, request, research_context, naming_result) -> dict:
        """Hashtags, code-built reference sections, placeholder cleanup, the 4000-character limit and venue rewrites.

        This is the job's post-generation text processing, moved into a method unchanged (plus measurement) so the
        sandbox harness runs exactly the code the job runs. Modifies ``content`` in place and returns the measurements
        of what the length limit removed. Writes nothing anywhere."""
        # Gap 3 fix 1: the paper labels [P1], [P2] ... are for the model only; remove any that leaked into the spoken
        # script or the description before anything is stored, spoken or shown.
        content['script'], _n_script = strip_pn_markers_counted(content.get('script') or "")
        content['description'], _n_desc = strip_pn_markers_counted(content.get('description') or "")
        # Gap 3 fix 1: notation that survived the prompt becomes words (the loop already refused anything the table cannot
        # convert, so a leftover here is a defect and stops the episode rather than being dropped).
        content['script'], _bad_s = speak_text(content['script'])
        _body, _sep, _tail = content['description'].partition("\n## ")
        _body, _bad_d = speak_text(_body)
        content['description'] = _body + (_sep + _tail if _sep else "")
        if _bad_s or _bad_d:
            raise UnspeakableNotationError(_bad_s + _bad_d)
        # Generate relevant hashtags
        content['hashtags'] = generate_relevant_hashtags(
            request.topic, 
            request.category, 
            content.get('title', ''), 
            ""
        )
        
        # Check if description already has hashtags and references, if not add them
        if '## Hashtags' not in content['description'] and '---' not in content['description']:
            # Add hashtags and closing message
            content['description'] += f"""

## Hashtags
{content['hashtags']}

"""
        
        # Gap 3 fix 1 (C6): References and Further reading are built by code from the confirmed papers. Any
        # reference section the model wrote anyway is removed first; the two legacy fallbacks that rebuilt
        # references from model text or from the first five sources are gone.
        if getattr(research_context, 'curated', None) is not None:
            content['description'] = _curated.apply_curated_sources(
                content['description'], research_context.curated, research_context.confirmed_papers, naming_result.named_pids)
        else:
            content['description'] = apply_reference_sections(
                content['description'], research_context.confirmed_papers, naming_result.named_pids, research_context.requested_pid)
        content['papers'] = [_curated.storage_dict(c) for c in research_context.confirmed_papers]
        content['papers_named'] = list(naming_result.named_pids)
        content['requested_pid'] = research_context.requested_pid
        content['references_built_by'] = REFERENCES_BUILT_BY if getattr(research_context, 'curated', None) is None else _curated.BUILT_BY

        # Clean placeholder text and limit description length
        content['description'] = clean_placeholder_text_from_description(content['description'])
        _before = content['description']
        content['description'] = limit_description_length(content['description'], 4000)
        _after = content['description']
        limit_metrics = {
            'description_chars_before_limit': len(_before),
            'description_chars_after_limit': len(_after),
            'body_chars_before_limit': len(self._description_body(_before)),
            'body_chars_after_limit': len(self._description_body(_after)),
        }
        limit_metrics['body_chars_removed_by_limit'] = limit_metrics['body_chars_before_limit'] - limit_metrics['body_chars_after_limit']
        content['description'] = sanitize_reference_placeholders(
            content['description'], known_year=request.paper_year
        )
        content['script'] = rewrite_index_venues(
            content.get('script') or "", request.paper_journal
        )
        content['description'] = rewrite_index_venues(
            content['description'], request.paper_journal
        )
        # (the requested paper is always P1 in References, built from its registry record, so nothing is added here)
        content['itunes_summary'] = extract_itunes_summary(content['description'])
        limit_metrics['pn_markers_removed'] = {'script': _n_script, 'description': _n_desc}
        return limit_metrics

    @staticmethod
    def _job_rejection_sink(job_ref):
        """A callback that appends rejection records to the job record (best effort: a storage error never fails the episode)."""
        def store(items):
            from google.cloud import firestore as _fs
            job_ref.update({'rejections': _fs.ArrayUnion(items)})
        return store

    async def _verify_final_text(self, content: dict, request, research_context, google_key: str, job_id: str, on_rejection=None) -> dict:
        """Run the post-generation checks again on the final text. They ran on the generated text inside the regeneration loop; the
        text that is stored and spoken has since been through notation conversion, venue rewriting, reference building and the
        description limit. Nothing can be regenerated here, so any failure fails the episode. Writes nothing; returns a summary."""
        script = content.get('script') or ''
        description = content.get('description') or ''
        body = self._description_body(description)
        words = len(script.split())
        min_words = calculate_minimum_words_for_duration(request.duration)
        max_words = calculate_maximum_words_for_duration(request.duration)

        final_seq = {"n": 0}

        def reject(items):
            for item in items:
                item["seq"] = 1000 + final_seq["n"]
                final_seq["n"] += 1
                structured_logger.warning("Rejection", job_id=job_id, **item)
            if on_rejection:
                try:
                    on_rejection(items)
                except Exception as e:
                    structured_logger.warning("Could not store rejections on the job", job_id=job_id, error=str(e))

        async def model_call(stage, factory):
            for n in range(self.MAX_TRANSIENT_RETRIES + 1):      # an unreadable answer from a check is repeated, not fatal
                try:
                    return await factory()
                except Exception as e:
                    reject([rejection_log.transient_item(0, "final_" + stage, e)])
                    if n >= self.MAX_TRANSIENT_RETRIES:
                        raise
                    await asyncio.sleep(2)

        if words > max_words:
            reject([rejection_log.length_item(0, "too_long", words, max_words)])
            raise ScriptTooLongError(words, max_words)
        if words < min_words:
            reject([rejection_log.length_item(0, "too_short", words, min_words)])
            raise ScriptTooShortError(words, min_words)
        bad_notation = notation_problems(script, body)
        if bad_notation:
            reject(rejection_log.notation_items(0, bad_notation))
            raise UnspeakableNotationError(bad_notation)
        banned = banned_phrase_hits(script, description)
        if banned:
            reject(rejection_log.banned_items(0, banned))
            raise BannedPhraseError(banned)
        read_aloud = read_aloud_sentences(script, request.topic)
        if read_aloud:
            reject(rejection_log.read_aloud_items(0, read_aloud))
            raise TopicReadAloudError(read_aloud)
        missing_cov = missing_coverage_statements(script, uncovered_named_things(request.topic, research_context.confirmed_papers))
        if missing_cov:
            reject(rejection_log.coverage_items(0, missing_cov))
            raise CoverageStatementError(missing_cov)
        llm = make_gemini_llm_call(google_key)
        naming = await model_call("naming_check", lambda: check_naming(script, description, research_context.confirmed_papers, llm, topic=request.topic))
        if not naming.passed:
            reject(rejection_log.naming_items(0, naming.violations))
            raise NamingViolationError(naming.violations)
        unlisted = [pid for pid in naming.named_pids if pid not in (content.get('papers_named') or [])]
        if unlisted:
            raise FinalTextCheckError("it names " + ", ".join(unlisted) + " which the reference list was not built for")
        named = [c for c in research_context.confirmed_papers if c.pid in naming.named_pids]
        attribution = await model_call("attribution_check", lambda: check_attributions(script, named, llm))
        if not attribution.passed:
            reject(rejection_log.attribution_items(0, attribution.checked, _curated.withheld_pids(research_context)))
            raise AttributionError(attribution.violations)
        curated = getattr(research_context, "curated", None)
        if curated is not None:
            curated_viol = curated.checks(script)
            if curated_viol:
                reject(rejection_log.curated_items(0, curated_viol))
                raise _cc.CuratedCheckError(curated_viol)
        summary = {'words': words, 'min_words': min_words, 'max_words': max_words, 'named_pids': list(naming.named_pids),
                   'attributions_checked': len(attribution.checked)}
        content['final_text_checks'] = summary
        structured_logger.info("Final text checks passed", job_id=job_id, **summary)
        return summary

    MAX_CONTENT_RETRIES = 3     # fix 5: four content attempts in all
    MAX_TRANSIENT_RETRIES = 3   # fix 5: model or parse errors, counted separately; they never use a content attempt

    async def _generate_checked_content(self, request, research_context, google_key: str, job_id: str, on_rejection=None):
        """Generate the script and description, accept them only if they pass every check.

        Up to four content attempts (MAX_CONTENT_RETRIES + 1). A script is rejected for being too short or too long, for naming works that are
        not among the confirmed papers, for notation that cannot be read aloud, for banned wording, or for an attribution its paper's abstract
        does not support; what was wrong is fed back to the next attempt, and after the last attempt the episode fails. Errors of the model
        itself (a generator reply that is not JSON, a timeout, a check whose answer cannot be read) are transient: that call is repeated
        without using a content attempt, up to MAX_TRANSIENT_RETRIES times in all. Every rejection is recorded in full (logged, kept in
        ``self._last_rejections`` and passed to ``on_rejection``). Returns (content, naming_result, naming_attempts). Writes nothing itself."""
        max_retries = self.MAX_CONTENT_RETRIES
        content = None
        min_words = calculate_minimum_words_for_duration(request.duration)
        max_words = calculate_maximum_words_for_duration(request.duration)
        naming_llm = make_gemini_llm_call(google_key)
        naming_feedback = ""
        naming_result = None
        naming_attempts = []
        rejections = []
        transient = {"n": 0}
        self._last_naming_attempts = naming_attempts  # same list objects: the sandbox harness reads them even when this raises
        uncovered = uncovered_named_things(request.topic, research_context.confirmed_papers)   # fix 7: names in the topic no paper covers
        self._last_rejections = rejections

        def reject(items):
            for i, item in enumerate(items):
                item["seq"] = len(rejections) + i    # keeps identical records distinct (Firestore ArrayUnion drops duplicates)
            rejections.extend(items)
            for item in items:
                structured_logger.warning("Rejection", job_id=job_id, **item)
            if on_rejection:
                try:
                    on_rejection(items)
                except Exception as e:
                    structured_logger.warning("Could not store rejections on the job", job_id=job_id, error=str(e))

        async def transient_retry(stage, attempt_no, factory):
            while True:
                try:
                    return await factory()
                except Exception as e:
                    transient["n"] += 1
                    reject([rejection_log.transient_item(attempt_no + 1, stage, e)])
                    if transient["n"] > self.MAX_TRANSIENT_RETRIES:
                        structured_logger.error("Model errors used up the transient retries", job_id=job_id, stage=stage,
                                               error=str(e), error_type=type(e).__name__)
                        raise
                    await asyncio.sleep(2)

        try:
            for attempt in range(max_retries + 1):
                last = attempt == max_retries
                async def generate_once():
                    reply = await asyncio.wait_for(
                        self.generate_content_from_research_context(request, research_context, google_key, retry_attempt=attempt, naming_feedback=naming_feedback),
                        timeout=600)
                    check_model_reply(reply, min_words)       # raises MalformedModelReply: a broken reply is a model error, not a short script
                    return reply
                generated_content = await transient_retry("generation", attempt, generate_once)
                script = generated_content.get('script', '') if isinstance(generated_content, dict) else ''
                description = generated_content.get('description', '') if isinstance(generated_content, dict) else ''
                word_count = len(script.split()) if script else 0

                if word_count > max_words or word_count < min_words:
                    too_long = word_count > max_words
                    naming_attempts.append({'attempt': attempt + 1, **({'too_long': word_count, 'max_words': max_words} if too_long else
                                                                      {'too_short': word_count, 'min_words': min_words})})
                    reject([rejection_log.length_item(attempt + 1, "too_long" if too_long else "too_short", word_count, max_words if too_long else min_words)])
                    if last:
                        raise ScriptTooLongError(word_count, max_words) if too_long else ScriptTooShortError(word_count, min_words)
                    naming_feedback = length_feedback(word_count, max_words, min_words) if too_long else short_feedback(word_count, min_words, max_words)
                    await asyncio.sleep(2)
                    continue

                # Gap 3 fix 1 (C5): the script may name only confirmed papers
                naming_result = await transient_retry("naming_check", attempt, lambda: check_naming(script, description, research_context.confirmed_papers, naming_llm, topic=request.topic))
                naming_attempts.append({'attempt': attempt + 1, **naming_result.summary()})
                # Gap 3 fix 1: notation the converter cannot turn into words is a reason to regenerate, then to fail
                bad_notation = notation_problems(script, description)
                naming_attempts[-1]['unspeakable_notation'] = bad_notation
                # Fix 4 (a): overstated or promotional wording from the one list in config/banned_phrases.json
                banned = banned_phrase_hits(script, description)
                naming_attempts[-1]['banned_phrases'] = [{'phrase': h['phrase'], 'matched': h['matched'], 'where': h['where']} for h in banned]
                # Fix 7: the topic title is not read aloud, and what the topic names but no paper covers is called out as not covered
                read_aloud = read_aloud_sentences(script, request.topic)
                missing_cov = missing_coverage_statements(script, uncovered)
                # Curated-sources mode: status wording, verbatim runs, spoken names, class labels (all deterministic)
                curated_viol = research_context.curated.checks(script) if getattr(research_context, "curated", None) is not None else []
                naming_attempts[-1]['curated_checks'] = _cc.summary(curated_viol)
                naming_attempts[-1]['topic_read_aloud'] = len(read_aloud)
                naming_attempts[-1]['coverage_statement_missing'] = missing_cov
                # Fix 4 (b): a claim attributed to a named paper must be supported by that paper's abstract
                attribution = None
                if naming_result.passed:
                    named = [c for c in research_context.confirmed_papers if c.pid in naming_result.named_pids]
                    attribution = await transient_retry("attribution_check", attempt, lambda: check_attributions(script, named, naming_llm))
                    naming_attempts[-1]['attribution'] = attribution.summary()
                    reject(rejection_log.attribution_items(attempt + 1, attribution.checked, _curated.withheld_pids(research_context)))     # every verdict, supported ones too, in full

                if naming_result.passed and not bad_notation and not banned and attribution.passed and not read_aloud and not missing_cov and not curated_viol:
                    content = generated_content
                    structured_logger.info(f"Content generation succeeded on attempt {attempt + 1}", job_id=job_id, word_count=word_count,
                                          min_required=min_words, transient_retries=transient["n"])
                    break
                reject(rejection_log.naming_items(attempt + 1, naming_result.violations) + rejection_log.notation_items(attempt + 1, bad_notation)
                       + rejection_log.banned_items(attempt + 1, banned) + rejection_log.read_aloud_items(attempt + 1, read_aloud)
                       + rejection_log.coverage_items(attempt + 1, missing_cov) + rejection_log.curated_items(attempt + 1, curated_viol))
                structured_logger.warning("Script rejected: unlisted works, unspeakable notation, banned wording or unsupported attribution",
                                         job_id=job_id, attempt=attempt + 1, violations=len(naming_result.violations),
                                         unspeakable_notation=bad_notation, banned_phrases=[h['matched'] for h in banned],
                                         unsupported_attributions=len(attribution.violations) if attribution else 0)
                if last:
                    if not naming_result.passed:
                        raise NamingViolationError(naming_result.violations)
                    if bad_notation:
                        raise UnspeakableNotationError(bad_notation)
                    if banned:
                        raise BannedPhraseError(banned)
                    if curated_viol:
                        raise _cc.CuratedCheckError(curated_viol)
                    if attribution is not None and not attribution.passed:
                        raise AttributionError(attribution.violations)
                    if read_aloud:
                        raise TopicReadAloudError(read_aloud)
                    raise CoverageStatementError(missing_cov)
                naming_feedback = ((feedback_text(naming_result, research_context.confirmed_papers) if not naming_result.passed else "")
                                   + (notation_feedback(bad_notation) if bad_notation else "")
                                   + (banned_feedback(banned) if banned else "")
                                   + (attribution_feedback(attribution) if attribution and not attribution.passed else "")
                                   + (read_aloud_feedback(read_aloud) if read_aloud else "")
                                   + (coverage_feedback(missing_cov) if missing_cov else "")
                                   + (_cc.feedback_text(curated_viol) if curated_viol else ""))
                await asyncio.sleep(2)
        except Exception as e:
            structured_logger.error("Content generation failed after all retries", job_id=job_id, error=str(e), error_type=type(e).__name__)
            raise

        if not content:
            raise Exception("Failed to generate content after all retry attempts")

        return content, naming_result, naming_attempts

    async def run_podcast_generation_job(
        self, 
        job_id: str, 
        request: PodcastRequest, 
        subscriber_id: Optional[str] = None,
        curated_run=None
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
                                          subscriber_id=subscriber_id)
            except Exception as e:
                structured_logger.warning("Could not get subscriber email, using default",
                                         job_id=job_id,
                                         subscriber_id=subscriber_id,
                                         error_type=type(e).__name__)
        
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
                    research_integrator.curated_research_for_podcast(curated_run, request.expertise_level) if curated_run is not None else
                    research_integrator.comprehensive_research_for_podcast(
                        topic=request.topic,
                        additional_context=request.additional_instructions or "",
                        source_links=request.source_links or [],
                        expertise_level=request.expertise_level,
                        require_minimum_sources=3,  # FAIL FAST unless 3 papers are CONFIRMED in their registry
                        required_paper=({"doi": request.paper_doi, "title": request.paper_title} if request.paper_title else None),
                    ),
                    timeout=300 if curated_run is None else 600  # 5 minutes for discovery; the curated mode only analyses
                )
                
                structured_logger.info("Research completed successfully",
                                      job_id=job_id,
                                      quality_score=round(research_context.research_quality_score, 1),
                                      sources_count=len(research_context.research_sources),
                                      significance_count=len(research_context.significance))
                
                # Store research metadata in job (including sources for references)
                research_sources_summary = []
                for source in research_context.research_sources[:10]:
                    research_sources_summary.append({
                        'title': source.title,
                        'source': source.source,
                        'journal': getattr(source, 'journal', None),
                        'doi': source.doi,
                        'url': source.url,
                        'publication_date': source.publication_date,
                        'authors': source.authors[:3],  # Store first 3 authors
                        'pid': getattr(source, 'pid', None),
                    })
                
                job_ref.update({
                    'research_sources_count': len(research_context.research_sources),
                    'research_quality_score': research_context.research_quality_score,
                    'significance_count': len(research_context.significance),
                    'research_sources_summary': research_sources_summary,
                    'confirmed_papers': [_curated.storage_dict(c) for c in research_context.confirmed_papers],
                    'dropped_candidates': [d.to_dict() for d in research_context.dropped_candidates],
                    'confirmation_stats': getattr(research_context, 'confirmation_stats', {}),
                    'relevance_scores': getattr(research_context, 'relevance_scores', {}),
                    'requested_pid': research_context.requested_pid,
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
                    'error_type': ('curated_analysis_failed' if type(e).__name__ == 'CuratedAnalysisFailed'
                                   else RESEARCH_FAILURE_TYPES.get(type(e).__name__, 'insufficient_research')),
                    'updated_at': datetime.utcnow().isoformat()
                })
                
                # Send failure email (C8). The call that used to be here was to send_podcast_ready_email, which EmailService
                # does not have: it raised AttributeError inside this handler and the job ended up recording that error
                # instead of the real research failure.
                if self.email_service:
                    await self._notify_failure(e, job_id, request.topic, subscriber_email)
                
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
                
                # Generate, check and (if needed) regenerate. Gap 3 fix 1 (C5): the script may name only confirmed
                # papers; after the allowed regenerations the episode fails (NamingViolationError).
                content, naming_result, naming_attempts = await self._generate_checked_content(
                    request, research_context, google_key, job_id, on_rejection=self._job_rejection_sink(job_ref))

                content_memory_after = psutil.virtual_memory().percent

                # Pre-publish gate (earliest possible point): refuse to
                # continue at all -- not to podcast_jobs, not to episodes,
                # not to the feed -- if the generated description still
                # contains a known generator placeholder pattern. Raising
                # here happens before job_ref.update() below, so nothing
                # gets written anywhere for this job.
                if isinstance(content, dict):
                    validate_description_before_publish(content.get('description', ''))

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
            
            limit_metrics = self._finalize_content(content, request, research_context, naming_result)
            
            # Robust validation added here:
            if (not content or 
                not isinstance(content, dict) or
                not all(k in content for k in ['title', 'script', 'description']) or
                not content.get('title') or len(str(content.get('title', '')).strip()) < 5 or
                not content.get('script') or len(str(content.get('script', '')).strip()) < 50 or
                not content.get('description') or len(str(content.get('description', '')).strip()) < 20):
                
                error_detail = f"Invalid content received: {str(content)[:200]}..."
                raise ValueError(f"Content generation returned empty, incomplete, or placeholder data. Details: {error_detail}")
            
            # Validate script length matches duration requirement (a script is never padded to reach it)
            script = content.get('script', '')
            is_valid, error_msg, final_script = validate_script_length(script, request.duration)
            if not is_valid:
                word_count = len(script.split())
                structured_logger.error("Script length validation failed",
                                       job_id=job_id,
                                       duration=request.duration,
                                       script_word_count=word_count,
                                       error=error_msg)
                raise ValueError(f"Script does not meet duration requirement. {error_msg}")
            
            # Fix 4: every post-generation check runs again on the text that is stored and spoken (after notation became words,
            # venues were rewritten, references were built and the description was limited); nothing is padded or added unchecked.
            await self._verify_final_text(content, request, research_context, google_key, job_id, on_rejection=self._job_rejection_sink(job_ref))
            if curated_run is not None:
                _curated.check_tts_threshold(len(content['script']))     # a script over the producer's own threshold stops before any audio is made

            structured_logger.info("Content validation passed",
                                  job_id=job_id,
                                  script_word_count=len(content['script'].split()),
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
            
            # Characters sent to ElevenLabs are counted per request. They are stored on the job whether or not the audio step
            # succeeds (a failed run still used them), and again, with the rest of the record, on success.
            tts_usage = TtsUsage()
            try:
                audio_url = await self.elevenlabs_voice_service.generate_multi_voice_audio_with_bumpers(
                    content["script"],
                    job_id,
                    canonical_filename,
                    intro_path="bumpers/copernicus-intro.mp3",
                    outro_path="bumpers/copernicus-outro.mp3",
                    host_voice_id=request.host_voice_id,
                    expert_voice_id=request.expert_voice_id,
                    tts_usage=tts_usage,
                )
            finally:
                if tts_usage.segments:
                    try:
                        job_ref.update(tts_usage.as_record())
                    except Exception as usage_error:
                        structured_logger.warning("Could not store the text-to-speech usage on the job",
                                                  job_id=job_id, error_type=type(usage_error).__name__)
                    structured_logger.info("Text-to-speech usage", job_id=job_id, tts_characters=tts_usage.characters,
                                           tts_segments=tts_usage.segments, tts_failed_segments=tts_usage.failed_segments)
            
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
            
            # Prepare update data
            update_data = {
                'status': 'completed',
                'updated_at': datetime.utcnow().isoformat(),
                'named_work_check': {'attempts': naming_attempts, 'final': 'passed'},
                **tts_usage.as_record(),
                **({'curated_run': curated_run.review_pack(
                    naming_result.named_pids,
                    {'naming_attempts': len(naming_attempts), 'final_text_checks': content.get('final_text_checks'),
                     'curated_checks': _cc.summary([])},
                    {'tts_estimated_characters': len(content.get('script') or ''), 'tts_warn_threshold': tts_usage.as_record()['tts_warn_threshold']})}
                   if curated_run is not None else {}),
                'references_built_by': content.get('references_built_by', REFERENCES_BUILT_BY),
                'description_limit': limit_metrics,  # what the 4000-character limit removed (gap 3 fix 1)
                'result': {
                    'title': content.get('title') or request.topic or 'Untitled Podcast',
                    'script': content.get('script', ''),
                    'description': content.get('description', ''),
                    'audio_url': audio_url,
                    'thumbnail_url': thumbnail_url,
                    'episode_images': episode_images,  # Array of 1-2 image URLs
                    'transcript_url': transcript_url,
                    'media_state': 'private',
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
            }
            
            # Generate embedding for vector search
            try:
                from utils.auto_embedding import add_embedding_to_podcast_data
                update_data = add_embedding_to_podcast_data(update_data)
                structured_logger.info("Embedding generated for podcast",
                                      job_id=job_id)
            except Exception as e:
                structured_logger.warning("Failed to generate embedding for podcast (non-blocking)",
                                         job_id=job_id,
                                         error=str(e))
                # Continue without embedding - podcast creation should not fail
            
            # Update job document
            job_ref.update(update_data)
            
            # NOTE: Option A Architecture - episodes as single source of truth for RSS
            # AUTO-PROMOTE by default (YouTube-style): All podcasts are automatically promoted to episodes
            # This gives users immediate publication ability without waiting for admin approval.
            # Admin can still unpromote/remove if needed (moderation after the fact).
            # - podcast_jobs: Complete generation history (all podcasts ever created)
            # - episodes: Public catalog (auto-promoted, can be unpromoted if needed)
            try:
                # Carry the embedding already computed onto update_data forward into
                # the episode doc -- it would otherwise land only on podcast_jobs.
                # Empty dict if missing or wrong-dimension; never blocks promote.
                from utils.auto_embedding import extract_valid_embedding_fields
                episode_embedding_fields = extract_valid_embedding_fields(update_data)

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
                        "media_state": "private",
                        "duration": request.duration,
                        "canonical_filename": canonical_filename,
                        "generated_at": generated_timestamp,
                        **tts_usage.as_record(),
                        **({'curated_list_id': curated_run.list_id, 'curated_list_hash': curated_run.list_hash} if curated_run is not None else {}),
                        **episode_embedding_fields,
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
            except DescriptionValidationError:
                # Never treat this as a non-blocking catalog hiccup -- it
                # means the episode was refused, not just "not promoted
                # yet". Let it propagate so the job ends up 'failed' with
                # a message naming the check that failed.
                raise
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
                                  memory_before_percent=round(email_memory_before, 1))
            
            # The audio is private until the episode is published, so its public address would not open: send a 7-day signed link
            listen_url, link_valid_days = audio_url, None
            try:
                signed_listen = await asyncio.to_thread(media_store.signed_audio_link, canonical_filename, media_store.MAX_SIGNED_DAYS)
                if signed_listen:
                    listen_url, link_valid_days = signed_listen, media_store.MAX_SIGNED_DAYS
            except Exception as link_error:
                structured_logger.warning("Could not sign the audio link for the ready email", job_id=job_id, error=str(link_error))
            await self.email_service.send_podcast_completion_email(
                recipient_email=subscriber_email,
                job_id=job_id,
                podcast_title=content.get('title', 'Untitled Podcast'),
                topic=request.topic,
                audio_url=listen_url,
                duration=request.duration,
                canonical_filename=canonical_filename,
                link_valid_days=link_valid_days
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
            
            # Send failure email notification (C8): the requester gets a plain explanation, the administrator the raw error
            await self._notify_failure(e, job_id, request.topic if request else "Unknown", subscriber_email)

    async def run_curated_generation_job(self, job_id: str, list_doc: dict, request: PodcastRequest, subscriber_id: Optional[str] = None,
                                         private_texts: Optional[dict] = None):
        """Curated-sources mode (design §3.1): generate one episode from an approved, frozen source list. Only the research stage differs
        from ``run_podcast_generation_job``, which does everything else (generation, every check, audio, the private record). Nothing here
        publishes: the episode is private (``submitted_to_rss=False``, media in the private bucket) until Gary publishes it."""
        try:
            run = _curated.CuratedRun.from_list_doc(list_doc, topic=request.topic, private_texts=private_texts)
        except _curated.CuratedListError as e:
            if db:
                db.collection('podcast_jobs').document(job_id).update({'status': 'failed', 'error': str(e), 'error_type': 'curated_list_invalid',
                                                                       'updated_at': datetime.utcnow().isoformat()})
            structured_logger.error("Curated source list refused", job_id=job_id, error_type="CuratedListError")
            return
        await self.run_podcast_generation_job(job_id, request, subscriber_id=subscriber_id, curated_run=run)


# Create singleton instance
# Note: vertex_ai_model will be injected when the service is used
podcast_generation_service = PodcastGenerationService()

