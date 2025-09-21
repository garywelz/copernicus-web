'use client'

import { useState } from 'react'
import { AlertCircle, CheckCircle } from 'lucide-react'

export default function SignInPage() {
  const [isDemoMode, setIsDemoMode] = useState(false)

  const handleDemoLogin = () => {
    // Set demo user data in localStorage for testing
    const demoUser = {
      user: {
        id: 'demo-user',
        email: 'demo@copernicus-ai.com',
        name: 'Demo User',
        image: null
      },
      expires: new Date(Date.now() + 24 * 60 * 60 * 1000).toISOString() // 24 hours
    }
    
    localStorage.setItem('demo-session', JSON.stringify(demoUser))
    window.location.href = '/dashboard'
  }

  return (
    <div className="min-h-screen bg-gray-50 flex items-center justify-center">
      <div className="max-w-md w-full bg-white rounded-lg shadow-md p-8">
        <div className="text-center mb-8">
          <h1 className="text-3xl font-bold text-gray-900 mb-2">
            Copernicus AI
          </h1>
          <p className="text-gray-600">
            Sign in to access your podcast dashboard
          </p>
        </div>

        {/* Environment Setup Warning */}
        <div className="mb-6 p-4 bg-yellow-50 border border-yellow-200 rounded-lg">
          <div className="flex items-start space-x-3">
            <AlertCircle className="h-5 w-5 text-yellow-600 mt-0.5" />
            <div>
              <h3 className="text-sm font-medium text-yellow-800">
                Setup Required
              </h3>
              <p className="text-sm text-yellow-700 mt-1">
                Google OAuth credentials need to be configured. For now, you can use Demo Mode to test the interface.
              </p>
            </div>
          </div>
        </div>

        {/* Demo Mode Button */}
        <div className="space-y-4">
          <button
            onClick={handleDemoLogin}
            className="w-full bg-blue-600 hover:bg-blue-700 text-white font-semibold py-3 px-4 rounded-lg transition duration-200 flex items-center justify-center space-x-2"
          >
            <CheckCircle className="h-5 w-5" />
            <span>Continue with Demo Mode</span>
          </button>

          <div className="text-center">
            <p className="text-sm text-gray-500">
              Demo mode uses a test account to explore the interface
            </p>
            <p className="text-sm text-gray-600 mt-2">
              Want to create a real account?{' '}
              <a
                href="/auth/signup"
                className="text-blue-600 hover:text-blue-500 font-medium"
              >
                Sign up here
              </a>
            </p>
          </div>
        </div>

        {/* Setup Instructions */}
        <div className="mt-8 p-4 bg-gray-50 rounded-lg">
          <h3 className="text-sm font-medium text-gray-900 mb-2">
            To enable Google Sign-In:
          </h3>
          <ol className="text-xs text-gray-600 space-y-1 list-decimal list-inside">
            <li>Go to Google Cloud Console</li>
            <li>Create OAuth 2.0 credentials</li>
            <li>Add authorized redirect URI: <code className="bg-gray-200 px-1 rounded">http://localhost:3000/api/auth/callback/google</code></li>
            <li>Create <code className="bg-gray-200 px-1 rounded">.env.local</code> with your credentials</li>
          </ol>
        </div>
      </div>
    </div>
  )
}
