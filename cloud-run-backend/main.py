from fastapi import FastAPI, HTTPException, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, List
import uuid
from datetime import datetime, timedelta, timezone
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
from email.utils import format_datetime, parsedate_to_datetime
from urllib.parse import urlparse
import xml.etree.ElementTree as ET
from xml.etree.ElementTree import Element, SubElement

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

# RSS Feed configuration
RSS_BUCKET_NAME = os.getenv("GCP_AUDIO_BUCKET", "regal-scholar-453620-r7-podcast-storage")
RSS_FEED_BLOB_NAME = os.getenv("COPERNICUS_RSS_FEED_BLOB", "feeds/copernicus-mvp-rss-feed.xml")
EPISODE_BASE_URL = os.getenv("COPERNICUS_EPISODE_BASE_URL", "https://copernicusai.fyi/episodes")
DEFAULT_ARTWORK_URL = os.getenv(
    "COPERNICUS_DEFAULT_ARTWORK",
    "https://storage.googleapis.com/regal-scholar-453620-r7-podcast-storage/images/copernicus-original-portrait-optimized.jpg"
)

CATEGORY_SLUG_TO_LABEL = {
    "bio": "Biology",
    "chem": "Chemistry",
    "compsci": "Computer Science",
    "math": "Mathematics",
    "phys": "Physics",
}

EPISODE_COLLECTION_NAME = os.getenv("COPERNICUS_EPISODE_COLLECTION", "episodes")

def _category_value_to_slug(category_value: Optional[str]) -> Optional[str]:
    """Normalize category input (slug or label) to canonical slug."""
    if not category_value:
        return None
    normalized = category_value.strip().lower()
    for slug, label in CATEGORY_SLUG_TO_LABEL.items():
        if normalized == slug or normalized == label.lower():
            return slug
    return None

RSS_NAMESPACES = {
    "itunes": "http://www.itunes.com/dtds/podcast-1.0.dtd",
    "atom": "http://www.w3.org/2005/Atom",
    "podcast": "https://podcastindex.org/namespace/1.0",
    "content": "http://purl.org/rss/1.0/modules/content/",
    "media": "http://search.yahoo.com/mrss/",
}

for prefix, uri in RSS_NAMESPACES.items():
    ET.register_namespace(prefix, uri)

LEGACY_DESCRIPTION_TAGLINES = {
    "Follow Copernicus AI for more cutting-edge science discussions and research explorations.",
    "**Follow Copernicus AI for more cutting-edge science discussions and research explorations.**",
}

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

"""
    
    try:
        print(f"🎙️ Generating podcast script from research analysis...")
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
                print(f"⚠️  Gemini 3.0 not available, falling back to 2.5...")
                model_name = 'models/gemini-2.5-flash'
                response_obj = client.models.generate_content(
                    model=model_name,
                    contents=prompt
                )
            else:
                raise
        
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

"""
    
    try:
        print(f"🔄 Generating topic-based research content with Gemini...")
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
                print(f"⚠️  Gemini 3.0 not available, falling back to 2.5...")
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

