"""The owners' workspace, part 2 (onboarding PR 3a-2; docs/design/ENGINE_ONBOARDING_FORM.md 3.2, 4.5, 4.6, 5.6, 5.7): the first gate (Mark final, one section or every
ready section), delegation of final say, and the e-mail notifications to the final-say holder. Approve and reject are PR 3b; the pages are 3a-3.

WHO MAY MARK FINAL: the engine's final-say holder (`final_say_subscriber_id` on the engine record), or the owner a delegation names, for the sections it covers.
Nobody else: an owner without either gets 403 (they are a member, so the workspace's existence is no secret from them); an administrator or a stranger gets 404
(decided 2026-10-20: Gary never overrides the final-say owner, and no route lets an administrator mark a section final).

EVERY CHECK THAT DECIDES A CHANGE RUNS INSIDE THE TRANSACTION THAT MAKES IT: the holder, the delegation (revocation takes effect on the very next action), the
engine state, and the section's readiness (its items and comments are read in the transaction, so a concurrent edit or a new disagreement cannot slip past).
Each change writes its onboarding_events record in the same transaction.

NOTIFICATIONS carry the engine's name, the section's title and a link, never an answer, and are sent by the caller AFTER the change has committed: a mail failure
cannot undo anything. This module only decides who should be told and records that a section's "ready" mail has gone out (`ready_notified` on the section), so
it is not sent again while the section stays ready.
"""
from datetime import datetime
from typing import Any, Dict, List, Optional
import uuid

from config.constants import ADMIN_SUBSCRIBER_EMAIL
from utils import onboarding as ob
from utils import onboarding_form as form
from utils import onboarding_template as tpl
from utils.onboarding_form import FormError
from utils.subscriber_helpers import generate_subscriber_id

DELEGATIONS = "onboarding_delegations"
LIST_CAP = 20
REOPEN_MAIL_FROM = ("final", "approved")      # an edit to finished content is something the final-say holder should hear about (Gary, 2026-11-06)
REFUSALS = {
    "not_ready": "This section is not ready: every item needs an answer and no disagreement may be open",
    "already_final": "This section is already marked final",
    "approved": "This section has already been approved; an edit starts a new draft",
    "rejected": "This section was sent back; revise it first",
    "not_delegated": "That section is not covered by your delegation",
}


def _iso(now: datetime) -> str:
    return now.isoformat()


def scope_clean(scope: Any):
    """'all', or a list of one to four distinct section keys (returned in template order)."""
    if scope == "all":
        return "all"
    if isinstance(scope, list) and 1 <= len(scope) <= len(tpl.SECTION_KEYS) and all(isinstance(s, str) and s in tpl.SECTION_KEYS for s in scope) and len(set(scope)) == len(scope):
        return [k for k in tpl.SECTION_KEYS if k in scope]
    raise FormError(400, 'scope must be "all" or a list of section keys: ' + ", ".join(tpl.SECTION_KEYS))


def covers(scope: Any, section: str) -> bool:
    return scope == "all" or (isinstance(scope, list) and section in scope)


def is_holder(engine: dict, subscriber_id: Optional[str]) -> bool:
    return bool(subscriber_id) and engine.get("final_say_subscriber_id") == subscriber_id


# ---- who may mark final -----------------------------------------------------------------------------------------------------------------------------
def active_delegation(transaction, db, engine_id: str, engine: dict) -> Optional[dict]:
    """The engine's delegation in force right now, or None. It is in force only while: it is not revoked, the owner who made it is STILL the final-say holder
    (a succession ends the old holder's delegations), and the owner it names is STILL an active member of the engine."""
    did = engine.get("active_delegation_id")
    if not did:
        return None
    snap = db.collection(DELEGATIONS).document(did).get(transaction=transaction)
    d = snap.to_dict() if snap.exists else None
    if not d or d.get("engine_id") != engine_id or d.get("revoked_at") or d.get("from_subscriber_id") != engine.get("final_say_subscriber_id"):
        return None
    to = d.get("to_subscriber_id")
    m = db.collection(ob.MEMBERS).document(ob.member_id(engine_id, to)).get(transaction=transaction) if to else None
    md = m.to_dict() if m is not None and m.exists else None
    if not md or md.get("status") != "active" or md.get("subscriber_id") != to or md.get("role") != "owner":
        return None
    return d


