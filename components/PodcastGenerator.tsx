// components/PodcastGenerator.tsx
// User interface for generating custom podcast episodes

import React, { useState } from 'react';

interface PodcastGeneratorProps {
  onGenerate: (request: PodcastRequest) => void;
  isGenerating: boolean;
}

interface PodcastRequest {
  prompt: string;
  title: string;
  description: string;
  category: string;
  tone: 'educational' | 'conversational' | 'technical' | 'accessible';
  length_minutes: number;
  voice_preference: 'default' | 'male' | 'female' | 'multi-voice';
  include_intro: boolean;
  include_outro: boolean;
  citations: boolean;
}

const CATEGORY_OPTIONS = [
  { value: 'biology', label: 'Biology', icon: '🧬' },
  { value: 'chemistry', label: 'Chemistry', icon: '⚗️' },
  { value: 'physics', label: 'Physics', icon: '⚛️' },
  { value: 'mathematics', label: 'Mathematics', icon: '📐' },
  { value: 'computer-science', label: 'Computer Science', icon: '💻' },
  { value: 'science', label: 'General Science', icon: '🔬' },
  { value: 'news', label: 'Science News', icon: '📰' }
];

const TONE_OPTIONS = [
  { value: 'educational', label: 'Educational', description: 'Academic and informative' },
  { value: 'conversational', label: 'Conversational', description: 'Friendly and engaging' },
  { value: 'technical', label: 'Technical', description: 'Detailed and precise' },
  { value: 'accessible', label: 'Accessible', description: 'Easy to understand' }
];

const EXAMPLE_PROMPTS = [
  {
    category: 'biology',
    prompt: 'Explain CRISPR gene editing and its recent applications in treating genetic diseases',
    title: 'CRISPR: Revolutionary Gene Editing'
  },
  {
    category: 'physics',
    prompt: 'Discuss the latest developments in quantum computing and their implications for cryptography',
    title: 'Quantum Computing: Breaking the Code'
  },
  {
    category: 'chemistry',
    prompt: 'Explore green chemistry principles and sustainable molecular design',
    title: 'Green Chemistry: Sustainable Molecular Design'
  },
  {
    category: 'mathematics',
    prompt: 'Explain the Riemann Hypothesis and its significance in number theory',
    title: 'The Riemann Hypothesis: Mathematical Mystery'
  }
];

