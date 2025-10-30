from fastapi import FastAPI, HTTPException, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, List
import uuid
from datetime import datetime, timedelta
import os
import asyncio
import aiohttp
import json
from paper_processor import process_paper, ResearchPaper, AnalyzeOptions, PaperAnalysis, format_citation
from copernicus_character import get_copernicus_character, get_character_prompt, CopernicusCharacter
from elevenlabs_voice_service import ElevenLabsVoiceService
from email_service import EmailService
from content_fixes import apply_content_fixes, fix_script_format_for_multi_voice, limit_description_length, extract_itunes_summary, generate_relevant_hashtags, validate_academic_references
from research_pipeline import ComprehensiveResearchPipeline, ResearchSource
from podcast_research_integrator import PodcastResearchIntegrator, PodcastResearchContext
import re
from google.api_core import retry
import time
import psutil
import gc
import logging
import sys
from contextlib import asynccontextmanager
from typing import Dict, Any

# Structured logging setup
class StructuredLogger:
    def __init__(self, name: str):
        self.logger = logging.getLogger(name)
        self.logger.setLevel(logging.INFO)
        
        # Ensure we have a handler
        if not self.logger.handlers:
            handler = logging.StreamHandler(sys.stdout)
            formatter = logging.Formatter('%(message)s')
            handler.setFormatter(formatter)
            self.logger.addHandler(handler)
    
    def log(self, level: str, message: str, **kwargs):
        """Log structured message with additional context"""
        log_entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "level": level.upper(),
            "message": message,
            **kwargs
        }
        self.logger.info(json.dumps(log_entry))
    
    def info(self, message: str, **kwargs):
        self.log("info", message, **kwargs)
    
    def error(self, message: str, **kwargs):
        self.log("error", message, **kwargs)
    
    def warning(self, message: str, **kwargs):
        self.log("warning", message, **kwargs)
    
    def debug(self, message: str, **kwargs):
        self.log("debug", message, **kwargs)

# Global structured logger
structured_logger = StructuredLogger("copernicus-podcast")

# 2-SPEAKER VOICE CONFIGURATION
# Simplified podcast format with just Matilda (female host) and Adam (male expert)
COPERNICUS_VOICES = {
    "matilda": {
        "voice_id": "XrExE9yKIg1WjnnlVkGX",
        "role": "host",
        "gender": "female",
        "description": "Professional host, warm and engaging interviewer"
    },
    "adam": {
        "voice_id": "pNInz6obpgDQGcFmaJgB",
        "role": "expert",
        "gender": "male",
        "description": "Expert researcher, authoritative but approachable"
    }
}

def get_speaker_labels():
    """Return the 2 speaker labels used in podcast scripts"""
    return ["MATILDA", "ADAM"]

# Context manager for step tracking
@asynccontextmanager
async def with_step(step_name: str, job_id: str = None, **context):
    """Context manager for tracking execution steps with timing"""
    start_time = time.time()
    step_id = f"{step_name}_{int(start_time * 1000)}"
    
    structured_logger.info(f"Starting step: {step_name}", 
                          job_id=job_id, 
                          step=step_name, 
                          step_id=step_id,
                          **context)
    
    try:
        yield step_id
    except Exception as e:
        duration_ms = int((time.time() - start_time) * 1000)
        structured_logger.error(f"Step failed: {step_name}", 
                               job_id=job_id,
                               step=step_name,
                               step_id=step_id,
                               duration_ms=duration_ms,
                               error=str(e),
                               error_type=type(e).__name__,
                               **context)
        raise
    else:
        duration_ms = int((time.time() - start_time) * 1000)
        structured_logger.info(f"Step completed: {step_name}", 
                              job_id=job_id,
                              step=step_name,
                              step_id=step_id,
                              duration_ms=duration_ms,
                              **context)

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
                        print(f"⚠️ Upload attempt {attempt + 1} failed: {e}. Retrying in {wait_time}s...")
                        await asyncio.sleep(wait_time)
                    else:
                        print(f"❌ Upload failed after {max_retries} attempts: {e}")
            raise last_exception
        return wrapper
    return decorator

def _extract_json_from_response(text: str) -> dict:
    """Extracts a JSON object from a string, even if it's embedded in other text."""
    import re
    import json
    
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
            print(f"✅ JSON parsing succeeded on attempt {i}")
            return result
        except json.JSONDecodeError as e:
            print(f"⚠️  JSON parsing attempt {i} failed: {e}")
            if i == len(parsing_attempts):
                # Last attempt failed, show detailed error
                print(f"❌ All JSON parsing attempts failed")
                print(f"Original text snippet: {json_str[:300]}...")
                raise ValueError(f"Failed to decode extracted JSON after {len(parsing_attempts)} attempts: {e}\nOriginal text snippet: {json_str[:200]}...")
        except Exception as e:
            print(f"⚠️  JSON parsing attempt {i} failed with unexpected error: {e}")
            if i == len(parsing_attempts):
                raise

def _extract_essential_json(json_str: str) -> dict:
    """Last resort: Try to extract essential JSON structure even if malformed"""
    import re
    
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

# Vertex AI and Secret Manager imports
try:
    from google import genai as google_genai_client
    import vertexai
    from google.cloud import secretmanager, firestore
    from google.oauth2 import service_account
    VERTEX_AI_AVAILABLE = True
except ImportError as e:
    print(f"⚠️  Vertex AI or Firestore dependencies not available: {e}")
    print("Install with: pip install google-cloud-aiplatform google-cloud-secret-manager google-cloud-firestore")
    VERTEX_AI_AVAILABLE = False

app = FastAPI(title="Copernicus Podcast API - Google AI")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class PodcastRequest(BaseModel):
    topic: str
    category: str = "Computer Science"  # Category from web form
    expertise_level: str = "intermediate"
    format_type: str = "interview"
    duration: str = "5-10 minutes"
    voice_style: str = "professional"
    # Voice selection (Phase 2.2)
    host_voice_id: Optional[str] = None  # Matilda (default)
    expert_voice_id: Optional[str] = None  # Adam (default)
    # Research paper processing fields
    paper_content: Optional[str] = None
    paper_title: Optional[str] = None
    paper_authors: Optional[List[str]] = None
    paper_abstract: Optional[str] = None
    paper_doi: Optional[str] = None
    focus_areas: Optional[List[str]] = None
    include_citations: bool = True
    paradigm_shift_analysis: bool = True
    source_links: Optional[List[str]] = None
    additional_instructions: Optional[str] = None

# Legacy request format for frontend compatibility

# --- Vertex AI Configuration ---
GCP_PROJECT_ID = "regal-scholar-453620-r7"  # Your Google Cloud Project ID
VERTEX_AI_REGION = "us-central1"             # Your desired Vertex AI region
SECRET_ID = "vertex-ai-service-account-key"  # Secret Manager secret ID
SECRET_VERSION_ID = "latest"                 # Use 'latest' or specific version

def get_service_account_credentials_from_secret_manager(project_id: str, secret_id: str, version_id: str):
    """Retrieve service account credentials from Secret Manager for Vertex AI"""
    if not VERTEX_AI_AVAILABLE:
        return None
        
    try:
        client = secretmanager.SecretManagerServiceClient()
        name = f"projects/{project_id}/secrets/{secret_id}/versions/{version_id}"
        response = client.access_secret_version(request={"name": name})
        payload = response.payload.data.decode("UTF-8")
        credentials_info = json.loads(payload)
        return service_account.Credentials.from_service_account_info(credentials_info)
    except Exception as e:
        print(f"❌ Failed to retrieve Vertex AI credentials from Secret Manager: {e}")
        return None

def initialize_vertex_ai():
    """Initialize Vertex AI with credentials from Secret Manager"""
    try:
        # Credentials should be picked up automatically by the library from the environment.
        # The gcloud auth application-default login or service account on Cloud Run handles this.
        client = google_genai_client.Client(vertexai=True, project=GCP_PROJECT_ID, location=VERTEX_AI_REGION)
        
        # Test connection by listing a model
        models = client.models.list()
        print("✅ google-genai client for Vertex AI initialized and model confirmed.")
        return client
        
    except Exception as e:
        print(f"❌ Failed to initialize google-genai Vertex AI client: {e}")
        print("Falling back to Google AI API key if available.")
        return None

def load_all_api_keys_from_secret_manager():
    """Load ALL API keys from Secret Manager on startup"""
    try:
        print("\n" + "="*70)
        print("🔑 LOADING API KEYS FROM SECRET MANAGER")
        print("="*70)
        client = secretmanager.SecretManagerServiceClient()
        
        api_keys = {
            # Research APIs
            "PUBMED_API_KEY": "pubmed-api-key",
            "NASA_ADS_TOKEN": "nasa-ads-token",
            "ZENODO_API_KEY": "zenodo-api-key",
            "NEWS_API_KEY": "news-api-key",
            "YOUTUBE_API_KEY": "youtube-api-key",
            "OPENROUTER_API_KEY": "openrouter-api-key",  # For processing user links
            "CORE_API_KEY": "core-api-key",  # CORE aggregator API
            # LLM APIs
            "GOOGLE_API_KEY": "GOOGLE_AI_API_KEY",
            "GOOGLE_AI_API_KEY": "GOOGLE_AI_API_KEY",
        }
        
        loaded_count = 0
        for env_var, secret_name in api_keys.items():
            if env_var in os.environ:
                print(f"   ⏭️  {env_var} already set in environment")
                loaded_count += 1
                continue
            try:
                name = f"projects/{GCP_PROJECT_ID}/secrets/{secret_name}/versions/latest"
                response = client.access_secret_version(request={"name": name})
                key = response.payload.data.decode("UTF-8").strip()
                if key:
                    os.environ[env_var] = key
                    loaded_count += 1
                    print(f"   ✅ {env_var} loaded from {secret_name}")
            except Exception as e:
                print(f"   ⚠️  Could not load {env_var}: {str(e)[:50]}")
        
        print(f"✅ Loaded {loaded_count}/{len(api_keys)} API keys")
        print("="*70 + "\n")
        return loaded_count > 0
        
    except Exception as e:
        print(f"❌ Failed to load API keys from Secret Manager: {e}")
        return False

def get_google_api_key():
    """Get Google AI API key from Secret Manager or environment"""
    # Check environment first (already loaded on startup)
    key = (os.environ.get("GOOGLE_AI_API_KEY") or 
           os.environ.get("GEMINI_API_KEY") or
           os.environ.get("GOOGLE_API_KEY"))
    
    if key:
        return key
    
    # Fallback: try Secret Manager directly
    try:
        print("🔄 Retrieving Google AI API key from Secret Manager...")
        client = secretmanager.SecretManagerServiceClient()
        name = f"projects/{GCP_PROJECT_ID}/secrets/GOOGLE_AI_API_KEY/versions/latest"
        response = client.access_secret_version(request={"name": name})
        key = response.payload.data.decode("UTF-8").strip()
        if key:
            print("✅ Google AI API key retrieved from Secret Manager")
            os.environ["GOOGLE_AI_API_KEY"] = key
            return key
    except Exception as e:
        print(f"❌ Could not retrieve Google AI API key: {e}")
    
    return None

# Initialize services on startup
print("\n" + "="*70)
print("🚀 COPERNICUS AI BACKEND INITIALIZATION")
print("="*70 + "\n")

# Load all API keys first
load_all_api_keys_from_secret_manager()

# Then initialize AI services
vertex_ai_model = initialize_vertex_ai()

