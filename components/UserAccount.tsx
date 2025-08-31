'use client'

import { useState, useEffect } from 'react'
import { User, Podcast, Playlist } from '@/types/user'

interface UserAccountProps {
  user: User
  onUpdateProfile: (updates: Partial<User>) => void
  onDeleteAccount: () => void
}

export default function UserAccount({ user, onUpdateProfile, onDeleteAccount }: UserAccountProps) {
  const [activeTab, setActiveTab] = useState<'profile' | 'podcasts' | 'playlists' | 'settings'>('profile')
  const [isEditing, setIsEditing] = useState(false)
  const [formData, setFormData] = useState({
    displayName: user.displayName || '',
    bio: user.bio || '',
    website: user.website || '',
    location: user.location || '',
    researchInterests: user.researchInterests || []
  })

  const tabs = [
    { id: 'profile', label: 'Profile', icon: '👤' },
    { id: 'podcasts', label: 'My Podcasts', icon: '🎙️' },
    { id: 'playlists', label: 'Playlists', icon: '📚' },
    { id: 'settings', label: 'Settings', icon: '⚙️' }
  ]

  const handleSave = () => {
    onUpdateProfile(formData)
    setIsEditing(false)
  }

  return (
    <div className="max-w-6xl mx-auto p-6">
      {/* Header */}
      <div className="flex items-center gap-6 mb-8">
        <div className="w-24 h-24 bg-gradient-to-br from-blue-500 to-purple-600 rounded-full flex items-center justify-center text-white text-3xl font-bold">
          {user.displayName?.charAt(0) || user.email.charAt(0).toUpperCase()}
        </div>
        <div>
          <h1 className="text-3xl font-bold">{user.displayName || 'User'}</h1>
          <p className="text-gray-600">{user.email}</p>
          <div className="flex items-center gap-4 mt-2">
            <span className="px-3 py-1 bg-blue-100 text-blue-800 rounded-full text-sm">
              {user.membershipTier} Member
            </span>
            <span className="text-gray-500">
              {user.episodesGenerated} episodes generated
            </span>
          </div>
        </div>
      </div>

      {/* Tabs */}
      <div className="border-b border-gray-200 mb-8">
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

      {/* Tab Content */}
      <div className="min-h-[400px]">
        {activeTab === 'profile' && (
          <div className="max-w-2xl">
            <div className="flex items-center justify-between mb-6">
              <h2 className="text-2xl font-bold">Profile Information</h2>
              <button
                onClick={() => setIsEditing(!isEditing)}
                className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700"
              >
                {isEditing ? 'Cancel' : 'Edit Profile'}
              </button>
            </div>

            {isEditing ? (
              <div className="space-y-6">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    Display Name
                  </label>
                  <input
                    type="text"
                    value={formData.displayName}
                    onChange={(e) => setFormData({ ...formData, displayName: e.target.value })}
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                  />
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    Bio
                  </label>
                  <textarea
                    value={formData.bio}
                    onChange={(e) => setFormData({ ...formData, bio: e.target.value })}
                    rows={4}
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                    placeholder="Tell us about your research interests..."
                  />
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    Website
                  </label>
                  <input
                    type="url"
                    value={formData.website}
                    onChange={(e) => setFormData({ ...formData, website: e.target.value })}
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                    placeholder="https://your-website.com"
                  />
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    Location
                  </label>
                  <input
                    type="text"
                    value={formData.location}
                    onChange={(e) => setFormData({ ...formData, location: e.target.value })}
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                    placeholder="City, Country"
                  />
                </div>

                <div className="flex gap-3">
                  <button
                    onClick={handleSave}
                    className="px-6 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700"
                  >
                    Save Changes
                  </button>
                  <button
                    onClick={() => setIsEditing(false)}
                    className="px-6 py-2 bg-gray-300 text-gray-700 rounded-lg hover:bg-gray-400"
                  >
                    Cancel
                  </button>
                </div>
              </div>
            ) : (
              <div className="space-y-6">
                <div>
                  <h3 className="text-lg font-semibold mb-2">Display Name</h3>
                  <p className="text-gray-700">{formData.displayName || 'Not set'}</p>
                </div>

                <div>
                  <h3 className="text-lg font-semibold mb-2">Bio</h3>
                  <p className="text-gray-700">{formData.bio || 'No bio added yet'}</p>
                </div>

                <div>
                  <h3 className="text-lg font-semibold mb-2">Website</h3>
                  <p className="text-gray-700">
                    {formData.website ? (
                      <a href={formData.website} target="_blank" rel="noopener noreferrer" className="text-blue-600 hover:underline">
                        {formData.website}
                      </a>
                    ) : (
                      'Not set'
                    )}
                  </p>
                </div>

                <div>
                  <h3 className="text-lg font-semibold mb-2">Location</h3>
                  <p className="text-gray-700">{formData.location || 'Not set'}</p>
                </div>
              </div>
            )}
          </div>
        )}

        {activeTab === 'podcasts' && (
          <div>
            <div className="flex items-center justify-between mb-6">
              <h2 className="text-2xl font-bold">My Podcasts</h2>
              <div className="flex gap-3">
                <select className="px-3 py-2 border border-gray-300 rounded-lg">
                  <option>All Podcasts</option>
                  <option>Published</option>
                  <option>Drafts</option>
                  <option>Private</option>
                </select>
                <button className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700">
                  Create New Podcast
                </button>
              </div>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
              {/* Podcast cards would go here */}
              <div className="bg-white rounded-lg shadow-md p-4">
                <div className="aspect-video bg-gray-200 rounded-lg mb-4"></div>
                <h3 className="font-semibold mb-2">Sample Podcast Title</h3>
                <p className="text-sm text-gray-600 mb-3">Published • 2 days ago</p>
                <div className="flex items-center justify-between">
                  <span className="text-sm text-gray-500">1.2K views</span>
                  <div className="flex gap-2">
                    <button className="px-3 py-1 text-sm bg-gray-100 text-gray-700 rounded hover:bg-gray-200">
                      Edit
                    </button>
                    <button className="px-3 py-1 text-sm bg-red-100 text-red-700 rounded hover:bg-red-200">
                      Delete
                    </button>
                  </div>
                </div>
              </div>
            </div>
          </div>
        )}

        {activeTab === 'playlists' && (
          <div>
            <div className="flex items-center justify-between mb-6">
              <h2 className="text-2xl font-bold">My Playlists</h2>
              <button className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700">
                Create Playlist
              </button>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
              {/* Playlist cards would go here */}
              <div className="bg-white rounded-lg shadow-md p-4">
                <div className="aspect-video bg-gradient-to-br from-purple-400 to-pink-400 rounded-lg mb-4 flex items-center justify-center text-white text-2xl">
                  📚
                </div>
                <h3 className="font-semibold mb-2">My Research Collection</h3>
                <p className="text-sm text-gray-600 mb-3">15 episodes • Private</p>
                <div className="flex gap-2">
                  <button className="px-3 py-1 text-sm bg-gray-100 text-gray-700 rounded hover:bg-gray-200">
                    Edit
                  </button>
                  <button className="px-3 py-1 text-sm bg-blue-100 text-blue-700 rounded hover:bg-blue-200">
                    Share
                  </button>
                </div>
              </div>
            </div>
          </div>
        )}

        {activeTab === 'settings' && (
          <div className="max-w-2xl">
            <h2 className="text-2xl font-bold mb-6">Account Settings</h2>
            
            <div className="space-y-6">
              <div className="border border-gray-200 rounded-lg p-6">
                <h3 className="text-lg font-semibold mb-4">Privacy Settings</h3>
                <div className="space-y-4">
                  <div className="flex items-center justify-between">
                    <div>
                      <p className="font-medium">Profile Visibility</p>
                      <p className="text-sm text-gray-600">Control who can see your profile</p>
                    </div>
                    <select className="px-3 py-2 border border-gray-300 rounded-lg">
                      <option>Public</option>
                      <option>Private</option>
                      <option>Friends Only</option>
                    </select>
                  </div>
                  
                  <div className="flex items-center justify-between">
                    <div>
                      <p className="font-medium">Podcast Visibility</p>
                      <p className="text-sm text-gray-600">Default visibility for new podcasts</p>
                    </div>
                    <select className="px-3 py-2 border border-gray-300 rounded-lg">
                      <option>Public</option>
                      <option>Unlisted</option>
                      <option>Private</option>
                    </select>
                  </div>
                </div>
              </div>

              <div className="border border-gray-200 rounded-lg p-6">
                <h3 className="text-lg font-semibold mb-4">Notification Preferences</h3>
                <div className="space-y-4">
                  <div className="flex items-center justify-between">
                    <div>
                      <p className="font-medium">Email Notifications</p>
                      <p className="text-sm text-gray-600">Receive email updates about your podcasts</p>
                    </div>
                    <input type="checkbox" className="w-4 h-4 text-blue-600" defaultChecked />
                  </div>
                  
                  <div className="flex items-center justify-between">
                    <div>
                      <p className="font-medium">Podcast Completion Alerts</p>
                      <p className="text-sm text-gray-600">Get notified when your podcasts are ready</p>
                    </div>
                    <input type="checkbox" className="w-4 h-4 text-blue-600" defaultChecked />
                  </div>
                </div>
              </div>

              <div className="border border-red-200 rounded-lg p-6">
                <h3 className="text-lg font-semibold mb-4 text-red-600">Danger Zone</h3>
                <div className="space-y-4">
                  <div>
                    <p className="font-medium text-red-600">Delete Account</p>
                    <p className="text-sm text-gray-600 mb-3">
                      This action cannot be undone. All your data will be permanently deleted.
                    </p>
                    <button
                      onClick={onDeleteAccount}
                      className="px-4 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700"
                    >
                      Delete Account
                    </button>
                  </div>
                </div>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
