import { NextRequest, NextResponse } from 'next/server';

// Force dynamic rendering for this API route
export const dynamic = 'force-dynamic';

interface PodcastGenerationRequest {
  subject: string;
  duration: string;
  speakers: string;
  difficulty: string;
  additionalNotes?: string;
  links?: string[];
  userId?: string;
}

interface GenerationJob {
  id: string;
  status: 'pending' | 'processing' | 'completed' | 'failed';
  request: PodcastGenerationRequest;
  createdAt: string;
  updatedAt: string;
  cloudRunJobId?: string;
  result?: {
    audioUrl?: string;
    transcriptUrl?: string;
    thumbnailUrl?: string;
    rssEntryUrl?: string;
  };
  audioUrl?: string;
  transcriptUrl?: string;
  thumbnailUrl?: string;
  rssEntryUrl?: string;
  error?: string;
}

// In-memory job storage (replace with database in production)
const jobs = new Map<string, GenerationJob>();

// Backend URL (local for testing, Cloud Run for production)
const BACKEND_URL = process.env.CLOUD_RUN_URL || 'http://localhost:8002';

// Submit job to Google AI backend
async function submitToCloudRun(requestData: any): Promise<any> {
  try {
    console.log(`🚀 Submitting to Google AI backend: ${BACKEND_URL}/generate-podcast-legacy`);
    
    // Create AbortController for timeout handling
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), 60000); // 60 second timeout
    
    const response = await fetch(`${BACKEND_URL}/generate-podcast-legacy`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(requestData),
      signal: controller.signal,
    });
    
    clearTimeout(timeoutId);

    if (!response.ok) {
      const errorText = await response.text();
      throw new Error(`Google AI Backend error: ${response.status} ${response.statusText} - ${errorText}`);
    }

    const result = await response.json();
    console.log(`✅ Google AI backend response:`, result);
    return result;
  } catch (error: any) {
    if (error.name === 'AbortError') {
      console.error('❌ Google AI backend request timed out after 60 seconds');
      throw new Error('Google AI backend request timed out. The backend may be processing - check job status.');
    }
    console.error('❌ Error submitting to Google AI backend:', error);
    throw error;
  }
}

