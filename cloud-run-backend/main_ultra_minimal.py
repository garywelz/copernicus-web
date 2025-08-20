from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, List
import uuid
from datetime import datetime
import os

app = FastAPI(title="Copernicus Podcast API - Ultra Minimal")

# CORS
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

async def process_job(job_id: str, request_data: PodcastGenerationRequest):
    """Ultra simple job processing"""
    try:
        jobs[job_id]["status"] = "processing"
        jobs[job_id]["updated_at"] = datetime.now().isoformat()
        
        # Simple content generation
        title = f"Research Podcast: {request_data.subject}"
        script = f"""Welcome to this research podcast about {request_data.subject}.

This {request_data.duration} episode explores the fascinating world of {request_data.subject}, examining current research and future implications.

Our discussion covers key developments in {request_data.subject}, designed for {request_data.difficulty} audiences interested in cutting-edge research.

Key topics include:
- Current state of research in {request_data.subject}
- Recent breakthrough discoveries
- Future research directions
- Practical applications

This demonstrates AI-powered podcast generation, combining research insights with professional content creation.

Thank you for experiencing the future of scientific communication."""
        
        description = f"An AI-generated exploration of {request_data.subject} research, designed for {request_data.difficulty} audiences."
        
        # Complete job
        jobs[job_id]["status"] = "completed"
        jobs[job_id]["result"] = {
            "title": title,
            "description": description,
            "script": script,
            "audio_url": f"https://storage.googleapis.com/regal-scholar-453620-r7-podcast-storage/audio/demo-{job_id[:8]}.mp3",
            "thumbnail_url": f"https://storage.googleapis.com/regal-scholar-453620-r7-podcast-storage/thumbnails/demo-{job_id[:8]}-thumb.jpg",
            "duration": request_data.duration,
            "subject": request_data.subject,
            "generated_at": datetime.now().isoformat()
        }
        jobs[job_id]["updated_at"] = datetime.now().isoformat()
        
    except Exception as e:
        jobs[job_id]["status"] = "failed"
        jobs[job_id]["error"] = str(e)
        jobs[job_id]["updated_at"] = datetime.now().isoformat()

@app.get("/")
async def root():
    return {"message": "Copernicus Podcast API - Ultra Minimal", "status": "operational"}

@app.get("/health")
async def health():
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "services": {"job_manager": "healthy", "total_jobs": len(jobs)}
    }

@app.post("/generate-podcast")
async def generate_podcast(request: PodcastGenerationRequest, background_tasks: BackgroundTasks):
    job_id = str(uuid.uuid4())
    
    jobs[job_id] = {
        "id": job_id,
        "status": "pending",
        "request": request.dict(),
        "created_at": datetime.now().isoformat(),
        "updated_at": datetime.now().isoformat()
    }
    
    background_tasks.add_task(process_job, job_id, request)
    return {"job_id": job_id, "status": "pending"}

@app.get("/job/{job_id}")
async def get_job_status(job_id: str):
    if job_id not in jobs:
        raise HTTPException(status_code=404, detail="Job not found")
    return {"job": jobs[job_id]}

if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8002))
    uvicorn.run(app, host="0.0.0.0", port=port)