def authority(transaction, db, engine_id: str, engine: dict, sid: str):
    """('holder', 'all') or ('delegate', scope) for this caller, or FormError(403)."""
    if is_holder(engine, sid):
        return "holder", "all"
    d = active_delegation(transaction, db, engine_id, engine)
    if d and d.get("to_subscriber_id") == sid:
        return "delegate", d.get("scope")
    raise FormError(403, "Only the final-say owner, or an owner they have delegated to, can mark a section final")


def authority_view(db, engine_id: str, engine: dict, sid: str) -> Dict[str, Any]:
    """For the engine page: may this owner mark final, and which sections."""
    try:
        _, scope = authority(None, db, engine_id, engine, sid)
    except FormError:
        return {"can_mark_final": False, "may_mark": []}
    return {"can_mark_final": True, "may_mark": list(tpl.SECTION_KEYS) if scope == "all" else list(scope)}


# ---- Mark final ---------------------------------------------------------------------------------------------------------------------------------------
def _final_in(transaction, db, engine_id, sid, wanted, bulk, now, ip_hash, request_id):
    engine_snap = db.collection(ob.ENGINES).document(engine_id).get(transaction=transaction)
    if not engine_snap.exists:
        raise FormError(404, "Not found")
    engine = engine_snap.to_dict() or {}
    who, scope = authority(transaction, db, engine_id, engine, sid)
    if engine.get("state") != "open":
        raise FormError(409, "This engine is not open for edits")
    plans, skipped = [], []
    for key in wanted:                                                       # reads first: every write below is buffered and committed together
        if not covers(scope, key):
            if not bulk:
                raise FormError(403, REFUSALS["not_delegated"], reason="not_delegated")
            skipped.append({"section": key, "reason": "not_delegated"})
            continue
        sec_ref = form._section_ref(db, engine_id, key)
        sec_snap = sec_ref.get(transaction=transaction)
        sec = sec_snap.to_dict() if sec_snap.exists else {"engine_id": engine_id, "section": key, "status": "draft", "revision": 1}
        status = sec.get("status", "draft")
        items = form._items_of(db, engine_id, key, transaction=transaction)
        counts = form.section_counts(items, form._disagreed_ids(form._comments_of(db, engine_id, key, transaction=transaction)), status)
        reason = {"final": "already_final", "approved": "approved", "rejected": "rejected"}.get(status) or (None if counts["ready"] else "not_ready")
        if reason:
            if not bulk:
                raise FormError(409, REFUSALS[reason], reason=reason, open=counts["open"], disagreed=counts["disagreed"])
            skipped.append({"section": key, "reason": reason})
            continue
        plans.append((key, sec_ref, sec, form.content_sha256(items)))
    marked = []
    for key, sec_ref, sec, digest in plans:
        revision = sec.get("revision", 1)
        transaction.set(sec_ref, {**sec, "engine_id": engine_id, "section": key, "status": "final", "revision": revision, "content_sha256": digest, "final_by": sid,
                                  "final_via_delegation": who == "delegate", "final_at": _iso(now), "updated_at": _iso(now), "ready_notified": False, "reopened_by": None})
        ob._event(transaction, db, engine_id=engine_id, actor=sid, actor_role="owner", action="final_all" if bulk else "final", target=key, before={"status": "draft"},
                  after={"status": "final", "content_sha256": digest}, ip_hash=ip_hash, request_id=request_id, now=now,
                  extra={"section": key, "revision": revision, "content_sha256": digest, "via_delegation": who == "delegate"})
        marked.append(key)
    return {"marked": marked, "skipped": skipped, "via_delegation": who == "delegate"}


def mark_final(db, *, engine_id: str, section: str, subscriber_id: str, now: Optional[datetime] = None, ip_hash: Optional[str] = None,
               request_id: Optional[str] = None) -> Dict[str, Any]:
    """Mark ONE section final. 403 if the caller is neither the holder nor a delegate for this section; 409 (with a reason) if the section is not ready, is already
    final, was approved or was sent back."""
    if section not in tpl.SECTION_KEYS:
        raise FormError(404, "Not found")
    out = ob._run_in_transaction(db, _final_in, db, engine_id, subscriber_id, [section], False, now or ob._utcnow(), ip_hash, request_id)
    return {"section": section, "status": "final", "via_delegation": out["via_delegation"]}


