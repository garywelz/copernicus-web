'use client'

import { useState, useEffect } from 'react'
import { Podcast, User } from '@/types/user'

interface PodcastDiscoveryProps {
  user?: User
  onPodcastClick: (podcast: Podcast) => void
}

export default function PodcastDiscovery({ user, onPodcastClick }: PodcastDiscoveryProps) {
  const [activeTab, setActiveTab] = useState<'trending' | 'recommended' | 'latest' | 'categories'>('trending')
  const [selectedCategory, setSelectedCategory] = useState<string>('all')
  const [podcasts, setPodcasts] = useState<Podcast[]>([])
  const [loading, setLoading] = useState(true)

  const categories = [
    { id: 'all', name: 'All', icon: '🎙️' },
    { id: 'physics', name: 'Physics', icon: '⚛️' },
    { id: 'biology', name: 'Biology', icon: '🧬' },
    { id: 'chemistry', name: 'Chemistry', icon: '🧪' },
    { id: 'computer-science', name: 'Computer Science', icon: '💻' },
    { id: 'mathematics', name: 'Mathematics', icon: '📐' },
    { id: 'astronomy', name: 'Astronomy', icon: '🔭' },
    { id: 'medicine', name: 'Medicine', icon: '🏥' },
    { id: 'psychology', name: 'Psychology', icon: '🧠' },
    { id: 'engineering', name: 'Engineering', icon: '⚙️' }
  ]

  const tabs = [
    { id: 'trending', label: 'Trending', icon: '🔥' },
    { id: 'recommended', label: 'Recommended', icon: '🎯' },
    { id: 'latest', label: 'Latest', icon: '🆕' },
    { id: 'categories', label: 'Categories', icon: '📂' }
  ]

  useEffect(() => {
    // Simulate loading podcasts
    setTimeout(() => {
      setPodcasts(generateMockPodcasts())
      setLoading(false)
    }, 1000)
  }, [activeTab, selectedCategory])

  const generateMockPodcasts = (): Podcast[] => {
    const mockPodcasts: Podcast[] = []
    const titles = [
      'The Future of Quantum Computing: Breaking Down the Latest Breakthroughs',
      'CRISPR Gene Editing: Revolutionizing Medicine One Cell at a Time',
      'Dark Matter Mysteries: What We Know and What We Don\'t',
      'Machine Learning in Drug Discovery: AI\'s Role in Pharmaceutical Research',
      'The Mathematics of Climate Change: Modeling Our Planet\'s Future',
      'Neuroscience Breakthroughs: Understanding Consciousness',
      'Renewable Energy Technologies: Solar, Wind, and Beyond',
      'The Human Microbiome: Your Body\'s Hidden Ecosystem',
      'Space Exploration: Mars Missions and Beyond',
      'Artificial Intelligence Ethics: Balancing Innovation and Responsibility'
    ]

    for (let i = 0; i < 20; i++) {
      const category = categories[Math.floor(Math.random() * categories.length)]
      mockPodcasts.push({
        id: `podcast-${i}`,
        userId: `user-${Math.floor(Math.random() * 10)}`,
        title: titles[i % titles.length],
        description: 'An in-depth exploration of cutting-edge scientific research and discoveries.',
        topic: 'Scientific Research',
        category: category.id,
        duration: `${Math.floor(Math.random() * 30) + 10} minutes`,
        expertiseLevel: ['beginner', 'intermediate', 'expert'][Math.floor(Math.random() * 3)] as any,
        formatType: ['interview', 'monologue', 'discussion'][Math.floor(Math.random() * 3)] as any,
        status: 'published',
        visibility: 'public',
        views: Math.floor(Math.random() * 10000) + 100,
        likes: Math.floor(Math.random() * 500) + 10,
        shares: Math.floor(Math.random() * 100) + 5,
        downloads: Math.floor(Math.random() * 2000) + 50,
        createdAt: new Date(Date.now() - Math.random() * 30 * 24 * 60 * 60 * 1000).toISOString(),
        updatedAt: new Date().toISOString(),
        publishedAt: new Date(Date.now() - Math.random() * 7 * 24 * 60 * 60 * 1000).toISOString()
      })
    }

    return mockPodcasts
  }

  const formatViews = (views: number): string => {
    if (views >= 1000000) {
      return `${(views / 1000000).toFixed(1)}M`
    } else if (views >= 1000) {
      return `${(views / 1000).toFixed(1)}K`
    }
    return views.toString()
  }

  const formatTimeAgo = (dateString: string): string => {
    const date = new Date(dateString)
    const now = new Date()
    const diffInHours = Math.floor((now.getTime() - date.getTime()) / (1000 * 60 * 60))
    
    if (diffInHours < 24) {
      return `${diffInHours} hours ago`
    } else if (diffInHours < 168) {
      return `${Math.floor(diffInHours / 24)} days ago`
    } else {
      return `${Math.floor(diffInHours / 168)} weeks ago`
    }
  }

  if (loading) {
    return (
      <div className="max-w-7xl mx-auto p-6">
        <div className="animate-pulse">
          <div className="h-8 bg-gray-200 rounded w-1/4 mb-6"></div>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-6">
            {[...Array(12)].map((_, i) => (
              <div key={i} className="space-y-4">
                <div className="aspect-video bg-gray-200 rounded-lg"></div>
                <div className="space-y-2">
                  <div className="h-4 bg-gray-200 rounded w-3/4"></div>
                  <div className="h-3 bg-gray-200 rounded w-1/2"></div>
                  <div className="h-3 bg-gray-200 rounded w-1/4"></div>
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>
    )
  }

  return (
    <div className="max-w-7xl mx-auto p-6">
      {/* Header */}
      <div className="mb-8">
        <h1 className="text-3xl font-bold mb-2">Discover Research Podcasts</h1>
        <p className="text-gray-600">Explore the latest scientific discoveries and research insights</p>
      </div>

      {/* Tabs */}
      <div className="border-b border-gray-200 mb-6">
        <nav className="flex space-x-8">
          {tabs.map((tab) => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id as any)}
              className={`py-4 px-1 border-b-2 font-medium text-sm flex items-center gap-2 ${
                activeTab === tab.id
                  ? 'border-blue-500 text-blue-600'
                  : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
              }`}
            >
              <span>{tab.icon}</span>
              {tab.label}
            </button>
          ))}
        </nav>
      </div>

      {/* Category Filter */}
      {activeTab === 'categories' && (
        <div className="mb-6">
          <div className="flex flex-wrap gap-2">
            {categories.map((category) => (
              <button
                key={category.id}
                onClick={() => setSelectedCategory(category.id)}
                className={`px-4 py-2 rounded-full text-sm font-medium flex items-center gap-2 ${
                  selectedCategory === category.id
                    ? 'bg-blue-600 text-white'
                    : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
                }`}
              >
                <span>{category.icon}</span>
                {category.name}
              </button>
            ))}
          </div>
        </div>
      )}

      {/* Podcast Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-6">
        {podcasts.map((podcast) => (
          <div
            key={podcast.id}
            onClick={() => onPodcastClick(podcast)}
            className="bg-white rounded-lg shadow-md overflow-hidden hover:shadow-lg transition-shadow cursor-pointer"
          >
            {/* Thumbnail */}
            <div className="aspect-video bg-gradient-to-br from-blue-400 to-purple-600 relative">
              <div className="absolute inset-0 flex items-center justify-center text-white text-4xl">
                🎙️
              </div>
              <div className="absolute bottom-2 right-2 bg-black bg-opacity-70 text-white text-xs px-2 py-1 rounded">
                {podcast.duration}
              </div>
            </div>

            {/* Content */}
            <div className="p-4">
              <h3 className="font-semibold text-gray-900 mb-2 line-clamp-2">
                {podcast.title}
              </h3>
              
              <div className="flex items-center gap-2 text-sm text-gray-600 mb-2">
                <span className="px-2 py-1 bg-gray-100 rounded text-xs">
                  {categories.find(c => c.id === podcast.category)?.name || 'Science'}
                </span>
                <span className="px-2 py-1 bg-blue-100 text-blue-800 rounded text-xs">
                  {podcast.expertiseLevel}
                </span>
              </div>

              <div className="flex items-center justify-between text-sm text-gray-500">
                <div className="flex items-center gap-4">
                  <span>{formatViews(podcast.views)} views</span>
                  <span>{formatTimeAgo(podcast.publishedAt || podcast.createdAt)}</span>
                </div>
                <div className="flex items-center gap-2">
                  <span className="flex items-center gap-1">
                    👍 {podcast.likes}
                  </span>
                  <span className="flex items-center gap-1">
                    📤 {podcast.shares}
                  </span>
                </div>
              </div>
            </div>
          </div>
        ))}
      </div>

      {/* Load More */}
      <div className="text-center mt-8">
        <button className="px-6 py-3 bg-blue-600 text-white rounded-lg hover:bg-blue-700">
          Load More Podcasts
        </button>
      </div>
    </div>
  )
}
