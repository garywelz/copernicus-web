import { SpotifyShow, SpotifyEpisode, SpotifySearchResponse, SpotifyTokenResponse } from '@/types/spotify';

const SPOTIFY_API_URL = 'https://api.spotify.com/v1';

async function getAccessToken(): Promise<string> {
  const clientId = process.env.SPOTIFY_CLIENT_ID;
  const clientSecret = process.env.SPOTIFY_CLIENT_SECRET;

  if (!clientId || !clientSecret) {
    throw new Error('Missing Spotify credentials');
  }

  try {
    const response = await fetch('https://accounts.spotify.com/api/token', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/x-www-form-urlencoded',
        Authorization: `Basic ${Buffer.from(`${clientId}:${clientSecret}`).toString('base64')}`,
      },
      body: 'grant_type=client_credentials',
      cache: 'no-store',
    });

    if (!response.ok) {
      throw new Error(`Failed to get access token: ${response.status} ${response.statusText}`);
    }

    const data = await response.json() as SpotifyTokenResponse;
    return data.access_token;
  } catch (error) {
    console.error('Error getting Spotify access token:', error);
    throw error;
  }
}

async function searchSpotifyPodcast(query: string): Promise<SpotifyShow[]> {
  const token = await getAccessToken();
  const response = await fetch(
    `${SPOTIFY_API_URL}/search?q=${encodeURIComponent(query)}&type=show&market=US`,
    {
      headers: {
        Authorization: `Bearer ${token}`,
      },
      cache: 'no-store',
    }
  );

  if (!response.ok) {
    throw new Error(`Failed to search podcasts: ${response.status} ${response.statusText}`);
  }

  const data = await response.json() as SpotifySearchResponse;
  return data.shows.items;
}

async function getSpotifyPodcast(showId: string): Promise<SpotifyShow> {
  const token = await getAccessToken();
  const response = await fetch(`${SPOTIFY_API_URL}/shows/${showId}?market=US`, {
    headers: {
      Authorization: `Bearer ${token}`,
    },
    cache: 'no-store',
  });

  if (!response.ok) {
    throw new Error(`Failed to fetch podcast: ${response.status} ${response.statusText}`);
  }

  const data = await response.json();
  
  // Type check the response
  if (!data.id || !data.name || !data.description || !Array.isArray(data.images)) {
    throw new Error('Invalid podcast data received from Spotify API');
  }

  return data as SpotifyShow;
}

async function getSpotifyEpisodes(showId: string): Promise<SpotifyEpisode[]> {
  const token = await getAccessToken();
  const limit = 50;
  let offset = 0;
  let allEpisodes: SpotifyEpisode[] = [];

  while (true) {
    const response = await fetch(
      `${SPOTIFY_API_URL}/shows/${showId}/episodes?market=US&limit=${limit}&offset=${offset}`,
      {
        headers: {
          Authorization: `Bearer ${token}`,
        },
        cache: 'no-store',
      }
    );

    if (!response.ok) {
      throw new Error(`Failed to fetch episodes: ${response.status} ${response.statusText}`);
    }

    const data = await response.json();
    
    // Type check the response
    if (!data.items || !Array.isArray(data.items)) {
      throw new Error('Invalid episode data received from Spotify API');
    }

    // Validate each episode
    data.items.forEach((item: any, index: number) => {
      if (!item.id || !item.name || !item.description || !item.release_date || !item.duration_ms) {
        throw new Error(`Invalid episode data at index ${index}`);
      }
    });

    allEpisodes = [...allEpisodes, ...data.items];
    
    if (data.items.length < limit) {
      break;
    }
    
    offset += limit;
  }

  return allEpisodes;
}

export { getAccessToken, searchSpotifyPodcast, getSpotifyPodcast, getSpotifyEpisodes }; 