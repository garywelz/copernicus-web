import { cache } from 'react';
import { Metadata } from 'next';
import { notFound } from 'next/navigation';

type EpisodeRecord = {
  title: string;
  slug: string;
  descriptionHtml: string;
  summary: string;
  audioUrl: string;
  thumbnailUrl?: string;
  pubDate?: string;
  duration?: string;
  category?: string;
  attribution?: string;
};

const EPISODE_API_BASE =
  process.env.COPERNICUS_API_BASE_URL ??
  'https://copernicus-podcast-api-204731194849.us-central1.run.app';

const getEpisodeFromCatalog = cache(async (slug: string): Promise<EpisodeRecord | null> => {
  const endpoint = `${EPISODE_API_BASE}/api/episodes/${encodeURIComponent(slug)}`;
  const response = await fetch(endpoint, {
    next: { revalidate: 300 },
    cache: 'no-store',
  });

  if (response.status === 404) {
    return null;
  }

  if (!response.ok) {
    console.error(`Failed to fetch episode from catalog: ${response.status}`);
    throw new Error('Unable to load episode data.');
  }

  const data = (await response.json()) as Record<string, any>;
  const descriptionMarkdown = data.description_markdown ?? data.descriptionMarkdown;

  const descriptionHtml =
    data.description_html ??
    descriptionMarkdown ??
    '<p>No episode description is available for this entry.</p>';

  return {
    title: data.title ?? 'Untitled Episode',
    slug: data.slug ?? data.episode_id ?? slug,
    descriptionHtml,
    summary: data.summary ?? descriptionMarkdown ?? '',
    audioUrl: data.audio_url ?? '',
    thumbnailUrl: data.thumbnail_url ?? undefined,
    pubDate: data.generated_at ?? data.created_at,
    duration: data.duration ?? data.request?.duration,
    category: data.category ?? data.category_slug,
    attribution: data.creator_attribution,
  };
});

type EpisodePageParams = {
  params: { episodeId: string };
};

export async function generateMetadata({ params }: EpisodePageParams): Promise<Metadata> {
  const episode = await getEpisodeFromCatalog(params.episodeId);

  if (!episode) {
    return {
      title: 'Episode Not Found | Copernicus AI Podcast',
      description: 'The requested Copernicus AI podcast episode could not be located.',
    };
  }

  return {
    title: `${episode.title} | Copernicus AI Podcast`,
    description: episode.summary || 'Listen to the latest Copernicus AI research podcast episode.',
    openGraph: {
      title: episode.title,
      description: episode.summary,
      images: episode.thumbnailUrl ? [episode.thumbnailUrl] : undefined,
    },
    twitter: {
      card: 'summary_large_image',
      title: episode.title,
      description: episode.summary,
      images: episode.thumbnailUrl ? [episode.thumbnailUrl] : undefined,
    },
  };
}

export default async function EpisodePage({ params }: EpisodePageParams) {
  const episode = await getEpisodeFromCatalog(params.episodeId);

  if (!episode) {
    notFound();
  }

  const publishedDate = episode.pubDate ? new Date(episode.pubDate) : null;
  const dateDisplay =
    publishedDate && !Number.isNaN(publishedDate.valueOf())
      ? new Intl.DateTimeFormat('en-US', {
          year: 'numeric',
          month: 'long',
          day: 'numeric',
        }).format(publishedDate)
      : null;

  return (
    <main className="mx-auto flex w-full max-w-4xl flex-col gap-6 px-4 py-10 lg:px-0">
      <article className="rounded-lg border border-gray-200 bg-white p-6 shadow-sm">
        <header className="flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
          <div>
            <p className="text-sm uppercase tracking-wide text-blue-600">{episode.category}</p>
            <h1 className="text-3xl font-bold text-gray-900">{episode.title}</h1>
            <div className="mt-2 text-sm text-gray-500">
              {dateDisplay && <span>Published {dateDisplay}</span>}
              {episode.duration && (
                <span className={dateDisplay ? 'ml-2' : undefined}>• {episode.duration}</span>
              )}
              {episode.attribution && (
                <span className="ml-2">• Contributor: {episode.attribution}</span>
              )}
            </div>
          </div>
          {episode.thumbnailUrl && (
            <img
              src={episode.thumbnailUrl}
              alt={`${episode.title} artwork`}
              className="h-36 w-36 rounded-lg object-cover shadow-md"
              loading="lazy"
            />
          )}
        </header>

        {episode.audioUrl && (
          <div className="mt-6">
            <audio controls preload="metadata" className="w-full">
              <source src={episode.audioUrl} type="audio/mpeg" />
              Your browser does not support the audio element.
            </audio>
            <div className="mt-2 text-sm text-gray-500">
              <a href={episode.audioUrl} className="text-blue-600 hover:underline">
                Download episode
              </a>
            </div>
          </div>
        )}

        <section
          className="prose prose-blue mt-8 max-w-none"
          dangerouslySetInnerHTML={{ __html: episode.descriptionHtml }}
        />
      </article>
    </main>
  );
}
