/**
 * Content Browser Component
 */

'use client'

import { useState, useEffect } from 'react'
import { API_BASE_URL, PROCESS_DATABASE_LINKS } from './constants'

type ContentItem = {
  id: string
  title: string
  type: 'paper' | 'podcast' | 'process'
  description?: string
  metadata?: { process_family?: string; category?: string }
}

type BrowseType = 'papers' | 'podcasts' | 'processes'

const PROCESS_FAMILIES = [
  { id: 'glmp', label: 'GLMP' },
  { id: 'math', label: 'Mathematics' },
  { id: 'chemistry', label: 'Chemistry' },
  { id: 'physics', label: 'Physics' },
  { id: 'computer_science', label: 'Computer Science' },
  { id: 'biology', label: 'Biology' },
] as const

export default function ContentBrowser() {
  const [contentType, setContentType] = useState<BrowseType>('papers')
  const [processFamily, setProcessFamily] = useState('math')
  const [loading, setLoading] = useState(false)
  const [items, setItems] = useState<ContentItem[]>([])
  const [total, setTotal] = useState(0)
  const [page, setPage] = useState(1)
  const limit = 20

  useEffect(() => {
    loadContent()
  }, [contentType, processFamily, page])

  const loadContent = async () => {
    setLoading(true)
    try {
      const params = new URLSearchParams({
        content_type: contentType,
        page: page.toString(),
        limit: limit.toString(),
      })
      if (contentType === 'processes') {
        params.set('process_family', processFamily)
      }

      const response = await fetch(`${API_BASE_URL}/api/content/browse?${params}`)
      if (!response.ok) throw new Error(`Failed to load: ${response.statusText}`)

      const data = await response.json()
      setItems(data.items || [])
      setTotal(data.pagination?.total || 0)
    } catch (error) {
      console.error('Error loading content:', error)
      setItems([])
      setTotal(0)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="space-y-4">
      <div className="bg-white rounded-lg shadow p-6">
        <h2 className="text-xl font-semibold text-gray-900 mb-4">Browse Content</h2>

        <div className="flex flex-wrap gap-2 mb-4">
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

        {contentType === 'processes' && (
          <div className="flex flex-wrap gap-2 mb-4">
            {PROCESS_FAMILIES.map((f) => (
              <button
                key={f.id}
                onClick={() => {
                  setProcessFamily(f.id)
                  setPage(1)
                }}
                className={`px-3 py-1 text-sm rounded-md ${
                  processFamily === f.id
                    ? 'bg-purple-600 text-white'
                    : 'bg-purple-50 text-purple-800 hover:bg-purple-100'
                }`}
              >
                {f.label}
              </button>
            ))}
          </div>
        )}

        <p className="text-sm text-gray-500 mb-4">
          {total > 0 ? `${total.toLocaleString()} items` : 'No items loaded'}
          {contentType === 'processes' && (
            <>
              {' · '}
              <a
                href={
                  PROCESS_DATABASE_LINKS.find((l) => {
                    const keyMap: Record<string, string> = {
                      glmp: 'glmp_v2',
                      math: 'mathematics',
                      chemistry: 'chemistry',
                      physics: 'physics',
                      computer_science: 'computer_science',
                      biology: 'biology',
                    }
                    return l.key === keyMap[processFamily]
                  })?.href
                }
                target="_blank"
                rel="noopener noreferrer"
                className="text-blue-600 hover:underline"
              >
                Open full database table
              </a>
            </>
          )}
        </p>

        {loading && (
          <div className="flex justify-center py-12">
            <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600" />
          </div>
        )}

        {!loading && items.length === 0 && (
          <div className="text-center py-12 text-gray-500">No items found.</div>
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
                  {item.metadata?.process_family ? ` · ${item.metadata.process_family}` : ''}
                </span>
              </div>
            ))}
          </div>
        )}

        {total > limit && (
          <div className="flex justify-center gap-4 mt-6">
            <button
              disabled={page <= 1}
              onClick={() => setPage((p) => Math.max(1, p - 1))}
              className="px-4 py-2 text-sm bg-gray-100 rounded disabled:opacity-40"
            >
              Previous
            </button>
            <span className="py-2 text-sm text-gray-600">Page {page}</span>
            <button
              disabled={page * limit >= total}
              onClick={() => setPage((p) => p + 1)}
              className="px-4 py-2 text-sm bg-gray-100 rounded disabled:opacity-40"
            >
              Next
            </button>
          </div>
        )}
      </div>
    </div>
  )
}
