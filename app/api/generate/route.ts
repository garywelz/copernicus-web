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
  error?: string;
}

// In-memory job storage (replace with database in production)
const jobs = new Map<string, GenerationJob>();

// Cloud Run backend URL (set via environment variable)
const CLOUD_RUN_URL = process.env.CLOUD_RUN_URL || 'https://copernicus-podcast-api-phzp4ie2sq-uc.a.run.app';

// Submit job to Cloud Run backend
async function submitToCloudRun(requestData: any): Promise<any> {
  try {
    const response = await fetch(`${CLOUD_RUN_URL}/generate-podcast`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(requestData),
    });

    if (!response.ok) {
      throw new Error(`Cloud Run API error: ${response.status} ${response.statusText}`);
    }

    const result = await response.json();
    return result;
  } catch (error) {
    console.error('Error submitting to Cloud Run:', error);
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
