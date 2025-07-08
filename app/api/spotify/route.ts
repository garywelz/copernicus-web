<<<<<<< HEAD
// app/api/spotify/route.js (Next.js 13+ App Router)
// This replaces the old Spotify API integration with RSS feed data

import { NextResponse } from 'next/server';

// Category mapping for proper website filtering
const CATEGORY_MAPPING = {
  'biology': 'biology',
  'chemistry': 'chemistry', 
  'physics': 'physics',
  'mathematics': 'mathematics',
  'computer-science': 'computer-science',
  'science': 'science',
  'news': 'news'
};

// Enhanced categorization based on title and description
function categorizeEpisode(title: string, description: string): string {
  const content = `${title} ${description}`.toLowerCase();
  
  // Check for news episodes first - this should take priority
  if (content.includes('news')) {
    return 'news';
  }
  
  // Check for episode 1 patterns that might be news
  if (content.includes('episode 1')) {
    // Determine subject for news episodes
    if (content.includes('biology')) return 'biology';
    if (content.includes('chemistry')) return 'chemistry';
    if (content.includes('physics')) return 'physics';
    if (content.includes('mathematics') || content.includes('math')) return 'mathematics';
    if (content.includes('computer') || content.includes('compsci')) return 'computer-science';
    return 'news';
  }
  
  // Biology-specific keywords
  if (content.includes('biology') || content.includes('cell') || content.includes('dna') || 
      content.includes('gene') || content.includes('crispr') || content.includes('organoids') ||
      content.includes('mitosis') || content.includes('optogenetics') || content.includes('synthetic biology') ||
      content.includes('spatial biology') || content.includes('neural') || content.includes('organ')) {
    return 'biology';
  }
  
  // Chemistry-specific keywords
  if (content.includes('chemistry') || content.includes('chemical') || content.includes('catalyst') || 
      content.includes('molecular') || content.includes('computational chemistry') || content.includes('green chemistry') ||
      content.includes('reaction') || content.includes('synthesis')) {
    return 'chemistry';
  }
  
  // Physics-specific keywords
  if (content.includes('physics') || content.includes('quantum') || content.includes('black hole') || 
      content.includes('higgs') || content.includes('spacetime') || content.includes('relativity') ||
      content.includes('string theory') || content.includes('theory of everything') || content.includes('particle') ||
      content.includes('entanglement') || content.includes('batteries')) {
    return 'physics';
  }
  
  // Mathematics-specific keywords
  if (content.includes('mathematics') || content.includes('mathematical') || content.includes('theorem') || 
      content.includes('conjecture') || content.includes('continuum hypothesis') || content.includes('gödel') || 
      content.includes('poincaré') || content.includes('arithmetic') || content.includes('peano') ||
      content.includes('incompleteness') || content.includes('logic')) {
    return 'mathematics';
  }
  
  // Computer Science-specific keywords
  if (content.includes('computer') || content.includes('computing') || content.includes('algorithm') || 
      content.includes('machine learning') || content.includes('artificial intelligence') || content.includes('edge computing') ||
      content.includes('neuromorphic') || content.includes('ai') || content.includes('agi') || 
      content.includes('artificial general intelligence') || content.includes('neural network')) {
    return 'computer-science';
  }
  
  return 'news';
}

// Create episode slug from title
function createSlug(title: string): string {
  return title
    .toLowerCase()
    .replace(/[^\w\s-]/g, '')
    .replace(/\s+/g, '-')
    .replace(/-+/g, '-')
    .trim();
}

