#!/usr/bin/env python3
"""One-time rebuild of the podcast feed's episode text for the items already in it (services/rss_service.rebuild_feed_text; feed_text.py).

WHY: on 2026-11-19, 8 of the 40 feed items reached podcast apps with their HTML escaped inside CDATA, so listeners saw "<p style=...>" and
"<h2>References</h2>" as text, and one description showed "&gt;". The writer is fixed for new publishes; an item already broken stays broken until it
is rebuilt, because every publish re-reads and re-writes the old items as they are.

WHAT IT CHANGES, per item: <description>, <itunes:summary> and <content:encoded>, rebuilt from the item's job record with today's builder (simple
paragraphs and a plain reference list; only the tags podcast apps accept). Nothing else: title (except a doubly escaped character), link, enclosure,
guid, date, images, duration, episode number and the creator credit stay as they are. An item without a job record is left exactly as it is. The job is
found the way the publish route finds it (podcast_jobs, result.canonical_filename == the item's guid, first match).

  python scripts/rebuild_feed_text.py                      dry run (the default): reads the feed and Firestore, writes NOTHING, prints a report
  python scripts/rebuild_feed_text.py --apply --approval "Approved: rebuild the feed text of N items"

--apply needs that exact line, with N the number of items the dry run would rebuild. It first copies the current feed, checksummed, to
gs://regal-scholar-453620-r7-internal/backups/feed/, then writes the new feed only if the feed has not changed since it was read (generation match).
The public feed file is cached for an hour, so podcast apps may show the old text for up to an hour after.

EXIT CODES: 0 done (or a dry run)   1 refused (a rebuilt text failed the pre-publish check, or the feed changed meanwhile)   2 usage or no access"""
import argparse
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

BACKUP_BUCKET = "regal-scholar-453620-r7-internal"
BACKUP_PREFIX = "backups/feed/"


def approval_line(n):
    return f"Approved: rebuild the feed text of {n} items"


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--apply", action="store_true")
    ap.add_argument("--approval", default="")
    args = ap.parse_args(argv)

    from google.cloud import storage
    from google.api_core.exceptions import PreconditionFailed
    from config.constants import RSS_BUCKET_NAME, RSS_FEED_BLOB_NAME
    from config.database import db
    from services.rss_service import rebuild_feed_text

    if db is None:
        print("ERROR: no Firestore access", file=sys.stderr)
        return 2
    client = storage.Client()
    blob = client.bucket(RSS_BUCKET_NAME).blob(RSS_FEED_BLOB_NAME)
    blob.reload()
    generation, old = blob.generation, blob.download_as_bytes()

    chosen = {}

    def job_for_guid(guid, title):
        """The job whose file name is the item's guid AND whose title is the item's title. Two episodes can share a file name (on 2026-11-19 the
        publish route's first match for ever-phys-250032 was a different episode), so a file name alone is not enough; no match, or more than one,
        leaves the item as it is."""
        from google.cloud.firestore import FieldFilter
        jobs = list(db.collection("podcast_jobs").where(filter=FieldFilter("result.canonical_filename", "==", guid)).stream())
        if not jobs:
            return None
        same = [d for d in jobs if ((d.to_dict() or {}).get("result") or {}).get("title", "").strip() == title]
        if len(same) != 1:
            return f"{len(jobs)} job(s) with this file name, {len(same)} with this item's title: not chosen"
        chosen[guid] = same[0].id
        return same[0].to_dict()

    try:
        new, report = rebuild_feed_text(old, job_for_guid)
    except Exception as e:                                                       # noqa: BLE001 - the pre-publish check refused a text
        print(f"REFUSED: {type(e).__name__}: {e}; nothing was written", file=sys.stderr)
        return 1
    rebuilt = [r for r in report if r["rebuilt"]]
    print(f"feed {RSS_FEED_BLOB_NAME} generation {generation}: {len(report)} items | rebuilt {len(rebuilt)} | left as they are {len(report) - len(rebuilt)}")
    for r in report:
        if r["rebuilt"]:
            print(f"  {r['guid']:24} job {chosen.get(r['guid'], '?')[:8]} | before {r['before']} -> after {r['after']} | changed {r['changed']} | lengths {r['lengths']}")
        else:
            print(f"  {r['guid']:24} NOT rebuilt: {r['reason']} | as it is: {r['before']}")
    # Proof that nothing else changed: every item's other elements (and the channel's own), compared before and after
    import xml.etree.ElementTree as ET
    from config.constants import RSS_NAMESPACES
    text_tags = {"description", f"{{{RSS_NAMESPACES['itunes']}}}summary", f"{{{RSS_NAMESPACES['content']}}}encoded"}

    def rest(root):
        ch = root.find("channel")
        head = [ET.tostring(e) for e in ch if e.tag != "item"]
        items = [[ET.tostring(e) for e in it if e.tag not in text_tags and e.tag != "title"] for it in ch.findall("item")]
        return head, items, [it.findtext("guid") for it in ch.findall("item")]
    before_rest, after_rest = rest(ET.fromstring(old)), rest(ET.fromstring(new))
    titles_changed = [r["guid"] for r in rebuilt if "title" in r["changed"]]
    print(f"other elements unchanged: channel {before_rest[0] == after_rest[0]} | items {before_rest[1] == after_rest[1]} | order {before_rest[2] == after_rest[2]}"
          f" | titles changed {titles_changed}")
    if before_rest != after_rest:
        print("REFUSED: something other than the episode text would change; nothing was written", file=sys.stderr)
        return 1
    escaped_before = sum(1 for r in report if "escaped" in r["before"].values())
    escaped_after = sum(1 for r in rebuilt if "escaped" in r["after"].values()) + sum(1 for r in report if not r["rebuilt"] and "escaped" in r["before"].values())
    print(f"items showing escaped markup to listeners: before {escaped_before} | after {escaped_after}")
    print(f"feed size: {len(old)} -> {len(new)} bytes | sha256 before {hashlib.sha256(old).hexdigest()[:16]} after {hashlib.sha256(new).hexdigest()[:16]}")

    if not args.apply:
        print(f"DRY RUN: nothing was written. To apply, Gary types the approval line:\n    {approval_line(len(rebuilt))}")
        return 0
    if args.approval.strip() != approval_line(len(rebuilt)):
        print(f"ERROR: --apply needs the exact line:\n  {approval_line(len(rebuilt))}", file=sys.stderr)
        return 2
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    backup = client.bucket(BACKUP_BUCKET).blob(f"{BACKUP_PREFIX}feed-before-text-rebuild-{stamp}.xml")
    backup.upload_from_string(old, content_type="application/rss+xml")
    backup.reload()
    if backup.size != len(old):
        print("REFUSED: the backup does not have the feed's size; nothing was written", file=sys.stderr)
        return 1
    try:
        blob.upload_from_string(new, content_type="application/rss+xml", if_generation_match=generation)
    except PreconditionFailed:
        print("REFUSED: the feed changed since it was read; nothing was written (the backup stays)", file=sys.stderr)
        return 1
    blob.reload()
    print(json.dumps({"written": True, "generation": blob.generation, "backup": f"gs://{BACKUP_BUCKET}/{backup.name}",
                      "backup_sha256": hashlib.sha256(old).hexdigest(), "new_sha256": hashlib.sha256(new).hexdigest()}))
    return 0


if __name__ == "__main__":
    sys.exit(main())
