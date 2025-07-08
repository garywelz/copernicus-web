// components/CategoryTabs.tsx
// Category filtering component matching your website structure

import React from 'react';

interface CategoryTabsProps {
  selectedCategory: string;
  onCategoryChange: (category: string) => void;
  categoryStats: Record<string, number>;
}

const CATEGORY_CONFIG = {
  all: {
    label: 'All Episodes',
    icon: '🎯',
    color: 'bg-blue-500 hover:bg-blue-600'
  },
  biology: {
    label: 'Biology',
    icon: '🧬',
    color: 'bg-green-500 hover:bg-green-600'
  },
  chemistry: {
    label: 'Chemistry',
    icon: '⚗️',
    color: 'bg-purple-500 hover:bg-purple-600'
  },
  physics: {
    label: 'Physics',
    icon: '⚛️',
    color: 'bg-blue-500 hover:bg-blue-600'
  },
  mathematics: {
    label: 'Mathematics',
    icon: '📐',
    color: 'bg-red-500 hover:bg-red-600'
  },
  'computer-science': {
    label: 'Computer Science',
    icon: '💻',
    color: 'bg-gray-500 hover:bg-gray-600'
  },
  news: {
    label: 'News',
    icon: '📰',
    color: 'bg-yellow-500 hover:bg-yellow-600'
  },
  science: {
    label: 'General Science',
    icon: '🔬',
    color: 'bg-indigo-500 hover:bg-indigo-600'
  }
};

export default function CategoryTabs({ selectedCategory, onCategoryChange, categoryStats }: CategoryTabsProps) {
  const totalEpisodes = Object.values(categoryStats).reduce((sum, count) => sum + count, 0);
  
  return (
    <div className="mb-8">
      <div className="flex flex-wrap gap-2 justify-center">
        {Object.entries(CATEGORY_CONFIG).map(([category, config]) => {
          const count = category === 'all' ? totalEpisodes : (categoryStats[category] || 0);
          const isSelected = selectedCategory === category;
          
          // Don't show categories with no episodes (except 'all')
          if (category !== 'all' && count === 0) {
            return null;
          }
          
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
              aria-label={`Filter by ${config.label}`}
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
      
      {/* Category description */}
      {selectedCategory !== 'all' && (
        <div className="mt-4 text-center text-gray-600">
          <p className="text-sm">
            Showing {categoryStats[selectedCategory] || 0} episodes in{' '}
            <span className="font-medium text-gray-800">
              {CATEGORY_CONFIG[selectedCategory as keyof typeof CATEGORY_CONFIG]?.label}
            </span>
          </p>
        </div>
      )}
    </div>
  );
}

// Enhanced episode list component
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

interface EpisodeListProps {
  episodes: Episode[];
  selectedCategory: string;
}

export function EpisodeList({ episodes, selectedCategory }: EpisodeListProps) {
  const getCategoryIcon = (category: string) => {
    return CATEGORY_CONFIG[category as keyof typeof CATEGORY_CONFIG]?.icon || '🎯';
  };
  
  const getCategoryColor = (category: string) => {
    return CATEGORY_CONFIG[category as keyof typeof CATEGORY_CONFIG]?.color.split(' ')[0] || 'bg-gray-500';
  };
  
  return (
    <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-3">
      {episodes.map((episode) => (
        <div
          key={episode.id}
          className="bg-white rounded-lg shadow-md hover:shadow-lg transition-shadow duration-200 overflow-hidden"
        >
          {/* Episode thumbnail */}
          <div className="relative aspect-video bg-gray-200">
            <img
              src={episode.thumbnail_url}
              alt={episode.title}
              className="w-full h-full object-cover"
              onError={(e) => {
                // Fallback to Copernicus portrait if episode thumbnail fails
                (e.target as HTMLImageElement).src = 'https://storage.googleapis.com/regal-scholar-453620-r7-podcast-storage/images/copernicus-original-portrait.jpg';
              }}
            />
            
            {/* Category badge */}
            <div className={`absolute top-2 left-2 px-2 py-1 rounded-full text-white text-xs font-medium ${getCategoryColor(episode.category)}`}>
              <span className="mr-1">{getCategoryIcon(episode.category)}</span>
              {CATEGORY_CONFIG[episode.category as keyof typeof CATEGORY_CONFIG]?.label || 'Science'}
            </div>
          </div>
          
          {/* Episode content */}
          <div className="p-4">
            <h3 className="font-bold text-lg mb-2 line-clamp-2">
              {episode.title}
            </h3>
            
            <p className="text-gray-600 text-sm mb-4 line-clamp-3">
              {episode.description}
            </p>
            
            {/* Episode actions */}
            <div className="flex gap-2 flex-wrap">
              <a
                href={episode.audio_url}
                target="_blank"
                rel="noopener noreferrer"
                className="flex-1 bg-blue-500 hover:bg-blue-600 text-white px-3 py-2 rounded text-sm font-medium text-center transition-colors"
              >
                🎵 Listen
              </a>
              
              <a
                href={episode.spotify_url}
                target="_blank"
                rel="noopener noreferrer"
                className="flex-1 bg-green-500 hover:bg-green-600 text-white px-3 py-2 rounded text-sm font-medium text-center transition-colors"
              >
                🎧 Spotify
              </a>
            </div>
            
            {/* Episode metadata */}
            <div className="mt-3 text-xs text-gray-500 flex justify-between">
              <span>Episode {episode.id}</span>
              <span>{new Date(episode.published_at).toLocaleDateString()}</span>
            </div>
          </div>
        </div>
      ))}
    </div>
  );
}

// Main podcast page component
interface PodcastPageProps {
  initialEpisodes: Episode[];
  initialStats: Record<string, number>;
}

export function PodcastPage({ initialEpisodes, initialStats }: PodcastPageProps) {
  const [episodes, setEpisodes] = React.useState<Episode[]>(initialEpisodes);
  const [categoryStats, setCategoryStats] = React.useState(initialStats);
  const [selectedCategory, setSelectedCategory] = React.useState('all');
  const [loading, setLoading] = React.useState(false);
  
  const handleCategoryChange = async (category: string) => {
    setSelectedCategory(category);
    setLoading(true);
    
    try {
      const response = await fetch(`/api/spotify?category=${category}`);
      const data = await response.json();
      
      if (data.episodes) {
        setEpisodes(data.episodes);
        setCategoryStats(data.stats.categories);
      }
    } catch (error) {
      console.error('Error fetching episodes:', error);
    } finally {
      setLoading(false);
    }
  };
  
  return (
    <div className="max-w-7xl mx-auto px-4 py-8">
      <div className="text-center mb-8">
        <h1 className="text-4xl font-bold mb-4">Copernicus AI: Frontiers of Research</h1>
        <p className="text-gray-600 max-w-2xl mx-auto">
          Educational podcast covering cutting-edge research in physics, biology, chemistry, 
          mathematics, and computer science. Hosted by AI in the spirit of Nicolaus Copernicus.
        </p>
      </div>
      
      <CategoryTabs
        selectedCategory={selectedCategory}
        onCategoryChange={handleCategoryChange}
        categoryStats={categoryStats}
      />
      
      {loading ? (
        <div className="text-center py-12">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-500 mx-auto"></div>
          <p className="mt-4 text-gray-600">Loading episodes...</p>
        </div>
      ) : (
        <EpisodeList episodes={episodes} selectedCategory={selectedCategory} />
      )}
    </div>
  );
} 