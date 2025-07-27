'use client';

import React, { useState } from 'react';

interface PromptFormState {
  subject: string;
  category: string; // Required: Biology, Chemistry, Computer Science, Mathematics, Physics
  duration: string;
  speakers: string;
  difficulty: string;
  additionalNotes: string;
}

const initialFormState: PromptFormState = {
  subject: '',
  category: '', // Required field for canonical naming
  duration: '',
  speakers: '',
  difficulty: '',
  additionalNotes: '',
};

export default function CreatePodcastPage() {
  const [form, setForm] = useState<PromptFormState>(initialFormState);
  const [submitted, setSubmitted] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [jobId, setJobId] = useState<string | null>(null);
  const [jobStatus, setJobStatus] = useState<string>('idle');
  const [links, setLinks] = useState<string[]>(['']);
  const [documents, setDocuments] = useState<File[]>([]);

  const handleChange = (e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement | HTMLSelectElement>) => {
    const { name, value } = e.target;
    setForm((prev) => ({ ...prev, [name]: value }));
  };

  const handleLinkChange = (idx: number, value: string) => {
    setLinks((prev) => {
      const newLinks = [...prev];
      newLinks[idx] = value;
      return newLinks;
    });
  };

  const addLinkField = () => setLinks((prev) => [...prev, '']);
  const removeLinkField = (idx: number) => setLinks((prev) => prev.filter((_, i) => i !== idx));

  const handleDocumentChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files) {
      setDocuments(Array.from(e.target.files));
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError(null);
    setSubmitted(false);
    
    try {
      // Create FormData for API submission
      const formData = new FormData();
      formData.append('subject', form.subject);
      formData.append('duration', form.duration);
      formData.append('speakers', form.speakers);
      formData.append('difficulty', form.difficulty);
      formData.append('additionalNotes', form.additionalNotes);
      formData.append('links', JSON.stringify(links.filter(link => link.trim())));
      
      // Add uploaded documents
      documents.forEach((doc, idx) => {
        formData.append(`document_${idx}`, doc);
      });

      // Submit to our generation API
      const response = await fetch('/api/generate', {
        method: 'POST',
        body: formData,
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.error || 'Failed to submit podcast generation request');
      }

      const result = await response.json();
      setJobId(result.jobId);
      setJobStatus('pending');
      setSubmitted(true);
      
      // Start polling for job status
      pollJobStatus(result.jobId);
      
      // Reset form after successful submission
      setTimeout(() => {
        setForm(initialFormState);
        setLinks(['']);
        setDocuments([]);
      }, 1000);
      
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to submit podcast generation request. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  // Poll job status
  const pollJobStatus = async (jobId: string) => {
    const maxPolls = 60; // 5 minutes max
    let pollCount = 0;
    
    const poll = async () => {
      try {
        const response = await fetch(`/api/generate?jobId=${jobId}`);
        if (response.ok) {
          const data = await response.json();
          const job = data.job;
          
          setJobStatus(job.status);
          
          if (job.status === 'completed' || job.status === 'failed') {
            if (job.status === 'failed') {
              setError(job.error || 'Podcast generation failed');
            }
            return; // Stop polling
          }
          
          // Continue polling if still processing
          if (job.status === 'pending' || job.status === 'processing') {
            pollCount++;
            if (pollCount < maxPolls) {
              setTimeout(poll, 5000); // Poll every 5 seconds
            } else {
              setError('Podcast generation timed out. Please try again.');
            }
          }
        }
      } catch (err) {
        console.error('Error polling job status:', err);
      }
    };
    
    // Start polling after 2 seconds
    setTimeout(poll, 2000);
  };

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <div className="bg-white shadow-sm border-b">
        <div className="max-w-4xl mx-auto px-4 py-6">
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-3xl font-bold text-gray-900">Create AI Podcast</h1>
              <p className="text-gray-600 mt-2">Generate research-focused podcast episodes from your prompts</p>
            </div>
            <a 
              href="/" 
              className="text-blue-600 hover:text-blue-800 font-medium"
            >
              ← Back to Episodes
            </a>
          </div>
        </div>
      </div>

      {/* Main Content */}
      <div className="max-w-2xl mx-auto py-8 px-4">
        
        {/* Info Banner */}
        <div className="mb-6 bg-blue-50 border border-blue-200 rounded-lg p-4">
          <div className="flex items-start">
            <div className="flex-shrink-0">
              <svg className="h-5 w-5 text-blue-400 mt-0.5" fill="currentColor" viewBox="0 0 20 20">
                <path fillRule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7-4a1 1 0 11-2 0 1 1 0 012 0zM9 9a1 1 0 000 2v3a1 1 0 001 1h1a1 1 0 100-2v-3a1 1 0 00-1-1H9z" clipRule="evenodd" />
              </svg>
            </div>
            <div className="ml-3">
              <h3 className="text-sm font-medium text-blue-800">AI-Powered Research Podcasts</h3>
              <p className="text-sm text-blue-700 mt-1">
                Our AI draws from ArXiv, recent publications, and web sources to create comprehensive research discussions. 
                You can also provide specific papers, documents, or links to focus the content.
              </p>
            </div>
          </div>
        </div>

        {/* Form */}
        <div className="bg-white rounded-lg shadow-sm border p-6">
          <form onSubmit={handleSubmit} className="space-y-6">
            
            {/* Subject */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Research Topic *
              </label>
              <input
                type="text"
                name="subject"
                value={form.subject}
                onChange={handleChange}
                required
                className="w-full border border-gray-300 rounded-md px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                placeholder="e.g., Quantum Error Correction, CRISPR Gene Editing, Neural Networks"
              />
            </div>

            {/* Subject Category - Required for Canonical Naming */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Subject Category *
                <span className="text-xs text-gray-500 ml-2">(Required for canonical naming)</span>
              </label>
              <select
                name="category"
                value={form.category}
                onChange={handleChange}
                required
                className="w-full border border-gray-300 rounded-md px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              >
                <option value="">Select subject category...</option>
                <option value="biology">Biology</option>
                <option value="chemistry">Chemistry</option>
                <option value="computer-science">Computer Science</option>
                <option value="mathematics">Mathematics</option>
                <option value="physics">Physics</option>
              </select>
              <p className="text-xs text-gray-500 mt-1">
                This determines the canonical filename (e.g., ever-compsci-250028, ever-phys-250032)
              </p>
            </div>

            {/* Duration */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Episode Duration *
              </label>
              <select
                name="duration"
                value={form.duration}
                onChange={handleChange}
                required
                className="w-full border border-gray-300 rounded-md px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              >
                <option value="">Select duration...</option>
                <option value="5">5 minutes (Quick overview)</option>
                <option value="10">10 minutes (Standard briefing)</option>
                <option value="15">15 minutes (Detailed discussion)</option>
                <option value="20">20 minutes (Comprehensive analysis)</option>
                <option value="30">30 minutes (Deep dive)</option>
              </select>
            </div>

            {/* Speakers */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Speaker Configuration *
              </label>
              <select
                name="speakers"
                value={form.speakers}
                onChange={handleChange}
                required
                className="w-full border border-gray-300 rounded-md px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              >
                <option value="">Select format...</option>
                <option value="single">Single narrator</option>
                <option value="interview">Interview format (2 speakers)</option>
                <option value="panel">Panel discussion (3-4 speakers)</option>
                <option value="debate">Debate format (2 opposing views)</option>
              </select>
            </div>

            {/* Difficulty */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Technical Level *
              </label>
              <select
                name="difficulty"
                value={form.difficulty}
                onChange={handleChange}
                required
                className="w-full border border-gray-300 rounded-md px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              >
                <option value="">Select level...</option>
                <option value="General">General audience (accessible explanations)</option>
                <option value="Undergraduate">Undergraduate level</option>
                <option value="Graduate">Graduate/Research level</option>
                <option value="Expert">Expert/Professional level</option>
              </select>
            </div>

            {/* Source Links */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Source Links (Optional)
              </label>
              <p className="text-sm text-gray-500 mb-3">
                Add specific papers, articles, or resources to focus the discussion
              </p>
              {links.map((link, idx) => (
                <div key={idx} className="flex items-center mb-2">
                  <input
                    type="url"
                    value={link}
                    onChange={e => handleLinkChange(idx, e.target.value)}
                    className="flex-1 border border-gray-300 rounded-md px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                    placeholder="https://arxiv.org/abs/1234.5678 or other research source"
                  />
                  {links.length > 1 && (
                    <button 
                      type="button" 
                      onClick={() => removeLinkField(idx)} 
                      className="ml-2 text-red-600 hover:text-red-800 font-bold text-lg"
                    >
                      ×
                    </button>
                  )}
                </div>
              ))}
              <button 
                type="button" 
                onClick={addLinkField} 
                className="text-blue-600 hover:text-blue-800 text-sm font-medium"
              >
                + Add another source
              </button>
            </div>

            {/* Document Upload */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Upload Documents (Optional)
              </label>
              <input
                type="file"
                accept=".pdf,.doc,.docx,.txt"
                multiple
                onChange={handleDocumentChange}
                className="w-full border border-gray-300 rounded-md px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              />
              {documents.length > 0 && (
                <div className="mt-2 text-sm text-gray-600">
                  <p className="font-medium">Selected files:</p>
                  {documents.map((file, idx) => (
                    <div key={idx} className="ml-2">• {file.name}</div>
                  ))}
                </div>
              )}
            </div>

            {/* Additional Notes */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Additional Instructions (Optional)
              </label>
              <textarea
                name="additionalNotes"
                value={form.additionalNotes}
                onChange={handleChange}
                className="w-full border border-gray-300 rounded-md px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                placeholder="Special themes, perspectives, or specific aspects to emphasize..."
                rows={3}
              />
            </div>

            {/* Submit Button */}
            <div className="pt-4">
              <button
                type="submit"
                disabled={loading}
                className="w-full bg-blue-600 text-white py-3 px-4 rounded-md font-medium hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
              >
                {loading ? (
                  <div className="flex items-center justify-center">
                    <svg className="animate-spin -ml-1 mr-3 h-5 w-5 text-white" fill="none" viewBox="0 0 24 24">
                      <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                      <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                    </svg>
                    Generating Podcast...
                  </div>
                ) : (
                  jobStatus === 'pending' || jobStatus === 'processing' ? 'Generating...' : 'Generate AI Podcast'
                )}
              </button>
            </div>

            {/* Status Messages */}
            {error && (
              <div className="bg-red-50 border border-red-200 rounded-md p-4">
                <div className="flex">
                  <svg className="h-5 w-5 text-red-400" fill="currentColor" viewBox="0 0 20 20">
                    <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clipRule="evenodd" />
                  </svg>
                  <div className="ml-3">
                    <p className="text-sm text-red-800">{error}</p>
                  </div>
                </div>
              </div>
            )}

            {submitted && (
              <div className={`border rounded-md p-4 ${
                jobStatus === 'completed' ? 'bg-green-50 border-green-200' :
                jobStatus === 'failed' ? 'bg-red-50 border-red-200' :
                'bg-blue-50 border-blue-200'
              }`}>
                <div className="flex">
                  {jobStatus === 'completed' ? (
                    <svg className="h-5 w-5 text-green-400" fill="currentColor" viewBox="0 0 20 20">
                      <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clipRule="evenodd" />
                    </svg>
                  ) : jobStatus === 'failed' ? (
                    <svg className="h-5 w-5 text-red-400" fill="currentColor" viewBox="0 0 20 20">
                      <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clipRule="evenodd" />
                    </svg>
                  ) : (
                    <svg className="animate-spin h-5 w-5 text-blue-400" fill="none" viewBox="0 0 24 24">
                      <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                      <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                    </svg>
                  )}
                  <div className="ml-3">
                    <p className={`text-sm ${
                      jobStatus === 'completed' ? 'text-green-800' :
                      jobStatus === 'failed' ? 'text-red-800' :
                      'text-blue-800'
                    }`}>
                      {jobStatus === 'pending' && 'Podcast generation request submitted! Initializing...'}
                      {jobStatus === 'processing' && 'AI is generating your podcast episode. This may take 5-10 minutes...'}
                      {jobStatus === 'completed' && 'Podcast generated successfully! Your episode is being processed for distribution.'}
                      {jobStatus === 'failed' && 'Podcast generation failed. Please try again with different parameters.'}
                    </p>
                    {jobId && (
                      <p className="text-xs text-gray-600 mt-1">
                        Job ID: {jobId}
                      </p>
                    )}
                  </div>
                </div>
              </div>
            )}
          </form>
        </div>
      </div>
    </div>
  );
}
