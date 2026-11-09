"""Gary's review of the owners' work (onboarding PR 3b-1; docs/design/ENGINE_ONBOARDING_FORM.md 4.5, 5.1, 5.7): the dashboard data, the proposed-vs-current diff, and
the second gate, Approve and Send back.

NO ID OF A PERSON: everything here is shown by role ("final-say owner", "owners", "admin"), never an id or an address.

APPROVE (final -> approved): only a FINAL section, only at the revision AND content hash the reviewer was looking at (the revision alone does not change when an
owner re-opens and re-finalises a section, so both are sent). It records the exact revision and content_sha256 approved. An approved section is frozen: a later
owner edit starts a new draft revision (the form module does that, unchanged).

SEND BACK (final -> draft), decided by Gary 2026-11-09: the section goes straight back to DRAFT, not to a sticky "rejected". His note is stored on the section as
`rejection_note` and shown to the owners at the top of the section and on the engine page until the section is next marked final (gates._final_in clears it).

Every check that decides the change runs inside the transaction that makes it, and the audit event is written in that same transaction. The note is stored on the
section; the event holds only its hash. Mail about a decision names the section and the engine and carries a link, never the note.
"""
from datetime import datetime
from typing import Any, Dict, List, Optional

from utils import onboarding as ob
from utils import onboarding_base as base
from utils import onboarding_form as form
from utils import onboarding_gates as gates
from utils import onboarding_render as render
from utils import onboarding_template as tpl
from utils.onboarding_form import FormError

NOTE_CAP = 1000
WAITING = {"final_say": "final-say owner", "admin": "admin", "owners": "owners", "none": "nobody"}
VIEWER = {"via": "admin"}


def _parse(iso: Any) -> Optional[datetime]:
    try:
        d = datetime.fromisoformat(iso) if isinstance(iso, str) else None
    except ValueError:
        return None
    return d if d is None or d.tzinfo else d.replace(tzinfo=ob._utcnow().tzinfo)


def _since(sec: dict, status: str) -> Optional[str]:
    if status == "final":
        return sec.get("final_at") or sec.get("updated_at")
    if status == "approved":
        return sec.get("approved_at") or sec.get("updated_at")
    return sec.get("rejected_at") if sec.get("rejection_note") and sec.get("rejected_at") else sec.get("updated_at")


def section_row(meta: dict, counts: dict, sec: dict, now: datetime) -> Dict[str, Any]:
    status = sec.get("status", "draft")
    if status == "final":
        who = "admin"
    elif status == "approved":
        who = "none"
    else:
        who = "final_say" if counts["ready"] else "owners"
    since = _since(sec, status)
    then = _parse(since)
    return {"key": meta["key"], "title": meta["title"], "status": status, "revision": sec.get("revision", 1), "content_sha256": sec.get("content_sha256"),
            "items": counts["items"], "ready": counts["ready"], "open": counts["open"], "disagreed": counts["disagreed"],
            "waiting_on": {"who": who, "label": WAITING[who]}, "since": since, "age_seconds": max(0, int((now - then).total_seconds())) if then else None,
            "rejection_note": sec.get("rejection_note"), "rejected_at": sec.get("rejected_at") if sec.get("rejection_note") else None,
            "approved_at": sec.get("approved_at") if status == "approved" else None, "approver_note": sec.get("approver_note") if status == "approved" else None,
            "approved_revision": sec.get("approved_revision") if status == "approved" else None}


def engine_overview(db, engine_id: str, engine: dict, now: datetime) -> Dict[str, Any]:
    items, comments, secs = form._items_of(db, engine_id), form._comments_of(db, engine_id), form._section_docs(db, engine_id)
    disagreed = form._disagreed_ids(comments)
    rows = []
    for meta in tpl.SECTIONS:
        its = [i for i in items if i.get("section") == meta["key"]]
        sec = secs.get(meta["key"]) or {}
        rows.append(section_row(meta, form.section_counts(its, disagreed, sec.get("status", "draft")), sec, now))
    return {"engine_id": engine_id, "label": engine.get("label"), "state": engine.get("state"), "repo": base.engine_repo(engine), "sections": rows,
            "awaiting_review": sum(1 for r in rows if r["status"] == "final")}


