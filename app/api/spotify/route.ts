import { getAccessToken } from '@/lib/spotify'
import { NextResponse } from 'next/server'

export const dynamic = 'force-dynamic'

export async function GET() {
  try {
    const token = await getAccessToken()
    return NextResponse.json({ accessToken: token })
  } catch (error) {
    console.error('Error getting Spotify access token:', error)
    return NextResponse.json(
      { error: 'Failed to get Spotify access token' },
      { status: 500 }
    )
  }
} 