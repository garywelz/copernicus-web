from fastapi import FastAPI, HTTPException, UploadFile, File, Depends, Header, Query
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
from contextlib import asynccontextmanager
from typing import Dict, Any
from email.utils import format_datetime, parsedate_to_datetime
from urllib.parse import urlparse
import xml.etree.ElementTree as ET
from xml.etree.ElementTree import Element, SubElement

# Import structured logger from utils
from utils.logging import structured_logger

# Import services
from services.rss_service import rss_service
from services.episode_service import episode_service
from services.podcast_generation_service import PodcastGenerationService

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

# Notification and error reporting configuration
ERROR_NOTIFICATION_EMAIL = os.getenv("ERROR_NOTIFICATION_EMAIL", os.getenv("NOTIFICATION_EMAIL", "garywelz@gmail.com"))
DEFAULT_SUBSCRIBER_EMAIL = os.getenv("DEFAULT_SUBSCRIBER_EMAIL", "garywelz@gmail.com")

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

# Step tracking moved to utils/step_tracking.py
from utils.step_tracking import with_step

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
    structured_logger.warning("Vertex AI or Firestore dependencies not available",
                             error=str(e),
                             install_command="pip install google-cloud-aiplatform google-cloud-secret-manager google-cloud-firestore")
    VERTEX_AI_AVAILABLE = False

app = FastAPI(title="Copernicus Podcast API - Google AI")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers from endpoints modules
from endpoints.public.health import router as health_router
from endpoints.public.debug import router as debug_router
from endpoints.public.routes import router as public_router
from endpoints.public.test import router as test_router
from endpoints.admin.routes import router as admin_router
from endpoints.subscriber.routes import router as subscriber_router
from endpoints.podcast.routes import router as podcast_router
from endpoints.papers.routes import router as papers_router
from endpoints.glmp.routes import router as glmp_router

app.include_router(health_router)
app.include_router(debug_router)
app.include_router(public_router)
app.include_router(test_router)
app.include_router(admin_router)
app.include_router(subscriber_router)
app.include_router(podcast_router)
app.include_router(papers_router)
app.include_router(glmp_router)

# PodcastRequest model moved to models/podcast.py
from models.podcast import PodcastRequest

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
        structured_logger.error("Failed to retrieve Vertex AI credentials from Secret Manager", error=str(e))
        return None

def initialize_vertex_ai():
    """Initialize Vertex AI with credentials from Secret Manager"""
    try:
        # Credentials should be picked up automatically by the library from the environment.
        # The gcloud auth application-default login or service account on Cloud Run handles this.
        client = google_genai_client.Client(vertexai=True, project=GCP_PROJECT_ID, location=VERTEX_AI_REGION)
        
        # Test connection by listing a model
        models = client.models.list()
        structured_logger.info("google-genai client for Vertex AI initialized and model confirmed")
        return client
        
    except Exception as e:
        structured_logger.warning("Failed to initialize google-genai Vertex AI client, falling back to Google AI API",
                                 error=str(e))
        return None

