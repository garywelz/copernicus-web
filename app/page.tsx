import PodcastHeader from '@/components/podcast-header'
import CategoryTabs from '@/components/category-tabs'
import { getSpotifyPodcast, getSpotifyEpisodes } from '@/lib/spotify'

// Force dynamic rendering
export const dynamic = 'force-dynamic'

export default async function Home() {
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
} 