"""The owners' workspace, part 1 (onboarding PR 3a-1; docs/design/ENGINE_ONBOARDING_FORM.md 4.1 to 4.5, 5.6, 5.7): items and sections with an optimistic revision
check, per-answer provenance and history, question add and split with never-reused ids, comment threads with the "disagree" marker, readiness and the progress
tracker. Marking a section final, delegation and notifications are PR 3a-2 (utils/onboarding_gates.py); the pages are 3a-3; approve and reject are 3b.

Every change here writes its onboarding_events record IN THE SAME TRANSACTION as the change (utils/onboarding.py _event): there is no change without a record.
No response carries a subscriber id: authors are shown as 'you', 'advisor', 'other owner' or 'admin'.

"Disagreed" (decided by Gary 2026-11-06): an owner may attach a comment of kind "disagree" to an item; the item counts as disagreed while that comment is
unresolved, and either owner can resolve it. (The design's wording, "two owners gave different values", cannot be computed from one stored value.)
"""
import re
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

from utils import onboarding as ob
from utils import onboarding_template as tpl

SECTIONS_COL, ITEMS, COMMENTS = "onboarding_sections", "onboarding_items", "onboarding_comments"
HISTORY_CAP = 20           # revisions kept on the item (the audit log keeps every prior value)
APPROVED_HISTORY_CAP = 20
LEFT_LIST_CAP = 50
MAX_SPLIT = 5
COMMENT_KINDS = ("comment", "disagree")
STATUSES = ("draft", "final", "approved", "rejected")


class FormError(Exception):
    def __init__(self, status: int, message: str, **extra: Any):
        super().__init__(message)
        self.status, self.message, self.extra = status, message, extra


def item_key(engine_id: str, section: str, item_id: str) -> str:
    return f"{engine_id}__{section}__{item_id}"


def section_doc_id(engine_id: str, section: str) -> str:
    return f"{engine_id}__{section}"


def _iso(now: datetime) -> str:
    return now.isoformat()


# ---- how an author is shown (never an id) ----------------------------------------------------------------------------------------------------------
def author_label(author: Optional[str], viewer: dict, engine: dict) -> str:
    if author == "admin":
        return "admin"
    if viewer.get("via") == "member" and author and author == viewer.get("subscriber_id"):
        return "you"
    if author and author == engine.get("final_say_subscriber_id"):
        return "advisor"
    return "other owner" if viewer.get("via") == "member" else "owner"


def public_comment(c: dict, viewer: dict, engine: dict, comment_id: Optional[str] = None) -> dict:
    return {"comment_id": comment_id or c.get("comment_id"), "item_id": c.get("item_id"), "kind": c.get("kind", "comment"), "body": c.get("body", ""),
            "author": author_label(c.get("author_subscriber_id"), viewer, engine), "role": c.get("author_role"), "created_at": c.get("created_at"),
            "resolved": bool(c.get("resolved")), "resolved_by": author_label(c.get("resolved_by"), viewer, engine) if c.get("resolved_by") else None,
            "resolved_at": c.get("resolved_at")}


def public_item(doc: dict, viewer: dict, engine: dict, comments: Optional[List[dict]] = None) -> dict:
    comments = comments or []
    return {"item_id": doc.get("item_id"), "section": doc.get("section"), "type": doc.get("type"), "choice": doc.get("choice"), "value": doc.get("value"),
            "context": doc.get("context") or {}, "revision": doc.get("revision", 0), "answered": doc.get("revision", 0) >= 1,
            "author": author_label(doc.get("author_subscriber_id"), viewer, engine) if doc.get("author_subscriber_id") else None, "updated_at": doc.get("updated_at"),
            "comment_count": doc.get("comment_count", 0), "disagreed": any(c.get("kind") == "disagree" and not c.get("resolved") for c in comments),
            "history": [{"revision": h.get("revision"), "choice": h.get("choice"), "value": h.get("value"), "author": author_label(h.get("author"), viewer, engine),
                         "at": h.get("at")} for h in (doc.get("history") or [])],
            "comments": [public_comment(c, viewer, engine) for c in comments]}


