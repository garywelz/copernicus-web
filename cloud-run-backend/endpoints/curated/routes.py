"""Curated source lists: create, fill, confirm, strike, override a class, approve and freeze (admin only).

Design: docs/design/CURATED_SOURCES_MODE.md §3. Every route here requires the admin key header (one dependency on the router, so no
route can be added without it). The one route that generates (`/generate`) makes a PRIVATE episode from an approved list; nothing here
publishes anything.

Confirmation (network) happens before the list is touched; the list is then changed in one Firestore transaction, so a failed
confirmation leaves the list exactly as it was and two simultaneous edits cannot overwrite each other.
"""

from datetime import datetime, timezone
from typing import Any, Callable, Dict, List
import uuid

from fastapi import APIRouter, Depends, HTTPException
from google.cloud import firestore

import curated_mode
import curated_sources as cs
import openai_math_index as omi
import paper_confirmation as pc
from config.database import db
from models.curated import AddCommentary, AddSourceItems, CreateSourceList, GenerateCuratedEpisode, OverrideItemClass, SetCheckedBy
from models.podcast import PodcastRequest
from utils.auth import verify_admin_api_key
from utils.logging import structured_logger
from utils.subscriber_helpers import resolve_generation_subscriber_id

router = APIRouter(dependencies=[Depends(verify_admin_api_key)])

COLLECTION = "curated_source_lists"
PRIVATE_COLLECTION = "curated_private_text"      # pasted commentary, one document per item; admin SDK only, never returned by a list route
MAX_REFUSED_KEPT = 100


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _require_db():
    if not db:
        raise HTTPException(status_code=503, detail="Firestore service is unavailable")


def _run_in_transaction(fn, *args):
    """Run fn(transaction, *args) in a Firestore transaction (retried on contention). Tests replace this."""
    return firestore.transactional(fn)(db.transaction(), *args)


def _mutate_in(transaction, list_id: str, mutator: Callable[[Dict[str, Any]], Any]):
    ref = db.collection(COLLECTION).document(list_id)
    snap = ref.get(transaction=transaction)
    if not snap.exists:
        raise HTTPException(status_code=404, detail="No such source list")
    doc = snap.to_dict() or {}
    result = mutator(doc)                # may raise HTTPException; nothing is written then
    doc["updated_at"] = _now()
    transaction.set(ref, doc)
    return result


def _mutate(list_id: str, mutator: Callable[[Dict[str, Any]], Any]):
    _require_db()
    return _run_in_transaction(_mutate_in, list_id, mutator)


def _require_draft(doc: Dict[str, Any]) -> None:
    if doc.get("status") != "draft":
        raise HTTPException(status_code=409, detail="This list is approved and frozen; make a new list to change anything")


def _private_ref(list_id: str, item_id: str):
    return db.collection(PRIVATE_COLLECTION).document(f"{list_id}__{item_id}")


def _private_text(list_id: str, item_id: str):
    snap = _private_ref(list_id, item_id).get()
    return (snap.to_dict() or {}).get("text") if snap.exists else None


def _summary(item: Dict[str, Any]) -> Dict[str, Any]:
    c = item.get("confirmation") or {}
    return {"item_id": item.get("item_id"), "class": item.get("class"), "title": item.get("title"), "status": c.get("status"),
            "reason": c.get("reason"), "detail": c.get("detail"), "directories": c.get("directories") or None,
            "overrides_allowed": cs.allowed_class_overrides(item)}


@router.post("/api/admin/curated/lists")
async def create_list(body: CreateSourceList):
    _require_db()
    commit = (body.pin_commit or omi.DEFAULT_COMMIT).strip().lower()
    if not omi.COMMIT_RE.match(commit):
        raise HTTPException(status_code=422, detail="pin_commit must be a 40-character commit id")
    list_id = uuid.uuid4().hex
    doc = {"list_id": list_id, "title": body.title.strip(), "topic": (body.topic or "").strip() or None, "status": "draft",
           "pin": {"repo": omi.REPO, "commit": commit}, "items": [], "refused": [], "list_hash": None,
           "created_at": _now(), "updated_at": _now(), "created_by": "admin", "approved_at": None}
    db.collection(COLLECTION).document(list_id).set(doc)
    structured_logger.info("Curated source list created", list_id=list_id)
    return {"list_id": list_id, "status": "draft", "pin": doc["pin"]}


@router.get("/api/admin/curated/lists")
async def list_lists():
    _require_db()
    out = []
    for d in db.collection(COLLECTION).stream():
        x = d.to_dict() or {}
        out.append({"list_id": x.get("list_id"), "title": x.get("title"), "status": x.get("status"), "items": len(x.get("items") or []),
                    "list_hash": x.get("list_hash"), "created_at": x.get("created_at")})
    return {"lists": sorted(out, key=lambda r: r.get("created_at") or "", reverse=True)}


