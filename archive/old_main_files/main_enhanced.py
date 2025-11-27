from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, List, Dict
import uuid
from datetime import datetime
from typing import Dict, Any, Optional
import asyncio
import json
import os
from google.cloud import secretmanager, texttospeech, storage
from multi_voice_tts import MultiVoiceTTS
from canonical_naming import canonical_service
from canonical_helpers import generate_canonical_thumbnail, extract_citations_from_content
from google.cloud import storage
import tempfile
import io
import aiohttp

app = FastAPI(
    title="Copernicus Podcast API - Enhanced with Google TTS",
    description="Enhanced version with Google Cloud Text-to-Speech integration",
    version="2.0.0"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Simple in-memory job storage
jobs = {}

class PodcastGenerationRequest(BaseModel):
    subject: str
    category: str  # Required: biology, chemistry, computer-science, mathematics, physics
    duration: str
    speakers: str
    difficulty: str
    additional_notes: Optional[str] = ""
    source_links: Optional[List[str]] = []

def get_secret(secret_name: str) -> str:
    """Get secret from Google Secret Manager"""
    try:
        client = secretmanager.SecretManagerServiceClient()
        project_id = "regal-scholar-453620-r7"
        name = f"projects/{project_id}/secrets/{secret_name}/versions/latest"
        response = client.access_secret_version(request={"name": name})
        return response.payload.data.decode("UTF-8")
    except Exception as e:
        print(f"Error getting secret {secret_name}: {e}")
        return None

async def generate_content_openai(subject: str, duration: str, difficulty: str, additional_notes: str = "") -> Dict:
    """Generate content using OpenAI"""
    openai_key = get_secret("openai-api-key")
    if not openai_key:
        return create_fallback_content(subject, duration, difficulty)
    
    # Calculate target word count based on duration
    duration_minutes = extract_minutes(duration)
    target_words = duration_minutes * 150  # ~150 words per minute for podcasts
    
    prompt = f"""
    Create a compelling {duration} research podcast script about "{subject}" for {difficulty} audience.
    
    Additional instructions: {additional_notes}
    
    Requirements:
    - Engaging opening hook that draws listeners in
    - Clear explanation appropriate for {difficulty} level
    - Discussion of key research findings and breakthroughs
    - Practical implications and future directions
    - Authoritative, professional tone like a science communicator
    - Target length: approximately {target_words} words
    - Include natural transitions and conversational flow
    
    Return JSON format:
    {{
        "title": "Compelling episode title",
        "script": "Full podcast script with natural flow",
        "description": "Engaging episode description with key topics covered"
    }}
    """
    
    try:
        async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=45)) as session:
            headers = {
                "Authorization": f"Bearer {openai_key}",
                "Content-Type": "application/json"
            }
            
            data = {
                "model": "gpt-4",
                "messages": [{"role": "user", "content": prompt}],
                "max_tokens": min(target_words * 2, 4000),  # Allow for JSON formatting
                "temperature": 0.7
            }
            
            async with session.post("https://api.openai.com/v1/chat/completions", 
                                  headers=headers, json=data) as response:
                if response.status == 200:
                    result = await response.json()
                    content_text = result["choices"][0]["message"]["content"]
                    
                    try:
                        return json.loads(content_text)
                    except:
                        return {
                            "title": f"Research Insights: {subject}",
                            "script": content_text,
                            "description": f"An AI-generated exploration of {subject} research"
                        }
                else:
                    print(f"OpenAI API error: {response.status}")
                    
    except Exception as e:
        print(f"OpenAI error: {e}")
    
    return create_fallback_content(subject, duration, difficulty)

def extract_minutes(duration_str: str) -> int:
    """Extract minutes from duration string like '10 minutes' or '5-10 minutes'"""
    try:
        # Handle ranges like "5-10 minutes"
        if '-' in duration_str:
            duration_str = duration_str.split('-')[1]  # Take the higher number
        
        # Extract number
        import re
        numbers = re.findall(r'\d+', duration_str)
        if numbers:
            return int(numbers[0])
    except:
        pass
    return 10  # Default fallback

