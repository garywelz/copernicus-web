/**
 * Content Browser Component
 */

'use client'

import { useState, useEffect, useMemo, FormEvent } from 'react'
import {
  API_BASE_URL,
  BROWSE_QUESTIONS,
  browseQuestionLabel,
  PAPERS_DATABASE_TABLE_HREF,
  PAPER_DISCIPLINES,
  PROCESS_DATABASE_LINKS,
  PROCESS_FAMILIES,
  VIDEOS_DATABASE_TABLE_HREF,
} from './constants'
import { KE_PROJECTS, type KEProjectId } from '@/lib/knowledge-engine-projects'
import { hrefForKnowledgeItem } from '@/lib/knowledge-engine-links'

type ContentItem = {
  id: string
  title: string
  type: 'paper' | 'podcast' | 'process' | 'video'
  description?: string
  doi?: string | null
  pmid?: string | null
  arxiv_id?: string | null
  url?: string | null
  metadata?: {
    process_family?: string
    category?: string
    subcategory?: string
    processType?: string
    process_type?: string
    episode_link?: string
    slug?: string
    youtube_id?: string
    channel_name?: string
    question_scope_ids?: string[]
  }
}

type FacetRow = { id: string; label?: string; count: number }

type BrowseType = 'papers' | 'podcasts' | 'processes' | 'videos'

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
    url: item.url || item.metadata?.episode_link,
    processFamily: item.metadata?.process_family,
    jobId: item.type === 'podcast' ? item.id : null,
    processId: item.type === 'process' ? item.id : null,
    slug: item.metadata?.slug || (item.type === 'podcast' ? item.id : null),
    episodeLink: item.metadata?.episode_link,
    subcategory: item.metadata?.subcategory,
    processType: item.metadata?.processType || item.metadata?.process_type,
    youtubeId: item.metadata?.youtube_id,
  })
}

