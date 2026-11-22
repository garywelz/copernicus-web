"""Curated source lists: create, fill, confirm, strike, override a class, approve and freeze (admin only).

Design: docs/design/CURATED_SOURCES_MODE.md §3. Every route here requires the admin key header (one dependency on the router, so no
route can be added without it). The one route that generates (`/generate`) makes a PRIVATE episode from an approved list; nothing here
publishes anything.

Confirmation (network) happens before the list is touched; the list is then changed in one Firestore transaction, so a failed
confirmation leaves the list exactly as it was and two simultaneous edits cannot overwrite each other.
"""

import hashlib
from datetime import datetime, timezone
from typing import Any, Callable, Dict, List
import uuid

from fastapi import APIRouter, Depends, HTTPException
from google.cloud import firestore

import curated_mode
import curated_sources as cs
import curated_web_release as cwr
import openai_math_index as omi
import paper_confirmation as pc
from config.database import db
from models.curated import (AddCommentary, AddCompanyRelease, AddPaperWithSuppliedAbstract, AddSourceItems, AttachReleaseText,
                            CheckSuppliedScript, CreateSourceList, GenerateCuratedEpisode, OverrideItemClass, SetCheckedBy)
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


def _note_job_on_list(list_id: str, job_id: str) -> bool:
    """Append `job_id` to the list's `jobs` array, and DO NOT fail the run if that write cannot be made.

    The array is a convenience for reading a list's history. The link of record is on the job itself, which carries `curated_list_id` and
    `curated_list_hash`, so the array can be rebuilt from the jobs collection at any time; nothing in this service reads it.

    It used to be written with the transaction that fails the whole request. On 2026-11-22 a run of 017 died here with "The referenced
    transaction has expired or is no longer valid" AFTER the job document was written and BEFORE generation began, leaving a job stuck at
    `pending` and throwing away a script that had passed every check. One retry covers the transient case; a second failure is logged as an
    error naming both ids, and the run goes on."""
    for attempt in (1, 2):
        try:
            _mutate(list_id, lambda d: d.setdefault("jobs", []).append(job_id))
            return True
        except HTTPException:
            raise                                               # a missing list, or a status refusal: the caller must see it
        except Exception as e:                                  # noqa: BLE001 - a breadcrumb must not cost a checked script
            if attempt == 1:
                structured_logger.warning("Could not note the job on its source list; retrying once",
                                          job_id=job_id, list_id=list_id, error=str(e), error_type=type(e).__name__)
                continue
            structured_logger.error("Could not note the job on its source list; the run continues and the list's jobs array is now "
                                    "incomplete. Rebuild it from podcast_jobs.curated_list_id if it is needed.",
                                    job_id=job_id, list_id=list_id, error=str(e), error_type=type(e).__name__)
    return False


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


def _store_results(list_id: str, results: List[Dict[str, Any]]):
    """Add confirmed items to a draft list and note the refused ones, in one transaction. Returns (added, refused)."""
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
    return added, refused


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

    added, refused = _store_results(list_id, results)
    structured_logger.info("Curated source items added", list_id=list_id, added=len(added), refused=len(refused))
    return {"list_id": list_id, "added": [_summary(i) for i in added], "refused": [_summary(r) | {"input": r.get("input")} for r in refused]}


@router.post("/api/admin/curated/lists/{list_id}/company-releases")
async def add_company_release(list_id: str, body: AddCompanyRelease):
    """A company release at a stable https address, confirmed by a guarded fetch and pinned by the SHA-256 of the bytes and the fetch date. If the address
    cannot be reached nothing is added (503). A refusal (wrong page, title or company not in the document, no readable text, not https) is reported and stored nowhere."""
    _require_db()
    snap = db.collection(COLLECTION).document(list_id).get()
    if not snap.exists:
        raise HTTPException(status_code=404, detail="No such source list")
    _require_draft(snap.to_dict() or {})
    try:
        result = await cwr.confirm_web_release(body.url, body.title, body.company, body.date, body.authors)
    except cwr.WebReleaseUnavailable as e:
        raise HTTPException(status_code=503, detail=f"The address could not be read, so nothing was added: {e}")
    added, refused = _store_results(list_id, [result])
    structured_logger.info("Curated company release added", list_id=list_id, added=len(added), refused=len(refused))
    return {"list_id": list_id, "added": [_summary(i) | {"sha256": (i.get("confirmation") or {}).get("sha256"),
                                                          "fetched_at": (i.get("confirmation") or {}).get("fetched_at")} for i in added],
            "refused": [_summary(r) | {"input": r.get("input")} for r in refused]}


