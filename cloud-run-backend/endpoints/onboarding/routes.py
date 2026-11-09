"""Onboarding routes, PR 2: invitations and engine roles (docs/design/ENGINE_ONBOARDING_FORM.md 3.1, 5.7, 8.1). There is no form yet.

  POST   /api/onboarding/invites/accept                 the holder of a valid single-use token (no session: the token is the proof)
  GET    /api/onboarding/engines/{engine_id}            a member of that engine, or the admin
  POST   /api/admin/onboarding/invites                  admin key: create an invitation (the address is entered once and kept only as a hash)
  GET    /api/admin/onboarding/invites?engine_id=       admin key: list one engine's invitations (never an address or token hash)
  DELETE /api/admin/onboarding/invites/{invite_id}      admin key: revoke an unused invitation; a used one also removes the membership (Q17)
  GET    /api/admin/onboarding/engines                  admin key: every engine with its sections, state, revision, age and who each waits on (PR 3b-1)
  GET    /api/admin/onboarding/engines/{e}              admin key: one engine with every item's history and comment threads, read only
  GET    /api/admin/onboarding/engines/{e}/diff?section=  admin key: the proposed output files for a final or approved section against the repository's main
  POST   /api/admin/onboarding/engines/{e}/sections/{s}/approve   admin key: approve a FINAL section at the revision and hash the reviewer saw
  POST   /api/admin/onboarding/engines/{e}/sections/{s}/reject    admin key: send a FINAL section back to DRAFT with a note

DEFAULT DENY: every route under /api/onboarding/engines/{engine_id}/... passes through `engine_gate`, which resolves the caller to a membership of that engine
or to the admin before any handler runs. Anyone else (signed in or not, member of another engine or none, engine real or invented) gets the same 404.
The accept route is the one exception; it is not an engine route and answers one and the same refusal for every kind of invalid invitation.
"""
import asyncio
from typing import Any, List, Optional

from fastapi import APIRouter, Depends, Header, HTTPException, Query, Request
from pydantic import BaseModel, Field, StrictBool, StrictInt

from config.constants import ADMIN_SUBSCRIBER_EMAIL
from config.database import db
from email_service import EmailService
from utils import onboarding as ob
from utils import onboarding_form as form
from utils import onboarding_gates as gates
from utils import onboarding_review as review
from utils import onboarding_template as tpl
from utils.auth import _admin_key_matches, verify_admin_api_key
from utils.credential_tokens import PASSWORD_MAX_LENGTH, PASSWORD_MIN_LENGTH
from utils.logging import structured_logger
from utils.rate_limit import check_rate_limit, last_forwarded_ip
from utils.subscriber_helpers import generate_subscriber_id, hash_password

router = APIRouter()
email_service = EmailService()

INVITATION_REFUSAL = "This invitation link is not valid."
ACCEPT_LIMIT_PER_IP_PER_HOUR = 10
ACCEPT_LIMIT_PER_ADDRESS_PER_HOUR = 5
ADMIN_INVITE_LIMIT_PER_HOUR = 60
ADMIN_LIST_LIMIT_PER_HOUR = 300
AUTOSAVE_LIMIT_PER_HOUR = 900       # one account saving as it types (the page debounces)
COMMENT_LIMIT_PER_HOUR = 120
QUESTION_LIMIT_PER_HOUR = 60
ENTRY_LIMIT_PER_HOUR = 60
FINAL_LIMIT_PER_HOUR = 60
DELEGATION_LIMIT_PER_HOUR = 30
ADMIN_REVIEW_LIMIT_PER_HOUR = 600
ADMIN_DECISION_LIMIT_PER_HOUR = 120
NOTIFICATION_LIMIT_PER_HOUR = 30
NOTICE_TIMEOUT_SECONDS = 10      # the mail is sent before the route returns, so a hung mail server must not hold an owner's save
ENGINE_PAGE_URL = "https://www.copernicusai.fyi/onboarding/engine.html"      # the link in a notification: the engine page, never an address
MAX_BODY_BYTES = 65536
PASSWORD_DETAIL = f"Password must be {PASSWORD_MIN_LENGTH} to {PASSWORD_MAX_LENGTH} characters."


# ---- the default-deny gate ------------------------------------------------------------------------------------------------------------------------
def origin_guard(origin: Optional[str] = Header(None)) -> None:
    """Browser calls come only from the site's own origin (design 9). A request with no Origin header (a server or a script) is not a browser call."""
    if origin and origin != ob.ALLOWED_ORIGIN:
        raise HTTPException(status_code=403, detail="Origin not allowed")


