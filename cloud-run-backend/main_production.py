"""
Production-Quality Copernicus Podcast API
Integrates sophisticated patterns from legacy architecture:
- Multi-paper research synthesis and connection analysis
- Essay-to-podcast conversion with theme extraction
- Sophisticated voice configuration and duration targeting
- Quality control workflows with validation
- Structured JSON prompts with error handling
"""

from fastapi import FastAPI, HTTPException, BackgroundTasks, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
import uuid
from datetime import datetime
import os
import asyncio
import json
import logging

# Import enhanced production services
from enhanced_research_service import EnhancedResearchService, PaperAnalysis, EnhancedPodcastScript
from elevenlabs_voice_service import ElevenLabsVoiceService, SynthesisResult
from research_pipeline import ComprehensiveResearchPipeline, ResearchSource
from canonical_helpers import determine_canonical_filename, get_next_episode_info
from gcs_manager import GCSManager
from copernicus_character import get_copernicus_character

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Copernicus Podcast API - Production Quality")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global job storage
jobs = {}

# Initialize production services
research_service = None
voice_service = None
research_pipeline = None
gcs_manager = None

class ProductionPodcastRequest(BaseModel):
    """Enhanced podcast request with research-driven capabilities"""
    topic: str
    expertise_level: str = "intermediate"
    format_type: str = "interview"
    duration: str = "8-10 minutes"
    voice_style: str = "professional"
    
    # Research configuration
    research_depth: str = "comprehensive"  # "quick", "standard", "comprehensive"
    include_preprints: bool = True
    include_news: bool = False
    max_papers: int = 5
    
    # Content configuration
    paradigm_shift_analysis: bool = True
    interdisciplinary_focus: bool = True
    practical_applications: bool = True
    
    # Audio configuration
    multi_voice: bool = True
    target_duration_seconds: Optional[int] = None
    voice_speed_adjustment: float = 1.0
    
    # Legacy compatibility
    subject: Optional[str] = None  # Maps to topic
    difficulty: Optional[str] = None  # Maps to expertise_level
    speakers: Optional[str] = None  # Maps to format_type
    additional_notes: Optional[str] = ""
    source_links: Optional[List[str]] = []

class ResearchPaperUpload(BaseModel):
    """Research paper upload for analysis"""
    title: str
    content: str
    authors: Optional[List[str]] = []
    doi: Optional[str] = None
    abstract: Optional[str] = None

def initialize_services():
    """Initialize production services with error handling"""
    global research_service, voice_service, research_pipeline, gcs_manager
    
    # Get Google AI API key from Secret Manager or environment
    from canonical_helpers import get_secret
    google_key = (get_secret("google-ai-api-key") or
                  get_secret("GOOGLE-AI-API-KEY") or
                  get_secret("gemini-api-key") or
                  os.environ.get("GOOGLE_AI_API_KEY") or 
                  os.environ.get("GEMINI_API_KEY") or
                  os.environ.get("GOOGLE_API_KEY"))
    
    if not google_key:
        logger.error("❌ No Google AI API key found in Secret Manager or environment")
        return False
    
    try:
        # Initialize enhanced services
        research_service = EnhancedResearchService(google_key)
        voice_service = ElevenLabsVoiceService()
        research_pipeline = ComprehensiveResearchPipeline()
        gcs_manager = GCSManager()
        
        logger.info("✅ Production services initialized successfully")
        return True
    except Exception as e:
        logger.error(f"❌ Service initialization failed: {e}")
        return False

