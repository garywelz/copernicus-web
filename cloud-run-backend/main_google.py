from fastapi import FastAPI, HTTPException, BackgroundTasks, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, List
import uuid
from datetime import datetime
import os
import asyncio
import aiohttp
import json
from paper_processor import process_paper, ResearchPaper, AnalyzeOptions, PaperAnalysis, format_citation
from copernicus_character import get_copernicus_character, get_character_prompt, CopernicusCharacter
from elevenlabs_voice_service import ElevenLabsVoiceService
import re

def _extract_json_from_response(text: str) -> dict:
    """Extracts a JSON object from a string, even if it's embedded in other text."""
    # Regex to find a JSON object, potentially wrapped in markdown ```json ... ```
    json_match = re.search(r'```json\s*(\{.*?\})\s*```|(\{.*?\})', text, re.DOTALL)
    
    if not json_match:
        raise ValueError("No JSON object found in the AI's response.")
        
    # The regex has two capturing groups, one for the markdown case, one for the raw case.
    json_str = json_match.group(1) or json_match.group(2)
    
    try:
        return json.loads(json_str)
    except json.JSONDecodeError as e:
        raise ValueError(f"Failed to decode extracted JSON: {e}\nOriginal text snippet: {json_str[:200]}...")

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
    expertise_level: str = "intermediate"
    format_type: str = "interview"
    duration: str = "5-10 minutes"
    voice_style: str = "professional"
    # Research paper processing fields
    paper_content: Optional[str] = None
    paper_title: Optional[str] = None
    paper_authors: Optional[List[str]] = None
    paper_abstract: Optional[str] = None
    paper_doi: Optional[str] = None
    focus_areas: Optional[List[str]] = None
    include_citations: bool = True
    paradigm_shift_analysis: bool = True

# Legacy request format for frontend compatibility
class LegacyPodcastRequest(BaseModel):
    subject: str
    duration: str
    speakers: str = "interview"
    difficulty: str = "intermediate"
    additional_notes: Optional[str] = ""
    source_links: Optional[List[str]] = []

def convert_legacy_request(legacy: LegacyPodcastRequest) -> PodcastRequest:
    """Convert legacy frontend request to new research-driven format"""
    
    # Map legacy fields to new format
    expertise_mapping = {
        "General": "beginner",
        "Intermediate": "intermediate", 
        "Advanced": "expert",
        "Expert": "expert"
    }
    
    format_mapping = {
        "interview": "interview",
        "monologue": "monologue",
        "discussion": "interview"
    }
    
    return PodcastRequest(
        topic=legacy.subject,
        expertise_level=expertise_mapping.get(legacy.difficulty, "intermediate"),
        format_type=format_mapping.get(legacy.speakers, "interview"),
        duration=f"{legacy.duration} minutes" if legacy.duration.isdigit() else legacy.duration,
        voice_style="professional",
        focus_areas=["methodology", "implications", "future_research"] if not legacy.additional_notes else [legacy.additional_notes],
        include_citations=True,
        paradigm_shift_analysis=True
    )

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
        client.models.get("models/gemini-1.5-pro-latest")
        print("✅ google-genai client for Vertex AI initialized and model confirmed.")
        return client
        
    except Exception as e:
        print(f"❌ Failed to initialize google-genai Vertex AI client: {e}")
        print("Falling back to Google AI API key if available.")
        return None

def get_google_api_key():
    """Get Google AI API key from Secret Manager or environment"""
    # First try Secret Manager
    try:
        print("🔄 Retrieving Google AI API key from Secret Manager...")
        client = secretmanager.SecretManagerServiceClient()
        name = f"projects/{GCP_PROJECT_ID}/secrets/GOOGLE_AI_API_KEY/versions/latest"
        response = client.access_secret_version(request={"name": name})
        key = response.payload.data.decode("UTF-8").strip()
        if key:
            print("✅ Google AI API key retrieved from Secret Manager")
            return key
    except Exception as e:
        print(f"⚠️  Could not retrieve Google AI API key from Secret Manager: {e}")
    
    # Fallback to environment variables
    key = (os.environ.get("GOOGLE_AI_API_KEY") or 
           os.environ.get("GEMINI_API_KEY") or
           os.environ.get("GOOGLE_API_KEY"))
    
    if key:
        print("✅ Google AI API key found in environment")
    else:
        print("❌ Google AI API key not found in Secret Manager or environment")
    return key

# Initialize services on startup
vertex_ai_model = initialize_vertex_ai()

# Initialize Firestore client
try:
    db = firestore.Client(project=GCP_PROJECT_ID, database="copernicusai")
    print("✅ Firestore client initialized successfully")