def engine_gate(engine_id: str, _origin: None = Depends(origin_guard),
                x_admin_api_key: Optional[str] = Header(None, alias="X-Admin-API-Key"),
                x_subscriber_token: Optional[str] = Header(None, alias="X-Subscriber-Token")) -> dict:
    """The shared membership dependency. Returns {"via": "admin"} or {"via": "member", "subscriber_id", "membership"}; anything else is a 404."""
    if not isinstance(engine_id, str) or not ob.ENGINE_ID_RE.match(engine_id) or "__" in engine_id:
        raise HTTPException(status_code=404, detail="Not found")
    if not db:
        raise HTTPException(status_code=503, detail="Firestore service is unavailable")
    if _admin_key_matches(x_admin_api_key):
        return {"via": "admin"}
    sid = ob.subscriber_for_token(db, x_subscriber_token)
    membership = ob.active_membership(db, engine_id, sid) if sid else None
    if not membership:
        raise HTTPException(status_code=404, detail="Not found")
    return {"via": "member", "subscriber_id": sid, "membership": membership}


engine_router = APIRouter(prefix="/api/onboarding/engines/{engine_id}", dependencies=[Depends(engine_gate)])


def _viewer(caller: dict) -> dict:
    return {"via": "admin"} if caller["via"] == "admin" else {"via": "member", "subscriber_id": caller["subscriber_id"]}


def _owner(caller: dict) -> dict:
    """Owners only. The administrator gets the same 404 as a stranger on every route that changes an owner's work, and an owner must have given consent first."""
    if caller.get("via") != "member":
        raise HTTPException(status_code=404, detail="Not found")
    if not (caller.get("membership") or {}).get("consent"):
        raise HTTPException(status_code=409, detail="Please complete the consent step first")
    return caller


def _fail(e: "form.FormError", viewer: Optional[dict] = None, engine_id: Optional[str] = None) -> HTTPException:
    if "current_doc" in e.extra:            # a stale save: say so, and hand back the current answer for a one-click merge
        return HTTPException(status_code=409, detail={"message": e.message, "stale": True, "current": form.item_view(db, engine_id, e.extra["current_doc"], viewer)})
    if e.extra:                              # a refusal with a reason (a section that is not ready, already final, ...)
        return HTTPException(status_code=e.status, detail={"message": e.message, **e.extra})
    return HTTPException(status_code=e.status, detail=e.message)


async def _notify(engine_id: str, section: Optional[str], reopened_from: Optional[str] = None, item_id: Optional[str] = None) -> None:
    """Tell the final-say owner (and a covering delegate) that a section is ready, or was re-opened. Runs AFTER the change has committed and BEFORE the route
    returns (Cloud Run may throttle the processor once a response is sent, so a background task could be starved): nothing here can undo a change or fail the
    request, and a failure is logged by error type only (never an address, a link or a name)."""
    try:
        if section is None and item_id:
            found = form.find_item(db, engine_id, item_id)
            section = found["section"] if found else None
        if not section:
            return
        plans = gates.plan_notifications(db, engine_id=engine_id, section=section, reopened_from=reopened_from)
    except Exception as e:
        structured_logger.error("Onboarding notice could not be planned", error_type=type(e).__name__)
        return
    link, sent = f"{ENGINE_PAGE_URL}?engine={engine_id}", 0
    for plan in plans:
        for address in plan["to"]:
            try:
                if await asyncio.wait_for(email_service.send_onboarding_notice(address, plan["kind"], plan["engine_label"], plan["section_title"], link), NOTICE_TIMEOUT_SECONDS):
                    sent += 1
            except Exception as e:
                structured_logger.error("Onboarding notice could not be sent", error_type=type(e).__name__)
    if plans:
        structured_logger.info("Onboarding notices", engine_id=engine_id, section=section, kinds=[p["kind"] for p in plans], sent=sent)


async def limit_body(request: Request) -> None:
    if int(request.headers.get("content-length") or 0) > MAX_BODY_BYTES:
        raise HTTPException(status_code=413, detail="That is too large")


def _trace(request: Request):
    return ob.pseudonymous_ip(last_forwarded_ip(request.headers.get("x-forwarded-for"))), (request.headers.get("x-cloud-trace-context", "")[:64] or None)


