// Vercel serverless function to proxy RSS feed with CORS headers
export default async function handler(req, res) {
  try {
    const RSS_FEED_URL = 'https://storage.googleapis.com/regal-scholar-453620-r7-podcast-storage/feeds/copernicus-mvp-rss-feed.xml';
    
    // Fetch the RSS feed
    const response = await fetch(RSS_FEED_URL);
    
    if (!response.ok) {
      throw new Error(`Failed to fetch RSS feed: ${response.status}`);
    }
    
    const xmlText = await response.text();
    
    // Set CORS headers
    res.setHeader('Access-Control-Allow-Origin', '*');
    res.setHeader('Access-Control-Allow-Methods', 'GET, OPTIONS');
    res.setHeader('Access-Control-Allow-Headers', 'Content-Type');
    res.setHeader('Content-Type', 'application/xml');
    res.setHeader('Cache-Control', 'public, max-age=300'); // Cache for 5 minutes
    
    // Return the XML
    res.status(200).send(xmlText);
  } catch (error) {
    console.error('Error proxying RSS feed:', error);
    res.status(500).json({ error: 'Failed to fetch RSS feed', message: error.message });
  }
}

