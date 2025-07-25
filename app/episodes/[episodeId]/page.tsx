import { notFound } from 'next/navigation';

// Fetch episode data from API using slug
async function fetchEpisodeBySlug(slug: string) {
  const res = await fetch('/api/spotify');
  if (!res.ok) throw new Error('Failed to fetch podcast data');
  const data = await res.json();
  const episode = data.episodes.find((ep: any) => ep.slug === slug);
  return episode;
}

export default async function EpisodePage({ params }: { params: { episodeId: string } }) {
  const episode = await fetchEpisodeBySlug(params.episodeId);
  if (!episode) return notFound();
  return (
    <main className="max-w-2xl mx-auto py-10 px-4">
      <h1 className="text-3xl font-bold mb-4">{episode.title}</h1>
      <audio controls src={episode.audio_url} className="w-full mb-4" />
      <img src={episode.thumbnail_url} alt={episode.title + ' artwork'} className="mb-4 rounded-lg" style={{ maxWidth: 400 }} />
      <div className="prose" dangerouslySetInnerHTML={{ __html: episode.description }} />
      <p className="mt-6 text-gray-500 text-sm">Published: {episode.published_at}</p>
    </main>
  );
}
