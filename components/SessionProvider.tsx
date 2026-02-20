'use client'

import { SessionProvider as NextAuthSessionProvider } from 'next-auth/react'
import { useState, useEffect } from 'react'

export function SessionProvider({ children }: { children: React.ReactNode }) {
  const [hasError, setHasError] = useState(false)

  useEffect(() => {
    // Check if NextAuth is properly configured
    if (!process.env.NEXT_PUBLIC_NEXTAUTH_URL && typeof window !== 'undefined') {
      // NextAuth not configured - render without session provider
      setHasError(true)
    }
  }, [])

  // If NextAuth is not configured or has errors, just render children
  // This allows the Knowledge Engine to work without authentication
  if (hasError || (!process.env.NEXT_PUBLIC_NEXTAUTH_URL && typeof window !== 'undefined')) {
    return <>{children}</>
  }

  return (
    <NextAuthSessionProvider>
      {children}
    </NextAuthSessionProvider>
  )
}
