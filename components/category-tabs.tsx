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

  // Define the exact episode lists for each category
  const categoryEpisodeLists = {
    News: ["Biology News", "Chemistry News", "Comp Sci News", "Math News", "Physics News"],
    Biology: ["CRISPR Chemistry", "Organoids", "Spatial Biology", "Synthetic Biology"],
    Chemistry: ["Green Chemistry", "Molecular Machines"],
    "Computer Science": [
      "Edge Computing Architectures",
      "Neuromorphic Computing",
      "Quantum Machine Learning",
      "The Promise and Challenges of Artificial General Intelligence",
    ],
    Mathematics: [
      "Frontiers of Mathematical Logic",
      "Godel's Incompleteness Theorems",
      "Independence Results in Peano Arithmetic",
      "The Independence of the Continuum Hypothesis",
      "The Poincare Conjecture",
    ],
    Physics: ["Black Holes", "The Higgs Boson", "Quantum Entanglement", "Quantum Batteries", "String Theory"],
  }

  // Function to get episodes for a specific category
  const getEpisodesForCategory = (category: string) => {
    const episodeNames = categoryEpisodeLists[category as keyof typeof categoryEpisodeLists] || []

    // Create a map to store the best match for each episode name
    const bestMatches = new Map<string, SpotifyEpisode>()

    // For each episode, check if it matches any of the required names
    episodes.forEach((episode) => {
      const episodeName = episode.name.toLowerCase()

      episodeNames.forEach((requiredName) => {
        const requiredNameLower = requiredName.toLowerCase()

        // Check if this episode matches the required name
        if (
          episodeName.includes(requiredNameLower) ||
          // Special cases
          (requiredNameLower === "organoids" && episodeName.includes("orgonoid")) ||
          (requiredNameLower === "godel's incompleteness theorems" &&
            (episodeName.includes("godel") || episodeName.includes("incompleteness"))) ||
          (requiredNameLower === "the independence of the continuum hypothesis" &&
            episodeName.includes("continuum hypothesis")) ||
          (requiredNameLower === "the poincare conjecture" &&
            (episodeName.includes("poincare") || episodeName.includes("poincaré")))
        ) {
          // If we don't have a match for this name yet, or this is a better match
          if (
            !bestMatches.has(requiredName) ||
            episodeName.length < bestMatches.get(requiredName)!.name.toLowerCase().length
          ) {
            bestMatches.set(requiredName, episode)
          }
        }
      })
    })

    // Create an array of episodes in the correct order
    const result: SpotifyEpisode[] = []

    episodeNames.forEach((name) => {
      if (bestMatches.has(name)) {
        result.push(bestMatches.get(name)!)
      }
    })

    return result
  }

  // Update filtered episodes when active subject changes
  useEffect(() => {
    setFilteredEpisodes(getEpisodesForCategory(activeSubject))
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