@router.post("/api/admin/curated/lists/{list_id}/items-with-supplied-abstract")
async def add_paper_with_supplied_abstract(list_id: str, body: AddPaperWithSuppliedAbstract):
    """One peer-reviewed paper whose registry record has no abstract, with the paper's own published abstract as the producer copied it from the
    publisher's page. Confirmed against Crossref as usual; the abstract is stored with its hash and page address and the item is labelled
    "abstract supplied by the producer". Refused if the registry has an abstract. If a registry cannot be reached nothing is added (503)."""
    _require_db()
    snap = db.collection(COLLECTION).document(list_id).get()
    if not snap.exists:
        raise HTTPException(status_code=404, detail="No such source list")
    _require_draft(snap.to_dict() or {})
    try:
        result = await cs.confirm_with_supplied_abstract(body.doi, body.abstract, body.abstract_url)
    except pc.RegistryUnavailable as e:
        raise HTTPException(status_code=503, detail=str(e))
    added, refused = _store_results(list_id, [result])
    structured_logger.info("Curated paper with supplied abstract added", list_id=list_id, added=len(added), refused=len(refused))
    return {"list_id": list_id, "added": [_summary(i) | {"abstract_sha256": (i.get("confirmation") or {}).get("abstract_sha256")} for i in added],
            "refused": [_summary(r) | {"input": r.get("input")} for r in refused]}


@router.post("/api/admin/curated/lists/{list_id}/items/{item_id}/release-text")
async def attach_release_text(list_id: str, item_id: str, body: AttachReleaseText):
    """Attach more of a company release's own text to that release's item. The text goes to the private store; the item keeps its hash,
    length, source path and note, so the list records what was attached without reproducing it. Draft lists only.

    This is what the commentary route was being used for before: a manuscript's own statement added as a separate commentary item made the
    list hold "commentary", which keeps the reaction section in the plan (`curated_script.plan_sections`) with no reaction material to
    write it from, and described a company as a commentator on its own work. Attached text belongs to the manuscript itself."""
    _require_db()
    snap = db.collection(COLLECTION).document(list_id).get()
    if not snap.exists:
        raise HTTPException(status_code=404, detail="No such source list")
    doc = snap.to_dict() or {}
    _require_draft(doc)
    item = next((i for i in doc.get("items") or [] if i.get("item_id") == item_id), None)
    if item is None:
        raise HTTPException(status_code=404, detail="No such item in this list")
    if item.get("class") != cs.COMPANY_RELEASE:
        raise HTTPException(status_code=422, detail="Only a company release carries attached text; a registry paper carries its abstract")
    if (item.get("confirmation") or {}).get("status") != cs.CONFIRMED:
        raise HTTPException(status_code=422, detail="The item is not confirmed")
    text = body.text.strip()
    if not text:
        raise HTTPException(status_code=422, detail="The text is empty")
    sha = hashlib.sha256(text.encode("utf-8")).hexdigest()
    _private_ref(list_id, item_id).set({"list_id": list_id, "item_id": item_id, "text": text, "text_sha256": sha, "created_at": _now()})

    def apply(d: Dict[str, Any]):
        _require_draft(d)
        target = next((i for i in d.get("items") or [] if i.get("item_id") == item_id), None)
        if target is None:
            raise HTTPException(status_code=404, detail="No such item in this list")
        target["release_text"] = {"sha256": sha, "chars": len(text), "source_path": body.source_path.strip(),
                                  "note": (body.note or "").strip() or None, "attached_at": _now()}
        return _summary(target) | {"release_text": target["release_text"]}

    out = _mutate(list_id, apply)
    structured_logger.info("Release text attached", list_id=list_id, item_id=item_id, chars=len(text))
    return {"list_id": list_id, "item_id": item_id, **out}


