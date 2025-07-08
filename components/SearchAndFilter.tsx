"use client"

// components/SearchAndFilter.tsx
// Advanced search and filtering for the growing podcast archive

import React, { useState, useEffect, useMemo } from 'react';
import { debounce } from 'lodash';

interface Episode {
  id: number;
  title: string;
  description: string;
  slug: string;
  category: string;
  audio_url: string;
  thumbnail_url: string;
  web_url: string;
  published_at: string;
  duration: string;
  spotify_url: string;
  apple_url: string;
}

interface SearchAndFilterProps {
  episodes: Episode[];
  onFilteredEpisodes: (episodes: Episode[]) => void;
  selectedCategory: string;
  onCategoryChange: (category: string) => void;
  categoryStats: Record<string, number>;
}

const CATEGORY_CONFIG = {
  all: { label: 'All Episodes', icon: '🎯', color: 'bg-blue-500 hover:bg-blue-600' },
  biology: { label: 'Biology', icon: '🧬', color: 'bg-green-500 hover:bg-green-600' },
  chemistry: { label: 'Chemistry', icon: '⚗️', color: 'bg-purple-500 hover:bg-purple-600' },
  physics: { label: 'Physics', icon: '⚛️', color: 'bg-blue-500 hover:bg-blue-600' },
  mathematics: { label: 'Mathematics', icon: '📐', color: 'bg-red-500 hover:bg-red-600' },
  'computer-science': { label: 'Computer Science', icon: '💻', color: 'bg-gray-500 hover:bg-gray-600' },
  news: { label: 'News', icon: '📰', color: 'bg-yellow-500 hover:bg-yellow-600' }
};