"""
    
    try:
        print(f"🎙️ Generating podcast script from research analysis using Vertex AI...")
        # Try Gemini 3.0 first, fallback to 2.5 if not available
        model_name = 'models/gemini-3.0-flash'
        try:
            response = vertex_ai_model.models.generate_content(
                model=model_name,
                contents=prompt
            )
        except Exception as e:
            error_msg = str(e).lower()
            if "not found" in error_msg or "does not exist" in error_msg:
                print(f"⚠️  Gemini 3.0 not available, falling back to 2.5...")
                model_name = 'models/gemini-2.5-flash'
                response = vertex_ai_model.models.generate_content(
                    model=model_name,
                    contents=prompt
                )
            else:
                raise
        
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

"""
    
    try:
        print(f"🔄 Generating topic-based research content with Vertex AI Gemini...")
        # Try Gemini 3.0 first, fallback to 2.5 if not available
        model_name = 'models/gemini-3.0-flash'
        try:
            response = vertex_ai_model.models.generate_content(
                model=model_name,
                contents=prompt
            )
        except Exception as e:
            error_msg = str(e).lower()
            if "not found" in error_msg or "does not exist" in error_msg:
                print(f"⚠️  Gemini 3.0 not available, falling back to 2.5...")
                model_name = 'models/gemini-2.5-flash'
                response = vertex_ai_model.models.generate_content(
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
        next_episode_str = str(next_episode).zfill(6)  # Pad to 6 digits like 250032
        
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
                    next_episode_str = str(next_episode).zfill(6)
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
    
    # Build comprehensive research-driven prompt with voice names
    prompt = research_integrator.build_2_speaker_research_prompt(
        research_context=research_context,
        duration=request.duration,
        format_type=request.format_type,
        additional_instructions=request.additional_instructions or "",
        host_voice_id=request.host_voice_id,
        expert_voice_id=request.expert_voice_id
    )
    
    print(f"📤 Sending prompt to Vertex AI ({len(prompt)} characters)")
    
    # Call Vertex AI with the research-rich prompt
    if vertex_ai_model:
        print("🚀 Using Vertex AI Gemini (via google-genai client)")
        try:
            from google.genai import types
            # Try Gemini 3.0 first, fallback to 2.0 if not available
            # CRITICAL: Increase max_output_tokens to prevent truncation
            model_name = 'models/gemini-3.0-flash'
            try:
                response = vertex_ai_model.models.generate_content(
                    model=model_name,
                    contents=prompt,
                    config=types.GenerateContentConfig(
                        max_output_tokens=8192,  # Increased from default 2048
                        temperature=0.8,
                        top_p=0.95
                    )
                )
            except Exception as e:
                error_msg = str(e).lower()
                if "not found" in error_msg or "does not exist" in error_msg:
                    print(f"⚠️  Gemini 3.0 not available, falling back to 2.0...")
                    model_name = 'models/gemini-2.0-flash-exp'
                    response = vertex_ai_model.models.generate_content(
                        model=model_name,
                        contents=prompt,
                        config=types.GenerateContentConfig(
                            max_output_tokens=8192,
                            temperature=0.8,
                            top_p=0.95
                        )
                    )
                else:
                    raise
        except Exception as e:
            print(f"❌ Vertex AI generation failed: {e}")
            # Fall back to Google AI API
            print("🔄 Falling back to Google AI API...")
            try:
                import google.generativeai as genai
                genai.configure(api_key=google_key)
                model = genai.GenerativeModel('gemini-1.5-flash')
                # Add generation config for fallback too
                generation_config = genai.types.GenerationConfig(
                    max_output_tokens=8192,
                    temperature=0.8,
                    top_p=0.95
                )
                response = model.generate_content(prompt, generation_config=generation_config)
            except Exception as fallback_error:
                print(f"❌ Google AI API also failed: {fallback_error}")
                raise Exception(f"Both Vertex AI and Google AI API failed. Vertex: {e}, Google: {fallback_error}")
        
        # Parse JSON response
        response_text = response.text
        print(f"📥 Received response ({len(response_text)} characters)")
        
        # DEBUG: Print first 1000 chars to see what LLM returned
        print(f"📄 Response preview:\n{response_text[:1000]}...")
        
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
        
        print(f"📊 Extracted JSON length: {len(json_str)} characters")
        
        try:
            content = json.loads(json_str)
        except json.JSONDecodeError as e:
            print(f"❌ JSON parse error: {e}")
            print(f"JSON string preview: {json_str[:800]}...")
            
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
    print(f"   Content keys: {list(content.keys())}")
    print(f"   Title: {content.get('title', 'N/A')[:60]}...")
    print(f"   Script length: {len(content.get('script', ''))} characters")
    print(f"   Description length: {len(content.get('description', ''))} characters")
    
    # CRITICAL: If description is missing, try to generate it from the content we have
    if not content.get('description'):
        print("⚠️ WARNING: LLM did not generate description field!")
        print("🔧 Attempting to create fallback description...")
        
        # Create a basic description from title and keywords
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
        # Add references from research sources
        for i, source in enumerate(research_context.research_sources[:5], 1):
            authors = ', '.join(source.authors[:2]) + (' et al.' if len(source.authors) > 2 else '')
            fallback_desc += f"- {authors}. {source.title}. {source.source}. "
            if source.doi:
                fallback_desc += f"DOI: {source.doi}"
            elif source.url:
                fallback_desc += f"Available: {source.url}"
            fallback_desc += "\n"
        
        content['description'] = fallback_desc
        print(f"✅ Created fallback description ({len(fallback_desc)} characters)")
    
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
    print(f"🎤 Voice IDs - Host: {request.host_voice_id or 'default'}, Expert: {request.expert_voice_id or 'default'}")
    
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
    request_snapshot = request.model_dump()
    
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
        print(f"🎙️ Initializing voice service with custom voice IDs:")
        print(f"   Host: {request.host_voice_id or 'XrExE9yKIg1WjnnlVkGX (Matilda - default)'}")
        print(f"   Expert: {request.expert_voice_id or 'pNInz6obpgDQGcFmaJgB (Adam - default)'}")
        
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
        generated_timestamp = datetime.utcnow().isoformat()
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
                'generated_at': generated_timestamp,
                'itunes_summary': content.get('itunes_summary'),
            },
            'metadata_extended': metadata_extended,
            'engagement_metrics': engagement_metrics
        })

        try:
            _upsert_episode_document(
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
                submitted_to_rss=False,
            )
        except Exception as catalog_error:
            print(f"⚠️ Failed to catalog episode {job_id}: {catalog_error}")
        
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
async def get_public_podcasts(category: Optional[str] = None, limit: int = 500):
    """Get all published podcasts (submitted to RSS) - Public API"""
    if not db:
        raise HTTPException(status_code=503, detail="Firestore service is unavailable")
    
    try:
        query = db.collection(EPISODE_COLLECTION_NAME).where('submitted_to_rss', '==', True)
        category_slug = _category_value_to_slug(category) if category else None
        if category_slug:
            query = query.where('category_slug', '==', category_slug)
        
        # Cap limit at 1000 to prevent excessive queries
        limit = min(limit, 1000)
        
        # Get episodes without ordering (Firestore requires index for filtered + ordered queries)
        # We'll sort in Python instead
        podcasts_query = query.limit(limit * 2)  # Get extra to account for missing fields
        podcasts = podcasts_query.stream()
        
        podcast_list = []
        for episode in podcasts:
            data = episode.to_dict() or {}
            data['episode_id'] = episode.id
            public_podcast = {
                'episode_id': episode.id,
                'title': data.get('title', 'Untitled'),
                'category': data.get('category', 'Unknown'),
                'category_slug': data.get('category_slug'),
                'expertise_level': data.get('request', {}).get('expertise_level', 'intermediate'),
                'duration': data.get('duration', '5-10 minutes'),
                'created_at': data.get('generated_at', data.get('created_at', '')),
                'status': 'published',
                'creator_attribution': data.get('creator_attribution'),
                'summary': data.get('summary'),
                'audio_url': data.get('audio_url'),
                'thumbnail_url': data.get('thumbnail_url'),
                'episode_link': data.get('episode_link'),
            }
            podcast_list.append(public_podcast)
        
        # Sort by generated_at in Python (descending - newest first)
        def get_sort_key(ep):
            gen_at = ep.get('created_at', '')
            # Handle datetime objects
            if isinstance(gen_at, datetime):
                return gen_at
            # Convert string dates to datetime for proper comparison
            if isinstance(gen_at, str):
                try:
                    # Try parsing common formats
                    for fmt in ['%Y-%m-%dT%H:%M:%S', '%a, %d %b %Y %H:%M:%S %Z', '%Y-%m-%d']:
                        try:
                            if 'T' in gen_at:
                                # ISO format with time
                                return datetime.fromisoformat(gen_at.replace('Z', '+00:00')[:19])
                            else:
                                # Try format string
                                return datetime.strptime(gen_at[:19], fmt)
                        except:
                            continue
                except:
                    pass
            # Fallback: use string comparison or very old date
            return datetime.min if isinstance(gen_at, str) and gen_at else datetime.min
        
        podcast_list.sort(key=get_sort_key, reverse=True)
        # Limit after sorting
        podcast_list = podcast_list[:limit]
        
        print(f"✅ Found {len(podcast_list)} published podcasts from episode catalog")
        
        return {
            "podcasts": podcast_list,
            "total_count": len(podcast_list),
            "category_filter": category_slug or category
        }
        
    except Exception as e:
        import traceback
        error_trace = traceback.format_exc()
        print(f"❌ Error fetching public podcasts: {e}")
        print(f"Error trace: {error_trace}")
        raise HTTPException(status_code=500, detail=f"Failed to fetch published podcasts: {str(e)}")

