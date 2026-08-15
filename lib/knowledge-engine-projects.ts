/**
 * Per-project chrome config for the Knowledge Engine frontend (GLMP/ATAP
 * toggle, chrome-first v1 -- see
 * docs/open-questions/knowledge-engine-project-toggle-plan-2026-08-15.md
 * in the glmp repo for the full plan and the decisions behind this scope).
 *
 * v1 is chrome only: framing copy, Quick Examples, and Search placeholder
 * text change with the selected project. Nothing here changes what
 * Search/Ask Questions actually retrieve -- that's a deliberate, separate,
 * not-yet-made decision (scoped retrieval), not an oversight.
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

export type KEProjectId = 'glmp' | 'atap'

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
  fullName: string
  /** Short line shown under the page header when this project is selected. */
  framingLine: string
  /** content_type key the API expects for this project's process family. */
  processContentType: 'glmp' | 'math'
  searchPlaceholder: string
  /**
   * DRAFT example queries, not a final ship list -- per the plan doc, these
   * need Gary/team review before being treated as final. GLMP's three below
   * were tested live against production on 2026-08-15 and are known to
   * return good, on-topic results (see the Knowledge Engine integration
   * assessment doc, same date). ATAP's are carried over unchanged from the
   * original two-example set; nothing new was added for ATAP because it
   * would mean inventing queries for a corpus without live-testing them
   * first -- deliberately left for someone who knows ATAP's corpus.
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

export const KE_PROJECTS: Record<KEProjectId, KEProjectConfig> = {
  glmp: {
    id: 'glmp',
    label: 'GLMP',
    fullName: 'Genome Logic Modeling Project',
    framingLine: "Exploring GLMP's gene-regulation corpus -- the glmp process family and its scoped papers.",
    processContentType: 'glmp',
    searchPlaceholder: 'Try: CRP activation of transcription, lac operon, catabolite repression...',
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
    fullName: 'ATAP (mathematics process graphs)',
    framingLine: "Exploring ATAP's mathematics corpus -- the atap_graphs process family.",
    processContentType: 'math',
    searchPlaceholder: 'Try: nilpotent groups, spectral sequences...',
    quickExamples: [
      {
        label: 'Nilpotent Groups (ATAP)',
        keyword: 'nilpotent group',
        disciplines: { ...NO_DISCIPLINES, mathematics: true },
      },
      {
        label: 'Spectral Sequences (ATAP)',
        keyword: 'spectral sequence',
        disciplines: { ...NO_DISCIPLINES, mathematics: true },
      },
    ],
  },
}

export const KE_PROJECT_IDS: KEProjectId[] = ['glmp', 'atap']

export function isKEProjectId(v: string | null | undefined): v is KEProjectId {
  return v === 'glmp' || v === 'atap'
}