# Initialize Firestore client
try:
    db = firestore.Client(project=GCP_PROJECT_ID, database="copernicusai")
    print("✅ Firestore client initialized successfully")
except Exception as e:
    print(f"❌ Failed to initialize Firestore client: {e}")
    db = None

async def generate_research_driven_content(request: PodcastRequest) -> dict:
    """Generate research-driven content using proper research methodology"""
    
    # Use the working research-driven approach directly
    print("🔬 Using research-driven content generation with proper methodology")
    
    # Try Vertex AI first, then fall back to Google AI API
    if vertex_ai_model:
        print("🚀 Using Vertex AI Gemini for content generation")
        try:
            return await generate_content_vertex_ai(request)
        except Exception as e:
            print(f"⚠️  Vertex AI failed: {e}. Falling back to Google AI API...")
            google_key = get_google_api_key()
            if not google_key:
                print("❌ No Google AI API key available")
                raise ValueError("Both Vertex AI and Google AI API are unavailable.")
            return await generate_content_google_api(request, google_key)
    else:
        print("🔄 Using Google AI API for research-driven content")
        google_key = get_google_api_key()
        if not google_key:
            print("❌ No Google AI API key - using fallback content")
            raise ValueError("Google AI API key is not available.")
        return await generate_content_google_api(request, google_key)

async def generate_enhanced_character_content(request: PodcastRequest) -> dict:
    """Generate content using enhanced character-driven approach"""
    
    try:
        # Use enhanced content generator with character configuration
        from enhanced_content_generator import EnhancedContentGenerator
        from character_config import CharacterConfig
        
        # Initialize character configuration
        character_config = CharacterConfig()
        
        # Initialize enhanced content generator
        content_generator = EnhancedContentGenerator(character_config)
        
        # Convert request to dictionary format
        request_data = {
            'topic': request.topic,
            'duration': request.duration,
            'expertise_level': request.expertise_level,
            'format_type': request.format_type,
            'paper_content': request.paper_content,
            'paper_title': request.paper_title,
            'source_links': request.source_links,
            'additional_instructions': request.additional_instructions
        }
        
        # Generate character-driven content
        content = await content_generator.generate_character_driven_content(request_data)
        
        # Ensure required fields are present
        if not content.get('script'):
            content['script'] = content.get('description', '')
        
        if not content.get('title'):
            content['title'] = f"Research Insights: {request.topic}"
        
        if not content.get('description'):
            content['description'] = f"An exploration of {request.topic} and its implications for scientific understanding."
        
        print(f"✅ Enhanced character-driven content generated successfully")
        return content
        
    except Exception as e:
        print(f"❌ Enhanced content generation failed: {e}")
        raise e

async def generate_content_vertex_ai(request: PodcastRequest) -> dict:
    """Generate content using Vertex AI Gemini. This function will now raise exceptions on failure."""
    # Check if we have research paper content to analyze
    if request.paper_content and request.paper_title:
        print(f"🔬 Processing research paper with Vertex AI: {request.paper_title[:50]}...")
        
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
        return await generate_podcast_from_analysis_vertex(paper, analysis, request)
    else:
        print(f"🎯 Generating topic-based research content with Vertex AI: {request.topic}")
        return await generate_topic_research_content_vertex(request)

async def generate_content_google_api(request: PodcastRequest, google_key: str) -> dict:
    """Generate content using Google AI API. This function will now raise exceptions on failure."""
    # Check if we have research paper content to analyze
    if request.paper_content and request.paper_title:
        print(f"🔬 Processing research paper with Google AI API: {request.paper_title[:50]}...")
        
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
        return await generate_podcast_from_analysis(paper, analysis, request, google_key)
        
    else:
        # No paper provided - generate topic-based research content
        print(f"📚 Generating research-driven content for topic: {request.topic}")
        return await generate_topic_research_content(request, google_key)

async def generate_podcast_from_analysis(paper: ResearchPaper, analysis: PaperAnalysis, request: PodcastRequest, api_key: str) -> dict:
    """Generate character-driven podcast content from research paper analysis"""
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

**Follow Copernicus AI for more cutting-edge science discussions and research explorations.**
"""
    
    try:
        print(f"🎙️ Generating podcast script from research analysis...")
        response_obj = client.models.generate_content(
            model='models/gemini-2.5-flash',
            contents=prompt
        )
        
        if response_obj and response_obj.text:
            content = _extract_json_from_response(response_obj.text)
            print(f"✅ Research-driven podcast content generated successfully")
            return content
        else:
            raise Exception("Empty response from Gemini")
            
    except Exception as e:
        print(f"❌ Error generating podcast from analysis: {e}")
        raise

async def generate_topic_research_content(request: PodcastRequest, api_key: str) -> dict:
    """Generate character-driven research content for a topic without specific paper"""
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

**Follow Copernicus AI for more cutting-edge science discussions and research explorations.**
"""
    
    try:
        print(f"🔄 Generating topic-based research content with Gemini...")
        response_obj = client.models.generate_content(
            model='models/gemini-2.5-flash',
            contents=prompt
        )
        
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
                        ref_section = desc_parts[1].split('##')[0]  # Get content until next section
                        validated_refs = validate_academic_references(ref_section)
                        content['description'] = desc_parts[0] + '## References\n' + validated_refs + '\n' + '##'.join(desc_parts[1].split('##')[1:])
            
            print(f"✅ Topic-based research content generated successfully")
            return content
        else:
            raise Exception("Empty response from Gemini")
            
    except Exception as e:
        print(f"❌ Error generating topic research content: {e}")
        raise

async def generate_podcast_from_analysis_vertex(paper: ResearchPaper, analysis: PaperAnalysis, request: PodcastRequest) -> dict:
    """Generate character-driven podcast content from research paper analysis using Vertex AI"""
    if not vertex_ai_model:
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

**Follow Copernicus AI for more cutting-edge science discussions and research explorations.**
"""
    
    try:
        print(f"🎙️ Generating podcast script from research analysis using Vertex AI...")
        response = vertex_ai_model.models.generate_content(
            model='models/gemini-2.5-flash',
            contents=prompt
        )
        
        if response and response.text:
            content = _extract_json_from_response(response.text)
            print(f"✅ Vertex AI research-driven podcast content generated successfully")
            return content
        else:
            raise Exception("Empty response from Vertex AI")
            
    except Exception as e:
        print(f"❌ Error generating podcast from analysis with Vertex AI: {e}")
        raise

async def generate_topic_research_content_vertex(request: PodcastRequest) -> dict:
    """Generate character-driven research content for a topic without specific paper using Vertex AI"""
    if not vertex_ai_model:
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

**Follow Copernicus AI for more cutting-edge science discussions and research explorations.**
"""
    
    try:
        print(f"🔄 Generating topic-based research content with Vertex AI Gemini...")
        response = vertex_ai_model.models.generate_content(
            model='models/gemini-2.5-flash',
            contents=prompt
        )
        
        if response and response.text:
            content = _extract_json_from_response(response.text)
            
            # Apply content fixes
            if 'script' in content:
                content['script'] = apply_content_fixes(content['script'], request.topic)
            
            # Content processing will be handled in the main validation area
            
            print(f"✅ Vertex AI topic-based podcast content generated successfully")
            return content
        else:
            raise Exception("Empty response from Vertex AI")
            
    except Exception as e:
        print(f"❌ Error generating topic research content with Vertex AI: {e}")
        raise

async def generate_audio_google_tts(script: str, job_id: str) -> str:
    """Generate audio using Google Cloud TTS"""
    try:
        from google.cloud import texttospeech
        
        print(f"🔄 Calling Google Cloud TTS for audio generation...")
        
        # Initialize the TTS client
        client = texttospeech.TextToSpeechClient()
        
        # Clean script for TTS
        clean_script = script.replace("**", "").replace("*", "").strip()
        
        # Check byte length (not character length) for Google TTS limit
        clean_script_bytes = clean_script.encode('utf-8')
        if len(clean_script_bytes) > 4800:  # Leave buffer for safety
            # Truncate by bytes, then decode back to string
            truncated_bytes = clean_script_bytes[:4800]
            # Ensure we don't cut in the middle of a UTF-8 character
            while len(truncated_bytes) > 0:
                try:
                    clean_script = truncated_bytes.decode('utf-8') + "..."
                    break
                except UnicodeDecodeError:
                    truncated_bytes = truncated_bytes[:-1]
        
        print(f"📝 Script length: {len(clean_script.encode('utf-8'))} bytes")
        
        # Set up the input text
        synthesis_input = texttospeech.SynthesisInput(text=clean_script)
        
        # Build the voice request - using Neural2 voice
        voice = texttospeech.VoiceSelectionParams(
            language_code="en-US",
            name="en-US-Neural2-F",  # Professional female voice
            ssml_gender=texttospeech.SsmlVoiceGender.FEMALE
        )
        
        # Select the type of audio file
        audio_config = texttospeech.AudioConfig(
            audio_encoding=texttospeech.AudioEncoding.MP3,
            speaking_rate=1.0,
            pitch=0.0
        )
        
        # Perform the text-to-speech request
        response = client.synthesize_speech(
            input=synthesis_input, 
            voice=voice, 
            audio_config=audio_config
        )
        
        # Save audio to local file
        audio_filename = f"/tmp/podcast_{job_id[:8]}.mp3"
        with open(audio_filename, "wb") as out:
            out.write(response.audio_content)
        
        print(f"✅ Google Cloud TTS audio generated: {audio_filename}")
        return f"file://{audio_filename}"
        
    except ImportError:
        print("❌ Google Cloud TTS library not installed - using fallback")
    except Exception as e:
        print(f"❌ Google Cloud TTS error: {e}")
    
    print("⚠️  Returning mock audio URL due to TTS issues")
    return f"https://storage.googleapis.com/regal-scholar-453620-r7-podcast-storage/audio/demo-{job_id[:8]}.mp3"

@retry_upload(max_retries=3, delay=2)
async def upload_description_to_gcs(description: str, canonical_filename: str) -> str:
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
        
        # Extract topic from description for better hashtag generation
        topic_match = re.search(r'^#\s*(.+)', description, re.MULTILINE)
        topic_for_hashtags = topic_match.group(1) if topic_match else ""
        
        # Generate context-aware hashtags based on description content
        hashtags = generate_relevant_hashtags(topic_for_hashtags, category, "", description)
        
        # Add hashtags section (don't add References header - it's already in description if needed)
        enhanced_description = f"{description}\n\n## Hashtags\n{hashtags}"
        
        # Ensure total description doesn't exceed 4000 characters (podcast description limit)
        MAX_DESCRIPTION_LENGTH = 4000
        if len(enhanced_description) > MAX_DESCRIPTION_LENGTH:
            print(f"⚠️ Description too long ({len(enhanced_description)} chars), trimming to {MAX_DESCRIPTION_LENGTH}...")
            
            # Try to preserve references by trimming the middle content first
            # Split into sections
            sections = enhanced_description.split('\n\n')
            references_sections = [s for s in sections if 'References' in s or s.strip().startswith('- ') or 'DOI:' in s or 'http' in s]
            other_sections = [s for s in sections if s not in references_sections]
            hashtag_sections = [s for s in sections if s.strip().startswith('#')]
            
            # Reserve space for references and hashtags (prioritize these)
            references_text = '\n\n'.join(references_sections)
            hashtags_text = '\n\n'.join(hashtag_sections)
            reserved_space = len(references_text) + len(hashtags_text) + 100  # 100 char buffer
            
            # Trim other sections to fit
            available_space = MAX_DESCRIPTION_LENGTH - reserved_space
            trimmed_other = []
            current_length = 0
            
            for section in other_sections:
                if current_length + len(section) + 2 < available_space:  # +2 for \n\n
                    trimmed_other.append(section)
                    current_length += len(section) + 2
                elif current_length < available_space:
                    # Add partial section
                    remaining = available_space - current_length - 20  # -20 for "..."
                    if remaining > 50:  # Only add if meaningful
                        trimmed_other.append(section[:remaining] + "...")
                    break
            
            # Rebuild description with full references and hashtags
            enhanced_description = '\n\n'.join(trimmed_other + references_sections + hashtag_sections)
            
            print(f"✅ Trimmed description to {len(enhanced_description)} chars, preserving full references")
        
        # Create description filename
        description_filename = f"{canonical_filename}.md"
        blob = bucket.blob(f"descriptions/{description_filename}")
        
        # Upload enhanced description as markdown
        blob.upload_from_string(enhanced_description, content_type="text/markdown")
        blob.make_public()
        
        # Return public URL
        public_url = f"https://storage.googleapis.com/regal-scholar-453620-r7-podcast-storage/descriptions/{description_filename}"
        print(f"📝 Enhanced description with hashtags uploaded to GCS: {public_url}")
        return public_url
        
    except Exception as e:
        print(f"❌ Error uploading description to GCS: {e}")
        return None