def load_all_api_keys_from_secret_manager():
    """Load ALL API keys from Secret Manager on startup"""
    try:
        structured_logger.info("Loading API keys from Secret Manager")
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
            # Admin API
            "ADMIN_API_KEY": "admin-api-key",
        }
        
        loaded_count = 0
        failed_keys = []
        for env_var, secret_name in api_keys.items():
            if env_var in os.environ:
                structured_logger.debug(f"{env_var} already set in environment")
                loaded_count += 1
                continue
            try:
                name = f"projects/{GCP_PROJECT_ID}/secrets/{secret_name}/versions/latest"
                response = client.access_secret_version(request={"name": name})
                key = response.payload.data.decode("UTF-8").strip()
                if key:
                    os.environ[env_var] = key
                    loaded_count += 1
                    structured_logger.debug(f"{env_var} loaded from {secret_name}")
            except Exception as e:
                failed_keys.append(env_var)
                structured_logger.warning(f"Could not load {env_var}", 
                                         error=str(e)[:50],
                                         secret_name=secret_name)
        
        structured_logger.info("API keys loaded from Secret Manager",
                              loaded_count=loaded_count,
                              total_keys=len(api_keys),
                              failed_keys=failed_keys if failed_keys else None)
        return loaded_count > 0
        
    except Exception as e:
        structured_logger.error("Failed to load API keys from Secret Manager", error=str(e))
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
        structured_logger.debug("Retrieving Google AI API key from Secret Manager")
        client = secretmanager.SecretManagerServiceClient()
        name = f"projects/{GCP_PROJECT_ID}/secrets/GOOGLE_AI_API_KEY/versions/latest"
        response = client.access_secret_version(request={"name": name})
        key = response.payload.data.decode("UTF-8").strip()
        if key:
            structured_logger.debug("Google AI API key retrieved from Secret Manager")
            os.environ["GOOGLE_AI_API_KEY"] = key
            return key
    except Exception as e:
        structured_logger.error("Could not retrieve Google AI API key", error=str(e))
    
    return None

# Admin Authentication
def get_admin_api_key() -> Optional[str]:
    """Get admin API key from environment or Secret Manager"""
    admin_key = os.environ.get('ADMIN_API_KEY')
    if admin_key:
        return admin_key.strip()
    return None

async def verify_admin_api_key(
    x_admin_api_key: Optional[str] = Header(None, alias="X-Admin-API-Key"),
    admin_key: Optional[str] = Query(None, alias="admin_key")
):
    """Verify admin API key from header or query parameter - FastAPI dependency"""
    expected_key = get_admin_api_key()
    
    if not expected_key:
        structured_logger.warning("ADMIN_API_KEY not configured - admin endpoints will be inaccessible")
        raise HTTPException(status_code=503, detail="Admin authentication not configured")
    
    # Check header first, then query parameter
    provided_key = x_admin_api_key or admin_key
    
    if not provided_key:
        raise HTTPException(
            status_code=401,
            detail="Admin API key required. Provide via X-Admin-API-Key header or admin_key query parameter"
        )
    
    if provided_key.strip() != expected_key.strip():
        structured_logger.warning("Invalid admin API key attempt")
        raise HTTPException(status_code=403, detail="Invalid admin API key")
    
    return True

# Initialize services on startup
structured_logger.info("COPERNICUS AI BACKEND INITIALIZATION")

# Load all API keys first
load_all_api_keys_from_secret_manager()

# Then initialize AI services
vertex_ai_model = initialize_vertex_ai()

# Initialize Podcast Generation Service with Vertex AI model
podcast_generation_service = PodcastGenerationService(vertex_ai_model=vertex_ai_model)
structured_logger.info("Podcast Generation Service initialized")

# Initialize Firestore client
try:
    db = firestore.Client(project=GCP_PROJECT_ID, database="copernicusai")
    structured_logger.info("Firestore client initialized successfully")
except Exception as e:
    structured_logger.error("Failed to initialize Firestore client", error=str(e))
    db = None

async def generate_research_driven_content(request: PodcastRequest) -> dict:
    """Generate research-driven content using proper research methodology"""
    
    # Use the working research-driven approach directly
    structured_logger.info("Using research-driven content generation with proper methodology",
                          topic=request.topic)
    
    # Try Vertex AI first, then fall back to Google AI API
    if vertex_ai_model:
        structured_logger.info("Using Vertex AI Gemini for content generation")
        try:
            return await generate_content_vertex_ai(request)
        except Exception as e:
            structured_logger.warning("Vertex AI failed, falling back to Google AI API",
                                     error=str(e),
                                     topic=request.topic)
            google_key = get_google_api_key()
            if not google_key:
                structured_logger.error("No Google AI API key available",
                                       topic=request.topic)
                raise ValueError("Both Vertex AI and Google AI API are unavailable.")
            return await generate_content_google_api(request, google_key)
    else:
        structured_logger.info("Using Google AI API for research-driven content")
        google_key = get_google_api_key()
        if not google_key:
            structured_logger.error("No Google AI API key - cannot generate content",
                                   topic=request.topic)
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
        
        structured_logger.info("Enhanced character-driven content generated successfully",
                              topic=request.topic if request else None)
        return content
        
    except Exception as e:
        structured_logger.error("Enhanced content generation failed",
                               error=str(e),
                               error_type=type(e).__name__,
                               topic=request.topic if request else None)
        raise e