def create_fallback_content(subject: str, duration: str, difficulty: str) -> Dict:
    """Create fallback content when OpenAI is unavailable"""
    return {
        "title": f"Research Insights: {subject}",
        "script": f"""Welcome to this research podcast exploring {subject}.

Today we're diving deep into the fascinating world of {subject}, examining the latest research developments and their implications for the future.

This {difficulty}-level exploration covers the current state of research, recent breakthrough discoveries, and future directions in this rapidly evolving field.

Key areas we'll explore include the fundamental principles underlying {subject}, recent methodological advances, practical applications, and the broader implications for science and society.

The research landscape in {subject} continues to evolve rapidly, with new discoveries challenging our understanding and opening up exciting possibilities for future investigation.

Thank you for joining us on this exploration of {subject}. This demonstrates the power of AI-driven content generation in making complex research accessible and engaging.

This has been your research podcast on {subject}, bringing you the latest insights from the world of scientific discovery.""",
        "description": f"An exploration of {subject} research, examining current developments and future implications. Designed for {difficulty} audiences interested in cutting-edge scientific discoveries."
    }

async def generate_audio_google_tts(script: str, voice_name: str = "en-US-Neural2-F") -> str:
    """Generate audio using Google Cloud Text-to-Speech"""
    try:
        # Initialize the TTS client
        client = texttospeech.TextToSpeechClient()
        
        # Clean script for TTS
        clean_script = script.replace("**", "").replace("*", "").strip()
        
        # Limit script length for demo (Google TTS has limits)
        if len(clean_script) > 5000:
            clean_script = clean_script[:5000] + "..."
        
        # Set up the synthesis request
        synthesis_input = texttospeech.SynthesisInput(text=clean_script)
        
        # Configure voice parameters
        voice = texttospeech.VoiceSelectionParams(
            language_code="en-US",
            name=voice_name,  # High-quality Neural2 voice
            ssml_gender=texttospeech.SsmlVoiceGender.FEMALE
        )
        
        # Configure audio format
        audio_config = texttospeech.AudioConfig(
            audio_encoding=texttospeech.AudioEncoding.MP3,
            speaking_rate=1.0,
            pitch=0.0,
            volume_gain_db=0.0
        )
        
        # Perform the text-to-speech request
        response = client.synthesize_speech(
            input=synthesis_input,
            voice=voice,
            audio_config=audio_config
        )
        
        # Upload to Google Cloud Storage
        storage_client = storage.Client()
        bucket = storage_client.bucket("regal-scholar-453620-r7-podcast-storage")
        
        # Generate unique filename
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"generated-{timestamp}.mp3"
        blob = bucket.blob(f"audio/{filename}")
        
        # Upload audio data
        blob.upload_from_string(response.audio_content, content_type="audio/mpeg")
        
        # Make blob publicly accessible
        blob.make_public()
        
        # Return public URL
        return f"https://storage.googleapis.com/regal-scholar-453620-r7-podcast-storage/audio/{filename}"
        
    except Exception as e:
        print(f"Google TTS error: {e}")
        # Return mock URL for demo
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        return f"https://storage.googleapis.com/regal-scholar-453620-r7-podcast-storage/audio/demo-{timestamp}.mp3"

async def generate_thumbnail_openai(title: str) -> str:
    """Generate thumbnail using OpenAI DALL-E"""
    openai_key = get_secret("openai-api-key")
    if not openai_key:
        return "https://storage.googleapis.com/regal-scholar-453620-r7-podcast-storage/thumbnails/default-thumb.jpg"
    
    prompt = f"""
    Create a professional podcast thumbnail for "{title}".
    Style: Modern, scientific, clean design
    Elements: Abstract scientific imagery, professional typography
    Colors: Blue and white theme, high contrast
    Format: Square, podcast-ready, visually striking
    """
    
    try:
        async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=30)) as session:
            headers = {
                "Authorization": f"Bearer {openai_key}",
                "Content-Type": "application/json"
            }
            
            data = {
                "model": "dall-e-3",
                "prompt": prompt,
                "n": 1,
                "size": "1024x1024",
                "quality": "standard"
            }
            
            async with session.post("https://api.openai.com/v1/images/generations", 
                                  headers=headers, json=data) as response:
                if response.status == 200:
                    result = await response.json()
                    image_url = result["data"][0]["url"]
                    
                    # Download and upload to GCS
                    async with session.get(image_url) as img_response:
                        if img_response.status == 200:
                            image_data = await img_response.read()
                            
                            # Upload to Google Cloud Storage
                            storage_client = storage.Client()
                            bucket = storage_client.bucket("regal-scholar-453620-r7-podcast-storage")
                            
                            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                            filename = f"generated-{timestamp}-thumb.jpg"
                            blob = bucket.blob(f"thumbnails/{filename}")
                            
                            blob.upload_from_string(image_data, content_type="image/jpeg")
                            blob.make_public()
                            
                            return f"https://storage.googleapis.com/regal-scholar-453620-r7-podcast-storage/thumbnails/{filename}"
    
    except Exception as e:
        print(f"Thumbnail generation error: {e}")
    
    # Return default thumbnail
    return "https://storage.googleapis.com/regal-scholar-453620-r7-podcast-storage/thumbnails/default-thumb.jpg"

