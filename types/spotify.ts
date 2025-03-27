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
  description: string;
  release_date: string;
  duration_ms: number;
  images: { url: string; height: number; width: number }[];
  external_urls: {
    spotify: string;
  };
}

export interface SpotifySearchResponse {
  shows: {
    items: SpotifyShow[];
  };
}

export interface SpotifyTokenResponse {
  access_token: string;
} 