# ---- lookups -----------------------------------------------------------------------------------------------------------------------------------
def _engine(db, engine_id: str) -> dict:
    snap = db.collection(ob.ENGINES).document(engine_id).get()
    if not snap.exists:
        raise FormError(404, "Not found")
    return snap.to_dict() or {}


def find_item(db, engine_id: str, item_id: str) -> Optional[dict]:
    """The stored item with this id in this engine (item ids are unique per engine), or None."""
    if not isinstance(item_id, str) or not tpl.ID_RE.match(item_id):
        return None
    for d in db.collection(ITEMS).where("engine_id", "==", engine_id).where("item_id", "==", item_id).limit(1).stream():
        return d.to_dict()
    return None


def _items_of(db, engine_id: str, section: Optional[str] = None, transaction=None) -> List[dict]:
    q = db.collection(ITEMS).where("engine_id", "==", engine_id)
    if section:
        q = q.where("section", "==", section)
    return sorted((d.to_dict() for d in q.stream(transaction=transaction)), key=lambda x: (x.get("order", 0), x.get("item_id", "")))


def _comments_of(db, engine_id: str, section: Optional[str] = None, transaction=None) -> List[dict]:
    q = db.collection(COMMENTS).where("engine_id", "==", engine_id)
    if section:
        q = q.where("section", "==", section)
    out = []
    for d in q.stream(transaction=transaction):
        c = d.to_dict()
        c["comment_id"] = d.id
        out.append(c)
    return sorted(out, key=lambda c: c.get("created_at", ""))


def _section_docs(db, engine_id: str) -> Dict[str, dict]:
    return {(d.to_dict() or {}).get("section"): d.to_dict() for d in db.collection(SECTIONS_COL).where("engine_id", "==", engine_id).stream()}


def section_status(db, engine_id: str, section: str) -> str:
    snap = _section_ref(db, engine_id, section).get()
    return (snap.to_dict() or {}).get("status", "draft") if snap.exists else "draft"


def item_view(db, engine_id: str, doc: dict, viewer: dict) -> dict:
    """The public form of one stored item, with its comments (so 'disagreed' is true to the data, not assumed)."""
    comments = [c for c in _comments_of(db, engine_id, doc.get("section")) if c.get("item_id") == doc.get("item_id")]
    return public_item(doc, viewer, _engine(db, engine_id), comments)


# ---- readiness and the section view ---------------------------------------------------------------------------------------------------------------
def content_sha256(items: List[dict]) -> str:
    """A hash of a section's content: every item's id, revision, choice and value. (Approval, in 3b, is of a section revision and this hash.)"""
    return ob._sha(sorted([[i.get("item_id"), i.get("revision", 0), i.get("choice"), i.get("value")] for i in items], key=lambda r: str(r[0])))


def section_counts(items: List[dict], disagreed_ids: set, status: str) -> dict:
    n = len(items)
    disagreed = sum(1 for i in items if i.get("item_id") in disagreed_ids)
    answered = sum(1 for i in items if i.get("revision", 0) >= 1 and i.get("item_id") not in disagreed_ids)
    open_ = n - disagreed - answered
    return {"items": n, "open": open_, "answered": answered, "disagreed": disagreed, "final": n if status == "final" else 0, "approved": n if status == "approved" else 0,
            # ready (design 4.5): every item answered and no open disagreement. A section with no items is not ready: there is nothing to finalise.
            "ready": n >= 1 and open_ == 0 and disagreed == 0}


def _disagreed_ids(comments: List[dict]) -> set:
    return {c.get("item_id") for c in comments if c.get("kind") == "disagree" and not c.get("resolved")}


def review_view(sec: dict, status: str) -> dict:
    """What Gary's review left on a section, for the owners (and Gary) to read: the send-back note while the section is a draft that was sent back (until it is next
    marked final), and the approval (when, which revision, his note) while it is approved. Plain text; never an id."""
    sent_back = status == "draft" and bool(sec.get("rejection_note"))
    return {"rejection_note": sec.get("rejection_note") if sent_back else None, "rejected_at": sec.get("rejected_at") if sent_back else None,
            "approved_at": sec.get("approved_at") if status == "approved" else None, "approver_note": sec.get("approver_note") if status == "approved" else None,
            "approved_revision": sec.get("approved_revision") if status == "approved" else None}


