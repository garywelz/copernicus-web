/**
 * Per-project chrome config for the Knowledge Engine frontend (GLMP/ATAP
 * toggle, chrome-first v1 -- see
 * docs/open-questions/knowledge-engine-project-toggle-plan-2026-08-15.md
 * in the glmp repo for the full plan and the decisions behind this scope).
 *
 * **Updated 2026-10-04 (architecture review Phase 2, gap 1):** v1 was
 * chrome only -- framing copy, Quick Examples, and Search placeholder
 * text, with nothing here changing what Search/Ask Questions actually
 * retrieved. That's no longer true. Browse, Search, and Ask Questions now
 * send the selected project as an `engine` param (backend: PRs #32/#33),
 * which strictly scopes paper retrieval to that engine's tagged papers.
 * "All projects" (project === null) still sends no `engine` param at
 * all -- fully unscoped, exactly as before. The Knowledge Map is the one
 * tab still unscoped in this release (see KnowledgeMapView.tsx's own
 * note to the user when a project is selected there).
 *
 * IMPORTANT: GLMP is not "the biology discipline" and ATAP is not "the
 * mathematics discipline" -- see the plan doc's correction on this. GLMP's
 * actual identity is the `glmp` process family + question_scope_ids-scoped
 * papers; ATAP's is `content_type=math` / the `atap_graphs` collection.
 * Individual example-query filters below still use `disciplines` (a valid
 * filter for paper search specifically), but that is not the same claim as
 * "GLMP == biology" -- do not use disciplines to define project identity
 * anywhere else in this codebase.
 */

export type KEProjectId = 'glmp' | 'atap' | 'tdap'

export interface KEQuickExample {
  label: string
  keyword: string
  disciplines: {
    biology: boolean
    chemistry: boolean
    physics: boolean
    mathematics: boolean
    computer_science: boolean
    interdisciplinary: boolean
  }
}

export interface KEProjectConfig {
  id: KEProjectId
  label: string
  /** Emoji shown next to the project label (Quick Examples list, etc.) --
   *  config-driven so a 3rd+ project doesn't need a per-component ternary
   *  that silently falls through (see KnowledgeMapView.tsx's Quick Examples
   *  header, fixed 2026-09-19 for TDAP). */
  icon: string
  fullName: string
  /** Short line shown under the page header when this project is selected. */
  framingLine: string
  /** content_type key the API expects for this project's process family.
   *  null when the project has no process/chart family yet -- TDAP v1 is
   *  metadata-first with no chart family (decision 2026-09-19: charts are
   *  a deliberately format-agnostic bucket to be filled later, not
   *  Mermaid-specific like GLMP/ATAP's). */
  processContentType: 'glmp' | 'math' | null
  searchPlaceholder: string
  /** Example questions for the Ask tab (same topics as quickExamples). */
  askExamples: string[]
  /**
   * Example queries. GLMP's three were tested live 2026-08-15 (KE
   * integration assessment). ATAP's three were re-chosen the same day
   * after Gary named the actual audience (axiomatic theories, algorithms,
   * proofs — not general mathematics): each keyword was live-tested
   * against /api/vector-search/semantic and returned cited_project=atap
   * papers on the matching declared question (atap-q1 or atap-q2).
   */
  quickExamples: KEQuickExample[]
}

const NO_DISCIPLINES = {
  biology: false,
  chemistry: false,
  physics: false,
  mathematics: false,
  computer_science: false,
  interdisciplinary: false,
}

/** ATAP papers sit in math.LO and cs.LO/cs.PL/cs.DM — mathematics-only
 *  filters drop the proof-theory hits (discipline=computer_science). */
const ATAP_DISCIPLINES = {
  ...NO_DISCIPLINES,
  mathematics: true,
  computer_science: true,
}

/** TDAP papers sit in math.AT/cs.CG/stat.ML/math.DS -- same shape as
 *  ATAP_DISCIPLINES above, mathematics+CS, not a life-science filter. */
const TDAP_DISCIPLINES = {
  ...NO_DISCIPLINES,
  mathematics: true,
  computer_science: true,
}

