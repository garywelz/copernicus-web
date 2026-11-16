"""The review of an engine's hold list (onboarding PR 4b-2a; docs/design/ENGINE_ONBOARDING_FORM.md 2.5, 5.6, 5.7).

TWO DOCUMENTS PER PAPER. The DECISION is an ordinary item (`onboarding_items`, type `candidate_decision`, section `review`): keep, drop or unsure, with a comment.
So readiness, Mark final, approval, the diff and the bundle work on it with no special case. The PAPER is the `onboarding_candidates` document the loader wrote,
which also holds its abstract once scripts/onboarding/fetch_abstracts.py has run.

ABSTRACTS LEAVE THE SERVER BY ONE ROUTE ONLY: `review_view` below (GET .../review), to a member of that engine or the administrator. An abstract is never part
of an item, so it cannot enter a section view, a diff, a bundle or the review dashboard.

BULK MARKING is all or nothing: up to BULK_MAX papers get one choice in ONE transaction. Each paper is sent with the revision the owner was looking at; if any
one has moved on, NOTHING is written and the refusal names the papers. A paper that already has the choice is left as it is (no new revision). Each paper keeps
its own comment. One `review_bulk` event is written in the same transaction.

THE WRONG-PAPER GUARD (`title_resembles`): the abstract fetch asks a registry about the identifier in the hold list. If the registry's title does not resemble
the hold list's title, the identifier may point at a different paper: the state is `title_mismatch`, the paper shows as unresolved, and the abstract is shown
with the registry's own title beside it and a plain warning.

FILL ONLY WHAT IS MISSING (`needs_fetch`, `fetch_update`): a paper that has an abstract is never fetched or written again; a later run can only add.
"""
import difflib
import re
from datetime import datetime
from typing import Any, Dict, List, Optional

from utils import onboarding as ob
from utils import onboarding_form as form
from utils import onboarding_template as tpl
from utils.onboarding_form import FormError

CANDIDATES = "onboarding_candidates"
SECTION = "review"
ITEM_TYPE = "candidate_decision"
BULK_MAX = 100
STATES = ("found", "no_abstract", "title_mismatch", "not_found", "unavailable")
RESOLVED = ("found",)                       # every other state, and a paper not fetched yet, is "unresolved": no abstract we can stand behind
MISMATCH_WARNING = ("The registry's record for this identifier has a different title, shown here. This abstract may belong to a different paper. "
                    "Please check before relying on it.")
_BRACKETS = re.compile(r"\[[^\]]{0,80}\]")
_NOT_WORD = re.compile(r"[^\w]+", re.UNICODE)


# ---- the wrong-paper guard -----------------------------------------------------------------------------------------------------------------------------
def _norm_title(text: Any) -> str:
    return " ".join(_NOT_WORD.sub(" ", _BRACKETS.sub(" ", text if isinstance(text, str) else "")).casefold().replace("_", " ").split())


def title_resembles(ours: Any, theirs: Any) -> bool:
    """Do these two titles look like the same paper? Case, punctuation and a bracketed reviewer's tag are ignored. True when one is the start of the other (a
    hold list may cut a long title short), or the two are close as text, or they share most of their words. Two empty titles do not resemble each other."""
    a, b = _norm_title(ours), _norm_title(theirs)
    if not a or not b:
        return False
    if a == b:
        return True
    short, long_ = sorted((a, b), key=len)
    if len(short) >= 20 and long_.startswith(short):
        return True
    if difflib.SequenceMatcher(None, a, b).ratio() >= 0.8:
        return True
    wa, wb = set(a.split()), set(b.split())
    return len(wa) >= 4 and len(wb) >= 4 and len(wa & wb) / len(wa | wb) >= 0.7


# ---- the abstract fetch: what to ask for and what to store (used by scripts/onboarding/fetch_abstracts.py) -----------------------------------------------
def needs_fetch(cand: dict) -> bool:
    """A paper is fetched only while it has no abstract. One that has an abstract (found, or shown under a title-mismatch warning) is never touched again."""
    return not (isinstance(cand.get("abstract"), str) and cand["abstract"].strip())