# Wrapper functions for GCS operations
async def upload_audio_to_gcs(audio_data: bytes, canonical_filename: str, duration: float) -> str:
    """Upload audio data to GCS and return public URL"""
    try:
        import tempfile
        import wave
        import subprocess
        
        # Debug logging
        logger.info(f"🔍 Audio upload debug:")
        logger.info(f"   Audio data size: {len(audio_data):,} bytes")
        logger.info(f"   Expected duration: {duration:.1f}s")
        logger.info(f"   Canonical filename: {canonical_filename}")
        
        # Convert LINEAR16 PCM to WAV first, then to MP3
        with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as wav_file:
            # Create WAV file from LINEAR16 PCM data
            with wave.open(wav_file.name, 'wb') as wav:
                wav.setnchannels(1)  # Mono
                wav.setsampwidth(2)  # 16-bit
                wav.setframerate(24000)  # 24kHz sample rate
                wav.writeframes(audio_data)
            
            wav_file_size = os.path.getsize(wav_file.name)
            logger.info(f"   WAV file size: {wav_file_size:,} bytes")
            
            # Convert WAV to MP3 using ffmpeg
            with tempfile.NamedTemporaryFile(suffix='.mp3', delete=False) as mp3_file:
                try:
                    subprocess.run([
                        'ffmpeg', '-i', wav_file.name, 
                        '-codec:a', 'libmp3lame', 
                        '-b:a', '128k',
                        '-y', mp3_file.name
                    ], check=True, capture_output=True)
                    
                    mp3_file_size = os.path.getsize(mp3_file.name)
                    logger.info(f"   MP3 file size: {mp3_file_size:,} bytes")
            
                    # Upload the converted MP3 file
                    blob_name = f"audio/{canonical_filename}.mp3"
                    url = await gcs_manager._upload_file(mp3_file.name, blob_name, "audio/mpeg")
                    
                    # Clean up temp files
                    os.unlink(wav_file.name)
                    os.unlink(mp3_file.name)
                    
                    logger.info(f"✅ Audio converted and uploaded: {canonical_filename}.mp3")
                    return url
                    
                except subprocess.CalledProcessError as e:
                    logger.error(f"❌ FFmpeg conversion failed: {e}")
                    # Fallback: upload WAV file as MP3 (may not play correctly)
                    blob_name = f"audio/{canonical_filename}.mp3"
                    url = await gcs_manager._upload_file(wav_file.name, blob_name, "audio/mpeg")
                    os.unlink(wav_file.name)
                    return url
    except Exception as e:
        logger.error(f"❌ Audio upload failed: {e}")
        return ""

async def upload_description_to_gcs(description: str, canonical_filename: str) -> str:
    """Upload description to GCS and return public URL"""
    try:
        blob_name = f"descriptions/{canonical_filename}.md"
        url = await gcs_manager._upload_text_content(description, blob_name, "text/markdown")
        return url
    except Exception as e:
        logger.error(f"❌ Description upload failed: {e}")
        return ""