@engine_router.get("")
async def get_engine(engine_id: str, caller: dict = Depends(engine_gate)):
    """The engine, the caller's own role in it, and the progress tracker (per section: items open, answered, disagreed, final, approved; what is left; who is
    being waited on)."""
    snap = db.collection(ob.ENGINES).document(engine_id).get()
    if not snap.exists:
        raise HTTPException(status_code=404, detail="Not found")
    e = snap.to_dict() or {}
    m = caller.get("membership") or {}
    member = caller["via"] == "member"
    return {"engine_id": engine_id, "label": e.get("label"), "state": e.get("state"),
            "role": m.get("role") if member else "admin", "final_say": bool(m.get("final_say")) if member else False,
            **(gates.authority_view(db, engine_id, e, caller["subscriber_id"]) if member else {"can_mark_final": False, "may_mark": []}),
            "notifications_email": (m.get("notifications_email", True) is not False) if member else None,
            "template_version": tpl.TEMPLATE_VERSION, "progress": form.get_progress(db, engine_id, _viewer(caller))}


@engine_router.get("/sections/{section_key}")
async def get_section(engine_id: str, section_key: str, caller: dict = Depends(engine_gate)):
    """One section: its status and counts, and every item with its answer, who last changed it and when, its history, and its comments."""
    try:
        return form.get_section(db, engine_id, section_key, _viewer(caller))
    except form.FormError as e:
        raise _fail(e)


class ItemSave(BaseModel):
    value: Any = None
    choice: Optional[str] = Field(None, max_length=20)
    base_revision: int = Field(..., ge=0)               # the revision the owner was looking at; a stale save is refused with the current answer


@engine_router.put("/items/{item_id}")
async def save_item(engine_id: str, item_id: str, body: ItemSave, request: Request, caller: dict = Depends(engine_gate),
                    _size: None = Depends(limit_body)):
    """Autosave one answer (owners only; an administrator gets 404). 409 with the current answer if the item has moved on; nothing is written then."""
    _owner(caller)
    check_rate_limit(db, caller["subscriber_id"], "onboarding_autosave", limit=AUTOSAVE_LIMIT_PER_HOUR, window_seconds=3600)
    viewer, (ip, rid), outcome = _viewer(caller), _trace(request), {}
    try:
        doc = form.save_item(db, engine_id=engine_id, item_id=item_id, subscriber_id=caller["subscriber_id"], value=body.value, choice=body.choice,
                             base_revision=body.base_revision, ip_hash=ip, request_id=rid, outcome=outcome)
    except form.FormError as e:
        raise _fail(e, viewer, engine_id)
    await _notify(engine_id, doc["section"], outcome.get("reopened_from"))
    return {"item": form.item_view(db, engine_id, doc, viewer), "section_status": form.section_status(db, engine_id, doc["section"])}


class CommentIn(BaseModel):
    body: str = Field(..., max_length=tpl.COMMENT_CAP * 2)
    kind: str = Field("comment", max_length=10)


@engine_router.post("/items/{item_id}/comments")
async def add_comment(engine_id: str, item_id: str, body: CommentIn, request: Request, caller: dict = Depends(engine_gate),
                      _size: None = Depends(limit_body)):
    """A plain-text comment on an item. Owners and the administrator may comment (the administrator's are labelled admin). An owner may mark one 'disagree'."""
    if caller["via"] == "member":
        _owner(caller)
    check_rate_limit(db, caller.get("subscriber_id") or "admin", "onboarding_comment", limit=COMMENT_LIMIT_PER_HOUR, window_seconds=3600)
    ip, rid = _trace(request)
    try:
        made = form.add_comment(db, engine_id=engine_id, item_id=item_id, viewer=_viewer(caller), body=body.body, kind=body.kind, ip_hash=ip, request_id=rid)
    except form.FormError as e:
        raise _fail(e)
    if caller["via"] == "member" and body.kind == "disagree":
        await _notify(engine_id, None, None, item_id)          # a disagreement can take a section out of "ready"; this clears its mail flag
    return made


@engine_router.post("/comments/{comment_id}/resolve")
async def resolve_comment(engine_id: str, comment_id: str, request: Request, caller: dict = Depends(engine_gate)):
    """Resolve a comment (either owner may; the administrator may not). Resolving a 'disagree' comment ends that item's disagreement. [An addition to design 5.7.]"""
    _owner(caller)
    ip, rid = _trace(request)
    try:
        resolved = form.resolve_comment(db, engine_id=engine_id, comment_id=comment_id, subscriber_id=caller["subscriber_id"], ip_hash=ip, request_id=rid)
    except form.FormError as e:
        raise _fail(e)
    await _notify(engine_id, None, None, resolved.get("item_id"))      # resolving the last disagreement can make a section ready
    return resolved