export default function PodcastGenerator({ onGenerate, isGenerating }: PodcastGeneratorProps) {
  const [request, setRequest] = useState<PodcastRequest>({
    prompt: '',
    title: '',
    description: '',
    category: 'science',
    tone: 'educational',
    length_minutes: 10,
    voice_preference: 'default',
    include_intro: true,
    include_outro: true,
    citations: true
  });

  const [showAdvanced, setShowAdvanced] = useState(false);
  const [currentStep, setCurrentStep] = useState(1);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    onGenerate(request);
  };

  const loadExample = (example: typeof EXAMPLE_PROMPTS[0]) => {
    setRequest(prev => ({
      ...prev,
      prompt: example.prompt,
      title: example.title,
      category: example.category,
      description: `An exploration of ${example.title.toLowerCase()}, examining the latest developments and their implications for the future of science and technology.`
    }));
  };

  const isFormValid = request.prompt.trim() && request.title.trim() && request.category;

  return (
    <div className="max-w-4xl mx-auto p-6">
      <div className="bg-white rounded-lg shadow-lg">
        {/* Header */}
        <div className="bg-gradient-to-r from-blue-600 to-purple-600 text-white p-6 rounded-t-lg">
          <h1 className="text-3xl font-bold mb-2">🎙️ Create Your Podcast Episode</h1>
          <p className="text-blue-100">
            Generate educational podcast episodes on any scientific topic using AI
          </p>
        </div>

        {/* Progress Steps */}
        <div className="p-6 border-b">
          <div className="flex items-center justify-between mb-4">
            {[1, 2, 3].map((step) => (
              <div
                key={step}
                className={`flex items-center ${step < 3 ? 'flex-1' : ''}`}
              >
                <div
                  className={`w-8 h-8 rounded-full flex items-center justify-center text-sm font-medium
                    ${currentStep >= step 
                      ? 'bg-blue-600 text-white' 
                      : 'bg-gray-200 text-gray-600'
                    }`}
                >
                  {step}
                </div>
                <span className={`ml-2 text-sm ${currentStep >= step ? 'text-blue-600' : 'text-gray-500'}`}>
                  {step === 1 && 'Topic & Content'}
                  {step === 2 && 'Customize'}
                  {step === 3 && 'Generate'}
                </span>
                {step < 3 && (
                  <div className={`flex-1 h-0.5 mx-4 ${currentStep > step ? 'bg-blue-600' : 'bg-gray-200'}`} />
                )}
              </div>
            ))}
          </div>
        </div>

        <form onSubmit={handleSubmit} className="p-6">
          {/* Step 1: Topic & Content */}
          {currentStep === 1 && (
            <div className="space-y-6">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  What would you like your podcast episode to cover?
                </label>
                <textarea
                  value={request.prompt}
                  onChange={(e) => setRequest(prev => ({ ...prev, prompt: e.target.value }))}
                  placeholder="Describe the topic you want to explore. Be specific about what aspects you'd like to cover..."
                  className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                  rows={4}
                  required
                />
                <p className="text-sm text-gray-500 mt-1">
                  Example: "Explain the latest developments in quantum computing and their potential impact on cryptography"
                </p>
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Episode Title
                </label>
                <input
                  type="text"
                  value={request.title}
                  onChange={(e) => setRequest(prev => ({ ...prev, title: e.target.value }))}
                  placeholder="Enter a compelling title for your episode"
                  className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                  required
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Category
                </label>
                <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
                  {CATEGORY_OPTIONS.map((option) => (
                    <button
                      key={option.value}
                      type="button"
                      onClick={() => setRequest(prev => ({ ...prev, category: option.value }))}
                      className={`p-3 rounded-lg border-2 transition-colors text-left
                        ${request.category === option.value
                          ? 'border-blue-500 bg-blue-50 text-blue-700'
                          : 'border-gray-200 hover:border-gray-300'
                        }`}
                    >
                      <div className="text-2xl mb-1">{option.icon}</div>
                      <div className="font-medium text-sm">{option.label}</div>
                    </button>
                  ))}
                </div>
              </div>

              {/* Example Prompts */}
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Need inspiration? Try these examples:
                </label>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                  {EXAMPLE_PROMPTS.map((example, index) => (
                    <button
                      key={index}
                      type="button"
                      onClick={() => loadExample(example)}
                      className="p-3 bg-gray-50 hover:bg-gray-100 rounded-lg text-left transition-colors"
                    >
                      <div className="font-medium text-sm mb-1">{example.title}</div>
                      <div className="text-xs text-gray-600 line-clamp-2">{example.prompt}</div>
                    </button>
                  ))}
                </div>
              </div>
            </div>
          )}

          {/* Step 2: Customize */}
          {currentStep === 2 && (
            <div className="space-y-6">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Tone & Style
                </label>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                  {TONE_OPTIONS.map((option) => (
                    <button
                      key={option.value}
                      type="button"
                      onClick={() => setRequest(prev => ({ ...prev, tone: option.value as any }))}
                      className={`p-4 rounded-lg border-2 transition-colors text-left
                        ${request.tone === option.value
                          ? 'border-blue-500 bg-blue-50'
                          : 'border-gray-200 hover:border-gray-300'
                        }`}
                    >
                      <div className="font-medium">{option.label}</div>
                      <div className="text-sm text-gray-600">{option.description}</div>
                    </button>
                  ))}
                </div>
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Episode Length: {request.length_minutes} minutes
                </label>
                <input
                  type="range"
                  min="5"
                  max="30"
                  step="5"
                  value={request.length_minutes}
                  onChange={(e) => setRequest(prev => ({ ...prev, length_minutes: parseInt(e.target.value) }))}
                  className="w-full"
                />
                <div className="flex justify-between text-sm text-gray-500 mt-1">
                  <span>5 min</span>
                  <span>15 min</span>
                  <span>30 min</span>
                </div>
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Voice Preference
                </label>
                <select
                  value={request.voice_preference}
                  onChange={(e) => setRequest(prev => ({ ...prev, voice_preference: e.target.value as any }))}
                  className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                >
                  <option value="default">Default (AI Host)</option>
                  <option value="male">Male Voice</option>
                  <option value="female">Female Voice</option>
                  <option value="multi-voice">Multi-Voice (Dialogue)</option>
                </select>
              </div>

              <div className="space-y-3">
                <label className="flex items-center">
                  <input
                    type="checkbox"
                    checked={request.include_intro}
                    onChange={(e) => setRequest(prev => ({ ...prev, include_intro: e.target.checked }))}
                    className="mr-3"
                  />
                  <span className="text-sm">Include "Welcome to Copernicus AI" introduction</span>
                </label>
                <label className="flex items-center">
                  <input
                    type="checkbox"
                    checked={request.include_outro}
                    onChange={(e) => setRequest(prev => ({ ...prev, include_outro: e.target.checked }))}
                    className="mr-3"
                  />
                  <span className="text-sm">Include closing remarks and subscription call-to-action</span>
                </label>
                <label className="flex items-center">
                  <input
                    type="checkbox"
                    checked={request.citations}
                    onChange={(e) => setRequest(prev => ({ ...prev, citations: e.target.checked }))}
                    className="mr-3"
                  />
                  <span className="text-sm">Include scientific citations and references</span>
                </label>
              </div>
            </div>
          )}

          {/* Step 3: Generate */}
          {currentStep === 3 && (
            <div className="space-y-6">
              <div className="bg-blue-50 p-6 rounded-lg">
                <h3 className="font-bold text-lg mb-4">📋 Episode Summary</h3>
                <div className="space-y-2 text-sm">
                  <p><strong>Title:</strong> {request.title}</p>
                  <p><strong>Category:</strong> {CATEGORY_OPTIONS.find(c => c.value === request.category)?.label}</p>
                  <p><strong>Length:</strong> ~{request.length_minutes} minutes</p>
                  <p><strong>Tone:</strong> {TONE_OPTIONS.find(t => t.value === request.tone)?.label}</p>
                  <p><strong>Voice:</strong> {request.voice_preference.replace('-', ' ')}</p>
                </div>
                <div className="mt-4 p-3 bg-white rounded border">
                  <p className="text-sm"><strong>Content:</strong></p>
                  <p className="text-sm text-gray-700 mt-1">{request.prompt}</p>
                </div>
              </div>

              <div className="bg-yellow-50 p-4 rounded-lg">
                <p className="text-sm text-yellow-800">
                  <strong>⏱️ Estimated generation time:</strong> 3-5 minutes
                </p>
                <p className="text-sm text-yellow-700 mt-1">
                  Your episode will include audio, transcript, and thumbnail image.
                </p>
              </div>
            </div>
          )}

          {/* Navigation Buttons */}
          <div className="flex justify-between mt-8 pt-6 border-t">
            <button
              type="button"
              onClick={() => setCurrentStep(Math.max(1, currentStep - 1))}
              disabled={currentStep === 1}
              className="px-6 py-2 border border-gray-300 rounded-lg hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              Previous
            </button>

            <div className="flex gap-3">
              {currentStep < 3 ? (
                <button
                  type="button"
                  onClick={() => setCurrentStep(currentStep + 1)}
                  disabled={currentStep === 1 && (!request.prompt.trim() || !request.title.trim())}
                  className="px-6 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  Next
                </button>
              ) : (
                <button
                  type="submit"
                  disabled={!isFormValid || isGenerating}
                  className="px-8 py-3 bg-gradient-to-r from-blue-600 to-purple-600 text-white rounded-lg hover:from-blue-700 hover:to-purple-700 disabled:opacity-50 disabled:cursor-not-allowed font-medium"
                >
                  {isGenerating ? (
                    <span className="flex items-center">
                      <svg className="animate-spin -ml-1 mr-3 h-5 w-5 text-white" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                        <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                        <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                      </svg>
                      Generating Episode...
                    </span>
                  ) : (
                    '🎙️ Generate Episode'
                  )}
                </button>
              )}
            </div>
          </div>
        </form>
      </div>
    </div>
  );
} 