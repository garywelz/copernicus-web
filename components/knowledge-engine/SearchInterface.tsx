/**
 * Search Interface Component
 * 
 * Copyright (c) 2025 Gary Welz / CopernicusAI
 * Licensed under MIT License
 */

'use client'

import { useState } from 'react'

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'https://copernicus-podcast-api-phzp4ie2sq-uc.a.run.app'

type SearchResult = {
  id: string
  title: string
  abstract?: string
  authors?: string[]
  categories?: string[]
  similarity_score?: number
  type: 'paper' | 'podcast' | 'process'
}

export default function SearchInterface() {
  const [query, setQuery] = useState('')
  const [loading, setLoading] = useState(false)
  const [results, setResults] = useState<SearchResult[]>([])
  const [searchMethod, setSearchMethod] = useState<string>('vector_semantic')
  const [contentTypes, setContentTypes] = useState({
    papers: true,
    podcasts: true,
    processes: true,
  })
  const [limit, setLimit] = useState(20)

  const handleSearch = async () => {
    if (!query.trim()) return

    setLoading(true)
    setResults([])
    setSearchMethod('vector_semantic')

    try {
      const params = new URLSearchParams({
        query: query,
        limit: limit.toString(),
      })

      // Add content types
      const types: string[] = []
      if (contentTypes.papers) types.push('papers')
      if (contentTypes.podcasts) types.push('podcasts')
      if (contentTypes.processes) types.push('glmp', 'math', 'chemistry', 'physics', 'computer_science')

      if (types.length > 0) {
        params.append('content_types', types.join(','))
      }

      const response = await fetch(`${API_BASE_URL}/api/vector-search/semantic?${params}`)
      if (!response.ok) {
        throw new Error(`Search failed: ${response.statusText}`)
      }

      const data = await response.json()
      setSearchMethod(data.search_method || 'vector_semantic')
      
      // Flatten results from all content types
      const allResults: SearchResult[] = []
      
      if (data.papers) {
        data.papers.forEach((paper: any) => {
          allResults.push({
            id: paper.paper_id || paper.id,
            title: paper.title || 'Untitled Paper',
            abstract: paper.abstract,
            authors: paper.authors,
            categories: paper.categories,
            similarity_score: paper.similarity_score,
            type: 'paper',
          })
        })
      }

      if (data.podcasts) {
        data.podcasts.forEach((podcast: any) => {
          allResults.push({
            id: podcast.job_id || podcast.id,
            title: podcast.result?.title || podcast.title || 'Untitled Podcast',
            abstract: podcast.result?.description || podcast.description,
            similarity_score: podcast.similarity_score,
            type: 'podcast',
          })
        })
      }

      if (data.glmp_processes) {
        data.glmp_processes.forEach((process: any) => {
          allResults.push({
            id: process.process_id || process.id,
            title: process.title || 'Untitled Process',
            abstract: process.description,
            similarity_score: process.similarity_score,
            type: 'process',
          })
        })
      }

      // Sort by similarity score
      allResults.sort((a, b) => (b.similarity_score || 0) - (a.similarity_score || 0))

      setResults(allResults)
    } catch (error: any) {
      console.error('Search error:', error)
      alert(`Search failed: ${error.message}`)
    } finally {
      setLoading(false)
    }
  }

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter') {
      handleSearch()
    }
  }

  return (
    <div className="space-y-4">
      {/* Search Form */}
      <div className="bg-white rounded-lg shadow p-6">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-xl font-semibold text-gray-900">Semantic Search</h2>
          <span className={`text-xs px-3 py-1 rounded-full font-medium ${searchMethod?.includes('keyword') ? 'bg-yellow-100 text-yellow-800' : 'bg-blue-100 text-blue-700'}`}>
            {searchMethod?.includes('keyword') ? 'Keyword Search Active' : 'Powered by Vector Search'}
          </span>
        </div>
        
        {/* Info Banner */}
        <div className={`mb-4 border rounded-md p-3 ${searchMethod?.includes('keyword') ? 'bg-yellow-50 border-yellow-200' : 'bg-blue-50 border-blue-200'}`}>
          <p className={`text-sm ${searchMethod?.includes('keyword') ? 'text-yellow-900' : 'text-blue-800'}`}>
            {searchMethod?.includes('keyword') ? (
              <>
                <strong>Search Mode:</strong> Keyword search (no embeddings). Results are based on title/abstract keyword overlap.
                <strong> Use the Browse tab</strong> to see what content is available.
              </>
            ) : (
              <>
                <strong>Vector Search Status:</strong> Vector search requires content to have embeddings. Content exists in the database, but embeddings may still be missing.
                <strong> Use the Browse tab to see available content.</strong>
              </>
            )}
          </p>
        </div>
        
        <div className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Search Query
            </label>
            <div className="flex space-x-2">
              <input
                type="text"
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                onKeyPress={handleKeyPress}
                placeholder="Try: aerobic respiration, acid resistance (E. coli), amino acid biosynthesis, nilpotent groups..."
                className="flex-1 px-4 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
              <button
                onClick={handleSearch}
                disabled={loading || !query.trim()}
                className="px-6 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 disabled:bg-gray-400 disabled:cursor-not-allowed transition-colors"
              >
                {loading ? 'Searching...' : 'Search'}
              </button>
            </div>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Content Types
              </label>
              <div className="space-y-2">
                <label className="flex items-center space-x-2">
                  <input
                    type="checkbox"
                    checked={contentTypes.papers}
                    onChange={(e) => setContentTypes({ ...contentTypes, papers: e.target.checked })}
                    className="h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300 rounded"
                  />
                  <span className="text-sm text-gray-700">Research Papers</span>
                </label>
                <label className="flex items-center space-x-2">
                  <input
                    type="checkbox"
                    checked={contentTypes.podcasts}
                    onChange={(e) => setContentTypes({ ...contentTypes, podcasts: e.target.checked })}
                    className="h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300 rounded"
                  />
                  <span className="text-sm text-gray-700">Podcasts</span>
                </label>
                <label className="flex items-center space-x-2">
                  <input
                    type="checkbox"
                    checked={contentTypes.processes}
                    onChange={(e) => setContentTypes({ ...contentTypes, processes: e.target.checked })}
                    className="h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300 rounded"
                  />
                  <span className="text-sm text-gray-700">Processes</span>
                </label>
              </div>
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Results Limit
              </label>
              <input
                type="number"
                min="1"
                max="100"
                value={limit}
                onChange={(e) => setLimit(parseInt(e.target.value) || 20)}
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
            </div>
          </div>
        </div>
      </div>

      {/* Results */}
      {results.length > 0 && (
        <div className="bg-white rounded-lg shadow p-6">
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-lg font-semibold text-gray-900">
              Search Results ({results.length})
            </h3>
            <span className="text-xs px-2 py-1 bg-green-100 text-green-700 rounded font-medium">
              Vector Search Active
            </span>
          </div>
          <div className="space-y-4">
            {results.map((result) => (
              <div
                key={result.id}
                className="border border-gray-200 rounded-lg p-4 hover:shadow-md transition-shadow"
              >
                <div className="flex items-start justify-between mb-2">
                  <div className="flex-1">
                    <h4 className="text-lg font-medium text-gray-900">
                      {result.title.replace(/\$([^$]+)\$/g, '$1').replace(/\$/g, '')}
                    </h4>
                    <div className="flex items-center space-x-2 mt-1">
                      <span className="text-xs px-2 py-1 bg-blue-100 text-blue-800 rounded">
                        {result.type}
                      </span>
                      {result.similarity_score && (
                        <span className="text-xs text-gray-500">
                          Similarity: {(result.similarity_score * 100).toFixed(1)}%
                        </span>
                      )}
                    </div>
                  </div>
                </div>
                {result.abstract && (
                  <p className="text-sm text-gray-600 mt-2 line-clamp-3">
                    {result.abstract}
                  </p>
                )}
                {result.authors && result.authors.length > 0 && (
                  <p className="text-xs text-gray-500 mt-2">
                    Authors: {result.authors.join(', ')}
                  </p>
                )}
                {result.categories && result.categories.length > 0 && (
                  <div className="flex flex-wrap gap-1 mt-2">
                    {result.categories.map((cat, idx) => (
                      <span
                        key={idx}
                        className="text-xs px-2 py-1 bg-gray-100 text-gray-700 rounded"
                      >
                        {cat}
                      </span>
                    ))}
                  </div>
                )}
              </div>
            ))}
          </div>
        </div>
      )}

      {!loading && results.length === 0 && query && (
        <div className="bg-white rounded-lg shadow p-6 text-center">
          <div className="text-gray-500 mb-2">
            <p className="font-medium">No results found for "{query}"</p>
            <p className="text-sm mt-2">Try:</p>
            <ul className="text-sm mt-2 list-disc list-inside text-left max-w-md mx-auto">
              <li>Using different keywords</li>
              <li>Checking if content is indexed in the vector database</li>
              <li>Browsing content directly using the Browse tab</li>
            </ul>
          </div>
        </div>
      )}
    </div>
  )
}