def get_section(db, engine_id: str, section: str, viewer: dict) -> dict:
    if section not in tpl.SECTION_KEYS:
        raise FormError(404, "Not found")
    engine = _engine(db, engine_id)
    items, comments = _items_of(db, engine_id, section), _comments_of(db, engine_id, section)
    sec = _section_docs(db, engine_id).get(section) or {}
    status = sec.get("status", "draft")
    by_item: Dict[str, List[dict]] = {}
    for c in comments:
        by_item.setdefault(c.get("item_id"), []).append(c)
    meta = next(s for s in tpl.SECTIONS if s["key"] == section)
    return {"section": {"key": section, "title": meta["title"], "design": meta["design"], "status": status, "revision": sec.get("revision", 1),
                        "content_sha256": content_sha256(items), "reopened_by": author_label(sec.get("reopened_by"), viewer, engine) if sec.get("reopened_by") else None,
                        **review_view(sec, status),
                        **section_counts(items, _disagreed_ids(comments), status)},
            "items": [public_item(i, viewer, engine, by_item.get(i.get("item_id"))) for i in items], "template_version": tpl.TEMPLATE_VERSION}


def get_progress(db, engine_id: str, viewer: dict) -> dict:
    """Per section: items open / answered / disagreed / final / approved, whether it is ready; a 'what is left' list; and the 'waiting on' line."""
    items, comments, sec_docs = _items_of(db, engine_id), _comments_of(db, engine_id), _section_docs(db, engine_id)
    disagreed = _disagreed_ids(comments)
    rows, left = [], []
    for meta in tpl.SECTIONS:
        its = [i for i in items if i.get("section") == meta["key"]]
        status = (sec_docs.get(meta["key"]) or {}).get("status", "draft")
        rows.append({"key": meta["key"], "title": meta["title"], "status": status, **section_counts(its, disagreed, status),
                     "rejection_note": review_view(sec_docs.get(meta["key"]) or {}, status)["rejection_note"]})
        for i in its:
            if i.get("item_id") in disagreed:
                left.append({"section": meta["key"], "item_id": i["item_id"], "reason": "disagreed"})
            elif i.get("revision", 0) < 1:
                left.append({"section": meta["key"], "item_id": i["item_id"], "reason": "unanswered"})
    waiting = []
    if any(r["ready"] and r["status"] in ("draft", "rejected") for r in rows):
        waiting.append(("final_say", "the final-say owner to mark ready sections final"))
    if any(r["status"] == "final" for r in rows):
        waiting.append(("admin", "Gary to approve or reject finished sections"))
    if any(r["items"] and not r["ready"] and r["status"] in ("draft", "rejected") for r in rows):
        waiting.append(("owners", "the owners to answer %d item(s) and resolve %d disagreement(s)" % (
            sum(r["open"] for r in rows if r["status"] in ("draft", "rejected")), sum(r["disagreed"] for r in rows if r["status"] in ("draft", "rejected")))))
    return {"template_version": tpl.TEMPLATE_VERSION, "sections": rows, "left": left[:LEFT_LIST_CAP], "left_total": len(left),
            "waiting_on": {"who": [w[0] for w in waiting], "line": ("Waiting on " + "; ".join(w[1] for w in waiting)) if waiting else "Nothing is waiting."}}


# ---- editing an item (optimistic concurrency) --------------------------------------------------------------------------------------------------------
def _check_choice_transition(cur: Optional[str], new: Optional[str]) -> None:
    if cur == "split":
        raise FormError(409, "A split question can no longer be edited; edit its replacements")
    if new == "split":
        raise FormError(400, "Use the split action to split a question")
    if new == "add" and cur != "add":
        raise FormError(400, "Only a question that was added can have the choice 'add'")
    if cur == "add" and new not in ("add", "drop"):
        raise FormError(400, "An added question can only stay added or be dropped")


