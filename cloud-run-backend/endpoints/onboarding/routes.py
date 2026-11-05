"""Onboarding routes, PR 2: invitations and engine roles (docs/design/ENGINE_ONBOARDING_FORM.md 3.1, 5.7, 8.1). There is no form yet.

  POST   /api/onboarding/invites/accept                 the holder of a valid single-use token (no session: the token is the proof)
  GET    /api/onboarding/engines/{engine_id}            a member of that engine, or the admin
  POST   /api/admin/onboarding/invites                  admin key: create an invitation (the address is entered once and kept only as a hash)
  GET    /api/admin/onboarding/invites?engine_id=       admin key: list one engine's invitations (never an address or token hash)
  DELETE /api/admin/onboarding/invites/{invite_id}      admin key: revoke an unused invitation; a used one also removes the membership (Q17)

DEFAULT DENY: every route under /api/onboarding/engines/{engine_id}/... passes through `engine_gate`, which resolves the caller to a membership of that engine
or to the admin before any handler runs. Anyone else (signed in or not, member of another engine or none, engine real or invented) gets the same 404.
The accept route is the one exception; it is not an engine route and answers one and the same refusal for every kind of invalid invitation.
"""
from typing import Any, Optional

from fastapi import APIRouter, Depends, Header, HTTPException, Query, Request
from pydantic import BaseModel, Field

from config.constants import ADMIN_SUBSCRIBER_EMAIL
from config.database import db
from email_service import EmailService
from utils import onboarding as ob
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


@engine_router.get("")
async def get_engine(engine_id: str, caller: dict = Depends(engine_gate)):
    """The engine, and the caller's own role in it. (Sections, progress and the form arrive in PR 3.)"""
    snap = db.collection(ob.ENGINES).document(engine_id).get()
    if not snap.exists:
        raise HTTPException(status_code=404, detail="Not found")
    e = snap.to_dict() or {}
    m = caller.get("membership") or {}
    return {"engine_id": engine_id, "label": e.get("label"), "state": e.get("state"),
            "role": m.get("role") if caller["via"] == "member" else "admin", "final_say": bool(m.get("final_say")) if caller["via"] == "member" else False}


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
    sent = await email_service.send_invitation_email(made["address"], link, days)
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
