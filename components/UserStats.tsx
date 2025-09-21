'use client'

import { useState, useEffect } from 'react'
import { TrendingUp, Clock, Star, Download } from 'lucide-react'

interface User {
  id: string
  email: string
  subscriptionTier: 'free' | 'premium' | 'research'
  podcastsUsed: number
  podcastsLimit: number
  createdAt: string
}

interface UserStatsProps {
  user: User | null
}

interface UserAnalytics {
  totalEpisodes: number
  totalListeningTime: number
  favoriteCategory: string
  recentActivity: any[]
}

export default function UserStats({ user }: UserStatsProps) {
  const [analytics, setAnalytics] = useState<UserAnalytics | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    if (user) {
      fetchUserAnalytics()
    }
  }, [user])

  const fetchUserAnalytics = async () => {
    try {
      const response = await fetch(`/api/user/analytics?email=${user?.email}`)
      if (response.ok) {
        const data = await response.json()
        setAnalytics(data)
      }
    } catch (error) {
      console.error('Error fetching user analytics:', error)
    } finally {
      setLoading(false)
    }
  }

  const getUsagePercentage = () => {
    if (!user || user.subscriptionTier !== 'free') return 0
    return Math.round((user.podcastsUsed / user.podcastsLimit) * 100)
  }

  const getTierBadge = () => {
    const colors = {
      free: 'bg-gray-100 text-gray-800',
      premium: 'bg-blue-100 text-blue-800',
      research: 'bg-purple-100 text-purple-800'
    }
    
    return colors[user?.subscriptionTier || 'free']
  }

  if (loading) {
    return (
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        {[...Array(4)].map((_, i) => (
          <div key={i} className="bg-gray-200 animate-pulse rounded-lg h-24"></div>
        ))}
      </div>
    )
  }

  return (
    <div className="space-y-6">
      {/* Quick Stats */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        <div className="bg-white border border-gray-200 rounded-lg p-4">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm font-medium text-gray-600">Podcasts Generated</p>
              <p className="text-2xl font-bold text-gray-900">{user?.podcastsUsed || 0}</p>
            </div>
            <TrendingUp className="h-8 w-8 text-blue-600" />
          </div>
        </div>

        <div className="bg-white border border-gray-200 rounded-lg p-4">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm font-medium text-gray-600">Subscription Tier</p>
              <div className="mt-1">
                <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${getTierBadge()}`}>
                  {user?.subscriptionTier?.charAt(0).toUpperCase() + user?.subscriptionTier?.slice(1)}
                </span>
              </div>
            </div>
            <Star className="h-8 w-8 text-yellow-600" />
          </div>
        </div>

        <div className="bg-white border border-gray-200 rounded-lg p-4">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm font-medium text-gray-600">Monthly Limit</p>
              <p className="text-2xl font-bold text-gray-900">
                {user?.subscriptionTier === 'free' 
                  ? `${user?.podcastsLimit - (user?.podcastsUsed || 0)}/${user?.podcastsLimit}`
                  : '∞'
                }
              </p>
            </div>
            <Clock className="h-8 w-8 text-green-600" />
          </div>
        </div>

        <div className="bg-white border border-gray-200 rounded-lg p-4">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm font-medium text-gray-600">Member Since</p>
              <p className="text-sm font-bold text-gray-900">
                {user?.createdAt ? new Date(user.createdAt).toLocaleDateString() : 'N/A'}
              </p>
            </div>
            <Download className="h-8 w-8 text-purple-600" />
          </div>
        </div>
      </div>

      {/* Usage Progress Bar (Free Tier Only) */}
      {user?.subscriptionTier === 'free' && (
        <div className="bg-white border border-gray-200 rounded-lg p-6">
          <h3 className="text-lg font-medium text-gray-900 mb-4">Monthly Usage</h3>
          <div className="space-y-3">
            <div className="flex justify-between text-sm">
              <span className="text-gray-600">Podcasts Generated</span>
              <span className="font-medium text-gray-900">
                {user?.podcastsUsed || 0} / {user?.podcastsLimit || 2}
              </span>
            </div>
            <div className="w-full bg-gray-200 rounded-full h-2">
              <div 
                className="bg-blue-600 h-2 rounded-full transition-all duration-300"
                style={{ width: `${getUsagePercentage()}%` }}
              ></div>
            </div>
            <p className="text-sm text-gray-600">
              {getUsagePercentage()}% of monthly limit used
              {getUsagePercentage() >= 80 && (
                <span className="text-orange-600 font-medium ml-2">
                  - Consider upgrading for unlimited access
                </span>
              )}
            </p>
          </div>
        </div>
      )}

      {/* Analytics (if available) */}
      {analytics && (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          <div className="bg-white border border-gray-200 rounded-lg p-6">
            <h3 className="text-lg font-medium text-gray-900 mb-4">Listening Habits</h3>
            <div className="space-y-3">
              <div className="flex justify-between">
                <span className="text-sm text-gray-600">Total Listening Time</span>
                <span className="text-sm font-medium text-gray-900">
                  {Math.round(analytics.totalListeningTime / 60)} minutes
                </span>
              </div>
              <div className="flex justify-between">
                <span className="text-sm text-gray-600">Favorite Category</span>
                <span className="text-sm font-medium text-gray-900">{analytics.favoriteCategory}</span>
              </div>
            </div>
          </div>

          <div className="bg-white border border-gray-200 rounded-lg p-6">
            <h3 className="text-lg font-medium text-gray-900 mb-4">Recent Activity</h3>
            <div className="space-y-2">
              {analytics.recentActivity.slice(0, 3).map((activity, index) => (
                <div key={index} className="flex items-center justify-between text-sm">
                  <span className="text-gray-600">{activity.action}</span>
                  <span className="text-gray-900">{activity.timestamp}</span>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}

      {/* Upgrade Prompt (Free Tier) */}
      {user?.subscriptionTier === 'free' && (
        <div className="bg-gradient-to-r from-blue-50 to-purple-50 border border-blue-200 rounded-lg p-6">
          <div className="flex items-center justify-between">
            <div>
              <h3 className="text-lg font-semibold text-gray-900">Unlock Premium Features</h3>
              <p className="text-sm text-gray-600 mt-1">
                Upgrade to Premium or Research Pro for unlimited podcast generation and advanced features.
              </p>
            </div>
            <button className="bg-blue-600 hover:bg-blue-700 text-white font-medium py-2 px-4 rounded-lg transition duration-200">
              View Plans
            </button>
          </div>
        </div>
      )}
    </div>
  )
}
