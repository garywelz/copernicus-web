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
<<<<<<< HEAD
    News: ["Biology News - Episode 1", "Chemistry News - Episode 1", "CompSci News - Episode 1", "Math News - Episode 1", "Physics News - Episode 1", "Science News - Episode 1"],
    Biology: ["CRISPR Chemistry", "Organoids", "Spatial Biology", "Synthetic Biology", "Neural Optogenetics"],
    Chemistry: ["Green Chemistry", "Molecular Machines", "Catalysis Revolution", "Computational Chemistry"],
    ComputerScience: [
=======
    News: ["Biology News", "Chemistry News", "Comp Sci News", "Math News", "Physics News"],
    Biology: ["CRISPR Chemistry", "Organoids", "Spatial Biology", "Synthetic Biology"],
    Chemistry: ["Green Chemistry", "Molecular Machines"],
    "Computer Science": [
>>>>>>> 7c13d53b1e209c067ff2ff680d00fe9aec2fd3bb
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
<<<<<<< HEAD
    Physics: ["Black Holes", "The Higgs Boson", "Quantum Entanglement", "Quantum Batteries", "String Theory", "Quantum Cryptography"],
=======
    Physics: ["Black Holes", "The Higgs Boson", "Quantum Entanglement", "Quantum Batteries", "String Theory"],
>>>>>>> 7c13d53b1e209c067ff2ff680d00fe9aec2fd3bb
  }

  // Function to get episodes for a specific category
  const getEpisodesForCategory = (category: string) => {
    const episodeNames = categoryEpisodeLists[category as keyof typeof categoryEpisodeLists] || []

    // Create a map to store the best match for each episode name
    const bestMatches = new Map<string, SpotifyEpisode>()

    // For each episode, check if it matches any of the required names
    episodes.forEach((episode) => {
<<<<<<< HEAD
      // Safely get episode name, ensuring we have a string
      const episodeName = (episode?.name || episode?.title || '').toString().toLowerCase()
      
      // Skip if no valid episode name
      if (!episodeName) return
=======
      const episodeName = episode.name.toLowerCase()
>>>>>>> 7c13d53b1e209c067ff2ff680d00fe9aec2fd3bb

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
<<<<<<< HEAD
          const existingMatch = bestMatches.get(requiredName)
          const existingMatchName = existingMatch ? (existingMatch.name || existingMatch.title || '').toString().toLowerCase() : ''
          
          if (
            !bestMatches.has(requiredName) ||
            episodeName.length < existingMatchName.length
=======
          if (
            !bestMatches.has(requiredName) ||
            episodeName.length < bestMatches.get(requiredName)!.name.toLowerCase().length
>>>>>>> 7c13d53b1e209c067ff2ff680d00fe9aec2fd3bb
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