@router.delete("/api/admin/curated/lists/{list_id}/items/{item_id}/release-text")
async def clear_release_text(list_id: str, item_id: str):
    """Remove attached text and the private document that holds it. Draft lists only."""
    _require_db()

    def apply(d: Dict[str, Any]):
        _require_draft(d)
        target = next((i for i in d.get("items") or [] if i.get("item_id") == item_id), None)
        if target is None or not target.get("release_text"):
            raise HTTPException(status_code=404, detail="That item has no attached text")
        target.pop("release_text", None)

    _mutate(list_id, apply)
    try:
        _private_ref(list_id, item_id).delete()
    except Exception as e:  # noqa: BLE001 - the list no longer points at it; a leftover private document is harmless and reported
        structured_logger.warning("Could not delete attached release text", list_id=list_id, error_type=type(e).__name__)
    return {"list_id": list_id, "item_id": item_id, "release_text": None}


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
             if (i.get("class") == cs.COMMENTARY and i.get("approved")) or i.get("release_text")}
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
                             format_type=body.format_type, host_voice_id=body.host_voice_id, expert_voice_id=body.expert_voice_id,
                             thumbnail_title=body.thumbnail_title, thumbnail_subtitle=body.thumbnail_subtitle)
    db.collection('podcast_jobs').document(job_id).set({
        'job_id': job_id, 'status': 'pending', 'created_at': _now(), 'updated_at': _now(), 'request': request.model_dump(),
        'subscriber_id': subscriber_id, 'submitted_to_rss': False, 'mode': 'curated_sources',
        'curated_list_id': run.list_id, 'curated_list_hash': run.list_hash})
    _note_job_on_list(body.list_id, job_id)
    structured_logger.info("Curated generation started", job_id=job_id, list_id=run.list_id)
    await service.run_curated_generation_job(job_id, doc, request, subscriber_id=subscriber_id, private_texts=texts, title=body.title)
    job = db.collection('podcast_jobs').document(job_id).get()
    data = (job.to_dict() or {}) if job.exists else {}
    out = {"job_id": job_id, "status": data.get("status"), "error_type": data.get("error_type"), "published": False,
           "curated_run": data.get("curated_run")}
    if (data.get("thumbnail") or {}).get("thumbnail_error_message"):
        out["thumbnail_warning"] = data["thumbnail"]["thumbnail_error_message"]          # the episode generated, with the default artwork, and this is why
    return out


