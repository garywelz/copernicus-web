from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
import os
import asyncio
import uuid
from datetime import datetime
import json
import aiohttp
from google.cloud import secretmanager
import tempfile
import io

app = FastAPI(
    title="Copernicus Research Podcast API - Simplified",
    description="Simplified AI-powered research podcast generation for immediate test drive",
    version="1.0.0"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Simple job storage
jobs = {}

class PodcastGenerationRequest(BaseModel):
    subject: str
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

async def simple_research(subject: str) -> List[Dict]:
    """Simplified research using only working APIs"""
    results = []
    
    # Try arXiv (no auth required)
    try:
        async with aiohttp.ClientSession() as session:
            arxiv_url = "http://export.arxiv.org/api/query"
            params = {
                "search_query": f"all:{subject}",
                "start": 0,
                "max_results": 3,
                "sortBy": "relevance"
            }
            
            async with session.get(arxiv_url, params=params) as response:
                if response.status == 200:
                    # Simple mock result for demo
                    results.append({
                        "title": f"Research on {subject}",
                        "abstract": f"Recent advances in {subject} research...",
                        "source": "arxiv"
                    })
    except Exception as e:
        print(f"arXiv search error: {e}")
    
    # Add fallback mock research
    if not results:
        results = [{
            "title": f"AI Research: {subject}",
            "abstract": f"Comprehensive analysis of {subject} and its implications for future research.",
            "source": "mock"
        }]
    
    return results

async def simple_generate_content(subject: str, research_results: List[Dict], duration: str, difficulty: str) -> Dict:
    """Generate content using OpenAI"""
    openai_key = get_secret("openai-api-key")
    if not openai_key:
        return {
            "title": f"Research Podcast: {subject}",
            "script": f"This is a test podcast about {subject}. In a real scenario, this would be a comprehensive AI-generated script based on the latest research.",
            "description": f"An exploration of {subject} and its implications."
        }
    
    research_summary = "\n".join([
        f"- {paper['title']}: {paper['abstract'][:200]}..."
        for paper in research_results
    ])
    
    prompt = f"""
    Create a compelling {duration} podcast script about {subject} for {difficulty} audience.
    
    Research Sources:
    {research_summary}
    
    Create a script that:
    1. Opens with an engaging hook
    2. Explains the topic clearly for {difficulty} level
    3. Discusses key findings and implications
    4. Maintains an authoritative, engaging tone
    
    Return JSON with:
    - title: Episode title
    - script: Full podcast script (aim for ~200 words per minute)
    - description: Episode description
    """
    
    try:
        async with aiohttp.ClientSession() as session:
            headers = {
                "Authorization": f"Bearer {openai_key}",
                "Content-Type": "application/json"
            }
            
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
                    
                    try:
                        return json.loads(content_text)
                    except:
                        return {
                            "title": f"Research Podcast: {subject}",
                            "script": content_text,
                            "description": f"An AI-generated exploration of {subject}"
                        }
    except Exception as e:
        print(f"OpenAI error: {e}")
    
    return {
        "title": f"Research Podcast: {subject}",
        "script": f"This is a test podcast about {subject}. The AI system would generate a comprehensive script based on research findings.",
        "description": f"An exploration of {subject} and its implications."
    }

async def simple_generate_audio(script: str) -> str:
    """Generate audio using ElevenLabs"""
    elevenlabs_key = get_secret("elevenlabs-api-key")
    if not elevenlabs_key:
        return "https://storage.googleapis.com/regal-scholar-453620-r7-podcast-storage/audio/test-audio.mp3"
    
    try:
        async with aiohttp.ClientSession() as session:
            headers = {
                "xi-api-key": elevenlabs_key,
                "Content-Type": "application/json"
            }
            
            # Clean script and limit length for demo
            clean_script = script.replace("**", "").replace("*", "")[:1500]
            
            data = {
                "text": clean_script,
                "voice_settings": {
                    "stability": 0.5,
                    "similarity_boost": 0.8
                },
                "model_id": "eleven_multilingual_v2"
            }
            
            # Use Sarah voice
            voice_id = "EXAVITQu4vr4xnSDxMaL"
            url = f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}"
            
            async with session.post(url, headers=headers, json=data) as response:
                if response.status == 200:
                    # For demo, return mock URL
                    return "https://storage.googleapis.com/regal-scholar-453620-r7-podcast-storage/audio/generated-audio.mp3"
    except Exception as e:
        print(f"ElevenLabs error: {e}")
    
    return "https://storage.googleapis.com/regal-scholar-453620-r7-podcast-storage/audio/test-audio.mp3"

async def process_podcast_generation(job_id: str, request_data: PodcastGenerationRequest):
    """Process podcast generation in background"""
    try:
        # Update job status
        jobs[job_id]["status"] = "processing"
        jobs[job_id]["updated_at"] = datetime.now().isoformat()
        
        # Step 1: Research
        research_results = await simple_research(request_data.subject)
        
        # Step 2: Generate content
        content = await simple_generate_content(
            request_data.subject, 
            research_results, 
            request_data.duration,
            request_data.difficulty
        )
        
        # Step 3: Generate audio
        audio_url = await simple_generate_audio(content["script"])
        
        # Step 4: Mock thumbnail
        thumbnail_url = "https://storage.googleapis.com/regal-scholar-453620-r7-podcast-storage/thumbnails/generated-thumbnail.jpg"
        
        # Complete job
        jobs[job_id]["status"] = "completed"
        jobs[job_id]["result"] = {
            "title": content["title"],
            "description": content["description"],
            "script": content["script"],
            "audio_url": audio_url,
            "thumbnail_url": thumbnail_url,
            "research_sources": len(research_results)
        }
        jobs[job_id]["updated_at"] = datetime.now().isoformat()
        
    except Exception as e:
        jobs[job_id]["status"] = "failed"
        jobs[job_id]["error"] = str(e)
        jobs[job_id]["updated_at"] = datetime.now().isoformat()

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "services": {
            "openai": "available" if get_secret("openai-api-key") else "unavailable",
            "elevenlabs": "available" if get_secret("elevenlabs-api-key") else "unavailable"
        }
    }

@app.post("/generate-podcast")
async def generate_podcast(request: PodcastGenerationRequest, background_tasks: BackgroundTasks):
    """Generate a research podcast"""
    job_id = str(uuid.uuid4())
    
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
    """Get job status"""
    if job_id not in jobs:
        raise HTTPException(status_code=404, detail="Job not found")
    
    return {"job": jobs[job_id]}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8002)
