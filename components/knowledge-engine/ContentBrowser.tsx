/**
 * Content Browser Component
 */

'use client'

import { useState, useEffect, useMemo } from 'react'
import {
  API_BASE_URL,
  PAPERS_DATABASE_TABLE_HREF,
  PROCESS_DATABASE_LINKS,
  PROCESS_FAMILIES,
  PAPER_DISCIPLINES,
} from './constants'
import { KE_PROJECTS, type KEProjectId } from '@/lib/knowledge-engine-projects'
import { hrefForKnowledgeItem } from '@/lib/knowledge-engine-links'

type ContentItem = {
  id: string
  title: string
  type: 'paper' | 'podcast' | 'process'
  description?: string
  doi?: string | null
  pmid?: string | null
  arxiv_id?: string | null
  url?: string | null
  metadata?: { process_family?: string; category?: string }
}

type BrowseType = 'papers' | 'podcasts' | 'processes'

function isUntitledPaper(item: ContentItem): boolean {
  const t = (item.title || '').trim()
  return !t || t === 'Untitled'
}

function titleHrefFor(item: ContentItem): string | null {
  return hrefForKnowledgeItem({
    type: item.type,
    id: item.id,
    doi: item.doi,
    pmid: item.pmid,
    arxiv_id: item.arxiv_id,
    url: item.url,
    processFamily: item.metadata?.process_family,
    jobId: item.type === 'podcast' ? item.id : null,
    processId: item.type === 'process' ? item.id : null,
  })
}

export default function ContentBrowser({ project = null }: { project?: KEProjectId | null } = {}) {
  const [contentType, setContentType] = useState<BrowseType>('papers')
  // Default family chip follows the selected project (chrome-level default
  // only -- the process_family filter and its effect on retrieval already
  // existed before the toggle; this just picks a sensible starting chip
  // instead of always defaulting to 'math' regardless of context).
  const [processFamily, setProcessFamily] = useState<string>(project ? KE_PROJECTS[project].processContentType : 'math')
  /** Paper-discipline chip. Empty = all papers. Mathematics is a paper family,
   *  distinct from ATAP process charts — same idea as Biology papers vs GLMP. */
  const [paperDiscipline, setPaperDiscipline] = useState<string>('')

  useEffect(() => {
    if (project) {
      setProcessFamily(KE_PROJECTS[project].processContentType)
    }
  }, [project])
  const [loading, setLoading] = useState(false)
  const [items, setItems] = useState<ContentItem[]>([])
  const [total, setTotal] = useState(0)
  const [page, setPage] = useState(1)
  /** Papers over-fetch so hiding Untitled stubs still leaves a usable card grid. */
  const limit = contentType === 'papers' ? 50 : 20

  useEffect(() => {
    loadContent()
  }, [contentType, processFamily, paperDiscipline, page])

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
      if (contentType === 'papers' && paperDiscipline) {
        params.set('discipline', paperDiscipline)
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

  const { visibleItems, hiddenStubCount } = useMemo(() => {
    if (contentType !== 'papers') {
      return { visibleItems: items, hiddenStubCount: 0 }
    }
    const visible = items.filter((it) => !isUntitledPaper(it))
    return {
      visibleItems: visible,
      hiddenStubCount: items.length - visible.length,
    }
  }, [contentType, items])

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

        {contentType === 'papers' && (
          <div className="flex flex-wrap gap-2 mb-4">
            <button
              onClick={() => {
                setPaperDiscipline('')
                setPage(1)
              }}
              className={`px-3 py-1 text-sm rounded-md ${
                paperDiscipline === ''
                  ? 'bg-purple-600 text-white'
                  : 'bg-purple-50 text-purple-800 hover:bg-purple-100'
              }`}
            >
              All disciplines
            </button>
            {PAPER_DISCIPLINES.map((d) => (
              <button
                key={d.id}
                onClick={() => {
                  setPaperDiscipline(d.id)
                  setPage(1)
                }}
                className={`px-3 py-1 text-sm rounded-md ${
                  paperDiscipline === d.id
                    ? 'bg-purple-600 text-white'
                    : 'bg-purple-50 text-purple-800 hover:bg-purple-100'
                }`}
              >
                {d.label}
              </button>
            ))}
          </div>
        )}

        <p className="text-sm text-gray-500 mb-4">
          {total > 0 ? `${total.toLocaleString()} items` : 'No items loaded'}
          {contentType === 'papers' && (
            <>
              {' · '}
              <a
                href={PAPERS_DATABASE_TABLE_HREF}
                target="_blank"
                rel="noopener noreferrer"
                className="text-blue-600 hover:underline"
              >
                Open full database table
              </a>
              {hiddenStubCount > 0 && (
                <span className="text-gray-400">
                  {` · ${hiddenStubCount} untitled stub${hiddenStubCount === 1 ? '' : 's'} hidden on this page`}
                </span>
              )}
            </>
          )}
          {contentType === 'processes' && (
            <>
              {' · '}
              <a
                href={
                  PROCESS_DATABASE_LINKS.find((l) => {
                    const fam = PROCESS_FAMILIES.find((f) => f.id === processFamily)
                    return fam ? l.key === fam.statusKey : false
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

        {!loading && visibleItems.length === 0 && (
          <div className="text-center py-12 text-gray-500">
            {hiddenStubCount > 0
              ? 'No titled papers on this page (untitled stubs hidden). Try Next.'
              : 'No items found.'}
          </div>
        )}

        {!loading && visibleItems.length > 0 && (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {visibleItems.map((item) => {
              const titleText = item.title.replace(/\$([^$]+)\$/g, '$1').replace(/\$/g, '')
              const titleHref = titleHrefFor(item)
              return (
                <div
                  key={item.id}
                  className="border border-gray-200 rounded-lg p-4 hover:shadow-md transition-shadow"
                >
                  <h3 className="font-medium text-gray-900 mb-2">
                    {titleHref ? (
                      <a
                        href={titleHref}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="text-blue-700 hover:underline"
                      >
                        {titleText}
                      </a>
                    ) : (
                      titleText
                    )}
                  </h3>
                  {item.description && (
                    <p className="text-sm text-gray-600 line-clamp-3">{item.description}</p>
                  )}
                  <span className="inline-block mt-2 text-xs px-2 py-1 bg-blue-100 text-blue-800 rounded">
                    {item.type}
                    {item.metadata?.process_family
                      ? ` · ${PROCESS_FAMILIES.find((f) => f.id === item.metadata?.process_family)?.label || item.metadata.process_family}`
                      : ''}
                  </span>
                </div>
              )
            })}
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