def list_engines(db, now: Optional[datetime] = None) -> List[Dict[str, Any]]:
    now = now or ob._utcnow()
    out = [engine_overview(db, d.id, d.to_dict() or {}, now) for d in db.collection(ob.ENGINES).stream()]
    return sorted(out, key=lambda e: e["engine_id"])


def engine_detail(db, engine_id: str, now: Optional[datetime] = None) -> Dict[str, Any]:
    """One engine for Gary: the overview, and for every section its items with their history and comment threads. Read only."""
    engine = form._engine(db, engine_id)
    now = now or ob._utcnow()
    return {**engine_overview(db, engine_id, engine, now), "details": [form.get_section(db, engine_id, key, VIEWER) for key in tpl.SECTION_KEYS]}


# ---- the diff ---------------------------------------------------------------------------------------------------------------------------------------
def section_diff(db, engine_id: str, section: str, now: Optional[datetime] = None, fetched_at: Optional[float] = None) -> Dict[str, Any]:
    """The proposed output files for a FINAL or APPROVED section, each diffed against the file on the engine repository's main (fetched with no token), with the
    base commit. No repository: every file is an add, and the response says so. A fetch that fails degrades to 'current file unavailable'."""
    if section not in tpl.SECTION_KEYS:
        raise FormError(404, "Not found")
    engine = form._engine(db, engine_id)
    sec = form._section_docs(db, engine_id).get(section) or {}
    status = sec.get("status", "draft")
    if status not in ("final", "approved"):
        raise FormError(409, "Only a final or approved section has a diff to review", current_status=status)
    now = now or ob._utcnow()
    items = form._items_of(db, engine_id, section)
    paths = render.files_for([section])
    fetched = base.fetch_bases(engine, paths, fetched_at)
    rendered = render.render_files({section: items}, {p: fetched["files"][p][1] for p in paths}, now.date().isoformat())
    files = []
    for r in rendered:
        state, current = fetched["files"][r["path"]]
        if state == "ok":
            body, action = base.unified(current, r["content"]), "unchanged" if current == r["content"] else "modify"
        else:
            body, action = base.plain_lines(r["content"]), "add" if state in ("missing", "none") else "unknown"
        files.append({"path": r["path"], "action": action, "base_state": state, "proposed_sha256": r["sha256"], "notes": r["notes"], **body})
    note = None
    if fetched["no_repo"]:
        note = "This engine has no repository, so every file is shown as an add against an empty tree."
    elif fetched["commit_state"] != "ok":
        note = "The repository's current commit could not be read; files were fetched from main."
    return {"engine_id": engine_id, "section": section, "section_status": status, "revision": sec.get("revision", 1), "content_sha256": form.content_sha256(items),
            "repo": fetched["repo"], "no_repo": fetched["no_repo"], "base": {"branch": "main", "commit_sha": fetched["commit_sha"], "commit_state": fetched["commit_state"]},
            "note": note, "files": files}


# ---- approve and send back ------------------------------------------------------------------------------------------------------------------------
def clean_note(note: Any, required: bool) -> str:
    try:
        return tpl.clean_text(note if note is not None else "", NOTE_CAP, "the note", required=required)
    except tpl.TemplateError as e:
        raise FormError(400, str(e))


