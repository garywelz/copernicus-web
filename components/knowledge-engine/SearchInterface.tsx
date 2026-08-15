/**
 * Search Interface Component
 *
 * Copyright (c) 2025 Gary Welz / CopernicusAI
 * Licensed under MIT License
 */

'use client'

import { useState } from 'react'
import { API_BASE_URL } from './constants'
import {
  KE_PROJECTS,
  searchContentTypesForProject,
  type KEProjectId,
} from '@/lib/knowledge-engine-projects'
import { hrefForKnowledgeItem, processFamilyFromSearchBucket } from '@/lib/knowledge-engine-links'

type SearchResult = {
  id: string
  title: string
  abstract?: string
  authors?: string[]
  categories?: string[]
  similarity_score?: number
  type: 'paper' | 'podcast' | 'process' | 'video'
  doi?: string | null
  pmid?: string | null
  arxiv_id?: string | null
  url?: string | null
  processFamily?: string | null
  jobId?: string | null
  slug?: string | null
  episodeLink?: string | null
  subcategory?: string | null
  processType?: string | null
  proofGraphHtml?: string | null
  youtubeId?: string | null
}

const normalizeText = (text: string): string =>
  text
    .replace(/<[^>]+>/g, '')
    .replace(/\$([^$]+)\$/g, '$1')
    .replace(/\$/g, '')