def _reopened(sec: dict, actor: str, now: datetime) -> dict:
    """The section document after an edit (design 4.5): a final or rejected section returns to draft; an approved one starts a new draft revision and its
    approved revision stays in approved_history; a draft stays a draft."""
    out = dict(sec)
    status = sec.get("status", "draft")
    out["status"], out["updated_at"] = "draft", _iso(now)
    out.setdefault("revision", 1)
    if status == "approved":
        out["approved_history"] = ((sec.get("approved_history") or []) + [{"revision": sec.get("revision", 1), "content_sha256": sec.get("content_sha256"),
                                                                           "approved_at": sec.get("approved_at")}])[-APPROVED_HISTORY_CAP:]
        out["revision"] = sec.get("revision", 1) + 1
    if status != "draft":
        out["reopened_by"] = actor
        out["final_by"], out["final_via_delegation"], out["final_at"] = None, False, None
    return out


def _section_ref(db, engine_id, section):
    return db.collection(SECTIONS_COL).document(section_doc_id(engine_id, section))


def _save_in(transaction, db, engine_id, section, item_id, sid, value, choice, base_revision, now, ip_hash, request_id, outcome=None):
    engine_snap = db.collection(ob.ENGINES).document(engine_id).get(transaction=transaction)
    item_ref = db.collection(ITEMS).document(item_key(engine_id, section, item_id))
    item_snap = item_ref.get(transaction=transaction)
    sec_ref = _section_ref(db, engine_id, section)
    sec_snap = sec_ref.get(transaction=transaction)
    if not engine_snap.exists or not item_snap.exists:
        raise FormError(404, "Not found")
    engine, item = engine_snap.to_dict() or {}, item_snap.to_dict() or {}
    if engine.get("state") != "open":
        raise FormError(409, "This engine is not open for edits")
    if base_revision != item.get("revision", 0):
        raise FormError(409, "Someone changed this answer since you opened it", current_doc=item)
    _check_choice_transition(item.get("choice"), choice)
    try:
        clean_value, clean_choice = tpl.validate_item(item.get("type"), value, choice)
    except tpl.TemplateError as e:
        raise FormError(400, str(e))
    sec = sec_snap.to_dict() if sec_snap.exists else {"engine_id": engine_id, "section": section, "status": "draft", "revision": 1}
    # All reads are done; every write below is buffered and committed together, or none is.
    history = ((item.get("history") or []) + ([{"revision": item["revision"], "choice": item.get("choice"), "value": item.get("value"),
                                                "value_sha256": ob._sha(item.get("value")), "author": item.get("author_subscriber_id"), "at": item.get("updated_at")}]
                                               if item.get("revision", 0) >= 1 else []))[-HISTORY_CAP:]
    new_item = {**item, "value": clean_value, "choice": clean_choice, "revision": item.get("revision", 0) + 1, "author_subscriber_id": sid, "updated_at": _iso(now),
                "history": history}
    transaction.set(item_ref, new_item)
    new_sec = _reopened(sec, sid, now)
    transaction.set(sec_ref, new_sec)
    if outcome is not None:
        outcome["reopened_from"] = sec.get("status", "draft")          # the notifications (3a-2) need to know a FINAL section was just re-opened
    ob._event(transaction, db, engine_id=engine_id, actor=sid, actor_role="owner", action="item_edit", target=f"{section}/{item_id}", before=item.get("value"), after=clean_value,
              ip_hash=ip_hash, request_id=request_id, now=now, extra={"section": section, "item_id": item_id, "revision": new_item["revision"], "before_value": item.get("value"),
                                                                      "before_choice": item.get("choice"), "choice": clean_choice})
    if sec.get("status", "draft") != "draft":
        ob._event(transaction, db, engine_id=engine_id, actor=sid, actor_role="owner", action="reopen", target=section, before={"status": sec.get("status")},
                  after={"status": "draft"}, ip_hash=ip_hash, request_id=request_id, now=now, extra={"section": section, "from_status": sec.get("status")})
    return new_item


