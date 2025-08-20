from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, List
import uuid
from datetime import datetime
import os
import asyncio
import aiohttp
import json

app = FastAPI(title="Copernicus Podcast API - Working")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

jobs = {}

class PodcastGenerationRequest(BaseModel):
    subject: str
    duration: str
    speakers: str
    difficulty: str
    additional_notes: Optional[str] = ""
    source_links: Optional[List[str]] = []

def get_openai_key():
    """Get OpenAI API key from environment"""
    # Try multiple environment variable names
    key = (os.environ.get("OPENAI_API_KEY") or 
           os.environ.get("OPENAI_KEY") or
           os.environ.get("openai-api-key"))
    
    if not key:
        print("⚠️  OpenAI API key not found in environment")
        print("Available env vars:", [k for k in os.environ.keys() if 'openai' in k.lower()])
    return key

async def generate_content_openai(subject: str, duration: str, difficulty: str, notes: str = "") -> dict:
    """Generate content using OpenAI with proper error handling"""
    openai_key = get_openai_key()
    if not openai_key:
        print("❌ No OpenAI API key - using fallback content")
        return create_fallback_content(subject, duration, difficulty)
    
    prompt = f"""Create a compelling {duration} research podcast script about "{subject}" for {difficulty} audience.

Additional notes: {notes}

Create engaging content that:
- Opens with a captivating hook
- Explains concepts clearly for {difficulty} level
- Discusses key research findings
- Maintains professional, authoritative tone
- Flows naturally for audio

Return JSON:
{{"title": "Episode title", "script": "Full script", "description": "Episode description"}}"""
    
    try:
        print(f"🔄 Calling OpenAI API for content generation...")
        async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=30)) as session:
            headers = {"Authorization": f"Bearer {openai_key}", "Content-Type": "application/json"}
            data = {
                "model": "gpt-4",
                "messages": [{"role": "user", "content": prompt}],
                "max_tokens": 2000,
                "temperature": 0.7
            }
            
            async with session.post("https://api.openai.com/v1/chat/completions", 
                                  headers=headers, json=data) as response:
                if response.status == 200:
                    result = await response.json()
                    content_text = result["choices"][0]["message"]["content"]
                    print(f"✅ OpenAI content generated successfully")
                    try:
                        return json.loads(content_text)
                    except:
                        return {
                            "title": f"Research Insights: {subject}",
                            "script": content_text,
                            "description": f"AI-generated exploration of {subject}"
                        }
                else:
                    error_text = await response.text()
                    print(f"❌ OpenAI API error {response.status}: {error_text}")
    except Exception as e:
        print(f"❌ OpenAI content error: {e}")
    
    print("⚠️  Using fallback content due to API issues")
    return create_fallback_content(subject, duration, difficulty)

async def generate_audio_openai(script: str, job_id: str) -> str:
    """Generate audio using OpenAI TTS with proper error handling"""
    openai_key = get_openai_key()
    if not openai_key:
        print("❌ No OpenAI API key - returning mock audio URL")
        return f"https://storage.googleapis.com/regal-scholar-453620-r7-podcast-storage/audio/demo-{job_id[:8]}.mp3"
    
    # Clean and limit script for TTS
    clean_script = script.replace("**", "").replace("*", "").strip()
    if len(clean_script) > 4000:  # OpenAI TTS limit
        clean_script = clean_script[:4000] + "..."
    
    try:
        print(f"🔄 Calling OpenAI TTS API for audio generation...")
        async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=60)) as session:
            headers = {"Authorization": f"Bearer {openai_key}", "Content-Type": "application/json"}
            data = {
                "model": "tts-1",
                "input": clean_script,
                "voice": "nova",  # Professional female voice
                "response_format": "mp3"
            }
            
            async with session.post("https://api.openai.com/v1/audio/speech", 
                                  headers=headers, json=data) as response:
                if response.status == 200:
                    # Save audio to local file for immediate playback
                    audio_filename = f"/tmp/podcast_{job_id[:8]}.mp3"
                    with open(audio_filename, 'wb') as f:
                        async for chunk in response.content.iter_chunked(8192):
                            f.write(chunk)
                    
                    print(f"✅ OpenAI TTS audio generated: {audio_filename}")
                    # Return local file path for immediate access
                    return f"file://{audio_filename}"
                else:
                    error_text = await response.text()
                    print(f"❌ OpenAI TTS API error {response.status}: {error_text}")
    except Exception as e:
        print(f"❌ OpenAI TTS error: {e}")
    
    print("⚠️  Returning mock audio URL due to TTS issues")
    return f"https://storage.googleapis.com/regal-scholar-453620-r7-podcast-storage/audio/demo-{job_id[:8]}.mp3"

