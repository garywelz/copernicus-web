#!/usr/bin/env python3
"""Fetch the abstracts of an engine's hold-list papers from the public scholarly registries, and store them for the owners' review
(docs/design/ENGINE_ONBOARDING_FORM.md 2.5, 5.5, 5.6; PR 4b-2a). Run by an agent, attended; never by the form and never on a schedule.

    python scripts/onboarding/fetch_abstracts.py --engine-id ID [--apply --approval "LINE"] [--project P] [--pace SECONDS] [--limit N]

NO OWNER'S CONSENT IS NEEDED FOR THIS STEP (decided by Gary, 2026-11-10): the identifiers it sends come from the engine's PUBLIC repository (docs/hold_list.md,
loaded by scripts/onboarding/load_engine.py), not from anything an owner typed or uploaded. An owner's own lookups in the form are a different matter and stay
behind their consent. Nothing but a DOI, an arXiv id or a PubMed id is sent, with no credential and no address, to the four registries of
cloud-run-backend/utils/onboarding_lookup.py (Crossref, OpenAlex, arXiv, Semantic Scholar), through that module, with its hosts, timeouts and size cap.

DRY RUN (the default) reads Firestore, calls NO registry and writes nothing: it lists which papers have no abstract yet and would be looked up.

--apply (with the typed approval line) looks each of those papers up, one every --pace seconds (default 3: arXiv asks for that), and then writes everything in
ONE Firestore transaction with ONE `abstract_fetch` event. Per paper it sets, on its onboarding_candidates document:
    lookup_state          found | no_abstract | title_mismatch | not_found | unavailable
    abstract_fetched_at
    registry_record       {title, authors, year, identifiers, sources}      when a registry had the paper
    abstract, abstract_source                                                when it had an abstract
The lookup cache is not used and not written.

IT ONLY FILLS WHAT IS MISSING. A paper that already has an abstract is not looked up and not written, so the script can be run again later (Semantic Scholar
is unreliable without a key, so expect some papers with no abstract after the first run). A later lookup that learns nothing never replaces a record already
stored. Every paper is read again inside the transaction, and one that has gained an abstract since is skipped.

title_mismatch: the registry's title for the identifier does not resemble the hold list's title, so the identifier may point at a different paper. The paper
shows as unresolved in the form; the abstract is shown with the registry's own title beside it and a warning.

LIMIT: at most --limit papers a run (default and maximum 400; Firestore allows 500 writes in a transaction). More than that is refused, never cut.

EXIT CODES:  0 done, or a dry run   1 refused   2 usage, no engine record, Firestore unreachable, or no valid approval line
"""
import argparse
import re
import sys
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
BACKEND = ROOT / "cloud-run-backend"
DEFAULT_PROJECT = "regal-scholar-453620-r7"
DATABASE = "copernicusai"
MAX_LIMIT = 400
DEFAULT_PACE = 3.0


def approval_line(engine_id, project):
    return f"Approved: fetch abstracts for {engine_id} into {project}"


def default_db(project):
    from google.cloud import firestore
    return firestore.Client(project=project, database=DATABASE)


def backend():
    """The form's own modules: the lookup service and the review rules. Imported late, so --help and a usage error need nothing installed."""
    if str(BACKEND) not in sys.path:
        sys.path.insert(0, str(BACKEND))
    from utils import onboarding as ob
    from utils import onboarding_candidates as candidates
    from utils import onboarding_lookup as lookup
    return ob, candidates, lookup


