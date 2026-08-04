#!/usr/bin/env python3
"""
Validate file-path citations in governance/*.md against the working tree.

Why this exists
---------------
Governance documents cite code paths as evidence for factual claims. When a
cleanout moves a file into the gitignored `local_archive/`, the file leaves the
repo silently and the citation rots without anything failing. On 2026-08-04 four
such citations were found in RESOURCE_MANIFEST.md; the underlying facts were all
still correct, only the pointers were dead. This script turns that recurring
finding into a caught error.

Run it before committing any edit to governance/, and after any cleanout that
moves files out of the tree.

    python3 governance/check_citations.py

Exit 0 = clean. Exit 1 = at least one dead or untracked citation.

What "clean" does NOT mean
---------------------------
This script verifies that pointers resolve, not that the claims they support
are true. A citation can point at a real file and still be describing that
file incorrectly. Case in point (2026-08-04): a manifest row claimed a resume
cited a superseded DOI under an old title -- the citation's path existed, but
the claim itself was wrong; the resume actually carried the current DOI. Exit
0 means every pointer in the document landed somewhere real. It says nothing
about whether what's written next to that pointer is accurate.

Conventions it understands
--------------------------
* A citation is a backticked path, optionally with :line or :start-end,
  e.g. `cloud-run-backend/main.py:85` or `components/foo.ts:6-7`.
* Paths containing "/" must resolve exactly, AND be tracked by git -- an
  untracked-but-present file resolves only on the machine that holds it and
  is dead for every other collaborator, so it gets its own UNTRACKED bucket
  rather than counting as resolved. (Found 2026-08-04: a citation to an
  untracked resume passed silently on the machine that had the file, and a
  fresh clone without it had no way to tell "moved to archive" apart from
  "never committed" -- the wrong "(archived)" guess that followed from that
  ambiguity is what prompted this fix.)
* A bare filename may resolve anywhere in the tracked tree; if it does,
  that's reported as a WARN (imprecise but not wrong) rather than an error.
* Names in CROSS_REPO live in sibling repos by design and are skipped.
* A citation whose surrounding text contains "(archived)" is treated as a
  deliberate pointer to something outside the tree and is skipped. Use this
  rather than deleting the citation, so the provenance trail survives.
"""

import os
import re
import sys
import glob
import subprocess

# Files that legitimately live in sibling repos (glmp, atap, sciencevideodb,
# progframe) rather than in copernicus-web. Cited by bare name on purpose.
CROSS_REPO = {
    "AGENT_ROLES.md",
    "GLMP_MASTER_TODO.md",
    "GLMP_GOALS.md",
    "SUITE_GOVERNANCE_TODO.md",
    "GITHUB_HOUSEKEEPING_TODO.md",
    "research_focus.json",
    "flowchart-source-papers.tsv",
    "app.py",
    "requirements.txt",
}

# A citation prefixed with a sibling repo's name points outside this repo by
# design, e.g. `glmp/archive/foo.md`. Not checkable from here.
SIBLING_REPOS = ("glmp/", "atap/", "progframe/", "sciencevideodb/", "metadata-database/")

# This repo's own name used as a prefix is a self-reference; strip it.
OWN_REPO_PREFIX = "copernicus-web/"

CITATION = re.compile(
    r"`([A-Za-z0-9_][A-Za-z0-9_./-]*\.(?:py|ts|tsx|js|jsx|json|md|html|ya?ml|sh|toml|tsv|csv))"
    r"(?::[0-9][0-9,\-]*)?`"
)

ARCHIVED_MARKER = "(archived)"


def tracked_files():
    """Return (basename -> [paths], set of tracked paths).

    Uses git rather than the filesystem so that gitignored and untracked files
    are distinguishable. A citation to an untracked file resolves on the machine
    that happens to hold it and is dead for every collaborator, so the two cases
    must not be conflated.
    """
    out = subprocess.run(
        ["git", "ls-files"], capture_output=True, text=True, check=True
    ).stdout.splitlines()
    index = {}
    for p in out:
        index.setdefault(os.path.basename(p), []).append(p)
    return index, set(out)


def check(docs):
    index, tracked_set = tracked_files()
    errors, warnings, untracked, skipped, ok = [], [], [], 0, 0

    for doc in docs:
        with open(doc, encoding="utf-8") as fh:
            lines = fh.readlines()
        for lineno, line in enumerate(lines, 1):
            for cited in CITATION.findall(line):
                if cited.startswith(OWN_REPO_PREFIX):
                    cited = cited[len(OWN_REPO_PREFIX):]
                base = os.path.basename(cited)

                if (
                    base in CROSS_REPO
                    or cited.startswith(SIBLING_REPOS)
                    or ARCHIVED_MARKER in line
                ):
                    skipped += 1
                    continue

                if "/" in cited:
                    if cited in tracked_set:
                        ok += 1
                    elif os.path.exists(cited):
                        untracked.append((doc, lineno, cited))
                    else:
                        alt = index.get(base, [])
                        hint = f" (found at {alt[0]})" if alt else ""
                        errors.append((doc, lineno, cited, hint))
                else:
                    found = index.get(base, [])
                    if found:
                        ok += 1
                        warnings.append((doc, lineno, cited, found[0]))
                    else:
                        errors.append((doc, lineno, cited, ""))

    return errors, warnings, untracked, skipped, ok


def main():
    docs = sorted(glob.glob("governance/*.md"))
    if not docs:
        print("No governance/*.md found. Run from the repo root.", file=sys.stderr)
        return 2

    errors, warnings, untracked, skipped, ok = check(docs)

    print(f"Checked {len(docs)} governance documents.")
    print(
        f"  resolved: {ok}   dead: {len(errors)}   untracked: {len(untracked)}"
        f"   imprecise: {len(warnings)}   skipped: {skipped}"
    )

    if warnings:
        print("\nIMPRECISE — cited by bare filename, resolves elsewhere in tree:")
        for doc, lineno, cited, found in warnings:
            print(f"  {doc}:{lineno}  `{cited}`  ->  {found}")

    if untracked:
        print("\nUNTRACKED — file is present locally but not committed:")
        for doc, lineno, cited in untracked:
            print(f"  {doc}:{lineno}  `{cited}`")
        print(
            "  These resolve on this machine only and are dead for every collaborator.\n"
            "  Either commit the file, or mark the citation as user-supplied."
        )

    if errors:
        print("\nDEAD — cited path does not exist:")
        for doc, lineno, cited, hint in errors:
            print(f"  {doc}:{lineno}  `{cited}`{hint}")
        print(
            "\nIf the file was moved to local_archive/ deliberately, mark the citation\n"
            f'with "{ARCHIVED_MARKER}" on the same line rather than deleting it, so the\n'
            "provenance trail survives the cleanout."
        )
        return 1

    if untracked:
        # Untracked citations fail too: they resolve only on one machine.
        # Flip this to `return 0` if you'd rather they warn without blocking.
        return 1

    print("\nAll citations resolve.")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except BrokenPipeError:
        # Tolerate being piped into head/less.
        os._exit(0)