def save_item(db, *, engine_id: str, item_id: str, subscriber_id: str, value: Any, choice: Any, base_revision: int, now: Optional[datetime] = None,
              ip_hash: Optional[str] = None, request_id: Optional[str] = None, outcome: Optional[dict] = None) -> dict:
    """Save one answer. `base_revision` is the revision the owner was looking at: if the stored item has moved on, FormError(409) carries the current item and
    NOTHING is written (a stale save is never silently merged or overwritten). Returns the new stored item."""
    now = now or ob._utcnow()
    found = find_item(db, engine_id, item_id)
    if not found:
        raise FormError(404, "Not found")
    return ob._run_in_transaction(db, _save_in, db, engine_id, found["section"], item_id, subscriber_id, value, choice, base_revision, now, ip_hash, request_id, outcome)


# ---- adding and splitting a question (ids assigned by the system, never reused) -----------------------------------------------------------------------
def _prefix(engine_id: str, engine: dict) -> str:
    p = str(engine.get("question_id_prefix") or engine_id).lower()
    return p if re.match(r"^[a-z0-9][a-z0-9-]{0,40}$", p) else engine_id


def _highest_question_number(db, engine_id: str, prefix: str) -> int:
    """The highest number already used by any question item of this engine (a dropped or split question still counts: ids are never reused)."""
    best = 0
    for d in db.collection(ITEMS).where("engine_id", "==", engine_id).where("type", "==", "question").stream():
        m = re.match(r"^%s-q(\d+)$" % re.escape(prefix), (d.to_dict() or {}).get("item_id", ""))
        if m:
            best = max(best, int(m.group(1)))
    return best


def _new_question_doc(engine_id, item_id, number, value, sid, now, context):
    return {"engine_id": engine_id, "section": "questions", "item_id": item_id, "type": "question", "value": value, "choice": "add", "revision": 1,
            "author_subscriber_id": sid, "updated_at": _iso(now), "comment_count": 0, "history": [], "context": context, "order": number}


def _add_in(transaction, db, engine_id, sid, new_values, split_from, floor, now, ip_hash, request_id, outcome=None):
    engine_snap = db.collection(ob.ENGINES).document(engine_id).get(transaction=transaction)
    if not engine_snap.exists:
        raise FormError(404, "Not found")
    engine = engine_snap.to_dict() or {}
    if engine.get("state") != "open":
        raise FormError(409, "This engine is not open for edits")
    prefix = _prefix(engine_id, engine)
    counter = engine.get("next_question_number")
    n = max(counter if isinstance(counter, int) and not isinstance(counter, bool) else 1, floor + 1)
    orig_ref = orig = None
    if split_from:
        orig_ref = db.collection(ITEMS).document(item_key(engine_id, "questions", split_from))
        snap = orig_ref.get(transaction=transaction)
        orig = snap.to_dict() if snap.exists else None
        if not orig or orig.get("type") != "question" or orig.get("choice") in ("split", "drop"):
            raise FormError(409, "That question cannot be split")
    sec_ref = _section_ref(db, engine_id, "questions")
    sec_snap = sec_ref.get(transaction=transaction)
    sec = sec_snap.to_dict() if sec_snap.exists else {"engine_id": engine_id, "section": "questions", "status": "draft", "revision": 1}
    created = []
    for value in new_values:
        while True:                               # a number is never reused: skip any id that already has a document
            item_id = f"{prefix}-q{n}"
            if not db.collection(ITEMS).document(item_key(engine_id, "questions", item_id)).get(transaction=transaction).exists:
                break
            n += 1
        created.append((item_id, n, value))
        n += 1
    # All reads are done; writes follow.
    for item_id, number, value in created:
        transaction.set(db.collection(ITEMS).document(item_key(engine_id, "questions", item_id)),
                        _new_question_doc(engine_id, item_id, number, value, sid, now, {"split_from": split_from} if split_from else {"added": True}))
    transaction.update(db.collection(ob.ENGINES).document(engine_id), {"next_question_number": n})
    if orig_ref is not None:
        history = ((orig.get("history") or []) + ([{"revision": orig["revision"], "choice": orig.get("choice"), "value": orig.get("value"), "value_sha256": ob._sha(orig.get("value")),
                                                    "author": orig.get("author_subscriber_id"), "at": orig.get("updated_at")}] if orig.get("revision", 0) >= 1 else []))[-HISTORY_CAP:]
        transaction.set(orig_ref, {**orig, "choice": "split", "value": {**(orig.get("value") or {}), "split_into": [c[0] for c in created]}, "revision": orig.get("revision", 0) + 1,
                                   "author_subscriber_id": sid, "updated_at": _iso(now), "history": history})
    transaction.set(sec_ref, _reopened(sec, sid, now))
    if outcome is not None:
        outcome["reopened_from"] = sec.get("status", "draft")
    ids = [c[0] for c in created]
    ob._event(transaction, db, engine_id=engine_id, actor=sid, actor_role="owner", action="question_split" if split_from else "question_add", target=split_from or ids[0],
              before=None, after={"new": ids}, ip_hash=ip_hash, request_id=request_id, now=now, extra={"section": "questions", "new_ids": ids})
    if sec.get("status", "draft") != "draft":
        ob._event(transaction, db, engine_id=engine_id, actor=sid, actor_role="owner", action="reopen", target="questions", before={"status": sec.get("status")},
                  after={"status": "draft"}, ip_hash=ip_hash, request_id=request_id, now=now, extra={"section": "questions", "from_status": sec.get("status")})
    return ids


