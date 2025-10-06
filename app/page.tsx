'use client'

import { useState } from 'react'
import { useAuth } from '@/lib/auth'
import { useRouter } from 'next/navigation'
import Image from 'next/image'
import { Plus, ExternalLink, UserPlus, LogIn } from 'lucide-react'

export default function Home() {
  const { user, isAuthenticated, loading } = useAuth()
  const router = useRouter()
  const [showAuthMessage, setShowAuthMessage] = useState(false)

  const handleCreatePodcast = () => {
    if (isAuthenticated) {
      // Redirect to the podcast creation form for authenticated users
      window.open('https://storage.googleapis.com/regal-scholar-453620-r7-podcast-storage/form.html', '_blank')
    } else {
      // Show message for non-authenticated users
      setShowAuthMessage(true)
      setTimeout(() => setShowAuthMessage(false), 3000)
    }
  }

  const handleCreateAccount = () => {
    router.push('/auth/signup')
  }

  const handleSignIn = () => {
    router.push('/auth/signin')
  }

  // Use the same data as the PodcastHeader component
  const imageUrl = "https://storage.googleapis.com/regal-scholar-453620-r7-podcast-storage/images/copernicus-original-portrait-optimized.jpg"
  const title = "Copernicus AI: Frontiers of Research"
  const description = "Educational podcast covering the latest breakthroughs in science, technology, mathematics, and research. Join us as we explore cutting-edge discoveries and their implications for the future."
  const spotifyUrl = "https://open.spotify.com/show/your-spotify-url" // You can add your actual Spotify URL here

  if (loading) {
      return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto"></div>
          <p className="mt-4 text-gray-600">Loading...</p>
            </div>
          </div>
    )
    }

    return (
    <div className="min-h-screen bg-gray-50">
      <div className="max-w-6xl mx-auto px-4 py-12">
        {/* Main Podcast Section */}
        <div className="flex flex-col md:flex-row gap-8 items-start mb-16">
          <div className="relative w-72 h-72 shrink-0">
            <Image
              src={imageUrl}
              alt={title}
              fill
              className="object-cover rounded-md"
              priority
            />
          </div>

          <div className="flex-1">
            <h1 className="text-4xl font-bold mb-2">{title}</h1>
            
            {/* Removed the "Podcast" oval as requested */}
            
            <p className="text-lg mb-8">{description}</p>

            <div className="flex flex-wrap gap-3 mb-4">
              <button
                onClick={handleCreatePodcast}
                className="inline-flex items-center px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-md font-medium transition-colors"
              >
                <Plus className="mr-2 h-4 w-4" />
                Create Podcast
              </button>
              
              <button
                onClick={handleCreateAccount}
                className="inline-flex items-center px-4 py-2 bg-green-600 hover:bg-green-700 text-white rounded-md font-medium transition-colors"
              >
                <UserPlus className="mr-2 h-4 w-4" />
                Create Account
              </button>

              {!isAuthenticated && (
                <button
                  onClick={handleSignIn}
                  className="inline-flex items-center px-4 py-2 bg-gray-600 hover:bg-gray-700 text-white rounded-md font-medium transition-colors"
                >
                  <LogIn className="mr-2 h-4 w-4" />
                  Sign In
                </button>
              )}

              {spotifyUrl && (
                <a
                  href={spotifyUrl}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="inline-flex items-center px-4 py-2 bg-green-600 hover:bg-green-700 text-white rounded-md font-medium transition-colors"
                >
                  <ExternalLink className="mr-2 h-4 w-4" />
                  Follow on Spotify
                </a>
              )}
            </div>

            {/* Authentication Message */}
            {showAuthMessage && (
              <div className="mt-4 p-4 bg-yellow-50 border border-yellow-200 rounded-md">
                <p className="text-yellow-800">
                  <strong>Account Required:</strong> Podcast creation is for account holders only. 
                  Please <button onClick={handleCreateAccount} className="underline font-medium">create an account</button> or <button onClick={handleSignIn} className="underline font-medium">sign in</button> to access podcast creation.
                </p>
              </div>
            )}

            {/* Welcome message for authenticated users */}
            {isAuthenticated && user && (
              <div className="mt-4 p-4 bg-blue-50 border border-blue-200 rounded-md">
                <p className="text-blue-800">
                  Welcome back, <strong>{user.name}</strong>! You can now create podcasts and access your dashboard.
                </p>
                <button
                  onClick={() => router.push('/dashboard')}
                  className="mt-2 text-blue-600 hover:text-blue-800 underline font-medium"
                >
                  Go to Dashboard →
                </button>
              </div>
            )}
          </div>
        </div>

        {/* Browse by Subject Section */}
        <div>
          <h2 className="text-3xl font-bold mb-8">Browse by Subject</h2>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {[
              { name: "Computer Science", episodes: 12, color: "bg-blue-100 text-blue-800" },
              { name: "Physics", episodes: 8, color: "bg-purple-100 text-purple-800" },
              { name: "Biology", episodes: 15, color: "bg-green-100 text-green-800" },
              { name: "Chemistry", episodes: 6, color: "bg-orange-100 text-orange-800" },
              { name: "Mathematics", episodes: 10, color: "bg-red-100 text-red-800" },
              { name: "Engineering", episodes: 7, color: "bg-gray-100 text-gray-800" },
            ].map((subject) => (
              <div key={subject.name} className="bg-white rounded-lg shadow-md p-6 hover:shadow-lg transition-shadow">
                <h3 className="text-xl font-semibold mb-2">{subject.name}</h3>
                <p className="text-gray-600 mb-3">{subject.episodes} episodes</p>
                <span className={`inline-block px-3 py-1 rounded-full text-sm font-medium ${subject.color}`}>
                  {subject.name}
                </span>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  )
}