@retry_upload(max_retries=3, delay=2)
async def generate_and_upload_transcript(script: str, canonical_filename: str) -> str:
    """Generate and upload transcript to GCS transcripts folder"""
    try:
        from google.cloud import storage
        import re
        
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
                # Handle non-speaker lines (descriptions, etc.)
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
        print(f"📄 Transcript uploaded to GCS: {public_url}")
        return public_url
        
    except Exception as e:
        print(f"❌ Error generating/uploading transcript: {e}")
        return None

async def get_openai_api_key_from_secret_manager() -> str:
    """Get OpenAI API key from Secret Manager"""
    try:
        from google.cloud import secretmanager
        client = secretmanager.SecretManagerServiceClient()
        name = f"projects/{GCP_PROJECT_ID}/secrets/openai-api-key/versions/latest"
        response = client.access_secret_version(request={"name": name})
        return response.payload.data.decode("UTF-8").strip()
    except Exception as e:
        print(f"⚠️ Could not get OpenAI API key from Secret Manager: {e}")
        return os.getenv("OPENAI_API_KEY", "")

async def generate_fallback_thumbnail(canonical_filename: str, topic: str) -> str:
    """Generate fallback thumbnail when DALL-E is not available"""
    try:
        from PIL import Image, ImageDraw, ImageFilter
        from google.cloud import storage
        import random
        import math
        import io
        
        print(f"🎨 Generating fallback thumbnail for {canonical_filename}")
        
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
        bucket = storage_client.bucket("regal-scholar-453620-r7-podcast-storage")
        
        # Save image to bytes
        img_bytes = io.BytesIO()
        img.save(img_bytes, format='JPEG', quality=95)
        img_bytes.seek(0)
        
        # Upload to GCS
        thumbnail_filename = f"{canonical_filename}-fallback-thumb.jpg"
        blob = bucket.blob(f"thumbnails/{thumbnail_filename}")
        blob.upload_from_file(img_bytes, content_type="image/jpeg")
        blob.make_public()
        
        public_url = f"https://storage.googleapis.com/regal-scholar-453620-r7-podcast-storage/thumbnails/{thumbnail_filename}"
        print(f"🖼️ Fallback thumbnail uploaded: {public_url}")
        return public_url
        
    except Exception as e:
        print(f"❌ Error generating fallback thumbnail: {e}")
        # Return a default thumbnail URL
        return "https://storage.googleapis.com/regal-scholar-453620-r7-podcast-storage/images/copernicus-original-portrait.jpg"

@retry_upload(max_retries=3, delay=2)
async def generate_and_upload_thumbnail(title: str, topic: str, canonical_filename: str) -> str:
    """Generate AI thumbnail using DALL-E 3 with 1792x1792 dimensions for podcast platforms"""
    try:
        import requests
        from google.cloud import storage
        import io
        
        # Initialize GCS client
        storage_client = storage.Client()
        bucket = storage_client.bucket("regal-scholar-453620-r7-podcast-storage")
        
        # Get OpenAI API key from Secret Manager for DALL-E
        openai_api_key = await get_openai_api_key_from_secret_manager()
        if not openai_api_key:
            print("❌ No OpenAI API key available for DALL-E thumbnail generation")
            return await generate_fallback_thumbnail(canonical_filename, topic)
        
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
        print(f"🎨 Generating DALL-E 3 thumbnail for {canonical_filename}")
        
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
                
                public_url = f"https://storage.googleapis.com/regal-scholar-453620-r7-podcast-storage/thumbnails/{thumbnail_filename}"
                print(f"🖼️ DALL-E thumbnail uploaded: {public_url}")
                return public_url
            else:
                print(f"❌ Failed to download DALL-E image: {img_response.status_code}")
                return await generate_fallback_thumbnail(canonical_filename, topic)
        else:
            print(f"❌ DALL-E API error: {response.status_code} - {response.text}")
            return await generate_fallback_thumbnail(canonical_filename, topic)

    except Exception as e:
        print(f"❌ Error generating/uploading thumbnail: {e}")
        return await generate_fallback_thumbnail(canonical_filename, topic)

async def determine_canonical_filename(topic: str, title: str, category: str = None, format_type: str = "feature") -> str:
    """Determine canonical filename based on topic category, format type, and next available episode number"""
    
    # Debug: Log the input parameters
    print(f"🔍 DEBUG: determine_canonical_filename called with:")
    print(f"🔍 DEBUG:   topic = '{topic}'")
    print(f"🔍 DEBUG:   title = '{title}'")
    print(f"🔍 DEBUG:   category = '{category}'")
    print(f"🔍 DEBUG:   format_type = '{format_type}'")
    
    try:
        import requests
        import csv
        import io
        
        # Query Firestore for highest episode numbers by category to avoid overwrites
        category_episodes = {
            "bio": 250007,       # Start from current max
            "chem": 0, 
            "compsci": 0,
            "math": 0,
            "phys": 0
        }
        
        try:
            # Query all completed podcasts from Firestore
            podcasts_ref = db.collection('podcast_jobs').where('status', '==', 'completed').stream()
            
            for podcast_doc in podcasts_ref:
                podcast_data = podcast_doc.to_dict()
                result = podcast_data.get('result', {})
                audio_url = result.get('audio_url', '')
                
                # Extract filename from audio URL
                if 'ever-' in audio_url:
                    filename = audio_url.split('/')[-1].replace('.mp3', '')
                    parts = filename.split('-')
                    if len(parts) >= 3:
                        cat = parts[1]
                        try:
                            episode_num = int(parts[2])
                            if cat in category_episodes:
                                category_episodes[cat] = max(category_episodes[cat], episode_num)
                        except ValueError:
                            continue
            
            print(f"📊 Current max episodes by category: {category_episodes}")
            
        except Exception as e:
            print(f"⚠️ Could not query Firestore for episode numbers, using defaults: {e}")
        
        # Use the category from the request instead of re-classifying
        # Map the request category to the canonical format
        category_mapping = {
            "Physics": "phys",
            "Computer Science": "compsci", 
            "Biology": "bio",
            "Chemistry": "chem",
            "Mathematics": "math",
            "Engineering": "eng",
            "Medicine": "med",
            "Psychology": "psych"
        }
        
        # Use the category from the request directly
        if category and category in category_mapping:
            request_category = category_mapping[category]
        else:
            # Direct mapping from common categories
            if "Physics" in str(category):
                request_category = "phys"
            elif "Computer Science" in str(category):
                request_category = "compsci"
            elif "Biology" in str(category):
                request_category = "bio"
            elif "Chemistry" in str(category):
                request_category = "chem"
            elif "Mathematics" in str(category):
                request_category = "math"
            else:
                request_category = "phys"  # Default to physics
        
        # Get the next episode number for this category
        next_episode = category_episodes[request_category] + 1
        next_episode_str = str(next_episode).zfill(5)  # Pad to 5 digits like 250032
        
        # Double-check we're not overwriting by checking GCS directly
        try:
            import requests
            gcs_list_url = f"https://storage.googleapis.com/storage/v1/b/regal-scholar-453620-r7-podcast-storage/o?prefix=audio/ever-{request_category}-{next_episode_str}"
            gcs_response = requests.get(gcs_list_url)
            if gcs_response.status_code == 200:
                gcs_data = gcs_response.json()
                if gcs_data.get('items'):
                    # File already exists, increment further
                    next_episode += 1
                    next_episode_str = str(next_episode).zfill(5)
                    print(f"⚠️ File already exists, incrementing to {next_episode_str}")
        except Exception as e:
            print(f"⚠️ Could not verify GCS for {next_episode_str}: {e}")
        
        # Generate filename based on format type
        if format_type == "news":
            # News format: news-{category}-{date}-{serial_number}
            from datetime import datetime
            date_str = datetime.now().strftime("%Y%m%d")
            
            # Check for existing news files with same date and category to determine serial number
            try:
                import requests
                gcs_list_url = f"https://storage.googleapis.com/storage/v1/b/regal-scholar-453620-r7-podcast-storage/o?prefix=audio/news-{request_category}-{date_str}"
                gcs_response = requests.get(gcs_list_url)
                if gcs_response.status_code == 200:
                    gcs_data = gcs_response.json()
                    existing_files = gcs_data.get('items', [])
                    
                    # Count existing files for this date/category
                    serial_number = len(existing_files) + 1
                    serial_str = str(serial_number).zfill(4)  # Pad to 4 digits (0001, 0002, etc.)
                    
                    canonical_filename = f"news-{request_category}-{date_str}-{serial_str}"
                    print(f"🎯 Determined NEWS filename: {canonical_filename} (category: {request_category}, date: {date_str}, serial: {serial_str})")
                else:
                    # Fallback if GCS check fails
                    canonical_filename = f"news-{request_category}-{date_str}-0001"
                    print(f"🎯 Determined NEWS filename (fallback): {canonical_filename}")
            except Exception as e:
                print(f"⚠️ Could not check GCS for news serial numbering: {e}")
                canonical_filename = f"news-{request_category}-{date_str}-0001"
                print(f"🎯 Determined NEWS filename (error fallback): {canonical_filename}")
        else:
            # Feature format: ever-{category}-{episode}
            canonical_filename = f"ever-{request_category}-{next_episode_str}"
            print(f"🎯 Determined FEATURE filename: {canonical_filename} (category: {request_category}, episode: {next_episode})")
        
        return canonical_filename
        
    except Exception as e:
        print(f"❌ Error determining canonical filename: {e}")
        # Fallback to timestamp-based naming
        from datetime import datetime
        timestamp = datetime.now().strftime("%y%m%d")
        return f"research-fallback-{timestamp}"

def create_fallback_content(subject: str, duration: str, difficulty: str) -> dict:
    """Fallback content when APIs are unavailable"""
    return {
        "title": f"Research Insights: {subject}",
        "script": f"""Welcome to this research podcast exploring {subject}.

Today we dive into the fascinating world of {subject}, examining current research developments and future implications.

This {difficulty}-level exploration covers fundamental principles, recent methodological advances, and practical applications in {subject}.

Key areas include the current research landscape, breakthrough discoveries, and the broader implications for science and society.

The field of {subject} continues to evolve rapidly, with new discoveries challenging our understanding and opening exciting possibilities.
"""
}