export default function SearchInterface({ project = null }: { project?: KEProjectId | null } = {}) {
  const [query, setQuery] = useState('')
  const [loading, setLoading] = useState(false)
  const [results, setResults] = useState<SearchResult[]>([])
  const [searchMethod, setSearchMethod] = useState<string>('vector_semantic')
  const [contentTypes, setContentTypes] = useState({
    papers: true,
    podcasts: true,
    processes: true,
    videos: true,
  })
  const [limit, setLimit] = useState(20)

  const processLabel = project
    ? `${KE_PROJECTS[project].label} process charts`
    : 'Processes (all 6 families)'

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
      const types = searchContentTypesForProject(project, contentTypes)
      if (types.length > 0) {
        params.append('content_types', types.join(','))
      }

      const response = await fetch(`${API_BASE_URL}/api/vector-search/semantic?${params}`)
      if (!response.ok) {
        throw new Error(`Search failed: ${response.statusText}`)
      }

      const data = await response.json()
      setSearchMethod(data.search_method || 'vector_semantic')

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
            doi: paper.doi ?? null,
            pmid: paper.pmid ?? null,
            arxiv_id: paper.arxiv_id ?? null,
            url: paper.url ?? null,
          })
        })
      }

      if (data.podcasts) {
        data.podcasts.forEach((podcast: any) => {
          const episodeId = podcast.slug || podcast.episode_id || podcast.job_id || podcast.id
          allResults.push({
            id: episodeId,
            title: podcast.result?.title || podcast.title || 'Untitled Podcast',
            abstract: podcast.result?.description || podcast.description,
            similarity_score: podcast.similarity_score,
            type: 'podcast',
            jobId: episodeId,
            slug: podcast.slug || episodeId,
            episodeLink: podcast.episode_link || podcast.url || null,
            url: podcast.episode_link || podcast.url || null,
          })
        })
      }

      if (data.videos) {
        data.videos.forEach((video: any) => {
          allResults.push({
            id: video.video_id || video.youtube_id || video.id,
            title: video.title || 'Untitled Video',
            abstract: video.description,
            similarity_score: video.similarity_score,
            type: 'video',
            url: video.video_url || video.url || null,
            youtubeId: video.youtube_id || video.source_id || video.youtubeId || null,
          })
        })
      }

      const processBuckets = [
        'glmp_processes',
        'math_processes',
        'chemistry_processes',
        'physics_processes',
        'computer_science_processes',
        'biology_processes',
      ] as const
      for (const bucket of processBuckets) {
        const list = data[bucket] || []
        const family = processFamilyFromSearchBucket(bucket)
        list.forEach((process: any) => {
          const processId = process.process_id || process.chart_id || process.id
          allResults.push({
            id: processId,
            title: process.title || process.name || 'Untitled Process',
            abstract: process.description,
            similarity_score: process.similarity_score,
            type: 'process',
            processFamily: family,
            subcategory: process.subcategory || null,
            processType: process.processType || process.process_type || null,
            proofGraphHtml: process.proofGraphHtml || process.proof_graph_html || null,
          })
        })
      }

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
      <div className="bg-white rounded-lg shadow p-6">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-xl font-semibold text-gray-900">Semantic Search</h2>
          <span className={`text-xs px-3 py-1 rounded-full font-medium ${searchMethod?.includes('keyword') ? 'bg-yellow-100 text-yellow-800' : 'bg-blue-100 text-blue-700'}`}>
            {searchMethod?.includes('keyword') ? 'Keyword Search Active' : 'Powered by Vector Search'}
          </span>
        </div>

        <div className={`mb-4 border rounded-md p-3 ${searchMethod?.includes('keyword') ? 'bg-yellow-50 border-yellow-200' : 'bg-blue-50 border-blue-200'}`}>
          <p className={`text-sm ${searchMethod?.includes('keyword') ? 'text-yellow-900' : 'text-blue-800'}`}>
            {searchMethod?.includes('keyword') ? (
              <>
                <strong>Search Mode:</strong> Keyword search (no embeddings). Results are based on title/abstract keyword overlap.
                <strong> Use the Browse tab</strong> to see what content is available.
              </>
            ) : (
              <>
                <strong>Vector Search:</strong> Semantic search across papers, podcasts, and{' '}
                {project ? `${KE_PROJECTS[project].label} process charts` : 'six process families'}
                (OpenAI embeddings). Keyword mode is used when the query embedding service is unavailable.
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
                placeholder={project ? KE_PROJECTS[project].searchPlaceholder : 'Try: aerobic respiration, acid resistance (E. coli), amino acid biosynthesis, proof nets...'}
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
                  <span className="text-sm text-gray-700">{processLabel}</span>
                </label>
                <label className="flex items-center space-x-2">
                  <input
                    type="checkbox"
                    checked={contentTypes.videos}
                    onChange={(e) => setContentTypes({ ...contentTypes, videos: e.target.checked })}
                    className="h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300 rounded"
                  />
                  <span className="text-sm text-gray-700">Videos</span>
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
            {results.map((result) => {
              const href = hrefForKnowledgeItem({
                type: result.type,
                id: result.id,
                doi: result.doi,
                pmid: result.pmid,
                arxiv_id: result.arxiv_id,
                url: result.url,
                processFamily: result.processFamily,
                jobId: result.jobId,
                processId: result.id,
                slug: result.slug,
                episodeLink: result.episodeLink,
                subcategory: result.subcategory,
                processType: result.processType,
                proofGraphHtml: result.proofGraphHtml,
                youtubeId: result.youtubeId,
              })
              const typeLabel = result.processFamily
                ? `${result.type} · ${result.processFamily === 'math' ? 'ATAP' : result.processFamily}`
                : result.type
              return (
                <div
                  key={`${result.type}-${result.id}`}
                  className="border border-gray-200 rounded-lg p-4 hover:shadow-md transition-shadow"
                >
                  <div className="flex items-start justify-between mb-2">
                    <div className="flex-1">
                      <h4 className="text-lg font-medium text-gray-900">
                        {href ? (
                          <a
                            href={href}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="text-blue-700 hover:underline"
                          >
                            {normalizeText(result.title)}
                          </a>
                        ) : (
                          normalizeText(result.title)
                        )}
                      </h4>
                      <div className="flex items-center space-x-2 mt-1">
                        <span className="text-xs px-2 py-1 bg-blue-100 text-blue-800 rounded">
                          {typeLabel}
                        </span>
                        {result.similarity_score ? (
                          <span className="text-xs text-gray-500">
                            Similarity: {(result.similarity_score * 100).toFixed(1)}%
                          </span>
                        ) : null}
                      </div>
                    </div>
                  </div>
                  {result.abstract && (
                    <p className="text-sm text-gray-600 mt-2 line-clamp-3">
                      {normalizeText(result.abstract)}
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
              )
            })}
          </div>
        </div>
      )}

      {!loading && results.length === 0 && query && (
        <div className="bg-white rounded-lg shadow p-6 text-center">
          <div className="text-gray-500 mb-2">
            <p className="font-medium">No results found for &quot;{query}&quot;</p>
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
