/**
 * RAG (Retrieval-Augmented Generation) Interface Component
 * 
 * Copyright (c) 2025 Gary Welz / CopernicusAI
 * Licensed under MIT License
 */

'use client'

import { useState } from 'react'

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'https://copernicus-podcast-api-phzp4ie2sq-uc.a.run.app'

type Citation = {
  number: number
  type: string
  title: string
  similarity_score?: number
}

type RAGResponse = {
  question: string
  answer: string
  citations: Citation[]
  sources?: any
  metadata?: any
  error?: string
}

export default function RAGInterface() {
  const [question, setQuestion] = useState('')
  const [loading, setLoading] = useState(false)
  const [response, setResponse] = useState<RAGResponse | null>(null)
  const [maxContextItems, setMaxContextItems] = useState(5)
  const retrievalMethod = response?.metadata?.retrieval_method as string | undefined
  const modelName = response?.metadata?.model as string | undefined
  const isKeywordMode = (retrievalMethod || '').includes('keyword') || (modelName || '') === 'none'

  const handleAsk = async () => {
    if (!question.trim()) return

    setLoading(true)
    setResponse(null)

    try {
      const params = new URLSearchParams({
        question: question,
        max_context_items: maxContextItems.toString(),
      })

      const response = await fetch(`${API_BASE_URL}/api/rag/answer?${params}`)
      if (!response.ok) {
        throw new Error(`RAG request failed: ${response.statusText}`)
      }

      const data = await response.json()
      setResponse(data)
    } catch (error: any) {
      console.error('RAG error:', error)
      setResponse({
        question,
        answer: `Error: ${error.message}`,
        citations: [],
        error: error.message,
      })
    } finally {
      setLoading(false)
    }
  }

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && e.shiftKey === false) {
      e.preventDefault()
      handleAsk()
    }
  }

  // These are tuned to return results in retrieval-only mode (Vertex AI disabled)
  const exampleQuestions = [
    'What is the glutamate-dependent acid resistance system in Escherichia coli, and what genes are involved?',
    'Explain aerobic respiration in mitochondria, including the electron transport chain and ATP synthase.',
    'What is amino acid biosynthesis and why is it important in cells?',
    'What are nilpotent groups? Give the definition and one example.',
  ]

  return (
    <div className="space-y-4">
      {/* Question Form */}
      <div className="bg-white rounded-lg shadow p-6">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-xl font-semibold text-gray-900">Ask a Question</h2>
          <span className={`text-xs px-3 py-1 rounded-full font-medium ${isKeywordMode ? 'bg-yellow-100 text-yellow-800' : 'bg-purple-100 text-purple-700'}`}>
            {isKeywordMode ? 'Keyword Retrieval Mode' : 'Powered by RAG'}
          </span>
        </div>
        
        {/* Info Banner */}
        <div className={`mb-4 border rounded-md p-3 ${isKeywordMode ? 'bg-yellow-50 border-yellow-200' : 'bg-blue-50 border-blue-200'}`}>
          <p className={`text-sm ${isKeywordMode ? 'text-yellow-900' : 'text-blue-800'}`}>
            {isKeywordMode ? (
              <>
                <strong>Status:</strong> Vertex/LLM is currently unavailable, so we’re returning a retrieval-based response (citations + excerpts) instead of a generated answer.
                <strong> Use the Browse tab</strong> to see what content is available.
              </>
            ) : (
              <>
                <strong>RAG Status:</strong> RAG requires content to have vector embeddings.
                <strong> Use the Browse tab</strong> to see available content.
              </>
            )}
          </p>
        </div>
        
        <div className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Your Question
            </label>
            <textarea
              value={question}
              onChange={(e) => setQuestion(e.target.value)}
              onKeyPress={handleKeyPress}
              placeholder="Ask a question about research papers, concepts, or processes..."
              rows={4}
              className="w-full px-4 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
          </div>

          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-2">
              <label className="text-sm font-medium text-gray-700">
                Max Context Items:
              </label>
              <input
                type="number"
                min="1"
                max="20"
                value={maxContextItems}
                onChange={(e) => setMaxContextItems(parseInt(e.target.value) || 5)}
                className="w-20 px-2 py-1 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
            </div>
            <button
              onClick={handleAsk}
              disabled={loading || !question.trim()}
              className="px-6 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 disabled:bg-gray-400 disabled:cursor-not-allowed transition-colors"
            >
              {loading ? 'Thinking...' : 'Ask Question'}
            </button>
          </div>
        </div>
      </div>

      {/* Example Questions */}
      <div className="bg-white rounded-lg shadow p-6">
        <h3 className="text-sm font-semibold text-gray-700 mb-2">Example Questions</h3>
        <div className="flex flex-wrap gap-2">
          {exampleQuestions.map((example, idx) => (
            <button
              key={idx}
              onClick={() => setQuestion(example)}
              className="text-sm px-3 py-1 bg-gray-100 hover:bg-gray-200 text-gray-700 rounded-md transition-colors"
            >
              {example}
            </button>
          ))}
        </div>
      </div>

      {/* Response */}
      {loading && (
        <div className="bg-white rounded-lg shadow p-6">
          <div className="flex items-center space-x-3">
            <div className="animate-spin rounded-full h-6 w-6 border-b-2 border-blue-600"></div>
            <p className="text-gray-600">Generating answer...</p>
          </div>
        </div>
      )}

      {response && !loading && (
        <div className="space-y-4">
          <div className="bg-white rounded-lg shadow p-6">
            <h3 className="text-lg font-semibold text-gray-900 mb-4">Answer</h3>
            <div className="prose max-w-none">
              {response.answer && response.answer.includes("I couldn't find relevant information") ? (
                <div className="bg-yellow-50 border border-yellow-200 rounded-md p-4">
                  <p className="text-gray-700 whitespace-pre-wrap mb-3">{response.answer}</p>
                  <div className="bg-blue-50 border border-blue-200 rounded p-3 mt-3">
                    <p className="text-sm text-blue-800 font-medium mb-2">Why no results?</p>
                    <p className="text-sm text-blue-700">
                      The RAG system needs content indexed in the vector database to answer questions. 
                      We're building our collection - try using the <strong>Browse Content</strong> tab to see available papers and processes, 
                      or check back as we add more content daily.
                    </p>
                  </div>
                  <p className="text-sm text-gray-600 mt-3">
                    <strong>Suggestions:</strong>
                  </p>
                  <ul className="text-sm text-gray-600 mt-1 list-disc list-inside ml-2">
                    <li>Browse available content using the Browse tab</li>
                    <li>Try questions about topics you see in the knowledge base</li>
                    <li>Check back regularly as we add more content</li>
                  </ul>
                </div>
              ) : (
                <p className="text-gray-700 whitespace-pre-wrap">{response.answer}</p>
              )}
            </div>
          </div>

          {response.citations && response.citations.length > 0 && (
            <div className="bg-white rounded-lg shadow p-6">
              <h3 className="text-lg font-semibold text-gray-900 mb-4">
                Citations ({response.citations.length})
              </h3>
              <div className="space-y-3">
                {response.citations.map((citation) => (
                  <div
                    key={citation.number}
                    className="border border-gray-200 rounded-lg p-4"
                  >
                    <div className="flex items-start space-x-2">
                      <span className="flex-shrink-0 w-6 h-6 bg-blue-100 text-blue-800 rounded-full flex items-center justify-center text-sm font-medium">
                        {citation.number}
                      </span>
                      <div className="flex-1">
                        <h4 className="font-medium text-gray-900">{citation.title}</h4>
                        <div className="flex items-center space-x-2 mt-1">
                          <span className="text-xs px-2 py-1 bg-gray-100 text-gray-700 rounded">
                            {citation.type}
                          </span>
                          {citation.similarity_score && (
                            <span className="text-xs text-gray-500">
                              Similarity: {(citation.similarity_score * 100).toFixed(1)}%
                            </span>
                          )}
                        </div>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {response.metadata && (
            <div className="bg-gray-50 rounded-lg p-4">
              <h4 className="text-sm font-semibold text-gray-700 mb-2">Metadata</h4>
              <div className="text-xs text-gray-600 space-y-1">
                <p>Context Items Used: {response.metadata.context_items_used || 0}</p>
                <p>Model: {response.metadata.model || 'N/A'}</p>
                {response.metadata.retrieval_method && (
                  <p>Retrieval Method: {response.metadata.retrieval_method}</p>
                )}
                {response.metadata.generated_at && (
                  <p>Generated: {new Date(response.metadata.generated_at).toLocaleString()}</p>
                )}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  )
}

