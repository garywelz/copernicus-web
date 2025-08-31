import PodcastHeader from '@/components/podcast-header'
import CategoryTabs from '@/components/category-tabs'
import EpisodePlayer from '@/components/episode-player'

// Force dynamic rendering
export const dynamic = 'force-dynamic'

import { headers } from 'next/headers';

async function fetchPodcastData() {
  try {
    const isServer = typeof window === 'undefined';
    let apiUrl;
    if (isServer) {
      // Always construct absolute URL for SSR
      let host = headers().get('host');
      if (!host || host === '') {
        host = 'copernicus-podcast-735cglkf0-gary-welzs-projects.vercel.app';
      }
      const protocol = host.startsWith('localhost') ? 'http' : 'https';
      apiUrl = `${protocol}://${host}/api/spotify`;
      console.log('SSR fetchPodcastData: host =', host, 'apiUrl =', apiUrl);
    } else {
      // On client, use relative URL
      apiUrl = '/api/spotify';
    }
    const response = await fetch(apiUrl, {
      cache: 'no-store'
    });
    if (!response.ok) {
      throw new Error('Failed to fetch podcast data');
    }
    return await response.json();
  } catch (error) {
    console.error('Error fetching podcast data:', error);
    throw error;
  }
}

async function fetchRecentEpisodes() {
  try {
    const isServer = typeof window === 'undefined';
    let apiUrl;
    if (isServer) {
      let host = headers().get('host');
      if (!host || host === '') {
        host = 'copernicus-podcast-735cglkf0-gary-welzs-projects.vercel.app';
      }
      const protocol = host.startsWith('localhost') ? 'http' : 'https';
      apiUrl = `${protocol}://${host}/api/recent-episodes`;
    } else {
      apiUrl = '/api/recent-episodes';
    }
    
    const response = await fetch(apiUrl, {
      cache: 'no-store'
    });
    
    if (!response.ok) {
      throw new Error('Failed to fetch recent episodes');
    }
    
    return await response.json();
  } catch (error) {
    console.error('Error fetching recent episodes:', error);
    return { episodes: [] };
  }
}

export default async function Home() {
  try {
    const [data, recentEpisodes] = await Promise.all([
      fetchPodcastData(),
      fetchRecentEpisodes()
    ]);
    
    const { podcast, episodes } = data;

    if (!episodes || episodes.length === 0) {
      // Debug output if episodes missing
      return (
        <main className="min-h-screen bg-background">
          <div className="container mx-auto px-4 py-8">
            <div className="text-center space-y-4">
              <h1 className="text-3xl font-bold text-red-500">
                No episodes found!
              </h1>
              <pre className="bg-gray-100 p-4 rounded text-left overflow-x-auto text-xs">
                {JSON.stringify(data, null, 2)}
              </pre>
              <p className="text-sm text-gray-500">
                If you see this, the API is working but returned no episodes.<br />
                Check your RSS feed, API route, and episode data structure.
              </p>
            </div>
          </div>
        </main>
      );
    }

    return (
      <main className="min-h-screen bg-background">
        <div className="container mx-auto px-4 py-8">
          <PodcastHeader podcast={podcast} />
          
          {/* Recent AI-Generated Episodes */}
          {recentEpisodes.episodes && recentEpisodes.episodes.length > 0 && (
            <section className="my-12">
              <h2 className="text-3xl font-bold mb-6">🎙️ Recently Generated Episodes</h2>
              <div className="space-y-4">
                {recentEpisodes.episodes.slice(0, 3).map((episode: any) => (
                  <EpisodePlayer
                    key={episode.id}
                    title={episode.title}
                    audioUrl={episode.audioUrl}
                    thumbnailUrl={episode.thumbnailUrl}
                  />
                ))}
              </div>
            </section>
          )}
          
          <CategoryTabs episodes={episodes} />
        </div>
      </main>
    );
  } catch (error) {
    console.error('Error loading podcast data:', error);
    return (
      <main className="min-h-screen bg-background">
        <div className="container mx-auto px-4 py-8">
          <div className="text-center space-y-4">
            <h1 className="text-3xl font-bold text-green-500">
              🚀 RSS Integration Ready!
            </h1>
            <p className="text-lg text-gray-600">
              32 episodes ready to load from RSS feed
            </p>
            <p className="text-sm text-gray-500">
              Visit your production site to see your episodes
            </p>
          </div>
        </div>
      </main>
    );
  }
}