def _decide_in(transaction, db, engine_id, section, decision, expected_revision, expected_sha, note, now, ip_hash, request_id):
    engine_snap = db.collection(ob.ENGINES).document(engine_id).get(transaction=transaction)
    if not engine_snap.exists:
        raise FormError(404, "Not found")
    sec_ref = form._section_ref(db, engine_id, section)
    sec_snap = sec_ref.get(transaction=transaction)
    sec = sec_snap.to_dict() if sec_snap.exists else {"engine_id": engine_id, "section": section, "status": "draft", "revision": 1}
    status = sec.get("status", "draft")
    if status != "final":
        raise FormError(409, "Only a final section can be approved or sent back", reason="not_final", current_status=status)
    items = form._items_of(db, engine_id, section, transaction=transaction)
    digest = form.content_sha256(items)
    if expected_revision != sec.get("revision", 1) or expected_sha != sec.get("content_sha256") or digest != sec.get("content_sha256"):
        raise FormError(409, "This section changed since you opened it; reload and look again", reason="changed")
    revision, iso = sec.get("revision", 1), now.isoformat()
    if decision == "approve":
        new = {**sec, "status": "approved", "approved_at": iso, "approved_revision": revision, "approved_content_sha256": digest, "approver_note": note or None,
               "approved_by": "admin", "rejection_note": None, "rejected_at": None, "updated_at": iso}
        action = "approve"
    else:
        new = {**sec, "status": "draft", "rejection_note": note, "rejected_at": iso, "final_by": None, "final_via_delegation": False, "final_at": None,
               "ready_notified": True, "updated_at": iso}      # ready_notified: the section is still ready, and the holder is told by the send-back mail instead
        action = "reject"
    transaction.set(sec_ref, new)
    ob._event(transaction, db, engine_id=engine_id, actor="admin", actor_role="admin", action=action, target=section, before={"status": "final"},
              after={"status": new["status"], "content_sha256": digest}, ip_hash=ip_hash, request_id=request_id, now=now,
              extra={"section": section, "revision": revision, "content_sha256": digest, "note_sha256": ob._sha(note) if note else None})
    return {"section": section, "status": new["status"], "revision": revision, "content_sha256": digest}


def decide(db, *, engine_id: str, section: str, decision: str, expected_revision: int, expected_content_sha256: str, note: Any, now: Optional[datetime] = None,
           ip_hash: Optional[str] = None, request_id: Optional[str] = None) -> Dict[str, Any]:
    """Approve or send back one FINAL section at the revision and hash the reviewer saw. A note is required to send back and optional to approve."""
    if section not in tpl.SECTION_KEYS:
        raise FormError(404, "Not found")
    text = clean_note(note, required=decision == "reject")
    return ob._run_in_transaction(db, _decide_in, db, engine_id, section, decision, expected_revision, expected_content_sha256, text, now or ob._utcnow(), ip_hash, request_id)


def owner_addresses(db, engine_id: str) -> List[str]:
    """The address of every ACTIVE owner of the engine who has not switched the engine's mail off (Gary, 2026-11-09: a decision concerns both owners)."""
    out = []
    for d in db.collection(ob.MEMBERS).where("engine_id", "==", engine_id).stream():
        sid = (d.to_dict() or {}).get("subscriber_id")
        m = ob.active_membership(db, engine_id, sid) if sid else None
        if not m or m.get("role") != "owner" or m.get("notifications_email", True) is False:
            continue
        snap = db.collection("subscribers").document(sid).get()
        address = ((snap.to_dict() or {}).get("email") if snap.exists else None) or ""
        if address and address not in out:
            out.append(address)
    return out


def plan_decision_mail(db, *, engine_id: str, section: str, decision: str) -> List[Dict[str, Any]]:
    """Who to tell: ALL active owners of the engine, each respecting their own notification switch (Gary, 2026-11-09). The mail names the engine and the section
    and says approved or sent back; it never carries the note."""
    engine = form._engine(db, engine_id)
    to = owner_addresses(db, engine_id)
    return [{"kind": "approved" if decision == "approve" else "sent_back", "engine_label": engine.get("label") or engine_id, "section_title": tpl.section_title(section), "to": to}] if to else []