@app.get("/api/episodes")
async def list_episode_catalog(category: Optional[str] = None, submitted: Optional[bool] = None, limit: int = 500):
    """List episodes from the canonical catalog (includes drafts + published)."""
    if not db:
        raise HTTPException(status_code=503, detail="Firestore service is unavailable")
    try:
        # Cap limit at 1000 to prevent excessive queries
        limit = min(limit, 1000)
        query = db.collection(EPISODE_COLLECTION_NAME)
        if submitted is not None:
            query = query.where('submitted_to_rss', '==', submitted)
        category_slug = _category_value_to_slug(category) if category else None
        if category_slug:
            query = query.where('category_slug', '==', category_slug)
        episodes_query = query.order_by('generated_at', direction=firestore.Query.DESCENDING).limit(limit)
        episodes = []
        for doc in episodes_query.stream():
            payload = doc.to_dict() or {}
            payload['episode_id'] = doc.id
            episodes.append(payload)
        return {
            "episodes": episodes,
            "total_count": len(episodes),
            "category_filter": category_slug or category,
            "submitted_filter": submitted,
        }
    except Exception as e:
        print(f"❌ Error listing episode catalog: {e}")
        raise HTTPException(status_code=500, detail="Failed to list episodes")

@app.get("/api/episodes/search")
async def search_episodes(q: str, limit: int = 100, search_transcripts: bool = False):
    """Search episodes by title, description, or transcript.
    
    Args:
        q: Search query string
        limit: Maximum number of results (default 100, max 500)
        search_transcripts: If True, also search transcript content (slower, requires GCS access)
    """
    if not db:
        raise HTTPException(status_code=503, detail="Firestore service is unavailable")
    
    if not q or not q.strip():
        raise HTTPException(status_code=400, detail="Search query is required")
    
    try:
        search_terms = q.strip().lower().split()
        limit = min(limit, 500)
        
        # Fetch all episodes (or a large subset)
        # We'll filter in Python since Firestore doesn't have full-text search
        query = db.collection(EPISODE_COLLECTION_NAME)
        episodes_query = query.order_by('generated_at', direction=firestore.Query.DESCENDING).limit(1000)
        
        matching_episodes = []
        transcript_matches = set() if search_transcripts else None
        
        # First pass: search title and description
        for doc in episodes_query.stream():
            data = doc.to_dict() or {}
            
            # Extract searchable text
            title = (data.get('title') or '').lower()
            description = (data.get('description_markdown') or data.get('description_html') or '').lower()
            summary = (data.get('summary') or '').lower()
            
            # Strip HTML tags from description for better matching
            import re
            description_plain = re.sub(r'<[^>]+>', '', description)
            
            # Check if all search terms match
            matches = all(term in title or term in description_plain or term in summary for term in search_terms)
            
            if matches:
                payload = data.copy()
                payload['episode_id'] = doc.id
                
                # Ensure episode_link is set (construct if missing)
                if not payload.get('episode_link') and payload.get('slug'):
                    payload['episode_link'] = f"{EPISODE_BASE_URL}/{payload.get('slug')}"
                elif not payload.get('episode_link') and payload.get('episode_id'):
                    payload['episode_link'] = f"{EPISODE_BASE_URL}/{payload.get('episode_id')}"
                
                # Ensure audio_url is included (use audio_url field)
                if not payload.get('audio_url'):
                    # Try alternative field names
                    payload['audio_url'] = data.get('audioUrl') or data.get('audio_url') or ''
                
                # Ensure slug is always included for category detection
                if not payload.get('slug') and payload.get('episode_id'):
                    payload['slug'] = payload.get('episode_id')
                
                # Debug logging
                print(f"🔍 Search result: {payload.get('title', 'No title')} - Slug: {payload.get('slug')} - Audio URL: {bool(payload.get('audio_url'))} - Episode Link: {payload.get('episode_link')}")
                
                # Add match context for highlighting
                payload['match_score'] = (
                    sum(1 for term in search_terms if term in title) * 3 +
                    sum(1 for term in search_terms if term in description_plain) * 2 +
                    sum(1 for term in search_terms if term in summary) * 2
                )
                matching_episodes.append(payload)
                if search_transcripts and data.get('transcript_url'):
                    transcript_matches.add(doc.id)
        
        # Second pass: search transcripts if requested
        if search_transcripts and transcript_matches:
            from google.cloud import storage
            import re
            storage_client = storage.Client()
            bucket = storage_client.bucket(RSS_BUCKET_NAME)
            
            # Re-check episodes with transcripts
            for episode_id in list(transcript_matches):
                episode = next((e for e in matching_episodes if e.get('episode_id') == episode_id), None)
                if not episode:
                    continue
                
                transcript_url = episode.get('transcript_url')
                if not transcript_url:
                    continue
                
                try:
                    # Extract blob name from GCS URL
                    blob_name = transcript_url.replace('https://storage.googleapis.com/', '').split('/', 1)[1]
                    blob = bucket.blob(blob_name)
                    
                    if blob.exists():
                        transcript_content = blob.download_as_text()
                        transcript_lower = transcript_content.lower()
                        
                        # Check if all terms match in transcript
                        if all(term in transcript_lower for term in search_terms):
                            # Boost match score for transcript matches
                            episode['match_score'] = episode.get('match_score', 0) + 1
                            episode['transcript_match'] = True
                            
                            # Find first occurrence of search terms in transcript
                            first_match_position = len(transcript_content)  # Initialize to end
                            first_match_term = None
                            
                            # Find the earliest position where any search term appears
                            for term in search_terms:
                                pattern = re.compile(re.escape(term), re.IGNORECASE)
                                match = pattern.search(transcript_content)
                                if match and match.start() < first_match_position:
                                    first_match_position = match.start()
                                    first_match_term = term
                            
                            # Estimate timestamp based on position in transcript
                            # Average speaking rate: ~150 words per minute = 2.5 words per second
                            # We'll count words from the beginning to the match position
                            text_before_match = transcript_content[:first_match_position]
                            
                            # Clean text to count words accurately (remove markdown, speaker labels)
                            clean_text = re.sub(r'\*\*([^*]+)\*\*', r'\1', text_before_match)  # Remove bold
                            clean_text = re.sub(r'\*([^*]+)\*', r'\1', clean_text)  # Remove italic
                            clean_text = re.sub(r'#+\s*', '', clean_text)  # Remove headers
                            clean_text = re.sub(r'\[([^\]]+)\]\([^\)]+\)', r'\1', clean_text)  # Remove links
                            clean_text = re.sub(r'\*\*(HOST|EXPERT|QUESTIONER|CORRESPONDENT):\s*\*\*', '', clean_text, flags=re.IGNORECASE)  # Remove speaker labels
                            clean_text = re.sub(r'(HOST|EXPERT|QUESTIONER|CORRESPONDENT):\s*', '', clean_text, flags=re.IGNORECASE)  # Remove speaker labels
                            
                            # Count words
                            word_count = len(re.findall(r'\b\w+\b', clean_text))
                            
                            # Estimate timestamp (150 words/min = 2.5 words/sec, with buffer)
                            # Using 2.5 words/second as a conservative estimate
                            estimated_seconds = max(0, int(word_count / 2.5))
                            episode['transcript_timestamp'] = estimated_seconds
                            
                            # Extract snippet with context around first match
                            snippet_length = 250  # characters before and after match
                            start = max(0, first_match_position - snippet_length)
                            end = min(len(transcript_content), first_match_position + len(first_match_term) + snippet_length)
                            
                            snippet = transcript_content[start:end]
                            
                            # Clean up: remove markdown formatting for preview
                            snippet = re.sub(r'\*\*([^*]+)\*\*', r'\1', snippet)  # Remove bold
                            snippet = re.sub(r'\*([^*]+)\*', r'\1', snippet)  # Remove italic
                            snippet = re.sub(r'#+\s*', '', snippet)  # Remove headers
                            snippet = re.sub(r'\[([^\]]+)\]\([^\)]+\)', r'\1', snippet)  # Remove links
                            snippet = snippet.replace('\n\n', ' ').replace('\n', ' ').strip()
                            
                            # Add ellipsis if truncated
                            if start > 0:
                                snippet = '...' + snippet
                            if end < len(transcript_content):
                                snippet = snippet + '...'
                            
                            episode['transcript_snippet'] = snippet
                            
                except Exception as e:
                    print(f"⚠️ Could not search transcript for {episode_id}: {e}")
        
        # Sort by match score (highest first)
        matching_episodes.sort(key=lambda x: x.get('match_score', 0), reverse=True)
        
        # Limit results
        matching_episodes = matching_episodes[:limit]
        
        return {
            "query": q,
            "episodes": matching_episodes,
            "total_count": len(matching_episodes),
            "searched_transcripts": search_transcripts,
        }
    except Exception as e:
        print(f"❌ Error searching episodes: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail="Failed to search episodes")

@app.get("/api/episodes/{episode_id}")
async def get_episode_record(episode_id: str):
    """Fetch a single episode from the catalog."""
    if not db:
        raise HTTPException(status_code=503, detail="Firestore service is unavailable")
    try:
        doc = db.collection(EPISODE_COLLECTION_NAME).document(episode_id).get()
        if not doc.exists:
            raise HTTPException(status_code=404, detail="Episode not found")
        payload = doc.to_dict() or {}
        payload['episode_id'] = doc.id
        return payload
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Error fetching episode {episode_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to load episode")

@app.get("/api/admin/subscribers")
async def list_all_subscribers():
    """List all registered subscribers - Admin endpoint"""
    if not db:
        raise HTTPException(status_code=503, detail="Firestore service is unavailable")
    
    try:
        # Query all subscribers
        subscribers_ref = db.collection('subscribers')
        subscribers = subscribers_ref.stream()
        
        subscriber_list = []
        for sub in subscribers:
            data = sub.to_dict()
            
            # Format timestamps
            created_at = data.get('created_at', 'Unknown')
            last_login = data.get('last_login', 'Never')
            
            if hasattr(created_at, 'timestamp'):
                created_at = datetime.fromtimestamp(created_at.timestamp()).isoformat()
            if hasattr(last_login, 'timestamp'):
                last_login = datetime.fromtimestamp(last_login.timestamp()).isoformat()
            
            subscriber_info = {
                'email': data.get('email', 'N/A'),  # Get email from document data, not document ID
                'subscriber_id': sub.id,  # Document ID is the hashed subscriber_id
                'display_name': data.get('display_name', 'N/A'),
                'initials': data.get('initials', 'N/A'),
                'show_attribution': data.get('show_attribution', False),
                'created_at': str(created_at),
                'last_login': str(last_login),
                'podcast_count': data.get('podcasts_generated', 0)  # Use correct field name
            }
            
            subscriber_list.append(subscriber_info)
        
        print(f"✅ Listed {len(subscriber_list)} total subscribers")
        
        return {
            "subscribers": subscriber_list,
            "total_count": len(subscriber_list)
        }
        
    except Exception as e:
        print(f"❌ Error listing subscribers: {e}")
        raise HTTPException(status_code=500, detail="Failed to list subscribers")

@app.delete("/api/admin/subscribers/{subscriber_id}")
async def delete_subscriber(subscriber_id: str):
    """Delete a subscriber account - Admin endpoint"""
    if not db:
        raise HTTPException(status_code=503, detail="Firestore service is unavailable")
    
    try:
        # Check if subscriber exists
        subscriber_doc = db.collection('subscribers').document(subscriber_id).get()
        if not subscriber_doc.exists:
            raise HTTPException(status_code=404, detail="Subscriber not found")
        
        subscriber_data = subscriber_doc.to_dict()
        email = subscriber_data.get('email', 'Unknown')
        
        # Delete the subscriber
        db.collection('subscribers').document(subscriber_id).delete()
        
        print(f"✅ Deleted subscriber: {email} (ID: {subscriber_id})")
        
        return {
            "message": "Subscriber deleted successfully",
            "email": email,
            "subscriber_id": subscriber_id
        }
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Error deleting subscriber: {e}")
        raise HTTPException(status_code=500, detail="Failed to delete subscriber")

@app.post("/api/admin/episodes/backfill")
async def backfill_episode_catalog(limit: int = 200):
    """Backfill the episode catalog from existing completed podcast jobs."""
    if not db:
        raise HTTPException(status_code=503, detail="Firestore service is unavailable")
    try:
        import traceback
        # NOTE: Keep this query simple to avoid requiring composite indexes in Firestore.
        # We only need "completed" jobs for backfill; ordering is not important.
        jobs_query = (
            db.collection('podcast_jobs')
            .where('status', '==', 'completed')
            .limit(limit)
        )
        created = 0
        skipped_no_result = 0
        errors = []
        
        print(f"🔄 Starting backfill for up to {limit} completed jobs...")
        try:
            jobs_stream = jobs_query.stream()
        except Exception as query_error:
            error_msg = str(query_error)
            if "index" in error_msg.lower():
                print(f"❌ Firestore index required. Query: status == 'completed' (no ordering).")
                print(f"💡 Error: {error_msg}")
                raise HTTPException(
                    status_code=400,
                    detail=f"Firestore index required for query. This query should not need an index. Error: {error_msg}"
                )
            raise
        
        for job in jobs_stream:
            job_payload = job.to_dict() or {}
            if not job_payload.get('result'):
                skipped_no_result += 1
                continue
            try:
                _ensure_episode_document_from_job(job.id, job_payload)
                created += 1
                if created % 10 == 0:
                    print(f"✅ Processed {created} episodes so far...")
            except Exception as job_error:
                error_msg = f"Job {job.id}: {str(job_error)}"
                errors.append(error_msg)
                print(f"⚠️ {error_msg}")
                print(traceback.format_exc())
                # Continue processing other jobs even if one fails
        
        result = {
            "processed_jobs": created,
            "skipped_no_result": skipped_no_result,
            "errors": errors if errors else None,
            "limit": limit,
            "message": f"Episode catalog backfill completed: {created} episodes created, {skipped_no_result} skipped (no result data), {len(errors)} errors"
        }
        print(f"✅ Backfill complete: {result['message']}")
        return result
    except Exception as e:
        import traceback
        error_trace = traceback.format_exc()
        print(f"❌ Fatal error during episode backfill: {e}")
        print(error_trace)
        raise HTTPException(status_code=500, detail=f"Failed to backfill episodes: {str(e)}")

@app.post("/api/admin/episodes/sync-rss-status")
async def sync_rss_status():
    """Sync Firestore episode catalog with actual RSS feed contents.
    
    This reads the RSS feed XML and updates Firestore episodes to mark
    them as submitted_to_rss=true if their slug appears in the feed.
    """
    if not db:
        raise HTTPException(status_code=503, detail="Firestore service is unavailable")
    
    try:
        from google.cloud import storage
        import xml.etree.ElementTree as ET
        
        # Read RSS feed from GCS
        storage_client = storage.Client()
        bucket = storage_client.bucket(RSS_BUCKET_NAME)
        blob = bucket.blob(RSS_FEED_BLOB_NAME)
        
        if not blob.exists():
            raise HTTPException(status_code=404, detail="RSS feed file not found in storage")
        
        xml_bytes = blob.download_as_bytes()
        root = ET.fromstring(xml_bytes)
        
        # Extract all GUIDs (episode slugs) from RSS feed
        rss_guids = set()
        for guid_elem in root.findall(".//guid"):
            if guid_elem.text:
                rss_guids.add(guid_elem.text.strip())
        
        print(f"📡 Found {len(rss_guids)} episodes in RSS feed")
        
        # Update Firestore episodes
        episodes_collection = db.collection(EPISODE_COLLECTION_NAME)
        updated_count = 0
        not_found_in_rss = 0
        
        # Get all episodes from Firestore
        all_episodes = episodes_collection.stream()
        for episode_doc in all_episodes:
            episode_data = episode_doc.to_dict() or {}
            slug = episode_data.get("slug") or episode_data.get("episode_id") or episode_doc.id
            
            # Check if this episode is in the RSS feed
            is_in_rss = slug in rss_guids
            currently_marked = episode_data.get("submitted_to_rss", False)
            
            if is_in_rss and not currently_marked:
                # Update to mark as submitted
                episodes_collection.document(episode_doc.id).update({
                    "submitted_to_rss": True,
                    "visibility": "public",
                    "updated_at": datetime.now(timezone.utc).isoformat()
                })
                updated_count += 1
                print(f"✅ Marked {slug} as submitted_to_rss=True")
            elif not is_in_rss and currently_marked:
                # Update to mark as not submitted (in case it was removed from RSS)
                episodes_collection.document(episode_doc.id).update({
                    "submitted_to_rss": False,
                    "visibility": "private",
                    "updated_at": datetime.now(timezone.utc).isoformat()
                })
                not_found_in_rss += 1
                print(f"⚠️ Marked {slug} as submitted_to_rss=False (not in RSS feed)")
        
        result = {
            "rss_feed_episodes": len(rss_guids),
            "updated_to_submitted": updated_count,
            "updated_to_not_submitted": not_found_in_rss,
            "rss_guids": sorted(list(rss_guids)),
            "message": f"RSS sync complete: {updated_count} episodes marked as submitted, {not_found_in_rss} marked as not submitted"
        }
        print(f"✅ RSS sync complete: {result['message']}")
        return result
        
    except Exception as e:
        import traceback
        error_trace = traceback.format_exc()
        print(f"❌ Fatal error during RSS sync: {e}")
        print(error_trace)
        raise HTTPException(status_code=500, detail=f"Failed to sync RSS status: {str(e)}")

def _markdown_to_html(markdown_text: str) -> str:
    """Convert markdown to HTML, fallback to paragraph-wrapped text on error."""
    if not markdown_text:
        return ""
    try:
        import markdown  # type: ignore
        import re
        
        # Pre-process: Convert references section with asterisks to proper markdown lists
        # Find the References section and convert asterisk items to list items
        def fix_references_section(match):
            header = match.group(1)
            content = match.group(2)
            # Convert lines starting with "*   " to proper markdown list items
            lines = content.split('\n')
            fixed_lines = []
            in_list = False
            for line in lines:
                # Check if line starts with "*   " (asterisk with spaces)
                if re.match(r'^\*\s+', line):
                    if not in_list:
                        fixed_lines.append('')  # Add blank line before list starts
                        in_list = True
                    # Convert "*   " to "- " for markdown list
                    line = re.sub(r'^\*\s+', '- ', line)
                    fixed_lines.append(line)
                else:
                    if in_list and line.strip() == '':
                        in_list = False
                    fixed_lines.append(line)
            return header + '\n'.join(fixed_lines)
        
        # Find and fix references section
        markdown_text = re.sub(
            r'(## References\n)(.*?)(?=\n##|\n\nHashtags|\Z)',
            fix_references_section,
            markdown_text,
            flags=re.DOTALL
        )
        
        html = markdown.markdown(markdown_text, extensions=["extra", "sane_lists"])
        
        # Post-process: Add CSS styling for lists to ensure proper spacing
        # Wrap references list in a div with proper spacing
        html = re.sub(
            r'(<h2[^>]*>## References</h2>)(.*?)(</ul>)',
            r'\1<div style="margin-top: 1rem; margin-bottom: 1.5rem;"><ul style="list-style-type: disc; padding-left: 2rem; line-height: 1.8; margin-top: 0.5rem;">\2\3</div>',
            html,
            flags=re.DOTALL
        )
        # Ensure all list items have proper spacing
        html = re.sub(r'<li>', r'<li style="margin-bottom: 0.75rem;">', html)
        # Ensure paragraphs have proper spacing
        html = re.sub(r'<p>', r'<p style="margin-bottom: 1rem; line-height: 1.7;">', html)
        return html
    except Exception:
        paragraphs = [p.strip() for p in markdown_text.split("\n\n") if p.strip()]
        return "".join(f"<p>{p}</p>" for p in paragraphs)

def _extract_category_from_filename(canonical: Optional[str], request_category: Optional[str]) -> Dict[str, str]:
    """Map canonical filename or request category to feed category slug and label."""
    slug = None
    if canonical:
        parts = canonical.split("-")
        if len(parts) >= 3:
            candidate = parts[1]
            if candidate in CATEGORY_SLUG_TO_LABEL:
                slug = candidate
    if not slug and request_category:
        for key, label in CATEGORY_SLUG_TO_LABEL.items():
            if label.lower() == request_category.lower():
                slug = key
                break
    if not slug:
        slug = "phys"
    return {"slug": slug, "label": CATEGORY_SLUG_TO_LABEL.get(slug, "Physics")}

def _parse_iso_datetime(value: Optional[str]) -> datetime:
    """Parse ISO 8601 timestamps into timezone-aware UTC datetimes."""
    if not value:
        return datetime.now(timezone.utc)
    try:
        if value.endswith("Z"):
            value = value[:-1]
        dt = datetime.fromisoformat(value)
    except ValueError:
        return datetime.now(timezone.utc)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)

def _format_duration(duration_str: Optional[str]) -> str:
    """Convert duration strings like '5-10 minutes' into itunes mm:ss format."""
    if not duration_str:
        return "10:00"
    try:
        cleaned = duration_str.replace("minutes", "").strip()
        if "-" in cleaned:
            minutes = int(float(cleaned.split("-")[-1].strip()))
        else:
            minutes = int(float(cleaned.split()[0]))
        minutes = max(minutes, 1)
        return f"{minutes:02d}:00"
    except Exception:
        return "10:00"

def _extract_blob_name_from_url(url: str) -> Optional[str]:
    """Extract the blob name within the bucket from a public GCS URL."""
    if not url:
        return None
    parsed = urlparse(url)
    path = parsed.path.lstrip("/")
    if not path:
        return None
    if path.startswith(f"{RSS_BUCKET_NAME}/"):
        return path[len(RSS_BUCKET_NAME) + 1 :]
    return path

def _strip_legacy_tagline(markdown_text: Optional[str]) -> str:
    """Remove legacy marketing taglines from generated descriptions."""
    if not markdown_text:
        return ""
    cleaned_lines = []
    for line in markdown_text.splitlines():
        if line.strip() in LEGACY_DESCRIPTION_TAGLINES:
            continue
        cleaned_lines.append(line)
    cleaned = "\n".join(cleaned_lines).strip()
    while "\n\n\n" in cleaned:
        cleaned = cleaned.replace("\n\n\n", "\n\n")
    return cleaned

EPISODE_REQUEST_SNAPSHOT_FIELDS = [
    "topic",
    "category",
    "expertise_level",
    "format_type",
    "duration",
    "voice_style",
    "host_voice_id",
    "expert_voice_id",
    "additional_instructions",
    "paper_title",
    "paper_doi",
    "paper_authors",
    "paper_abstract",
    "include_citations",
    "paradigm_shift_analysis",
]

def _compact_request_snapshot(request_data: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    """Reduce request payload to the fields we want to persist on an episode."""
    if not isinstance(request_data, dict):
        return {}
    snapshot: Dict[str, Any] = {}
    for field in EPISODE_REQUEST_SNAPSHOT_FIELDS:
        if field in request_data and request_data[field] is not None:
            snapshot[field] = request_data[field]
    return snapshot

def _prepare_episode_document(
    job_id: str,
    subscriber_id: Optional[str],
    request_data: Dict[str, Any],
    result_data: Dict[str, Any],
    metadata_extended: Optional[Dict[str, Any]],
    engagement_metrics: Optional[Dict[str, Any]],
    submitted_to_rss: bool = False,
    creator_attribution: Optional[str] = None,
) -> Dict[str, Any]:
    """Create the canonical document we persist for each episode."""
    metadata_extended = metadata_extended or {}
    engagement_metrics = engagement_metrics or {}
    description_markdown = result_data.get("description", "") or ""
    description_html = _markdown_to_html(description_markdown)
    summary_text = result_data.get("itunes_summary") or extract_itunes_summary(description_markdown)
    canonical = result_data.get("canonical_filename")
    slug = canonical or job_id
    category_info = _extract_category_from_filename(canonical, request_data.get("category"))
    now_iso = datetime.utcnow().isoformat()

    episode_doc: Dict[str, Any] = {
        "episode_id": slug,
        "job_id": job_id,
        "subscriber_id": subscriber_id,
        "title": result_data.get("title", "Untitled Episode"),
        "slug": slug,
        "canonical_filename": canonical,
        "topic": request_data.get("topic"),
        "category": category_info["label"],
        "category_slug": category_info["slug"],
        "summary": summary_text,
        "description_markdown": description_markdown,
        "description_html": description_html,
        "script": result_data.get("script", ""),
        "duration": result_data.get("duration"),
        "audio_url": result_data.get("audio_url"),
        "thumbnail_url": result_data.get("thumbnail_url") or DEFAULT_ARTWORK_URL,
        "transcript_url": result_data.get("transcript_url"),
        "description_url": result_data.get("description_url"),
        "episode_link": f"{EPISODE_BASE_URL}/{slug}",
        "submitted_to_rss": submitted_to_rss,
        "creator_attribution": creator_attribution,
        "visibility": "public" if submitted_to_rss else "private",
        "request": _compact_request_snapshot(request_data),
        "metadata_extended": metadata_extended,
        "engagement_metrics": engagement_metrics,
        "search_keywords": metadata_extended.get("keywords_indexed", []),
        "created_at": result_data.get("generated_at") or now_iso,
        "generated_at": result_data.get("generated_at") or now_iso,
        "updated_at": now_iso,
        "assets": {
            "audio_blob": _extract_blob_name_from_url(result_data.get("audio_url", "")),
            "transcript_blob": _extract_blob_name_from_url(result_data.get("transcript_url", "")),
            "description_blob": _extract_blob_name_from_url(result_data.get("description_url", "")),
            "thumbnail_blob": _extract_blob_name_from_url(result_data.get("thumbnail_url", "")),
        },
    }

    return episode_doc

def _upsert_episode_document(
    job_id: str,
    subscriber_id: Optional[str],
    request_data: Dict[str, Any],
    result_data: Dict[str, Any],
    metadata_extended: Optional[Dict[str, Any]],
    engagement_metrics: Optional[Dict[str, Any]],
    submitted_to_rss: bool = False,
    creator_attribution: Optional[str] = None,
) -> None:
    """Persist or update the canonical episode document in Firestore."""
    if not db:
        return
    try:
        episode_doc = _prepare_episode_document(
            job_id,
            subscriber_id,
            request_data,
            result_data,
            metadata_extended,
            engagement_metrics,
            submitted_to_rss,
            creator_attribution,
        )
        episode_id = episode_doc["episode_id"]
        episode_ref = db.collection(EPISODE_COLLECTION_NAME).document(episode_id)
        existing = episode_ref.get()
        if existing.exists:
            existing_data = existing.to_dict() or {}
            episode_doc.setdefault("created_at", existing_data.get("created_at"))
        episode_ref.set(episode_doc, merge=True)
        print(f"🗃️ Episode catalog updated for {episode_id}")
    except Exception as e:
        print(f"⚠️ Failed to upsert episode document for job {job_id}: {e}")

def _ensure_episode_document_from_job(job_id: str, job_payload: Dict[str, Any]) -> None:
    """Ensure an episode record exists for a previously-generated job."""
    if not isinstance(job_payload, dict):
        return
    result_data = job_payload.get("result") or {}
    if not result_data:
        return
    request_data = job_payload.get("request") or {}
    metadata_extended = job_payload.get("metadata_extended") or {}
    engagement_metrics = job_payload.get("engagement_metrics") or {}
    submitted_to_rss = job_payload.get("submitted_to_rss", False)
    creator_attribution = job_payload.get("creator_attribution")
    _upsert_episode_document(
        job_id,
        job_payload.get("subscriber_id"),
        request_data,
        result_data,
        metadata_extended,
        engagement_metrics,
        submitted_to_rss=submitted_to_rss,
        creator_attribution=creator_attribution,
    )

def _update_episode_submission_state(
    canonical: Optional[str],
    submitted: bool,
    creator_attribution: Optional[str] = None,
) -> None:
    """Keep the episode catalog in sync with RSS submission status."""
    if not db or not canonical:
        return
    update_payload: Dict[str, Any] = {
        "submitted_to_rss": submitted,
        "visibility": "public" if submitted else "private",
        "updated_at": datetime.utcnow().isoformat(),
    }
    if creator_attribution is not None:
        update_payload["creator_attribution"] = creator_attribution
    timestamp_field = "rss_submitted_at" if submitted else "rss_removed_at"
    update_payload[timestamp_field] = datetime.utcnow().isoformat()
    db.collection(EPISODE_COLLECTION_NAME).document(canonical).set(update_payload, merge=True)

def _build_rss_item_data(podcast_data: Dict[str, Any], subscriber_data: Optional[Dict[str, Any]], attribution_initials: Optional[str]) -> Dict[str, Any]:
    """Prepare structured metadata required to render an RSS item."""
    result = podcast_data.get("result", {})
    request_data = podcast_data.get("request", {})

    canonical = result.get("canonical_filename")
    category_info = _extract_category_from_filename(canonical, request_data.get("category"))

    audio_url = result.get("audio_url", "")
    thumbnail_url = result.get("thumbnail_url") or DEFAULT_ARTWORK_URL
    transcript_url = result.get("transcript_url")
    description_markdown = _strip_legacy_tagline(result.get("description", ""))

    description_html = _markdown_to_html(description_markdown)
    if transcript_url:
        description_html += f'\n<p><a href="{transcript_url}">View full transcript</a></p>'
    if attribution_initials:
        description_html += f"\n<p>Creator: {attribution_initials}</p>"

    summary_text = extract_itunes_summary(description_markdown or "")

    generated_at = result.get("generated_at") or podcast_data.get("updated_at") or podcast_data.get("created_at")
    pub_date = _parse_iso_datetime(generated_at)

    guid = canonical or result.get("topic") or podcast_data.get("job_id")

    return {
        "title": result.get("title", "Untitled Episode"),
        "description_html": description_html,
        "summary": summary_text or result.get("title", ""),
        "audio_url": audio_url,
        "thumbnail_url": thumbnail_url,
        "transcript_url": transcript_url,
        "category_slug": category_info["slug"],
        "category_label": category_info["label"],
        "canonical": canonical,
        "guid": guid,
        "pub_date": pub_date,
        "duration_display": _format_duration(result.get("duration")),
        "episode_link": f"{EPISODE_BASE_URL}/{canonical}" if canonical else EPISODE_BASE_URL,
        "attribution": attribution_initials,
    }

def _append_cdata_element(parent: Element, tag: str, text: str) -> Element:
    """Append an element whose contents will be serialized as CDATA."""
    safe_text = text.replace("]]>", "]]]]><![CDATA[>")
    element = SubElement(parent, tag)
    element.text = f"<![CDATA[{safe_text}]]>"
    return element

def _create_rss_item_element(item_data: Dict[str, Any], audio_size: int) -> Element:
    """Create a fully populated RSS <item> element."""
    item_el = Element("item")

    _append_cdata_element(item_el, "title", item_data["title"])
    SubElement(item_el, "link").text = item_data["episode_link"]

    _append_cdata_element(item_el, "description", item_data["description_html"])
    _append_cdata_element(item_el, f"{{{RSS_NAMESPACES['itunes']}}}summary", item_data["summary"])
    _append_cdata_element(item_el, f"{{{RSS_NAMESPACES['content']}}}encoded", item_data["description_html"])

    _append_cdata_element(item_el, f"{{{RSS_NAMESPACES['itunes']}}}author", "CopernicusAI")

    SubElement(
        item_el,
        "enclosure",
        attrib={
            "url": item_data["audio_url"],
            "type": "audio/mpeg",
            "length": str(max(audio_size, 1)),
        },
    )

    guid_el = SubElement(item_el, "guid", attrib={"isPermaLink": "false"})
    guid_el.text = item_data["guid"]

    SubElement(item_el, "pubDate").text = format_datetime(item_data["pub_date"])

    itunes_image = SubElement(item_el, f"{{{RSS_NAMESPACES['itunes']}}}image")
    itunes_image.set("href", item_data["thumbnail_url"])

    media_thumb = SubElement(item_el, f"{{{RSS_NAMESPACES['media']}}}thumbnail")
    media_thumb.set("url", item_data["thumbnail_url"])

    media_content = SubElement(item_el, f"{{{RSS_NAMESPACES['media']}}}content")
    media_content.set("url", item_data["thumbnail_url"])
    media_content.set("medium", "image")

    SubElement(item_el, f"{{{RSS_NAMESPACES['itunes']}}}duration").text = item_data["duration_display"]
    SubElement(item_el, f"{{{RSS_NAMESPACES['itunes']}}}explicit").text = "false"
    SubElement(item_el, f"{{{RSS_NAMESPACES['itunes']}}}season").text = "1"

    episode_number = 1
    canonical = item_data["canonical"]
    if canonical and canonical.split("-")[-1].isdigit():
        episode_number = int(canonical.split("-")[-1])
    SubElement(item_el, f"{{{RSS_NAMESPACES['itunes']}}}episode").text = str(episode_number)

    _append_cdata_element(item_el, "category", item_data["category_label"])

    if item_data["attribution"]:
        person_el = SubElement(item_el, f"{{{RSS_NAMESPACES['podcast']}}}person")
        person_el.set("role", "contributor")
        person_el.text = item_data["attribution"]

    return item_el

async def _update_rss_feed(podcast_data: Dict[str, Any], subscriber_data: Optional[Dict[str, Any]], submit_to_rss: bool, attribution_initials: Optional[str]) -> None:
    """Insert or remove an episode entry in the shared RSS feed on GCS."""

    def _sync_update():
        from google.cloud import storage
        from google.api_core.exceptions import PreconditionFailed

        storage_client = storage.Client()
        bucket = storage_client.bucket(RSS_BUCKET_NAME)
        blob = bucket.blob(RSS_FEED_BLOB_NAME)

        if not blob.exists():
            raise HTTPException(status_code=500, detail="RSS feed file not found in storage.")

        blob.reload()
        current_generation = blob.generation
        xml_bytes = blob.download_as_bytes()

        root = ET.fromstring(xml_bytes)
        channel = root.find("channel")
        if channel is None:
            raise HTTPException(status_code=500, detail="RSS feed missing channel element.")

        result = podcast_data.get("result", {})
        canonical = result.get("canonical_filename")
        guid = canonical or result.get("topic") or podcast_data.get("job_id")
        if not guid:
            raise HTTPException(status_code=400, detail="Unable to determine canonical identifier for podcast.")

        existing_items: List[Element] = []
        for item in channel.findall("item"):
            guid_el = item.find("guid")
            guid_text = guid_el.text if guid_el is not None else None
            if guid_text == guid:
                continue
            existing_items.append(item)

        if submit_to_rss:
            item_data = _build_rss_item_data(podcast_data, subscriber_data, attribution_initials)
            audio_blob_name = _extract_blob_name_from_url(item_data["audio_url"])
            audio_size = 1
            if audio_blob_name:
                audio_blob = bucket.blob(audio_blob_name)
                if audio_blob.exists():
                    audio_blob.reload()
                    audio_size = audio_blob.size or 1
            new_item = _create_rss_item_element(item_data, audio_size)
            existing_items.append(new_item)

        def item_sort_key(item: Element):
            pub_el = item.find("pubDate")
            if pub_el is not None and pub_el.text:
                try:
                    return parsedate_to_datetime(pub_el.text)
                except Exception:
                    pass
            return datetime.min

        existing_items.sort(key=item_sort_key, reverse=True)

        for old_item in channel.findall("item"):
            channel.remove(old_item)
        for sorted_item in existing_items:
            channel.append(sorted_item)

        new_xml_bytes = ET.tostring(root, encoding="utf-8", xml_declaration=True)
        # Restore CDATA markers (ElementTree escapes them by default)
        xml_text = new_xml_bytes.decode("utf-8")
        xml_text = xml_text.replace("&lt;![CDATA[", "<![CDATA[").replace("]]&gt;", "]]>")
        new_xml_bytes = xml_text.encode("utf-8")
        try:
            blob.upload_from_string(
                new_xml_bytes,
                content_type="application/rss+xml",
                if_generation_match=current_generation,
            )
        except PreconditionFailed:
            raise HTTPException(status_code=409, detail="RSS feed was updated concurrently. Please retry.")

    await asyncio.to_thread(_sync_update)

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
        
        _ensure_episode_document_from_job(submission.podcast_id, podcast_data)
        canonical = (podcast_data.get('result') or {}).get('canonical_filename')
        
        # Update podcast to mark as submitted to RSS
        if submission.submit_to_rss:
            # Get subscriber attribution info if they opted in
            subscriber_doc = db.collection('subscribers').document(subscriber_id).get()
            creator_attribution = None
            subscriber_payload = subscriber_doc.to_dict() if subscriber_doc.exists else None
            
            if subscriber_doc.exists:
                subscriber_data = subscriber_payload
                # Check if user wants attribution
                if subscriber_data.get('show_attribution', False):
                    initials = subscriber_data.get('initials')
                    if initials:
                        creator_attribution = initials
                    elif subscriber_data.get('display_name'):
                        display_name = subscriber_data['display_name']
                        creator_attribution = "".join(part[0].upper() for part in display_name.split() if part).strip() or None

            # Update RSS feed with new entry before committing Firestore changes
            await _update_rss_feed(podcast_data, subscriber_payload, True, creator_attribution)
                
            # Update subscriber's RSS submission count
            if subscriber_payload is not None:
                new_count = subscriber_payload.get('podcasts_submitted_to_rss', 0) + 1
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
            _update_episode_submission_state(canonical, True, creator_attribution)
            
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
            subscriber_doc = db.collection('subscribers').document(subscriber_id).get()
            await _update_rss_feed(podcast_data, subscriber_doc.to_dict() if subscriber_doc.exists else None, False, None)

            db.collection('podcast_jobs').document(submission.podcast_id).update({
                'submitted_to_rss': False,
                'rss_removed_at': datetime.utcnow().isoformat()
            })
            _update_episode_submission_state(canonical, False, None)

            if subscriber_doc.exists:
                subscriber_data = subscriber_doc.to_dict()
                current_count = subscriber_data.get('podcasts_submitted_to_rss', 0)
                db.collection('subscribers').document(subscriber_id).update({
                    'podcasts_submitted_to_rss': max(current_count - 1, 0)
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
        canonical = (podcast_data.get('result') or {}).get('canonical_filename')
        
        if not subscriber_id:
            raise HTTPException(status_code=400, detail="Podcast not associated with a subscriber")
        
        # Delete the podcast
        db.collection('podcast_jobs').document(podcast_id).delete()
        if canonical:
            db.collection(EPISODE_COLLECTION_NAME).document(canonical).delete()
        
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