async def process_production_podcast_generation(job_id: str, request: ProductionPodcastRequest):
    """
    Production-quality podcast generation with full research pipeline
    """
    try:
        jobs[job_id]["status"] = "processing"
        jobs[job_id]["stage"] = "research_discovery"
        jobs[job_id]["updated_at"] = datetime.now().isoformat()
        
        logger.info(f"🚀 Starting production podcast generation for job {job_id}")
        logger.info(f"📋 Topic: {request.topic}")
        logger.info(f"🎯 Expertise: {request.expertise_level}, Duration: {request.duration}")
        logger.info(f"🔬 Research depth: {request.research_depth}, Max papers: {request.max_papers}")
        
        # Stage 1: Research Discovery
        logger.info("🔍 Stage 1: Research Discovery")
        research_sources = await research_pipeline.comprehensive_search(
            subject=request.topic,
            additional_context=request.additional_notes,
            source_links=request.source_links,
            depth=request.research_depth,
            include_preprints=request.include_preprints,
            include_social_trends=request.include_news
        )
        
        # Limit to max papers and rank by relevance
        research_sources = research_sources[:request.max_papers]
        logger.info(f"📚 Found {len(research_sources)} research sources")
        
        jobs[job_id]["stage"] = "research_analysis"
        jobs[job_id]["research_sources"] = len(research_sources)
        
        # Stage 2: Multi-Paper Analysis and Synthesis
        logger.info("🧠 Stage 2: Multi-Paper Analysis and Synthesis")
        paper_analyses = await research_service.analyze_multiple_papers(
            research_sources, 
            complexity=request.expertise_level
        )
        
        logger.info(f"📊 Completed analysis of {len(paper_analyses)} papers")
        
        jobs[job_id]["stage"] = "script_generation"
        jobs[job_id]["analyses_completed"] = len(paper_analyses)
        
        # Stage 3: Research-Driven Script Generation
        logger.info("📝 Stage 3: Research-Driven Script Generation")
        
        # Parse duration
        target_minutes = 8  # Default
        if request.duration:
            import re
            duration_match = re.search(r'(\d+)', request.duration)
            if duration_match:
                target_minutes = int(duration_match.group(1))
        
        podcast_script = await research_service.generate_podcast_from_research(
            topic=request.topic,
            research_analyses=paper_analyses,
            duration_minutes=target_minutes,
            expertise_level=request.expertise_level
        )
        
        logger.info(f"✅ Generated script with {len(podcast_script.segments)} segments")
        logger.info(f"🎭 Speakers: {', '.join(podcast_script.speakers)}")
        logger.info(f"📋 Themes: {', '.join(podcast_script.themes)}")
        
        jobs[job_id]["stage"] = "audio_synthesis"
        jobs[job_id]["script_segments"] = len(podcast_script.segments)
        
        # Stage 4: Multi-Voice Audio Synthesis
        logger.info("🎙️ Stage 4: Multi-Voice Audio Synthesis")
        
        # Prepare script segments for multi-voice synthesis (without speaker labels in content)
        script_segments = []
        
        # Add introduction as host
        if podcast_script.introduction:
            script_segments.append({
                "speaker": "host",
                "content": podcast_script.introduction
            })
        
        # Add main segments with proper speaker mapping
        for segment in podcast_script.segments:
            script_segments.append({
                "speaker": segment.speaker.lower(),
                "content": segment.content
            })
        
        # Add conclusion as host
        if podcast_script.conclusion:
            script_segments.append({
                "speaker": "host",
                "content": podcast_script.conclusion
            })
        
        # Create clean script content for synthesis (no speaker labels)
        # Synthesize with target duration
        target_duration = request.target_duration_seconds or (target_minutes * 60)
        
        # Use the new segment-based synthesis method
        synthesis_result = await voice_service.synthesize_script_segments(
            script_segments,
            target_duration_seconds=target_duration,
            voice_style=request.voice_style
        )
        
        logger.info(f"🔊 Audio synthesis complete: {synthesis_result.total_duration:.1f}s")
        logger.info(f"🎭 Speakers used: {', '.join(synthesis_result.speakers_used)}")
        
        # Add audio bumpers (intro and outro)
        logger.info("🎵 Adding audio bumpers...")
        intro_path = "/home/gdubs/copernicus-web-public/bumpers/copernicus-intro.mp3"
        outro_path = "/home/gdubs/copernicus-web-public/bumpers/copernicus-outro.mp3"
        
        final_audio = await voice_service.add_audio_bumpers(
            synthesis_result.audio_data, intro_path, outro_path
        )
        
        # Update synthesis result with bumpers
        synthesis_result.audio_data = final_audio
        
        jobs[job_id]["stage"] = "asset_generation"
        jobs[job_id]["audio_duration"] = synthesis_result.total_duration
        
        # Stage 5: Asset Generation and Upload
        logger.info("📦 Stage 5: Asset Generation and Upload")
        
        # Determine canonical filename
        canonical_info = determine_canonical_filename(request.topic, podcast_script.title)
        canonical_filename = canonical_info["filename"]
        
        logger.info(f"📝 Canonical filename: {canonical_filename}")
        
        # Generate comprehensive description
        description = await generate_comprehensive_description(
            podcast_script, paper_analyses, canonical_info
        )
        
        # Generate AI thumbnail
        from canonical_helpers import generate_canonical_thumbnail
        thumbnail_url = await generate_canonical_thumbnail(
            title=podcast_script.title,
            canonical_filename=canonical_filename
        )
        thumbnail_success = bool(thumbnail_url)
        
        # Upload audio to GCS
        audio_url = await upload_audio_to_gcs(
            audio_data=synthesis_result.audio_data,
            canonical_filename=canonical_filename,
            duration=synthesis_result.total_duration
        )
        
        # Upload description to GCS
        description_url = await upload_description_to_gcs(
            description=description,
            canonical_filename=canonical_filename
        )
        
        logger.info("✅ All assets uploaded to GCS")
        
        # Stage 6: Finalization
        jobs[job_id]["status"] = "completed"
        jobs[job_id]["stage"] = "completed"
        jobs[job_id]["result"] = {
            "canonical_filename": canonical_filename,
            "title": podcast_script.title,
            "duration": synthesis_result.total_duration,
            "audio_url": audio_url,
            "description_url": description_url,
            "thumbnail_generated": thumbnail_success,
            "speakers_used": synthesis_result.speakers_used,
            "themes": podcast_script.themes,
            "research_sources": len(research_sources),
            "citations": podcast_script.citations,
            "hashtags": podcast_script.hashtags,
            "quality_metrics": {
                "duration_accuracy": f"{(synthesis_result.estimated_vs_actual_duration['actual']/synthesis_result.estimated_vs_actual_duration['estimated']*100):.1f}%",
                "voice_segments": len(synthesis_result.segments),
                "research_depth": request.research_depth,
                "papers_analyzed": len(paper_analyses)
            }
        }
        
        logger.info(f"🎉 Production podcast generation completed for job {job_id}")
        logger.info(f"📊 Final metrics: {synthesis_result.total_duration:.1f}s, {len(research_sources)} sources, {len(paper_analyses)} analyses")
        
    except Exception as e:
        logger.error(f"❌ Production podcast generation failed for job {job_id}: {e}")
        jobs[job_id]["status"] = "failed"
        jobs[job_id]["error"] = str(e)
        jobs[job_id]["updated_at"] = datetime.now().isoformat()