@router.post("/api/admin/curated/dry-run")
async def dry_run_script(body: GenerateCuratedEpisode):
    """Script-only dry run: the same pipeline and the same checks as a real generation, but NO job record, NO episode record, NO audio and NO media:
    nothing is written anywhere. Returns the script, its sections, the notes it was written from, the checks and the trace, to the administrator
    only (the notes and the script paraphrase private commentary, so this answer is never logged). A failure is returned as evidence, not raised."""
    _require_db()
    snap = db.collection(COLLECTION).document(body.list_id).get()
    if not snap.exists:
        raise HTTPException(status_code=404, detail="No such source list")
    doc = snap.to_dict() or {}
    texts = {i["item_id"]: _private_text(body.list_id, i["item_id"]) for i in doc.get("items") or []
             if (i.get("class") == cs.COMMENTARY and i.get("approved")) or i.get("release_text")}
    texts = {k: v for k, v in texts.items() if v is not None}
    try:
        run = curated_mode.CuratedRun.from_list_doc(doc, topic=body.topic, private_texts=texts, title=body.title)
    except curated_mode.CuratedListError as e:
        raise HTTPException(status_code=409, detail=str(e))
    import curated_pipeline
    import curated_script
    import paper_confirmation
    from named_work_check import make_gemini_llm_call
    from podcast_research_integrator import PodcastResearchContext
    from utils.api_keys import get_google_api_key
    from utils.script_validation import calculate_maximum_words_for_duration, calculate_minimum_words_for_duration
    request = PodcastRequest(topic=run.topic, category=body.category, duration=body.duration, expertise_level=body.expertise_level,
                             format_type=body.format_type, host_voice_id=body.host_voice_id, expert_voice_id=body.expert_voice_id)
    confirmed = run.confirmed_papers()
    context = PodcastResearchContext(
        topic=run.topic, research_sources=[paper_confirmation.as_research_source(c) for c in confirmed if c.source_class != cs.COMMENTARY],
        paper_analyses=[], significance=[], interdisciplinary_connections=[], key_findings=[], real_citations=[], research_quality_score=5.0,
        recommended_expertise_level=body.expertise_level, confirmed_papers=confirmed, dropped_candidates=[], requested_pid=None, curated=run)
    key = get_google_api_key()
    base = {"list_id": run.list_id, "list_hash": run.list_hash, "dry_run": True, "published": False, "written": "nothing",
            "limits": {"min_words": calculate_minimum_words_for_duration(body.duration), "max_words": calculate_maximum_words_for_duration(body.duration)}}
    try:
        gen = await curated_pipeline.generate_curated_content(request, context, make_gemini_llm_call(key), curated_pipeline.make_writer_llm(key),
                                                              job_id="dry-run", with_metadata=True)
    except curated_script.ScriptPipelineError as e:
        return {**base, "status": "failed", "error_type": type(e).__name__, "error": str(e),
                "violations": [curated_script.reported_violation(x) for x in getattr(e, "violations", [])],
                **getattr(e, "diagnostics", {})}
    script = gen.content["script"]
    return {**base, "status": "ok", "words": len(script.split()), "tts_characters": len(script), "title": gen.content["title"],
            "description": gen.content["description"], "plan": gen.plan, "section_words": {k: len(v.split()) for k, v in gen.sections.items()},
            "script": script, "notes": gen.notes, "checks": gen.naming_attempts, "trace": gen.trace, "rejection_count": len(gen.rejections),
            "model_calls": gen.model_calls, "model_calls_total": sum(gen.model_calls.values())}


def _supplied_answer(answer: Dict[str, Any], job_id: str, data: Dict[str, Any]) -> Dict[str, Any]:
    """What `check-script` reports once a job has run. The checks passing does not mean an episode exists: a job can pass every check and
    then fail (a source analysis that cannot be read, a voicing error), as job 036f703c did on 2026-11-19 while the route still answered
    `passed: true, generated: true`. The answer therefore reports what the JOB did, and an episode counts as made only when its media is
    recorded and the job completed."""
    out = dict(answer)
    result = data.get("result") or {}
    made = bool(result.get("audio_url")) and data.get("status") == "completed"
    out.update({"generated": made, "job_id": job_id, "job_status": data.get("status"), "error_type": data.get("error_type"),
                "status": "pass" if made else "failed_after_checks", "written": "an episode" if made else "nothing",
                "canonical_filename": result.get("canonical_filename"), "tts_characters": data.get("tts_characters")})
    if made:
        # Where the audio actually is. `result["audio_url"]` is the address it will have once the episode is published, so on a private
        # episode it names an object that does not exist yet and answers 404 (as the link reported on 2026-11-20 did).
        import media_store
        out["media_state"] = result.get("media_state")
        out["audio_location"] = media_store.media_uri(result)
    if not made:
        out["error"] = data.get("error") or "the checks passed but the job did not produce an episode"
    if (data.get("thumbnail") or {}).get("thumbnail_error_message"):
        out["thumbnail_warning"] = data["thumbnail"]["thumbnail_error_message"]
    return out