except Exception as e:
    print(f"❌ Failed to initialize Firestore client: {e}")
    db = None

async def generate_research_driven_content(request: PodcastRequest) -> dict:
    """Generate research-driven content using paper analysis and Google Gemini (Vertex AI or API)"""
    
    # Try Vertex AI first, then fall back to Google AI API
    if vertex_ai_model:
        print("🚀 Using Vertex AI Gemini for content generation")
        return await generate_content_vertex_ai(request)
    else:
        print("🔄 Falling back to Google AI API")
        google_key = get_google_api_key()
        if not google_key:
            print("❌ No Google AI API key - using fallback content")
            raise ValueError("Google AI API key is not available.")
        return await generate_content_google_api(request, google_key)

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
- ALL speakers must be FICTIONAL with first names ONLY (e.g., "Sarah", "Marcus", "Elena")
- NO titles (Dr., Professor, PhD), NO surnames, NO real person identification
- When introducing speakers, use only first names (e.g., "Let's bring in Sarah, our expert...")
- NEVER use "Dr." or any academic titles in the script

**Script Format Requirements:**
- Create natural dialogue without speaker labels in the final script
- Write as continuous narrative with clear speaker transitions
- Use phrases like "Sarah explains" or "Marcus adds" instead of "EXPERT:" labels
- Make the conversation flow naturally without technical markers
- Include proper academic citations with DOIs where relevant
- Focus on paradigm-shifting implications and research insights
- Duration: {request.duration}
- Expertise Level: {request.expertise_level}

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
            model='gemini-1.5-flash-latest',
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
- All speakers use FIRST NAMES ONLY (e.g., Sarah, Tom, Maya) - NO surnames, titles, or honorifics
- Speakers are clearly fictional characters, not real people

**Multi-Voice Script Requirements:**
Create a natural dialogue between HOST, EXPERT, and QUESTIONER that follows this structure:
{chr(10).join([f"- {step}" for step in character.structure])}

**Format Guidelines:**
- Use "HOST:", "EXPERT:", and "QUESTIONER:" to mark each speaker
- HOST introduces the topic and guides the conversation for "Copernicus AI: Frontiers of Science"
- EXPERT provides technical analysis and research insights about {request.topic}
- QUESTIONER asks clarifying questions and represents audience curiosity
- Use only first names like Sarah, Tom, Maya, Alex, Jordan, etc.
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
            model='gemini-1.5-flash-latest',
            contents=prompt
        )
        
        if response_obj and response_obj.text:
            content = _extract_json_from_response(response_obj.text)
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
- ALL speakers must be FICTIONAL with first names ONLY (e.g., "Sarah", "Marcus", "Elena")
- NO titles (Dr., Professor, PhD), NO surnames, NO real person identification
- When introducing speakers, use only first names (e.g., "Let's bring in Sarah, our expert...")
- NEVER use "Dr." or any academic titles in the script

**Script Format Requirements:**
- Create natural dialogue without speaker labels in the final script
- Write as continuous narrative with clear speaker transitions
- Use phrases like "Sarah explains" or "Marcus adds" instead of "EXPERT:" labels
- Make the conversation flow naturally without technical markers
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
            model='models/gemini-1.5-pro-latest',
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
- ALL speakers must be FICTIONAL with first names ONLY (e.g., "Sarah", "Marcus", "Elena")
- NO titles (Dr., Professor, PhD), NO surnames, NO real person identification
- When introducing speakers, use only first names (e.g., "Let's bring in Sarah, our expert...")
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
            model='models/gemini-1.5-pro-latest',
            contents=prompt
        )
        
        if response and response.text:
            content = _extract_json_from_response(response.text)
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

async def upload_description_to_gcs(description: str, canonical_filename: str) -> str:
    """Upload episode description to GCS descriptions folder"""
    try:
        from google.cloud import storage
        
        # Initialize GCS client
        storage_client = storage.Client()
        bucket = storage_client.bucket("regal-scholar-453620-r7-podcast-storage")
        
        # Create description filename
        description_filename = f"{canonical_filename}.md"
        blob = bucket.blob(f"descriptions/{description_filename}")
        
        # Upload description as markdown
        blob.upload_from_string(description, content_type="text/markdown")
        blob.make_public()
        
        # Return public URL
        public_url = f"https://storage.googleapis.com/regal-scholar-453620-r7-podcast-storage/descriptions/{description_filename}"
        print(f"📝 Description uploaded to GCS: {public_url}")
        return public_url
        
    except Exception as e:
        print(f"❌ Error uploading description to GCS: {e}")
        return None

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
            "size": "1792x1792",  # Perfect for podcast platforms
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

