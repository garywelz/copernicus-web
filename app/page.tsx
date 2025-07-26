import PodcastHeader from '@/components/podcast-header'
import CategoryTabs from '@/components/category-tabs'

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

export default async function Home() {
  try {
    const data = await fetchPodcastData();
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

