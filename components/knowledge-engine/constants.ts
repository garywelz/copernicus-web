/** Shared config for Knowledge Engine UI */

export const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_URL || 'https://copernicus-podcast-api-phzp4ie2sq-uc.a.run.app'

export const GCS_STATUS_URL =
  'https://storage.googleapis.com/regal-scholar-453620-r7-podcast-storage/knowledge-engine-status.json'

/** Content types passed to /api/vector-search/semantic and /api/rag/answer */
export const ALL_PROCESS_CONTENT_TYPES = [
  'glmp',
  'math',
  'chemistry',
  'physics',
  'computer_science',
  'biology',
] as const

export const DEFAULT_SEARCH_CONTENT_TYPES = [
  'papers',
  'podcasts',
  ...ALL_PROCESS_CONTENT_TYPES,
] as const

/** Process-chart families. `math` is ATAP (atap_graphs), not general mathematics.
 *  Biology is its own family, distinct from GLMP. There is no separate
 *  non-ATAP mathematics *process* collection yet — mathematics papers are
 *  a paper-discipline family (PAPER_DISCIPLINES), same shape as biology
 *  papers vs GLMP charts. */
export const PROCESS_FAMILIES = [
  { id: 'glmp', label: 'GLMP', statusKey: 'glmp_v2' },
  { id: 'math', label: 'ATAP', statusKey: 'mathematics' },
  { id: 'biology', label: 'Biology', statusKey: 'biology' },
  { id: 'chemistry', label: 'Chemistry', statusKey: 'chemistry' },
  { id: 'physics', label: 'Physics', statusKey: 'physics' },
  { id: 'computer_science', label: 'Computer Science', statusKey: 'computer_science' },
] as const

/** Paper-discipline families. Mathematics lives here, not under ATAP. */
export const PAPER_DISCIPLINES = [
  { id: 'biology', label: 'Biology' },
  { id: 'mathematics', label: 'Mathematics' },
  { id: 'chemistry', label: 'Chemistry' },
  { id: 'physics', label: 'Physics' },
  { id: 'computer_science', label: 'Computer Science' },
  { id: 'interdisciplinary', label: 'Interdisciplinary' },
] as const

export const PROCESS_DATABASE_LINKS = [
  { key: 'glmp_v2', label: 'GLMP', href: 'https://storage.googleapis.com/regal-scholar-453620-r7-podcast-storage/glmp-v2/glmp-database-table.html' },
  { key: 'mathematics', label: 'ATAP', href: 'https://storage.googleapis.com/regal-scholar-453620-r7-podcast-storage/mathematics-processes-database/mathematics-database-table.html' },
  { key: 'biology', label: 'Biology', href: 'https://storage.googleapis.com/regal-scholar-453620-r7-podcast-storage/biology-processes-database/biology-database-table.html' },
  { key: 'chemistry', label: 'Chemistry', href: 'https://storage.googleapis.com/regal-scholar-453620-r7-podcast-storage/chemistry-processes-database/chemistry-database-table.html' },
  { key: 'physics', label: 'Physics', href: 'https://storage.googleapis.com/regal-scholar-453620-r7-podcast-storage/physics-processes-database/physics-database-table.html' },
  { key: 'computer_science', label: 'Computer Science', href: 'https://storage.googleapis.com/regal-scholar-453620-r7-podcast-storage/computer-science-processes-database/computer-science-database-table.html' },
] as const

/** Public papers table (GCS); same family as PROCESS_DATABASE_LINKS. */
export const PAPERS_DATABASE_TABLE_HREF =
  'https://storage.googleapis.com/regal-scholar-453620-r7-podcast-storage/papers-database-table.html'
