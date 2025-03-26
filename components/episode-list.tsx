"use client"

import * as React from "react"
import Image from "next/image"
import { formatDistanceToNow } from "date-fns"
import { Card, CardContent } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Play, Clock } from 'lucide-react'

interface Episode {
  id: string
  name: string
  description: string
  release_date: string
  duration_ms: number
  images: { url: string }[]
  external_urls: { spotify: string }
}

interface EpisodeListProps {
  episodes: Episode[]
}

export default function EpisodeList({ episodes }: EpisodeListProps) {
  if (!episodes || episodes.length === 0) {
    return <p className="text-center text-gray-500">No episodes found in this category</p>
  }

  const formatDuration = (ms: number) => {
    const minutes = Math.floor(ms / 60000)
    const seconds = Math.floor((ms % 60000) / 1000)
    return `${minutes}:${seconds.toString().padStart(2, "0")}`
  }

  return (
    <div className="grid grid-cols-1 gap-6">
      {episodes.map((episode) => (
        <Card key={episode.id} className="overflow-hidden">
          <CardContent className="p-0">
            <div className="flex flex-col md:flex-row">
              <div className="relative w-full md:w-48 h-48 shrink-0">
                <Image
                  src={episode.images[0]?.url || "/placeholder.svg"}
                  alt={episode.name}
                  fill
                  className="object-cover"
                />
              </div>

              <div className="p-6 flex-1">
                <h3 className="text-xl font-bold mb-2">{episode.name}</h3>

                <div className="flex items-center gap-4 text-sm text-gray-500 mb-4">
                  <span>{formatDistanceToNow(new Date(episode.release_date), { addSuffix: true })}</span>
                  <span className="flex items-center">
                    <Clock className="h-4 w-4 mr-1" />
                    {formatDuration(episode.duration_ms)}
                  </span>
                </div>

                <p className="text-gray-700 mb-4 line-clamp-3">{episode.description}</p>

                <Button variant="outline" className="gap-2" asChild>
                  <a href={episode.external_urls.spotify} target="_blank" rel="noopener noreferrer">
                    <Play className="h-4 w-4" />
                    Play Episode
                  </a>
                </Button>
              </div>
            </div>
          </CardContent>
        </Card>
      ))}
    </div>
  )
} 