export const KE_PROJECTS: Record<KEProjectId, KEProjectConfig> = {
  glmp: {
    id: 'glmp',
    label: 'GLMP',
    icon: '🧬',
    fullName: 'Genome Logic Modeling Project',
    framingLine: "Exploring GLMP's gene-regulation corpus -- the glmp process family and its scoped papers.",
    processContentType: 'glmp',
    searchPlaceholder: 'Try: CRP activation of transcription, lac operon, catabolite repression...',
    askExamples: [
      'How does CRP activate transcription at Class I promoters?',
      'How is the lac operon regulated in Escherichia coli?',
      'What is catabolite repression and what role does the cAMP receptor protein play?',
    ],
    quickExamples: [
      {
        label: 'CRP Activation (GLMP)',
        keyword: 'CRP activation of transcription',
        disciplines: { ...NO_DISCIPLINES, biology: true },
      },
      {
        label: 'Lac Operon (GLMP)',
        keyword: 'lac operon regulation Escherichia coli',
        disciplines: { ...NO_DISCIPLINES, biology: true },
      },
      {
        label: 'Catabolite Repression (GLMP)',
        keyword: 'catabolite repression cAMP receptor protein',
        disciplines: { ...NO_DISCIPLINES, biology: true },
      },
    ],
  },
  atap: {
    id: 'atap',
    label: 'ATAP',
    icon: '📐',
    fullName: 'Axiomatic Theories, Algorithms and Proofs',
    framingLine:
      'Axiomatic Theories, Algorithms and Proofs — for logicians, foundations researchers, proof theorists, and theoretical computer scientists.',
    processContentType: 'math',
    searchPlaceholder: 'Try: proof nets, Gödel incompleteness, Curry-Howard...',
    askExamples: [
      'What are proof nets, and how do they relate to natural deduction?',
      'What does Gödel\'s incompleteness theorem say, and why does it matter for foundations?',
      'What is the Curry-Howard correspondence between proofs and programs?',
    ],
    quickExamples: [
      {
        label: 'Proof Nets (ATAP)',
        keyword: 'proof nets natural deduction',
        disciplines: ATAP_DISCIPLINES,
      },
      {
        label: 'Gödel Incompleteness (ATAP)',
        keyword: 'Gödel incompleteness independence',
        disciplines: ATAP_DISCIPLINES,
      },
      {
        label: 'Curry-Howard (ATAP)',
        keyword: 'Curry-Howard correspondence proof assistant',
        disciplines: ATAP_DISCIPLINES,
      },
    ],
  },
  tdap: {
    id: 'tdap',
    label: 'TDAP',
    icon: '🍩',
    fullName: 'Topological Data Analysis Project',
    framingLine:
      "Exploring TDAP's persistent cohomology and circular-coordinate corpus -- a new, seed-driven engine, still small.",
    processContentType: null,
    searchPlaceholder: 'Try: persistent cohomology, circular coordinates, computing persistent homology...',
    askExamples: [
      'How does persistent cohomology recover circular and toroidal coordinates from data?',
      'What algorithms compute persistent (co)homology at scale, and what are the tradeoffs?',
      'Where has cyclic or recurrent structure been found in biomedical or physiological data using these methods?',
    ],
    // NOT live-tested against /api/vector-search/semantic like GLMP/ATAP's
    // above -- there is no TDAP corpus yet (2026-09-19: citation-expansion
    // dry run only, zero papers written). Re-test once real data exists.
    quickExamples: [
      {
        label: 'Circular Coordinates (TDAP)',
        keyword: 'circular coordinates persistent cohomology',
        disciplines: TDAP_DISCIPLINES,
      },
      {
        label: 'Persistent Homology Algorithms (TDAP)',
        keyword: 'computing persistent homology algorithm',
        disciplines: TDAP_DISCIPLINES,
      },
      {
        label: 'Toroidal Coordinates (TDAP)',
        keyword: 'toroidal coordinates lattice reduction',
        disciplines: TDAP_DISCIPLINES,
      },
    ],
  },
}

export const KE_PROJECT_IDS: KEProjectId[] = ['glmp', 'atap', 'tdap']

export function isKEProjectId(v: string | null | undefined): v is KEProjectId {
  return v === 'glmp' || v === 'atap' || v === 'tdap'
}

/** `engine` query param for Browse/Search/Ask Questions (architecture
 *  review Phase 2, gap 1, 2026-10-04). Returns the project id itself, or
 *  undefined for "All projects" -- send no `engine` param at all in that
 *  case, not an empty string; the backend treats a present-but-empty
 *  value as "not set" too (config.engine_registry.resolve_engine_tags_or_400),
 *  but omitting it entirely is the clearer contract from this side. */
export function engineParamForProject(project: KEProjectId | null): string | undefined {
  return project ?? undefined
}

/** Human-readable scope label for the "Searching ___" indicator shown on
 *  Browse, Search, and Ask Questions. */
export function scopeLabelForProject(project: KEProjectId | null): string {
  if (!project) return 'all projects'
  return `${KE_PROJECTS[project].label} papers`
}

/** Search/RAG content_types for the current toggle. Project view scopes
 *  processes to that project's family only. Papers are now scoped too,
 *  via the `engine` param built by engineParamForProject() above -- not
 *  by narrowing content_types, since "papers" stays in this list either
 *  way; the engine param is what actually restricts which papers. */
export function searchContentTypesForProject(
  project: KEProjectId | null,
  selected: { papers: boolean; podcasts: boolean; processes: boolean; videos?: boolean },
): string[] {
  const types: string[] = []
  if (selected.papers) types.push('papers')
  if (selected.podcasts) types.push('podcasts')
  if (selected.videos) types.push('videos')
  if (selected.processes) {
    if (project) {
      const pct = KE_PROJECTS[project].processContentType
      if (pct) types.push(pct)
    } else {
      types.push('glmp', 'math', 'chemistry', 'physics', 'computer_science', 'biology')
    }
  }
  return types
}
