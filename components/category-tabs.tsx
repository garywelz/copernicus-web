"use client"

import { useState, useEffect } from "react"
import SubjectFilter from "./subject-filter"
import EpisodeList from "./episode-list"
import { SpotifyEpisode } from "@/types/spotify"

interface CategoryTabsProps {
  episodes: SpotifyEpisode[]
}

export default function CategoryTabs({ episodes }: CategoryTabsProps) {
  const [activeSubject, setActiveSubject] = useState("News")
  const [filteredEpisodes, setFilteredEpisodes] = useState<SpotifyEpisode[]>([])

  // Map UI subject to API category value
  const subjectToCategory: { [key: string]: string } = {
    News: 'news',
    Biology: 'biology',
    Chemistry: 'chemistry',
    ComputerScience: 'computer-science',
    Mathematics: 'mathematics',
    Physics: 'physics',
  }

  // Update filtered episodes when active subject changes
  useEffect(() => {
    const apiCategory = subjectToCategory[activeSubject] || 'news';
    setFilteredEpisodes(
      episodes.filter(ep => (ep.category || '').toLowerCase() === apiCategory)
    );
  }, [activeSubject, episodes])

  return (
    <>
      <section className="my-12">
        <h2 className="text-3xl font-bold mb-6">Browse by Subject</h2>
        <SubjectFilter activeSubject={activeSubject} onSubjectChange={setActiveSubject} />
      </section>

      <section className="my-12">
        <h2 className="text-3xl font-bold mb-6">{activeSubject} Episodes</h2>
        {filteredEpisodes.length > 0 ? (
          <EpisodeList episodes={filteredEpisodes} />
        ) : (
          <p className="text-center text-gray-500">No episodes found in this category</p>
        )}
      </section>
    </>
  )
} 