export interface SpotifyShow {
  id: string;
  name: string;
  description: string;
  images: { url: string; height: number; width: number }[];
  publisher: string;
  total_episodes: number;
  external_urls: {
    spotify: string;
  };
}

export interface SpotifyEpisode {
  id: string;
  name: string;
  title?: string; // RSS custom property
  description: string;
  release_date: string;
  published_at?: string; // RSS custom property
  duration_ms: number;
  images: { url: string; height: number; width: number }[];
  thumbnail_url?: string; // RSS custom property
  external_urls: {
    spotify: string;
  };
  spotify_url?: string; // RSS custom property
  category?: string; // RSS custom property
  audio_url?: string; // RSS custom property
  web_url?: string; // RSS custom property
  apple_url?: string; // RSS custom property
  slug?: string; // RSS custom property
}

export interface SpotifySearchResponse {
  shows: {
    items: SpotifyShow[];
  };
}

export interface SpotifyTokenResponse {
  access_token: string;
} 