def add_questions(db, *, engine_id: str, subscriber_id: str, action: str, wordings: List[dict], from_item: Optional[str] = None, now: Optional[datetime] = None,
                  ip_hash: Optional[str] = None, request_id: Optional[str] = None, outcome: Optional[dict] = None) -> List[str]:
    """Add one question, or split one into two or more. The system assigns the ids: '<prefix>-qN', the next free number from a counter on the engine record that
    only goes up. Each new question carries the choice 'add', its own wording and centrality, and no terms yet."""
    now = now or ob._utcnow()
    if action not in ("add", "split"):
        raise FormError(400, "action must be add or split")
    if action == "add" and len(wordings) != 1:
        raise FormError(400, "add takes exactly one question")
    if action == "split" and not (2 <= len(wordings) <= MAX_SPLIT):
        raise FormError(400, f"split takes from 2 to {MAX_SPLIT} new questions")
    if action == "split" and (not isinstance(from_item, str) or not tpl.ID_RE.match(from_item)):
        raise FormError(400, "split needs the question to split")
    values = []
    for w in wordings:
        try:
            values.append(tpl.validate_item("question", {"wording": (w or {}).get("wording"), "centrality": (w or {}).get("centrality"), "terms": []}, "add")[0])
        except (tpl.TemplateError, AttributeError) as e:
            raise FormError(400, str(e))
    engine = _engine(db, engine_id)
    floor = _highest_question_number(db, engine_id, _prefix(engine_id, engine))
    return ob._run_in_transaction(db, _add_in, db, engine_id, subscriber_id, values, from_item if action == "split" else None, floor, now, ip_hash, request_id, outcome)


# ---- adding a keyword, horizon or mute entry (ids assigned by the system, never reused; a fourth addition to design 5.7) -----------------------------------
MAX_KEYWORD_ENTRIES = 500       # every keyword item of an engine, loaded or added


def _keyword_numbers(db, engine_id: str, prefix: str):
    """(how many keyword items the engine has, the highest number used by an id of the form '<prefix>-kN'). A dropped entry still counts: ids are never reused."""
    count, best = 0, 0
    for d in db.collection(ITEMS).where("engine_id", "==", engine_id).where("type", "==", "keyword_entry").stream():
        count += 1
        m = re.match(r"^%s-k(\d+)$" % re.escape(prefix), (d.to_dict() or {}).get("item_id", ""))
        if m:
            best = max(best, int(m.group(1)))
    return count, best


