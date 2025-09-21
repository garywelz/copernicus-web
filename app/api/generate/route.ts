import { NextRequest, NextResponse } from 'next/server'

export async function POST(request: NextRequest) {
  try {
    const body = await request.json()
    
    // Validate required fields
    const { subject, duration, speakers, difficulty, category, podcast_type, additional_notes, source_links } = body
    
    if (!subject || !duration || !speakers || !difficulty || !category) {
      return NextResponse.json(
        { error: 'Missing required fields: subject, duration, speakers, difficulty, category' },
        { status: 400 }
      )
    }

    // Prepare request for backend (using main PodcastRequest format)
    const backendRequest = {
      topic: subject,  // Convert subject to topic
      category: category,
      expertise_level: difficulty,
      format_type: podcast_type || 'feature',
      duration: duration,
      voice_style: speakers,
      focus_areas: source_links || [],
      include_citations: true,
      paradigm_shift_analysis: true
    }

    // Get backend URL from environment or use default
    const backendUrl = process.env.BACKEND_URL || 'https://copernicus-podcast-api-v2-204731194849.us-central1.run.app'
    
    console.log('Sending request to backend:', backendUrl)
    console.log('Request payload:', backendRequest)

    // Send request to backend (using main sophisticated endpoint)
    const response = await fetch(`${backendUrl}/generate-podcast`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(backendRequest),
    })

    if (!response.ok) {
      const errorText = await response.text()
      console.error('Backend error:', errorText)
      return NextResponse.json(
        { error: 'Backend service error', details: errorText },
        { status: response.status }
      )
    }

    const result = await response.json()
    console.log('Backend response:', result)

    return NextResponse.json(result)

  } catch (error) {
    console.error('Error in generate API:', error)
    return NextResponse.json(
      { error: 'Internal server error', details: error instanceof Error ? error.message : 'Unknown error' },
      { status: 500 }
    )
  }
}

export async function GET() {
  return NextResponse.json({ 
    message: 'Copernicus Podcast Generation API',
    status: 'operational',
    endpoints: {
      'POST /api/generate': 'Generate a new podcast episode'
    }
  })
}