class NewQuestion(BaseModel):
    wording: str = Field(..., max_length=tpl.WORDING_CAP * 2)
    centrality: str = Field(..., max_length=12)


class QuestionAction(BaseModel):
    action: str = Field(..., max_length=10)                          # "add" or "split"
    from_item: Optional[str] = Field(None, max_length=64)            # the question to split
    questions: List[NewQuestion] = Field(..., min_length=1, max_length=form.MAX_SPLIT)


@engine_router.post("/questions")
async def add_or_split_question(engine_id: str, body: QuestionAction, request: Request, caller: dict = Depends(engine_gate),
                                _size: None = Depends(limit_body)):
    """Add a question, or split one into two or more. The system assigns the ids ('<prefix>-qN', the next free number, never reused). [An addition to design 5.7.]"""
    _owner(caller)
    check_rate_limit(db, caller["subscriber_id"], "onboarding_question", limit=QUESTION_LIMIT_PER_HOUR, window_seconds=3600)
    viewer, (ip, rid), outcome = _viewer(caller), _trace(request), {}
    try:
        ids = form.add_questions(db, engine_id=engine_id, subscriber_id=caller["subscriber_id"], action=body.action, from_item=body.from_item,
                                 wordings=[q.model_dump() for q in body.questions], ip_hash=ip, request_id=rid, outcome=outcome)
    except form.FormError as e:
        raise _fail(e)
    await _notify(engine_id, "questions", outcome.get("reopened_from"))
    return {"ids": ids, "items": [form.item_view(db, engine_id, form.find_item(db, engine_id, i), viewer) for i in ids]}


class EntryIn(BaseModel):
    list_name: str = Field(..., alias="list", max_length=20)           # categories, horizons, mute, frontier or flagged
    text: str = Field(..., max_length=tpl.ENTRY_CAP * 2)


@engine_router.post("/entries")
async def add_entry(engine_id: str, body: EntryIn, request: Request, caller: dict = Depends(engine_gate), _size: None = Depends(limit_body)):
    """Create a keyword, horizon or mute entry. The system assigns the id ('<prefix>-kN', never reused). [The fourth addition to design 5.7, approved by Gary.]"""
    _owner(caller)
    check_rate_limit(db, caller["subscriber_id"], "onboarding_entry", limit=ENTRY_LIMIT_PER_HOUR, window_seconds=3600)
    viewer, (ip, rid), outcome = _viewer(caller), _trace(request), {}
    try:
        item_id = form.add_entry(db, engine_id=engine_id, subscriber_id=caller["subscriber_id"], list_name=body.list_name, text=body.text, ip_hash=ip, request_id=rid,
                                 outcome=outcome)
    except form.FormError as e:
        raise _fail(e)
    await _notify(engine_id, "keywords", outcome.get("reopened_from"))
    return {"id": item_id, "item": form.item_view(db, engine_id, form.find_item(db, engine_id, item_id), viewer)}


# ---- the first gate: Mark final, and delegation of final say (PR 3a-2) -----------------------------------------------------------------------------
@engine_router.post("/sections/final-all")
async def mark_all_final(engine_id: str, request: Request, caller: dict = Depends(engine_gate)):
    """Mark every READY section the caller may mark final. The final-say holder (or a delegate, for the sections delegated) only; an administrator gets 404, an
    owner without the power gets 403. Returns which sections were marked and which were left, with the reason for each. One audit event per section marked."""
    _owner(caller)
    check_rate_limit(db, caller["subscriber_id"], "onboarding_final", limit=FINAL_LIMIT_PER_HOUR, window_seconds=3600)
    ip, rid = _trace(request)
    try:
        out = gates.mark_all_final(db, engine_id=engine_id, subscriber_id=caller["subscriber_id"], ip_hash=ip, request_id=rid)
    except form.FormError as e:
        raise _fail(e)
    return {**out, "progress": form.get_progress(db, engine_id, _viewer(caller))}


