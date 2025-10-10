import { NextRequest, NextResponse } from 'next/server'
import { google } from 'googleapis'

// Initialize Firestore
const { initializeApp, cert } = require('firebase-admin/app')
const { getFirestore } = require('firebase-admin/firestore')

// Extend global type
declare global {
  var firebaseApp: any
}

if (!global.firebaseApp) {
  // Use environment variables for Firebase credentials
  const serviceAccount = {
    type: "service_account",
    project_id: process.env.FIREBASE_PROJECT_ID,
    private_key_id: process.env.FIREBASE_PRIVATE_KEY_ID,
    private_key: process.env.FIREBASE_PRIVATE_KEY?.replace(/\\n/g, '\n'),
    client_email: process.env.FIREBASE_CLIENT_EMAIL,
    client_id: process.env.FIREBASE_CLIENT_ID,
    auth_uri: "https://accounts.google.com/o/oauth2/auth",
    token_uri: "https://oauth2.googleapis.com/token",
    auth_provider_x509_cert_url: "https://www.googleapis.com/oauth2/v1/certs",
    client_x509_cert_url: `https://www.googleapis.com/robot/v1/metadata/x509/${process.env.FIREBASE_CLIENT_EMAIL}`
  }
  
  if (!serviceAccount.project_id || !serviceAccount.private_key || !serviceAccount.client_email) {
    console.error('Missing Firebase environment variables')
    throw new Error('Firebase credentials not configured')
  }
  
  global.firebaseApp = initializeApp({
    credential: cert(serviceAccount)
  })
}

const db = getFirestore(global.firebaseApp)

export async function GET(request: NextRequest) {
  try {
    const { searchParams } = new URL(request.url)
    const category = searchParams.get('category')
    const search = searchParams.get('search')
    const page = parseInt(searchParams.get('page') || '1')
    const limit = parseInt(searchParams.get('limit') || '20')
    const tier = searchParams.get('tier') || 'free'

    let query = db.collection('podcast_jobs')
      .where('status', '==', 'completed')
      .orderBy('updated_at', 'desc')

    // Apply filters
    if (category && category !== 'all') {
      query = query.where('request.category', '==', category)
    }

    const snapshot = await query.limit(limit * page).get()
    let episodes: any[] = []

    snapshot.forEach((doc: any) => {
      const data = doc.data()
      if (data.result) {
        episodes.push({
          id: doc.id,
          title: data.result.title,
          topic: data.result.topic,
          category: data.request.category,
          duration: data.result.duration,
          audioUrl: data.result.audio_url,
          thumbnailUrl: data.result.thumbnail_url,
          transcriptUrl: data.result.transcript_url,
          descriptionUrl: data.result.description_url,
          canonicalFilename: data.result.canonical_filename,
          expertiseLevel: data.request.expertise_level,
          formatType: data.request.format_type,
          generatedAt: data.result.generated_at,
          hasResearchPaper: data.result.has_research_paper,
          paperTitle: data.result.paper_title,
          // Access control
          requiresPremium: data.request.expertise_level === 'expert' || 
                          data.request.format_type === 'research',
          requiresResearch: data.request.format_type === 'research'
        })
      }
    })

    // Apply search filter
    if (search) {
      const searchLower = search.toLowerCase()
      episodes = episodes.filter(episode => 
        episode.title.toLowerCase().includes(searchLower) ||
        episode.topic.toLowerCase().includes(searchLower) ||
        episode.category.toLowerCase().includes(searchLower)
      )
    }

    // Apply tier-based access control
    episodes = episodes.filter(episode => {
      if (episode.requiresResearch && tier !== 'research') return false
      if (episode.requiresPremium && tier === 'free') return false
      return true
    })

    // Pagination
    const startIndex = (page - 1) * limit
    const endIndex = startIndex + limit
    const paginatedEpisodes = episodes.slice(startIndex, endIndex)

    // Get categories for filter
    const categories = Array.from(new Set(episodes.map((ep: any) => ep.category)))

    return NextResponse.json({
      episodes: paginatedEpisodes,
      pagination: {
        page,
        limit,
        total: episodes.length,
        totalPages: Math.ceil(episodes.length / limit),
        hasMore: endIndex < episodes.length
      },
      filters: {
        categories: categories.sort(),
        availableTiers: ['free', 'premium', 'research']
      }
    })

  } catch (error) {
    console.error('Error fetching podcast catalog:', error)
    return NextResponse.json({ error: 'Internal server error' }, { status: 500 })
  }
}

// Get single podcast episode
export async function POST(request: NextRequest) {
  try {
    const { episodeId, userEmail } = await request.json()
    
    if (!episodeId) {
      return NextResponse.json({ error: 'Episode ID required' }, { status: 400 })
    }

    // Get episode details
    const episodeDoc = await db.collection('podcast_jobs').doc(episodeId).get()
    
    if (!episodeDoc.exists) {
      return NextResponse.json({ error: 'Episode not found' }, { status: 404 })
    }

    const episodeData = episodeDoc.data()
    
    // Check user access
    if (userEmail) {
      const userDoc = await db.collection('users').doc(userEmail).get()
      if (userDoc.exists) {
        const userData = userDoc.data()
        
        // Log episode view for analytics
        await db.collection('episode_views').add({
          episodeId,
          userEmail,
          viewedAt: new Date().toISOString(),
          userTier: userData.subscriptionTier
        })
      }
    }

    return NextResponse.json({
      episode: {
        id: episodeId,
        ...episodeData.result,
        request: episodeData.request,
        status: episodeData.status
      }
    })

  } catch (error) {
    console.error('Error fetching episode details:', error)
    return NextResponse.json({ error: 'Internal server error' }, { status: 500 })
  }
}
