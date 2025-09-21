'use client'

import { useState } from 'react'
import { Send, AlertCircle, CheckCircle } from 'lucide-react'

interface User {
  id: string
  email: string
  subscriptionTier: 'free' | 'premium' | 'research'
  podcastsUsed: number
  podcastsLimit: number
}

interface CustomRequestFormProps {
  user: User | null
}

export default function CustomRequestForm({ user }: CustomRequestFormProps) {
  const [formData, setFormData] = useState({
    topic: '',
    category: 'Computer Science',
    expertiseLevel: 'intermediate',
    formatType: 'feature',
    duration: '5 minutes',
    focusAreas: '',
    additionalNotes: '',
    paperContent: '',
    paperTitle: ''
  })
  
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [submitStatus, setSubmitStatus] = useState<'idle' | 'success' | 'error'>('idle')
  const [errorMessage, setErrorMessage] = useState('')

  const categories = [
    'Computer Science',
    'Physics', 
    'Biology',
    'Chemistry',
    'Mathematics',
    'Engineering',
    'Medicine',
    'Psychology',
    'Economics',
    'Environmental Science'
  ]

  const canSubmit = () => {
    if (!user) return false
    if (user.subscriptionTier === 'free' && user.podcastsUsed >= user.podcastsLimit) {
      return false
    }
    return formData.topic.trim().length > 0
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    
    if (!canSubmit()) {
      setErrorMessage('You have reached your monthly podcast limit. Upgrade your subscription to generate more podcasts.')
      setSubmitStatus('error')
      return
    }

    setIsSubmitting(true)
    setSubmitStatus('idle')

    try {
      const requestData = {
        topic: formData.topic,
        category: formData.category,
        expertise_level: formData.expertiseLevel,
        format_type: formData.formatType,
        duration: formData.duration,
        voice_style: 'multi-voice',
        focus_areas: formData.focusAreas.split(',').map(area => area.trim()).filter(Boolean),
        include_citations: true,
        paradigm_shift_analysis: formData.formatType === 'feature',
        paper_content: formData.paperContent || null,
        paper_title: formData.paperTitle || null,
        additional_notes: formData.additionalNotes || null
      }

      const response = await fetch('/api/generate-podcast', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(requestData),
      })

      if (response.ok) {
        const result = await response.json()
        setSubmitStatus('success')
        setFormData({
          topic: '',
          category: 'Computer Science',
          expertiseLevel: 'intermediate',
          formatType: 'feature',
          duration: '5 minutes',
          focusAreas: '',
          additionalNotes: '',
          paperContent: '',
          paperTitle: ''
        })
      } else {
        const error = await response.json()
        setErrorMessage(error.detail || 'Failed to generate podcast')
        setSubmitStatus('error')
      }
    } catch (error) {
      setErrorMessage('Network error. Please try again.')
      setSubmitStatus('error')
    } finally {
      setIsSubmitting(false)
    }
  }

  const getRemainingPodcasts = () => {
    if (!user) return 0
    if (user.subscriptionTier === 'free') {
      return Math.max(0, user.podcastsLimit - user.podcastsUsed)
    }
    return 'Unlimited'
  }

  return (
    <div className="space-y-6">
      {/* Usage Status */}
      <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
        <div className="flex items-center justify-between">
          <div>
            <h3 className="font-medium text-blue-900">Monthly Podcast Usage</h3>
            <p className="text-sm text-blue-700">
              {user?.subscriptionTier === 'free' 
                ? `You have ${getRemainingPodcasts()} podcasts remaining this month`
                : 'You have unlimited podcast generation'
              }
            </p>
          </div>
          <div className="text-right">
            <div className="text-2xl font-bold text-blue-600">
              {user?.subscriptionTier === 'free' ? getRemainingPodcasts() : '∞'}
            </div>
            <div className="text-xs text-blue-500">Available</div>
          </div>
        </div>
      </div>

      {/* Request Form */}
      <form onSubmit={handleSubmit} className="space-y-6">
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          <div>
            <label htmlFor="topic" className="block text-sm font-medium text-gray-700 mb-2">
              Research Topic *
            </label>
            <input
              type="text"
              id="topic"
              value={formData.topic}
              onChange={(e) => setFormData(prev => ({ ...prev, topic: e.target.value }))}
              placeholder="e.g., Quantum Computing Breakthroughs"
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              required
            />
          </div>

          <div>
            <label htmlFor="category" className="block text-sm font-medium text-gray-700 mb-2">
              Category *
            </label>
            <select
              id="category"
              value={formData.category}
              onChange={(e) => setFormData(prev => ({ ...prev, category: e.target.value }))}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
            >
              {categories.map(category => (
                <option key={category} value={category}>{category}</option>
              ))}
            </select>
          </div>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          <div>
            <label htmlFor="expertiseLevel" className="block text-sm font-medium text-gray-700 mb-2">
              Technical Level
            </label>
            <select
              id="expertiseLevel"
              value={formData.expertiseLevel}
              onChange={(e) => setFormData(prev => ({ ...prev, expertiseLevel: e.target.value }))}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
            >
              <option value="general">General Audience</option>
              <option value="intermediate">Intermediate</option>
              <option value="expert">Expert/Professional</option>
            </select>
          </div>

          <div>
            <label htmlFor="formatType" className="block text-sm font-medium text-gray-700 mb-2">
              Format Type
            </label>
            <select
              id="formatType"
              value={formData.formatType}
              onChange={(e) => setFormData(prev => ({ ...prev, formatType: e.target.value }))}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
            >
              <option value="feature">Feature (Comprehensive)</option>
              <option value="news">News (Current Developments)</option>
              <option value="research">Research Analysis</option>
            </select>
          </div>

          <div>
            <label htmlFor="duration" className="block text-sm font-medium text-gray-700 mb-2">
              Duration
            </label>
            <select
              id="duration"
              value={formData.duration}
              onChange={(e) => setFormData(prev => ({ ...prev, duration: e.target.value }))}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
            >
              <option value="5 minutes">5 minutes</option>
              <option value="10 minutes">10 minutes</option>
              <option value="15 minutes">15 minutes</option>
              <option value="20 minutes">20 minutes</option>
            </select>
          </div>
        </div>

        <div>
          <label htmlFor="focusAreas" className="block text-sm font-medium text-gray-700 mb-2">
            Focus Areas (Optional)
          </label>
          <input
            type="text"
            id="focusAreas"
            value={formData.focusAreas}
            onChange={(e) => setFormData(prev => ({ ...prev, focusAreas: e.target.value }))}
            placeholder="e.g., machine learning, neural networks, quantum algorithms"
            className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
          />
          <p className="text-xs text-gray-500 mt-1">Separate multiple areas with commas</p>
        </div>

        <div>
          <label htmlFor="additionalNotes" className="block text-sm font-medium text-gray-700 mb-2">
            Additional Instructions (Optional)
          </label>
          <textarea
            id="additionalNotes"
            value={formData.additionalNotes}
            onChange={(e) => setFormData(prev => ({ ...prev, additionalNotes: e.target.value }))}
            placeholder="Any specific aspects, perspectives, or themes you'd like emphasized..."
            rows={3}
            className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
          />
        </div>

        {/* Research Paper Upload (Research Pro only) */}
        {user?.subscriptionTier === 'research' && (
          <div className="space-y-4 p-4 bg-purple-50 border border-purple-200 rounded-lg">
            <h4 className="font-medium text-purple-900">Research Paper Analysis (Research Pro Feature)</h4>
            
            <div>
              <label htmlFor="paperTitle" className="block text-sm font-medium text-purple-700 mb-2">
                Paper Title
              </label>
              <input
                type="text"
                id="paperTitle"
                value={formData.paperTitle}
                onChange={(e) => setFormData(prev => ({ ...prev, paperTitle: e.target.value }))}
                placeholder="Title of the research paper to analyze"
                className="w-full px-3 py-2 border border-purple-300 rounded-lg focus:ring-2 focus:ring-purple-500 focus:border-transparent"
              />
            </div>

            <div>
              <label htmlFor="paperContent" className="block text-sm font-medium text-purple-700 mb-2">
                Paper Content
              </label>
              <textarea
                id="paperContent"
                value={formData.paperContent}
                onChange={(e) => setFormData(prev => ({ ...prev, paperContent: e.target.value }))}
                placeholder="Paste the abstract, key sections, or full paper content here..."
                rows={6}
                className="w-full px-3 py-2 border border-purple-300 rounded-lg focus:ring-2 focus:ring-purple-500 focus:border-transparent"
              />
              <p className="text-xs text-purple-600 mt-1">
                The AI will analyze this paper and create a podcast discussing its key findings and implications.
              </p>
            </div>
          </div>
        )}

        {/* Submit Status */}
        {submitStatus === 'success' && (
          <div className="flex items-center space-x-2 p-4 bg-green-50 border border-green-200 rounded-lg">
            <CheckCircle className="h-5 w-5 text-green-600" />
            <div>
              <p className="font-medium text-green-900">Podcast generation started!</p>
              <p className="text-sm text-green-700">
                You'll receive an email notification when your podcast is ready.
              </p>
            </div>
          </div>
        )}

        {submitStatus === 'error' && (
          <div className="flex items-center space-x-2 p-4 bg-red-50 border border-red-200 rounded-lg">
            <AlertCircle className="h-5 w-5 text-red-600" />
            <div>
              <p className="font-medium text-red-900">Error generating podcast</p>
              <p className="text-sm text-red-700">{errorMessage}</p>
            </div>
          </div>
        )}

        {/* Submit Button */}
        <div className="flex justify-end">
          <button
            type="submit"
            disabled={!canSubmit() || isSubmitting}
            className={`flex items-center space-x-2 px-6 py-3 rounded-lg font-medium transition duration-200 ${
              canSubmit() && !isSubmitting
                ? 'bg-blue-600 hover:bg-blue-700 text-white'
                : 'bg-gray-300 text-gray-500 cursor-not-allowed'
            }`}
          >
            {isSubmitting ? (
              <>
                <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white"></div>
                <span>Generating Podcast...</span>
              </>
            ) : (
              <>
                <Send className="h-4 w-4" />
                <span>Generate Podcast</span>
              </>
            )}
          </button>
        </div>
      </form>
    </div>
  )
}