async def generate_content_from_research_context(
    request: PodcastRequest,
    research_context: PodcastResearchContext,
    google_key: str
) -> dict:
    """
    Generate 2-speaker podcast content from research context
    Uses the research integrator to create Copernicus-spirit content
    """
    print(f"📝 Generating 2-speaker content from {len(research_context.research_sources)} research sources")
    
    # Initialize research integrator
    research_integrator = PodcastResearchIntegrator(google_key)
    
    # Build comprehensive research-driven prompt
    prompt = research_integrator.build_2_speaker_research_prompt(
        research_context=research_context,
        duration=request.duration,
        format_type=request.format_type,
        additional_instructions=request.additional_instructions or ""
    )
    
    print(f"📤 Sending prompt to Vertex AI ({len(prompt)} characters)")
    
    # Call Vertex AI with the research-rich prompt
    if vertex_ai_model:
        print("🚀 Using Vertex AI Gemini (via google-genai client)")
        try:
            # Use gemini-2.0-flash-exp which is available in Vertex AI
            response = vertex_ai_model.models.generate_content(
                model='gemini-2.0-flash-exp',
                contents=prompt
            )
        except Exception as e:
            print(f"❌ Vertex AI generation failed: {e}")
            # Fall back to Google AI API
            print("🔄 Falling back to Google AI API...")
            try:
                import google.generativeai as genai
                genai.configure(api_key=google_key)
                model = genai.GenerativeModel('gemini-1.5-flash')
                response = model.generate_content(prompt)
            except Exception as fallback_error:
                print(f"❌ Google AI API also failed: {fallback_error}")
                raise Exception(f"Both Vertex AI and Google AI API failed. Vertex: {e}, Google: {fallback_error}")
        
        # Parse JSON response
        response_text = response.text
        print(f"📥 Received response ({len(response_text)} characters)")
        
        # Extract JSON from response
        import json
        import re
        
        # Try to extract JSON from markdown code blocks
        json_match = re.search(r'```json\s*(.*?)\s*```', response_text, re.DOTALL)
        if json_match:
            json_str = json_match.group(1)
        else:
            # Try to find JSON object directly
            json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
            if json_match:
                json_str = json_match.group(0)
            else:
                json_str = response_text
        
        try:
            content = json.loads(json_str)
        except json.JSONDecodeError as e:
            print(f"❌ JSON parse error: {e}")
            print(f"Response preview: {response_text[:500]}...")
            
            # Try to repair truncated JSON by finding the last complete field
            try:
                # Find the last complete quote before the error
                error_pos = e.pos if hasattr(e, 'pos') else len(json_str)
                truncated = json_str[:error_pos]
                
                # Try to close incomplete strings and objects
                # Count unclosed braces and quotes
                open_braces = truncated.count('{') - truncated.count('}')
                
                # Close the JSON properly
                repaired = truncated.rstrip(',') + ('}' * open_braces)
                
                print(f"🔧 Attempting to repair JSON...")
                content = json.loads(repaired)
                print(f"✅ JSON repair successful!")
                
            except Exception as repair_error:
                print(f"❌ JSON repair failed: {repair_error}")
                raise Exception(f"Failed to parse LLM response as JSON: {e}")
        
    else:
        # Fall back to Google AI API
        print("🔄 Using Google AI API")
        import google.genai as genai
        genai.configure(api_key=google_key)
        model = genai.GenerativeModel('gemini-pro')
        
        response = model.generate_content(prompt)
        response_text = response.text
        
        # Parse JSON (same as above)
        import json
        import re
        json_match = re.search(r'```json\s*(.*?)\s*```', response_text, re.DOTALL)
        if json_match:
            json_str = json_match.group(1)
        else:
            json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
            if json_match:
                json_str = json_match.group(0)
            else:
                json_str = response_text
        
        try:
            content = json.loads(json_str)
        except json.JSONDecodeError as e:
            raise Exception(f"Failed to parse LLM response as JSON: {e}")
    
    print(f"✅ Content generated successfully")
    print(f"   Title: {content.get('title', 'N/A')[:60]}...")
    print(f"   Script length: {len(content.get('script', ''))} characters")
    print(f"   Description length: {len(content.get('description', ''))} characters")
    
    # Add research metadata to content
    content['research_quality_score'] = research_context.research_quality_score
    content['research_sources_used'] = len(research_context.research_sources)
    content['paradigm_shifts'] = research_context.paradigm_shifts
    
    return content

async def run_podcast_generation_job(job_id: str, request: PodcastRequest, subscriber_id: Optional[str] = None):
    """Process research-driven podcast generation with comprehensive research integration"""
    from datetime import datetime
    
    # Comprehensive logging setup
    start_time = time.time()
    initial_memory = psutil.virtual_memory().percent
    
    print(f"🚀 Job {job_id}: Starting COPERNICUS RESEARCH-DRIVEN podcast generation pipeline")
    print(f"📊 Initial system state: Memory {initial_memory:.1f}%")
    print(f"🎯 Topic: {request.topic}")
    print(f"📋 Category: {request.category}, Format: {request.format_type}")
    print(f"⏱️ Target duration: {request.duration}")
    
    # Get subscriber email for notifications
    subscriber_email = "garywelz@gmail.com"  # Default fallback
    if subscriber_id and db:
        try:
            subscriber_doc = db.collection('subscribers').document(subscriber_id).get()
            if subscriber_doc.exists:
                subscriber_data = subscriber_doc.to_dict()
                subscriber_email = subscriber_data.get('email', subscriber_email)
                print(f"📧 Will send completion email to: {subscriber_email}")
        except Exception as e:
            print(f"⚠️ Could not get subscriber email: {e}")
            print(f"📧 Using default email: {subscriber_email}")
    
    if not db:
        print(f"❌ Firestore not available. Cannot update job {job_id}.")
        return

    job_ref = db.collection('podcast_jobs').document(job_id)
    
    try:
        # ═════════════════════════════════════════════════════════════════
        # 🔬 PHASE 1: COMPREHENSIVE RESEARCH (NEW - Copernicus Spirit!)
        # ═════════════════════════════════════════════════════════════════
        print(f"\n{'═'*70}")
        print(f"🔬 PHASE 1: COMPREHENSIVE RESEARCH DISCOVERY")
        print(f"{'═'*70}\n")
        
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
            
            print(f"\n✅ Research completed successfully!")
            print(f"   Quality Score: {research_context.research_quality_score:.1f}/10")
            print(f"   Sources: {len(research_context.research_sources)}")
            print(f"   Paradigm Shifts: {len(research_context.paradigm_shifts)}")
            
            # Store research metadata in job
            job_ref.update({
                'research_sources_count': len(research_context.research_sources),
                'research_quality_score': research_context.research_quality_score,
                'paradigm_shifts_count': len(research_context.paradigm_shifts),
                'updated_at': datetime.utcnow().isoformat()
            })
            
        except Exception as e:
            error_msg = str(e)
            print(f"\n❌ Research phase failed: {error_msg}")
            
            # Update job with failure
            job_ref.update({
                'status': 'failed',
                'error': f"Research failed: {error_msg}",
                'error_type': 'insufficient_research',
                'updated_at': datetime.utcnow().isoformat()
            })
            
            # Send failure email
            if email_service:
                await email_service.send_podcast_ready_email(
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
        print(f"\n{'═'*70}")
        print(f"🎙️ PHASE 2: GENERATING 2-SPEAKER PODCAST FROM RESEARCH")
        print(f"{'═'*70}\n")
        
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
                    generate_content_from_research_context(request, research_context, google_key),
                    timeout=600  # 10 minute timeout for content generation
                )
                
                content_memory_after = psutil.virtual_memory().percent
                structured_logger.info("Content generation completed successfully", 
                                      job_id=job_id,
                                      memory_before=content_memory_before,
                                      memory_after=content_memory_after,
                                      memory_delta=content_memory_after - content_memory_before,
                                      content_type=type(content).__name__,
                                      content_keys=list(content.keys()) if isinstance(content, dict) else None)
                
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
        print(f"\n{'═'*70}")
        print(f"✅ PHASE 3: VALIDATING CONTENT QUALITY")
        print(f"{'═'*70}\n")
        
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

