/**
 * Shared outbound-link resolvers for Knowledge Engine cards and citations.
 * Browse already had this; Search / Ask / Map now use the same functions
 * so a process or podcast result is never an unlinked title.
 */

export const GLMP_VIEWER_BASE =
  'https://storage.googleapis.com/regal-scholar-453620-r7-podcast-storage/glmp-v2/viewer/index.html'

export const PODCAST_EPISODE_BASE = 'https://copernicusai.fyi/episodes'

export function hasText(v: string | null | undefined): v is string {
  if (v == null) return false
  const s = String(v).trim()
  return Boolean(s) && s.toLowerCase() !== 'none' && s.toLowerCase() !== 'null'
}

/** Same priority as papers-database-table.html. */
export function paperExternalUrl(item: {
  doi?: string | null
  pmid?: string | null
  arxiv_id?: string | null
  url?: string | null
}): string | null {
  if (hasText(item.doi)) {
    const doi = item.doi.replace(/^https?:\/\/(dx\.)?doi\.org\//i, '')
    return `https://doi.org/${encodeURI(doi)}`
  }
  if (hasText(item.pmid)) {
    return `https://pubmed.ncbi.nlm.nih.gov/${encodeURIComponent(item.pmid)}`
  }
  if (hasText(item.arxiv_id)) {
    const id = item.arxiv_id.replace(/^arxiv:/i, '')
    return `https://arxiv.org/abs/${encodeURIComponent(id)}`
  }
  if (hasText(item.url) && /^https?:\/\//i.test(item.url)) {
    return item.url
  }
  return null
}

export function isUsableGlmpChartId(id: string | undefined): id is string {
  if (!id || !id.trim()) return false
  return /^[A-Za-z][A-Za-z0-9_.-]*$/.test(id)
}

export function isUsablePodcastId(id: string | undefined): id is string {
  if (!id || !id.trim()) return false
  return /^[A-Za-z][A-Za-z0-9_.-]*$/.test(id)
}

export function glmpViewerUrl(chartId: string): string {
  return `${GLMP_VIEWER_BASE}?process=${encodeURIComponent(chartId)}`
}

export function podcastEpisodeUrl(episodeId: string): string {
  return `${PODCAST_EPISODE_BASE}/${encodeURIComponent(episodeId)}`
}

export function pmidFromNodeId(id: string): string | null {
  const m = id.match(/^pubmed_(.+)$/i)
  return m ? m[1] : null
}

const SEARCH_BUCKET_TO_FAMILY: Record<string, string> = {
  glmp_processes: 'glmp',
  math_processes: 'math',
  chemistry_processes: 'chemistry',
  physics_processes: 'physics',
  computer_science_processes: 'computer_science',
  biology_processes: 'biology',
}

export function processFamilyFromSearchBucket(bucket: string): string | null {
  return SEARCH_BUCKET_TO_FAMILY[bucket] ?? null
}

const RAG_TYPE_TO_FAMILY: Record<string, string> = {
  glmp_process: 'glmp',
  math_process: 'math',
  chemistry_process: 'chemistry',
  physics_process: 'physics',
  computer_science_process: 'computer_science',
  biology_process: 'biology',
}

export function processFamilyFromRagType(type: string): string | null {
  return RAG_TYPE_TO_FAMILY[type] ?? null
}

export function hrefForKnowledgeItem(item: {
  type: string
  id?: string | null
  doi?: string | null
  pmid?: string | null
  arxiv_id?: string | null
  url?: string | null
  processFamily?: string | null
  jobId?: string | null
  processId?: string | null
}): string | null {
  const kind = (item.type || '').toLowerCase()
  if (kind === 'paper') {
    return paperExternalUrl(item)
  }
  if (kind === 'podcast') {
    const episodeId = item.jobId || item.id
    return isUsablePodcastId(episodeId || undefined) ? podcastEpisodeUrl(episodeId!) : null
  }
  const family = item.processFamily || processFamilyFromRagType(kind)
  const chartId = item.processId || item.id
  if (family === 'glmp' && isUsableGlmpChartId(chartId || undefined)) {
    return glmpViewerUrl(chartId!)
  }
  return null
}