async def generate_comprehensive_description(
    script: EnhancedPodcastScript,
    analyses: List[PaperAnalysis],
    canonical_info: Dict[str, Any]
) -> str:
    """
    Generate comprehensive episode description with actual content and detailed references
    """
    # Extract detailed content from script segments
    main_topics = []
    technical_insights = []
    discussion_highlights = []
    
    # Analyze script content for actual topics discussed
    for segment in script.segments:
        content = segment.get('content', '').strip()
        if len(content) > 50:  # Substantial content
            if 'research' in content.lower() or 'study' in content.lower():
                technical_insights.append(content[:150] + "...")
            elif '?' in content:  # Questions/discussions
                discussion_highlights.append(content[:120] + "...")
            else:
                main_topics.append(content[:130] + "...")
    
    # Extract key findings with more detail
    detailed_findings = []
    research_methods = []
    practical_applications = []
    
    for analysis in analyses:
        # Get detailed findings
        detailed_findings.extend(analysis.key_findings[:3])
        
        # Extract methodology information
        if hasattr(analysis, 'methodology') and analysis.methodology:
            research_methods.append(analysis.methodology[:100] + "...")
        
        # Get practical applications
        practical_applications.extend(analysis.practical_applications[:2])
    
    # Generate rich description with actual episode content
    description = f"""# {script.title}

## Episode Overview
Join Sarah, Tom, and Mary as they explore {script.title.lower()}. This episode delves into cutting-edge research, practical applications, and the future implications of this fascinating field.

{script.introduction[:300] if script.introduction else 'This episode provides an in-depth exploration of recent scientific developments and their broader implications.'}

## What You'll Learn

### Key Research Findings
{chr(10).join([f"• {finding}" for finding in detailed_findings[:4]]) if detailed_findings else '• Latest research developments and breakthrough discoveries'}

### Technical Insights Discussed
{chr(10).join([f"• {insight}" for insight in technical_insights[:3]]) if technical_insights else '• In-depth analysis of scientific methodologies and approaches'}

### Research Methodologies
{chr(10).join([f"• {method}" for method in research_methods[:2]]) if research_methods else '• Overview of experimental approaches and analytical techniques'}

## Practical Applications
{chr(10).join([f"• {app}" for app in practical_applications[:4]]) if practical_applications else '• Real-world applications and industry implications'}

## Discussion Highlights
{chr(10).join([f"• {highlight}" for highlight in discussion_highlights[:3]]) if discussion_highlights else '• Engaging conversations about scientific implications and future possibilities'}

## Research Sources
This episode synthesizes findings from {len(analyses)} peer-reviewed research papers:

{chr(10).join([f"• **{analysis.title}** - {', '.join(analysis.keywords[:3])}" for analysis in analyses[:5]])}

## Future Research Directions
{chr(10).join([f"• {direction}" for direction in [analysis.future_research_directions[0] for analysis in analyses if analysis.future_research_directions][:3]]) if any(analysis.future_research_directions for analysis in analyses) else '• Emerging trends and future research opportunities'}

## Episode Information
- **Duration**: {script.total_duration // 60 if hasattr(script, 'total_duration') and script.total_duration else 'N/A'}m {script.total_duration % 60 if hasattr(script, 'total_duration') and script.total_duration else ''}s
- **Hosts**: Sarah (Host), Tom (Expert), Mary (Questioner)
- **Format**: Conversational interview with research insights
- **Episode**: Season {canonical_info.get('season', 1)}, Episode {canonical_info.get('episode', 1)}
- **Category**: {canonical_info.get('category', 'Science')}
- **Research Papers Analyzed**: {len(analyses)}

## Connect With Us
For more episodes exploring the frontiers of science and technology, visit [copernicusai.fyi](https://copernicusai.fyi)

## Tags
{' '.join(script.hashtags[:15]) if hasattr(script, 'hashtags') and script.hashtags else '#CopernicusAI #SciencePodcast #Research #Science #Technology'}
"""
    
    return description



@app.on_event("startup")
async def startup_event():
    """Initialize production services on startup"""
    success = initialize_services()
    if not success:
        logger.warning("⚠️ Some services failed to initialize - running in degraded mode")

@app.get("/")
async def root():
    """API root with production service status"""
    service_status = {
        "research_service": research_service is not None,
        "voice_service": voice_service is not None,
        "research_pipeline": research_pipeline is not None
    }
    
    return {
        "message": "Copernicus Podcast API - Production Quality",
        "version": "2.0.0",
        "services": service_status,
        "features": [
            "Multi-paper research synthesis",
            "Theme extraction and analysis",
            "Multi-voice audio generation",
            "Quality control workflows",
            "Canonical asset management"
        ]
    }

