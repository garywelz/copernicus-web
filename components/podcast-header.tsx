"use client"

import * as React from "react"
import Image from "next/image"
import Link from "next/link"
import { ExternalLink, Plus } from 'lucide-react'

interface PodcastHeaderProps {
  podcast: {
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
  }
}

export default function PodcastHeader({ podcast }: PodcastHeaderProps) {
  // Support both Spotify and RSS shapes
  // Always use the Copernicus portrait from GCS for the homepage header
  const imageUrl = "https://storage.googleapis.com/regal-scholar-453620-r7-podcast-storage/images/copernicus-original-portrait-optimized.jpg";
  // Use the Spotify show title
  const title = "Copernicus AI: Frontiers of Research";
  // Use the Spotify About text, no 'About' heading
  const description = "Educational podcast covering the latest breakthroughs in science, technology, mathematics, and research. Join us as we explore cutting-edge discoveries and their implications for the future.";
  const publisher = podcast.publisher || "Copernicus AI";
  const totalEpisodes = podcast.total_episodes;
  const spotifyUrl = podcast.spotify_url || podcast.external_urls?.spotify;

  return (
    <div className="flex flex-col md:flex-row gap-8 items-start">
      <div className="relative w-72 h-72 shrink-0">
        <Image
          src={imageUrl}
          alt={title}
          fill
          className="object-cover rounded-md"
          priority
        />
      </div>

      <div className="flex-1">
        <h1 className="text-4xl font-bold mb-2">{title}</h1>


        <div className="flex gap-3 mb-6">
          {typeof totalEpisodes === "number" && (
            <div className="bg-gray-100 rounded-full px-4 py-2 text-sm font-medium">
              {totalEpisodes} Episodes
            </div>
          )}
          <div className="bg-gray-100 rounded-full px-4 py-2 text-sm font-medium">Podcast</div>
        </div>

        <p className="text-lg mb-8">{description}</p>

        <div className="flex gap-3">
          <Link
            href="/create"
            className="inline-flex items-center px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-md font-medium transition-colors"
          >
            <Plus className="mr-2 h-4 w-4" />
            Create Podcast
          </Link>
          {spotifyUrl && (
            <a
              href={spotifyUrl}
              target="_blank"
              rel="noopener noreferrer"
              className="inline-flex items-center px-4 py-2 bg-green-600 hover:bg-green-700 text-white rounded-md font-medium transition-colors"
            >
              <ExternalLink className="mr-2 h-4 w-4" />
              Follow on Spotify
            </a>
          )}
        </div>
      </div>
    </div>
  );
}