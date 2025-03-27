import PodcastHeader from '@/components/podcast-header'
import CategoryTabs from '@/components/category-tabs'
import { getSpotifyPodcast, getSpotifyEpisodes } from '@/lib/spotify'

// Force dynamic rendering
export const dynamic = 'force-dynamic'

export default async function Home() {
  try {
    const podcast = await getSpotifyPodcast('4rOoJ6Egrf8K2IrywzwOMk')
    const episodes = await getSpotifyEpisodes('4rOoJ6Egrf8K2IrywzwOMk')

    return (
      <main className="min-h-screen bg-background">
        <div className="container mx-auto px-4 py-8">
          <PodcastHeader podcast={podcast} />
          <CategoryTabs episodes={episodes} />
        </div>
      </main>
    )
  } catch (error) {
    console.error('Error fetching podcast data:', error)
    return (
      <main className="min-h-screen bg-background">
        <div className="container mx-auto px-4 py-8">
          <h1 className="text-2xl font-bold text-red-500">
            Error loading podcast data. Please try again later.
          </h1>
        </div>
      </main>
    )
  }
} 