@engine_router.post("/sections/{section_key}/final")
async def mark_section_final(engine_id: str, section_key: str, request: Request, caller: dict = Depends(engine_gate)):
    """Mark one section final. The final-say holder, or a delegate for THIS section; an administrator gets 404, any other owner 403. 409 (with a reason) if the
    section is not ready, is already final, was approved, or was sent back."""
    _owner(caller)
    check_rate_limit(db, caller["subscriber_id"], "onboarding_final", limit=FINAL_LIMIT_PER_HOUR, window_seconds=3600)
    ip, rid = _trace(request)
    try:
        out = gates.mark_final(db, engine_id=engine_id, section=section_key, subscriber_id=caller["subscriber_id"], ip_hash=ip, request_id=rid)
    except form.FormError as e:
        raise _fail(e)
    return {**out, "progress": form.get_progress(db, engine_id, _viewer(caller))}


class DelegationIn(BaseModel):
    to: str = Field("other_owner", max_length=20)          # the form never shows a person's id, so the delegate is "the other owner"
    scope: Any = "all"                                      # "all", or a list of section keys


@engine_router.get("/delegations")
async def get_delegations(engine_id: str, caller: dict = Depends(engine_gate)):
    """The final-say holder sees the engine's delegations; a delegate sees the ones that name them; any other owner sees none. An administrator gets 404."""
    _owner(caller)
    try:
        return {"delegations": gates.list_delegations(db, engine_id=engine_id, subscriber_id=caller["subscriber_id"])}
    except form.FormError as e:
        raise _fail(e)


@engine_router.put("/delegations")
async def put_delegation(engine_id: str, body: DelegationIn, request: Request, caller: dict = Depends(engine_gate), _size: None = Depends(limit_body)):
    """Delegate final say to the other owner of this engine (the holder only; a delegate cannot delegate further). A new delegation replaces the active one: both a
    revoke event and a create event are written. [An unchanged route of design 5.7.]"""
    _owner(caller)
    check_rate_limit(db, caller["subscriber_id"], "onboarding_delegation", limit=DELEGATION_LIMIT_PER_HOUR, window_seconds=3600)
    if body.to != "other_owner":
        raise HTTPException(status_code=400, detail='to must be "other_owner"')
    try:
        if not gates.is_holder(form._engine(db, engine_id), caller["subscriber_id"]):
            raise form.FormError(403, "Only the final-say owner can delegate final say")
        to_sid = gates.other_owner(db, engine_id, caller["subscriber_id"])
        if not to_sid:
            raise form.FormError(409, "There is no single other owner of this engine to delegate to")
        ip, rid = _trace(request)
        return gates.create_delegation(db, engine_id=engine_id, subscriber_id=caller["subscriber_id"], to_subscriber_id=to_sid, scope=body.scope, ip_hash=ip, request_id=rid)
    except form.FormError as e:
        raise _fail(e)


@engine_router.delete("/delegations/{delegation_id}")
async def delete_delegation(engine_id: str, delegation_id: str, request: Request, caller: dict = Depends(engine_gate)):
    """Revoke a delegation (the holder only). It stops working at the delegate's very next action."""
    _owner(caller)
    check_rate_limit(db, caller["subscriber_id"], "onboarding_delegation", limit=DELEGATION_LIMIT_PER_HOUR, window_seconds=3600)
    ip, rid = _trace(request)
    try:
        return gates.revoke_delegation(db, engine_id=engine_id, subscriber_id=caller["subscriber_id"], delegation_id=delegation_id, ip_hash=ip, request_id=rid)
    except form.FormError as e:
        raise _fail(e)


class NotificationsIn(BaseModel):
    email: StrictBool


@engine_router.put("/notifications")
async def put_notifications(engine_id: str, body: NotificationsIn, request: Request, caller: dict = Depends(engine_gate)):
    """An owner's own switch for the e-mails about final sections (on by default). Stored on their membership; audited. [An addition to design 5.7.]"""
    _owner(caller)
    check_rate_limit(db, caller["subscriber_id"], "onboarding_notifications", limit=NOTIFICATION_LIMIT_PER_HOUR, window_seconds=3600)
    ip, rid = _trace(request)
    try:
        return {"email": gates.set_notifications(db, engine_id=engine_id, subscriber_id=caller["subscriber_id"], email=body.email, ip_hash=ip, request_id=rid)}
    except form.FormError as e:
        raise _fail(e)


router.include_router(engine_router)


# ---- accepting an invitation ----------------------------------------------------------------------------------------------------------------------
class Consent(BaseModel):
    naming: str = "role"                                   # how the person may be named in the public repository (2.8); the default is by role only
    licence_confirmed: bool = False
    licence_other: Optional[str] = Field(None, max_length=200)
    lookups: bool = False                                  # consent for third-party scholarly lookups (2.8)
    acknowledged: bool = False                             # the statements: no address is ever published; the engine's records are kept in Gary's archives


