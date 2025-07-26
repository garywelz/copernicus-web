import asyncio
import json
import os
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
import uuid

@dataclass
class JobRecord:
    job_id: str
    status: str  # "pending", "researching", "generating", "producing", "uploading", "completed", "failed"
    progress: int  # 0-100
    message: str
    request_data: Dict[str, Any]
    created_at: str
    updated_at: str
    estimated_completion: Optional[str] = None
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    processing_stages: Optional[List[str]] = None
    current_stage: Optional[str] = None

class JobManager:
    """
    In-memory job manager for tracking podcast generation jobs
    In production, this would be replaced with a database (Firestore, PostgreSQL, etc.)
    """
    
    def __init__(self):
        self.jobs: Dict[str, JobRecord] = {}
        self.max_jobs = 1000  # Keep last 1000 jobs in memory
        
        # Job status definitions
        self.status_definitions = {
            "pending": "Job queued for processing",
            "researching": "Discovering and analyzing research sources",
            "generating": "Creating podcast content with AI",
            "producing": "Generating audio and visual assets",
            "uploading": "Uploading to cloud storage",
            "completed": "Podcast generation completed successfully",
            "failed": "Job failed with error"
        }
        
        # Processing stages
        self.processing_stages = [
            "Research Discovery",
            "Content Analysis", 
            "Script Generation",
            "Audio Production",
            "Media Processing",
            "Distribution Preparation"
        ]

    def health_check(self) -> Dict[str, Any]:
        """Get job manager health status"""
        active_jobs = len([j for j in self.jobs.values() 
                          if j.status not in ["completed", "failed"]])
        
        return {
            "status": "healthy",
            "total_jobs": len(self.jobs),
            "active_jobs": active_jobs,
            "memory_usage": f"{len(self.jobs)}/{self.max_jobs}",
            "last_cleanup": datetime.utcnow().isoformat()
        }

    async def create_job(
        self, 
        job_id: str, 
        request_data: Dict[str, Any],
        status: str = "pending"
    ) -> JobRecord:
        """Create a new job record"""
        
        now = datetime.utcnow().isoformat()
        
        job = JobRecord(
            job_id=job_id,
            status=status,
            progress=0,
            message=self.status_definitions.get(status, "Job created"),
            request_data=request_data,
            created_at=now,
            updated_at=now,
            processing_stages=self.processing_stages.copy(),
            current_stage=self.processing_stages[0] if self.processing_stages else None
        )
        
        # Store job
        self.jobs[job_id] = job
        
        # Clean up old jobs if needed
        await self._cleanup_old_jobs()
        
        return job

    async def get_job(self, job_id: str) -> Optional[Dict[str, Any]]:
        """Get job by ID"""
        job = self.jobs.get(job_id)
        if job:
            return asdict(job)
        return None

    async def update_job(
        self,
        job_id: str,
        status: Optional[str] = None,
        progress: Optional[int] = None,
        message: Optional[str] = None,
        result: Optional[Dict[str, Any]] = None,
        error: Optional[str] = None,
        estimated_completion: Optional[str] = None
    ) -> bool:
        """Update job record"""
        
        job = self.jobs.get(job_id)
        if not job:
            return False
        
        # Update fields
        if status is not None:
            job.status = status
            if message is None:
                job.message = self.status_definitions.get(status, f"Status: {status}")
            
            # Update current stage based on status
            stage_mapping = {
                "researching": "Research Discovery",
                "generating": "Script Generation", 
                "producing": "Audio Production",
                "uploading": "Distribution Preparation"
            }
            job.current_stage = stage_mapping.get(status, job.current_stage)
        
        if progress is not None:
            job.progress = max(0, min(100, progress))
        
        if message is not None:
            job.message = message
        
        if result is not None:
            job.result = result
        
        if error is not None:
            job.error = error
        
        if estimated_completion is not None:
            job.estimated_completion = estimated_completion
        
        job.updated_at = datetime.utcnow().isoformat()
        
        return True

    async def list_jobs(
        self, 
        limit: int = 50, 
        status_filter: Optional[str] = None,
        user_id: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """List jobs with optional filtering"""
        
        jobs = list(self.jobs.values())
        
        # Apply filters
        if status_filter:
            jobs = [j for j in jobs if j.status == status_filter]
        
        if user_id:
            jobs = [j for j in jobs if j.request_data.get("user_id") == user_id]
        
        # Sort by creation time (newest first)
        jobs.sort(key=lambda x: x.created_at, reverse=True)
        
        # Limit results
        jobs = jobs[:limit]
        
        return [asdict(job) for job in jobs]

    async def get_job_statistics(self) -> Dict[str, Any]:
        """Get comprehensive job statistics"""
        
        if not self.jobs:
            return {
                "total_jobs": 0,
                "status_breakdown": {},
                "success_rate": 0.0,
                "average_duration": 0,
                "recent_activity": []
            }
        
        jobs = list(self.jobs.values())
        
        # Status breakdown
        status_counts = {}
        for job in jobs:
            status_counts[job.status] = status_counts.get(job.status, 0) + 1
        
        # Success rate
        completed = status_counts.get("completed", 0)
        failed = status_counts.get("failed", 0)
        total_finished = completed + failed
        success_rate = (completed / total_finished * 100) if total_finished > 0 else 0
        
        # Average duration for completed jobs
        durations = []
        for job in jobs:
            if job.status in ["completed", "failed"]:
                try:
                    created = datetime.fromisoformat(job.created_at)
                    updated = datetime.fromisoformat(job.updated_at)
                    duration = (updated - created).total_seconds() / 60  # minutes
                    durations.append(duration)
                except:
                    pass
        
        avg_duration = sum(durations) / len(durations) if durations else 0
        
        # Recent activity (last 24 hours)
        cutoff = datetime.utcnow() - timedelta(hours=24)
        recent_jobs = []
        for job in jobs:
            try:
                job_time = datetime.fromisoformat(job.created_at)
                if job_time > cutoff:
                    recent_jobs.append({
                        "job_id": job.job_id,
                        "status": job.status,
                        "subject": job.request_data.get("subject", "Unknown"),
                        "created_at": job.created_at
                    })
            except:
                pass
        
        recent_jobs.sort(key=lambda x: x["created_at"], reverse=True)
        
        return {
            "total_jobs": len(jobs),
            "status_breakdown": status_counts,
            "success_rate": round(success_rate, 1),
            "average_duration_minutes": round(avg_duration, 1),
            "recent_activity": recent_jobs[:10],  # Last 10 recent jobs
            "active_jobs": len([j for j in jobs if j.status not in ["completed", "failed"]]),
            "queue_depth": len([j for j in jobs if j.status == "pending"])
        }

    async def cancel_job(self, job_id: str) -> bool:
        """Cancel a job (if it's still pending or processing)"""
        
        job = self.jobs.get(job_id)
        if not job:
            return False
        
        if job.status in ["completed", "failed"]:
            return False  # Can't cancel completed jobs
        
        job.status = "failed"
        job.error = "Job cancelled by user"
        job.message = "Job was cancelled"
        job.progress = 0
        job.updated_at = datetime.utcnow().isoformat()
        
        return True

    async def retry_job(self, job_id: str) -> bool:
        """Retry a failed job"""
        
        job = self.jobs.get(job_id)
        if not job or job.status != "failed":
            return False
        
        # Reset job to pending state
        job.status = "pending"
        job.progress = 0
        job.message = "Job queued for retry"
        job.error = None
        job.result = None
        job.current_stage = self.processing_stages[0] if self.processing_stages else None
        job.updated_at = datetime.utcnow().isoformat()
        
        return True

    async def delete_job(self, job_id: str) -> bool:
        """Delete a job record"""
        
        if job_id in self.jobs:
            del self.jobs[job_id]
            return True
        return False

    async def get_user_jobs(self, user_id: str, limit: int = 20) -> List[Dict[str, Any]]:
        """Get jobs for a specific user"""
        
        user_jobs = []
        for job in self.jobs.values():
            if job.request_data.get("user_id") == user_id:
                user_jobs.append(job)
        
        # Sort by creation time (newest first)
        user_jobs.sort(key=lambda x: x.created_at, reverse=True)
        
        return [asdict(job) for job in user_jobs[:limit]]

    async def get_queue_status(self) -> Dict[str, Any]:
        """Get current processing queue status"""
        
        queue_jobs = []
        processing_jobs = []
        
        for job in self.jobs.values():
            if job.status == "pending":
                queue_jobs.append({
                    "job_id": job.job_id,
                    "subject": job.request_data.get("subject", "Unknown"),
                    "created_at": job.created_at,
                    "estimated_start": self._estimate_start_time(job)
                })
            elif job.status in ["researching", "generating", "producing", "uploading"]:
                processing_jobs.append({
                    "job_id": job.job_id,
                    "subject": job.request_data.get("subject", "Unknown"),
                    "status": job.status,
                    "progress": job.progress,
                    "current_stage": job.current_stage,
                    "estimated_completion": job.estimated_completion
                })
        
        return {
            "queue_length": len(queue_jobs),
            "processing_count": len(processing_jobs),
            "queued_jobs": sorted(queue_jobs, key=lambda x: x["created_at"]),
            "processing_jobs": processing_jobs,
            "estimated_queue_time": len(queue_jobs) * 10  # Rough estimate: 10 min per job
        }

    def _estimate_start_time(self, job: JobRecord) -> str:
        """Estimate when a queued job will start processing"""
        
        # Count jobs ahead in queue
        jobs_ahead = 0
        for other_job in self.jobs.values():
            if (other_job.status == "pending" and 
                other_job.created_at < job.created_at):
                jobs_ahead += 1
        
        # Estimate start time (assuming 10 minutes per job)
        estimated_minutes = jobs_ahead * 10
        estimated_start = datetime.utcnow() + timedelta(minutes=estimated_minutes)
        
        return estimated_start.isoformat()

    async def _cleanup_old_jobs(self):
        """Clean up old jobs to prevent memory bloat"""
        
        if len(self.jobs) <= self.max_jobs:
            return
        
        # Sort jobs by creation time
        sorted_jobs = sorted(
            self.jobs.items(), 
            key=lambda x: x[1].created_at, 
            reverse=True
        )
        
        # Keep only the most recent jobs
        jobs_to_keep = dict(sorted_jobs[:self.max_jobs])
        
        # Update jobs dict
        self.jobs = jobs_to_keep

    async def export_job_data(self, job_id: str) -> Optional[Dict[str, Any]]:
        """Export complete job data for backup/analysis"""
        
        job = self.jobs.get(job_id)
        if not job:
            return None
        
        return {
            "job_record": asdict(job),
            "export_timestamp": datetime.utcnow().isoformat(),
            "export_version": "1.0"
        }

    async def import_job_data(self, job_data: Dict[str, Any]) -> bool:
        """Import job data from backup"""
        
        try:
            job_record_data = job_data.get("job_record", {})
            
            job = JobRecord(
                job_id=job_record_data["job_id"],
                status=job_record_data["status"],
                progress=job_record_data["progress"],
                message=job_record_data["message"],
                request_data=job_record_data["request_data"],
                created_at=job_record_data["created_at"],
                updated_at=job_record_data["updated_at"],
                estimated_completion=job_record_data.get("estimated_completion"),
                result=job_record_data.get("result"),
                error=job_record_data.get("error"),
                processing_stages=job_record_data.get("processing_stages"),
                current_stage=job_record_data.get("current_stage")
            )
            
            self.jobs[job.job_id] = job
            return True
        
        except Exception as e:
            print(f"Error importing job data: {e}")
            return False

    def get_job_progress_details(self, job_id: str) -> Optional[Dict[str, Any]]:
        """Get detailed progress information for a job"""
        
        job = self.jobs.get(job_id)
        if not job:
            return None
        
        # Calculate stage progress
        stage_progress = {}
        if job.processing_stages and job.current_stage:
            try:
                current_index = job.processing_stages.index(job.current_stage)
                total_stages = len(job.processing_stages)
                
                for i, stage in enumerate(job.processing_stages):
                    if i < current_index:
                        stage_progress[stage] = 100
                    elif i == current_index:
                        stage_progress[stage] = job.progress
                    else:
                        stage_progress[stage] = 0
            except ValueError:
                pass
        
        return {
            "job_id": job.job_id,
            "overall_progress": job.progress,
            "current_stage": job.current_stage,
            "stage_progress": stage_progress,
            "status": job.status,
            "message": job.message,
            "estimated_completion": job.estimated_completion,
            "processing_stages": job.processing_stages
        }