@router.get("/api/admin/curated/lists/{list_id}")
async def get_list(list_id: str):
    _require_db()
    snap = db.collection(COLLECTION).document(list_id).get()
    if not snap.exists:
        raise HTTPException(status_code=404, detail="No such source list")
    doc = snap.to_dict() or {}
    ok, counts = cs.minimum_check(doc.get("items") or [])
    doc["minimum"] = {"required": cs.MIN_NON_COMMENTARY, "met": ok, "counts": counts}
    return doc


@router.post("/api/admin/curated/lists/{list_id}/items")
async def add_items(list_id: str, body: AddSourceItems):
    _require_db()
    snap = db.collection(COLLECTION).document(list_id).get()
    if not snap.exists:
        raise HTTPException(status_code=404, detail="No such source list")
    current = snap.to_dict() or {}
    _require_draft(current)
    commit = (current.get("pin") or {}).get("commit") or omi.DEFAULT_COMMIT

    # Network first. If any registry or the repository cannot be reached nothing is added (503): try again later.
    results: List[Dict[str, Any]] = []
    try:
        for raw in body.items:
            results.extend(await cs.confirm_pasted(raw, commit))
    except pc.RegistryUnavailable as e:
        raise HTTPException(status_code=503, detail=str(e))
    except omi.RepoUnavailable as e:
        raise HTTPException(status_code=503, detail=f"The repository could not be read, so nothing was added: {e}")

    added: List[Dict[str, Any]] = []
    refused: List[Dict[str, Any]] = []

    def apply(doc: Dict[str, Any]):
        _require_draft(doc)
        items = doc.setdefault("items", [])
        have = {i["item_id"] for i in items}
        for r in results:
            if (r.get("confirmation") or {}).get("status") == cs.REFUSED or not r.get("item_id"):
                refused.append(r)
                continue
            if r["item_id"] in have:
                dup = dict(r)
                dup["confirmation"] = {"status": cs.REFUSED, "reason": "duplicate", "detail": "already in this list", "directories": []}
                refused.append(dup)
                continue
            if len(items) >= cs.MAX_ITEMS_PER_LIST:
                raise HTTPException(status_code=409, detail=f"A list holds at most {cs.MAX_ITEMS_PER_LIST} items")
            items.append(r)
            have.add(r["item_id"])
            added.append(r)
        kept = (doc.get("refused") or []) + [{"input": r.get("input"), "reason": (r.get("confirmation") or {}).get("reason"),
                                              "at": _now()} for r in refused]
        doc["refused"] = kept[-MAX_REFUSED_KEPT:]

    _mutate(list_id, apply)
    structured_logger.info("Curated source items added", list_id=list_id, added=len(added), refused=len(refused))
    return {"list_id": list_id, "added": [_summary(i) for i in added], "refused": [_summary(r) | {"input": r.get("input")} for r in refused]}


@router.delete("/api/admin/curated/lists/{list_id}/items/{item_id}")
async def strike_item(list_id: str, item_id: str):
    def apply(doc: Dict[str, Any]):
        _require_draft(doc)
        before = len(doc.get("items") or [])
        doc["items"] = [i for i in doc.get("items") or [] if i.get("item_id") != item_id]
        if len(doc["items"]) == before:
            raise HTTPException(status_code=404, detail="No such item in this list")
    _mutate(list_id, apply)
    try:
        _private_ref(list_id, item_id).delete()          # a no-op for any item that has no private text
    except Exception as e:  # noqa: BLE001 - the item is already gone from the list; a leftover private document is harmless and reported
        structured_logger.warning("Could not delete private commentary text", list_id=list_id, error_type=type(e).__name__)
    return {"list_id": list_id, "removed": item_id}


@router.put("/api/admin/curated/lists/{list_id}/items/{item_id}/class")
async def override_class(list_id: str, item_id: str, body: OverrideItemClass):
    def apply(doc: Dict[str, Any]):
        _require_draft(doc)
        item = next((i for i in doc.get("items") or [] if i.get("item_id") == item_id), None)
        if item is None:
            raise HTTPException(status_code=404, detail="No such item in this list")
        allowed = cs.allowed_class_overrides(item)
        if body.source_class not in allowed:
            raise HTTPException(status_code=422, detail={"message": "That class change is not allowed for this item",
                                                         "allowed": allowed})
        item["class"] = body.source_class
        item["class_overridden_from"] = item["confirmation"].get("source_class")
        return _summary(item)
    return _mutate(list_id, apply)