class AcceptRequest(BaseModel):
    token: str = Field(..., min_length=1, max_length=ob.MAX_TOKEN_LENGTH)
    email: str = Field(..., min_length=3, max_length=254)
    name: str = Field(..., min_length=1, max_length=100)
    password: str = Field(..., max_length=PASSWORD_MAX_LENGTH)    # sets the password of a NEW account; an existing account's password is never changed
    consent: Consent


@router.post("/api/onboarding/invites/accept")
async def accept_invitation(body: AcceptRequest, request: Request, _origin: None = Depends(origin_guard)):
    """Accept an invitation. The emailed single-use token proves control of the mailbox; the address typed must also match the one the invitation was made
    for. Every refusal (unknown, used, expired, revoked, wrong address, closed engine, already a member) is the same 400. Rate limited per client and per
    address, failing CLOSED. No address, token or password reaches a log line."""
    client_ip = last_forwarded_ip(request.headers.get("x-forwarded-for"))
    norm = ob.normalise_address(body.email)
    check_rate_limit(db, client_ip, "onboarding_accept", limit=ACCEPT_LIMIT_PER_IP_PER_HOUR, window_seconds=3600, fail_closed=True)
    check_rate_limit(db, ob.address_hash(norm), "onboarding_accept_address", limit=ACCEPT_LIMIT_PER_ADDRESS_PER_HOUR, window_seconds=3600, fail_closed=True)
    if not db:
        raise HTTPException(status_code=503, detail="Firestore service is unavailable")
    # Checked for every request, whether or not the person already has an account, so the answer reveals nothing about accounts. The token is not spent.
    if not (PASSWORD_MIN_LENGTH <= len(body.password) <= PASSWORD_MAX_LENGTH):
        raise HTTPException(status_code=400, detail=PASSWORD_DETAIL)
    c = body.consent
    if not c.acknowledged or c.naming not in ob.NAMING_CHOICES:
        raise HTTPException(status_code=400, detail="Please complete the consent step.")
    consent = {"naming": c.naming, "licence_confirmed": bool(c.licence_confirmed), "licence_other": (c.licence_other or "").strip() or None, "lookups": bool(c.lookups)}
    now = ob._utcnow()
    new_fields = {
        'name': body.name.strip(), 'subscription_tier': 'free', 'subscription_status': 'active', 'created_at': now.isoformat(), 'last_login': now.isoformat(),
        'podcasts_generated': 0, 'podcasts_submitted_to_rss': 0, 'google_id': None, 'password_hash': hash_password(body.password),
        'display_name': None, 'initials': None, 'show_attribution': False,
    }
    try:
        result = ob.accept_invite(db, raw_token=body.token, email=body.email, new_account_fields=new_fields, consent=consent, now=now,
                                  ip_hash=ob.pseudonymous_ip(client_ip), request_id=request.headers.get("x-cloud-trace-context", "")[:64] or None)
    except Exception as e:
        structured_logger.error("Invitation could not be completed", error_type=type(e).__name__)
        raise HTTPException(status_code=500, detail="Could not complete the invitation. Nothing was changed.")
    if not result:
        raise HTTPException(status_code=400, detail=INVITATION_REFUSAL)
    structured_logger.info("Invitation accepted", engine_id=result["engine_id"], subscriber_id=result["subscriber_id"])
    return {"message": "Invitation accepted. You can now sign in.", "engine_id": result["engine_id"]}


# ---- admin: create and revoke --------------------------------------------------------------------------------------------------------------------
class InviteCreate(BaseModel):
    engine_id: str = Field(..., min_length=2, max_length=60)
    email: str = Field(..., min_length=3, max_length=254)           # entered once; used to send the email and to compute a hash; never stored
    final_say: bool = False
    can_generate: bool = True
    monthly_quota: Optional[Any] = Field(ob.DEFAULT_INVITE_QUOTA)    # an integer 0..200, or null for unlimited; the default is 10
    expires_days: Any = ob.INVITE_DEFAULT_DAYS


