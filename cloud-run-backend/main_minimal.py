from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, List, Dict
import uuid
from datetime import datetime
import json
import os

app = FastAPI(
    title="Copernicus Podcast API - Minimal",
    description="Minimal working version for test drive",
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

# Simple in-memory job storage
jobs = {}

class PodcastGenerationRequest(BaseModel):
    subject: str
    duration: str
    speakers: str
    difficulty: str
    additional_notes: Optional[str] = ""
    source_links: Optional[List[str]] = []

async def process_podcast_generation(job_id: str, request_data: PodcastGenerationRequest):
    """Process podcast generation - minimal working version"""
    try:
        # Update job status
        jobs[job_id]["status"] = "processing"
        jobs[job_id]["updated_at"] = datetime.now().isoformat()
        
        # Simulate processing time
        import asyncio
        await asyncio.sleep(2)
        
        # Generate mock content
        content = {
            "title": f"Research Podcast: {request_data.subject}",
            "script": f"""Welcome to this research podcast about {request_data.subject}. 
            
This episode explores the fascinating world of {request_data.subject}, examining the latest research developments and their implications for the future.

Our AI-powered research system has analyzed multiple academic sources to bring you this comprehensive overview. The {request_data.difficulty} level content is designed to be both informative and accessible.

Key topics covered include:
- Current state of research in {request_data.subject}
- Recent breakthrough discoveries
- Future research directions
- Practical applications and implications

This demonstrates the power of AI-driven podcast generation, combining comprehensive research with professional content creation.

Thank you for experiencing the future of scientific communication with Copernicus AI.""",
            "description": f"An AI-generated exploration of {request_data.subject} research, designed for {request_data.difficulty} audiences. Duration: {request_data.duration}."
        }
        
        # Mock URLs for demonstration
        audio_url = f"https://storage.googleapis.com/regal-scholar-453620-r7-podcast-storage/audio/demo-{job_id[:8]}.mp3"
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
            "difficulty": request_data.difficulty,
            "generated_at": datetime.now().isoformat()
        }
        jobs[job_id]["updated_at"] = datetime.now().isoformat()
        
        print(f"Job {job_id} completed successfully")
        
    except Exception as e:
        print(f"Job {job_id} failed: {e}")
        jobs[job_id]["status"] = "failed"
        jobs[job_id]["error"] = str(e)
        jobs[job_id]["updated_at"] = datetime.now().isoformat()

@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "message": "Copernicus Research Podcast API - Minimal Working Version",
        "status": "operational",
        "version": "1.0.0",
        "endpoints": ["/health", "/generate-podcast", "/job/{job_id}"]
    }

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "services": {
            "job_manager": "healthy",
            "total_jobs": len(jobs),
            "active_jobs": len([j for j in jobs.values() if j["status"] in ["pending", "processing"]])
        }
    }

@app.post("/generate-podcast")
async def generate_podcast(request: PodcastGenerationRequest, background_tasks: BackgroundTasks):
    """Generate a research podcast"""
    job_id = str(uuid.uuid4())
    
    print(f"Starting minimal podcast generation job {job_id} for subject: {request.subject}")
    
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
    port = int(os.environ.get("PORT", 8002))
    uvicorn.run(app, host="0.0.0.0", port=port)