// Mapping of episode titles to available thumbnail names
const THUMBNAIL_MAPPING: { [key: string]: string } = {
  // News episodes with specific thumbnails
  'biology-news': 'crispr-based',
  'chemistry-news': 'chemical-bonds',
  'compsci-news': 'machine-learning',
  'math-news': 'a-new-approach-to-prime-gap-distributions',
  'physics-news': 'quantum-mechanics-principles',
  'science-news': 'synthetic-biology',
  
  // Core science topics
  'machine-learning': 'machine-learning',
  'quantum-computing': 'quantum-computing-episode',
  'quantum-mechanics': 'quantum-mechanics-principles',
  'quantum-machine-learning': 'machine-learning',
  'quantum-batteries': 'quantum-mechanics-principles',
  'quantum-cryptography': 'quantum-mechanics-principles',
  'quantum-entanglement': 'quantum-mechanics-principles',
  
  // Mathematics
  'calculus-derivatives': 'calculus-derivatives-basics',
  'calculus': 'calculus-derivatives-basics',
  'mathematics': 'mathematics-archive',
  'mathematical': 'mathematics-archive',
  'chaos': 'overview-chaos-in-mathematics',
  'riemann': 'riemann-hypothesis-and-primes',
  'prime': 'a-new-approach-to-prime-gap-distributions',
  'independence': 'mathematics-archive',
  'peano': 'mathematics-archive',
  'continuum': 'mathematics-archive',
  'godel': 'mathematics-archive',
  'incompleteness': 'mathematics-archive',
  'frontiers': 'mathematics-archive',
  
  // Biology
  'cell-division': 'cell-division',
  'cellular-mitosis': 'cellular-mitosis',
  'cell': 'cell-division',
  'mitosis': 'cellular-mitosis',
  'crispr': 'crispr-based',
  'organoids': 'synthetic-minimal',
  'spatial-biology': 'improving-progressive',
  'synthetic-biology': 'synthetic-biology',
  'neural-optogenetics': 'real-time',
  'optogenetics': 'real-time',
  'biology': 'crispr-based',
  
  // Chemistry
  'chemical-bonds': 'chemical-bonds',
  'chemistry': 'chemical-bonds',
  'green-chemistry': 'chemical-bonds',
  'molecular-machines': 'chemical-bonds',
  'catalysis': 'chemical-bonds',
  'computational-chemistry': 'chemical-bonds',
  
  // Physics
  'string-theory': 'quantum-mechanics-principles',
  'physics': 'quantum-mechanics-principles',
  
  // Computer Science
  'edge-computing': 'machine-learning',
  'neuromorphic': 'machine-learning',
  'artificial-general-intelligence': 'machine-learning',
  'agi': 'machine-learning',
  'computer': 'machine-learning',
  'computing': 'machine-learning',
  'ai': 'machine-learning'
};

