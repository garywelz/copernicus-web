const { parseStringPromise } = require('xml2js');

const RSS_FEED_URL =
  process.env.COPERNICUS_RSS_FEED_URL ??
  'https://storage.googleapis.com/regal-scholar-453620-r7-podcast-storage/feeds/copernicus-mvp-rss-feed.xml';

const EPISODE_API_BASE =
  process.env.COPERNICUS_API_BASE_URL ??
  'https://copernicus-podcast-api-204731194849.us-central1.run.app';

function pickString(value) {
  if (!value) return undefined;
  if (Array.isArray(value)) {
    const first = value[0];
    if (typeof first === 'string') return first;
    if (first && typeof first === 'object' && '_' in first) return first._;
  }
  if (typeof value === 'string') return value;
  if (value && typeof value === 'object' && '_' in value) return value._;
  return undefined;
}

function normalizeApiEpisode(payload = {}, slug) {
  const descriptionMarkdown = payload.description_markdown ?? payload.descriptionMarkdown;
  const descriptionHtml =
    payload.description_html ??
    descriptionMarkdown ??
    '<p>No episode description available.</p>';

  return {
    title: payload.title ?? 'Copernicus AI Episode',
    descriptionHtml,
    summary: payload.summary ?? descriptionMarkdown ?? '',
    category: payload.category ?? payload.category_slug ?? '',
    pubDate: payload.generated_at ?? payload.created_at ?? '',
    duration: payload.duration ?? payload.request?.duration ?? '',
    audioUrl: payload.audio_url ?? '',
    imageUrl: payload.thumbnail_url ?? '',
    attribution: payload.creator_attribution ?? '',
    slug: payload.slug ?? payload.episode_id ?? slug,
  };
}

async function fetchEpisodeFromApi(slug) {
  try {
    const endpoint = `${EPISODE_API_BASE}/api/episodes/${encodeURIComponent(slug)}`;
    const response = await fetch(endpoint);
    if (response.status === 404) {
      return null;
    }
    if (!response.ok) {
      throw new Error(`API episode request failed: ${response.status}`);
    }
    const data = await response.json();
    return normalizeApiEpisode(data, slug);
  } catch (error) {
    console.error('Episode API fetch failed:', error);
    throw error;
  }
}

async function fetchEpisodeFromRss(slug) {
  const response = await fetch(RSS_FEED_URL);
  if (!response.ok) {
    throw new Error(`Failed to fetch RSS feed: ${response.status}`);
  }

  const xml = await response.text();
  const parsed = await parseStringPromise(xml, { explicitArray: true });
  const items = parsed?.rss?.channel?.[0]?.item ?? [];

  const episode = items.find((item) => {
    const guidValue = pickString(item.guid);
    if (guidValue && guidValue.trim() === slug) {
      return true;
    }
    const linkValue = pickString(item.link);
    return linkValue && linkValue.endsWith(slug);
  });

  if (!episode) {
    return null;
  }

  return {
    title: pickString(episode.title) ?? 'Copernicus AI Podcast Episode',
    descriptionHtml:
      pickString(episode['content:encoded']) ??
      pickString(episode.description) ??
      '<p>No description available.</p>',
    summary: pickString(episode['itunes:summary']) ?? '',
    category: pickString(episode.category) ?? '',
    pubDate: pickString(episode.pubDate) ?? '',
    duration: pickString(episode['itunes:duration']) ?? '',
    audioUrl: episode.enclosure?.[0]?.$?.url ?? '',
    imageUrl:
      episode['itunes:image']?.[0]?.$?.href ??
      episode['media:thumbnail']?.[0]?.$?.url ??
      '',
    attribution: pickString(episode['podcast:person']),
  };
}

