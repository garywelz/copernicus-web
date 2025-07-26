"use client"

import * as React from "react"
import { useState } from "react"
import Image from "next/image"
import { formatDistanceToNow } from "date-fns"
import { Card, CardContent } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Play, Clock, Pause, Volume2 } from 'lucide-react'
import { SpotifyEpisode } from "@/types/spotify"

interface EpisodeListProps {
  episodes: SpotifyEpisode[]
}

export default function EpisodeList({ episodes }: EpisodeListProps) {
  const [currentlyPlaying, setCurrentlyPlaying] = useState<string | null>(null);
  const [expandedEpisodes, setExpandedEpisodes] = useState<Set<string>>(new Set());

  if (!episodes || episodes.length === 0) {
    return <p className="text-center text-gray-500">No episodes found in this category</p>;
  }

  const formatDuration = (durationString: string) => {
    // Handle duration formats like "14,32" or "6,04" from RSS feed
    if (durationString && durationString.includes(',')) {
      return durationString.replace(',', ':');
    }
    return durationString || '0:00';
  };

  const toggleExpanded = (episodeId: string) => {
    const newExpanded = new Set(expandedEpisodes);
    if (newExpanded.has(episodeId)) {
      newExpanded.delete(episodeId);
    } else {
      newExpanded.add(episodeId);
    }
    setExpandedEpisodes(newExpanded);
  };

  const handleAudioPlay = (episodeId: string) => {
    setCurrentlyPlaying(episodeId);
  };

  const handleAudioPause = () => {
    setCurrentlyPlaying(null);
  };

  return (
    <div className="grid grid-cols-1 gap-6">
      {episodes.map((episode) => {
        const episodeId = episode.id || episode.guid || episode.title;
        const isExpanded = expandedEpisodes.has(episodeId);
        const isPlaying = currentlyPlaying === episodeId;
        
        return (
          <Card key={episodeId} className="overflow-hidden">
            <CardContent className="p-0">
              <div className="flex flex-col md:flex-row">
                <div className="relative w-full md:w-48 h-48 shrink-0">
                  <Image
                    src={episode.thumbnail_url || episode.images?.[0]?.url || "https://storage.googleapis.com/regal-scholar-453620-r7-podcast-storage/images/copernicus-original-portrait.jpg"}
                    alt={episode.title || episode.name || "Episode"}
                    fill
                    className="object-cover"
                    unoptimized={true}
                    onError={(e) => {
                      console.log('Image load error:', e);
                      // Fallback to Copernicus portrait
                      e.currentTarget.src = "https://storage.googleapis.com/regal-scholar-453620-r7-podcast-storage/images/copernicus-original-portrait.jpg";
                    }}
                  />
                </div>
                <div className="p-6 flex-1">
                  <div className="flex items-start justify-between mb-2">
                    <h3 className="text-xl font-bold flex-1">{episode.title || episode.name}</h3>
                    {episode.season && episode.episode && (
                      <span className="text-sm text-gray-500 ml-4">
                        S{episode.season}E{episode.episode}
                      </span>
                    )}
                  </div>
                  
                  <div className="flex items-center gap-4 text-sm text-gray-500 mb-4">
                    <span>{formatDistanceToNow(new Date(episode.published_at || episode.release_date), { addSuffix: true })}</span>
                    <span className="flex items-center">
                      <Clock className="h-4 w-4 mr-1" />
                      {formatDuration(episode.duration)}
                    </span>
                  </div>
                  
                  {/* Episode Description */}
                  <div className="mb-4">
                    <p className={`text-gray-700 ${isExpanded ? '' : 'line-clamp-3'}`}>
                      {episode.description}
                    </p>
                    {episode.description && episode.description.length > 200 && (
                      <button
                        onClick={() => toggleExpanded(episodeId)}
                        className="text-blue-600 hover:text-blue-800 text-sm mt-1"
                      >
                        {isExpanded ? 'Show less' : 'Show more'}
                      </button>
                    )}
                  </div>

                  {/* Audio Player */}
                  {episode.audio_url && (
                    <div className="mb-4">
                      <audio
                        controls
                        className="w-full h-10"
                        preload="metadata"
                        onPlay={() => handleAudioPlay(episodeId)}
                        onPause={handleAudioPause}
                        onEnded={handleAudioPause}
                      >
                        <source src={episode.audio_url} type="audio/mpeg" />
                        Your browser does not support the audio element.
                      </audio>
                    </div>
                  )}

                  {/* External Links */}
                  <div className="flex gap-2">
                    {(episode.spotify_url || episode.external_urls?.spotify) && (
                      <Button variant="outline" size="sm" className="gap-2" asChild>
                        <a
                          href={episode.spotify_url || episode.external_urls?.spotify}
                          target="_blank"
                          rel="noopener noreferrer"
                        >
                          <Play className="h-4 w-4" />
                          Spotify
                        </a>
                      </Button>
                    )}
                  </div>
                </div>
              </div>
            </CardContent>
          </Card>
        );
      })}
    </div>
  );
}