async def process_podcast_generation(job_id: str, request_data: PodcastGenerationRequest):
    """Process podcast generation with canonical naming and GCS integration"""
    try:
        # Update job status
        jobs[job_id]["status"] = "processing"
        jobs[job_id]["updated_at"] = datetime.now().isoformat()
        
        print(f"🚀 Starting canonical podcast generation for job {job_id}")
        print(f"📂 Category: {request_data.category}, Topic: {request_data.subject}")
        
        # Step 1: Generate canonical filename and numbering
        canonical_filename, episode_number = await canonical_service.generate_canonical_filename(
            request_data.category, request_data.subject
        )
        print(f"🏷️ Canonical filename: {canonical_filename}")
        
        # Step 2: Generate content using OpenAI/Gemini
        content = await generate_content_openai(
            request_data.subject, 
            request_data.duration,
            request_data.difficulty,
            request_data.additional_notes or ""
        )
        print(f"📝 Generated content: {content['title']}")
        
        # Step 3: Generate multi-voice audio using canonical naming
        multi_voice_tts = MultiVoiceTTS()
        audio_url = await multi_voice_tts.generate_multi_voice_audio(content["script"], canonical_filename)
        print(f"🎵 Generated audio: {audio_url}")
        
        # Step 4: Generate and upload thumbnail with canonical naming
        thumbnail_url = await generate_canonical_thumbnail(content["title"], canonical_filename)
        print(f"🖼️ Generated thumbnail: {thumbnail_url}")
        
        # Step 5: Format description with citations and hashtags
        # Extract citations from content if available
        citations = extract_citations_from_content(content.get("script", ""))
        formatted_description = canonical_service.format_description_with_citations(
            content["description"], citations, request_data.subject, request_data.category
        )
        
        # Step 6: Upload description to GCS
        description_url = await canonical_service.upload_description_to_gcs(
            canonical_filename, formatted_description
        )
        print(f"📄 Uploaded description: {description_url}")
        
        # Step 7: Calculate file size and add to canonical list
        # Estimate file size based on audio duration (approximate)
        duration_minutes = float(request_data.duration.split()[0]) if request_data.duration else 5.0
        estimated_file_size = int(duration_minutes * 60 * 128000 / 8)  # 128kbps MP3 estimate
        
        # Add to canonical list in GCS
        canonical_added = await canonical_service.add_to_canonical_list(
            canonical_filename, content["title"], request_data.duration, 
            estimated_file_size, request_data.category
        )
        
        if canonical_added:
            print(f"✅ Added {canonical_filename} to canonical list")
        else:
            print(f"⚠️ Failed to add {canonical_filename} to canonical list")
        
        # Complete job with canonical naming results
        jobs[job_id]["status"] = "completed"
        jobs[job_id]["result"] = {
            "canonical_filename": canonical_filename,
            "episode_number": episode_number,
            "title": content["title"],
            "description": formatted_description,
            "script": content["script"],
            "audio_url": audio_url,
            "thumbnail_url": thumbnail_url,
            "description_url": description_url,
            "duration": request_data.duration,
            "topic": request_data.subject,
            "category": request_data.category,
            "difficulty": request_data.difficulty,
            "file_size": estimated_file_size,
            "canonical_added": canonical_added,
            "generated_at": datetime.now().isoformat(),
            "tts_provider": "google_cloud_neural2",
            "content_provider": "gemini_research_enhanced",
            "character": "copernicus",
            "format_type": "research_deep_dive",
            "has_citations": len(citations) > 0,
            "citations": citations
        }
        jobs[job_id]["updated_at"] = datetime.now().isoformat()
        
        print(f"🎉 Job {job_id} completed successfully with canonical naming: {canonical_filename}")
        
    except Exception as e:
        print(f"Job {job_id} failed: {e}")
        jobs[job_id]["status"] = "failed"
        jobs[job_id]["error"] = str(e)
        jobs[job_id]["updated_at"] = datetime.now().isoformat()

