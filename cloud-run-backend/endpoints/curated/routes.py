"""Curated source lists: create, fill, confirm, strike, override a class, approve and freeze (admin only).

Design: docs/design/CURATED_SOURCES_MODE.md §3. Every route here requires the admin key header (one dependency on the router, so no
route can be added without it). Nothing here generates anything: an approved list is the input a later build step reads.

Confirmation (network) happens before the list is touched; the list is then changed in one Firestore transaction, so a failed
confirmation leaves the list exactly as it was and two simultaneous edits cannot overwrite each other.
"""

from datetime import datetime, timezone
from typing import Any, Callable, Dict, List
import uuid

from fastapi import APIRouter, Depends, HTTPException
from google.cloud import firestore

import curated_sources as cs
import openai_math_index as omi
import paper_confirmation as pc
from config.database import db
from models.curated import AddSourceItems, CreateSourceList, OverrideItemClass
from utils.auth import verify_admin_api_key
from utils.logging import structured_logger

router = APIRouter(dependencies=[Depends(verify_admin_api_key)])

COLLECTION = "curated_source_lists"
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