def fetch_update(cand: dict, result: dict, now_iso: str) -> Optional[Dict[str, Any]]:
    """The fields to set on a candidate after one lookup (utils/onboarding_lookup.lookup's result), or None when nothing should be written. It can only ADD: it
    is None for a paper that already has an abstract, and a lookup that learned nothing (`not_found`, `unavailable`) never replaces a registry record already
    stored by an earlier run."""
    if not needs_fetch(cand):
        return None
    rec = (result.get("results") or [None])[0] if result.get("state") == "found" else None
    if rec is None:
        state = result.get("state") if result.get("state") in ("not_found", "unavailable") else "unavailable"
        if cand.get("registry_record"):
            return None
        return None if cand.get("lookup_state") == state else {"lookup_state": state, "abstract_fetched_at": now_iso}
    ours = (cand.get("flags") or {}).get("title")
    abstract = rec.get("abstract") or ""
    state = "title_mismatch" if not title_resembles(ours, rec.get("title")) else ("found" if abstract else "no_abstract")
    out = {"lookup_state": state, "abstract_fetched_at": now_iso,
           "registry_record": {"title": rec.get("title") or "", "authors": list(rec.get("authors") or []), "year": rec.get("year"),
                               "identifiers": dict(rec.get("identifiers") or {}), "sources": dict(rec.get("sources") or {})}}
    if abstract:
        out["abstract"], out["abstract_source"] = abstract, (rec.get("sources") or {}).get("abstract")
    return out


def _apply_abstracts_in(transaction, db, engine_id, updates, now, request_id):
    """ONE transaction for a whole run: every candidate is read again here, and a field is written only if the paper STILL has no abstract. One `abstract_fetch`
    event carries the counts and the candidate ids by state (ids and states only, never a title or an abstract)."""
    engine_ref = db.collection(ob.ENGINES).document(engine_id)
    if not engine_ref.get(transaction=transaction).exists:
        raise FormError(404, "Not found")
    reads = [(cid, db.collection(CANDIDATES).document(cid), fields) for cid, fields in updates.items()]
    current = [(cid, ref, fields, ref.get(transaction=transaction)) for cid, ref, fields in reads]
    written: Dict[str, List[str]] = {}
    skipped = []
    for cid, ref, fields, snap in current:
        cand = snap.to_dict() if snap.exists else None
        if not cand or cand.get("engine_id") != engine_id or not needs_fetch(cand):
            skipped.append(cid)
            continue
        transaction.update(ref, fields)
        written.setdefault(fields["lookup_state"], []).append(cid)
    if written:
        ob._event(transaction, db, engine_id=engine_id, actor="admin", actor_role="admin", action="abstract_fetch", target=SECTION, before=None,
                  after={k: len(v) for k, v in written.items()}, ip_hash=None, request_id=request_id, now=now,
                  extra={"section": SECTION, "counts": {k: len(v) for k, v in written.items()}, "candidates": written, "skipped": skipped})
    return {"written": written, "skipped": skipped}


def apply_abstracts(db, *, engine_id: str, updates: Dict[str, Dict[str, Any]], now: Optional[datetime] = None, request_id: Optional[str] = None) -> Dict[str, Any]:
    return ob._run_in_transaction(db, _apply_abstracts_in, db, engine_id, updates, now or ob._utcnow(), request_id)


# ---- the review view (the only place an abstract is returned) -------------------------------------------------------------------------------------------
def _candidates(db, engine_id: str) -> Dict[str, dict]:
    return {d.id: (d.to_dict() or {}) for d in db.collection(CANDIDATES).where("engine_id", "==", engine_id).stream()}