def _add_entry_in(transaction, db, engine_id, sid, value, floor, now, ip_hash, request_id, outcome=None):
    engine_snap = db.collection(ob.ENGINES).document(engine_id).get(transaction=transaction)
    if not engine_snap.exists:
        raise FormError(404, "Not found")
    engine = engine_snap.to_dict() or {}
    if engine.get("state") != "open":
        raise FormError(409, "This engine is not open for edits")
    prefix = _prefix(engine_id, engine)
    counter = engine.get("next_entry_number")
    n = max(counter if isinstance(counter, int) and not isinstance(counter, bool) else 1, floor + 1)
    while db.collection(ITEMS).document(item_key(engine_id, "keywords", f"{prefix}-k{n}")).get(transaction=transaction).exists:      # a number is never reused
        n += 1
    item_id = f"{prefix}-k{n}"
    sec_ref = _section_ref(db, engine_id, "keywords")
    sec_snap = sec_ref.get(transaction=transaction)
    sec = sec_snap.to_dict() if sec_snap.exists else {"engine_id": engine_id, "section": "keywords", "status": "draft", "revision": 1}
    # All reads are done; writes follow.
    transaction.set(db.collection(ITEMS).document(item_key(engine_id, "keywords", item_id)),
                    {"engine_id": engine_id, "section": "keywords", "item_id": item_id, "type": "keyword_entry", "value": value, "choice": "add", "revision": 1,
                     "author_subscriber_id": sid, "updated_at": _iso(now), "comment_count": 0, "history": [], "context": {"added": True}, "order": 1000 + n})
    transaction.update(db.collection(ob.ENGINES).document(engine_id), {"next_entry_number": n + 1})
    transaction.set(sec_ref, _reopened(sec, sid, now))
    if outcome is not None:
        outcome["reopened_from"] = sec.get("status", "draft")
    ob._event(transaction, db, engine_id=engine_id, actor=sid, actor_role="owner", action="entry_add", target=item_id, before=None, after={"list": value["list"]}, ip_hash=ip_hash,
              request_id=request_id, now=now, extra={"section": "keywords", "item_id": item_id, "list": value["list"]})
    if sec.get("status", "draft") != "draft":
        ob._event(transaction, db, engine_id=engine_id, actor=sid, actor_role="owner", action="reopen", target="keywords", before={"status": sec.get("status")},
                  after={"status": "draft"}, ip_hash=ip_hash, request_id=request_id, now=now, extra={"section": "keywords", "from_status": sec.get("status")})
    return item_id


def add_entry(db, *, engine_id: str, subscriber_id: str, list_name: Any, text: Any, now: Optional[datetime] = None, ip_hash: Optional[str] = None,
              request_id: Optional[str] = None, outcome: Optional[dict] = None) -> str:
    """Create a new keyword, horizon, mute (or other §2.3 list) entry with the choice 'add'. The system assigns the id: '<prefix>-kN', the next free number from a
    counter on the engine record that only goes up. The text is validated and capped like any entry; an engine holds at most MAX_KEYWORD_ENTRIES of them."""
    now = now or ob._utcnow()
    try:
        value = tpl.validate_item("keyword_entry", {"list": list_name, "text": text}, "add")[0]
    except tpl.TemplateError as e:
        raise FormError(400, str(e))
    engine = _engine(db, engine_id)
    count, floor = _keyword_numbers(db, engine_id, _prefix(engine_id, engine))
    if count >= MAX_KEYWORD_ENTRIES:
        raise FormError(409, f"This engine already has {MAX_KEYWORD_ENTRIES} keyword entries")
    return ob._run_in_transaction(db, _add_entry_in, db, engine_id, subscriber_id, value, floor, now, ip_hash, request_id, outcome)