async def determine_canonical_filename(topic: str, title: str) -> str:
    """Determine canonical filename based on topic category and next available episode number"""
    try:
        import requests
        import csv
        import io
        
        # Download canonical CSV from GCS
        csv_url = "https://storage.googleapis.com/regal-scholar-453620-r7-podcast-storage/canonical/Copernicus%20AI%20Canonical%20List%20071825.csv"
        response = requests.get(csv_url)
        response.raise_for_status()
        
        # Parse CSV to find highest episode number for each category
        csv_reader = csv.reader(io.StringIO(response.text))
        category_episodes = {
            "bio": 0,
            "chem": 0, 
            "compsci": 0,
            "math": 0,
            "phys": 0
        }
        
        for row in csv_reader:
            if len(row) >= 2 and row[0].startswith("ever-"):
                # Extract category and episode number from filename
                parts = row[0].split("-")
                if len(parts) >= 3:
                    category = parts[1]
                    try:
                        episode_num = int(parts[2])
                        if category in category_episodes:
                            category_episodes[category] = max(category_episodes[category], episode_num)
                    except ValueError:
                        continue
        
        # Determine category based on topic keywords
        topic_lower = topic.lower()
        title_lower = title.lower()
        combined_text = f"{topic_lower} {title_lower}"
        
        category = "phys"  # Default to physics
        if any(word in combined_text for word in ["biology", "bio", "genetic", "dna", "protein", "cell", "organism", "evolution"]):
            category = "bio"
        elif any(word in combined_text for word in ["chemistry", "chemical", "molecule", "compound", "reaction", "catalyst"]):
            category = "chem"
        elif any(word in combined_text for word in ["computer", "computing", "algorithm", "software", "programming", "ai", "artificial intelligence", "machine learning"]):
            category = "compsci"
        elif any(word in combined_text for word in ["mathematics", "math", "equation", "theorem", "proof", "statistics", "probability"]):
            category = "math"
        elif any(word in combined_text for word in ["physics", "quantum", "particle", "energy", "matter", "relativity", "thermodynamics"]):
            category = "phys"
        
        # Find the next available episode number for this category
        existing_numbers = set()
        for row in csv_reader:
            if len(row) >= 2 and row[0].startswith(f"ever-{category}-"):
                try:
                    episode_num = int(row[0].split('-')[2])
                    existing_numbers.add(episode_num)
                except (ValueError, IndexError):
                    continue

        # Start checking from the highest known number + 1
        next_episode = category_episodes[category] + 1
        while next_episode in existing_numbers:
            next_episode += 1
        next_episode_str = str(next_episode).zfill(6)  # Pad to 6 digits like 250032
        
        canonical_filename = f"ever-{category}-{next_episode_str}"
        print(f"🎯 Determined canonical filename: {canonical_filename} (category: {category}, episode: {next_episode})")
        
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

async def run_podcast_generation_job(job_id: str, request: PodcastRequest):
    """Process research-driven podcast generation with Google AI services"""
    from datetime import datetime
    if not db:
        print(f"❌ Firestore not available. Cannot update job {job_id}.")
        return

    job_ref = db.collection('podcast_jobs').document(job_id)
    try:
        print(f"Job {job_id}: Starting podcast generation for topic '{request.topic}'")
        job_ref.update({'status': 'generating_content', 'updated_at': datetime.utcnow().isoformat()})
        
        # Generate research-driven content with Gemini + Paper Analysis
        print(f"Job {job_id}: Generating research-driven content for: {request.topic}")
        if request.paper_content:
            print(f"📜 Processing research paper: {request.paper_title[:50]}...")
        
        content = await generate_research_driven_content(request)
        
        # Robust validation added here:
        if (not content or 
            not isinstance(content, dict) or
            not all(k in content for k in ['title', 'description']) or
            not content.get('title') or len(str(content.get('title', '')).strip()) < 5 or
            not content.get('description') or len(str(content.get('description', '')).strip()) < 20):
            raise ValueError("Content generation returned empty, incomplete, or placeholder data.")
        
        # Determine canonical filename based on topic category and next available episode number
        canonical_filename = await determine_canonical_filename(request.topic, content["title"])
        
        # Generate multi-voice audio with ElevenLabs and bumpers
        print(f"🎙️  Generating multi-voice ElevenLabs audio for job {job_id}")
        # Force deployment: 2025-01-21 13:45:00 UTC - Multi-voice audio generation enabled
        voice_service = ElevenLabsVoiceService()
        audio_url = await voice_service.generate_multi_voice_audio_with_bumpers(
            content["script"], 
            job_id, 
            canonical_filename,
            intro_path="bumpers/copernicus-intro.mp3",
            outro_path="bumpers/copernicus-outro.mp3"
        )
        
        # Generate and upload transcript to GCS
        print(f"📄 Generating and uploading transcript for job {job_id}")
        transcript_url = await generate_and_upload_transcript(content["script"], canonical_filename)
        
        # Upload description to GCS
        print(f"📝 Uploading episode description to GCS")
        description_url = await upload_description_to_gcs(content["description"], canonical_filename)
        
        # Generate and upload thumbnail to GCS
        print(f"🖼️  Generating and uploading episode thumbnail")
        thumbnail_url = await generate_and_upload_thumbnail(content["title"], request.topic, canonical_filename)
        
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
            }
        })
        
    except Exception as e:
        job_ref.update({
            'status': 'failed',
            'error': str(e),
            'updated_at': datetime.utcnow().isoformat()
        })
        print(f"❌ Podcast generation failed for job {job_id}: {e}")