**Follow Copernicus AI for more cutting-edge science discussions and research explorations.**"""
        
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
        print(f"✅ Job {job_id}: Content validation passed.")
        # --- End of Robust Content Validation ---       
        # Determine canonical filename based on topic category, format type, and next available episode number
        canonical_filename = await determine_canonical_filename(request.topic, content["title"], request.category, request.format_type)
        
        # Generate multi-voice audio with ElevenLabs and bumpers
        audio_start_time = time.time()
        audio_memory_before = psutil.virtual_memory().percent
        print(f"🎙️ Job {job_id}: Starting multi-voice ElevenLabs audio generation")
        print(f"📊 Memory before audio generation: {audio_memory_before:.1f}%")
        print(f"📝 Script length: {len(content['script'])} characters")
        print(f"📁 Canonical filename: {canonical_filename}")
        
        # Force deployment: 2025-01-21 13:45:00 UTC - Multi-voice audio generation enabled
        voice_service = ElevenLabsVoiceService()
        audio_url = await voice_service.generate_multi_voice_audio_with_bumpers(
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
        print(f"✅ Audio generation completed in {audio_generation_time:.2f}s")
        print(f"📊 Memory after audio generation: {audio_memory_after:.1f}% (Δ{audio_memory_after - audio_memory_before:+.1f}%)")
        print(f"🔗 Audio URL: {audio_url}")
        
        # Force garbage collection after audio generation
        gc.collect()
        gc_memory_after = psutil.virtual_memory().percent
        print(f"🗑️ Garbage collection completed. Memory: {gc_memory_after:.1f}%")
        
        # Generate and upload transcript to GCS
        transcript_start_time = time.time()
        print(f"📄 Job {job_id}: Generating and uploading transcript")
        print(f"📊 Memory before transcript: {psutil.virtual_memory().percent:.1f}%")
        transcript_url = await generate_and_upload_transcript(content["script"], canonical_filename)
        transcript_time = time.time() - transcript_start_time
        print(f"✅ Transcript completed in {transcript_time:.2f}s: {transcript_url}")
        
        # Upload description to GCS
        description_start_time = time.time()
        print(f"📝 Job {job_id}: Uploading episode description to GCS")
        print(f"📊 Memory before description: {psutil.virtual_memory().percent:.1f}%")
        description_url = await upload_description_to_gcs(content["description"], canonical_filename)
        description_time = time.time() - description_start_time
        print(f"✅ Description completed in {description_time:.2f}s: {description_url}")
        
        # Generate and upload thumbnail
        thumbnail_start_time = time.time()
        print(f"🖼️ Job {job_id}: Generating AI thumbnail")
        print(f"📊 Memory before thumbnail: {psutil.virtual_memory().percent:.1f}%")
        
        async with with_step("thumbnail_generation", job_id):
            thumbnail_url = await generate_and_upload_thumbnail(
                content["title"], 
                request.topic, 
                canonical_filename
            )
        
        thumbnail_time = time.time() - thumbnail_start_time
        print(f"✅ Thumbnail completed in {thumbnail_time:.2f}s: {thumbnail_url}")
        
        # Extract keywords from content for search/discovery
        keywords_indexed = []
        if 'keywords' in content:
            keywords_indexed = content['keywords']
        elif 'description' in content:
            # Extract from hashtags in description
            import re
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
        job_ref.update({
            'status': 'completed',
            'updated_at': datetime.utcnow().isoformat(),
            'result': {
                'title': content.get('title', 'Untitled Podcast'),
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
                'generated_at': datetime.utcnow().isoformat()
            },
            'metadata_extended': metadata_extended,
            'engagement_metrics': engagement_metrics
        })
        
        # Send email notification
        email_start_time = time.time()
        print(f"📧 Job {job_id}: Sending completion email notification")
        print(f"📊 Memory before email: {psutil.virtual_memory().percent:.1f}%")
        
        email_service = EmailService()
        await email_service.send_podcast_completion_email(
            recipient_email=subscriber_email,
            job_id=job_id,
            podcast_title=content.get('title', 'Untitled Podcast'),
            topic=request.topic,
            audio_url=audio_url,
            duration=request.duration,
            canonical_filename=canonical_filename
        )
        
        email_time = time.time() - email_start_time
        print(f"✅ Email notification sent in {email_time:.2f}s")
        
        # Final pipeline summary
        total_time = time.time() - start_time
        final_memory = psutil.virtual_memory().percent
        print(f"🎉 Job {job_id}: PIPELINE COMPLETED SUCCESSFULLY!")
        print(f"⏱️ Total processing time: {total_time:.2f}s")
        print(f"📊 Memory usage: {initial_memory:.1f}% → {final_memory:.1f}% (Δ{final_memory - initial_memory:+.1f}%)")
        print(f"📁 Final files generated:")
        print(f"   🎵 Audio: {audio_url}")
        print(f"   📄 Transcript: {transcript_url}")
        print(f"   📝 Description: {description_url}")
        print(f"   🖼️ Thumbnail: {thumbnail_url}")
        
    except Exception as e:
        job_ref.update({
            'status': 'failed',
            'error': str(e),
            'updated_at': datetime.utcnow().isoformat()
        })
        print(f"❌ Podcast generation failed for job {job_id}: {e}")
        
        # Send failure email notification
        try:
            email_service = EmailService()
            await email_service.send_podcast_failure_email(
                recipient_email="garywelz@gmail.com",
                job_id=job_id,
                topic=request.topic,
                error_message=str(e)
            )
        except Exception as email_error:
            print(f"❌ Failed to send failure email notification: {email_error}")

@app.post("/generate-podcast")
async def generate_podcast(request: PodcastRequest):
    job_id = str(uuid.uuid4())
    
    # Enhanced logging for research-driven requests
    paper_info = f" + Paper: {request.paper_title[:30]}..." if request.paper_content else ""
    print(f"📥 New research podcast request: {request.topic} ({request.duration}, {request.expertise_level}){paper_info}")
    
    if not db:
        raise HTTPException(status_code=503, detail="Firestore service is unavailable. Cannot create job.")

    job_data = {
        'job_id': job_id,
        'status': 'pending',
        'created_at': datetime.utcnow().isoformat(),
        'updated_at': datetime.utcnow().isoformat(),
        'request': request.model_dump(),
    }
    
    try:
        db.collection('podcast_jobs').document(job_id).set(job_data)
        print(f"✅ Job {job_id} created in Firestore for topic: {request.topic}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create job in Firestore: {e}")
    
    # Run podcast generation synchronously (not as background task)
    # This fixes the issue where background tasks don't execute in Cloud Run
    try:
        structured_logger.info("Starting synchronous podcast generation", 
                              job_id=job_id,
                              topic=request.topic)
        
        await run_podcast_generation_job(job_id, request, subscriber_id)
        
        # Get final status
        job_doc = db.collection('podcast_jobs').document(job_id).get()
        if job_doc.exists:
            job_data = job_doc.to_dict()
            return {
                "job_id": job_id, 
                "status": job_data.get('status', 'completed'),
                "result": job_data.get('result')
            }
        
        return {"job_id": job_id, "status": "completed"}
        
    except Exception as e:
        structured_logger.error("Podcast generation failed", 
                               job_id=job_id,
                               error=str(e))
        
        # Update job status to failed
        job_ref = db.collection('podcast_jobs').document(job_id)
        job_ref.update({
            'status': 'failed',
            'error': str(e),
            'updated_at': datetime.utcnow().isoformat()
        })
        
        raise HTTPException(status_code=500, detail=f"Podcast generation failed: {str(e)}")



@app.post("/debug/run-content")
async def debug_content_generation(request: PodcastRequest):
    """Debug endpoint to test content generation in isolation"""
    job_id = f"debug-{uuid.uuid4()}"
    
    structured_logger.info("Debug content generation started", 
                          job_id=job_id,
                          topic=request.topic,
                          category=request.category,
                          duration=request.duration)
    
    try:
        async with with_step("debug_content_generation", job_id, 
                           topic=request.topic, category=request.category):
            
            # Test content generation with timeout and detailed logging
            structured_logger.info("Calling generate_research_driven_content", 
                                  job_id=job_id)
            
            content = await asyncio.wait_for(
                generate_research_driven_content(request),
                timeout=300  # 5 minute timeout
            )
            
            structured_logger.info("Content generation completed", 
                                  job_id=job_id,
                                  content_keys=list(content.keys()) if isinstance(content, dict) else "not_dict",
                                  content_length=len(str(content)) if content else 0)
            
            return {
                "job_id": job_id,
                "status": "success",
                "content": content,
                "timestamp": datetime.utcnow().isoformat()
            }
            
    except asyncio.TimeoutError:
        structured_logger.error("Content generation timed out", 
                               job_id=job_id,
                               timeout_seconds=300)
        return {
            "job_id": job_id,
            "status": "timeout",
            "error": "Content generation timed out after 5 minutes",
            "timestamp": datetime.utcnow().isoformat()
        }
    except Exception as e:
        structured_logger.error("Content generation failed", 
                               job_id=job_id,
                               error=str(e),
                               error_type=type(e).__name__)
        return {
            "job_id": job_id,
            "status": "error",
            "error": str(e),
            "error_type": type(e).__name__,
            "timestamp": datetime.utcnow().isoformat()
        }

@app.post("/debug/watchdog")
async def debug_watchdog():
    """Watchdog endpoint to check for stuck jobs and mark them as failed"""
    try:
        if not db:
            return {"status": "error", "message": "Firestore not available"}
        
        # Find jobs stuck in generating_content for more than 15 minutes
        cutoff_time = datetime.utcnow() - timedelta(minutes=15)
        
        stuck_jobs = db.collection('podcast_jobs').where(
            'status', '==', 'generating_content'
        ).where(
            'updated_at', '<', cutoff_time.isoformat()
        ).get()
        
        results = []
        for job in stuck_jobs:
            job_id = job.id
            job_data = job.to_dict()
            
            structured_logger.warning("Found stuck job, marking as failed", 
                                     job_id=job_id,
                                     status=job_data.get('status'),
                                     updated_at=job_data.get('updated_at'))
            
            # Mark job as failed
            db.collection('podcast_jobs').document(job_id).update({
                'status': 'failed',
                'error': 'Job stuck in generating_content for more than 15 minutes - marked as failed by watchdog',
                'error_code': 'WATCHDOG_TIMEOUT',
                'updated_at': datetime.utcnow().isoformat()
            })
            
            results.append({
                "job_id": job_id,
                "previous_status": job_data.get('status'),
                "updated_at": job_data.get('updated_at'),
                "action": "marked_failed"
            })
        
        return {
            "status": "success",
            "stuck_jobs_found": len(results),
            "jobs": results,
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        structured_logger.error("Watchdog failed", error=str(e))
        return {"status": "error", "message": str(e)}

@app.get("/health")
async def health_check():
    """Health check endpoint for Cloud Run"""
    # Check ElevenLabs API key availability
    try:
        from elevenlabs_voice_service import ElevenLabsVoiceService
        voice_service = ElevenLabsVoiceService()
        elevenlabs_available = bool(voice_service.api_key)
    except Exception as e:
        print(f"❌ ElevenLabs check failed: {e}")
        elevenlabs_available = False

    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "service": "copernicus-podcast-api",
        "vertex_ai_available": VERTEX_AI_AVAILABLE,
        "google_api_key_available": bool(get_google_api_key()),
        "elevenlabs_available": elevenlabs_available
    }

@app.get("/test-frontend")
async def test_frontend():
    """Test endpoint for frontend connectivity"""
    return {
        "message": "Frontend connectivity test successful",
        "timestamp": datetime.utcnow().isoformat(),
        "backend_url": "https://copernicus-podcast-api-204731194849.us-central1.run.app"
    }

@app.get("/status/{job_id}")
async def get_job_status(job_id: str):
    if not db:
        raise HTTPException(status_code=503, detail="Firestore service is unavailable")

    try:
        job_ref = db.collection('podcast_jobs').document(job_id)
        job_doc = job_ref.get()

        if not job_doc.exists:
            raise HTTPException(status_code=404, detail=f"Job '{job_id}' not found in Firestore.")
        
        return job_doc.to_dict()
    except Exception as e:
        print(f"❌ Error fetching job {job_id} from Firestore: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve job status")

# ============================================================================
# SUBSCRIBER MANAGEMENT APIs
# ============================================================================

# Subscriber Data Models
class SubscriberRegistration(BaseModel):
    email: str
    name: str
    password: Optional[str] = None  # For email/password auth
    google_id: Optional[str] = None  # For Google OAuth
    subscription_tier: str = "free"  # free, premium, research
    
    # RSS Attribution fields (Phase 2.1)
    display_name: Optional[str] = None  # Public screen name (e.g., "QuantumPhysicist")
    initials: Optional[str] = None      # Abbreviation for attribution (e.g., "GW")
    show_attribution: bool = False      # Opt-in to show attribution on published podcasts

class SubscriberLogin(BaseModel):
    email: str
    password: Optional[str] = None
    google_id: Optional[str] = None

class PasswordResetRequest(BaseModel):
    email: str

class PasswordReset(BaseModel):
    email: str
    new_password: str

class SubscriberProfile(BaseModel):
    subscriber_id: str
    email: str
    name: str
    subscription_tier: str
    subscription_status: str = "active"
    created_at: str
    last_login: str
    podcasts_generated: int = 0
    podcasts_submitted_to_rss: int = 0
    
    # RSS Attribution fields
    display_name: Optional[str] = None
    initials: Optional[str] = None
    show_attribution: bool = False

class PodcastSubmission(BaseModel):
    podcast_id: str
    submit_to_rss: bool = False

# --- Phase 1 Enhanced Database Models ---

class UserPreferences(BaseModel):
    favorite_topics: List[str] = []
    preferred_expertise_levels: List[str] = []
    notification_settings: Dict[str, bool] = {
        "email_on_completion": True,
        "email_on_failure": False,
        "weekly_digest": False
    }

class UsageAnalytics(BaseModel):
    total_listens: int = 0
    favorite_categories: List[str] = []
    average_session_duration: float = 0.0
    last_activity: Optional[str] = None

class QualityScores(BaseModel):
    content_accuracy: float = 0.0
    audio_quality: float = 0.0
    user_rating: float = 0.0
    reference_quality: float = 0.0

class PodcastMetadataExtended(BaseModel):
    source_papers: List[str] = []  # Array of DOIs/URLs
    references_extracted: List[Dict[str, str]] = []  # Structured citations
    keywords_indexed: List[str] = []  # For search
    glmp_visualizations: List[str] = []  # Links to GLMP models
    quality_scores: QualityScores = QualityScores()

class EngagementMetrics(BaseModel):
    play_count: int = 0
    completion_rate: float = 0.0
    user_ratings: List[float] = []
    shares: int = 0
    feedback_comments: List[str] = []

class ResearchPaperPreprocessing(BaseModel):
    key_findings: List[str] = []
    llm_summary: str = ""
    entities_extracted: Dict[str, List[str]] = {
        "genes": [],
        "proteins": [],
        "equations": [],
        "methods": [],
        "organisms": []
    }
    processed_by_model: str = ""
    processed_at: str = ""

class ResearchPaperModel(BaseModel):
    paper_id: str
    doi: Optional[str] = None
    title: str
    authors: List[str] = []
    journal: Optional[str] = None
    publication_date: Optional[str] = None
    abstract: Optional[str] = None
    url: Optional[str] = None
    pdf_url: Optional[str] = None
    arxiv_id: Optional[str] = None
    discipline: str = "biology"  # biology|chemistry|physics|mathematics|computer_science
    keywords: List[str] = []
    preprocessing: ResearchPaperPreprocessing = ResearchPaperPreprocessing()
    used_in_podcasts: List[str] = []  # Array of podcast_ids
    citation_count: int = 0
    created_at: str = ""
    updated_at: str = ""

class PaperUploadRequest(BaseModel):
    doi: Optional[str] = None
    url: Optional[str] = None
    title: Optional[str] = None
    authors: Optional[List[str]] = None
    abstract: Optional[str] = None
    discipline: str = "biology"
    preprocess: bool = True  # Whether to run LLM preprocessing

class PaperQueryRequest(BaseModel):
    discipline: Optional[str] = None
    keywords: Optional[List[str]] = None
    min_citation_count: Optional[int] = None
    limit: int = 20

# Authentication helper functions
def generate_subscriber_id(email: str) -> str:
    """Generate a unique subscriber ID from email"""
    import hashlib
    # Use full SHA256 hash to avoid collisions
    return hashlib.sha256(email.encode()).hexdigest()

def get_subscriber_by_email(email: str):
    """Get subscriber by email, trying both old and new ID formats"""
    import hashlib
    if not db:
        return None
    
    # Try new format first (full hash)
    new_id = generate_subscriber_id(email)
    subscriber_doc = db.collection('subscribers').document(new_id).get()
    if subscriber_doc.exists:
        return subscriber_doc
    
    # Try old format (16 chars) for backward compatibility
    old_id = hashlib.sha256(email.encode()).hexdigest()[:16]
    subscriber_doc = db.collection('subscribers').document(old_id).get()
    if subscriber_doc.exists:
        return subscriber_doc
    
    return None

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify password (simple implementation - in production use proper hashing)"""
    # Hash the plain password and compare with stored hash
    return hash_password(plain_password) == hashed_password

