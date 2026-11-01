#!/usr/bin/env python3
"""Publish-day re-check of an approved curated source list (design §4.3). Run BY HAND, attended, before an episode is published.

    cd cloud-run-backend
    python scripts/recheck_curated_statuses.py <list_id>              # against the current head of openai/math
    python scripts/recheck_curated_statuses.py <list_id> --head <40-character commit>
    python scripts/recheck_curated_statuses.py <list_id> --json

It READS the approved list from Firestore (your own credentials; it writes nothing, anywhere), asks GitHub for the current head of the
repository's default branch, recomputes the status of every company-release manuscript in the list at that head (withdrawn, has a Lean
formalization, unverified) and compares it with the status the repository gave it when the list was built (for an item marked `checked by
experts` that is the status it had before a commentary source was cited, kept with the item). It also flags a manuscript whose file changed
since the pinned commit and one that is no longer in the manuscript map. For every `checked by experts` item it reads the cited commentary's
private text (read-only; never printed) and confirms that the quoted sentence still occurs in it and that the text still hashes to the value
the list was approved with.

Exit code:  0  nothing changed: publication may go ahead;
            2  something changed, or a checked-by quotation or text no longer matches: DO NOT PUBLISH; show the table to Gary (an episode already published goes through the severity ladder, rule 16);
            3  the repository or the list could not be read: nothing was checked, try again;
            1  usage error.
"""
from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import curated_sources as cs  # noqa: E402
import openai_math_index as omi  # noqa: E402
import openai_math_status as oms  # noqa: E402

COLLECTION = "curated_source_lists"
PRIVATE_COLLECTION = "curated_private_text"      # the pasted commentary; read here, never printed, never written


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


def load_private_text(list_id: str, item_id: str, db=None):
    if db is None:
        from config.database import db as _db
        db = _db
    snap = db.collection(PRIVATE_COLLECTION).document(f"{list_id}__{item_id}").get()
    return (snap.to_dict() or {}).get("text") if snap.exists else None


def check_checked_by(list_id: str, items, db=None):
    """For every item marked `checked by experts`: does the quoted sentence still occur in the cited commentary's private text, and does that text
    still hash to the value the list was approved with? One row per item: {item_id, title, source, quote_found, hash_matches, ok, notes}.
    The text itself is never returned or printed."""
    by_id = {i.get("item_id"): i for i in items}
    rows = []
    for it in items:
        if it.get("class") != "company_release" or it.get("result_status") != oms.STATUS_CHECKED:
            continue
        cb = (it.get("status_basis") or {}).get("checked_by") or {}
        src = by_id.get(cb.get("commentary_item_id"))
        notes = []
        text = None
        if src is None or src.get("class") != cs.COMMENTARY:
            notes.append("the cited commentary source is no longer in the list")
        else:
            text = load_private_text(list_id, src["item_id"], db)
            if text is None:
                notes.append("the cited commentary's private text could not be found")
        quote_found = text is not None and cs.text_contains(text, cb.get("quote") or "")
        hash_matches = text is not None and hashlib.sha256(text.encode("utf-8")).hexdigest() == src.get("text_sha256")
        if text is not None and not quote_found:
            notes.append("the quoted sentence no longer occurs in the text")
        if text is not None and not hash_matches:
            notes.append("the text no longer matches the hash the list was approved with")
        rows.append({"item_id": it.get("item_id"), "title": it.get("title"), "source": it.get("checked_by") or (src or {}).get("title"),
                     "quote_found": quote_found, "hash_matches": hash_matches, "ok": quote_found and hash_matches, "notes": notes})
    return rows


async def check(list_id: str, head: str | None = None, db=None, fetch=None):
    """(doc, head, rows, checked_by). Raises LookupError for an unknown list, omi.RepoUnavailable when the repository cannot be read."""
    doc = load_list(list_id, db)
    head = head or await oms.resolve_head(fetch)
    rows = await oms.recheck_items(doc.get("items") or [], head, fetch)
    return doc, head, rows, check_checked_by(list_id, doc.get("items") or [], db)


def render(doc, head, rows, checked=()) -> str:
    pin = (doc.get("pin") or {}).get("commit", "")
    out = [f"list {doc.get('list_id')}  status {doc.get('status')}  hash {str(doc.get('list_hash'))[:12]}",
           f"pinned commit {pin[:9]}   head now {head[:9]}   {'(the pin is the head)' if pin == head else '(the repository has moved)'}", ""]
    if not rows:
        out.append("no company-release manuscripts in this list: nothing to re-check")
    for r in rows:
        flag = "CHANGED" if r["changed"] else "same   "
        was = r["recorded"] if r["recorded"] == r["baseline"] else f"{r['baseline']} (+experts)"
        out.append(f"{flag}  {was:<24} -> {r['current']:<24} {r['title']}")
        for n in r["notes"]:
            out.append(f"         note: {n}")
    for c in checked:
        out.append(f"{'ok     ' if c['ok'] else 'FAILED '}  checked by {c['source']}: quoted sentence {'found' if c['quote_found'] else 'NOT found'}, "
                   f"text hash {'matches' if c['hash_matches'] else 'DOES NOT match'}   {c['title']}")
        for n in c["notes"]:
            out.append(f"         note: {n}")
    changed = [r for r in rows if r["changed"]]
    failed = [c for c in checked if not c["ok"]]
    problems = []
    if changed:
        problems.append(f"{len(changed)} item(s) changed since the list was approved")
    if failed:
        problems.append(f"{len(failed)} checked-by item(s) no longer match their cited commentary")
    out += ["", ("DO NOT PUBLISH: " + "; ".join(problems) + ". Show this to Gary.") if problems else "No change since approval: publication may go ahead."]
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
        doc, head, rows, checked = loop.run_until_complete(check(args.list_id, args.head, db, fetch))
    except LookupError as e:
        print(str(e), file=sys.stderr)
        return 3
    except omi.RepoUnavailable as e:
        print(f"could not check: {e}", file=sys.stderr)
        return 3
    finally:
        loop.close()
    if args.json:
        print(json.dumps({"list_id": args.list_id, "head": head, "rows": rows, "checked_by": checked}, indent=2))
    else:
        print(render(doc, head, rows, checked))
    if any(r["current"] == "unreadable" for r in rows):
        return 3
    return 2 if any(r["changed"] for r in rows) or any(not c["ok"] for c in checked) else 0


if __name__ == "__main__":
    sys.exit(main())