export default function ContentBrowser({ project = null }: { project?: KEProjectId | null } = {}) {
  const [contentType, setContentType] = useState<BrowseType>('papers')
  // Default family chip follows the selected project (chrome-level default
  // only -- the process_family filter and its effect on retrieval already
  // existed before the toggle; this just picks a sensible starting chip
  // instead of always defaulting to 'math' regardless of context).
  const [processFamily, setProcessFamily] = useState<string>(project ? KE_PROJECTS[project].processContentType : 'math')
  /** Paper/video-discipline chip. Empty = all. Mathematics is a paper family,
   *  distinct from ATAP process charts — same idea as Biology papers vs GLMP. */
  const [paperDiscipline, setPaperDiscipline] = useState<string>('')
  const [question, setQuestion] = useState('')
  const [channel, setChannel] = useState('')
  const [keywordInput, setKeywordInput] = useState('')
  const [keyword, setKeyword] = useState('')
  const [note, setNote] = useState<string | null>(null)
  const [facets, setFacets] = useState<{
    disciplines: FacetRow[]
    channels: FacetRow[]
    questions: FacetRow[]
  } | null>(null)

  useEffect(() => {
    if (project) {
      setProcessFamily(KE_PROJECTS[project].processContentType)
    }
  }, [project])
  const [loading, setLoading] = useState(false)
  const [items, setItems] = useState<ContentItem[]>([])
  const [total, setTotal] = useState(0)
  const [pages, setPages] = useState(0)
  const [page, setPage] = useState(1)
  /** Papers over-fetch so hiding Untitled stubs still leaves a usable card grid. */
  const limit = contentType === 'papers' ? 50 : 20
  const catalogFilters = contentType === 'papers' || contentType === 'videos'

  useEffect(() => {
    loadContent()
  }, [contentType, processFamily, paperDiscipline, question, channel, keyword, page])

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
      if ((contentType === 'papers' || contentType === 'videos') && paperDiscipline) {
        params.set('discipline', paperDiscipline)
      }
      if ((contentType === 'papers' || contentType === 'videos') && question) {
        params.set('question', question)
      }
      if ((contentType === 'papers' || contentType === 'videos') && keyword) {
        params.set('keyword', keyword)
      }
      if (contentType === 'videos' && channel) {
        params.set('channel', channel)
      }

      const response = await fetch(`${API_BASE_URL}/api/content/browse?${params}`)
      if (!response.ok) throw new Error(`Failed to load: ${response.statusText}`)

      const data = await response.json()
      setItems(data.items || [])
      setTotal(data.pagination?.total || 0)
      setPages(data.pagination?.pages || 0)
      setNote(typeof data.note === 'string' ? data.note : null)
      setFacets(data.facets || null)
    } catch (error) {
      console.error('Error loading content:', error)
      setItems([])
      setTotal(0)
      setPages(0)
      setNote(null)
      setFacets(null)
    } finally {
      setLoading(false)
    }
  }

  const applyKeyword = (event?: FormEvent) => {
    event?.preventDefault()
    const next = keywordInput.trim()
    setPage(1)
    setKeyword(next)
  }

  const resetCatalogFilters = () => {
    setPaperDiscipline('')
    setQuestion('')
    setChannel('')
    setKeywordInput('')
    setKeyword('')
    setPage(1)
  }

  const questionOptions = useMemo(() => {
    const known = BROWSE_QUESTIONS.map((q) => q.id)
    const extra = (facets?.questions || [])
      .map((row) => row.id)
      .filter((id) => !known.includes(id as (typeof BROWSE_QUESTIONS)[number]['id']))
    return [
      ...BROWSE_QUESTIONS.map((q) => ({ id: q.id, label: q.label })),
      ...extra.map((id) => ({ id, label: id })),
    ]
  }, [facets])

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
          {(['papers', 'podcasts', 'processes', 'videos'] as const).map((type) => (
            <button
              key={type}
              onClick={() => {
                setContentType(type)
                resetCatalogFilters()
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

        {catalogFilters && (
          <div className="space-y-3 mb-4 border border-gray-100 rounded-lg p-4 bg-gray-50">
            <p className="text-xs text-gray-500">
              Catalog filters (title/channel/question tags). For meaning search, use the Search tab.
            </p>
            <form onSubmit={applyKeyword} className="flex flex-wrap gap-2">
              <input
                type="search"
                value={keywordInput}
                onChange={(e) => setKeywordInput(e.target.value)}
                placeholder={
                  contentType === 'videos'
                    ? 'Filter by title, channel, or tag…'
                    : 'Filter by title or abstract…'
                }
                className="flex-1 min-w-[16rem] px-3 py-2 text-sm border border-gray-300 rounded-md"
              />
              <button
                type="submit"
                className="px-4 py-2 text-sm bg-blue-600 text-white rounded-md hover:bg-blue-700"
              >
                Filter
              </button>
              {(keyword || question || channel || paperDiscipline) && (
                <button
                  type="button"
                  onClick={resetCatalogFilters}
                  className="px-4 py-2 text-sm bg-white border border-gray-300 rounded-md hover:bg-gray-100"
                >
                  Clear filters
                </button>
              )}
            </form>

            <div className="flex flex-wrap gap-4">
              <label className="text-sm text-gray-700">
                Question
                <select
                  value={question}
                  onChange={(e) => {
                    setQuestion(e.target.value)
                    setPage(1)
                  }}
                  className="ml-2 px-2 py-1 border border-gray-300 rounded-md bg-white"
                >
                  <option value="">All questions</option>
                  {questionOptions.map((q) => {
                    const count = facets?.questions?.find((row) => row.id === q.id)?.count
                    return (
                      <option key={q.id} value={q.id}>
                        {q.label}
                        {typeof count === 'number' ? ` (${count})` : ''}
                      </option>
                    )
                  })}
                </select>
              </label>
              {contentType === 'videos' && (
                <label className="text-sm text-gray-700">
                  Channel
                  <select
                    value={channel}
                    onChange={(e) => {
                      setChannel(e.target.value)
                      setPage(1)
                    }}
                    className="ml-2 px-2 py-1 border border-gray-300 rounded-md bg-white max-w-xs"
                  >
                    <option value="">All channels</option>
                    {(facets?.channels || []).map((row) => (
                      <option key={row.id} value={row.id}>
                        {row.label || row.id} ({row.count})
                      </option>
                    ))}
                  </select>
                </label>
              )}
            </div>

            <div className="flex flex-wrap gap-2">
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
              {PAPER_DISCIPLINES.map((d) => {
                const count = facets?.disciplines?.find((row) => row.id === d.id)?.count
                return (
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
                    {typeof count === 'number' ? ` (${count})` : ''}
                  </button>
                )
              })}
            </div>
          </div>
        )}

        <p className="text-sm text-gray-500 mb-4">
          {total > 0 ? `${total.toLocaleString()} items` : 'No items loaded'}
          {keyword ? ` · keyword “${keyword}”` : ''}
          {question ? ` · ${browseQuestionLabel(question)}` : ''}
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
          {contentType === 'videos' && (
            <>
              {' · '}
              <a
                href={VIDEOS_DATABASE_TABLE_HREF}
                target="_blank"
                rel="noopener noreferrer"
                className="text-blue-600 hover:underline"
              >
                Open full database table
              </a>
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
        {note && <p className="text-xs text-amber-800 mb-4">{note}</p>}

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
                  {item.metadata?.channel_name && (
                    <p className="text-xs text-gray-500 mb-1">{item.metadata.channel_name}</p>
                  )}
                  {item.description && (
                    <p className="text-sm text-gray-600 line-clamp-3">{item.description}</p>
                  )}
                  <span className="inline-block mt-2 text-xs px-2 py-1 bg-blue-100 text-blue-800 rounded">
                    {item.type}
                    {item.metadata?.process_family
                      ? ` · ${PROCESS_FAMILIES.find((f) => f.id === item.metadata?.process_family)?.label || item.metadata.process_family}`
                      : ''}
                  </span>
                  {(item.metadata?.question_scope_ids || []).slice(0, 3).map((qid) => (
                    <span
                      key={qid}
                      className="inline-block mt-2 ml-1 text-xs px-2 py-1 bg-purple-50 text-purple-800 rounded"
                    >
                      {qid}
                    </span>
                  ))}
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
            <span className="py-2 text-sm text-gray-600">
              Page {page}
              {pages > 0 ? ` of ${pages}` : ''}
            </span>
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
