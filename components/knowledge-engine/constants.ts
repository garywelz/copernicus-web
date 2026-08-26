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

/** Declared research questions for Browse (catalog slice, not vector search). */
export const BROWSE_QUESTIONS = [
  { id: 'glmp-q1', label: 'GLMP q1 · CRP/CAP sites' },
  { id: 'glmp-q2', label: 'GLMP q2 · PWM evidence' },
  { id: 'glmp-q3', label: 'GLMP q3 · Network motifs' },
  { id: 'glmp-q4', label: 'GLMP q4 · Bistable switches' },
  { id: 'glmp-q5', label: 'GLMP q5 · Synthetic circuits' },
  { id: 'glmp-q6', label: 'GLMP q6 · Stress regulons' },
  { id: 'glmp-q7', label: 'GLMP q7 · Two-component' },
  { id: 'glmp-q8', label: 'GLMP q8 · Catabolite repression' },
  { id: 'glmp-q9', label: 'GLMP q9 · Cell fate' },
  { id: 'glmp-q10', label: 'GLMP q10 · Network inference' },
  { id: 'glmp-q11', label: 'GLMP q11 · CRP methods' },
  { id: 'atap-q1', label: 'ATAP q1 · Proof objects' },
  { id: 'atap-q2', label: 'ATAP q2 · Algorithm capsules' },
  { id: 'atap-q3', label: 'ATAP q3 · Graph similarity' },
  { id: 'atap-q4', label: 'ATAP q4 · Formal methods in biology' },
] as const

export function browseQuestionLabel(id: string): string {
  return BROWSE_QUESTIONS.find((q) => q.id === id)?.label || id
}

export const PROCESS_DATABASE_LINKS = [
  { key: 'glmp_v2', label: 'GLMP', href: 'https://storage.googleapis.com/regal-scholar-453620-r7-podcast-storage/glmp-database-table.html' },
  { key: 'mathematics', label: 'ATAP', href: 'https://storage.googleapis.com/regal-scholar-453620-r7-podcast-storage/mathematics-processes-database/mathematics-database-table.html' },
  { key: 'biology', label: 'Biology', href: 'https://storage.googleapis.com/regal-scholar-453620-r7-podcast-storage/biology-processes-database/biology-database-table.html' },
  { key: 'chemistry', label: 'Chemistry', href: 'https://storage.googleapis.com/regal-scholar-453620-r7-podcast-storage/chemistry-processes-database/chemistry-database-table.html' },
  { key: 'physics', label: 'Physics', href: 'https://storage.googleapis.com/regal-scholar-453620-r7-podcast-storage/physics-processes-database/physics-database-table.html' },
  { key: 'computer_science', label: 'Computer Science', href: 'https://storage.googleapis.com/regal-scholar-453620-r7-podcast-storage/computer-science-processes-database/computer-science-database-table.html' },
] as const

/** Public papers table (GCS); same family as PROCESS_DATABASE_LINKS. */
export const PAPERS_DATABASE_TABLE_HREF =
  'https://storage.googleapis.com/regal-scholar-453620-r7-podcast-storage/papers-database-table.html'

export const VIDEOS_DATABASE_TABLE_HREF =
  'https://storage.googleapis.com/regal-scholar-453620-r7-podcast-storage/videos-database-table.html'
