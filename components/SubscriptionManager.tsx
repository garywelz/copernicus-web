'use client'

import { useState } from 'react'
import { Check, Crown, Star, Zap, AlertCircle } from 'lucide-react'

interface User {
  id: string
  email: string
  subscriptionTier: 'free' | 'premium' | 'research'
  subscriptionStatus: 'active' | 'cancelled' | 'expired'
  podcastsUsed: number
  podcastsLimit: number
}

interface SubscriptionPlan {
  id: string
  name: string
  tier: 'free' | 'premium' | 'research'
  price: number
  podcastsPerMonth: number
  features: string[]
  stripePriceId?: string
}

interface SubscriptionManagerProps {
  user: User | null
  plans: SubscriptionPlan[]
}

export default function SubscriptionManager({ user, plans }: SubscriptionManagerProps) {
  const [isLoading, setIsLoading] = useState(false)
  const [message, setMessage] = useState<{ type: 'success' | 'error', text: string } | null>(null)

  const currentPlan = plans.find(plan => plan.tier === user?.subscriptionTier)
  const availablePlans = plans.filter(plan => plan.tier !== user?.subscriptionTier)

  const handleUpgrade = async (planId: string) => {
    if (!user) return

    setIsLoading(true)
    setMessage(null)

    try {
      const response = await fetch('/api/subscription/manage', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          userEmail: user.email,
          planId,
          action: 'upgrade'
        }),
      })

      const data = await response.json()

      if (response.ok && data.checkoutUrl) {
        window.location.href = data.checkoutUrl
      } else {
        setMessage({ type: 'error', text: data.error || 'Failed to upgrade subscription' })
      }
    } catch (error) {
      setMessage({ type: 'error', text: 'Network error. Please try again.' })
    } finally {
      setIsLoading(false)
    }
  }

  const handleCancel = async () => {
    if (!user) return

    const confirmed = window.confirm(
      'Are you sure you want to cancel your subscription? You will retain access until the end of your billing period.'
    )

    if (!confirmed) return

    setIsLoading(true)
    setMessage(null)

    try {
      const response = await fetch('/api/subscription/manage', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          userEmail: user.email,
          planId: user.subscriptionTier,
          action: 'cancel'
        }),
      })

      const data = await response.json()

      if (response.ok) {
        setMessage({ type: 'success', text: 'Subscription cancelled successfully. You will retain access until the end of your billing period.' })
      } else {
        setMessage({ type: 'error', text: data.error || 'Failed to cancel subscription' })
      }
    } catch (error) {
      setMessage({ type: 'error', text: 'Network error. Please try again.' })
    } finally {
      setIsLoading(false)
    }
  }

  const handleReactivate = async () => {
    if (!user) return

    setIsLoading(true)
    setMessage(null)

    try {
      const response = await fetch('/api/subscription/manage', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          userEmail: user.email,
          planId: user.subscriptionTier,
          action: 'reactivate'
        }),
      })

      const data = await response.json()

      if (response.ok) {
        setMessage({ type: 'success', text: 'Subscription reactivated successfully!' })
      } else {
        setMessage({ type: 'error', text: data.error || 'Failed to reactivate subscription' })
      }
    } catch (error) {
      setMessage({ type: 'error', text: 'Network error. Please try again.' })
    } finally {
      setIsLoading(false)
    }
  }

  const getPlanIcon = (tier: string) => {
    switch (tier) {
      case 'free':
        return <Star className="h-5 w-5 text-gray-600" />
      case 'premium':
        return <Zap className="h-5 w-5 text-blue-600" />
      case 'research':
        return <Crown className="h-5 w-5 text-purple-600" />
      default:
        return <Star className="h-5 w-5 text-gray-600" />
    }
  }

  const getPlanColor = (tier: string) => {
    switch (tier) {
      case 'free':
        return 'border-gray-200 bg-gray-50'
      case 'premium':
        return 'border-blue-200 bg-blue-50'
      case 'research':
        return 'border-purple-200 bg-purple-50'
      default:
        return 'border-gray-200 bg-gray-50'
    }
  }

  return (
    <div className="space-y-8">
      {/* Current Plan */}
      {currentPlan && (
        <div className="bg-white border-2 border-blue-200 rounded-lg p-6">
          <div className="flex items-center justify-between mb-4">
            <div className="flex items-center space-x-3">
              {getPlanIcon(currentPlan.tier)}
              <div>
                <h3 className="text-lg font-semibold text-gray-900">Current Plan</h3>
                <p className="text-sm text-gray-600">{currentPlan.name}</p>
              </div>
            </div>
            <div className="text-right">
              <div className="text-2xl font-bold text-blue-600">
                ${currentPlan.price}/month
              </div>
              <div className="text-sm text-gray-500">
                {currentPlan.podcastsPerMonth === -1 ? 'Unlimited' : `${currentPlan.podcastsPerMonth}/month`}
              </div>
            </div>
          </div>

          <div className="space-y-2 mb-4">
            {currentPlan.features.map((feature, index) => (
              <div key={index} className="flex items-center space-x-2">
                <Check className="h-4 w-4 text-green-600" />
                <span className="text-sm text-gray-700">{feature}</span>
              </div>
            ))}
          </div>

          {user?.subscriptionStatus === 'active' && user.subscriptionTier !== 'free' && (
            <div className="flex space-x-3">
              <button
                onClick={handleCancel}
                disabled={isLoading}
                className="px-4 py-2 text-sm font-medium text-red-600 hover:text-red-700 border border-red-300 rounded-lg hover:bg-red-50 transition duration-200 disabled:opacity-50"
              >
                Cancel Subscription
              </button>
            </div>
          )}

          {user?.subscriptionStatus === 'cancelled' && user.subscriptionTier !== 'free' && (
            <div className="flex items-center space-x-3">
              <AlertCircle className="h-5 w-5 text-orange-500" />
              <span className="text-sm text-orange-700">
                Subscription cancelled. You will retain access until the end of your billing period.
              </span>
              <button
                onClick={handleReactivate}
                disabled={isLoading}
                className="px-4 py-2 text-sm font-medium text-blue-600 hover:text-blue-700 border border-blue-300 rounded-lg hover:bg-blue-50 transition duration-200 disabled:opacity-50"
              >
                Reactivate
              </button>
            </div>
          )}
        </div>
      )}

      {/* Available Plans */}
      <div>
        <h3 className="text-lg font-semibold text-gray-900 mb-4">Available Plans</h3>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          {availablePlans.map((plan) => (
            <div key={plan.id} className={`border rounded-lg p-6 ${getPlanColor(plan.tier)}`}>
              <div className="flex items-center justify-between mb-4">
                <div className="flex items-center space-x-3">
                  {getPlanIcon(plan.tier)}
                  <div>
                    <h4 className="font-semibold text-gray-900">{plan.name}</h4>
                    <p className="text-sm text-gray-600">
                      {plan.podcastsPerMonth === -1 ? 'Unlimited podcasts' : `${plan.podcastsPerMonth} podcasts/month`}
                    </p>
                  </div>
                </div>
                <div className="text-right">
                  <div className="text-xl font-bold text-gray-900">
                    ${plan.price}/month
                  </div>
                </div>
              </div>

              <div className="space-y-2 mb-6">
                {plan.features.map((feature, index) => (
                  <div key={index} className="flex items-center space-x-2">
                    <Check className="h-4 w-4 text-green-600" />
                    <span className="text-sm text-gray-700">{feature}</span>
                  </div>
                ))}
              </div>

              <button
                onClick={() => handleUpgrade(plan.id)}
                disabled={isLoading}
                className={`w-full py-2 px-4 rounded-lg font-medium transition duration-200 disabled:opacity-50 ${
                  plan.tier === 'premium'
                    ? 'bg-blue-600 hover:bg-blue-700 text-white'
                    : 'bg-purple-600 hover:bg-purple-700 text-white'
                }`}
              >
                {isLoading ? 'Processing...' : `Upgrade to ${plan.name}`}
              </button>
            </div>
          ))}
        </div>
      </div>

      {/* Usage Statistics */}
      <div className="bg-gray-50 rounded-lg p-6">
        <h3 className="text-lg font-semibold text-gray-900 mb-4">Usage Statistics</h3>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          <div className="text-center">
            <div className="text-2xl font-bold text-blue-600">{user?.podcastsUsed || 0}</div>
            <div className="text-sm text-gray-600">Podcasts Generated</div>
          </div>
          <div className="text-center">
            <div className="text-2xl font-bold text-green-600">
              {user?.subscriptionTier === 'free' 
                ? `${(user?.podcastsLimit || 2) - (user?.podcastsUsed || 0)}`
                : '∞'
              }
            </div>
            <div className="text-sm text-gray-600">Remaining This Month</div>
          </div>
          <div className="text-center">
            <div className="text-2xl font-bold text-purple-600">
              {user?.subscriptionTier?.charAt(0).toUpperCase() + user?.subscriptionTier?.slice(1)}
            </div>
            <div className="text-sm text-gray-600">Current Tier</div>
          </div>
        </div>
      </div>

      {/* Messages */}
      {message && (
        <div className={`p-4 rounded-lg ${
          message.type === 'success' 
            ? 'bg-green-50 border border-green-200 text-green-800'
            : 'bg-red-50 border border-red-200 text-red-800'
        }`}>
          <div className="flex items-center space-x-2">
            {message.type === 'success' ? (
              <Check className="h-5 w-5" />
            ) : (
              <AlertCircle className="h-5 w-5" />
            )}
            <span className="font-medium">{message.text}</span>
          </div>
        </div>
      )}
    </div>
  )
}
