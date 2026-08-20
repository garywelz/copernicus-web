# Handoff — 20 August 2026 (synthesis-paper status, not item 26/33/59)

**From:** Claude Code (this session)
**To:** Cursor and Claude Chat
**Repo:** `glmp` @ `d66e098` (`origin/main`)
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

## Not done / not decided

- Did not read Papers I/II/III's actual content — flagging as unread, not vouching for their state.
- No decision made on whether/when to actually submit to bioRxiv, or whether the E. coli decoder
  work should eventually become its own paper or fold into this one via §11's cross-species item.
  Gary's call.

---

## Key paths

- `glmp/collaborations/krampis-virtual-cell/synthesis_genomic_logic.md` — current synthesis draft
- `glmp/collaborations/krampis-virtual-cell/synthesis-biorxiv.md` — retired, now a pointer
- `glmp/collaborations/krampis-virtual-cell/paper-I-foundational-typology.md`
- `glmp/collaborations/krampis-virtual-cell/paper-II-genome-as-computer.md`
- `glmp/collaborations/krampis-virtual-cell/paper-III-empirical-sequel.md`