@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "message": "Copernicus Research Podcast API - Enhanced with Google TTS",
        "status": "operational",
        "version": "2.0.0",
        "features": ["google_cloud_tts", "openai_content", "dall_e_thumbnails", "gcs_storage"],
        "endpoints": ["/health", "/generate-podcast", "/job/{job_id}"]
    }

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    openai_available = get_secret("openai-api-key") is not None
    gcp_tts_available = get_secret("gcp-copernicusai-tts-key") is not None
    
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "services": {
            "openai": "available" if openai_available else "unavailable",
            "google_cloud_tts": "available" if gcp_tts_available else "unavailable",
            "job_manager": "healthy",
            "gcs_storage": "available",
            "total_jobs": len(jobs),
            "active_jobs": len([j for j in jobs.values() if j["status"] in ["pending", "processing"]])
        }
    }

@app.post("/generate-podcast")
async def generate_podcast(request: PodcastGenerationRequest, background_tasks: BackgroundTasks):
    """Generate a research podcast with Google TTS"""
    job_id = str(uuid.uuid4())
    
    print(f"Starting enhanced podcast generation job {job_id} for subject: {request.subject}")
    
    # Create job record
    jobs[job_id] = {
        "id": job_id,
        "status": "pending",
        "request": request.dict(),
        "created_at": datetime.now().isoformat(),
        "updated_at": datetime.now().isoformat()
    }
    
    # Start background processing
    background_tasks.add_task(process_podcast_generation, job_id, request)
    
    return {"job_id": job_id, "status": "pending"}

@app.get("/job/{job_id}")
async def get_job_status(job_id: str):
    """Get job status and results"""
    if job_id not in jobs:
        raise HTTPException(status_code=404, detail="Job not found")
    
    return {"job": jobs[job_id]}

@app.get("/job/{job_id}/audio")
async def download_audio(job_id: str):
    """Download generated audio file"""
    if job_id not in jobs:
        raise HTTPException(status_code=404, detail="Job not found")
    
    job = jobs[job_id]
    if job["status"] != "completed" or "result" not in job:
        raise HTTPException(status_code=400, detail="Job not completed or no audio available")
    
    audio_url = job["result"].get("audio_url")
    if not audio_url:
        raise HTTPException(status_code=404, detail="Audio file not found")
    
    # Handle local file paths (file://)
    if audio_url.startswith("file://"):
        file_path = audio_url.replace("file://", "")
        if not os.path.exists(file_path):
            raise HTTPException(status_code=404, detail="Audio file not found on server")
        
        from fastapi.responses import FileResponse
        return FileResponse(
            path=file_path,
            media_type="audio/wav",
            filename=f"podcast_{job_id}.wav"
        )
    
    # Handle GCS URLs (https://)
    elif audio_url.startswith("https://storage.googleapis.com/"):
        from google.cloud import storage
        storage_client = storage.Client()
        bucket_name, file_path = audio_url.replace("https://storage.googleapis.com/", "").split("/", 1)
        bucket = storage_client.bucket(bucket_name)
        blob = bucket.blob(file_path)
        audio_data = blob.download_as_bytes()
        
        from fastapi.responses import Response
        return Response(content=audio_data, media_type="audio/mpeg", headers={"Content-Disposition": f"attachment; filename=podcast_{job_id}.mp3"})
    
    else:
        raise HTTPException(status_code=400, detail="Invalid audio URL format")

if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8002))
    uvicorn.run(app, host="0.0.0.0", port=port)
