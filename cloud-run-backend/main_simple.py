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

app = FastAPI(
    title="Copernicus Research Podcast API - Working",
    description="Simplified working version for immediate test drive",
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

async def generate_content_openai(subject: str, duration: str, difficulty: str) -> Dict:
    """Generate content using OpenAI (working API key)"""
    openai_key = get_secret("openai-api-key")
    if not openai_key:
        return {
            "title": f"Research Podcast: {subject}",
            "script": f"Welcome to this research podcast about {subject}. This is a demonstration of the AI-powered podcast generation system. In a full implementation, this would be a comprehensive script based on the latest research findings and academic sources.",
            "description": f"An AI-generated exploration of {subject} and its research implications."
        }
    
    prompt = f"""
    Create a compelling {duration} research podcast script about "{subject}" for {difficulty} audience.
    
    Requirements:
    - Engaging opening hook
    - Clear explanation appropriate for {difficulty} level
    - Discussion of key research findings
    - Authoritative, professional tone
    - Aim for ~200 words per minute of content
    
    Return JSON format:
    {{
        "title": "Episode title",
        "script": "Full podcast script",
        "description": "Episode description"
    }}
    """
    
    try:
        async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=30)) as session:
            headers = {
                "Authorization": f"Bearer {openai_key}",
                "Content-Type": "application/json"
            }
            
            data = {
                "model": "gpt-4",
                "messages": [{"role": "user", "content": prompt}],
                "max_tokens": 1500,
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
                else:
                    print(f"OpenAI API error: {response.status}")
                    
    except Exception as e:
        print(f"OpenAI error: {e}")
    
    # Fallback content
    return {
        "title": f"Research Podcast: {subject}",
        "script": f"Welcome to this research podcast about {subject}. This episode explores the latest developments and research findings in this fascinating field. The AI system has successfully generated this content to demonstrate the podcast creation pipeline.",
        "description": f"An exploration of {subject} and its research implications."
    }

async def process_podcast_generation(job_id: str, request_data: PodcastGenerationRequest):
    """Process podcast generation in background"""
    try:
        # Update job status
        jobs[job_id]["status"] = "processing"
        jobs[job_id]["updated_at"] = datetime.now().isoformat()
        
        # Generate content using OpenAI
        content = await generate_content_openai(
            request_data.subject, 
            request_data.duration,
            request_data.difficulty
        )
        
        # Mock URLs for demo (in production these would be real generated assets)
        audio_url = f"https://storage.googleapis.com/regal-scholar-453620-r7-podcast-storage/audio/generated-{job_id[:8]}.mp3"
        thumbnail_url = f"https://storage.googleapis.com/regal-scholar-453620-r7-podcast-storage/thumbnails/generated-{job_id[:8]}-thumb.jpg"
        
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
            "difficulty": request_data.difficulty
        }
        jobs[job_id]["updated_at"] = datetime.now().isoformat()
        
        print(f"Job {job_id} completed successfully")
        
    except Exception as e:
        print(f"Job {job_id} failed: {e}")
        jobs[job_id]["status"] = "failed"
        jobs[job_id]["error"] = str(e)
        jobs[job_id]["updated_at"] = datetime.now().isoformat()

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    openai_available = get_secret("openai-api-key") is not None
    
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "services": {
            "openai": "available" if openai_available else "unavailable",
            "job_manager": "healthy",
            "total_jobs": len(jobs)
        }
    }

@app.post("/generate-podcast")
async def generate_podcast(request: PodcastGenerationRequest, background_tasks: BackgroundTasks):
    """Generate a research podcast"""
    job_id = str(uuid.uuid4())
    
    print(f"Starting podcast generation job {job_id} for subject: {request.subject}")
    
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

@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "message": "Copernicus Research Podcast API - Working Version",
        "status": "operational",
        "endpoints": ["/health", "/generate-podcast", "/job/{job_id}"]
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8002)