def hash_password(password: str) -> str:
    """Hash password (simple implementation - in production use proper hashing)"""
    # For now, simple encoding - in production use bcrypt or similar
    return password.encode().hex()

# Subscriber Management Endpoints
@app.post("/api/subscribers/register")
async def register_subscriber(registration: SubscriberRegistration):
    """Register a new subscriber"""
    if not db:
        raise HTTPException(status_code=503, detail="Firestore service is unavailable")
    
    subscriber_id = generate_subscriber_id(registration.email)
    print(f"🔍 Generated subscriber_id for {registration.email}: {subscriber_id}")
    
    # Check if subscriber already exists
    try:
        existing_doc = db.collection('subscribers').document(subscriber_id).get()
        if existing_doc.exists:
            print(f"⚠️ Subscriber already exists with ID: {subscriber_id}")
            # Update existing subscriber with new password if provided
            existing_data = existing_doc.to_dict()
            if registration.password:
                existing_data['password_hash'] = hash_password(registration.password)
                existing_data['last_login'] = datetime.utcnow().isoformat()
                db.collection('subscribers').document(subscriber_id).update(existing_data)
                print(f"✅ Updated existing subscriber password: {registration.email}")
            
            return {
                "subscriber_id": subscriber_id,
                "email": registration.email,
                "name": existing_data.get('name', registration.name),
                "subscription_tier": existing_data.get('subscription_tier', 'free'),
                "message": "Existing subscriber updated"
            }
    except Exception as e:
        print(f"❌ Error checking existing subscriber: {e}")
        raise HTTPException(status_code=500, detail="Failed to check existing subscriber")
    
    # Create new subscriber
    subscriber_data = {
        'subscriber_id': subscriber_id,
        'email': registration.email,
        'name': registration.name,
        'subscription_tier': registration.subscription_tier,
        'subscription_status': 'active',
        'created_at': datetime.utcnow().isoformat(),
        'last_login': datetime.utcnow().isoformat(),
        'podcasts_generated': 0,
        'podcasts_submitted_to_rss': 0,
        'google_id': registration.google_id,
        'password_hash': hash_password(registration.password) if registration.password else None,
        
        # RSS Attribution fields (Phase 2.1)
        'display_name': registration.display_name,
        'initials': registration.initials,
        'show_attribution': registration.show_attribution
    }
    
    try:
        db.collection('subscribers').document(subscriber_id).set(subscriber_data)
        print(f"✅ New subscriber registered: {registration.email} (ID: {subscriber_id})")
        
        return {
            "subscriber_id": subscriber_id,
            "email": registration.email,
            "name": registration.name,
            "subscription_tier": registration.subscription_tier,
            "message": "Subscriber registered successfully"
        }
    except Exception as e:
        print(f"❌ Error registering subscriber: {e}")
        raise HTTPException(status_code=500, detail="Failed to register subscriber")