export default function SearchAndFilter({ 
  episodes, 
  onFilteredEpisodes, 
  selectedCategory, 
  onCategoryChange, 
  categoryStats 
}: SearchAndFilterProps) {
  const [searchQuery, setSearchQuery] = useState('');
  const [sortBy, setSortBy] = useState<'newest' | 'oldest' | 'title' | 'relevance'>('newest');
  const [showAdvancedSearch, setShowAdvancedSearch] = useState(false);
  const [searchHistory, setSearchHistory] = useState<string[]>([]);

  // Debounced search function
  const debouncedSearch = useMemo(
    () => debounce((query: string) => {
      if (query.trim() && !searchHistory.includes(query.trim())) {
        setSearchHistory(prev => [query.trim(), ...prev.slice(0, 4)]);
      }
    }, 500),
    [searchHistory]
  );

  // Advanced search and filtering logic
  const filteredAndSortedEpisodes = useMemo(() => {
    let filtered = episodes;

    // Category filter
    if (selectedCategory !== 'all') {
      filtered = filtered.filter(episode => episode.category === selectedCategory);
    }

    // Search filter
    if (searchQuery.trim()) {
      const query = searchQuery.toLowerCase();
      filtered = filtered.filter(episode => 
        episode.title.toLowerCase().includes(query) ||
        episode.description.toLowerCase().includes(query) ||
        episode.category.toLowerCase().includes(query)
      );
    }

    // Sort episodes
    const sorted = [...filtered].sort((a, b) => {
      switch (sortBy) {
        case 'newest':
          return new Date(b.published_at).getTime() - new Date(a.published_at).getTime();
        case 'oldest':
          return new Date(a.published_at).getTime() - new Date(b.published_at).getTime();
        case 'title':
          return a.title.localeCompare(b.title);
        case 'relevance':
          if (!searchQuery.trim()) return 0;
          const aScore = getRelevanceScore(a, searchQuery);
          const bScore = getRelevanceScore(b, searchQuery);
          return bScore - aScore;
        default:
          return 0;
      }
    });

    return sorted;
  }, [episodes, selectedCategory, searchQuery, sortBy]);

  // Calculate relevance score for search results
  const getRelevanceScore = (episode: Episode, query: string): number => {
    const lowerQuery = query.toLowerCase();
    let score = 0;
    
    // Title matches are more important
    if (episode.title.toLowerCase().includes(lowerQuery)) score += 10;
    if (episode.title.toLowerCase().startsWith(lowerQuery)) score += 5;
    
    // Description matches
    if (episode.description.toLowerCase().includes(lowerQuery)) score += 3;
    
    // Category matches
    if (episode.category.toLowerCase().includes(lowerQuery)) score += 2;
    
    return score;
  };

  // Update parent component when filtered episodes change
  useEffect(() => {
    onFilteredEpisodes(filteredAndSortedEpisodes);
  }, [filteredAndSortedEpisodes, onFilteredEpisodes]);

  // Handle search input
  const handleSearchChange = (value: string) => {
    setSearchQuery(value);
    debouncedSearch(value);
  };

  // Clear search
  const clearSearch = () => {
    setSearchQuery('');
    setSortBy('newest');
  };

  // Quick search suggestions
  const searchSuggestions = [
    'quantum', 'biology', 'chemistry', 'AI', 'mathematics', 'physics', 'computing', 'news'
  ];

  const totalEpisodes = Object.values(categoryStats).reduce((sum, count) => sum + count, 0);

  return (
    <div className="mb-8 space-y-4">
      {/* Search Bar */}
      <div className="relative max-w-2xl mx-auto">
        <div className="relative">
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => handleSearchChange(e.target.value)}
            placeholder="Search episodes by title, description, or category..."
            className="w-full px-4 py-3 pl-12 pr-12 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
          />
          <div className="absolute left-4 top-1/2 transform -translate-y-1/2">
            <span className="text-gray-400 text-xl">🔍</span>
          </div>
          {searchQuery && (
            <button
              onClick={clearSearch}
              className="absolute right-4 top-1/2 transform -translate-y-1/2 text-gray-400 hover:text-gray-600"
            >
              <span className="text-xl">✕</span>
            </button>
          )}
        </div>

        {/* Search History */}
        {searchHistory.length > 0 && searchQuery === '' && (
          <div className="absolute top-full left-0 right-0 bg-white border border-gray-200 rounded-lg mt-1 shadow-lg z-10">
            <div className="p-3">
              <p className="text-sm text-gray-600 mb-2">Recent searches:</p>
              <div className="flex flex-wrap gap-2">
                {searchHistory.map((term, index) => (
                  <button
                    key={index}
                    onClick={() => setSearchQuery(term)}
                    className="px-3 py-1 bg-gray-100 hover:bg-gray-200 rounded-full text-sm transition-colors"
                  >
                    {term}
                  </button>
                ))}
              </div>
            </div>
          </div>
        )}
      </div>

      {/* Quick Search Suggestions */}
      {!searchQuery && (
        <div className="text-center">
          <p className="text-sm text-gray-600 mb-2">Quick search:</p>
          <div className="flex flex-wrap gap-2 justify-center">
            {searchSuggestions.map((suggestion) => (
              <button
                key={suggestion}
                onClick={() => setSearchQuery(suggestion)}
                className="px-3 py-1 bg-blue-100 hover:bg-blue-200 text-blue-700 rounded-full text-sm transition-colors"
              >
                {suggestion}
              </button>
            ))}
          </div>
        </div>
      )}

      {/* Category Tabs */}
      <div className="flex flex-wrap gap-2 justify-center">
        {Object.entries(CATEGORY_CONFIG).map(([category, config]) => {
          const count = category === 'all' ? totalEpisodes : (categoryStats[category] || 0);
          const isSelected = selectedCategory === category;
          
          if (category !== 'all' && count === 0) return null;
          
          return (
            <button
              key={category}
              onClick={() => onCategoryChange(category)}
              className={`
                px-4 py-2 rounded-lg text-white font-medium transition-colors duration-200
                flex items-center gap-2 min-w-fit
                ${isSelected 
                  ? config.color.replace('hover:', '') + ' ring-2 ring-white ring-opacity-50' 
                  : config.color + ' opacity-70 hover:opacity-100'
                }
              `}
            >
              <span className="text-lg">{config.icon}</span>
              <span className="hidden sm:inline">{config.label}</span>
              <span className="bg-white bg-opacity-20 px-2 py-1 rounded-full text-xs">
                {count}
              </span>
            </button>
          );
        })}
      </div>

      {/* Advanced Filters */}
      <div className="flex justify-between items-center">
        <div className="flex items-center gap-4">
          <label className="text-sm font-medium text-gray-700">Sort by:</label>
          <select
            value={sortBy}
            onChange={(e) => setSortBy(e.target.value as any)}
            className="px-3 py-1 border border-gray-300 rounded focus:ring-2 focus:ring-blue-500 focus:border-transparent"
          >
            <option value="newest">Newest First</option>
            <option value="oldest">Oldest First</option>
            <option value="title">Title A-Z</option>
            {searchQuery && <option value="relevance">Most Relevant</option>}
          </select>
        </div>

        <button
          onClick={() => setShowAdvancedSearch(!showAdvancedSearch)}
          className="text-sm text-blue-600 hover:text-blue-800 font-medium"
        >
          {showAdvancedSearch ? 'Hide' : 'Show'} Advanced Search
        </button>
      </div>

      {/* Advanced Search Panel */}
      {showAdvancedSearch && (
        <div className="bg-gray-50 p-4 rounded-lg border">
          <h3 className="font-medium mb-3">Advanced Search Options</h3>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Search in specific fields:
              </label>
              <div className="space-y-2">
                <label className="flex items-center">
                  <input type="checkbox" className="mr-2" defaultChecked />
                  <span className="text-sm">Episode titles</span>
                </label>
                <label className="flex items-center">
                  <input type="checkbox" className="mr-2" defaultChecked />
                  <span className="text-sm">Descriptions</span>
                </label>
                <label className="flex items-center">
                  <input type="checkbox" className="mr-2" defaultChecked />
                  <span className="text-sm">Categories</span>
                </label>
              </div>
            </div>
            
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Episode length:
              </label>
              <select className="w-full px-3 py-1 border border-gray-300 rounded">
                <option>Any length</option>
                <option>Short (0-5 min)</option>
                <option>Medium (5-15 min)</option>
                <option>Long (15+ min)</option>
              </select>
            </div>
          </div>
        </div>
      )}

      {/* Search Results Summary */}
      {(searchQuery || selectedCategory !== 'all') && (
        <div className="text-center text-gray-600">
          <p className="text-sm">
            {searchQuery && (
              <>
                Found <span className="font-medium">{filteredAndSortedEpisodes.length}</span> episodes 
                matching "<span className="font-medium">{searchQuery}</span>"
                {selectedCategory !== 'all' && (
                  <> in <span className="font-medium">{CATEGORY_CONFIG[selectedCategory as keyof typeof CATEGORY_CONFIG]?.label}</span></>
                )}
              </>
            )}
            {!searchQuery && selectedCategory !== 'all' && (
              <>
                Showing <span className="font-medium">{filteredAndSortedEpisodes.length}</span> episodes 
                in <span className="font-medium">{CATEGORY_CONFIG[selectedCategory as keyof typeof CATEGORY_CONFIG]?.label}</span>
              </>
            )}
          </p>
        </div>
      )}
    </div>
  );
} 