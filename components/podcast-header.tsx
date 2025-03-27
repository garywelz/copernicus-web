"use client"

import * as React from "react"
import Image from "next/image"
import { ExternalLink } from 'lucide-react'

interface PodcastHeaderProps {
  podcast: {
    name: string
    description: string
    images: { url: string }[]
    publisher: string
    total_episodes: number
    external_urls: { spotify: string }
  }
}

export default function PodcastHeader({ podcast }: PodcastHeaderProps) {
  return (
    <div className="flex flex-col md:flex-row gap-8 items-start">
      <div className="relative w-72 h-72 shrink-0">
        <Image
          src={podcast.images[0]?.url || "/placeholder.svg"}
          alt={podcast.name}
          fill
          className="object-cover rounded-md"
          priority
        />
      </div>

      <div className="flex-1">
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