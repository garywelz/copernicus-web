import { signIn, signOut, useSession } from 'next-auth/react'
import { useState, useEffect } from 'react'

export interface User {
  id: string
  email: string
  name: string
  subscriptionTier: 'free' | 'premium' | 'research'
  subscriptionStatus: 'active' | 'cancelled' | 'expired'
  podcastsUsed: number
  podcastsLimit: number
  createdAt: Date
  lastLogin: Date
}

export interface SubscriptionPlan {
  id: string
  name: string
  tier: 'free' | 'premium' | 'research'
  price: number
  podcastsPerMonth: number
  features: string[]
  stripePriceId?: string
}

export const SUBSCRIPTION_PLANS: SubscriptionPlan[] = [
  {
    id: 'free',
    name: 'Free Tier',
    tier: 'free',
    price: 0,
    podcastsPerMonth: 10,
    features: [
      '10 AI-generated podcasts per month',
      'Basic catalog access',
      'Standard audio quality',
      'Community support'
    ]
  },
  {
    id: 'premium',
    name: 'Premium',
    tier: 'premium',
    price: 9.99,
    podcastsPerMonth: -1, // unlimited
    features: [
      'Unlimited AI-generated podcasts',
      'Full catalog access',
      'High-quality audio',
      'Download for offline listening',
      'Priority support',
      'Advanced search & filters'
    ],
    stripePriceId: 'price_premium_monthly'
  },
  {
    id: 'research',
    name: 'Research Pro',
    tier: 'research',
    price: 29.99,
    podcastsPerMonth: -1, // unlimited
    features: [
      'Unlimited AI-generated podcasts',
      'Custom topic requests',
      'Priority generation queue',
      'Research paper analysis',
      'Advanced AI features',
      'API access',
      'White-label options'
    ],
    stripePriceId: 'price_research_monthly'
  }
]

export function useAuth() {
  const { data: session, status } = useSession()
  const [user, setUser] = useState<User | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    // Check for demo mode first
    if (typeof window !== 'undefined') {
      const demoSession = localStorage.getItem('demo-session')
      if (demoSession && !session) {
        try {
          const demoData = JSON.parse(demoSession)
          const demoUser: User = {
            id: 'demo-user',
            email: 'demo@copernicus-ai.com',
            name: 'Demo User',
            subscriptionTier: 'free',
            subscriptionStatus: 'active',
            podcastsUsed: 3,
            podcastsLimit: 10,
            createdAt: new Date().toISOString(),
            lastLogin: new Date().toISOString()
          }
          setUser(demoUser)
          setLoading(false)
          return
        } catch (error) {
          localStorage.removeItem('demo-session')
        }
      }
    }

    if (session?.user) {
      // Fetch user subscription data
      fetchUserData(session.user.email!)
        .then(setUser)
        .catch(console.error)
        .finally(() => setLoading(false))
    } else {
      setLoading(false)
    }
  }, [session])

  const handleSignOut = () => {
    if (typeof window !== 'undefined') {
      localStorage.removeItem('demo-session')
    }
    signOut()
  }

  return {
    user,
    session,
    loading,
    isAuthenticated: !!session || !!user,
    signIn: () => signIn('google'),
    signOut: handleSignOut
  }
}

async function fetchUserData(email: string): Promise<User> {
  const response = await fetch('/api/user/profile', {
    headers: { 'Authorization': `Bearer ${email}` }
  })
  
  if (!response.ok) {
    throw new Error('Failed to fetch user data')
  }
  
  return response.json()
}

export async function checkSubscriptionAccess(
  user: User,
  action: 'generate_podcast' | 'download_audio' | 'custom_request'
): Promise<boolean> {
  // Check subscription tier and limits
  switch (action) {
    case 'generate_podcast':
      if (user.subscriptionTier === 'free') {
        return user.podcastsUsed < user.podcastsLimit
      }
      return user.subscriptionStatus === 'active'
    
    case 'download_audio':
      return user.subscriptionTier !== 'free'
    
    case 'custom_request':
      return user.subscriptionTier === 'research'
    
    default:
      return false
  }
}