async def generate_content_vertex_ai(request: PodcastRequest) -> dict:
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
        return await generate_podcast_from_analysis_vertex(paper, analysis, request)
    else:
        structured_logger.info("Generating topic-based research content with Vertex AI",
                              topic=request.topic)
        return await generate_topic_research_content_vertex(request)

async def generate_content_google_api(request: PodcastRequest, google_key: str) -> dict:
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
        return await generate_podcast_from_analysis(paper, analysis, request, google_key)
        
    else:
        # No paper provided - generate topic-based research content
        structured_logger.info("Generating research-driven content for topic",
                              topic=request.topic)
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

**CRITICAL: Generate a CONCISE description using this EXACT format:**

**LENGTH REQUIREMENT: The description content (excluding References, Episode Details, and Hashtags) MUST be under 2000-2500 characters total. This leaves room for complete References and Hashtags sections which will be added separately. Be concise and focused.**

IMPORTANT: Do NOT include a "## Episode Overview" header. Start directly with 1-2 engaging paragraphs (CONCISE) introducing the research paper, its significance, and why this research matters. Explain the broader context and implications. Make it compelling but brief. Begin the description immediately without any section header for the opening content.

## Key Concepts Explored
- [Key Finding 1]: [Brief explanation with implications - keep to 1-2 sentences]
- [Key Finding 2]: [Brief explanation with applications - keep to 1-2 sentences]
- [Key Finding 3]: [Brief explanation - keep to 1-2 sentences]
- [Paradigm Shift]: [How this changes the field - keep to 1-2 sentences]
- [Future Direction]: [What this enables next - keep to 1-2 sentences]

