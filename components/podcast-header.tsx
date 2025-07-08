"use client"

import * as React from "react"
import Image from "next/image"
import { ExternalLink } from 'lucide-react'

interface PodcastHeaderProps {
  podcast: {
<<<<<<< HEAD
    // For Spotify API shape
    name?: string
    description?: string
    images?: { url: string }[]
    publisher?: string
    total_episodes?: number
    external_urls?: { spotify?: string }
    // For RSS shape
    title?: string
    cover_art?: string
    rss_feed?: string
    spotify_url?: string
    website?: string
=======
    name: string
    description: string
    images: { url: string }[]
    publisher: string
    total_episodes: number
    external_urls: { spotify: string }
>>>>>>> 7c13d53b1e209c067ff2ff680d00fe9aec2fd3bb
  }
}

export default function PodcastHeader({ podcast }: PodcastHeaderProps) {
<<<<<<< HEAD
  // Support both Spotify and RSS shapes
  const imageUrl = podcast.cover_art || podcast.images?.[0]?.url || "/placeholder.svg";
  const title = podcast.title || podcast.name || "Copernicus AI Podcast";
  const description = podcast.description || "";
  const publisher = podcast.publisher || "Copernicus AI";
  const totalEpisodes = podcast.total_episodes;
  const spotifyUrl = podcast.spotify_url || podcast.external_urls?.spotify;

=======
>>>>>>> 7c13d53b1e209c067ff2ff680d00fe9aec2fd3bb
  return (
    <div className="flex flex-col md:flex-row gap-8 items-start">
      <div className="relative w-72 h-72 shrink-0">
        <Image
<<<<<<< HEAD
          src={imageUrl}
          alt={title}
=======
          src={podcast.images[0]?.url || "/placeholder.svg"}
          alt={podcast.name}
>>>>>>> 7c13d53b1e209c067ff2ff680d00fe9aec2fd3bb
          fill
          className="object-cover rounded-md"
          priority
        />
      </div>

      <div className="flex-1">
<<<<<<< HEAD
        <h1 className="text-4xl font-bold mb-2">{title}</h1>
        {publisher && <p className="text-xl mb-4">{publisher}</p>}

        <div className="flex gap-3 mb-6">
          {typeof totalEpisodes === "number" && (
            <div className="bg-gray-100 rounded-full px-4 py-2 text-sm font-medium">
              {totalEpisodes} Episodes
            </div>
          )}
          <div className="bg-gray-100 rounded-full px-4 py-2 text-sm font-medium">Podcast</div>
        </div>

        <p className="text-lg mb-8">{description}</p>

        {spotifyUrl && (
          <a
            href={spotifyUrl}
            target="_blank"
            rel="noopener noreferrer"
            className="inline-flex items-center px-4 py-2 bg-green-600 hover:bg-green-700 text-white rounded-md"
          >
            <ExternalLink className="mr-2 h-4 w-4" />
            Follow on Spotify
          </a>
        )}
      </div>
    </div>
  );
}
=======
        <h1 className="text-4xl font-bold mb-2">{podcast.name}</h1>
        <p className="text-xl mb-4">{podcast.publisher}</p>

        <div className="flex gap-3 mb-6">
          <div className="bg-gray-100 rounded-full px-4 py-2 text-sm font-medium">
            {podcast.total_episodes} Episodes
          </div>
          <div className="bg-gray-100 rounded-full px-4 py-2 text-sm font-medium">Podcast</div>
        </div>

        <p className="text-lg mb-8">{podcast.description}</p>

        <a 
          href={podcast.external_urls.spotify} 
          target="_blank" 
          rel="noopener noreferrer"
          className="inline-flex items-center px-4 py-2 bg-green-600 hover:bg-green-700 text-white rounded-md"
        >
          <ExternalLink className="mr-2 h-4 w-4" />
          Follow on Spotify
        </a>
      </div>
    </div>
  )
} 
>>>>>>> 7c13d53b1e209c067ff2ff680d00fe9aec2fd3bb
