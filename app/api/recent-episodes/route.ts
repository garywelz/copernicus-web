import { NextResponse } from 'next/server'

export async function GET() {
  try {
    // Fetch recent episodes from Google Cloud Storage
    const response = await fetch('https://storage.googleapis.com/storage/v1/b/regal-scholar-453620-r7-podcast-storage/o?prefix=audio/&orderBy=timeCreated&maxResults=10', {
      headers: {
        'Accept': 'application/json'
      }
    })

    if (!response.ok) {
      throw new Error('Failed to fetch episodes')
    }

    const data = await response.json()
    
    // Process the episodes
    const episodes = data.items?.map((item: any) => {
      const filename = item.name.replace('audio/', '').replace('.mp3', '')
      return {
        id: filename,
        title: filename.replace(/-/g, ' ').replace(/\d+/g, '').trim(),
        audioUrl: `https://storage.googleapis.com/regal-scholar-453620-r7-podcast-storage/audio/${filename}.mp3`,
        descriptionUrl: `https://storage.googleapis.com/regal-scholar-453620-r7-podcast-storage/descriptions/${filename}.md`,
        thumbnailUrl: `https://storage.googleapis.com/regal-scholar-453620-r7-podcast-storage/thumbnails/${filename}.jpg`,
        createdAt: item.timeCreated,
        size: item.size
      }
    }) || []

    return NextResponse.json({ episodes })
  } catch (error) {
    console.error('Error fetching recent episodes:', error)
    return NextResponse.json({ episodes: [] }, { status: 500 })
  }
}