def _paper(item: dict, cand: dict, viewer: dict, engine: dict, disagreed: set) -> Dict[str, Any]:
    ctx, value = item.get("context") or {}, item.get("value") if isinstance(item.get("value"), dict) else {}
    state = cand.get("lookup_state") if cand.get("lookup_state") in STATES else None
    rec = cand.get("registry_record") if isinstance(cand.get("registry_record"), dict) else None
    mismatch = state == "title_mismatch"
    return {"item_id": item.get("item_id"), "identifier": ctx.get("identifier"), "title": ctx.get("title"), "group": ctx.get("group"),
            "likely_keep": bool(ctx.get("likely_keep")), "reason": ctx.get("reason"), "cited_by": ctx.get("cited_by"),
            "choice": item.get("choice"), "comment": value.get("comment", ""), "revision": item.get("revision", 0), "answered": item.get("revision", 0) >= 1,
            "author": form.author_label(item.get("author_subscriber_id"), viewer, engine) if item.get("author_subscriber_id") else None,
            "updated_at": item.get("updated_at"), "comment_count": item.get("comment_count", 0), "disagreed": item.get("item_id") in disagreed,
            "lookup_state": state, "unresolved": state not in RESOLVED,
            "abstract": cand.get("abstract") or None, "abstract_source": cand.get("abstract_source"), "abstract_fetched_at": cand.get("abstract_fetched_at"),
            "registry": {"title": rec.get("title"), "authors": rec.get("authors") or [], "year": rec.get("year")} if rec else None,
            "warning": MISMATCH_WARNING if mismatch else None}


def review_view(db, engine_id: str, viewer: dict) -> Dict[str, Any]:
    """Every paper of the engine's hold list with its decision, comment, flags and abstract, in the hold list's order, with the groups and the counts the page
    filters by. 404 for an engine with no hold list (the section does not exist for it)."""
    engine = form._engine(db, engine_id)
    items = [i for i in form._items_of(db, engine_id, SECTION) if i.get("type") == ITEM_TYPE]
    if not items:
        raise FormError(404, "Not found")
    comments = form._comments_of(db, engine_id, SECTION)
    disagreed = form._disagreed_ids(comments)
    cands = _candidates(db, engine_id)
    sec = form._section_docs(db, engine_id).get(SECTION) or {}
    status = sec.get("status", "draft")
    papers = [_paper(i, cands.get((i.get("context") or {}).get("candidate_id")) or {}, viewer, engine, disagreed) for i in items]
    groups: List[str] = []
    for p in papers:
        if p["group"] and p["group"] not in groups:
            groups.append(p["group"])
    counts = {"papers": len(papers), "likely_keep": sum(p["likely_keep"] for p in papers), "unresolved": sum(p["unresolved"] for p in papers),
              **{c: sum(p["choice"] == c for p in papers) for c in tpl.REVIEW_CHOICES}, "unanswered": sum(not p["answered"] for p in papers)}
    return {"section": {"key": SECTION, "title": tpl.section_title(SECTION), "status": status, "revision": sec.get("revision", 1),
                        "content_sha256": form.content_sha256(items), **form.review_view(sec, status), **form.section_counts(items, disagreed, status)},
            "papers": papers, "groups": groups, "counts": counts, "choices": list(tpl.REVIEW_CHOICES), "bulk_max": BULK_MAX,
            "template_version": tpl.TEMPLATE_VERSION}