// Get thumbnail URL for episode
function getThumbnailUrl(title: string): string {
  const lowerTitle = title.toLowerCase();
  
  // Precise title-to-thumbnail mapping
  const exactMappings: { [key: string]: string } = {
    // News episodes
    'biology news - episode 1': 'biology-news',
    'chemistry news - episode 1': 'chemistry-news', 
    'compsci news - episode 1': 'compsci-news',
    'math news - episode 1': 'math-news',
    'physics news - episode 1': 'physics-news',
    'science news - episode 1': 'science-news',
    
    // Specific episodes with exact matches
    'the promise and challenges of artificial general intelligence': 'artificial-general-intelligence',
    'black holes: cosmic enigmas of spacetime': 'black-holes',
    'the independence of the continuum hypothesis: set theory\'s enduring mystery': 'continuum-hypothesis',
    'independence results in peano arithmetic': 'peano-arithmetic',
    'gödel\'s incompleteness theorems: the limits of mathematical truth': 'godels-incompleteness',
    'frontiers of mathematical logic: recent breakthroughs in 2024': 'mathematical-logic',
    'the poincaré conjecture: a century-long mathematical journey': 'poincare-conjecture',
    
    // Biology episodes
    'crispr chemistry: precise molecular editing beyond dna': 'crispr-chemistry',
    'organoids: miniature organs in a dish': 'organoids',
    'spatial biology and cell atlas projects: mapping life\'s building blocks': 'spatial-biology',
    'synthetic biology: redesigning life\'s building blocks': 'synthetic-biology',
    'neural optogenetics': 'real-time',
    'crispr epigenome': 'crispr-epigenome',
    'minimal cells': 'synthetic-minimal',
    
    // Chemistry episodes  
    'catalysis revolution: transforming chemical reactions': 'catalysis-revolution',
    'computational chemistry: simulating molecular reality': 'computational-chemistry',
    'green chemistry: sustainable approaches to chemical synthesis': 'green-chemistry',
    'molecular machines: engineering at the nanoscale': 'molecular-machines',
    
    // Physics episodes
    'the higgs boson: hunt for the god particle': 'higgs-boson',
    'quantum batteries: the future of energy storage': 'quantum-batteries',
    'quantum cryptography and post-quantum security': 'quantum-cryptography',
    'quantum entanglement: spooky action at a distance': 'quantum-entanglement',
    'quantum machine learning: when quantum computing meets ai': 'quantum-machine-learning',
    'string theory: the quest for a theory of everything': 'string-theory',
    
    // Computer Science episodes
    'edge computing architectures: bringing intelligence to the data frontier': 'edge-computing',
    'neuromorphic computing: brain-inspired computer architectures': 'neuromorphic-computing'
  };
  
  // Check for exact matches first
  if (exactMappings[lowerTitle]) {
    return `https://storage.googleapis.com/regal-scholar-453620-r7-podcast-storage/images/episodes/${exactMappings[lowerTitle]}-thumbnail.jpg`;
  }
  
  // Fallback keyword matching for any missed episodes
  if (lowerTitle.includes('machine learning') || lowerTitle.includes('artificial intelligence')) {
    return `https://storage.googleapis.com/regal-scholar-453620-r7-podcast-storage/images/episodes/machine-learning-thumbnail.jpg`;
  }
  if (lowerTitle.includes('quantum')) {
    return `https://storage.googleapis.com/regal-scholar-453620-r7-podcast-storage/images/episodes/quantum-mechanics-principles-thumbnail.jpg`;
  }
  if (lowerTitle.includes('crispr')) {
    return `https://storage.googleapis.com/regal-scholar-453620-r7-podcast-storage/images/episodes/crispr-based-thumbnail.jpg`;
  }
  if (lowerTitle.includes('chemistry') || lowerTitle.includes('chemical')) {
    return `https://storage.googleapis.com/regal-scholar-453620-r7-podcast-storage/images/episodes/chemical-bonds-thumbnail.jpg`;
  }
  if (lowerTitle.includes('mathematics') || lowerTitle.includes('mathematical')) {
    return `https://storage.googleapis.com/regal-scholar-453620-r7-podcast-storage/images/episodes/mathematics-archive-thumbnail.jpg`;
  }
  if (lowerTitle.includes('biology') || lowerTitle.includes('cell')) {
    return `https://storage.googleapis.com/regal-scholar-453620-r7-podcast-storage/images/episodes/cell-division-thumbnail.jpg`;
  }
  
  // Fallback to Copernicus portrait for episodes without specific thumbnails
  return 'https://storage.googleapis.com/regal-scholar-453620-r7-podcast-storage/images/copernicus-original-portrait.jpg';
}

// Fetch and parse RSS feed
async function fetchRSSFeed() {
  try {
    // Use environment variable for RSS feed, fallback to canonical feed
    const rssFeedUrl = process.env.PODCAST_RSS_FEED_URL || 'https://storage.googleapis.com/regal-scholar-453620-r7-podcast-storage/rss-feed.xml';
    const response = await fetch(rssFeedUrl);
    
    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }
    
    const xmlText = await response.text();
    
    // Parse XML manually (since we can't use DOMParser in Node.js)
    const episodes = [];
    // ES2017-compatible: split on <item> and manually extract content
    const itemBlocks = xmlText.split('<item>').slice(1);
    let id = 1;
    for (const block of itemBlocks) {
      const itemContent = block.split('</item>')[0];
      
      // Extract title
      const titleMatch = itemContent.match(/<title><!\[CDATA\[(.*?)\]\]><\/title>|<title>(.*?)<\/title>/);
      const title = titleMatch ? (titleMatch[1] || titleMatch[2]) : `Episode ${id}`;
      
      // Extract description
      const descMatch = itemContent.match(/<description><!\[CDATA\[(.*?)\]\]><\/description>|<description>(.*?)<\/description>/);
      const description = descMatch ? (descMatch[1] || descMatch[2]) : '';
      
      // Extract audio URL
      const enclosureMatch = itemContent.match(/<enclosure\s+url="([^"]+)"/);
      const audioUrl = enclosureMatch ? enclosureMatch[1] : '';
      
      // Extract publication date
      const pubDateMatch = itemContent.match(/<pubDate>(.*?)<\/pubDate>/);
      const pubDate = pubDateMatch ? pubDateMatch[1] : '2025-03-26T00:00:00';
      
      // Categorize episode
      const category = categorizeEpisode(title, description);
      const slug = createSlug(title);
      
      episodes.push({
        id: id++,
        title,
        description,
        slug,
        category,
        audio_url: audioUrl,
        thumbnail_url: getThumbnailUrl(title),
        web_url: `https://copernicusai.fyi/episodes/${slug}`,
        published_at: pubDate,
        duration: 'Unknown',
        spotify_url: 'https://open.spotify.com/show/14YNKUgCOFC2UhGKYJMos5',
        apple_url: `https://podcasts.apple.com/podcast/${slug}`
      });
    }
    
    return episodes;
  } catch (error) {
    console.error('Error fetching RSS feed:', error);
    return [];
  }
}

