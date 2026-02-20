/**
 * Content Browser Component
 * 
 * Copyright (c) 2025 Gary Welz / CopernicusAI
 * Licensed under MIT License
 */

'use client'

import { useState, useEffect } from 'react'

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'https://copernicus-podcast-api-phzp4ie2sq-uc.a.run.app'

type ContentItem = {
  id: string
  title: string
  type: 'paper' | 'podcast' | 'process'
  description?: string
  metadata?: any
}

export default function ContentBrowser() {
  const [contentType, setContentType] = useState<'papers' | 'podcasts' | 'processes'>('papers')
  const [loading, setLoading] = useState(false)
  const [items, setItems] = useState<ContentItem[]>([])
  const [page, setPage] = useState(1)
  const [limit] = useState(20)

  useEffect(() => {
    loadContent()
  }, [contentType, page])

  const loadContent = async () => {
    setLoading(true)
    try {
      const params = new URLSearchParams({
        content_type: contentType,
        page: page.toString(),
        limit: limit.toString(),
      })
      
      const response = await fetch(`${API_BASE_URL}/api/content/browse?${params}`)
      if (!response.ok) {
        throw new Error(`Failed to load content: ${response.statusText}`)
      }
      
      const data = await response.json()
      setItems(data.items || [])
    } catch (error: any) {
      console.error('Error loading content:', error)
      setItems([])
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="space-y-4">
      {/* Content Type Selector */}
      <div className="bg-white rounded-lg shadow p-6">
        <h2 className="text-xl font-semibold text-gray-900 mb-4">Browse Content</h2>
        
        <div className="flex space-x-4 mb-4">
          {(['papers', 'podcasts', 'processes'] as const).map((type) => (
            <button
              key={type}
              onClick={() => {
                setContentType(type)
                setPage(1)
              }}
              className={`px-4 py-2 rounded-md transition-colors ${
                contentType === type
                  ? 'bg-blue-600 text-white'
                  : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
              }`}
            >
              {type.charAt(0).toUpperCase() + type.slice(1)}
            </button>
          ))}
        </div>

        {loading && (
          <div className="flex items-center justify-center py-12">
            <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
          </div>
        )}

        {!loading && items.length === 0 && (
          <div className="text-center py-12 text-gray-500">
            <p>Content browser coming soon.</p>
            <p className="text-sm mt-2">
              This feature will allow you to browse all papers, podcasts, and processes in the knowledge base.
            </p>
          </div>
        )}

        {!loading && items.length > 0 && (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {items.map((item) => (
              <div
                key={item.id}
                className="border border-gray-200 rounded-lg p-4 hover:shadow-md transition-shadow"
              >
                <h3 className="font-medium text-gray-900 mb-2">
                  {item.title.replace(/\$([^$]+)\$/g, '$1').replace(/\$/g, '')}
                </h3>
                {item.description && (
                  <p className="text-sm text-gray-600 line-clamp-3">{item.description}</p>
                )}
                <span className="inline-block mt-2 text-xs px-2 py-1 bg-blue-100 text-blue-800 rounded">
                  {item.type}
                </span>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}

