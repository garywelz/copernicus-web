// app/api/spotify/route.js (Next.js 13+ App Router)
// This replaces the old Spotify API integration with RSS feed data

import { NextResponse } from 'next/server';
import { appendFile } from 'fs/promises';

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
function getThumbnailUrl(title: string, canonicalFilename?: string): string {
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
  }
  // Fallback to slug mapping (legacy)
  const slug = createSlug(title);
  if (slug) {
    return `https://storage.googleapis.com/regal-scholar-453620-r7-podcast-storage/images/thumbnails/${slug}-thumb.jpg`;
  }
  // Fallback to Copernicus portrait
  return 'https://storage.googleapis.com/regal-scholar-453620-r7-podcast-storage/images/copernicus-original-portrait.jpg';
}

// Fetch and parse RSS feed from local canonical XML
import { promises as fs } from 'fs';
import { parseStringPromise } from 'xml2js';

async function fetchRSSFeed() {
  try {
    // Read the canonical RSS XML from disk
    const xmlText = await fs.readFile('/home/gdubs/copernicus-web-public/copernicus-mvp-rss-feed.xml', 'utf-8');
    // Parse XML using xml2js
    const rss = await parseStringPromise(xmlText, { explicitArray: false, mergeAttrs: true });
    const items = rss.rss.channel.item || [];
    const episodes = items.map((item: any, idx: number) => {
      // Extract all relevant fields from RSS
      return {
        id: idx + 1,
        guid: item.guid?._ || item.guid || '',
        title: item.title || '',
        // Strip HTML tags from description for frontend display
        description: (item.description || '').replace(/<[^>]+>/g, ''),
        summary: item['itunes:summary'] || '',
        slug: item.title ? createSlug(item.title) : '',
        // Assign canonical category from guid/filename
        category: (() => {
          const guid = item.guid?._ || item.guid || '';
          if (guid.startsWith('news-')) return 'news';
          if (guid.startsWith('ever-bio')) return 'biology';
          if (guid.startsWith('ever-chem')) return 'chemistry';
          if (guid.startsWith('ever-compsci')) return 'computer-science';
          if (guid.startsWith('ever-math')) return 'mathematics';
          if (guid.startsWith('ever-phys')) return 'physics';
          return 'science';
        })(),
        published_at: item.pubDate || '',
        audio_url: item.enclosure?.url || '',
        duration: item['itunes:duration'] || '',
        episode: item['itunes:episode'] || '',
        season: item['itunes:season'] || '',
        explicit: item['itunes:explicit'] || '',
        episode_type: item['itunes:episodeType'] || '',
        thumbnail_url: (() => {
          const guid = item.guid?._ || item.guid || '';
          return `https://storage.googleapis.com/regal-scholar-453620-r7-podcast-storage/thumbnails/${guid}-thumb.jpg`;
        })(),
        // Add any other Apple/Spotify tags as needed
      };
    });
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
      filteredEpisodes = episodes.filter((episode: any) => episode.category === category);
    }
    
    // Apply limit if specified
    if (limit) {
      filteredEpisodes = filteredEpisodes.slice(0, parseInt(limit));
    }
    
    // Generate category statistics
    const categoryStats: { [key: string]: number } = {};
    episodes.forEach((episode: any) => {
      categoryStats[episode.category] = (categoryStats[episode.category] || 0) + 1;
    });
    
    // Create response data structure matching your website expectations
    const responseData = {
      podcast: {
        title: "Copernicus AI: Frontiers of Research",
        description: "Educational podcast covering cutting-edge research in physics, biology, chemistry, mathematics, and computer science. Hosted by AI in the spirit of Nicolaus Copernicus.",
        cover_art: "https://storage.googleapis.com/regal-scholar-453620-r7-podcast-storage/images/copernicus-original-portrait.jpg",
        rss_feed: "https://storage.googleapis.com/regal-scholar-453620-r7-podcast-storage/feeds/copernicus-mvp-rss-feed.xml",
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

 