export async function POST(request: NextRequest) {
  try {
    const formData = await request.formData();
    
    // Extract form fields
    const subject = formData.get('subject') as string;
    const duration = formData.get('duration') as string;
    const speakers = formData.get('speakers') as string;
    const difficulty = formData.get('difficulty') as string;
    const additionalNotes = formData.get('additionalNotes') as string;
    const linksJson = formData.get('links') as string;
    
    // Parse links
    let links: string[] = [];
    if (linksJson) {
      try {
        links = JSON.parse(linksJson);
      } catch (e) {
        console.error('Failed to parse links:', e);
      }
    }

    // Extract uploaded documents
    const documents: File[] = [];
    const entries = Array.from(formData.entries());
    for (const [key, value] of entries) {
      if (key.startsWith('document_') && value instanceof File) {
        documents.push(value);
      }
    }

    // Validate required fields
    if (!subject || !duration || !speakers || !difficulty) {
      return NextResponse.json(
        { error: 'Missing required fields: subject, duration, speakers, difficulty' },
        { status: 400 }
      );
    }

    // Generate unique job ID
    const jobId = `job_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;

    // Create job record
    const job: GenerationJob = {
      id: jobId,
      status: 'pending',
      request: {
        subject,
        duration,
        speakers,
        difficulty,
        additionalNotes: additionalNotes || '',
        links: links.filter(link => link.trim()),
      },
      createdAt: new Date().toISOString(),
      updatedAt: new Date().toISOString(),
    };

    // Store job in memory (replace with database)
    jobs.set(jobId, job);

    console.log(`Created podcast generation job ${jobId}:`, {
      subject,
      duration,
      speakers,
      difficulty,
      linksCount: links.length,
      documentsCount: documents.length,
    });

    // Submit job to Google Cloud Run backend
    try {
      const cloudRunResponse = await submitToCloudRun({
        subject,
        duration,
        speakers,
        difficulty,
        additional_notes: additionalNotes || '',
        source_links: links.filter(link => link.trim())
      });

      // The minimal backend returns {job_id, status} directly
      if (!cloudRunResponse.job_id) {
        throw new Error('Cloud Run submission failed - no job_id returned');
      }

      console.log(`Successfully submitted job ${jobId} to Cloud Run:`, cloudRunResponse);
      
      // Update our job with the Cloud Run job ID
      const updatedJob = jobs.get(jobId);
      if (updatedJob) {
        updatedJob.cloudRunJobId = cloudRunResponse.job_id;
        jobs.set(jobId, updatedJob);
      }
    } catch (error) {
      console.error(`Failed to submit job ${jobId} to Cloud Run:`, error);
      // Update job status to failed
      const failedJob = jobs.get(jobId);
      if (failedJob) {
        failedJob.status = 'failed';
        failedJob.error = `Cloud Run submission failed: ${error}`;
        failedJob.updatedAt = new Date().toISOString();
        jobs.set(jobId, failedJob);
      }
    }

    return NextResponse.json({
      success: true,
      jobId,
      message: 'Podcast generation job created successfully',
      estimatedCompletionTime: '5-10 minutes',
    });

  } catch (error) {
    console.error('Error creating podcast generation job:', error);
    return NextResponse.json(
      { error: 'Internal server error' },
      { status: 500 }
    );
  }
}

export async function GET(request: NextRequest) {
  const { searchParams } = new URL(request.url);
  const jobId = searchParams.get('jobId');

  if (!jobId) {
    // Return all jobs (for admin/debugging)
    const allJobs = Array.from(jobs.values()).sort(
      (a, b) => new Date(b.createdAt).getTime() - new Date(a.createdAt).getTime()
    );
    return NextResponse.json({ jobs: allJobs });
  }

  const job = jobs.get(jobId);
  if (!job) {
    return NextResponse.json(
      { error: 'Job not found' },
      { status: 404 }
    );
  }

  // If we have a Google AI backend job ID, poll the backend for status
  if (job.cloudRunJobId) {
    try {
      console.log(`🔍 Polling Google AI backend for job status: ${job.cloudRunJobId}`);
      
      const response = await fetch(`${BACKEND_URL}/job/${job.cloudRunJobId}`, {
        method: 'GET',
        headers: {
          'Content-Type': 'application/json',
        },
      });

      if (response.ok) {
        const backendResult = await response.json();
        const backendJob = backendResult.job;
        
        console.log(`✅ Google AI backend job status:`, backendJob.status);
        
        // Update our job with backend status
        job.status = backendJob.status;
        job.updatedAt = new Date().toISOString();
        
        // If completed, copy the result
        if (backendJob.status === 'completed' && backendJob.result) {
          job.result = {
            audioUrl: backendJob.result.audio_url,
            transcriptUrl: backendJob.result.script ? `data:text/plain;base64,${btoa(backendJob.result.script)}` : undefined,
            thumbnailUrl: backendJob.result.thumbnail_url,
            rssEntryUrl: undefined, // Not provided by Google AI backend
          };
          
          // Store additional metadata
          job.audioUrl = backendJob.result.audio_url;
          job.transcriptUrl = job.result.transcriptUrl;
          job.thumbnailUrl = backendJob.result.thumbnail_url;
        }
        
        // If failed, copy the error
        if (backendJob.status === 'failed') {
          job.error = backendJob.error || 'Google AI backend processing failed';
        }
        
        // Update job in storage
        jobs.set(jobId, job);
        
      } else {
        console.error(`❌ Failed to poll Google AI backend: ${response.status} ${response.statusText}`);
        // Don't update job status if backend polling fails - keep existing status
      }
    } catch (error) {
      console.error('❌ Error polling Google AI backend:', error);
      // Don't update job status if backend polling fails - keep existing status
    }
  }

  return NextResponse.json({ job });
}

// Simulate processing for development
async function simulateProcessing(jobId: string) {
  const job = jobs.get(jobId);
  if (!job) return;

  // Update to processing
  job.status = 'processing';
  job.updatedAt = new Date().toISOString();
  jobs.set(jobId, job);

  // Simulate processing time (3-8 seconds)
  const processingTime = 3000 + Math.random() * 5000;
  
  setTimeout(() => {
    const updatedJob = jobs.get(jobId);
    if (!updatedJob) return;

    // Simulate success/failure (90% success rate)
    const success = Math.random() > 0.1;

    if (success) {
      updatedJob.status = 'completed';
      updatedJob.result = {
        audioUrl: `https://storage.googleapis.com/regal-scholar-453620-r7-podcast-storage/generated/audio/${jobId}.mp3`,
        transcriptUrl: `https://storage.googleapis.com/regal-scholar-453620-r7-podcast-storage/generated/transcripts/${jobId}.md`,
        thumbnailUrl: `https://storage.googleapis.com/regal-scholar-453620-r7-podcast-storage/generated/thumbnails/${jobId}-thumb.jpg`,
        rssEntryUrl: `https://storage.googleapis.com/regal-scholar-453620-r7-podcast-storage/generated/rss/${jobId}.xml`,
      };
    } else {
      updatedJob.status = 'failed';
      updatedJob.error = 'Processing failed due to insufficient source material or technical error';
    }

    updatedJob.updatedAt = new Date().toISOString();
    jobs.set(jobId, updatedJob);

    console.log(`Job ${jobId} completed with status: ${updatedJob.status}`);
  }, processingTime);
}