async def run_podcast_generation_job(job_id: str, request: PodcastRequest):
    """Process research-driven podcast generation with Google AI services"""
    from datetime import datetime
    if not db:
        print(f"❌ Firestore not available. Cannot update job {job_id}.")
        return

    job_ref = db.collection('podcast_jobs').document(job_id)
    try:
        print(f"Job {job_id}: Starting podcast generation for topic '{request.topic}'")
        job_ref.update({'status': 'generating_content', 'updated_at': datetime.utcnow().isoformat()})
        
        # Generate research-driven content with Gemini + Paper Analysis
        print(f"Job {job_id}: Generating research-driven content for: {request.topic}")
        if request.paper_content:
            print(f"📜 Processing research paper: {request.paper_title[:50]}...")
        
        content = await generate_research_driven_content(request)
        # --- Start of Robust Content Validation ---
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
        # Determine canonical filename based on topic category and next available episode number
        canonical_filename = await determine_canonical_filename(request.topic, content["title"])
        
        # Generate multi-voice audio with ElevenLabs and bumpers
        print(f"🎙️  Generating multi-voice ElevenLabs audio for job {job_id}")
        # Force deployment: 2025-01-21 13:45:00 UTC - Multi-voice audio generation enabled
        voice_service = ElevenLabsVoiceService()
        audio_url = await voice_service.generate_multi_voice_audio_with_bumpers(
            content["script"], 
            job_id, 
            canonical_filename,
            intro_path="bumpers/copernicus-intro.mp3",
            outro_path="bumpers/copernicus-outro.mp3"
        )
        
        # Generate and upload transcript to GCS
        print(f"📄 Generating and uploading transcript for job {job_id}")
        transcript_url = await generate_and_upload_transcript(content["script"], canonical_filename)
        
        # Upload description to GCS
        print(f"📝 Uploading episode description to GCS")
        description_url = await upload_description_to_gcs(content["description"], canonical_filename)
        
        # Generate and upload thumbnail to GCS
        print(f"🖼️  Generating and uploading episode thumbnail")
        thumbnail_url = await generate_and_upload_thumbnail(content["title"], request.topic, canonical_filename)
        
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
            }
        })
        
    except Exception as e:
        job_ref.update({
            'status': 'failed',
            'error': str(e),
            'updated_at': datetime.utcnow().isoformat()
        })
        print(f"❌ Podcast generation failed for job {job_id}: {e}")

@app.post("/generate-podcast")
async def generate_podcast(request: PodcastRequest, background_tasks: BackgroundTasks):
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
    
    background_tasks.add_task(run_podcast_generation_job, job_id, request)
    return {"job_id": job_id, "status": "pending"}


@app.post("/generate-legacy-podcast")
async def generate_legacy_podcast(request: LegacyPodcastRequest, background_tasks: BackgroundTasks):
    """Endpoint for legacy frontend to generate podcasts"""
    
    # Convert legacy request to new format
    converted_request = convert_legacy_request(request)
    
    job_id = str(uuid.uuid4())
    
    # Enhanced logging showing conversion
    print(f"🔄 Legacy request converted: {request.subject} → {converted_request.topic} ({converted_request.expertise_level})")

    if not db:
        raise HTTPException(status_code=503, detail="Firestore service is unavailable. Cannot create job.")

    job_data = {
        'job_id': job_id,
        'status': 'pending',
        'created_at': datetime.utcnow().isoformat(),
        'updated_at': datetime.utcnow().isoformat(),
        'request': converted_request.model_dump(),
        'legacy_request': request.model_dump(),
    }
    
    try:
        db.collection('podcast_jobs').document(job_id).set(job_data)
        print(f"✅ Job {job_id} created in Firestore for topic: {converted_request.topic}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create job in Firestore: {e}")
    
    background_tasks.add_task(run_podcast_generation_job, job_id, converted_request)
    return {"job_id": job_id, "status": "pending"}

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
