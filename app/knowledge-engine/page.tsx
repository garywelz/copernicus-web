/**
 * Knowledge Engine Dashboard Page
 * 
 * Copyright (c) 2025 Gary Welz / CopernicusAI
 * Licensed under MIT License
 */

'use client'

import { useState, useEffect } from 'react'
import dynamic from 'next/dynamic'
import { KE_PROJECTS, KE_PROJECT_IDS, isKEProjectId, type KEProjectId } from '@/lib/knowledge-engine-projects'

// Dynamically import components with SSR disabled to prevent server-side errors
const KnowledgeMapView = dynamic(
  () => import('@/components/knowledge-engine/KnowledgeMapView'),
  { 
    ssr: false,
    loading: () => <div className="p-8 text-center">Loading Knowledge Map...</div>
  }
)
const SearchInterface = dynamic(
  () => import('@/components/knowledge-engine/SearchInterface'),
  { 
    ssr: false,
    loading: () => <div className="p-8 text-center">Loading Search...</div>
  }
)
const RAGInterface = dynamic(
  () => import('@/components/knowledge-engine/RAGInterface'),
  { 
    ssr: false,
    loading: () => <div className="p-8 text-center">Loading RAG Interface...</div>
  }
)
const ContentBrowser = dynamic(
  () => import('@/components/knowledge-engine/ContentBrowser'),
  { 
    ssr: false,
    loading: () => <div className="p-8 text-center">Loading Content Browser...</div>
  }
)
const StatsDashboard = dynamic(
  () => import('@/components/knowledge-engine/StatsDashboard'),
  { 
    ssr: false,
    loading: () => <div className="p-8 text-center">Loading Statistics...</div>
  }
)

type Tab = 'map' | 'search' | 'rag' | 'browse' | 'stats'

export default function KnowledgeEnginePage() {
  const [activeTab, setActiveTab] = useState<Tab>('map')
  // 692 is the 2026-08-15 verified process_databases.sum (all six families).
  // Fallback of last resort if the live fetch below fails -- will go stale
  // again if left here long enough, same as the "594" it replaces did.
  const [processCount, setProcessCount] = useState<number>(692)
  // GLMP/ATAP toggle, chrome-first v1 (see
  // docs/open-questions/knowledge-engine-project-toggle-plan-2026-08-15.md,
  // glmp repo). null/both is the default landing state, deliberately --
  // a forced pick would hide chemistry/physics/CS/non-GLMP-biology, same
  // failure shape as the "594" count-honesty bug fixed the same week.
  const [selectedProject, setSelectedProject] = useState<KEProjectId | null>(null)

  // Read ?project=glmp|atap on first load so a direct link can open scoped
  // to a project without needing sticky client state. Read-only sync from
  // URL -> state; does not push URL updates on manual toggle clicks (kept
  // simple for v1 -- add router-based sync later if deep-linking on every
  // click turns out to matter).
  useEffect(() => {
    const params = new URLSearchParams(window.location.search)
    const fromUrl = params.get('project')
    if (isKEProjectId(fromUrl)) {
      setSelectedProject(fromUrl)
    }
  }, [])

  useEffect(() => {
    fetch('https://storage.googleapis.com/regal-scholar-453620-r7-podcast-storage/knowledge-engine-status.json', { cache: 'no-store' })
      .then((r) => (r.ok ? r.json() : Promise.reject(r.status)))
      .then((d) => {
        const sum = d?.process_databases?.sum
        if (typeof sum === 'number') {
          setProcessCount(sum)
        }
      })
      .catch(() => {
        /* keep static fallback value */
      })
  }, [])

  const tabs = [
    { id: 'map' as Tab, label: 'Knowledge Map', icon: '🗺️' },
    { id: 'search' as Tab, label: 'Search', icon: '🔍' },
    { id: 'rag' as Tab, label: 'Ask Questions', icon: '💬' },
    { id: 'browse' as Tab, label: 'Browse Content', icon: '📚' },
    { id: 'stats' as Tab, label: 'Statistics', icon: '📊' },
  ]

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <header className="bg-white shadow-sm border-b sticky top-0 z-10">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex flex-col sm:flex-row sm:justify-between sm:items-center py-4 gap-3">
            <div>
              <h1 className="text-2xl font-bold text-gray-900">CopernicusAI Knowledge Engine: Research Tools</h1>
              <p className="text-sm text-gray-600">
                Papers, podcasts, videos, and {processCount.toLocaleString()} process charts across six scientific families
              </p>
              {selectedProject && (
                <p className="text-xs text-blue-700 mt-1">{KE_PROJECTS[selectedProject].framingLine}</p>
              )}
            </div>
            <div className="flex items-center gap-2" role="group" aria-label="Project view">
              <button
                onClick={() => setSelectedProject(null)}
                className={`text-xs px-3 py-1.5 rounded-md border transition-colors ${
                  selectedProject === null
                    ? 'bg-gray-800 text-white border-gray-800'
                    : 'bg-white text-gray-600 border-gray-300 hover:bg-gray-50'
                }`}
              >
                All projects
              </button>
              {KE_PROJECT_IDS.map((id) => (
                <button
                  key={id}
                  onClick={() => setSelectedProject(id)}
                  className={`text-xs px-3 py-1.5 rounded-md border transition-colors ${
                    selectedProject === id
                      ? 'bg-blue-600 text-white border-blue-600'
                      : 'bg-white text-gray-600 border-gray-300 hover:bg-gray-50'
                  }`}
                  title={KE_PROJECTS[id].fullName}
                >
                  {KE_PROJECTS[id].label}
                </button>
              ))}
            </div>
          </div>
        </div>
      </header>

      {/* Navigation Tabs */}
      <nav className="bg-white border-b">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex space-x-8 overflow-x-auto">
            {tabs.map((tab) => (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id)}
                className={`py-4 px-1 border-b-2 font-medium text-sm transition-colors whitespace-nowrap ${
                  activeTab === tab.id
                    ? 'border-blue-500 text-blue-600'
                    : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
                }`}
              >
                <span className="mr-2">{tab.icon}</span>
                {tab.label}
              </button>
            ))}
          </div>
        </div>
      </nav>

      {/* Main Content */}
      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {activeTab === 'map' && <KnowledgeMapView project={selectedProject} />}
        {activeTab === 'search' && <SearchInterface project={selectedProject} />}
        {activeTab === 'rag' && <RAGInterface />}
        {activeTab === 'browse' && <ContentBrowser project={selectedProject} />}
        {activeTab === 'stats' && <StatsDashboard />}
      </main>
    </div>
  )
}