# ---- comments ----------------------------------------------------------------------------------------------------------------------------------
def _add_comment_in(transaction, db, engine_id, section, item_id, comment_id, doc, viewer_actor, now, ip_hash, request_id):
    item_ref = db.collection(ITEMS).document(item_key(engine_id, section, item_id))
    snap = item_ref.get(transaction=transaction)
    if not snap.exists:
        raise FormError(404, "Not found")
    item = snap.to_dict() or {}
    transaction.set(db.collection(COMMENTS).document(comment_id), doc)
    transaction.update(item_ref, {"comment_count": item.get("comment_count", 0) + 1})
    ob._event(transaction, db, engine_id=engine_id, actor=viewer_actor, actor_role=doc["author_role"], action="comment", target=f"{section}/{item_id}", before=None,
              after={"kind": doc["kind"], "body_sha256": ob._sha(doc["body"])}, ip_hash=ip_hash, request_id=request_id, now=now,
              extra={"section": section, "item_id": item_id, "kind": doc["kind"], "comment_id": comment_id})


def add_comment(db, *, engine_id: str, item_id: str, viewer: dict, body: Any, kind: str = "comment", now: Optional[datetime] = None, ip_hash: Optional[str] = None,
                request_id: Optional[str] = None) -> dict:
    """Add a plain-text comment to an item. An owner may mark it kind 'disagree'; the administrator may comment but never disagree (it would block readiness)."""
    now = now or ob._utcnow()
    if kind not in COMMENT_KINDS:
        raise FormError(400, "kind must be comment or disagree")
    is_admin = viewer.get("via") == "admin"
    if is_admin and kind == "disagree":
        raise FormError(400, "Only an owner can mark a disagreement")
    try:
        text = tpl.clean_text(body, tpl.COMMENT_CAP, "the comment", required=True)
    except tpl.TemplateError as e:
        raise FormError(400, str(e))
    found = find_item(db, engine_id, item_id)
    if not found:
        raise FormError(404, "Not found")
    actor = "admin" if is_admin else viewer["subscriber_id"]
    comment_id = uuid.uuid4().hex
    doc = {"engine_id": engine_id, "section": found["section"], "item_id": item_id, "thread_id": f"{found['section']}__{item_id}", "author_subscriber_id": actor,
           "author_role": "admin" if is_admin else "owner", "kind": kind, "body": text, "created_at": _iso(now), "resolved": False}
    ob._run_in_transaction(db, _add_comment_in, db, engine_id, found["section"], item_id, comment_id, doc, actor, now, ip_hash, request_id)
    return public_comment(doc, viewer, _engine(db, engine_id), comment_id)


def _resolve_in(transaction, db, engine_id, comment_id, sid, now, ip_hash, request_id):
    ref = db.collection(COMMENTS).document(comment_id)
    snap = ref.get(transaction=transaction)
    c = snap.to_dict() if snap.exists else None
    if not c or c.get("engine_id") != engine_id:
        raise FormError(404, "Not found")
    if c.get("resolved"):
        return c
    new = {**c, "resolved": True, "resolved_by": sid, "resolved_at": _iso(now)}
    transaction.set(ref, new)
    ob._event(transaction, db, engine_id=engine_id, actor=sid, actor_role="owner", action="comment_resolve", target=f"{c.get('section')}/{c.get('item_id')}", before={"resolved": False},
              after={"resolved": True}, ip_hash=ip_hash, request_id=request_id, now=now, extra={"section": c.get("section"), "item_id": c.get("item_id"), "kind": c.get("kind"),
                                                                                              "comment_id": comment_id})
    return new


def resolve_comment(db, *, engine_id: str, comment_id: str, subscriber_id: str, now: Optional[datetime] = None, ip_hash: Optional[str] = None,
                    request_id: Optional[str] = None) -> dict:
    """Resolve a comment (either owner may). Resolving a 'disagree' comment ends the item's disagreement. Idempotent."""
    now = now or ob._utcnow()
    if not isinstance(comment_id, str) or not re.match(r"^[0-9a-f]{32}$", comment_id):
        raise FormError(404, "Not found")
    c = ob._run_in_transaction(db, _resolve_in, db, engine_id, comment_id, subscriber_id, now, ip_hash, request_id)
    return public_comment(c, {"via": "member", "subscriber_id": subscriber_id}, _engine(db, engine_id), comment_id)