@app.get("/health")
async def health():
    """Comprehensive health check"""
    health_status = {"status": "healthy", "services": {}}
    
    # Check research pipeline
    if research_pipeline:
        pipeline_health = await research_pipeline.health_check()
        health_status["services"]["research_sources"] = pipeline_health
    
    # Check voice service
    if voice_service:
        voice_test = await voice_service.test_voice_synthesis()
        health_status["services"]["voice_synthesis"] = voice_test["success"]
    
    # Check Google AI
    google_key = os.environ.get("GOOGLE_AI_API_KEY") or os.environ.get("GEMINI_API_KEY")
    health_status["services"]["google_ai"] = bool(google_key)
    
    return health_status

@app.post("/generate-podcast")
async def generate_podcast(request: ProductionPodcastRequest, background_tasks: BackgroundTasks):
    """Generate production-quality research-driven podcast"""
    
    # Handle legacy field mapping
    if request.subject and not request.topic:
        request.topic = request.subject
    if request.difficulty and not request.expertise_level:
        request.expertise_level = request.difficulty
    if request.speakers and not request.format_type:
        request.format_type = request.speakers
    
    job_id = str(uuid.uuid4())
    
    logger.info(f"📥 New production podcast request: {request.topic}")
    logger.info(f"🔬 Research depth: {request.research_depth}, Papers: {request.max_papers}")
    logger.info(f"🎙️ Multi-voice: {request.multi_voice}, Duration: {request.duration}")
    
    jobs[job_id] = {
        "id": job_id,
        "status": "pending",
        "stage": "initialization",
        "request": request.model_dump(),
        "created_at": datetime.now().isoformat(),
        "updated_at": datetime.now().isoformat()
    }
    
    background_tasks.add_task(process_production_podcast_generation, job_id, request)
    return {"job_id": job_id, "status": "pending", "message": "Production podcast generation started"}

@app.post("/analyze-papers")
async def analyze_papers(papers: List[ResearchPaperUpload]):
    """Analyze multiple research papers for synthesis"""
    if not research_service:
        raise HTTPException(status_code=503, detail="Research service not available")
    
    # Convert uploads to ResearchSource objects
    research_sources = []
    for paper in papers:
        source = ResearchSource(
            title=paper.title,
            authors=paper.authors,
            abstract=paper.abstract or paper.content[:500],
            url="",
            publication_date=datetime.now().isoformat(),
            source="upload",
            doi=paper.doi
        )
        research_sources.append(source)
    
    # Analyze papers
    analyses = await research_service.analyze_multiple_papers(research_sources)
    
    return {
        "analyses": [
            {
                "title": analysis.title,
                "summary": analysis.summary,
                "key_findings": analysis.key_findings,
                "implications": analysis.implications,
                "technical_complexity": analysis.technical_complexity,
                "paradigm_shift_potential": analysis.paradigm_shift_potential
            }
            for analysis in analyses
        ]
    }

@app.get("/voice-info")
async def get_voice_info():
    """Get voice configuration information"""
    if not voice_service:
        raise HTTPException(status_code=503, detail="Voice service not available")
    
    return voice_service.get_voice_info()

@app.get("/research-sources")
async def get_research_sources():
    """Get available research sources and their status"""
    if not research_pipeline:
        raise HTTPException(status_code=503, detail="Research pipeline not available")
    
    return await research_pipeline.get_source_status()

@app.get("/job/{job_id}")
async def get_job_status(job_id: str):
    """Get detailed job status with production metrics"""
    if job_id not in jobs:
        raise HTTPException(status_code=404, detail="Job not found")
    
    return {"job": jobs[job_id]}

@app.post("/test-synthesis")
async def test_synthesis(text: str = "Hello, this is a test of the production voice synthesis system.", speaker: str = "host"):
    """Test voice synthesis for development"""
    if not voice_service:
        raise HTTPException(status_code=503, detail="Voice service not available")
    
    result = await voice_service.test_voice_synthesis(speaker)
    return result

if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8003))
    logger.info(f"🚀 Starting Production Copernicus Podcast API on port {port}")
    logger.info(f"🔑 Google AI API: {'✅ Found' if os.environ.get('GOOGLE_AI_API_KEY') else '❌ Missing'}")
    logger.info(f"🎙️ Google Cloud TTS: Available via service account")
    logger.info(f"🔬 Research Sources: Multi-API integration")
    uvicorn.run(app, host="0.0.0.0", port=port)
