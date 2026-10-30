# Curated episodes: the publish-day status re-check

**What it is for.** An episode made from a curated source list says things about OpenAI's `openai/math` manuscripts: that a manuscript has a Lean formalization, that it was withdrawn, that it is unverified. Those statuses were read from the repository at a pinned commit when the list was approved (design `docs/design/CURATED_SOURCES_MODE.md` §4). The repository moves. A manuscript can be withdrawn, or gain or lose a formalization entry, between the day the episode was made and the day it is published. **A withdrawn paper must never be presented as standing**, so this check runs, by hand, immediately before an episode is published.

**Who runs it, and when.** The Core-lane agent, attended, on the day Gary approves publication and **before** the publish call (`POST /api/subscribers/podcasts/submit-to-rss` with the admin key, after the feed backup that rule 16 requires). It is not scheduled and nothing triggers it.

## The command

```
cd cloud-run-backend
python scripts/recheck_curated_statuses.py <list_id>                 # against the current head of openai/math
python scripts/recheck_curated_statuses.py <list_id> --head <40-character commit>
python scripts/recheck_curated_statuses.py <list_id> --json
```

The list id is on the episode's job record (`curated_list_id`) and in `curated_run.list_id`. It needs your own Google credentials (it reads the list from Firestore) and network access to GitHub. **It writes nothing, anywhere.**

## What it does

1. Reads the approved list.
2. Asks GitHub for the current head of the repository's default branch.
3. For every company-release manuscript in the list, recomputes its status **at that head**: withdrawn (its README is a withdrawal notice), has a Lean formalization (its directory is a `sources:` entry of `lean/formalization.yaml`), or unverified. Withdrawn beats the other two.
4. Compares each with the status recorded in the list, and also flags a manuscript whose file changed since the pinned commit, one that is no longer in the manuscript map, and a withdrawn one that has come back into it.

It does **not** re-check registry sources (arXiv, PubMed, Crossref), and it cannot tell whether a `checked_by_experts` statement made by a cited commentary source is still true; read those sources again by hand if an episode relies on one.

## Reading the result

| Exit code | Meaning | What to do |
|---|---|---|
| 0 | Nothing changed. | Publication may go ahead. |
| 2 | Something changed. The output says **DO NOT PUBLISH**. | Do not publish. Show the table to Gary. The episode is regenerated from a list pinned at the new head, or published only after Gary decides how to treat the change. |
| 3 | The repository, the list or one manuscript could not be read, so nothing is known. | Try again. An unreadable manuscript is never treated as unchanged. |
| 1 | Usage error (no list id, or `--head` that is not a full commit id). | Fix the command. |

Each table row shows the recorded status, the current status and any notes. The repository's own dates can disagree (the first three withdrawals are dated October 6 in the notices and October 7 in `history.md`); the list records both.

## If the change is found after publication

An episode already on the feed whose statuses have since changed is a published problem: it goes through the severity ladder in rule 16 of `governance/AGENT_ROLES.md` (a correction note, a prominent correction note, or withdrawal), with Gary the only approver at every level. It is never silently edited.