@router.post("/api/admin/onboarding/invites")
async def create_invitation(body: InviteCreate, request: Request, admin_auth: bool = Depends(verify_admin_api_key)):
    """Create one invitation and email it. The response never contains the address or the token."""
    client_ip = last_forwarded_ip(request.headers.get("x-forwarded-for"))
    check_rate_limit(db, client_ip, "onboarding_invite_create", limit=ADMIN_INVITE_LIMIT_PER_HOUR, window_seconds=3600, fail_closed=True)
    if not db:
        raise HTTPException(status_code=503, detail="Firestore service is unavailable")
    try:
        made = ob.create_invite(db, engine_id=body.engine_id, email=body.email, final_say=body.final_say, can_generate=body.can_generate,
                                monthly_quota=body.monthly_quota, expires_days=body.expires_days, ip_hash=ob.pseudonymous_ip(client_ip),
                                request_id=request.headers.get("x-cloud-trace-context", "")[:64] or None)
    except ob.InviteError as e:
        raise HTTPException(status_code=e.status, detail=e.message)
    link = f"{ob.ACCEPT_PAGE_URL}#token={made['raw_token']}"
    days = int(body.expires_days)
    sent = await email_service.send_invitation_email(made["address"], link, days, made["engine_label"])
    structured_logger.info("Invitation created", invite_id=made["invite_id"], engine_id=body.engine_id, email_sent=bool(sent))
    return {"invite_id": made["invite_id"], "engine_id": body.engine_id, "expires_at": made["expires_at"], "email_sent": bool(sent)}


@router.get("/api/admin/onboarding/invites")
async def list_invitations(request: Request, engine_id: str = Query(..., min_length=2, max_length=60), admin_auth: bool = Depends(verify_admin_api_key)):
    """The invitations of one engine, newest first: id, engine, status (unused, used, expired or revoked), final_say, can_generate, monthly_quota and the
    four dates. Never the address hash, the token hash or the account that used an invitation."""
    client_ip = last_forwarded_ip(request.headers.get("x-forwarded-for"))
    check_rate_limit(db, client_ip, "onboarding_invite_list", limit=ADMIN_LIST_LIMIT_PER_HOUR, window_seconds=3600, fail_closed=True)
    if not db:
        raise HTTPException(status_code=503, detail="Firestore service is unavailable")
    if not ob.ENGINE_ID_RE.match(engine_id) or "__" in engine_id:
        raise HTTPException(status_code=400, detail="engine_id is not valid")
    return {"engine_id": engine_id, "invites": ob.list_invites(db, engine_id)}


@router.delete("/api/admin/onboarding/invites/{invite_id}")
async def revoke_invitation(invite_id: str, request: Request, admin_auth: bool = Depends(verify_admin_api_key)):
    """Revoke an invitation. An unused one stops working. A used one also removes the engine membership and clears can_generate and the quota (design Q17;
    the account and its episodes stay). Never changes the administrator's own account."""
    if not db:
        raise HTTPException(status_code=503, detail="Firestore service is unavailable")
    client_ip = last_forwarded_ip(request.headers.get("x-forwarded-for"))
    result = ob.revoke_invite(db, invite_id, admin_subscriber_id=generate_subscriber_id(ADMIN_SUBSCRIBER_EMAIL), ip_hash=ob.pseudonymous_ip(client_ip),
                              request_id=request.headers.get("x-cloud-trace-context", "")[:64] or None)
    if result is None:
        raise HTTPException(status_code=404, detail="No such invitation")
    return {"invite_id": invite_id, "outcome": result["outcome"]}


# ---- admin: Gary's review (PR 3b-1) -----------------------------------------------------------------------------------------------------------------------
def admin_only(_origin: None = Depends(origin_guard), x_admin_api_key: Optional[str] = Header(None, alias="X-Admin-API-Key"),
               x_subscriber_token: Optional[str] = Header(None, alias="X-Subscriber-Token")) -> None:
    """The review routes are for the administrator alone. A request that carries a SESSION (a member of any engine, or any signed-in person) without the admin key
    is told 404, as an owner is on every route that is not theirs: the routes' existence is no business of an owner. A request with no credential at all is told 401,
    so the dashboard can ask for the key. The key is read from its header only."""
    if _admin_key_matches(x_admin_api_key):
        return
    if x_subscriber_token:
        raise HTTPException(status_code=404, detail="Not found")
    raise HTTPException(status_code=401, detail="Admin API key required. Provide via X-Admin-API-Key header")


def _admin_limit(request: Request, name: str, limit: int) -> None:
    check_rate_limit(db, last_forwarded_ip(request.headers.get("x-forwarded-for")), name, limit=limit, window_seconds=3600, fail_closed=True)
    if not db:
        raise HTTPException(status_code=503, detail="Firestore service is unavailable")


def _valid_engine(engine_id: str) -> None:
    if not isinstance(engine_id, str) or not ob.ENGINE_ID_RE.match(engine_id) or "__" in engine_id:
        raise HTTPException(status_code=404, detail="Not found")


