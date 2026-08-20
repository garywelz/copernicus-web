# Handoff — 20 August 2026 (synthesis-paper status, not item 26/33/59)

**From:** Claude Code (this session)
**To:** Cursor and Claude Chat
**Repo:** `glmp` @ `1edee4a` (`origin/main`)
**Regenerate from a fresh fetch before acting.**

Share this file as-is. Separate thread from the day's item #26/#33/#59 work (see the other 2026-08-20
handoff, `claude_code_handoff_2026-08-20_item59_validation.md`) — this one is about the K562/
virtual-cell "synthesis for biologists" paper, not the E. coli decoder.

---

## What happened

Gary asked for a read on where GLMP stands toward a publishable paper, pointing at
`collaborations/krampis-virtual-cell/synthesis-biorxiv.md` on GitHub as the doc he's been sharing.

Checking it directly turned up a real problem, not just a status question: **that file's links to
Papers I/II/III pointed at filenames that don't exist in the repo**
(`primitive-relations-genomic-computational-class.md`, `genome-as-computer.md`,
`circuit-class-predicts-virtual-cell-model-accuracy.md`) — the real files are
`paper-I-foundational-typology.md`, `paper-II-genome-as-computer.md`,
`paper-III-empirical-sequel.md`. Every companion-paper link was dead.

Further check found a second file, `synthesis_genomic_logic.md` — same title/abstract, larger
(52KB vs. 46KB), correctly linked to the real paper filenames, and with real additional content the
other version lacks: a section tying GLMP's typology to Arc Institute's Evo 2 (published *Nature*
2026) as an interpretability lens for frontier genomic foundation models. Footer dates: the retired
file said "not peer-reviewed · April 2026"; the current one says "Working draft — not yet
submitted · July 2026." So the file linked from GitHub was the stale one; the better, current one
was sitting under a name nothing pointed to.

## What I did

Gary confirmed: retire `synthesis-biorxiv.md` in favor of `synthesis_genomic_logic.md`. Replaced
`synthesis-biorxiv.md`'s content with a short retirement notice pointing to the current file, rather
than deleting it — the existing GitHub URL people may have bookmarked still resolves, it just now
redirects instead of showing stale content with broken links. `synthesis_genomic_logic.md` itself
was not touched. Committed and pushed (`glmp@d66e098`).

## What I found, worth flagging beyond the immediate fix

- **Papers I/II/III themselves are untouched since 2026-06-12** — over two months dormant as of
  today. Have not read their content this session; only confirmed they exist and haven't moved.
  Whether they're actually complete or mid-draft, someone should check before treating the paper
  stack as submission-ready.
- **Today's E. coli decoder work (items 26/33/59) is not part of either synthesis draft.** It only
  shows up as an aspirational future item ("cross-species bacterial tests," §11) in both versions.
  It also isn't ready to fold in yet even if someone wanted to — lac's Class II call is still
  PROVISIONAL pending Lents, and item 59's validation numbers only stabilized today after two rounds
  of correction. Nothing from today is citable-as-settled in a paper yet.
- **On its own terms, the synthesis content is a real, specific, falsifiable result** (780 K562
  Replogle genes, 16 model evaluations, t = −3.55, p = 0.0015) — genuinely postable as a preprint.
  Its own Limitations/Recommended-experiments sections are honest that real validation work remains
  (multi-line replication, expert-adjudicated gold-standard subset, single-cell attractor assays) —
  normal for a bioRxiv preprint, but worth being clear-eyed that "postable" and "review-proof" are
  different bars.

## Not done / not decided (as of the original post above)

- Did not read Papers I/II/III's actual content — flagging as unread, not vouching for their state.
- No decision made on whether/when to actually submit to bioRxiv, or whether the E. coli decoder
  work should eventually become its own paper or fold into this one via §11's cross-species item.
  Gary's call.

---

## Follow-up, same day: Papers I/II/III read; three fixes applied; one premise corrected

Gary asked for a full read of Papers I/II/III plus a review of the methods paper
(`methods-mermaid-perturbation-design.md`), which he initially framed as "the paper most likely to
be postable."

**Read all three papers in full.** Paper III (the empirical K562 piece) is the strongest — genuinely
rigorous: it reports a robustness test that killed its own signal (expanding Class III 14→22 genes
abolished the effect), then correctly diagnoses why (persistent vs. transient bistability), and
reports two hypotheses (H4, H5) as **not supported** with honest explanations rather than hand-waving.
Papers I/II are explicit about their own status — "motivated hypothesis," not a theorem, a 7-rung
epistemic ladder with "none of these proofs exist yet" stated plainly.