# --- pasted commentary (the paste fallback; no automated fetch) ---------------------------------------------------------------------------
@router.post("/api/admin/curated/check-script")
async def check_supplied_script(body: CheckSuppliedScript):
    """Check a script an editor wrote, exactly as a generated script is checked: every curated check and every ordinary one, the duration window and the
    line format. Nothing is repaired and NOTHING IS WRITTEN. The answer (violations quote the script and, for a copied run, the commentary; attribution_detail carries the routing, the verdicts and the supporting excerpts) goes to the
    administrator only and is never logged. With ``generate=true``, and ONLY when every check passed, the audio and a private episode record are made
    through the existing pipeline (``submitted_to_rss`` False; the checks run again on the stored text); publishing stays a separate step."""
    _require_db()
    snap = db.collection(COLLECTION).document(body.list_id).get()
    if not snap.exists:
        raise HTTPException(status_code=404, detail="No such source list")
    doc = snap.to_dict() or {}
    texts = {i["item_id"]: _private_text(body.list_id, i["item_id"]) for i in doc.get("items") or []
             if (i.get("class") == cs.COMMENTARY and i.get("approved")) or i.get("release_text")}
    texts = {k: v for k, v in texts.items() if v is not None}
    try:
        run = curated_mode.CuratedRun.from_list_doc(doc, topic=body.topic, private_texts=texts, title=body.title)
    except curated_mode.CuratedListError as e:
        raise HTTPException(status_code=409, detail=str(e))
    import curated_pipeline
    import curated_script
    import paper_confirmation
    from named_work_check import make_gemini_llm_call
    from podcast_research_integrator import PodcastResearchContext
    from utils.api_keys import get_google_api_key
    request = PodcastRequest(topic=run.topic, category=body.category, duration=body.duration, expertise_level=body.expertise_level,
                             format_type=body.format_type, host_voice_id=body.host_voice_id, expert_voice_id=body.expert_voice_id,
                             thumbnail_title=body.thumbnail_title, thumbnail_subtitle=body.thumbnail_subtitle)
    confirmed = run.confirmed_papers()
    context = PodcastResearchContext(
        topic=run.topic, research_sources=[paper_confirmation.as_research_source(c) for c in confirmed if c.source_class != cs.COMMENTARY],
        paper_analyses=[], significance=[], interdisciplinary_connections=[], key_findings=[], real_citations=[], research_quality_score=5.0,
        recommended_expertise_level=body.expertise_level, confirmed_papers=confirmed, dropped_candidates=[], requested_pid=None, curated=run)
    checked = await curated_pipeline.check_supplied_script(request, context, make_gemini_llm_call(get_google_api_key()), body.script, title=body.title,
                                                           with_metadata=False)
    answer = {"list_id": run.list_id, "list_hash": run.list_hash, "title": body.title, "passed": checked.passed, "status": "pass" if checked.passed else "fail",
              "words": checked.words, "tts_characters": len(body.script), "limits": {"min_words": checked.min_words, "max_words": checked.max_words},
              "length_ok": checked.length_ok, "format_problems": checked.format_problems, "check_results": checked.entry,
              "violations": [curated_script.reported_violation(x) for x in checked.violations],
              "attribution_detail": checked.attribution.detail() if hasattr(checked.attribution, "detail") else [],
              "model_calls": checked.model_calls, "written": "nothing", "generated": False, "published": False}
    if not (body.generate and checked.passed):
        if body.generate:
            answer["generate_skipped"] = "a check failed, so nothing was generated"
        return answer
    service = _get_service()
    if service is None:
        raise HTTPException(status_code=503, detail="Podcast generation service is not available")
    job_id = str(uuid.uuid4())
    subscriber_id = resolve_generation_subscriber_id(None)
    db.collection('podcast_jobs').document(job_id).set({
        'job_id': job_id, 'status': 'pending', 'created_at': _now(), 'updated_at': _now(), 'request': request.model_dump(),
        'subscriber_id': subscriber_id, 'submitted_to_rss': False, 'mode': 'curated_sources', 'supplied_script': True,
        'curated_list_id': run.list_id, 'curated_list_hash': run.list_hash})
    _note_job_on_list(body.list_id, job_id)
    structured_logger.info("Curated generation from a supplied script started", job_id=job_id, list_id=run.list_id)
    await service.run_curated_generation_job(job_id, doc, request, subscriber_id=subscriber_id, private_texts=texts, title=body.title,
                                             supplied={"script": body.script, "title": body.title})
    job = db.collection('podcast_jobs').document(job_id).get()
    data = (job.to_dict() or {}) if job.exists else {}
    return _supplied_answer(answer, job_id, data)


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
