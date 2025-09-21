'use client'

import { useState } from 'react'

export default function CreatePodcast() {
  const [formData, setFormData] = useState({
    subject: '',
    duration: '10 minutes',
    speakers: 'multi-voice',
    difficulty: 'intermediate',
    category: 'Computer Science',
    podcast_type: 'feature',
    additional_notes: '',
    source_links: ''
  })
  
  const [isGenerating, setIsGenerating] = useState(false)
  const [result, setResult] = useState<any>(null)
  const [error, setError] = useState<string | null>(null)

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setIsGenerating(true)
    setError(null)
    setResult(null)

    try {
      const response = await fetch('/api/generate', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          ...formData,
          source_links: formData.source_links ? formData.source_links.split('\n').filter(link => link.trim()) : []
        }),
      })

      const data = await response.json()

      if (!response.ok) {
        throw new Error(data.error || 'Failed to generate podcast')
      }

      setResult(data)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'An error occurred')
    } finally {
      setIsGenerating(false)
    }
  }

  const handleInputChange = (e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement | HTMLSelectElement>) => {
    const { name, value } = e.target
    setFormData(prev => ({
      ...prev,
      [name]: value
    }))
  }

  return (
    <div className="min-h-screen bg-background py-8">
      <div className="container mx-auto px-4 max-w-2xl">
        <h1 className="text-3xl font-bold mb-8 text-center">🎙️ Create New Podcast</h1>
        
        <form onSubmit={handleSubmit} className="space-y-6">
          <div>
            <label htmlFor="subject" className="block text-sm font-medium mb-2">
              Subject *
            </label>
            <input
              type="text"
              id="subject"
              name="subject"
              value={formData.subject}
              onChange={handleInputChange}
              required
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
              placeholder="e.g., Quantum Computing, Climate Change, AI Ethics"
            />
          </div>

          <div>
            <label htmlFor="duration" className="block text-sm font-medium mb-2">
              Duration
            </label>
            <select
              id="duration"
              name="duration"
              value={formData.duration}
              onChange={handleInputChange}
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
            >
              <option value="5 minutes">5 minutes</option>
              <option value="10 minutes">10 minutes</option>
              <option value="15 minutes">15 minutes</option>
              <option value="20 minutes">20 minutes</option>
            </select>
          </div>

          <div>
            <label htmlFor="speakers" className="block text-sm font-medium mb-2">
              Speakers
            </label>
            <select
              id="speakers"
              name="speakers"
              value={formData.speakers}
              onChange={handleInputChange}
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
            >
              <option value="multi-voice">Multi-Voice (Host, Expert, Questioner)</option>
              <option value="single-voice">Single Voice</option>
            </select>
          </div>

          <div>
            <label htmlFor="difficulty" className="block text-sm font-medium mb-2">
              Difficulty Level
            </label>
            <select
              id="difficulty"
              name="difficulty"
              value={formData.difficulty}
              onChange={handleInputChange}
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
            >
              <option value="beginner">Beginner</option>
              <option value="intermediate">Intermediate</option>
              <option value="advanced">Advanced</option>
            </select>
          </div>

          <div>
            <label htmlFor="category" className="block text-sm font-medium mb-2">
              Subject Category *
            </label>
            <select
              id="category"
              name="category"
              value={formData.category}
              onChange={handleInputChange}
              required
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
            >
              <option value="Biology">Biology</option>
              <option value="Chemistry">Chemistry</option>
              <option value="Computer Science">Computer Science</option>
              <option value="Mathematics">Mathematics</option>
              <option value="Physics">Physics</option>
            </select>
            <p className="text-xs text-gray-500 mt-1">
              This determines the canonical filename (e.g., ever-compsci-250028, ever-phys-250032)
            </p>
          </div>

          <div>
            <label htmlFor="podcast_type" className="block text-sm font-medium mb-2">
              Podcast Type
            </label>
            <select
              id="podcast_type"
              name="podcast_type"
              value={formData.podcast_type}
              onChange={handleInputChange}
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
            >
              <option value="feature">Feature (In-depth Analysis)</option>
              <option value="news">News (Recent Developments)</option>
            </select>
          </div>

          <div>
            <label htmlFor="additional_notes" className="block text-sm font-medium mb-2">
              Additional Notes
            </label>
            <textarea
              id="additional_notes"
              name="additional_notes"
              value={formData.additional_notes}
              onChange={handleInputChange}
              rows={3}
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
              placeholder="Any specific requirements or focus areas..."
            />
          </div>

          <div>
            <label htmlFor="source_links" className="block text-sm font-medium mb-2">
              Source Links (one per line)
            </label>
            <textarea
              id="source_links"
              name="source_links"
              value={formData.source_links}
              onChange={handleInputChange}
              rows={3}
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
              placeholder="https://example.com/research-paper&#10;https://example.com/news-article"
            />
          </div>

          <button
            type="submit"
            disabled={isGenerating}
            className="w-full bg-blue-600 text-white py-3 px-4 rounded-md hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-500 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {isGenerating ? '🎙️ Generating Podcast...' : '🚀 Generate Podcast'}
          </button>
        </form>

        {error && (
          <div className="mt-6 p-4 bg-red-100 border border-red-400 text-red-700 rounded-md">
            <h3 className="font-semibold">Error:</h3>
            <p>{error}</p>
          </div>
        )}

        {result && (
          <div className="mt-6 p-4 bg-green-100 border border-green-400 text-green-700 rounded-md">
            <h3 className="font-semibold">✅ Podcast Generation Started!</h3>
            <p><strong>Job ID:</strong> {result.job_id}</p>
            <p><strong>Status:</strong> {result.status}</p>
            <p className="mt-2 text-sm">
              Your podcast is being generated. This may take a few minutes. 
              Check back later or use the job ID to track progress.
            </p>
          </div>
        )}
      </div>
    </div>
  )
}