def mark_all_final(db, *, engine_id: str, subscriber_id: str, now: Optional[datetime] = None, ip_hash: Optional[str] = None, request_id: Optional[str] = None) -> Dict[str, Any]:
    """Mark every ready section the caller may mark. Returns which were marked and which were left, with the reason for each (not ready, not delegated, already
    final, approved or sent back). One audit event per section marked."""
    return ob._run_in_transaction(db, _final_in, db, engine_id, subscriber_id, list(tpl.SECTION_KEYS), True, now or ob._utcnow(), ip_hash, request_id)


# ---- delegation ---------------------------------------------------------------------------------------------------------------------------------------
def delegation_view(d: dict, delegation_id: str, viewer: dict, engine: dict) -> dict:
    """Never an id of a person: 'you', 'advisor' or 'other owner'."""
    return {"delegation_id": delegation_id, "from": form.author_label(d.get("from_subscriber_id"), viewer, engine), "to": form.author_label(d.get("to_subscriber_id"), viewer, engine),
            "scope": d.get("scope"), "created_at": d.get("created_at"), "revoked_at": d.get("revoked_at"),
            "active": not d.get("revoked_at") and engine.get("active_delegation_id") == delegation_id}


def other_owner(db, engine_id: str, sid: str) -> Optional[str]:
    """The ONE other active owner of the engine, or None when there is none or several (the form never shows a person's id, so a holder names the delegate as
    'the other owner'; an engine with more than two owners would need a handle, which v1 does not have)."""
    ids = [d.to_dict().get("subscriber_id") for d in db.collection(ob.MEMBERS).where("engine_id", "==", engine_id).stream()
           if (d.to_dict() or {}).get("status") == "active" and (d.to_dict() or {}).get("role") == "owner"]
    others = [i for i in ids if i and i != sid]
    return others[0] if len(others) == 1 else None


def _revoke_doc(transaction, db, engine_id, did, d, engine, revoker, now, ip_hash, request_id, replaced=False):
    transaction.set(db.collection(DELEGATIONS).document(did), {**d, "revoked_at": _iso(now), "revoked_by": revoker})
    if engine.get("active_delegation_id") == did:
        transaction.update(db.collection(ob.ENGINES).document(engine_id), {"active_delegation_id": None})
    ob._event(transaction, db, engine_id=engine_id, actor=revoker, actor_role="owner", action="revoke_delegation", target=did, before={"scope": d.get("scope")}, after={"revoked": True},
              ip_hash=ip_hash, request_id=request_id, now=now, extra={"delegation_id": did, "scope": d.get("scope"), "delegate_subscriber_id": d.get("to_subscriber_id"), "replaced": replaced})


def _create_delegation_in(transaction, db, engine_id, sid, to_sid, scope, now, ip_hash, request_id):
    engine_snap = db.collection(ob.ENGINES).document(engine_id).get(transaction=transaction)
    if not engine_snap.exists:
        raise FormError(404, "Not found")
    engine = engine_snap.to_dict() or {}
    if not is_holder(engine, sid):
        raise FormError(403, "Only the final-say owner can delegate final say")      # also ends a delegate delegating further: a delegate is not the holder
    if engine.get("state") != "open":
        raise FormError(409, "This engine is not open for edits")
    if not to_sid or to_sid == sid:
        raise FormError(400, "Final say can only be delegated to the other owner")
    if to_sid == generate_subscriber_id(ADMIN_SUBSCRIBER_EMAIL):
        raise FormError(400, "Final say can only be delegated to the other owner")
    m = db.collection(ob.MEMBERS).document(ob.member_id(engine_id, to_sid)).get(transaction=transaction)
    md = m.to_dict() if m.exists else None
    if not md or md.get("status") != "active" or md.get("role") != "owner" or md.get("engine_id") != engine_id or md.get("subscriber_id") != to_sid:
        raise FormError(400, "Final say can only be delegated to the other owner")
    old_id = engine.get("active_delegation_id")
    old = None
    if old_id:
        osnap = db.collection(DELEGATIONS).document(old_id).get(transaction=transaction)
        old = osnap.to_dict() if osnap.exists else None
    # reads done; writes follow. At most ONE delegation is active per engine: making a new one ends the old one in the same transaction.
    if old and not old.get("revoked_at"):
        _revoke_doc(transaction, db, engine_id, old_id, old, engine, sid, now, ip_hash, request_id, replaced=True)
    did = uuid.uuid4().hex
    doc = {"engine_id": engine_id, "from_subscriber_id": sid, "to_subscriber_id": to_sid, "scope": scope, "created_at": _iso(now), "revoked_at": None, "revoked_by": None}
    transaction.set(db.collection(DELEGATIONS).document(did), doc)
    transaction.update(db.collection(ob.ENGINES).document(engine_id), {"active_delegation_id": did})
    ob._event(transaction, db, engine_id=engine_id, actor=sid, actor_role="owner", action="delegate", target=did, before=None, after={"scope": scope}, ip_hash=ip_hash,
              request_id=request_id, now=now, extra={"delegation_id": did, "scope": scope, "delegate_subscriber_id": to_sid})
    return did, doc, engine