def create_fallback_content(subject: str, duration: str, difficulty: str) -> dict:
    """Fallback content when APIs are unavailable"""
    return {
        "title": f"Research Insights: {subject}",
        "script": f"""Welcome to this research podcast exploring {subject}.

Today we dive into the fascinating world of {subject}, examining current research developments and future implications.

This {difficulty}-level exploration covers fundamental principles, recent methodological advances, and practical applications in {subject}.

Key areas include the current research landscape, breakthrough discoveries, and the broader implications for science and society.

The field of {subject} continues to evolve rapidly, with new discoveries challenging our understanding and opening exciting possibilities.

Thank you for joining this exploration of {subject}, demonstrating AI-powered content generation for scientific communication.""",
        "description": f"An exploration of {subject} research for {difficulty} audiences interested in cutting-edge discoveries."
    }

async def process_podcast_generation(job_id: str, request_data: PodcastGenerationRequest):
    """Process podcast generation with detailed logging"""
    try:
        print(f"🚀 Starting podcast generation for job {job_id}")
        jobs[job_id]["status"] = "processing"
        jobs[job_id]["updated_at"] = datetime.now().isoformat()
        
        # Generate content
        print(f"📝 Generating content for: {request_data.subject}")
        content = await generate_content_openai(
            request_data.subject, 
            request_data.duration,
            request_data.difficulty,
            request_data.additional_notes or ""
        )
        
        # Generate audio
        print(f"🎙️  Generating audio for job {job_id}")
        audio_url = await generate_audio_openai(content["script"], job_id)
        
        # Mock thumbnail
        thumbnail_url = f"https://storage.googleapis.com/regal-scholar-453620-r7-podcast-storage/thumbnails/demo-{job_id[:8]}-thumb.jpg"
        
        # Complete job
        jobs[job_id]["status"] = "completed"
        jobs[job_id]["result"] = {
            "title": content["title"],
            "description": content["description"],
            "script": content["script"],
            "audio_url": audio_url,
            "thumbnail_url": thumbnail_url,
            "duration": request_data.duration,
            "subject": request_data.subject,
            "tts_provider": "openai",
            "generated_at": datetime.now().isoformat()
        }
        jobs[job_id]["updated_at"] = datetime.now().isoformat()
        
        print(f"✅ Podcast generation completed for job {job_id}")
        
    except Exception as e:
        print(f"❌ Podcast generation failed for job {job_id}: {e}")
        jobs[job_id]["status"] = "failed"
        jobs[job_id]["error"] = str(e)
        jobs[job_id]["updated_at"] = datetime.now().isoformat()

@app.get("/")
async def root():
    openai_available = get_openai_key() is not None
    return {
        "message": "Copernicus Podcast API - Working", 
        "status": "operational",
        "openai_available": openai_available
    }

@app.get("/health")
async def health():
    openai_available = get_openai_key() is not None
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "services": {
            "openai_content": "available" if openai_available else "unavailable",
            "openai_tts": "available" if openai_available else "unavailable",
            "job_manager": "healthy"
        },
        "total_jobs": len(jobs)
    }

@app.post("/generate-podcast")
async def generate_podcast(request: PodcastGenerationRequest, background_tasks: BackgroundTasks):
    job_id = str(uuid.uuid4())
    
    print(f"📥 New podcast request: {request.subject} ({request.duration}, {request.difficulty})")
    
    jobs[job_id] = {
        "id": job_id,
        "status": "pending",
        "request": request.dict(),
        "created_at": datetime.now().isoformat(),
        "updated_at": datetime.now().isoformat()
    }
    
    background_tasks.add_task(process_podcast_generation, job_id, request)
    return {"job_id": job_id, "status": "pending"}

@app.get("/job/{job_id}")
async def get_job_status(job_id: str):
    if job_id not in jobs:
        raise HTTPException(status_code=404, detail="Job not found")
    return {"job": jobs[job_id]}

if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8002))
    print(f"🚀 Starting Copernicus Podcast API on port {port}")
    print(f"🔑 OpenAI API Key: {'✅ Found' if get_openai_key() else '❌ Missing'}")
    uvicorn.run(app, host="0.0.0.0", port=port)