**Three fixes applied and pushed (`glmp@1edee4a`):**
1. The exact same broken-link bug found in the retired `synthesis-biorxiv.md` exists **inside Papers
   II and III themselves** — 9 instances, both pointing at pre-rename filenames for each other. Also
   found the same bug a third place: `synthesis_genomic_logic.md` (the current canonical synthesis
   draft) still linked to the methods paper's *pre-rename* filename
   (`mermaid-flowcharts-smarter-perturbation-design.md` instead of
   `methods-mermaid-perturbation-design.md`). All 10 instances fixed.
2. Verified Paper III's Data and Code Availability section against the actual repo — every cited
   file (`gene_circuit_classes.tsv`, all 7 scripts in `k562-empirical-sequel/scripts/`, all 5 cited
   `results/*.tsv` files) genuinely exists. No changes needed; reproducibility claims check out.
3. Paper I's "108-graph sample" was stale (8 instances). Verified the live corpus directly
   (`glmp-v2/processes/**/*.json` = **220**, not the 217 from the 2026-08-04 loop-audit) and updated
   all 8 instances to 220.

**The methods paper's premise needed correcting, not just reviewing.** It's not an unposted draft —
it's **already live on Zenodo**, v1.6, 2026-06-28, DOI `10.5281/zenodo.20831780`. More load-bearing:
per `glmp-collaboration-plan-2026.md` (last touched 2026-06-29, so ~7 weeks stale itself), **bioRxiv
declined it outright as a methods-only submission** — "they accept research articles only." It can't
be the bioRxiv posting regardless of quality; that door is structurally closed. The plan's own
candidate for the next bioRxiv submission is a **different, not-yet-written paper: the RPE1
replication study (Priority 1 in the collaboration plan)** — testing whether the Class III effect
replicates outside K562, ~1–2 months out, joint task with Krampis. Gary confirmed he does not want
the GitHub `methods-mermaid-perturbation-design.md` re-edited right now — the README already flags
it as "under active revision," and editing it risks drifting from what's archived at the Zenodo DOI.
Left untouched.

**Class I–V rename — confirmed real, still nowhere implemented, deliberately parked.**
`glmp-note-for-hunter.md` (2026-07-20, untracked in git, not yet committed): *"'Class I–V' collided
with an existing promoter-architecture usage — inverted, for lac. Now retired."* Cross-checked
against `GLMP_MASTER_TODO.md`'s own resolution (same collision, item 33/glmp-f1 area): the retirement
applies to the Papers I–III complexity-ladder typology specifically, **not** to the decoder's own
real-biology "lac Class II" usage (item 26's CRP promoter architecture), which stays as-is. But nine
weeks later, none of it has actually been renamed anywhere — not Papers I/II/III's core typology, not
`flowchart-circuit-classes.tsv`'s `class (I–V)` column, and the collaboration plan's own "Class
IIIa/IIIb" language (Priorities 3–4) predates the July 20 retirement note, so it's stale on this
point too. Gary's explicit call: **do nothing on this yet — wait for Lents to propose the actual
replacement term** before any rename, rather than guessing (Gary's own tentative memory, "tiers,"
already means something else in `glmp-note-for-hunter.md` — a 3-way epistemic distinction, not the
5-level ladder — so reusing it would create a second collision, not fix the first one).

## Not done / not decided (current)

- Class I–V rename: intentionally not started. Needs Lents' proposed replacement term first.
- Whether the GitHub `methods-mermaid-perturbation-design.md` draft ever gets reconciled with the
  archived Zenodo v1.6, and when — not decided, not urgent per Gary.
- Whether/when the RPE1 replication paper (the actual next bioRxiv candidate) gets started — that's
  Priority 1 in the collaboration plan, joint with Krampis, not something to begin unprompted.

---

## Key paths

- `glmp/collaborations/krampis-virtual-cell/synthesis_genomic_logic.md` — current synthesis draft
- `glmp/collaborations/krampis-virtual-cell/synthesis-biorxiv.md` — retired, now a pointer
- `glmp/collaborations/krampis-virtual-cell/paper-I-foundational-typology.md`
- `glmp/collaborations/krampis-virtual-cell/paper-II-genome-as-computer.md`
- `glmp/collaborations/krampis-virtual-cell/paper-III-empirical-sequel.md`
- `glmp/collaborations/krampis-virtual-cell/methods-mermaid-perturbation-design.md` — GitHub working
  copy; do not treat as identical to the archived Zenodo v1.6
- `glmp/collaborations/krampis-virtual-cell/glmp-collaboration-plan-2026.md` — paper trajectory,
  ~7 weeks stale, worth a fresh-eyes re-read before trusting its near-term priorities as current
- `glmp/collaborations/krampis-virtual-cell/glmp-note-for-hunter.md` — untracked, not yet committed;
  source of the Class I–V retirement note