@router.post("/api/admin/curated/lists/{list_id}/approve")
async def approve_list(list_id: str):
    def apply(doc: Dict[str, Any]):
        _require_draft(doc)
        items = doc.get("items") or []
        pending = [i["item_id"] for i in items if (i.get("confirmation") or {}).get("status") != cs.CONFIRMED]
        if pending:
            raise HTTPException(status_code=409, detail={"message": "Remove or complete the unconfirmed items first", "items": pending})
        ok, counts = cs.minimum_check(items)
        if not ok:
            raise HTTPException(status_code=422, detail={"message": f"At least {cs.MIN_NON_COMMENTARY} confirmed non-commentary sources "
                                                         "are needed; commentary never counts", "counts": counts})
        doc["list_hash"] = cs.list_hash(doc["pin"], items)
        doc["status"] = "approved"
        doc["approved_at"] = _now()
        return {"list_id": list_id, "status": "approved", "list_hash": doc["list_hash"], "counts": counts, "pin": doc["pin"]}
    result = _mutate(list_id, apply)
    structured_logger.info("Curated source list approved", list_id=list_id, list_hash=result["list_hash"])
    return result


def _get_service():
    """The podcast generation service, initialised in main.py before the routers are registered."""
    import sys
    main_module = sys.modules.get('main')
    return getattr(main_module, 'podcast_generation_service', None) if main_module else None


@router.post("/api/admin/curated/generate")
async def generate_episode(body: GenerateCuratedEpisode):
    """Generate ONE private episode from an approved, frozen source list. The list is checked before any job exists: it must be approved,
    still match its hash, have at least three confirmed non-commentary sources and fit one episode. The episode is never published here
    (``submitted_to_rss`` is False and its media stay in the private bucket); publishing is a separate, gated step."""
    _require_db()
    snap = db.collection(COLLECTION).document(body.list_id).get()
    if not snap.exists:
        raise HTTPException(status_code=404, detail="No such source list")
    doc = snap.to_dict() or {}
    texts = {i["item_id"]: _private_text(body.list_id, i["item_id"]) for i in doc.get("items") or []
             if i.get("class") == cs.COMMENTARY and i.get("approved")}
    texts = {k: v for k, v in texts.items() if v is not None}
    try:
        run = curated_mode.CuratedRun.from_list_doc(doc, topic=body.topic, private_texts=texts)
    except curated_mode.CuratedListError as e:
        raise HTTPException(status_code=409, detail=str(e))
    service = _get_service()
    if service is None:
        raise HTTPException(status_code=503, detail="Podcast generation service is not available")

    job_id = str(uuid.uuid4())
    subscriber_id = resolve_generation_subscriber_id(None)       # the administrator's account, as for the other admin generation
    request = PodcastRequest(topic=run.topic, category=body.category, duration=body.duration, expertise_level=body.expertise_level,
                             format_type=body.format_type, host_voice_id=body.host_voice_id, expert_voice_id=body.expert_voice_id)
    db.collection('podcast_jobs').document(job_id).set({
        'job_id': job_id, 'status': 'pending', 'created_at': _now(), 'updated_at': _now(), 'request': request.model_dump(),
        'subscriber_id': subscriber_id, 'submitted_to_rss': False, 'mode': 'curated_sources',
        'curated_list_id': run.list_id, 'curated_list_hash': run.list_hash})
    _mutate(body.list_id, lambda d: d.setdefault("jobs", []).append(job_id))
    structured_logger.info("Curated generation started", job_id=job_id, list_id=run.list_id)
    await service.run_curated_generation_job(job_id, doc, request, subscriber_id=subscriber_id, private_texts=texts)
    job = db.collection('podcast_jobs').document(job_id).get()
    data = (job.to_dict() or {}) if job.exists else {}
    return {"job_id": job_id, "status": data.get("status"), "error_type": data.get("error_type"), "published": False,
            "curated_run": data.get("curated_run")}