def create_delegation(db, *, engine_id: str, subscriber_id: str, to_subscriber_id: Optional[str], scope: Any, now: Optional[datetime] = None, ip_hash: Optional[str] = None,
                      request_id: Optional[str] = None) -> dict:
    """Delegate final say to the other owner, for 'all' sections or a list. The holder only; one active delegation per engine (a new one replaces the old)."""
    scope = scope_clean(scope)
    did, doc, engine = ob._run_in_transaction(db, _create_delegation_in, db, engine_id, subscriber_id, to_subscriber_id, scope, now or ob._utcnow(), ip_hash, request_id)
    return delegation_view(doc, did, {"via": "member", "subscriber_id": subscriber_id}, {**engine, "active_delegation_id": did})


def _revoke_in(transaction, db, engine_id, sid, did, now, ip_hash, request_id):
    engine_snap = db.collection(ob.ENGINES).document(engine_id).get(transaction=transaction)
    if not engine_snap.exists:
        raise FormError(404, "Not found")
    engine = engine_snap.to_dict() or {}
    if not is_holder(engine, sid):
        raise FormError(403, "Only the final-say owner can revoke a delegation")
    snap = db.collection(DELEGATIONS).document(did).get(transaction=transaction)
    d = snap.to_dict() if snap.exists else None
    if not d or d.get("engine_id") != engine_id:
        raise FormError(404, "Not found")
    if d.get("revoked_at"):
        return d, engine
    _revoke_doc(transaction, db, engine_id, did, d, engine, sid, now, ip_hash, request_id)
    return {**d, "revoked_at": _iso(now), "revoked_by": sid}, {**engine, "active_delegation_id": None}


def revoke_delegation(db, *, engine_id: str, subscriber_id: str, delegation_id: str, now: Optional[datetime] = None, ip_hash: Optional[str] = None,
                      request_id: Optional[str] = None) -> dict:
    """Revoke a delegation (the holder only). Takes effect on the delegate's very next action. Idempotent: revoking a revoked delegation changes nothing."""
    if not isinstance(delegation_id, str) or len(delegation_id) != 32 or any(c not in "0123456789abcdef" for c in delegation_id):
        raise FormError(404, "Not found")
    d, engine = ob._run_in_transaction(db, _revoke_in, db, engine_id, subscriber_id, delegation_id, now or ob._utcnow(), ip_hash, request_id)
    return delegation_view(d, delegation_id, {"via": "member", "subscriber_id": subscriber_id}, engine)


def list_delegations(db, *, engine_id: str, subscriber_id: str) -> List[dict]:
    """The holder sees every delegation of the engine (newest first, capped); a delegate sees only the ones that name them; any other owner sees none."""
    engine = form._engine(db, engine_id)
    viewer = {"via": "member", "subscriber_id": subscriber_id}
    holder = is_holder(engine, subscriber_id)
    rows = []
    for snap in db.collection(DELEGATIONS).where("engine_id", "==", engine_id).stream():
        d = snap.to_dict() or {}
        if holder or d.get("to_subscriber_id") == subscriber_id:
            rows.append((d.get("created_at") or "", snap.id, d))
    rows.sort(key=lambda r: (r[0], r[1]), reverse=True)
    return [delegation_view(d, did, viewer, engine) for _, did, d in rows[:LIST_CAP]]