def main(argv=None, db=None, now=None, out=print, sleep=time.sleep, modules=None):
    ap = argparse.ArgumentParser(description="Fetch abstracts for an engine's hold-list papers (see the module docstring).")
    ap.add_argument("--engine-id", required=True)
    ap.add_argument("--apply", action="store_true")
    ap.add_argument("--approval", default="")
    ap.add_argument("--project", default=DEFAULT_PROJECT)
    ap.add_argument("--pace", type=float, default=DEFAULT_PACE, help="seconds between papers (at least 1)")
    ap.add_argument("--limit", type=int, default=MAX_LIMIT)
    try:
        args = ap.parse_args(argv)
    except SystemExit:
        return 2
    eid = args.engine_id
    if not re.match(r"^[a-z0-9][a-z0-9-]{1,40}$", eid) or args.pace < 1 or not (1 <= args.limit <= MAX_LIMIT):
        print(f"ERROR: the engine id is not valid, --pace is under 1 second, or --limit is not between 1 and {MAX_LIMIT}", file=sys.stderr)
        return 2
    line = approval_line(eid, args.project)
    if args.apply and args.approval.strip() != line:
        print(f"ERROR: --apply needs the exact approval line, typed by Gary:\n  {line}", file=sys.stderr)
        return 2
    now = now or datetime.now(timezone.utc)
    ob, candidates, lookup = modules or backend()
    try:
        if db is None:
            db = default_db(args.project)
        if not db.collection(ob.ENGINES).document(eid).get().exists:
            print(f"ERROR: no engine record {eid}", file=sys.stderr)
            return 2
        docs = sorted(((d.id, d.to_dict() or {}) for d in db.collection(candidates.CANDIDATES).where("engine_id", "==", eid).stream()), key=lambda r: r[0])
    except Exception as e:                                                         # noqa: BLE001
        print(f"ERROR: Firestore: {type(e).__name__}", file=sys.stderr)
        return 2
    todo = [(cid, c) for cid, c in docs if candidates.needs_fetch(c)]
    out(f"{'APPLY' if args.apply else 'DRY RUN'}: engine {eid}: {len(docs)} hold-list papers, {len(docs) - len(todo)} already have an abstract, {len(todo)} to look up")
    bad = [cid for cid, c in todo if not isinstance(c.get("identifier"), str) or c["identifier"].split(":", 1)[0] not in ("doi", "arxiv", "pmid")]
    if bad:
        print(f"REFUSED: {len(bad)} papers have no usable identifier: {', '.join(bad[:10])}", file=sys.stderr)
        return 1
    if len(todo) > args.limit:
        print(f"REFUSED: {len(todo)} papers to look up, over the limit of {args.limit} for one run; nothing was looked up or written", file=sys.stderr)
        return 1
    if not args.apply:
        for cid, c in todo:
            out(f"  would look up: {c['identifier']}  ({cid}; state now: {c.get('lookup_state') or 'never fetched'})")
        out(f"  no registry was called and nothing was written (dry run). It would take about {int(len(todo) * args.pace)} seconds. To apply, Gary types the approval line:\n    {line}")
        return 0
    if not todo:
        out("  nothing to look up: no registry was called and no write was made")
        return 0
    updates, seen = {}, {}
    for n, (cid, c) in enumerate(todo):
        if n:
            sleep(args.pace)
        kind = c["identifier"].split(":", 1)[0]
        try:
            result = lookup.lookup(None, kind, c["identifier"], now=now)            # None: the lookup cache is neither read nor written
        except ValueError:
            result = {"state": "unavailable", "results": []}
        fields = candidates.fetch_update(c, result, now.isoformat())
        state = fields["lookup_state"] if fields else "unchanged"
        seen[state] = seen.get(state, 0) + 1
        out(f"  {n + 1}/{len(todo)} {c['identifier']}: {state}")
        if fields:
            updates[cid] = fields
    if not updates:
        out("  nothing new was learned: no write was made")
        return 0
    try:
        done = candidates.apply_abstracts(db, engine_id=eid, updates=updates, now=now, request_id=uuid.uuid4().hex)
    except Exception as e:                                                         # noqa: BLE001
        print(f"ERROR: the write failed ({type(e).__name__}); nothing was written", file=sys.stderr)
        return 2
    counts = ", ".join(f"{len(v)} {k}" for k, v in sorted(done["written"].items())) or "none"
    out(f"  APPLIED: {sum(len(v) for v in done['written'].values())} papers written ({counts}); {len(done['skipped'])} skipped because they changed meanwhile; "
        f"{'one abstract_fetch event recorded' if done['written'] else 'no event'}")
    return 0


def utf8_output():
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="backslashreplace")


if __name__ == "__main__":
    utf8_output()
    sys.exit(main())
