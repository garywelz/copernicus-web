'use client'

import { useState, useEffect } from 'react'
import { useAuth, SUBSCRIPTION_PLANS } from '@/lib/auth'
import { useSession } from 'next-auth/react'
import PodcastCatalog from '@/components/PodcastCatalog'
import SubscriptionManager from '@/components/SubscriptionManager'
import UserStats from '@/components/UserStats'
import CustomRequestForm from '@/components/CustomRequestForm'

export default function Dashboard() {
  const { user, loading, isAuthenticated, signIn } = useAuth()
  const { data: session } = useSession()
  const [activeTab, setActiveTab] = useState<'catalog' | 'library' | 'requests' | 'subscription'>('catalog')
  const [recentEpisodes, setRecentEpisodes] = useState([])

  useEffect(() => {
    if (user && isAuthenticated) {
      fetchRecentEpisodes()
    }
  }, [user, isAuthenticated])

  const fetchRecentEpisodes = async () => {
    try {
      const response = await fetch(`/api/podcasts/catalog?limit=10&tier=${user?.subscriptionTier}`)
      const data = await response.json()
      setRecentEpisodes(data.episodes || [])
    } catch (error) {
      console.error('Error fetching recent episodes:', error)
    }
  }

  if (loading) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="animate-spin rounded-full h-32 w-32 border-b-2 border-blue-600"></div>
      </div>
    )
  }

  if (!isAuthenticated) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="max-w-md w-full bg-white rounded-lg shadow-md p-8 text-center">
          <h1 className="text-3xl font-bold text-gray-900 mb-4">
            Welcome to Copernicus AI
          </h1>
          <p className="text-gray-600 mb-6">
            Sign in to access your personalized podcast dashboard and start exploring AI-generated research content.
          </p>
          <button
            onClick={() => signIn()}
            className="w-full bg-blue-600 hover:bg-blue-700 text-white font-semibold py-3 px-4 rounded-lg transition duration-200"
          >
            Sign In with Google
          </button>
        </div>
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <header className="bg-white shadow-sm border-b">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex justify-between items-center py-4">
            <div>
              <h1 className="text-2xl font-bold text-gray-900">Copernicus AI Dashboard</h1>
              <p className="text-sm text-gray-600">Welcome back, {user?.name}</p>
            </div>
            <div className="flex items-center space-x-4">
              <a
                href="https://storage.googleapis.com/regal-scholar-453620-r7-podcast-storage/form.html?redirect=true"
                target="_blank"
                rel="noopener noreferrer"
                className="bg-blue-600 hover:bg-blue-700 text-white px-4 py-2 rounded-lg font-medium transition duration-200"
              >
                Create Podcast
              </a>
              <div className="text-right">
                <div className="text-sm font-medium text-gray-900">
                  {user?.subscriptionTier?.charAt(0).toUpperCase() + user?.subscriptionTier?.slice(1)} Plan
                </div>
                <div className="text-xs text-gray-500">
                  {user?.subscriptionTier === 'free' 
                    ? `${user?.podcastsUsed}/${user?.podcastsLimit} podcasts used`
                    : 'Unlimited access'
                  }
                </div>
              </div>
              <img
                src={session?.user?.image || '/default-avatar.png'}
                alt="Profile"
                className="h-10 w-10 rounded-full"
              />
            </div>
          </div>
        </div>
      </header>

      {/* Navigation Tabs */}
      <nav className="bg-white border-b">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex space-x-8">
            {[
              { id: 'catalog', label: 'Podcast Catalog', icon: '🎙️' },
              { id: 'library', label: 'My Library', icon: '📚' },
              { id: 'requests', label: 'Custom Requests', icon: '✨' },
              { id: 'subscription', label: 'Subscription', icon: '⚙️' }
            ].map((tab) => (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id as any)}
                className={`py-4 px-1 border-b-2 font-medium text-sm transition-colors ${
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
        {activeTab === 'catalog' && (
          <div className="space-y-6">
            <div className="bg-white rounded-lg shadow p-6">
              <h2 className="text-xl font-semibold text-gray-900 mb-4">
                🎙️ AI-Generated Podcast Catalog
              </h2>
              <p className="text-gray-600 mb-6">
                Explore our collection of AI-generated research podcasts across various scientific disciplines.
              </p>
              <PodcastCatalog userTier={user?.subscriptionTier} />
            </div>
          </div>
        )}

        {activeTab === 'library' && (
          <div className="space-y-6">
            <div className="bg-white rounded-lg shadow p-6">
              <h2 className="text-xl font-semibold text-gray-900 mb-4">
                📚 My Library
              </h2>
              <UserStats user={user} />
              
              <div className="mt-6">
                <h3 className="text-lg font-medium text-gray-900 mb-4">
                  Recently Generated Episodes
                </h3>
                {recentEpisodes.length > 0 ? (
                  <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                    {recentEpisodes.map((episode: any) => (
                      <div key={episode.id} className="border rounded-lg p-4 hover:shadow-md transition-shadow">
                        <img
                          src={episode.thumbnailUrl}
                          alt={episode.title}
                          className="w-full h-32 object-cover rounded mb-3"
                        />
                        <h4 className="font-medium text-gray-900 mb-2">{episode.title}</h4>
                        <p className="text-sm text-gray-600 mb-2">{episode.topic}</p>
                        <div className="flex justify-between items-center">
                          <span className="text-xs text-gray-500">{episode.category}</span>
                          <span className="text-xs text-gray-500">{episode.duration}</span>
                        </div>
                      </div>
                    ))}
                  </div>
                ) : (
                  <p className="text-gray-500 text-center py-8">
                    No episodes generated yet. Start by requesting a custom podcast!
                  </p>
                )}
              </div>
            </div>
          </div>
        )}

        {activeTab === 'requests' && (
          <div className="space-y-6">
            <div className="bg-white rounded-lg shadow p-6">
              <h2 className="text-xl font-semibold text-gray-900 mb-4">
                ✨ Custom Podcast Requests
              </h2>
              <CustomRequestForm user={user} />
            </div>
          </div>
        )}

        {activeTab === 'subscription' && (
          <div className="space-y-6">
            <div className="bg-white rounded-lg shadow p-6">
              <h2 className="text-xl font-semibold text-gray-900 mb-4">
                ⚙️ Subscription Management
              </h2>
              <SubscriptionManager user={user} plans={SUBSCRIPTION_PLANS} />
            </div>
          </div>
        )}
      </main>
    </div>
  )
}