# --- pasted commentary (the paste fallback; no automated fetch) ---------------------------------------------------------------------------
@router.post("/api/admin/curated/lists/{list_id}/commentary")
async def add_commentary(list_id: str, body: AddCommentary):
    """Add commentary the producer pasted. Its text goes to the private store; the list keeps only its hash and length. A pending item for the same
    address is replaced by it (that is how a commentary address pasted earlier is completed). Draft lists only."""
    _require_db()
    try:
        item, text = cs.build_commentary_item(body.title, body.outlet, body.authors, body.date, body.text, body.url, body.fetch_refused,
                                              body.approved_quotes)
    except cs.CommentaryError as e:
        raise HTTPException(status_code=422, detail=str(e))
    snap = db.collection(COLLECTION).document(list_id).get()
    if not snap.exists:
        raise HTTPException(status_code=404, detail="No such source list")
    _require_draft(snap.to_dict() or {})
    _private_ref(list_id, item["item_id"]).set({"list_id": list_id, "item_id": item["item_id"], "text": text, "text_sha256": item["text_sha256"],
                                                 "created_at": _now()})

    def apply(doc: Dict[str, Any]):
        _require_draft(doc)
        items = doc.setdefault("items", [])
        existing = next((i for i in items if i.get("item_id") == item["item_id"]), None)
        if existing is not None and (existing.get("confirmation") or {}).get("status") == cs.CONFIRMED:
            raise HTTPException(status_code=409, detail="This commentary is already in the list; strike it first to replace it")
        if existing is not None:
            items[:] = [i for i in items if i.get("item_id") != item["item_id"]]
        elif len(items) >= cs.MAX_ITEMS_PER_LIST:
            raise HTTPException(status_code=409, detail=f"A list holds at most {cs.MAX_ITEMS_PER_LIST} items")
        items.append(item)
    try:
        _mutate(list_id, apply)
    except HTTPException:
        _private_ref(list_id, item["item_id"]).delete()     # nothing was added: do not leave the text behind
        raise
    structured_logger.info("Curated commentary added", list_id=list_id, item_id=item["item_id"], characters=item["text_chars"])
    return {"list_id": list_id, "added": _summary(item), "text_chars": item["text_chars"], "text_sha256": item["text_sha256"], "limits": item["limits"]}


@router.get("/api/admin/curated/lists/{list_id}/commentary/{item_id}")
async def read_commentary(list_id: str, item_id: str):
    """The stored text of one commentary item, for the producer to check what the episode will be written from."""
    _require_db()
    text = _private_text(list_id, item_id)
    if text is None:
        raise HTTPException(status_code=404, detail="No pasted text for this item")
    return {"list_id": list_id, "item_id": item_id, "text": text, "chars": len(text)}


@router.put("/api/admin/curated/lists/{list_id}/items/{item_id}/checked-by")
async def set_checked_by(list_id: str, item_id: str, body: SetCheckedBy):
    """Mark a company-release manuscript `checked by experts` because a commentary source IN THIS LIST says so (design §4). The sentence that says it
    must occur in that commentary's pasted text. Not allowed for a withdrawn manuscript. The status is only ever 'reported by' that source."""
    _require_db()
    text = _private_text(list_id, body.commentary_item_id)
    if text is None or not cs.text_contains(text, body.quote):
        raise HTTPException(status_code=422, detail="The quotation does not occur in that commentary's pasted text")

    def apply(doc: Dict[str, Any]):
        _require_draft(doc)
        items = doc.get("items") or []
        item = next((i for i in items if i.get("item_id") == item_id), None)
        source = next((i for i in items if i.get("item_id") == body.commentary_item_id), None)
        if item is None or source is None:
            raise HTTPException(status_code=404, detail="No such item in this list")
        if item.get("class") != cs.COMPANY_RELEASE or source.get("class") != cs.COMMENTARY or (source.get("confirmation") or {}).get("status") != cs.CONFIRMED:
            raise HTTPException(status_code=422, detail="Only a company release can be checked by a commentary source that is in the list")
        if item.get("result_status") == "withdrawn":
            raise HTTPException(status_code=422, detail="A withdrawn manuscript is never presented as checked")
        basis = dict(item.get("status_basis") or {})
        basis["checked_by"] = {"commentary_item_id": body.commentary_item_id, "quote": body.quote.strip(),
                               "previous_status": basis.get("checked_by", {}).get("previous_status") or item.get("result_status") or "unverified"}
        item["status_basis"], item["result_status"], item["checked_by"] = basis, "checked_by_experts", source.get("venue") or source.get("title")
        return _summary(item)
    return _mutate(list_id, apply)


@router.delete("/api/admin/curated/lists/{list_id}/items/{item_id}/checked-by")
async def clear_checked_by(list_id: str, item_id: str):
    def apply(doc: Dict[str, Any]):
        _require_draft(doc)
        item = next((i for i in doc.get("items") or [] if i.get("item_id") == item_id), None)
        if item is None or item.get("result_status") != "checked_by_experts":
            raise HTTPException(status_code=404, detail="That item is not marked as checked by experts")
        item["result_status"] = item["status_basis"]["checked_by"]["previous_status"]
        item.pop("checked_by", None)
        item["status_basis"].pop("checked_by", None)
        return _summary(item)
    return _mutate(list_id, apply)
