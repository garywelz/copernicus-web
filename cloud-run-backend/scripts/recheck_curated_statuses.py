#!/usr/bin/env python3
"""Publish-day re-check of an approved curated source list (design §4.3). Run BY HAND, attended, before an episode is published.

    cd cloud-run-backend
    python scripts/recheck_curated_statuses.py <list_id>              # against the current head of openai/math
    python scripts/recheck_curated_statuses.py <list_id> --head <40-character commit>
    python scripts/recheck_curated_statuses.py <list_id> --json

It READS the approved list from Firestore (your own credentials; it writes nothing, anywhere), asks GitHub for the current head of the
repository's default branch, recomputes the status of every company-release manuscript in the list at that head (withdrawn, has a Lean
formalization, unverified) and compares it with the status recorded when the list was approved. It also flags a manuscript whose file changed
since the pinned commit and one that is no longer in the manuscript map.

Exit code:  0  nothing changed: publication may go ahead;
            2  something changed: DO NOT PUBLISH; show the table to Gary (an episode already published goes through the severity ladder, rule 16);
            3  the repository or the list could not be read: nothing was checked, try again;
            1  usage error.
"""
from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import openai_math_index as omi  # noqa: E402
import openai_math_status as oms  # noqa: E402

COLLECTION = "curated_source_lists"


def load_list(list_id: str, db=None):
    if db is None:
        from config.database import db as _db
        db = _db
    if db is None:
        raise omi.RepoUnavailable("Firestore is not available with these credentials")
    snap = db.collection(COLLECTION).document(list_id).get()
    if not snap.exists:
        raise LookupError(f"no source list {list_id}")
    return snap.to_dict() or {}


async def check(list_id: str, head: str | None = None, db=None, fetch=None):
    """(doc, head, rows). Raises LookupError for an unknown list, omi.RepoUnavailable when the repository cannot be read."""
    doc = load_list(list_id, db)
    head = head or await oms.resolve_head(fetch)
    rows = await oms.recheck_items(doc.get("items") or [], head, fetch)
    return doc, head, rows


def render(doc, head, rows) -> str:
    pin = (doc.get("pin") or {}).get("commit", "")
    out = [f"list {doc.get('list_id')}  status {doc.get('status')}  hash {str(doc.get('list_hash'))[:12]}",
           f"pinned commit {pin[:9]}   head now {head[:9]}   {'(the pin is the head)' if pin == head else '(the repository has moved)'}", ""]
    if not rows:
        out.append("no company-release manuscripts in this list: nothing to re-check")
    for r in rows:
        flag = "CHANGED" if r["changed"] else "same   "
        out.append(f"{flag}  {r['recorded']:<24} -> {r['current']:<24} {r['title']}")
        for n in r["notes"]:
            out.append(f"         note: {n}")
    changed = [r for r in rows if r["changed"]]
    out += ["", ("DO NOT PUBLISH: " + str(len(changed)) + " item(s) changed since the list was approved. Show this to Gary.") if changed
            else "No change since approval: publication may go ahead."]
    return "\n".join(out)


def main(argv=None, db=None, fetch=None) -> int:
    ap = argparse.ArgumentParser(description="Re-check an approved curated source list against the current head of openai/math (read-only).")
    ap.add_argument("list_id")
    ap.add_argument("--head", help="check against this commit instead of the current head")
    ap.add_argument("--json", action="store_true", help="print the rows as JSON")
    try:
        args = ap.parse_args(argv)
    except SystemExit:
        return 1
    if args.head and not omi.COMMIT_RE.match(args.head):
        print("--head must be a full 40-character lower-case commit id", file=sys.stderr)
        return 1
    loop = asyncio.new_event_loop()          # not asyncio.run(): that would leave the thread without an event loop
    try:
        doc, head, rows = loop.run_until_complete(check(args.list_id, args.head, db, fetch))
    except LookupError as e:
        print(str(e), file=sys.stderr)
        return 3
    except omi.RepoUnavailable as e:
        print(f"could not check: {e}", file=sys.stderr)
        return 3
    finally:
        loop.close()
    if args.json:
        print(json.dumps({"list_id": args.list_id, "head": head, "rows": rows}, indent=2))
    else:
        print(render(doc, head, rows))
    if any(r["current"] == "unreadable" for r in rows):
        return 3
    return 2 if any(r["changed"] for r in rows) else 0


if __name__ == "__main__":
    sys.exit(main())
