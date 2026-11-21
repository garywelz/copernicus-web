import { NextResponse } from 'next/server'

// The RSS feed, not a bucket listing. Listing the bucket over anonymous HTTP only works while the bucket grants `allUsers` the right to
// list it, which exposes every object name to anyone; the feed is the published record of what exists and carries real titles and dates,
// where a listing carried only file names.
const FEED_URL =
  'https://storage.googleapis.com/regal-scholar-453620-r7-podcast-storage/feeds/copernicus-mvp-rss-feed.xml'
const LIMIT = 10

function tagText(item: string, tag: string): string {
  const m = item.match(new RegExp(`<${tag}(?:\\s[^>]*)?>([\\s\\S]*?)</${tag}>`, 'i'))
  if (!m) return ''
  return m[1]
    .replace(/<!\[CDATA\[([\s\S]*?)\]\]>/g, '$1')
    .replace(/&lt;/g, '<')
    .replace(/&gt;/g, '>')
    .replace(/&amp;/g, '&')
    .trim()
}

function attr(item: string, tag: string, name: string): string {
  const m = item.match(new RegExp(`<${tag}\\b[^>]*\\b${name}="([^"]*)"`, 'i'))
  return m ? m[1] : ''
}

export function parseFeed(xml: string, limit: number = LIMIT) {
  const items = xml.match(/<item\b[\s\S]*?<\/item>/gi) || []
  return items.slice(0, limit).map((item) => {
    const audioUrl = attr(item, 'enclosure', 'url')
    const id = (audioUrl.split('/').pop() || '').replace(/\.mp3$/i, '') || tagText(item, 'guid')
    return {
      id,
      title: tagText(item, 'title'),
      audioUrl,
      description: tagText(item, 'description'),
      duration: tagText(item, 'itunes:duration'),
      createdAt: tagText(item, 'pubDate'),
      size: attr(item, 'enclosure', 'length'),
    }
  })
}

export async function GET() {
  try {
    const response = await fetch(FEED_URL, { headers: { Accept: 'application/rss+xml, application/xml' } })
    if (!response.ok) {
      throw new Error(`Failed to fetch the feed: ${response.status}`)
    }
    return NextResponse.json({ episodes: parseFeed(await response.text()) })
  } catch (error) {
    console.error('Error fetching recent episodes:', error)
    return NextResponse.json({ episodes: [] }, { status: 500 })
  }
}
