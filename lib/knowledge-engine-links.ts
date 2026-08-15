/**
 * Shared outbound-link resolvers for Knowledge Engine cards and citations.
 * Search / Ask / Browse / Map use the same functions so a process, podcast,
 * paper, or video result is a live title whenever a public URL exists.
 */

export const GLMP_VIEWER_BASE =
  'https://storage.googleapis.com/regal-scholar-453620-r7-podcast-storage/glmp-v2/viewer/index.html'

export const PODCAST_EPISODE_BASE = 'https://copernicusai.fyi/episodes'

const GCS_PROCESS_ROOT =
  'https://storage.googleapis.com/regal-scholar-453620-r7-podcast-storage'

/** Family table (always a real page). Used when a per-chart HTML path is unknown. */
export const PROCESS_FAMILY_TABLE_HREF: Record<string, string> = {
  glmp: `${GCS_PROCESS_ROOT}/glmp-v2/glmp-database-table.html`,
  math: `${GCS_PROCESS_ROOT}/mathematics-processes-database/mathematics-database-table.html`,
  biology: `${GCS_PROCESS_ROOT}/biology-processes-database/biology-database-table.html`,
  chemistry: `${GCS_PROCESS_ROOT}/chemistry-processes-database/chemistry-database-table.html`,
  physics: `${GCS_PROCESS_ROOT}/physics-processes-database/physics-database-table.html`,
  computer_science: `${GCS_PROCESS_ROOT}/computer-science-processes-database/computer-science-database-table.html`,
}

/** Per-chart HTML lives under these GCS prefixes (same as the family tables). */
const PROCESS_CHART_GCS_BASE: Record<string, string> = {
  math: `${GCS_PROCESS_ROOT}/mathematics-processes-database`,
  biology: `${GCS_PROCESS_ROOT}/biology-processes-database`,
  chemistry: `${GCS_PROCESS_ROOT}/chemistry-processes-database`,
  physics: `${GCS_PROCESS_ROOT}/physics-processes-database`,
  computer_science: `${GCS_PROCESS_ROOT}/computer-science-processes-database`,
}

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

export function isUsableChartId(id: string | undefined): id is string {
  if (!id || !id.trim()) return false
  return /^[A-Za-z][A-Za-z0-9_.-]*$/.test(id)
}

/** @deprecated use isUsableChartId — kept for existing Map/Browse call sites */
export function isUsableGlmpChartId(id: string | undefined): id is string {
  return isUsableChartId(id)
}

export function isUsablePodcastId(id: string | undefined): id is string {
  if (!id || !id.trim()) return false
  // Firestore job UUIDs are not public episode slugs.
  if (/^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i.test(id)) {
    return false
  }
  return /^[A-Za-z0-9][A-Za-z0-9_.-]*$/.test(id)
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

function firstHttpUrl(...candidates: Array<string | null | undefined>): string | null {
  for (const c of candidates) {
    if (hasText(c) && /^https?:\/\//i.test(c)) return c
  }
  return null
}

function youtubeWatchUrl(id: string): string {
  return `https://www.youtube.com/watch?v=${encodeURIComponent(id)}`
}

export function videoExternalUrl(item: {
  url?: string | null
  youtubeId?: string | null
  id?: string | null
}): string | null {
  const direct = firstHttpUrl(item.url)
  if (direct) return direct
  const yt = item.youtubeId || item.id
  if (hasText(yt) && /^[A-Za-z0-9_-]{11}$/.test(yt)) {
    return youtubeWatchUrl(yt)
  }
  return null
}

export function podcastExternalUrl(item: {
  url?: string | null
  episodeLink?: string | null
  slug?: string | null
  episodeId?: string | null
  jobId?: string | null
  id?: string | null
}): string | null {
  const direct = firstHttpUrl(item.episodeLink, item.url)
  if (direct) return direct
  const episodeId = item.slug || item.episodeId || item.jobId || item.id
  return isUsablePodcastId(episodeId || undefined) ? podcastEpisodeUrl(episodeId!) : null
}

/**
 * Per-chart HTML for non-GLMP families, matching mathematics-database-table.html
 * getProcessUrl() and the other discipline tables. Falls back to the family table.
 */
export function processExternalUrl(item: {
  processFamily?: string | null
  processId?: string | null
  id?: string | null
  subcategory?: string | null
  processType?: string | null
  proofGraphHtml?: string | null
}): string | null {
  const family = item.processFamily || ''
  const chartId = item.processId || item.id
  if (family === 'glmp' && isUsableChartId(chartId || undefined)) {
    return glmpViewerUrl(chartId!)
  }
  const base = PROCESS_CHART_GCS_BASE[family]
  if (base && isUsableChartId(chartId || undefined)) {
    const processType = (item.processType || '').toLowerCase()
    const subcategory = item.subcategory || ''
    if (processType === 'proof_graph' || subcategory === 'proof_graphs') {
      const fname = hasText(item.proofGraphHtml)
        ? item.proofGraphHtml.replace(/^.*\//, '')
        : `${chartId}.html`
      if (isUsableChartId(fname.replace(/\.html$/i, ''))) {
        return `${base}/proof-graphs/${fname}`
      }
    }
    if (hasText(subcategory) && isUsableChartId(subcategory)) {
      return `${base}/processes/${encodeURIComponent(subcategory)}/${encodeURIComponent(chartId!)}.html`
    }
  }
  return PROCESS_FAMILY_TABLE_HREF[family] || null
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
  slug?: string | null
  episodeId?: string | null
  episodeLink?: string | null
  subcategory?: string | null
  processType?: string | null
  proofGraphHtml?: string | null
  youtubeId?: string | null
}): string | null {
  const kind = (item.type || '').toLowerCase()
  if (kind === 'paper') {
    return paperExternalUrl(item)
  }
  if (kind === 'podcast') {
    return podcastExternalUrl(item)
  }
  if (kind === 'video') {
    return videoExternalUrl(item)
  }
  const family = item.processFamily || processFamilyFromRagType(kind)
  if (family || kind === 'process') {
    return processExternalUrl({
      processFamily: family,
      processId: item.processId,
      id: item.id,
      subcategory: item.subcategory,
      processType: item.processType,
      proofGraphHtml: item.proofGraphHtml,
    })
  }
  return null
}
