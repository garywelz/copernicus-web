/**
 * Statistics Dashboard Component
 * 
 * Copyright (c) 2025 Gary Welz / CopernicusAI
 * Licensed under MIT License
 */

'use client'

import { useState, useEffect } from 'react'

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'https://copernicus-podcast-api-phzp4ie2sq-uc.a.run.app'

type Stats = {
  papers?: number
  podcasts?: number
  processes?: number
  concepts?: number
  nodes?: number
  edges?: number
  knowledge_map?: {
    nodes: number
    edges: number
    papers: number
    concepts: number
  }
}

export default function StatsDashboard() {
  const [loading, setLoading] = useState(true)
  const [stats, setStats] = useState<Stats>({})
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    loadStats()
  }, [])

  const loadStats = async () => {
    setLoading(true)
    setError(null)

    try {
      // Load knowledge map stats
      const kmResponse = await fetch(`${API_BASE_URL}/api/knowledge-map/stats`)
      if (kmResponse.ok) {
        const kmData = await kmResponse.json()
        setStats((prev) => ({
          ...prev,
          knowledge_map: kmData,
        }))
      }

      // Fetch content counts by trying to get pagination totals
      // Note: These are approximations since count() queries can be expensive
      try {
        const papersResponse = await fetch(`${API_BASE_URL}/api/content/browse?content_type=papers&page=1&limit=1`)
        if (papersResponse.ok) {
          const papersData = await papersResponse.json()
          const papersCount = papersData.pagination?.total || 0
          if (papersCount > 0) {
            setStats((prev) => ({ ...prev, papers: papersCount }))
          }
        }
      } catch (e) {
        // Ignore errors - counts are optional
      }

      try {
        const podcastsResponse = await fetch(`${API_BASE_URL}/api/content/browse?content_type=podcasts&page=1&limit=1`)
        if (podcastsResponse.ok) {
          const podcastsData = await podcastsResponse.json()
          const podcastsCount = podcastsData.pagination?.total || 0
          if (podcastsCount > 0) {
            setStats((prev) => ({ ...prev, podcasts: podcastsCount }))
          }
        }
      } catch (e) {
        // Ignore errors - counts are optional
      }

      try {
        const processesResponse = await fetch(`${API_BASE_URL}/api/content/browse?content_type=processes&page=1&limit=1`)
        if (processesResponse.ok) {
          const processesData = await processesResponse.json()
          const processesCount = processesData.pagination?.total || 0
          if (processesCount > 0) {
            setStats((prev) => ({ ...prev, processes: processesCount }))
          }
        }
      } catch (e) {
        // Ignore errors - counts are optional
      }
    } catch (err: any) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  if (loading) {
    return (
      <div className="bg-white rounded-lg shadow p-6">
        <div className="flex items-center justify-center py-12">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
        </div>
      </div>
    )
  }

  if (error) {
    return (
      <div className="bg-white rounded-lg shadow p-6">
        <div className="bg-red-50 border border-red-200 rounded-md p-4">
          <p className="text-red-800">Error loading statistics: {error}</p>
        </div>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      {/* Overview Stats */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        <div className="bg-white rounded-lg shadow p-6">
          <div className="text-3xl font-bold text-blue-600">{stats.papers?.toLocaleString() || 'N/A'}</div>
          <div className="text-sm text-gray-600 mt-1">Research Papers</div>
        </div>
        <div className="bg-white rounded-lg shadow p-6">
          <div className="text-3xl font-bold text-green-600">{stats.podcasts?.toLocaleString() || 'N/A'}</div>
          <div className="text-sm text-gray-600 mt-1">Podcasts</div>
        </div>
        <div className="bg-white rounded-lg shadow p-6">
          <div className="text-3xl font-bold text-purple-600">{stats.processes?.toLocaleString() || 'N/A'}</div>
          <div className="text-sm text-gray-600 mt-1">Processes</div>
        </div>
        <div className="bg-white rounded-lg shadow p-6">
          <div className="text-3xl font-bold text-red-600">{stats.concepts?.toLocaleString() || 'N/A'}</div>
          <div className="text-sm text-gray-600 mt-1">Concepts</div>
        </div>
      </div>

      {/* Knowledge Map Stats */}
      {stats.knowledge_map && (
        <div className="bg-white rounded-lg shadow p-6">
          <h3 className="text-lg font-semibold text-gray-900 mb-4">Knowledge Map Statistics</h3>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            <div>
              <div className="text-2xl font-bold text-blue-600">
                {stats.knowledge_map.nodes?.toLocaleString() || 0}
              </div>
              <div className="text-sm text-gray-600">Total Nodes</div>
            </div>
            <div>
              <div className="text-2xl font-bold text-green-600">
                {stats.knowledge_map.edges?.toLocaleString() || 0}
              </div>
              <div className="text-sm text-gray-600">Total Edges</div>
            </div>
            <div>
              <div className="text-2xl font-bold text-purple-600">
                {stats.knowledge_map.papers?.toLocaleString() || 0}
              </div>
              <div className="text-sm text-gray-600">Papers</div>
            </div>
            <div>
              <div className="text-2xl font-bold text-red-600">
                {stats.knowledge_map.concepts?.toLocaleString() || 0}
              </div>
              <div className="text-sm text-gray-600">Concepts</div>
            </div>
          </div>
        </div>
      )}

      {/* System Information */}
      <div className="bg-white rounded-lg shadow p-6">
        <h3 className="text-lg font-semibold text-gray-900 mb-4">System Information</h3>
        <div className="space-y-2 text-sm">
          <div className="flex justify-between">
            <span className="text-gray-600">API Base URL:</span>
            <span className="text-gray-900 font-mono">{API_BASE_URL}</span>
          </div>
          <div className="flex justify-between">
            <span className="text-gray-600">Status:</span>
            <span className="text-green-600 font-medium">Operational</span>
          </div>
        </div>
      </div>
    </div>
  )
}