async function handler(req, res) {
  if (req.method !== 'GET') {
    res.setHeader('Allow', 'GET');
    return res.status(405).json({ error: 'Method not allowed' });
  }

  // Try to get episodeId from query params first
  let episodeId = req.query.episodeId;
  
  // If not in query, try to extract from URL path
  // Handles both /api/episodes?episodeId=xxx and /api/episodes/xxx
  if (!episodeId && req.url) {
    // Extract from URL path: /api/episodes/ever-bio-250036
    const match = req.url.match(/\/episodes\/([^/?]+)/);
    if (match) {
      episodeId = match[1];
    }
  }
  
  if (!episodeId) {
    console.error('Missing episode identifier. Query:', req.query, 'URL:', req.url);
    return res.status(400).json({ error: 'Missing episode identifier' });
  }

  try {
    let episode;
    try {
      episode = await fetchEpisodeFromApi(episodeId);
    } catch (apiError) {
      console.warn('Falling back to RSS feed for episode:', episodeId);
    }

    if (!episode) {
      episode = await fetchEpisodeFromRss(episodeId);
    }

    if (!episode) {
      return res.status(404).send('Episode not found');
    }

    const {
      title,
      descriptionHtml,
      summary,
      category,
      pubDate,
      duration,
      audioUrl,
      imageUrl,
      attribution,
    } = episode;

    const html = `<!DOCTYPE html>
<html lang="en">
  <head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    <title>${title}</title>
    ${summary ? `<meta name="description" content="${summary.replace(/"/g, '&quot;')}" />` : ''}
    ${imageUrl ? `<meta property="og:image" content="${imageUrl}" />` : ''}
    <meta property="og:title" content="${title}" />
    <meta property="og:type" content="website" />
    ${summary ? `<meta property="og:description" content="${summary.replace(/"/g, '&quot;')}" />` : ''}
    <style>
      body { font-family: system-ui, -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; margin: 0; padding: 2rem; background-color: #f4f5f7; color: #1f2933; }
      main { max-width: 820px; margin: 0 auto; background: #fff; border-radius: 16px; box-shadow: 0 12px 35px rgba(15, 23, 42, 0.08); overflow: hidden; }
      header { padding: 2.5rem 2.5rem 2rem; border-bottom: 1px solid #e5e7eb; background: linear-gradient(135deg, #1d4ed8, #9333ea 65%); color: #fff; }
      header h1 { margin: 0 0 0.75rem; font-size: clamp(1.75rem, 3vw, 2.4rem); line-height: 1.2; }
      header .meta { font-size: 0.95rem; opacity: 0.9; display: flex; flex-wrap: wrap; gap: 0.75rem; align-items: center; }
      header .meta span { display: inline-flex; align-items: center; gap: 0.4rem; background: rgba(255, 255, 255, 0.16); padding: 0.35rem 0.75rem; border-radius: 999px; }
      section { padding: 2rem 2.5rem; }
      img.hero { max-width: 100%; border-radius: 18px; margin: 1.5rem 0; box-shadow: 0 15px 35px rgba(30, 64, 175, 0.22); }
      audio { width: 100%; margin-top: 1rem; }
      .description { font-size: 1.05rem; line-height: 1.65; color: #1f2937; }
      .description h1, .description h2, .description h3 { color: #0f172a; margin-top: 2rem; }
      .description a { color: #1d4ed8; }
      footer { padding: 1.75rem 2.5rem; border-top: 1px solid #e5e7eb; background: #f9fafb; font-size: 0.95rem; color: #4b5563; display: flex; flex-wrap: wrap; gap: 1rem; justify-content: space-between; align-items: center; }
      .actions a { display: inline-flex; align-items: center; gap: 0.5rem; padding: 0.75rem 1.2rem; border-radius: 999px; text-decoration: none; font-weight: 600; transition: transform 0.15s ease, background 0.15s ease; }
      .actions a.listen { background: #1d4ed8; color: #fff; }
      .actions a.download { background: #e0e7ff; color: #1d4ed8; }
      .actions a:hover { transform: translateY(-2px); }
      @media (max-width: 640px) {
        header, section, footer { padding: 1.8rem; }
        header .meta { flex-direction: column; align-items: flex-start; }
      }
    </style>
  </head>
  <body>
    <main>
      <header>
        <h1>${title}</h1>
        <div class="meta">
          ${category ? `<span>🧭 ${category}</span>` : ''}
          ${duration ? `<span>⏱️ ${duration}</span>` : ''}
          ${pubDate ? `<span>📅 ${pubDate}</span>` : ''}
          ${attribution ? `<span>👤 Contributor: ${attribution}</span>` : ''}
        </div>
      </header>
      <section>
        ${imageUrl ? `<img class="hero" src="${imageUrl}" alt="${title} artwork" loading="lazy" />` : ''}
        ${audioUrl ? `<audio controls preload="metadata" src="${audioUrl}"></audio>` : ''}
        <article class="description">${descriptionHtml}</article>
      </section>
      <footer>
        <div>Part of the Copernicus AI Podcast</div>
        <div class="actions">
          ${audioUrl ? `<a class="listen" href="${audioUrl}">▶️ Listen</a>` : ''}
          <a class="download" href="https://storage.googleapis.com/regal-scholar-453620-r7-podcast-storage/feeds/copernicus-mvp-rss-feed.xml">📡 RSS Feed</a>
        </div>
      </footer>
    </main>
  </body>
</html>`;

    res.setHeader('Content-Type', 'text/html; charset=utf-8');
    res.setHeader('Cache-Control', 'public, max-age=300');
    return res.status(200).send(html);
  } catch (error) {
    console.error('Failed to render episode page:', error);
    return res.status(500).send('Failed to load episode page');
  }
}

module.exports = handler;