# ---- bulk marking ---------------------------------------------------------------------------------------------------------------------------------------
def _bulk_in(transaction, db, engine_id, sid, choice, papers, now, ip_hash, request_id, outcome=None):
    engine_snap = db.collection(ob.ENGINES).document(engine_id).get(transaction=transaction)
    if not engine_snap.exists:
        raise FormError(404, "Not found")
    if (engine_snap.to_dict() or {}).get("state") != "open":
        raise FormError(409, "This engine is not open for edits")
    rows = []
    for item_id, base_revision in papers:                                            # ALL reads first; every write below is committed together, or none is
        ref = db.collection(form.ITEMS).document(form.item_key(engine_id, SECTION, item_id))
        snap = ref.get(transaction=transaction)
        item = snap.to_dict() if snap.exists else None
        if not item or item.get("type") != ITEM_TYPE or item.get("engine_id") != engine_id:
            raise FormError(404, "Not found")
        rows.append((item_id, base_revision, ref, item))
    sec_ref = form._section_ref(db, engine_id, SECTION)
    sec_snap = sec_ref.get(transaction=transaction)
    sec = sec_snap.to_dict() if sec_snap.exists else {"engine_id": engine_id, "section": SECTION, "status": "draft", "revision": 1}
    stale = [{"item_id": i, "title": (item.get("context") or {}).get("title")} for i, base, _, item in rows if base != item.get("revision", 0)]
    if stale:
        raise FormError(409, f"{len(stale)} of these papers changed since you opened the page, so nothing was marked. Reload and try again.", reason="stale", stale=stale)
    changed, unchanged = [], []
    for item_id, _, ref, item in rows:
        if item.get("choice") == choice:
            unchanged.append(item_id)
            continue
        value = item.get("value") if isinstance(item.get("value"), dict) else {}
        try:
            clean_value, clean_choice = tpl.validate_item(ITEM_TYPE, {"comment": value.get("comment", "")}, choice)
        except tpl.TemplateError as e:
            raise FormError(400, str(e))
        history = ((item.get("history") or []) + ([{"revision": item["revision"], "choice": item.get("choice"), "value": item.get("value"),
                                                    "value_sha256": ob._sha(item.get("value")), "author": item.get("author_subscriber_id"), "at": item.get("updated_at")}]
                                                   if item.get("revision", 0) >= 1 else []))[-form.HISTORY_CAP:]
        new = {**item, "value": clean_value, "choice": clean_choice, "revision": item.get("revision", 0) + 1, "author_subscriber_id": sid, "updated_at": now.isoformat(),
               "history": history}
        transaction.set(ref, new)
        changed.append({"item_id": item_id, "before_choice": item.get("choice"), "revision": new["revision"]})
    if not changed:
        return {"marked": [], "unchanged": unchanged}
    transaction.set(sec_ref, form._reopened(sec, sid, now))
    if outcome is not None:
        outcome["reopened_from"] = sec.get("status", "draft")
    ob._event(transaction, db, engine_id=engine_id, actor=sid, actor_role="owner", action="review_bulk", target=SECTION, before=None,
              after={"choice": choice, "count": len(changed)}, ip_hash=ip_hash, request_id=request_id, now=now,
              extra={"section": SECTION, "choice": choice, "items": changed, "unchanged": len(unchanged)})
    if sec.get("status", "draft") != "draft":
        ob._event(transaction, db, engine_id=engine_id, actor=sid, actor_role="owner", action="reopen", target=SECTION, before={"status": sec.get("status")},
                  after={"status": "draft"}, ip_hash=ip_hash, request_id=request_id, now=now, extra={"section": SECTION, "from_status": sec.get("status")})
    return {"marked": [c["item_id"] for c in changed], "unchanged": unchanged}


def bulk_mark(db, *, engine_id: str, subscriber_id: str, choice: Any, papers: Any, now: Optional[datetime] = None, ip_hash: Optional[str] = None,
              request_id: Optional[str] = None, outcome: Optional[dict] = None) -> Dict[str, Any]:
    """Give up to BULK_MAX papers one choice, all or nothing. `papers` is [{item_id, base_revision}]: the revision of each paper as the owner saw it. Returns
    {marked: [item ids], unchanged: [item ids that already had the choice]}."""
    if choice not in tpl.REVIEW_CHOICES:
        raise FormError(400, "choice must be one of: " + ", ".join(tpl.REVIEW_CHOICES))
    if not isinstance(papers, list) or not (1 <= len(papers) <= BULK_MAX):
        raise FormError(400, f"Select from 1 to {BULK_MAX} papers")
    clean = []
    for p in papers:
        item_id, base = (p or {}).get("item_id") if isinstance(p, dict) else None, (p or {}).get("base_revision") if isinstance(p, dict) else None
        if not isinstance(item_id, str) or not tpl.ID_RE.match(item_id) or not isinstance(base, int) or isinstance(base, bool) or base < 0:
            raise FormError(400, "Each paper needs its id and the revision you were looking at")
        clean.append((item_id, base))
    if len({c[0] for c in clean}) != len(clean):
        raise FormError(400, "A paper is listed twice")
    return ob._run_in_transaction(db, _bulk_in, db, engine_id, subscriber_id, choice, clean, now or ob._utcnow(), ip_hash, request_id, outcome)