// Main API handler
export async function GET(request: Request) {
  // TEMP: Test API route works at all
  if (process.env.TEST_API === '1') {
    return NextResponse.json({ ok: true, message: 'API route is alive' });
  }
  try {
    console.log('API: about to fetch RSS feed');
    const episodes = await fetchRSSFeed();
    console.log('API: fetched episodes', episodes && episodes.length);
    
    // Get URL parameters for filtering
    const { searchParams } = new URL(request.url);
    const category = searchParams.get('category');
    const limit = searchParams.get('limit');
    
    // Filter by category if specified
    let filteredEpisodes = episodes;
    if (category && category !== 'all') {
      filteredEpisodes = episodes.filter(episode => episode.category === category);
    }
    
    // Apply limit if specified
    if (limit) {
      filteredEpisodes = filteredEpisodes.slice(0, parseInt(limit));
    }
    
    // Generate category statistics
    const categoryStats: { [key: string]: number } = {};
    episodes.forEach(episode => {
      categoryStats[episode.category] = (categoryStats[episode.category] || 0) + 1;
    });
    
    // Create response data structure matching your website expectations
    const responseData = {
      podcast: {
        title: "Copernicus AI: Frontiers of Research",
        description: "Educational podcast covering cutting-edge research in physics, biology, chemistry, mathematics, and computer science. Hosted by AI in the spirit of Nicolaus Copernicus.",
        cover_art: "https://storage.googleapis.com/regal-scholar-453620-r7-podcast-storage/images/copernicus-original-portrait.jpg",
        rss_feed: "https://storage.googleapis.com/regal-scholar-453620-r7-podcast-storage/feeds/copernicus-historical-podcast-feed.xml",
        spotify_url: "https://open.spotify.com/show/14YNKUgCOFC2UhGKYJMos5",
        website: "https://copernicusai.fyi"
      },
      episodes: filteredEpisodes,
      stats: {
        total_episodes: episodes.length,
        categories: categoryStats,
        filtered_count: filteredEpisodes.length,
        last_updated: new Date().toISOString()
      }
    };
    
    return NextResponse.json(responseData);
    
  } catch (error) {
    console.error('API Error:', error);
    return NextResponse.json(
      { error: 'Failed to fetch podcast data', message: error instanceof Error ? error.message : 'Unknown error' },
      { status: 500 }
    );
  }
}

 
=======
import { NextResponse } from 'next/server'
import { getAccessToken } from '@/lib/spotify'

export const dynamic = 'force-dynamic'

export async function GET() {
  try {
    const token = await getAccessToken()
    return NextResponse.json({ access_token: token })
  } catch (error) {
    console.error('Error getting Spotify access token:', error)
    return NextResponse.json(
      { error: 'Failed to get Spotify access token' },
      { status: 500 }
    )
  }
} 
>>>>>>> 7c13d53b1e209c067ff2ff680d00fe9aec2fd3bb