@app.post("/api/subscribers/login")
async def login_subscriber(login: SubscriberLogin):
    """Authenticate a subscriber"""
    if not db:
        raise HTTPException(status_code=503, detail="Firestore service is unavailable")
    
    print(f"🔍 Login attempt for {login.email}")
    
    try:
        subscriber_doc = get_subscriber_by_email(login.email)
        if not subscriber_doc:
            raise HTTPException(status_code=404, detail="Subscriber not found")
        
        # Get the actual document ID (could be old or new format)
        subscriber_id = subscriber_doc.id
        print(f"✅ Found subscriber with ID: {subscriber_id}")
        
        subscriber_data = subscriber_doc.to_dict()
        
        # Verify authentication method
        if login.google_id and subscriber_data.get('google_id') == login.google_id:
            # Google OAuth authentication
            pass  # Google ID matches
        elif login.password and subscriber_data.get('password_hash'):
            # Email/password authentication
            if not verify_password(login.password, subscriber_data['password_hash']):
                raise HTTPException(status_code=401, detail="Invalid password")
        else:
            raise HTTPException(status_code=401, detail="Invalid authentication method")
        
        # Update last login
        db.collection('subscribers').document(subscriber_id).update({
            'last_login': datetime.utcnow().isoformat()
        })
        
        print(f"✅ Subscriber login successful: {login.email}")
        
        return {
            "subscriber_id": subscriber_id,
            "email": subscriber_data['email'],
            "name": subscriber_data['name'],
            "subscription_tier": subscriber_data['subscription_tier'],
            "message": "Login successful"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Error during login: {e}")
        raise HTTPException(status_code=500, detail="Login failed")

@app.get("/api/subscribers/profile/{subscriber_id}")
async def get_subscriber_profile(subscriber_id: str):
    """Get subscriber profile information"""
    if not db:
        raise HTTPException(status_code=503, detail="Firestore service is unavailable")
    
    try:
        subscriber_doc = db.collection('subscribers').document(subscriber_id).get()
        if not subscriber_doc.exists:
            raise HTTPException(status_code=404, detail="Subscriber not found")
        
        subscriber_data = subscriber_doc.to_dict()
        
        # Remove sensitive data
        subscriber_data.pop('password_hash', None)
        
        return subscriber_data
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Error fetching subscriber profile: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch profile")

class SubscriberProfileUpdate(BaseModel):
    name: Optional[str] = None
    display_name: Optional[str] = None
    initials: Optional[str] = None
    show_attribution: Optional[bool] = None

@app.put("/api/subscribers/profile/{subscriber_id}")
async def update_subscriber_profile(subscriber_id: str, updates: SubscriberProfileUpdate):
    """Update subscriber profile information"""
    if not db:
        raise HTTPException(status_code=503, detail="Firestore service is unavailable")
    
    try:
        subscriber_doc = db.collection('subscribers').document(subscriber_id).get()
        if not subscriber_doc.exists:
            raise HTTPException(status_code=404, detail="Subscriber not found")
        
        # Build update dictionary only with provided fields
        update_data = {}
        if updates.name is not None:
            update_data['name'] = updates.name
        if updates.display_name is not None:
            update_data['display_name'] = updates.display_name
        if updates.initials is not None:
            update_data['initials'] = updates.initials
        if updates.show_attribution is not None:
            update_data['show_attribution'] = updates.show_attribution
        
        if not update_data:
            raise HTTPException(status_code=400, detail="No fields to update")
        
        # Update the document
        db.collection('subscribers').document(subscriber_id).update(update_data)
        
        print(f"✅ Updated subscriber profile: {subscriber_id}")
        
        # Return updated data
        updated_doc = db.collection('subscribers').document(subscriber_id).get()
        updated_data = updated_doc.to_dict()
        updated_data.pop('password_hash', None)
        
        return updated_data
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Error updating subscriber profile: {e}")
        raise HTTPException(status_code=500, detail="Failed to update profile")

@app.get("/api/subscribers/podcasts/{subscriber_id}")
async def get_subscriber_podcasts(subscriber_id: str):
    """Get all podcasts generated by a subscriber"""
    if not db:
        raise HTTPException(status_code=503, detail="Firestore service is unavailable")
    
    try:
        # Query podcast_jobs collection for this subscriber
        podcasts_query = db.collection('podcast_jobs').where('subscriber_id', '==', subscriber_id).order_by('created_at', direction=firestore.Query.DESCENDING)
        podcasts = podcasts_query.stream()
        
        podcast_list = []
        for podcast in podcasts:
            podcast_data = podcast.to_dict()
            # Add podcast ID from document ID
            podcast_data['podcast_id'] = podcast.id
            podcast_list.append(podcast_data)
        
        print(f"✅ Found {len(podcast_list)} podcasts for subscriber {subscriber_id}")
        
        return {
            "subscriber_id": subscriber_id,
            "podcasts": podcast_list,
            "total_count": len(podcast_list)
        }
        
    except Exception as e:
        print(f"❌ Error fetching subscriber podcasts: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch podcasts")

@app.get("/api/public/podcasts")
async def get_public_podcasts(category: Optional[str] = None, limit: int = 100):
    """Get all published podcasts (submitted to RSS) - Public API"""
    if not db:
        raise HTTPException(status_code=503, detail="Firestore service is unavailable")
    
    try:
        # Query for podcasts submitted to RSS
        query = db.collection('podcast_jobs').where('submitted_to_rss', '==', True).order_by('created_at', direction=firestore.Query.DESCENDING)
        
        if category:
            query = query.where('request.category', '==', category)
        
        podcasts_query = query.limit(limit)
        podcasts = podcasts_query.stream()
        
        podcast_list = []
        for podcast in podcasts:
            podcast_data = podcast.to_dict()
            podcast_data['podcast_id'] = podcast.id
            
            # Extract relevant fields for public display
            public_podcast = {
                'podcast_id': podcast.id,
                'title': podcast_data.get('request', {}).get('topic', 'Untitled'),
                'category': podcast_data.get('request', {}).get('category', 'Unknown'),
                'expertise_level': podcast_data.get('request', {}).get('expertise_level', 'intermediate'),
                'duration': podcast_data.get('request', {}).get('duration', '5-10 minutes'),
                'created_at': podcast_data.get('created_at', ''),
                'status': podcast_data.get('status', 'unknown'),
                'creator_attribution': podcast_data.get('creator_attribution'),
                'result': podcast_data.get('result', {}),
            }
            podcast_list.append(public_podcast)
        
        print(f"✅ Found {len(podcast_list)} published podcasts")
        
        return {
            "podcasts": podcast_list,
            "total_count": len(podcast_list),
            "category_filter": category
        }
        
    except Exception as e:
        print(f"❌ Error fetching public podcasts: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch published podcasts")

@app.post("/api/subscribers/podcasts/submit-to-rss")
async def submit_podcast_to_rss(submission: PodcastSubmission):
    """Submit a podcast to the RSS feed"""
    if not db:
        raise HTTPException(status_code=503, detail="Firestore service is unavailable")
    
    try:
        # Get podcast details
        podcast_doc = db.collection('podcast_jobs').document(submission.podcast_id).get()
        if not podcast_doc.exists:
            raise HTTPException(status_code=404, detail="Podcast not found")
        
        podcast_data = podcast_doc.to_dict()
        subscriber_id = podcast_data.get('subscriber_id')
        
        if not subscriber_id:
            raise HTTPException(status_code=400, detail="Podcast not associated with a subscriber")
        
        # Update podcast to mark as submitted to RSS
        if submission.submit_to_rss:
            # Get subscriber attribution info if they opted in
            subscriber_doc = db.collection('subscribers').document(subscriber_id).get()
            creator_attribution = None
            
            if subscriber_doc.exists:
                subscriber_data = subscriber_doc.to_dict()
                
                # Check if user wants attribution
                if subscriber_data.get('show_attribution', False):
                    # Build attribution string
                    attribution_parts = []
                    
                    if subscriber_data.get('display_name'):
                        attribution_parts.append(subscriber_data['display_name'])
                    elif subscriber_data.get('initials'):
                        attribution_parts.append(subscriber_data['initials'])
                    
                    if attribution_parts:
                        creator_attribution = attribution_parts[0]
                
                # Update subscriber's RSS submission count
                new_count = subscriber_data.get('podcasts_submitted_to_rss', 0) + 1
                db.collection('subscribers').document(subscriber_id).update({
                    'podcasts_submitted_to_rss': new_count
                })
            
            # Update podcast with RSS info and attribution
            update_data = {
                'submitted_to_rss': True,
                'rss_submitted_at': datetime.utcnow().isoformat()
            }
            
            if creator_attribution:
                update_data['creator_attribution'] = creator_attribution
            
            db.collection('podcast_jobs').document(submission.podcast_id).update(update_data)
            
            print(f"✅ Podcast {submission.podcast_id} submitted to RSS feed" + 
                  (f" with attribution: {creator_attribution}" if creator_attribution else " (no attribution)"))
            
            return {
                "podcast_id": submission.podcast_id,
                "submitted_to_rss": True,
                "creator_attribution": creator_attribution,
                "message": "Podcast successfully submitted to RSS feed"
            }
        else:
            # Remove from RSS feed
            db.collection('podcast_jobs').document(submission.podcast_id).update({
                'submitted_to_rss': False,
                'rss_removed_at': datetime.utcnow().isoformat()
            })
            
            print(f"✅ Podcast {submission.podcast_id} removed from RSS feed")
            
            return {
                "podcast_id": submission.podcast_id,
                "submitted_to_rss": False,
                "message": "Podcast removed from RSS feed"
            }
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Error submitting podcast to RSS: {e}")
        raise HTTPException(status_code=500, detail="Failed to submit podcast to RSS")

# Modify existing generate-podcast endpoint to support subscribers
@app.post("/generate-podcast-with-subscriber")
async def generate_podcast_with_subscriber(request: PodcastRequest, subscriber_id: Optional[str] = None):
    """Generate podcast with optional subscriber association"""
    job_id = str(uuid.uuid4())
    
    # Enhanced logging for research-driven requests
    paper_info = f" + Paper: {request.paper_title[:30]}..." if request.paper_content else ""
    subscriber_info = f" (Subscriber: {subscriber_id})" if subscriber_id else " (Anonymous)"
    print(f"📥 New research podcast request: {request.topic} ({request.duration}, {request.expertise_level}){paper_info}{subscriber_info}")
    
    if not db:
        raise HTTPException(status_code=503, detail="Firestore service is unavailable. Cannot create job.")

    job_data = {
        'job_id': job_id,
        'status': 'pending',
        'created_at': datetime.utcnow().isoformat(),
        'updated_at': datetime.utcnow().isoformat(),
        'request': request.model_dump(),
        'subscriber_id': subscriber_id,  # Associate with subscriber
        'submitted_to_rss': False,  # Default to not submitted
    }
    
    try:
        db.collection('podcast_jobs').document(job_id).set(job_data)
        print(f"✅ Job {job_id} created in Firestore for topic: {request.topic}")
        
        # Update subscriber's podcast count if they're logged in
        if subscriber_id:
            subscriber_doc = db.collection('subscribers').document(subscriber_id).get()
            if subscriber_doc.exists:
                subscriber_data = subscriber_doc.to_dict()
                new_count = subscriber_data.get('podcasts_generated', 0) + 1
                db.collection('subscribers').document(subscriber_id).update({
                    'podcasts_generated': new_count
                })
                print(f"✅ Updated subscriber {subscriber_id} podcast count to {new_count}")
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create job in Firestore: {e}")
    
    # Run the same podcast generation logic as the original endpoint
    try:
        structured_logger.info("Starting synchronous podcast generation with subscriber", 
                              job_id=job_id,
                              subscriber_id=subscriber_id,
                              topic=request.topic)
        
        await run_podcast_generation_job(job_id, request, subscriber_id)
        
        # Get final status
        job_doc = db.collection('podcast_jobs').document(job_id).get()
        if job_doc.exists:
            job_data = job_doc.to_dict()
            return {
                "job_id": job_id, 
                "status": job_data.get('status', 'completed'),
                "result": job_data.get('result'),
                "subscriber_id": subscriber_id
            }
        
        return {"job_id": job_id, "status": "completed", "subscriber_id": subscriber_id}
        
    except Exception as e:
        structured_logger.error("Podcast generation failed", 
                              job_id=job_id,
                              subscriber_id=subscriber_id,
                              error=str(e))
        
        # Update job status to failed
        job_ref = db.collection('podcast_jobs').document(job_id)
        job_ref.update({
            'status': 'failed',
            'error': str(e),
            'updated_at': datetime.utcnow().isoformat()
        })
        
        raise HTTPException(status_code=500, detail=f"Podcast generation failed: {str(e)}")

@app.post("/api/subscribers/password-reset-request")
async def request_password_reset(reset_request: PasswordResetRequest):
    """Request a password reset for a subscriber"""
    if not db:
        raise HTTPException(status_code=503, detail="Firestore service is unavailable")
    
    subscriber_id = generate_subscriber_id(reset_request.email)
    
    try:
        subscriber_doc = db.collection('subscribers').document(subscriber_id).get()
        if not subscriber_doc.exists:
            # Don't reveal if email exists or not for security
            return {"message": "If the email exists, a password reset link has been sent"}
        
        subscriber_data = subscriber_doc.to_dict()
        
        # For now, just return success - in production, send email
        print(f"📧 Password reset requested for: {reset_request.email}")
        
        return {"message": "If the email exists, a password reset link has been sent"}
        
    except Exception as e:
        print(f"❌ Error processing password reset request: {e}")
        raise HTTPException(status_code=500, detail="Failed to process password reset request")

@app.post("/api/subscribers/password-reset")
async def reset_password(reset_data: PasswordReset):
    """Reset a subscriber's password"""
    if not db:
        raise HTTPException(status_code=503, detail="Firestore service is unavailable")
    
    subscriber_id = generate_subscriber_id(reset_data.email)
    
    try:
        subscriber_doc = db.collection('subscribers').document(subscriber_id).get()
        if not subscriber_doc.exists:
            raise HTTPException(status_code=404, detail="Subscriber not found")
        
        # Update password
        db.collection('subscribers').document(subscriber_id).update({
            'password_hash': hash_password(reset_data.new_password),
            'last_login': datetime.utcnow().isoformat()
        })
        
        print(f"✅ Password reset successful for: {reset_data.email}")
        
        return {"message": "Password reset successfully"}
        
    except Exception as e:
        print(f"❌ Error resetting password: {e}")
        raise HTTPException(status_code=500, detail="Failed to reset password")

@app.delete("/api/subscribers/podcasts/{podcast_id}")
async def delete_subscriber_podcast(podcast_id: str):
    """Delete a podcast generated by a subscriber"""
    if not db:
        raise HTTPException(status_code=503, detail="Firestore service is unavailable")
    
    try:
        # Get podcast details to verify it exists
        podcast_doc = db.collection('podcast_jobs').document(podcast_id).get()
        if not podcast_doc.exists:
            raise HTTPException(status_code=404, detail="Podcast not found")
        
        podcast_data = podcast_doc.to_dict()
        subscriber_id = podcast_data.get('subscriber_id')
        
        if not subscriber_id:
            raise HTTPException(status_code=400, detail="Podcast not associated with a subscriber")
        
        # Delete the podcast
        db.collection('podcast_jobs').document(podcast_id).delete()
        
        # Update subscriber's podcast count
        subscriber_doc = db.collection('subscribers').document(subscriber_id).get()
        if subscriber_doc.exists:
            subscriber_data = subscriber_doc.to_dict()
            current_count = subscriber_data.get('podcasts_generated', 0)
            if current_count > 0:
                db.collection('subscribers').document(subscriber_id).update({
                    'podcasts_generated': current_count - 1
                })
        
        print(f"✅ Podcast {podcast_id} deleted successfully")
        
        return {"message": "Podcast deleted successfully"}
        
    except Exception as e:
        print(f"❌ Error deleting podcast: {e}")
        raise HTTPException(status_code=500, detail="Failed to delete podcast")

# --- Research Papers API Endpoints (Phase 1) ---

async def preprocess_paper_with_llm(paper: ResearchPaperModel) -> ResearchPaperPreprocessing:
    """Preprocess a research paper using LLM to extract key information"""
    try:
        # Construct preprocessing prompt
        prompt = f"""Analyze this research paper and extract key information:

Title: {paper.title}
Authors: {', '.join(paper.authors)}
Abstract: {paper.abstract or 'Not provided'}
Discipline: {paper.discipline}

Please provide:
1. Key findings (3-5 main discoveries or contributions)
2. A concise summary (2-3 sentences)
3. Extracted entities:
   - Genes (if applicable)
   - Proteins (if applicable)
   - Mathematical equations/theorems (if applicable)
   - Methods/techniques used
   - Organisms studied (if applicable)

Format your response as JSON with keys: key_findings (array), summary (string), entities (object with arrays for genes, proteins, equations, methods, organisms)"""

        # Use available AI model
        model_used = "gemini-2.0-flash"
        response_text = ""
        
        if vertex_ai_model:
            response = vertex_ai_model.models.generate_content(
                model='models/gemini-2.0-flash',
                contents=prompt
            )
            response_text = response.text
        elif get_google_api_key():
            import google.generativeai as genai
            genai.configure(api_key=get_google_api_key())
            model = genai.GenerativeModel('gemini-2.0-flash')
            response = model.generate_content(prompt)
            response_text = response.text
        else:
            raise Exception("No AI model available for preprocessing")
        
        # Parse JSON response
        # Clean the response to extract JSON
        json_start = response_text.find('{')
        json_end = response_text.rfind('}') + 1
        if json_start != -1 and json_end > json_start:
            json_str = response_text[json_start:json_end]
            parsed_data = json.loads(json_str)
            
            return ResearchPaperPreprocessing(
                key_findings=parsed_data.get('key_findings', []),
                llm_summary=parsed_data.get('summary', ''),
                entities_extracted=parsed_data.get('entities', {}),
                processed_by_model=model_used,
                processed_at=datetime.utcnow().isoformat()
            )
        else:
            # Fallback if JSON parsing fails
            return ResearchPaperPreprocessing(
                key_findings=[],
                llm_summary=response_text[:500],  # First 500 chars
                entities_extracted={},
                processed_by_model=model_used,
                processed_at=datetime.utcnow().isoformat()
            )
            
    except Exception as e:
        print(f"❌ Error preprocessing paper: {e}")
        # Return empty preprocessing rather than failing
        return ResearchPaperPreprocessing()

@app.post("/api/papers/upload")
async def upload_research_paper(paper_request: PaperUploadRequest):
    """Upload and optionally preprocess a research paper"""
    if not db:
        raise HTTPException(status_code=503, detail="Firestore service is unavailable")
    
    try:
        # Generate paper ID
        paper_id = str(uuid.uuid4())
        
        # Create paper model
        paper = ResearchPaperModel(
            paper_id=paper_id,
            doi=paper_request.doi,
            title=paper_request.title or "Untitled",
            authors=paper_request.authors or [],
            abstract=paper_request.abstract,
            url=paper_request.url,
            discipline=paper_request.discipline,
            created_at=datetime.utcnow().isoformat(),
            updated_at=datetime.utcnow().isoformat()
        )
        
        # Preprocess if requested
        if paper_request.preprocess and paper.abstract:
            print(f"🔬 Preprocessing paper: {paper.title}")
            paper.preprocessing = await preprocess_paper_with_llm(paper)
        
        # Store in Firestore
        db.collection('research_papers').document(paper_id).set(paper.dict())
        
        print(f"✅ Paper uploaded: {paper_id}")
        
        return {"paper_id": paper_id, "message": "Paper uploaded successfully", "paper": paper.dict()}
        
    except Exception as e:
        print(f"❌ Error uploading paper: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to upload paper: {str(e)}")

@app.get("/api/papers/{paper_id}")
async def get_research_paper(paper_id: str):
    """Get a specific research paper by ID"""
    if not db:
        raise HTTPException(status_code=503, detail="Firestore service is unavailable")
    
    try:
        paper_doc = db.collection('research_papers').document(paper_id).get()
        if not paper_doc.exists:
            raise HTTPException(status_code=404, detail="Paper not found")
        
        return paper_doc.to_dict()
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Error fetching paper: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch paper")

@app.post("/api/papers/query")
async def query_research_papers(query: PaperQueryRequest):
    """Query research papers by discipline, keywords, etc."""
    if not db:
        raise HTTPException(status_code=503, detail="Firestore service is unavailable")
    
    try:
        # Build Firestore query
        papers_ref = db.collection('research_papers')
        
        # Apply filters
        if query.discipline:
            papers_ref = papers_ref.where('discipline', '==', query.discipline)
        
        if query.min_citation_count:
            papers_ref = papers_ref.where('citation_count', '>=', query.min_citation_count)
        
        # Limit results
        papers_ref = papers_ref.limit(query.limit)
        
        # Execute query
        papers = papers_ref.stream()
        results = []
        
        for paper in papers:
            paper_data = paper.to_dict()
            
            # Filter by keywords if provided
            if query.keywords:
                paper_keywords = set(paper_data.get('keywords', []))
                if not any(kw.lower() in ' '.join(paper_keywords).lower() for kw in query.keywords):
                    continue
            
            results.append(paper_data)
        
        return {"papers": results, "count": len(results)}
        
    except Exception as e:
        print(f"❌ Error querying papers: {e}")
        raise HTTPException(status_code=500, detail="Failed to query papers")

@app.post("/api/papers/{paper_id}/link-podcast/{podcast_id}")
async def link_paper_to_podcast(paper_id: str, podcast_id: str):
    """Link a research paper to a podcast"""
    if not db:
        raise HTTPException(status_code=503, detail="Firestore service is unavailable")
    
    try:
        # Update paper's used_in_podcasts array
        paper_ref = db.collection('research_papers').document(paper_id)
        paper_doc = paper_ref.get()
        
        if not paper_doc.exists:
            raise HTTPException(status_code=404, detail="Paper not found")
        
        paper_data = paper_doc.to_dict()
        used_in_podcasts = paper_data.get('used_in_podcasts', [])
        
        if podcast_id not in used_in_podcasts:
            used_in_podcasts.append(podcast_id)
            paper_ref.update({
                'used_in_podcasts': used_in_podcasts,
                'citation_count': len(used_in_podcasts),
                'updated_at': datetime.utcnow().isoformat()
            })
        
        # Update podcast's metadata_extended.source_papers
        podcast_ref = db.collection('podcast_jobs').document(podcast_id)
        podcast_doc = podcast_ref.get()
        
        if podcast_doc.exists:
            podcast_data = podcast_doc.to_dict()
            metadata = podcast_data.get('metadata_extended', {})
            source_papers = metadata.get('source_papers', [])
            
            if paper_id not in source_papers:
                source_papers.append(paper_id)
                metadata['source_papers'] = source_papers
                podcast_ref.update({'metadata_extended': metadata})
        
        print(f"✅ Linked paper {paper_id} to podcast {podcast_id}")
        
        return {"message": "Paper linked to podcast successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Error linking paper to podcast: {e}")
        raise HTTPException(status_code=500, detail="Failed to link paper to podcast")

# --- GLMP API Endpoints ---

@app.get("/api/glmp/processes")
async def list_glmp_processes():
    """List all available GLMP processes from Google Cloud Storage"""
    try:
        from google.cloud import storage
        
        bucket_name = "regal-scholar-453620-r7-podcast-storage"
        prefix = "glmp-v2/processes/"
        
        print(f"🔍 Listing GLMP processes from gs://{bucket_name}/{prefix}")
        
        # Initialize GCS client
        client = storage.Client()
        bucket = client.bucket(bucket_name)
        blobs = bucket.list_blobs(prefix=prefix)
        
        processes = []
        for blob in blobs:
            if blob.name.endswith('.json'):
                # Extract process name from file path
                process_name = blob.name.replace(prefix, '').replace('.json', '')
                processes.append({
                    'id': process_name,
                    'name': process_name.replace('-', ' ').title(),
                    'file_path': blob.name,
                    'url': f"gs://{bucket_name}/{blob.name}",
                    'size': blob.size,
                    'updated': blob.updated.isoformat() if blob.updated else None
                })
        
        print(f"✅ Found {len(processes)} GLMP processes")
        return {"processes": processes, "count": len(processes)}
        
    except Exception as e:
        print(f"❌ Error listing GLMP processes: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to list GLMP processes: {str(e)}")

@app.get("/api/glmp/processes/{process_id}")
async def get_glmp_process(process_id: str):
    """Get a specific GLMP process flowchart from Google Cloud Storage"""
    try:
        from google.cloud import storage
        
        bucket_name = "regal-scholar-453620-r7-podcast-storage"
        file_path = f"glmp-v2/processes/{process_id}.json"
        
        print(f"🔍 Fetching GLMP process: {process_id}")
        
        # Initialize GCS client
        client = storage.Client()
        bucket = client.bucket(bucket_name)
        blob = bucket.blob(file_path)
        
        if not blob.exists():
            print(f"❌ GLMP process not found: {process_id}")
            raise HTTPException(status_code=404, detail=f"GLMP process '{process_id}' not found")
        
        # Download and parse JSON
        json_content = blob.download_as_text()
        process_data = json.loads(json_content)
        
        print(f"✅ Loaded GLMP process: {process_id}")
        
        # Extract key information
        mermaid_code = process_data.get('mermaid_syntax', '') or process_data.get('mermaid', '') or process_data.get('flowchart', '')
        
        return {
            "process_id": process_id,
            "data": process_data,
            "mermaid_code": mermaid_code,
            "metadata": {
                "title": process_data.get('title', process_data.get('name', process_id.replace('-', ' ').title())),
                "description": process_data.get('description', ''),
                "category": process_data.get('category', ''),
                "version": process_data.get('version', '1.0'),
                "authors": process_data.get('authors', []),
                "references": process_data.get('references', [])
            }
        }
        
    except HTTPException:
        raise
    except json.JSONDecodeError as e:
        print(f"❌ Invalid JSON in GLMP process {process_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Invalid JSON format in process file: {str(e)}")
    except Exception as e:
        print(f"❌ Error fetching GLMP process {process_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to fetch GLMP process: {str(e)}")

@app.get("/api/glmp/processes/{process_id}/preview")
async def preview_glmp_process(process_id: str):
    """Get a lightweight preview of a GLMP process (metadata only)"""
    try:
        from google.cloud import storage
        
        bucket_name = "regal-scholar-453620-r7-podcast-storage"
        file_path = f"glmp-v2/processes/{process_id}.json"
        
        client = storage.Client()
        bucket = client.bucket(bucket_name)
        blob = bucket.blob(file_path)
        
        if not blob.exists():
            raise HTTPException(status_code=404, detail=f"GLMP process '{process_id}' not found")
        
        # Download and parse JSON
        json_content = blob.download_as_text()
        process_data = json.loads(json_content)
        
        # Return only metadata (no large mermaid code)
        return {
            "process_id": process_id,
            "title": process_data.get('title', process_data.get('name', process_id.replace('-', ' ').title())),
            "description": process_data.get('description', ''),
            "category": process_data.get('category', ''),
            "version": process_data.get('version', '1.0'),
            "has_mermaid": bool(process_data.get('mermaid_syntax') or process_data.get('mermaid') or process_data.get('flowchart')),
            "file_size": blob.size,
            "updated": blob.updated.isoformat() if blob.updated else None
        }
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Error previewing GLMP process {process_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to preview GLMP process: {str(e)}")

# Test endpoint
@app.get("/api/test")
async def test_endpoint():
    return {"message": "API is working", "glmp_endpoints": "available"}

if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8080))
    print(f"🚀 Starting Copernicus Podcast API with Vertex AI on port {port}")
    print(f"🤖 Vertex AI Gemini: {'✅ Available' if vertex_ai_model else '❌ Not Available'}")
    print(f"🔑 Google AI API Key: {'✅ Found' if get_google_api_key() else '❌ Missing'}")
    print(f"🎙️  Google Cloud TTS: Available via service account")
    print(f"🔧 AI Provider: {'Vertex AI' if vertex_ai_model else 'Google AI API' if get_google_api_key() else 'Fallback'}")
    if vertex_ai_model:
        print(f"📍 Vertex AI Project: {GCP_PROJECT_ID} ({VERTEX_AI_REGION})")
    uvicorn.run(app, host="0.0.0.0", port=port)