## Research Insights
[1 paragraph (CONCISE) about the paper's methodology, breakthrough findings, and contribution to the field. Keep it brief and focused on what makes this research unique.]

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
                        ref_section = desc_parts[1].split('##')[0]  # Get content until next section
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

**CRITICAL: Generate a CONCISE description using this EXACT format:**

**LENGTH REQUIREMENT: The description content (excluding References, Episode Details, and Hashtags) MUST be under 2000-2500 characters total. This leaves room for complete References and Hashtags sections which will be added separately. Be concise and focused.**

IMPORTANT: Do NOT include a "## Episode Overview" header. Start directly with 1-2 engaging paragraphs (CONCISE) introducing the research paper, its significance, and why this research matters. Explain the broader context and implications. Make it compelling but brief. Begin the description immediately without any section header for the opening content.

## Key Concepts Explored
- [Key Finding 1]: [Brief explanation with implications - keep to 1-2 sentences]
- [Key Finding 2]: [Brief explanation with applications - keep to 1-2 sentences]
- [Key Finding 3]: [Brief explanation - keep to 1-2 sentences]
- [Paradigm Shift]: [How this changes the field - keep to 1-2 sentences]
- [Future Direction]: [What this enables next - keep to 1-2 sentences]

## Research Insights
[1 paragraph (CONCISE) about the paper's methodology, breakthrough findings, and contribution to the field. Keep it brief and focused on what makes this research unique.]

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
            response = vertex_ai_model.models.generate_content(
                model=model_name,
                contents=prompt
            )
        except Exception as e:
            error_msg = str(e).lower()
            if "not found" in error_msg or "does not exist" in error_msg:
                structured_logger.info("Gemini 3.0 not available, falling back to 2.5")
                model_name = 'models/gemini-2.5-flash'
                response = vertex_ai_model.models.generate_content(
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

Generate a detailed, engaging episode description (aim for 2500-3500 characters to maximize discoverability). Be thorough and informative while remaining accessible.

## Episode Overview
[3-4 engaging paragraphs introducing the topic, its significance in the field, and why this research area matters. Explain the broader context, historical background, and implications. Make it compelling and informative.]

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
        structured_logger.info("Generating topic-based research content with Vertex AI Gemini",
                              topic=request.topic)
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
                structured_logger.info("Gemini 3.0 not available, falling back to 2.5",
                                      topic=request.topic)
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

async def generate_audio_google_tts(script: str, job_id: str) -> str:
    """Generate audio using Google Cloud TTS"""
    try:
        from google.cloud import texttospeech
        
        structured_logger.info("Calling Google Cloud TTS for audio generation", job_id=job_id)
        
        # Initialize the TTS client
        client = texttospeech.TextToSpeechClient()
        
        # Clean script for TTS
        clean_script = script.replace("**", "").replace("*", "").strip()
        
        # Check byte length (not character length) for Google TTS limit
        clean_script_bytes = clean_script.encode('utf-8')
        script_length = len(clean_script_bytes)
        if script_length > 4800:  # Leave buffer for safety
            # Truncate by bytes, then decode back to string
            truncated_bytes = clean_script_bytes[:4800]
            # Ensure we don't cut in the middle of a UTF-8 character
            while len(truncated_bytes) > 0:
                try:
                    clean_script = truncated_bytes.decode('utf-8') + "..."
                    break
                except UnicodeDecodeError:
                    truncated_bytes = truncated_bytes[:-1]
            structured_logger.warning("Script truncated for Google TTS",
                                     job_id=job_id,
                                     original_length=script_length,
                                     truncated_length=len(clean_script.encode('utf-8')))
        
        structured_logger.debug("Script prepared for TTS",
                               job_id=job_id,
                               script_length_bytes=len(clean_script.encode('utf-8')))
        
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
        
        structured_logger.info("Google Cloud TTS audio generated",
                              job_id=job_id,
                              audio_filename=audio_filename)
        return f"file://{audio_filename}"
        
    except ImportError:
        structured_logger.warning("Google Cloud TTS library not installed - using fallback",
                                  job_id=job_id)
    except Exception as e:
        structured_logger.error("Google Cloud TTS error",
                               job_id=job_id,
                               error=str(e))
    
    structured_logger.warning("Returning mock audio URL due to TTS issues", job_id=job_id)
    return f"https://storage.googleapis.com/regal-scholar-453620-r7-podcast-storage/audio/demo-{job_id[:8]}.mp3"

@retry_upload(max_retries=3, delay=2)
async def upload_description_to_gcs(description: str, canonical_filename: str, title: str = "", topic: str = "") -> str:
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
            # Extract topic from description for better hashtag generation if not provided
            if not topic:
                topic_match = re.search(r'^#\s*(.+)', description, re.MULTILINE)
                topic_for_hashtags = topic_match.group(1) if topic_match else ""
            else:
                topic_for_hashtags = topic
            
            # Generate context-aware hashtags using title, topic, and description
            hashtags = generate_relevant_hashtags(topic_for_hashtags, category, title or "", description)
            
            # Add hashtags section (don't add References header - it's already in description if needed)
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
            
            # Reserve space for references and hashtags (prioritize these)
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
            
            structured_logger.debug("Trimmed description, preserving full references",
                                   canonical_filename=canonical_filename,
                                   final_length=len(enhanced_description))
        
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
        structured_logger.info("Transcript uploaded to GCS",
                              canonical_filename=canonical_filename,
                              public_url=public_url)
        return public_url
        
    except Exception as e:
        structured_logger.error("Error generating/uploading transcript",
                               canonical_filename=canonical_filename,
                               error=str(e))
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
        structured_logger.warning("Could not get OpenAI API key from Secret Manager",
                                  error=str(e))
        return os.getenv("OPENAI_API_KEY", "")

async def generate_fallback_thumbnail(canonical_filename: str, topic: str) -> str:
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
            structured_logger.warning("No OpenAI API key available for DALL-E thumbnail generation, using fallback",
                                     canonical_filename=canonical_filename)
            return await generate_fallback_thumbnail(canonical_filename, topic)
        
        # Extract category from canonical filename for more specific visuals
        # Each discipline has a DISTINCT visual style and color palette
        import re
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
            
            # Build the enhanced prompt with category-specific styling
            if category and category in category_styles:
                style_config = category_styles[category]
                category_style_text = f"""
Discipline-Specific Style: {style_config['style']}
Visual Aesthetic: {style_config['mood']}
Color Approach: {style_config['color_palette']}
"""
            else:
                category_style_text = ""
            
            # Create enhanced DALL-E prompt with title-specific details and distinct discipline styling
            dalle_prompt = f"""Create a breathtaking scientific visualization for a research podcast episode titled "{title}".

The podcast explores: {topic}
Discipline Category: {category.upper() if category else 'Science'}

{category_style_text}

Visual Style: Ultra-modern scientific illustration, photorealistic 3D rendering with depth and dimension. Professional digital art with cinematic lighting and dramatic composition. The style should be distinctly recognizable as belonging to this scientific discipline.

Key Visual Elements: {enhanced_visual_elements} specifically related to "{title}". Focus on the most distinctive and recognizable visual concepts from the title. Dynamic, flowing compositions that suggest motion and discovery. Include subtle abstract patterns that represent breakthrough thinking and paradigm shifts. Ensure the visual elements clearly identify this as {category.upper() if category else 'scientific'} content.

Color Palette: {color_palette}. High contrast for maximum visual impact. Professional color grading. The color scheme should be distinctly characteristic of this discipline and immediately recognizable.

Composition: Square format optimized for podcast platforms. Centered focal point with surrounding elements creating visual flow. Balanced negative space. Depth-of-field effect with foreground elements sharp and background slightly blurred for dimension.

Technical Quality: Ultra-high resolution, crystal-clear detail, professional photography quality. No pixelation or artifacts. Suitable for high-DPI displays and large format printing.

Important: Absolutely NO text, NO words, NO titles, NO labels. Pure visual scientific concept art that tells a story through imagery alone. The visual style must be distinctive enough that viewers can identify the scientific discipline at a glance.

Mood and Atmosphere: {mood_description}. Convey the excitement and importance of scientific advancement in this specific field. The thumbnail should feel uniquely representative of {category.upper() if category else 'scientific'} research."""
        
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
                
                public_url = f"https://storage.googleapis.com/regal-scholar-453620-r7-podcast-storage/thumbnails/{thumbnail_filename}"
                structured_logger.info("DALL-E thumbnail uploaded",
                                     canonical_filename=canonical_filename,
                                     public_url=public_url)
                return public_url
            else:
                structured_logger.warning("Failed to download DALL-E image, using fallback",
                                         canonical_filename=canonical_filename,
                                         status_code=img_response.status_code)
                return await generate_fallback_thumbnail(canonical_filename, topic)
        else:
            structured_logger.warning("DALL-E API error, using fallback",
                                     canonical_filename=canonical_filename,
                                     status_code=response.status_code,
                                     error_text=response.text[:200] if response.text else None)
            return await generate_fallback_thumbnail(canonical_filename, topic)

    except Exception as e:
        structured_logger.error("Error generating/uploading thumbnail, using fallback",
                               canonical_filename=canonical_filename,
                               error=str(e))
        return await generate_fallback_thumbnail(canonical_filename, topic)

async def determine_canonical_filename(topic: str, title: str, category: str = None, format_type: str = "feature") -> str:
    """Determine canonical filename based on topic category, format type, and next available episode number"""
    
    # Debug: Log the input parameters
    structured_logger.debug("determine_canonical_filename called",
                           topic=topic,
                           title=title,
                           category=category,
                           format_type=format_type)
    
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
            
            structured_logger.debug("Current max episodes by category",
                                   category_episodes=category_episodes)
            
        except Exception as e:
            structured_logger.warning("Could not query Firestore for episode numbers, using defaults",
                                     error=str(e))
        
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
                    structured_logger.debug("File already exists, incrementing episode number",
                                           category=request_category,
                                           new_episode=next_episode_str)
        except Exception as e:
            structured_logger.warning("Could not verify GCS for episode number",
                                     episode_str=next_episode_str,
                                     error=str(e))
        
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
                    structured_logger.debug("Determined NEWS filename",
                                          filename=canonical_filename,
                                          category=request_category,
                                          date=date_str,
                                          serial=serial_str)
                else:
                    # Fallback if GCS check fails
                    canonical_filename = f"news-{request_category}-{date_str}-0001"
                    structured_logger.debug("Determined NEWS filename (fallback)", filename=canonical_filename)
            except Exception as e:
                structured_logger.warning("Could not check GCS for news serial numbering",
                                         error=str(e))
                canonical_filename = f"news-{request_category}-{date_str}-0001"
                structured_logger.debug("Determined NEWS filename (error fallback)", filename=canonical_filename)
        else:
            # Feature format: ever-{category}-{episode}
            canonical_filename = f"ever-{request_category}-{next_episode_str}"
            structured_logger.debug("Determined FEATURE filename",
                                  filename=canonical_filename,
                                  category=request_category,
                                  episode=next_episode)
        
        return canonical_filename
        
    except Exception as e:
        structured_logger.error("Error determining canonical filename",
                               error=str(e),
                               topic=topic,
                               title=title,
                               category=category)
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


# Podcast generation endpoints moved to endpoints/podcast/routes.py

# Debug endpoints moved to endpoints/public/debug.py

# Health endpoints moved to endpoints/public/health.py

# Subscriber endpoints moved to endpoints/subscriber/routes.py

# Public/episode endpoints moved to endpoints/public/routes.py

# Podcast generation endpoints moved to endpoints/podcast/routes.py

# Public/episode endpoints moved to endpoints/public/routes.py

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

# Episode management functions moved to services/episode_service.py - use episode_service methods

# RSS feed functions moved to services/rss_service.py - use rss_service.update_rss_feed() and rss_service.update_episode_submission_state()

# Subscriber submit-to-rss endpoint moved to endpoints/subscriber/routes.py

# Modify existing generate-podcast endpoint to support subscribers
# Subscriber password-reset and delete endpoints moved to endpoints/subscriber/routes.py

# --- Research Papers API Endpoints moved to endpoints/papers/routes.py ---
# Helper function for paper preprocessing (used by papers router)
from typing import Dict, Any

class ResearchPaperPreprocessing(BaseModel):
    """Paper preprocessing result"""
    key_findings: List[str] = []
    llm_summary: str = ""
    entities_extracted: Dict[str, Any] = {}
    processed_by_model: Optional[str] = None
    processed_at: Optional[str] = None


class ResearchPaperModel(BaseModel):
    """Research paper model for storage"""
    paper_id: str
    doi: Optional[str] = None
    title: str
    authors: List[str] = []
    abstract: Optional[str] = None
    url: Optional[str] = None
    discipline: Optional[str] = None
    created_at: str
    updated_at: str
    preprocessing: Optional[ResearchPaperPreprocessing] = None


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
        structured_logger.error("Error preprocessing paper",
                               paper_title=paper.title if paper else None,
                               error=str(e))
        # Return empty preprocessing rather than failing
        return ResearchPaperPreprocessing()

# --- GLMP API Endpoints ---

# Test endpoint moved to endpoints/public/test.py

if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8080))
    structured_logger.info("Starting Copernicus Podcast API",
                          port=port,
                          vertex_ai_available=bool(vertex_ai_model),
                          google_api_key_available=bool(get_google_api_key()),
                          ai_provider="Vertex AI" if vertex_ai_model else "Google AI API" if get_google_api_key() else "Fallback",
                          vertex_ai_project=GCP_PROJECT_ID if vertex_ai_model else None,
                          vertex_ai_region=VERTEX_AI_REGION if vertex_ai_model else None)
    uvicorn.run(app, host="0.0.0.0", port=port)
