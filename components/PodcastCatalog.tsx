'use client'

import { useState, useEffect } from 'react'
import { Play, Download, BookOpen, Filter, Search } from 'lucide-react'

interface Episode {
  id: string
  title: string
  topic: string
  category: string
  duration: string
  audioUrl: string
  thumbnailUrl: string
  transcriptUrl: string
  descriptionUrl: string
  expertiseLevel: string
  formatType: string
  generatedAt: string
  requiresPremium: boolean
  requiresResearch: boolean
}

interface PodcastCatalogProps {
  userTier?: string
}

export default function PodcastCatalog({ userTier = 'free' }: PodcastCatalogProps) {
  const [episodes, setEpisodes] = useState<Episode[]>([])
  const [loading, setLoading] = useState(true)
  const [searchTerm, setSearchTerm] = useState('')
  const [selectedCategory, setSelectedCategory] = useState('all')
  const [categories, setCategories] = useState<string[]>([])
  const [currentPage, setCurrentPage] = useState(1)
  const [hasMore, setHasMore] = useState(true)
  const [currentlyPlaying, setCurrentlyPlaying] = useState<string | null>(null)

  useEffect(() => {
    fetchEpisodes()
  }, [selectedCategory, currentPage, userTier])

  const fetchEpisodes = async () => {
    try {
      setLoading(true)
      const params = new URLSearchParams({
        category: selectedCategory,
        page: currentPage.toString(),
        limit: '12',
        tier: userTier
      })
      
      if (searchTerm) {
        params.set('search', searchTerm)
      }

      const response = await fetch(`/api/podcasts/catalog?${params}`)
      const data = await response.json()
      
      if (currentPage === 1) {
        setEpisodes(data.episodes || [])
      } else {
        setEpisodes(prev => [...prev, ...(data.episodes || [])])
      }
      
      setCategories(data.filters?.categories || [])
      setHasMore(data.pagination?.hasMore || false)
    } catch (error) {
      console.error('Error fetching episodes:', error)
    } finally {
      setLoading(false)
    }
  }

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault()
    setCurrentPage(1)
    fetchEpisodes()
  }

  const loadMore = () => {
    setCurrentPage(prev => prev + 1)
  }

  const playEpisode = (episode: Episode) => {
    setCurrentlyPlaying(episode.id)
    // Here you would integrate with your audio player
    console.log('Playing episode:', episode.title)
  }

  const downloadEpisode = async (episode: Episode) => {
    if (userTier === 'free') {
      alert('Download is available for Premium and Research subscribers')
      return
    }
    
    try {
      const response = await fetch(episode.audioUrl)
      const blob = await response.blob()
      const url = window.URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = `${episode.title}.mp3`
      document.body.appendChild(a)
      a.click()
      window.URL.revokeObjectURL(url)
      document.body.removeChild(a)
    } catch (error) {
      console.error('Error downloading episode:', error)
    }
  }

  const getAccessBadge = (episode: Episode) => {
    if (episode.requiresResearch && userTier !== 'research') {
      return <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-purple-100 text-purple-800">Research Pro</span>
    }
    if (episode.requiresPremium && userTier === 'free') {
      return <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-blue-100 text-blue-800">Premium</span>
    }
    return null
  }

  return (
    <div className="space-y-6">
      {/* Search and Filters */}
      <div className="flex flex-col sm:flex-row gap-4">
        <form onSubmit={handleSearch} className="flex-1">
          <div className="relative">
            <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400 h-4 w-4" />
            <input
              type="text"
              placeholder="Search podcasts..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              className="w-full pl-10 pr-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
            />
          </div>
        </form>
        
        <div className="flex items-center space-x-2">
          <Filter className="h-4 w-4 text-gray-400" />
          <select
            value={selectedCategory}
            onChange={(e) => {
              setSelectedCategory(e.target.value)
              setCurrentPage(1)
            }}
            className="border border-gray-300 rounded-lg px-3 py-2 focus:ring-2 focus:ring-blue-500 focus:border-transparent"
          >
            <option value="all">All Categories</option>
            {categories.map(category => (
              <option key={category} value={category}>{category}</option>
            ))}
          </select>
        </div>
      </div>

      {/* Episodes Grid */}
      {loading && episodes.length === 0 ? (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-6">
          {[...Array(8)].map((_, i) => (
            <div key={i} className="bg-gray-200 animate-pulse rounded-lg h-80"></div>
          ))}
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-6">
          {episodes.map((episode) => (
            <div key={episode.id} className="bg-white rounded-lg shadow-sm border hover:shadow-md transition-shadow">
              <div className="relative">
                <img
                  src={episode.thumbnailUrl}
                  alt={episode.title}
                  className="w-full h-48 object-cover rounded-t-lg"
                />
                {getAccessBadge(episode) && (
                  <div className="absolute top-2 right-2">
                    {getAccessBadge(episode)}
                  </div>
                )}
                <button
                  onClick={() => playEpisode(episode)}
                  className="absolute inset-0 flex items-center justify-center bg-black bg-opacity-0 hover:bg-opacity-30 transition-all duration-200 rounded-t-lg group"
                >
                  <div className="bg-white bg-opacity-90 rounded-full p-3 opacity-0 group-hover:opacity-100 transition-opacity">
                    <Play className="h-6 w-6 text-blue-600 ml-1" />
                  </div>
                </button>
              </div>
              
              <div className="p-4">
                <h3 className="font-semibold text-gray-900 mb-2 line-clamp-2">
                  {episode.title}
                </h3>
                <p className="text-sm text-gray-600 mb-3 line-clamp-2">
                  {episode.topic}
                </p>
                
                <div className="flex items-center justify-between text-xs text-gray-500 mb-3">
                  <span className="bg-gray-100 px-2 py-1 rounded">
                    {episode.category}
                  </span>
                  <span>{episode.duration}</span>
                </div>
                
                <div className="flex items-center justify-between">
                  <div className="flex space-x-2">
                    <button
                      onClick={() => playEpisode(episode)}
                      className="flex items-center space-x-1 text-blue-600 hover:text-blue-700 text-sm font-medium"
                    >
                      <Play className="h-4 w-4" />
                      <span>Play</span>
                    </button>
                    
                    <a
                      href={episode.transcriptUrl}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="flex items-center space-x-1 text-gray-600 hover:text-gray-700 text-sm font-medium"
                    >
                      <BookOpen className="h-4 w-4" />
                      <span>Transcript</span>
                    </a>
                  </div>
                  
                  {userTier !== 'free' && (
                    <button
                      onClick={() => downloadEpisode(episode)}
                      className="flex items-center space-x-1 text-green-600 hover:text-green-700 text-sm font-medium"
                    >
                      <Download className="h-4 w-4" />
                      <span>Download</span>
                    </button>
                  )}
                </div>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Load More Button */}
      {hasMore && !loading && (
        <div className="text-center">
          <button
            onClick={loadMore}
            className="bg-blue-600 hover:bg-blue-700 text-white font-medium py-2 px-6 rounded-lg transition duration-200"
          >
            Load More Episodes
          </button>
        </div>
      )}

      {loading && episodes.length > 0 && (
        <div className="text-center">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600 mx-auto"></div>
        </div>
      )}

      {!loading && episodes.length === 0 && (
        <div className="text-center py-12">
          <p className="text-gray-500 text-lg">No episodes found matching your criteria.</p>
          <p className="text-gray-400 text-sm mt-2">
            Try adjusting your search terms or category filter.
          </p>
        </div>
      )}
    </div>
  )
}
