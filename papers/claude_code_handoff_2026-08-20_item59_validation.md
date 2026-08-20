# Handoff — 20 August 2026 (item #59 — GLMP validation, computation track)

**From:** Claude Code (this session)
**To:** Cursor and Claude Chat
**Repo:** `glmp` @ `9cc9b1d` (`origin/main`)
**Regenerate from a fresh fetch before acting.**

Share this file as-is.

**Closed out, 2026-08-20.** Claude Chat independently verified the corrected numbers directly
against the live files (thresholds in `custom_pwm_registry.yaml`, trp q-values and window
coordinates in the revised report, precision/recall arithmetic) — all confirmed accurate. Chat also
caught one remaining stale line: `GLMP_MASTER_TODO.md` item 59 still said the Lents draft's item-3
paragraph revision was undecided, when it had already been rewritten. Fixed and pushed
(`glmp@9cc9b1d`). Nothing outstanding on item 59 as of this commit.

**Superseded, same day:** the "Bottom line" and Cursor-flags sections below reflect the first-pass
analysis. Cursor caught a real bug in it (a single p ≤ 0.0001 threshold applied to all three motifs;
the decoder's real per-motif locks are LacI 1e-5, CRP 1e-4, **TrpR 0.05**) and confirmed two of the
"findings" below were already documented in the 2026-07-08 B1 notebook, not new. Corrected numbers
and framing: `GLMP_MASTER_TODO.md` item 59 and the revised report, both updated in place. Trp's
picture changed materially (10 false positives at its real threshold, driven by a window that
doesn't reach `trpLp`, not by PWM quality) — do not quote this file's "5/5, 100% precision" line
below as current.

---

## What happened

The GLMP validation package (`.../validation/index.html`) assigned the computation track
(RegulonDB cross-reference for lac/ara/trp) to Prof. Krampis's student assistant. No response after
an extended period. Gary asked whether this was something he could do himself; confirmed yes — it's
purely computational, every input file was already staged locally, and it requires no biological
judgment (that's the separate, still-open biology track). Gary said go; I ran it.

**Full detail:** `glmp/docs/GLMP_MASTER_TODO.md` item 59. Full report:
`glmp/collaborations/krampis-virtual-cell/dna-decoder/docs/crp_lac_ara_trp_regulondb_validation_report.md`.
Script + raw output: `glmp/collaborations/krampis-virtual-cell/dna-decoder/scripts/regulondb_crossref_analysis.py`
/ `regulondb_crossref_results.json`.

## Bottom line

At the decoder's own locked threshold (p ≤ 0.0001), across lac + ara: **5 predictions, all 5 correct
by sequence identity, 0 false positives, precision 100%.** Trp made zero threshold-passing
predictions. This is a clean result for what the decoder actually predicts — the discrepancies below
are about how two of the three decode files report *coordinates*, not about wrong predictions.

## For Cursor — two decoder-pipeline findings, not fixed here on purpose

I did not touch `crp_cap.meme`, rebuild anything, or attempt a fix — out of scope per this session's
own standing constraint (same one from the item #26 handoff: I don't build/rebuild/re-decode a PWM
or touch decoder internals). Flagging both for whoever owns the decode pipeline:

1. **Lac coordinate-frame mismatch.** `ecoli_lac_operon_logic_20260708.json`'s 4 threshold-passing
   predictions have exactly correct DNA sequences (verified against RegulonDB's `tfrsSeq`) but
   genomic coordinates that don't match RegulonDB's true `NC_000913.3` positions for those same
   sequences. Not a simple constant offset — 636 bp / 677 bp / 820 bp across three sites — and the
   direction is inverted relative to RegulonDB (decoder positions increase where RegulonDB's
   decrease), though the internal spacing between sites matches exactly in both systems (20 bp,
   72 bp). Worth checking whether this traces to how the file's scan window/coordinates were
   assembled.
2. **Trp window miss.** `ecoli_trp_operon_logic_20260708.json`'s scanned window
   (1319737–1320275) entirely misses RegulonDB's real `trpLp` TrpR sites (1323103–1323136), ~3.4 kb
   away. Separately, all 10 raw TrpR FIMO hits fail the locked threshold by a wide margin (best
   p = 0.001) — worth a look at the TrpR motif/PWM independent of the window issue.
3. Smaller: a real Confirmed LacI site (365922–365942) sits outside the lac file's scanned window
   entirely — never scanned, not mis-anchored. Possible case for widening the lac scan window
   upstream of `lacZp1`.

Ara's decode file has none of these problems — matched RegulonDB exactly, by both position and
sequence, no fix needed there.

None of this is urgent from my side; it's a report for whoever picks it up next, not a live
blocker.

## For Claude Chat — how this touches #26

This is a separate, parallel track from #26 (CRP PWM sign-off) — the validation package's own README
says the two tracks are non-redundant by design, and I confirmed that reasoning with Gary before
running this. It doesn't resolve or replace anything in the A/B/C/D decision on #26. It's additional,
independently-generated evidence that the CRP PWM's threshold-passing predictions for lac/ara are
sequence-correct, which may be useful context if it comes up in the Lents conversation, but it's not
a substitute for Lents' three-checkbox sign-off. Your call whether/how to bring it into that
conversation — not deciding that here.

Also note: the biology track (annotation review, Class II question, quantitative values) is still
open and unaddressed — this item only covers the computation track. Someone with biology judgment
still needs to do that half.

## Not done / explicitly left open

- Report has not been sent to Krampis/Lents or anywhere external — sitting in the repo for Gary to
  review first.
- No decision made on whether the coordinate-frame findings become their own tracked item or fold
  into an existing one — Gary's/your call.

---

## Key paths

- `glmp/docs/GLMP_MASTER_TODO.md` — item 59
- `glmp/collaborations/krampis-virtual-cell/dna-decoder/docs/crp_lac_ara_trp_regulondb_validation_report.md`
- `glmp/collaborations/krampis-virtual-cell/dna-decoder/scripts/regulondb_crossref_analysis.py`
- `glmp/collaborations/krampis-virtual-cell/dna-decoder/scripts/regulondb_crossref_results.json`