@router.get("/api/admin/onboarding/engines", dependencies=[Depends(admin_only)])
async def admin_list_engines(request: Request):
    """Every engine: its state, repository, and per section the status, revision, age in that status and who it waits on (as a role label, never an id)."""
    _admin_limit(request, "onboarding_review_read", ADMIN_REVIEW_LIMIT_PER_HOUR)
    return {"engines": review.list_engines(db)}


@router.get("/api/admin/onboarding/engines/{engine_id}", dependencies=[Depends(admin_only)])
async def admin_get_engine(engine_id: str, request: Request):
    """One engine for review: the overview and, per section, every item with its history and comment threads (authors as roles). Read only."""
    _valid_engine(engine_id)
    _admin_limit(request, "onboarding_review_read", ADMIN_REVIEW_LIMIT_PER_HOUR)
    try:
        return review.engine_detail(db, engine_id)
    except form.FormError as e:
        raise _fail(e)


@router.get("/api/admin/onboarding/engines/{engine_id}/diff", dependencies=[Depends(admin_only)])
async def admin_section_diff(engine_id: str, request: Request, section: str = Query(..., min_length=1, max_length=30)):
    """The proposed output files of a FINAL or APPROVED section against the repository's main (fetched with no token; the base commit is shown). An engine with no
    repository is diffed against empty and the response says so. A failed fetch degrades to 'current file unavailable'; it is never a 500."""
    _valid_engine(engine_id)
    _admin_limit(request, "onboarding_review_read", ADMIN_REVIEW_LIMIT_PER_HOUR)
    try:
        return await asyncio.to_thread(review.section_diff, db, engine_id, section)
    except form.FormError as e:
        raise _fail(e)


class DecisionIn(BaseModel):
    note: Optional[str] = Field(None, max_length=review.NOTE_CAP * 2)
    expected_revision: StrictInt = Field(..., ge=0)         # the revision and hash the reviewer was looking at: a section that changed since is refused with 409
    expected_content_sha256: str = Field(..., min_length=64, max_length=64)


async def _decide(engine_id: str, section_key: str, decision: str, body: DecisionIn, request: Request) -> dict:
    _valid_engine(engine_id)
    _admin_limit(request, "onboarding_review_decide", ADMIN_DECISION_LIMIT_PER_HOUR)
    ip, rid = _trace(request)
    try:
        out = review.decide(db, engine_id=engine_id, section=section_key, decision=decision, expected_revision=body.expected_revision,
                            expected_content_sha256=body.expected_content_sha256, note=body.note, ip_hash=ip, request_id=rid)
    except form.FormError as e:
        raise _fail(e)
    try:
        plans = review.plan_decision_mail(db, engine_id=engine_id, section=section_key, decision=decision)
    except Exception as e:                      # the decision is already committed; a mail problem must not undo or fail it
        structured_logger.error("Onboarding decision notice could not be planned", error_type=type(e).__name__)
        plans = []
    link, sent = f"{ENGINE_PAGE_URL}?engine={engine_id}", 0
    for plan in plans:
        for address in plan["to"]:
            try:
                if await asyncio.wait_for(email_service.send_onboarding_notice(address, plan["kind"], plan["engine_label"], plan["section_title"], link), NOTICE_TIMEOUT_SECONDS):
                    sent += 1
            except Exception as e:
                structured_logger.error("Onboarding notice could not be sent", error_type=type(e).__name__)
    structured_logger.info("Onboarding review decision", engine_id=engine_id, section=section_key, decision=decision, sent=sent)
    return {**out, "mail_sent": sent}


@router.post("/api/admin/onboarding/engines/{engine_id}/sections/{section_key}/approve", dependencies=[Depends(admin_only)])
async def admin_approve(engine_id: str, section_key: str, body: DecisionIn, request: Request, _size: None = Depends(limit_body)):
    """Approve a FINAL section at the revision and content hash the reviewer saw (409 otherwise). The note is optional. Frozen until an owner edits it."""
    return await _decide(engine_id, section_key, "approve", body, request)


@router.post("/api/admin/onboarding/engines/{engine_id}/sections/{section_key}/reject", dependencies=[Depends(admin_only)])
async def admin_reject(engine_id: str, section_key: str, body: DecisionIn, request: Request, _size: None = Depends(limit_body)):
    """Send a FINAL section back to DRAFT. The note is required; the owners see it until the section is next marked final."""
    return await _decide(engine_id, section_key, "reject", body, request)
