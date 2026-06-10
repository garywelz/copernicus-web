/**
 * Statistics Dashboard Component
 */

'use client'

import { useState, useEffect } from 'react'
import {
  API_BASE_URL,
  GCS_STATUS_URL,
  PROCESS_DATABASE_LINKS,
} from './constants'

type EngineStatus = {
  papers?: number
  podcasts?: number
  videos?: number
  processes?: number
  papers_with_embedding?: number
  papers_embedding_coverage_percent?: number
  last_updated?: string
  process_databases?: Record<string, number>
  notes?: Record<string, string>
}

type Stats = {
  knowledge_map?: {
    nodes: number
    edges: number
    papers: number
    concepts: number
  }
}

export default function StatsDashboard() {
  const [loading, setLoading] = useState(true)
  const [engineStatus, setEngineStatus] = useState<EngineStatus | null>(null)
  const [stats, setStats] = useState<Stats>({})
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    loadStats()
  }, [])

  const loadStats = async () => {
    setLoading(true)
    setError(null)
    try {
      const [statusRes, kmRes] = await Promise.all([
        fetch(`${GCS_STATUS_URL}?cb=${Date.now()}`),
        fetch(`${API_BASE_URL}/api/knowledge-map/stats`),
      ])

      if (statusRes.ok) {
        setEngineStatus(await statusRes.json())
      }

      if (kmRes.ok) {
        const kmData = await kmRes.json()
        setStats({ knowledge_map: kmData })
      }
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Failed to load statistics')
    } finally {
      setLoading(false)
    }
  }

  if (loading) {
    return (
      <div className="bg-white rounded-lg shadow p-6 flex justify-center py-12">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600" />
      </div>
    )
  }

  if (error) {
    return (
      <div className="bg-white rounded-lg shadow p-6">
        <p className="text-red-800">Error loading statistics: {error}</p>
      </div>
    )
  }

  const pdb = engineStatus?.process_databases || {}
  const processSum = pdb.sum ?? 0

  return (
    <div className="space-y-6">
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        <div className="bg-white rounded-lg shadow p-6">
          <div className="text-3xl font-bold text-blue-600">
            {engineStatus?.papers?.toLocaleString() ?? '—'}
          </div>
          <div className="text-sm text-gray-600 mt-1">Research Papers</div>
          {engineStatus?.papers_embedding_coverage_percent != null && (
            <div className="text-xs text-green-700 mt-2">
              {engineStatus.papers_embedding_coverage_percent}% embedded (OpenAI)
            </div>
          )}
        </div>
        <div className="bg-white rounded-lg shadow p-6">
          <div className="text-3xl font-bold text-green-600">
            {engineStatus?.podcasts?.toLocaleString() ?? '—'}
          </div>
          <div className="text-sm text-gray-600 mt-1">Podcasts</div>
        </div>
        <div className="bg-white rounded-lg shadow p-6">
          <div className="text-3xl font-bold text-amber-600">
            {engineStatus?.videos?.toLocaleString() ?? '—'}
          </div>
          <div className="text-sm text-gray-600 mt-1">Science Videos</div>
        </div>
        <div className="bg-white rounded-lg shadow p-6">
          <div className="text-3xl font-bold text-purple-600">
            {processSum.toLocaleString()}
          </div>
          <div className="text-sm text-gray-600 mt-1">Process Charts (6 families)</div>
          <div className="text-xs text-gray-500 mt-1">
            Firestore GLMP only: {engineStatus?.processes?.toLocaleString() ?? '—'}
          </div>
        </div>
      </div>

      <div className="bg-white rounded-lg shadow p-6">
        <h3 className="text-lg font-semibold text-gray-900 mb-4">Process Databases (JSON-canonical)</h3>
        <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-3 text-sm">
          {PROCESS_DATABASE_LINKS.map((link) => (
            <a
              key={link.key}
              href={link.href}
              target="_blank"
              rel="noopener noreferrer"
              className="border border-gray-200 rounded-lg p-3 hover:border-blue-400 hover:shadow-sm transition"
            >
              <div className="font-semibold text-gray-900">{link.label}</div>
              <div className="text-2xl font-bold text-purple-600 mt-1">
                {typeof pdb[link.key] === 'number' ? pdb[link.key].toLocaleString() : '—'}
              </div>
            </a>
          ))}
        </div>
        <p className="text-xs text-gray-500 mt-4">
          Total across families: {processSum.toLocaleString()} (excludes graph-type pilots).
          Math, chemistry, physics, CS, and biology are embedded with OpenAI text-embedding-3-small for vector search.
        </p>
      </div>

      {stats.knowledge_map && (
        <div className="bg-white rounded-lg shadow p-6">
          <h3 className="text-lg font-semibold text-gray-900 mb-4">Knowledge Map</h3>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            <div>
              <div className="text-2xl font-bold text-blue-600">{stats.knowledge_map.nodes}</div>
              <div className="text-sm text-gray-600">Nodes</div>
            </div>
            <div>
              <div className="text-2xl font-bold text-green-600">{stats.knowledge_map.edges}</div>
              <div className="text-sm text-gray-600">Edges</div>
            </div>
            <div>
              <div className="text-2xl font-bold text-purple-600">{stats.knowledge_map.papers}</div>
              <div className="text-sm text-gray-600">Papers on map</div>
            </div>
            <div>
              <div className="text-2xl font-bold text-red-600">{stats.knowledge_map.concepts}</div>
              <div className="text-sm text-gray-600">Concepts</div>
            </div>
          </div>
        </div>
      )}

      <div className="bg-white rounded-lg shadow p-6 text-sm text-gray-600 space-y-2">
        <div className="flex justify-between">
          <span>Status updated</span>
          <span className="text-gray-900">{engineStatus?.last_updated ?? '—'}</span>
        </div>
        <div className="flex justify-between">
          <span>API</span>
          <span className="font-mono text-gray-900">{API_BASE_URL}</span>
        </div>
        {engineStatus?.notes?.media_catalogs && (
          <p className="text-xs pt-2 border-t">{engineStatus.notes.media_catalogs}</p>
        )}
      </div>
    </div>
  )
}
