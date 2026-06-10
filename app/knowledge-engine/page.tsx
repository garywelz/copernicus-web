/**
 * Knowledge Engine Dashboard Page
 * 
 * Copyright (c) 2025 Gary Welz / CopernicusAI
 * Licensed under MIT License
 */

'use client'

import { useState } from 'react'
import dynamic from 'next/dynamic'

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
          <div className="flex justify-between items-center py-4">
            <div>
              <h1 className="text-2xl font-bold text-gray-900">CopernicusAI Knowledge Engine: Research Tools</h1>
              <p className="text-sm text-gray-600">
                Papers, podcasts, videos, and 594 process charts across six scientific families
              </p>
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
        {activeTab === 'map' && <KnowledgeMapView />}
        {activeTab === 'search' && <SearchInterface />}
        {activeTab === 'rag' && <RAGInterface />}
        {activeTab === 'browse' && <ContentBrowser />}
        {activeTab === 'stats' && <StatsDashboard />}
      </main>
    </div>
  )
}

