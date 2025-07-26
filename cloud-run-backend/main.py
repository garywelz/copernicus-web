from fastapi import FastAPI, HTTPException, Request, Form, BackgroundTasks
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
import os
import asyncio
import uuid
from datetime import datetime
import json

# Import our enhanced research and generation modules
from research_pipeline import ComprehensiveResearchPipeline
from podcast_generator import EnhancedPodcastGenerator
from gcs_manager import GCSManager
from job_manager import JobManager

app = FastAPI(
    title="Copernicus Research Podcast API",
    description="AI-powered research podcast generation with comprehensive academic source integration",
    version="3.0.0"
)

# CORS middleware for web integration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://copernicusai.fyi", "https://copernicus-web-public.vercel.app", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize services
research_pipeline = ComprehensiveResearchPipeline()
podcast_generator = EnhancedPodcastGenerator()
gcs_manager = GCSManager()
job_manager = JobManager()

class PodcastGenerationRequest(BaseModel):
    subject: str
    duration: str  # "5-10 minutes", "15-20 minutes", etc.
    speakers: str  # "single", "multi-voice"
    difficulty: str  # "beginner", "intermediate", "advanced"
    additional_notes: Optional[str] = ""
    source_links: Optional[List[str]] = []
    user_id: Optional[str] = None
    # Advanced research options
    research_depth: Optional[str] = "comprehensive"  # "basic", "comprehensive", "exhaustive"
    include_preprints: Optional[bool] = True
    include_social_trends: Optional[bool] = False
    llm_provider: Optional[str] = "auto"  # "openai", "claude", "gemini", "auto"

class JobStatusResponse(BaseModel):
    job_id: str
    status: str  # "pending", "researching", "generating", "producing", "completed", "failed"
    progress: int  # 0-100
    message: str
    estimated_completion: Optional[str] = None
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None

@app.get("/")
async def root():
    """API health check and info"""
    return {
        "service": "Copernicus Research Podcast API",
        "version": "3.0.0",
        "status": "operational",
        "capabilities": [
            "Multi-source research discovery",
            "AI-powered content generation", 
            "Professional audio production",
            "Multi-platform distribution",
            "Real-time progress tracking"
        ],
        "research_sources": [
            "PubMed", "arXiv", "NASA ADS", "Zenodo", 
            "Google Scholar", "News API", "Social Trends"
        ],
        "ai_models": [
            "OpenAI GPT-4", "Anthropic Claude", "Google Gemini",
            "Multi-LLM optimization via OpenRouter"
        ]
    }

@app.get("/health")
async def health_check():
    """Detailed health check"""
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "services": {
            "research_pipeline": await research_pipeline.health_check(),
            "podcast_generator": await podcast_generator.health_check(),
            "gcs_storage": await gcs_manager.health_check(),
            "job_manager": job_manager.health_check()
        }
    }

@app.post("/generate-podcast")
async def generate_podcast(
    request: PodcastGenerationRequest,
    background_tasks: BackgroundTasks
):
    """Generate a research-driven podcast episode"""
    try:
        # Generate unique job ID
        job_id = f"podcast_{uuid.uuid4().hex[:12]}"
        
        # Create job record
        job = await job_manager.create_job(
            job_id=job_id,
            request_data=request.dict(),
            status="pending"
        )
        
        # Start background processing
        background_tasks.add_task(
            process_podcast_generation,
            job_id,
            request
        )
        
        return JSONResponse({
            "success": True,
            "job_id": job_id,
            "message": "Podcast generation started",
            "estimated_completion": "8-15 minutes",
            "status_url": f"/job-status/{job_id}",
            "research_sources": len(await research_pipeline.get_available_sources()),
            "processing_stages": [
                "Research Discovery",
                "Content Analysis", 
                "Script Generation",
                "Audio Production",
                "Media Processing",
                "Distribution Preparation"
            ]
        })
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to start generation: {str(e)}")

@app.get("/job-status/{job_id}")
async def get_job_status(job_id: str) -> JobStatusResponse:
    """Get real-time job status and progress"""
    try:
        job = await job_manager.get_job(job_id)
        if not job:
            raise HTTPException(status_code=404, detail="Job not found")
        
        return JobStatusResponse(**job)
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get job status: {str(e)}")

@app.get("/jobs")
async def list_jobs(limit: int = 50, status: Optional[str] = None):
    """List recent jobs (admin/debugging)"""
    try:
        jobs = await job_manager.list_jobs(limit=limit, status_filter=status)
        return {"jobs": jobs, "total": len(jobs)}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to list jobs: {str(e)}")

@app.get("/research-sources")
async def get_research_sources():
    """Get available research sources and their status"""
    try:
        sources = await research_pipeline.get_source_status()
        return {
            "sources": sources,
            "total_sources": len(sources),
            "active_sources": len([s for s in sources if s["status"] == "active"])
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get research sources: {str(e)}")

async def process_podcast_generation(job_id: str, request: PodcastGenerationRequest):
    """Background task for comprehensive podcast generation"""
    try:
        # Update job status
        await job_manager.update_job(job_id, status="researching", progress=10, 
                                   message="Discovering research sources...")
        
        # Stage 1: Comprehensive Research Discovery
        research_results = await research_pipeline.comprehensive_search(
            subject=request.subject,
            additional_context=request.additional_notes,
            source_links=request.source_links,
            depth=request.research_depth,
            include_preprints=request.include_preprints,
            include_social_trends=request.include_social_trends
        )
        
        await job_manager.update_job(job_id, status="generating", progress=30,
                                   message=f"Found {len(research_results)} sources. Generating content...")
        
        # Stage 2: AI-Powered Content Generation
        content = await podcast_generator.generate_comprehensive_content(
            research_data=research_results,
            subject=request.subject,
            duration=request.duration,
            difficulty=request.difficulty,
            speakers=request.speakers,
            llm_provider=request.llm_provider
        )
        
        await job_manager.update_job(job_id, status="producing", progress=60,
                                   message="Generating audio and media assets...")
        
        # Stage 3: Professional Media Production
        media_assets = await podcast_generator.produce_media(
            script=content["script"],
            title=content["title"],
            description=content["description"],
            speakers=request.speakers,
            job_id=job_id
        )
        
        await job_manager.update_job(job_id, status="uploading", progress=85,
                                   message="Uploading to cloud storage...")
        
        # Stage 4: Cloud Storage and Distribution
        final_urls = await gcs_manager.upload_episode_assets(
            job_id=job_id,
            audio_file=media_assets["audio"],
            thumbnail=media_assets["thumbnail"],
            transcript=content["transcript"],
            description=content["description"],
            metadata=content["metadata"]
        )
        
        # Stage 5: Complete
        await job_manager.update_job(
            job_id, 
            status="completed", 
            progress=100,
            message="Podcast generation completed successfully!",
            result={
                "audio_url": final_urls["audio"],
                "thumbnail_url": final_urls["thumbnail"], 
                "transcript_url": final_urls["transcript"],
                "description_url": final_urls["description"],
                "rss_entry_url": final_urls["rss_entry"],
                "metadata": content["metadata"],
                "research_sources_count": len(research_results),
                "generation_time": datetime.utcnow().isoformat()
            }
        )
        
    except Exception as e:
        await job_manager.update_job(
            job_id,
            status="failed",
            progress=0,
            message=f"Generation failed: {str(e)}",
            error=str(e)
        )
        print(f"Job {job_id} failed: {e}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8080)