# ---- notifications ------------------------------------------------------------------------------------------------------------------------------------
def _set_notifications_in(transaction, db, engine_id, sid, on, now, ip_hash, request_id):
    ref = db.collection(ob.MEMBERS).document(ob.member_id(engine_id, sid))
    snap = ref.get(transaction=transaction)
    m = snap.to_dict() if snap.exists else None
    if not m or m.get("status") != "active":
        raise FormError(404, "Not found")
    before = m.get("notifications_email", True) is not False
    transaction.update(ref, {"notifications_email": on})
    ob._event(transaction, db, engine_id=engine_id, actor=sid, actor_role="owner", action="notifications", target="self", before={"email": before}, after={"email": on},
              ip_hash=ip_hash, request_id=request_id, now=now, extra={"email": on})


def set_notifications(db, *, engine_id: str, subscriber_id: str, email: bool, now: Optional[datetime] = None, ip_hash: Optional[str] = None,
                      request_id: Optional[str] = None) -> bool:
    """An owner's own switch for the e-mails about final sections (on by default). Audited."""
    if not isinstance(email, bool):
        raise FormError(400, "email must be true or false")
    ob._run_in_transaction(db, _set_notifications_in, db, engine_id, subscriber_id, email, now or ob._utcnow(), ip_hash, request_id)
    return email


def _reconcile_in(transaction, db, engine_id, section, reopened_from, now):
    sec_ref = form._section_ref(db, engine_id, section)
    sec_snap = sec_ref.get(transaction=transaction)
    sec = sec_snap.to_dict() if sec_snap.exists else {"engine_id": engine_id, "section": section, "status": "draft", "revision": 1}
    status = sec.get("status", "draft")
    items = form._items_of(db, engine_id, section, transaction=transaction)
    ready = form.section_counts(items, form._disagreed_ids(form._comments_of(db, engine_id, section, transaction=transaction)), status)["ready"]
    flag = bool(sec.get("ready_notified"))
    send = False
    if status != "draft":
        new = flag                                       # a final, approved or sent-back section is not "becoming ready"
    elif reopened_from in REOPEN_MAIL_FROM:
        new = ready                                      # the re-open mail covers a section that is still ready: one mail, not two
    else:
        send, new = ready and not flag, ready
    if new != flag:
        transaction.set(sec_ref, {**sec, "ready_notified": new})
    return send


def _addresses(db, engine_id: str, engine: dict, section: str) -> List[str]:
    """Where to send a mail about this section: the final-say holder and, if a delegation covers the section, the delegate; not an owner who switched them off."""
    ids = [engine.get("final_say_subscriber_id")]
    d = active_delegation(None, db, engine_id, engine)
    if d and covers(d.get("scope"), section):
        ids.append(d.get("to_subscriber_id"))
    out = []
    for sid in dict.fromkeys(i for i in ids if i):
        m = ob.active_membership(db, engine_id, sid)
        if not m or m.get("notifications_email", True) is False:
            continue
        snap = db.collection("subscribers").document(sid).get()
        address = ((snap.to_dict() or {}).get("email") if snap.exists else None) or ""
        if address:
            out.append(address)
    return out


def plan_notifications(db, *, engine_id: str, section: str, reopened_from: Optional[str], now: Optional[datetime] = None) -> List[Dict[str, Any]]:
    """Decide which mails this change calls for, and record that a 'ready' mail is going out (so it is not repeated while the section stays ready). Returns
    [{kind: 'reopened'|'ready', engine_label, section_title, to: [addresses]}]. The caller sends them AFTER the change has committed."""
    if section not in tpl.SECTION_KEYS:
        return []
    now = now or ob._utcnow()
    engine = form._engine(db, engine_id)
    kinds = []
    if reopened_from in REOPEN_MAIL_FROM:
        kinds.append("reopened")
    if ob._run_in_transaction(db, _reconcile_in, db, engine_id, section, reopened_from, now):
        kinds.append("ready")
    plans = []
    for kind in kinds:
        to = _addresses(db, engine_id, engine, section)
        if to:
            plans.append({"kind": kind, "engine_label": engine.get("label") or engine_id, "section_title": tpl.section_title(section), "to": to})
    return plans
