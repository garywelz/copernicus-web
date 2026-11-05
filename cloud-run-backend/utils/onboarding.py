"""Invitations and engine membership (onboarding PR 2; docs/design/ENGINE_ONBOARDING_FORM.md section 3.1, 5.6, 5.7, 8.1).

An invitation carries the permissions an account will receive (can_generate, monthly_quota, the engine membership). The administrator enters the
invitee's address once; the server normalises it (trimmed, lower-cased) and stores ONLY its sha256, never the address, plus the sha256 of a random single-use
token. The emailed link carries the token (in the URL fragment, which a browser never sends to a server). The token is what proves the person controls the
mailbox; the address hash is a second check, not a credential.

Reused from PR 0 (utils/credential_tokens.py): hash_token (sha256 of a token), _run_in_transaction (the Firestore transaction runner that tests replace),
MAX_TOKEN_LENGTH and the password length limits. The token is generated the same way (secrets.token_urlsafe(32)) and is single use, expiring and stored
only as a hash; it lives on the invitation document (not in credential_tokens) because an invitee may not have an account yet.

Every state change writes an onboarding_events record IN THE SAME TRANSACTION as the change, so there is no change without a record. No event, invitation
or log line holds an address or a token.
"""
import hashlib
import hmac
import json
import re
import secrets
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

from google.cloud import firestore

from utils.credential_tokens import MAX_TOKEN_LENGTH, _run_in_transaction, hash_token
from utils.generation_quota import validate_quota_value

ENGINES = "onboarding_engines"
MEMBERS = "onboarding_members"
INVITES = "onboarding_invites"
EVENTS = "onboarding_events"

ACCEPT_PAGE_URL = "https://www.copernicusai.fyi/onboarding/accept.html"
ALLOWED_ORIGIN = "https://www.copernicusai.fyi"       # the only browser origin the onboarding routes accept (design 9, defence in depth)

INVITE_DEFAULT_DAYS = 7
INVITE_MAX_DAYS = 30
DEFAULT_INVITE_QUOTA = 10                              # design 3.1 / Q14

CONSENT_VERSION = "1"
NAMING_CHOICES = ("role", "name", "name_and_role", "none")     # design 2.8; the default is by role only

ENGINE_ID_RE = re.compile(r"^[a-z0-9][a-z0-9-]{1,40}$")
_ADDRESS_FORBIDDEN = re.compile(r"[\s<>\"',;()\[\]\\\x00-\x1f\x7f]")


def normalise_address(raw: Any) -> str:
    """Trimmed and lower-cased (design Q16). Does not validate."""
    return raw.strip().lower() if isinstance(raw, str) else ""


def address_ok(normalised: str) -> bool:
    """A plain address shape: one @, a dotted domain, no spaces or control or quoting characters, at most 254 characters."""
    if not normalised or len(normalised) > 254 or _ADDRESS_FORBIDDEN.search(normalised):
        return False
    local, _, domain = normalised.partition("@")
    return bool(local) and "@" not in domain and "." in domain and not domain.startswith(".") and not domain.endswith(".") and ".." not in domain


def address_hash(normalised: str) -> str:
    return hashlib.sha256(normalised.encode()).hexdigest()


def address_variants(raw: str) -> List[str]:
    """The spellings an existing account may be stored under (its id is the sha256 of the address AS TYPED at registration): the address as typed, the
    normalised form, all upper case, and first letter upper case. An account stored under some other mixed-case spelling is not found (design 3.1 accepts
    that two spellings of one mailbox can be two accounts)."""
    typed = raw.strip()
    norm = typed.lower()
    out: List[str] = []
    for v in (typed, norm, norm.upper(), norm[:1].upper() + norm[1:]):
        if v and v not in out:
            out.append(v)
    return out


def candidate_subscriber_ids(raw: str) -> List[str]:
    ids: List[str] = []
    for v in address_variants(raw):
        full = hashlib.sha256(v.encode()).hexdigest()
        for sid in (full, full[:16]):                       # the older 16-character id format is still on some accounts
            if sid not in ids:
                ids.append(sid)
    return ids


def member_id(engine_id: str, subscriber_id: str) -> str:
    return f"{engine_id}__{subscriber_id}"


def pseudonymous_ip(ip: Optional[str]) -> Optional[str]:
    """A stable pseudonym for the audit log (a plain hash of an IPv4 address can be brute-forced; this is a pseudonym, not anonymisation)."""
    return hashlib.sha256(f"onboarding-ip:{ip}".encode()).hexdigest()[:32] if ip else None


def _sha(obj: Any) -> str:
    return hashlib.sha256(json.dumps(obj, sort_keys=True, default=str).encode()).hexdigest()


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _event(transaction, db, *, engine_id: Optional[str], actor: str, actor_role: str, action: str, target: Optional[str], before: Any, after: Any,
           ip_hash: Optional[str], request_id: Optional[str], now: datetime) -> None:
    """Append one audit record in the caller's transaction. Holds ids and hashes only: never an address, a token or a name."""
    transaction.set(db.collection(EVENTS).document(uuid.uuid4().hex), {
        "ts": now.isoformat(), "engine_id": engine_id, "actor_subscriber_id": actor, "actor_role": actor_role, "action": action, "target": target,
        "before_sha256": _sha(before) if before is not None else None, "after_sha256": _sha(after) if after is not None else None,
        "ip_hash": ip_hash, "request_id": request_id,
    })


def _expired(iso: Any, now: datetime) -> bool:
    try:
        return datetime.fromisoformat(iso) < now
    except (TypeError, ValueError):
        return True


# ---- creating an invitation (admin) ---------------------------------------------------------------------------------------------------------------
class InviteError(Exception):
    def __init__(self, status: int, message: str):
        super().__init__(message)
        self.status, self.message = status, message


def _create_in(transaction, db, invite_id: str, doc: dict, engine_id: str, final_say: bool, now: datetime, ip_hash, request_id):
    engine_ref = db.collection(ENGINES).document(engine_id)
    engine_snap = engine_ref.get(transaction=transaction)
    if not engine_snap.exists:
        raise InviteError(404, "No such engine")
    engine = engine_snap.to_dict() or {}
    if engine.get("state") != "open":
        raise InviteError(409, "The engine is not open for new members")
    pending_ref = None
    if final_say:
        if engine.get("final_say_subscriber_id"):
            raise InviteError(409, "The engine already has a final-say holder")
        pending_id = engine.get("pending_final_say_invite_id")
        if pending_id:
            pending_ref = db.collection(INVITES).document(pending_id)
            pending = pending_ref.get(transaction=transaction)
            p = pending.to_dict() if pending.exists else None
            if p and not p.get("used_at") and not p.get("revoked_at") and not _expired(p.get("expires_at"), now):
                raise InviteError(409, "A final-say invitation for this engine is already outstanding")
    # All reads are done; writes follow.
    transaction.set(db.collection(INVITES).document(invite_id), doc)
    if final_say:
        transaction.update(engine_ref, {"pending_final_say_invite_id": invite_id})
    _event(transaction, db, engine_id=engine_id, actor="admin", actor_role="admin", action="invite", target=invite_id, before=None,
           after={"final_say": final_say, "can_generate": doc["can_generate"], "monthly_quota": doc["monthly_quota"], "expires_at": doc["expires_at"]},
           ip_hash=ip_hash, request_id=request_id, now=now)


def create_invite(db, *, engine_id: str, email: str, final_say: bool = False, can_generate: bool = True, monthly_quota: Optional[int] = DEFAULT_INVITE_QUOTA,
                  expires_days: int = INVITE_DEFAULT_DAYS, now: Optional[datetime] = None, ip_hash: Optional[str] = None,
                  request_id: Optional[str] = None) -> Dict[str, Any]:
    """Create one invitation. Returns {invite_id, raw_token, expires_at, address}: the raw token and the normalised address are for the one email only and
    must never be stored, returned to a client or logged. Raises InviteError."""
    now = now or _utcnow()
    if not isinstance(engine_id, str) or not ENGINE_ID_RE.match(engine_id) or "__" in engine_id:
        raise InviteError(400, "engine_id is not valid")
    norm = normalise_address(email)
    if not address_ok(norm):
        raise InviteError(400, "The address is not valid")
    try:
        quota = validate_quota_value(monthly_quota)
    except ValueError as e:
        raise InviteError(400, str(e))
    if isinstance(expires_days, bool) or not isinstance(expires_days, int) or not 1 <= expires_days <= INVITE_MAX_DAYS:
        raise InviteError(400, f"expires_days must be a whole number from 1 to {INVITE_MAX_DAYS}")
    ehash = address_hash(norm)
    # Best effort (not transactional): one outstanding invitation per engine and address. Two simultaneous requests could both pass; each invitation
    # is still single use, and the second acceptance is refused because the first already made the membership.
    for d in db.collection(INVITES).where("engine_id", "==", engine_id).where("email_sha256", "==", ehash).stream():
        x = d.to_dict() or {}
        if not x.get("used_at") and not x.get("revoked_at") and not _expired(x.get("expires_at"), now):
            raise InviteError(409, "An invitation for this address and engine is already outstanding; revoke it first")
    raw = secrets.token_urlsafe(32)
    invite_id = uuid.uuid4().hex
    expires = now + timedelta(days=expires_days)
    doc = {"engine_id": engine_id, "email_sha256": ehash, "roles": ["owner"], "final_say": bool(final_say), "can_generate": bool(can_generate),
           "monthly_quota": quota, "token_hash": hash_token(raw), "expires_at": expires.isoformat(), "created_by": "admin", "created_at": now.isoformat(),
           "used_at": None, "used_by_subscriber_id": None, "revoked_at": None, "revoked_by": None}
    _run_in_transaction(db, _create_in, db, invite_id, doc, engine_id, bool(final_say), now, ip_hash, request_id)
    return {"invite_id": invite_id, "raw_token": raw, "expires_at": doc["expires_at"], "address": norm}


# ---- listing invitations (admin) --------------------------------------------------------------------------------------------------------------------
INVITE_LIST_FIELDS = ("invite_id", "engine_id", "status", "final_say", "can_generate", "monthly_quota", "created_at", "expires_at", "used_at", "revoked_at")


def invite_status(inv: dict, now: datetime) -> str:
    """revoked, used, expired or unused, in that order of precedence (a used invitation that was later revoked reads as revoked)."""
    if inv.get("revoked_at"):
        return "revoked"
    if inv.get("used_at"):
        return "used"
    if _expired(inv.get("expires_at"), now):
        return "expired"
    return "unused"


def list_invites(db, engine_id: str, now: Optional[datetime] = None) -> List[Dict[str, Any]]:
    """The invitations of one engine, newest first, as an EXPLICIT allow-list of fields. The address hash, the token hash and the id of the account that used
    an invitation are never in the result: a field cannot leak by being added to the stored document later."""
    now = now or _utcnow()
    out = []
    for d in db.collection(INVITES).where("engine_id", "==", engine_id).stream():
        inv = d.to_dict() or {}
        row = {"invite_id": d.id, "engine_id": inv.get("engine_id"), "status": invite_status(inv, now), "final_say": bool(inv.get("final_say")),
               "can_generate": bool(inv.get("can_generate")), "monthly_quota": inv.get("monthly_quota"), "created_at": inv.get("created_at"),
               "expires_at": inv.get("expires_at"), "used_at": inv.get("used_at"), "revoked_at": inv.get("revoked_at")}
        out.append({k: row[k] for k in INVITE_LIST_FIELDS})
    out.sort(key=lambda r: r.get("created_at") or "", reverse=True)
    return out


# ---- accepting an invitation ----------------------------------------------------------------------------------------------------------------------
def _accept_in(transaction, db, invite_id: str, token_hash: str, email_sha: str, subscriber_id: str, new_account: Optional[dict], consent: dict,
               now: datetime, ip_hash, request_id) -> Optional[dict]:
    invite_ref = db.collection(INVITES).document(invite_id)
    invite_snap = invite_ref.get(transaction=transaction)
    if not invite_snap.exists:
        return None
    inv = invite_snap.to_dict() or {}
    if inv.get("used_at") or inv.get("revoked_at") or _expired(inv.get("expires_at"), now):
        return None
    if not hmac.compare_digest(str(inv.get("token_hash", "")), token_hash) or not hmac.compare_digest(str(inv.get("email_sha256", "")), email_sha):
        return None
    engine_id = inv["engine_id"]
    engine_ref = db.collection(ENGINES).document(engine_id)
    engine_snap = engine_ref.get(transaction=transaction)
    if not engine_snap.exists or (engine_snap.to_dict() or {}).get("state") != "open":
        return None
    engine = engine_snap.to_dict() or {}
    sub_ref = db.collection("subscribers").document(subscriber_id)
    sub_snap = sub_ref.get(transaction=transaction)
    member_ref = db.collection(MEMBERS).document(member_id(engine_id, subscriber_id))
    if member_ref.get(transaction=transaction).exists:
        return None                                        # already a member of this engine
    holder = engine.get("final_say_subscriber_id")
    if inv.get("final_say") and holder and holder != subscriber_id:
        return None                                        # final say is exclusive per engine
    if not sub_snap.exists and not new_account:
        return None
    # All reads are done; every write below is buffered and committed together, or none is.
    perms = {"can_generate": bool(inv.get("can_generate")), "monthly_quota": inv.get("monthly_quota")}
    if sub_snap.exists:
        transaction.update(sub_ref, perms)                 # never the password, the address, or a session
        created = False
    else:
        transaction.set(sub_ref, {**new_account, **perms})
        created = True
    transaction.set(member_ref, {
        "engine_id": engine_id, "subscriber_id": subscriber_id, "role": "owner", "final_say": bool(inv.get("final_say")), "status": "active",
        "consent": {**consent, "version": CONSENT_VERSION, "at": now.isoformat()}, "joined_at": now.isoformat(), "invite_id": invite_id})
    engine_updates: Dict[str, Any] = {}
    if inv.get("final_say"):
        engine_updates["final_say_subscriber_id"] = subscriber_id
    if engine.get("pending_final_say_invite_id") == invite_id:
        engine_updates["pending_final_say_invite_id"] = None
    if engine_updates:
        transaction.update(engine_ref, engine_updates)
    transaction.update(invite_ref, {"used_at": now.isoformat(), "used_by_subscriber_id": subscriber_id})
    _event(transaction, db, engine_id=engine_id, actor=subscriber_id, actor_role="invitee", action="accept", target=invite_id,
           before={"invite": "unused"}, after={"invite": "used", "member": "active", "account_created": created, **perms}, ip_hash=ip_hash,
           request_id=request_id, now=now)
    _event(transaction, db, engine_id=engine_id, actor=subscriber_id, actor_role="owner", action="consent", target=member_id(engine_id, subscriber_id),
           before=None, after={**consent, "version": CONSENT_VERSION}, ip_hash=ip_hash, request_id=request_id, now=now)
    return {"engine_id": engine_id, "subscriber_id": subscriber_id, "account_created": created}


def find_invite_by_token(db, raw_token: Any) -> Optional[tuple]:
    """(invite_id, token_hash) for a presented token, or None. Reads only the hash."""
    if not isinstance(raw_token, str) or not raw_token or len(raw_token) > MAX_TOKEN_LENGTH:
        return None
    th = hash_token(raw_token)
    for d in db.collection(INVITES).where("token_hash", "==", th).limit(1).stream():
        return d.id, th
    return None


SUBSCRIBER_SCAN_CAP = 5000


def existing_subscriber_id(db, raw_email: str) -> Optional[str]:
    """The id of the account that already belongs to this address, or None. First the cheap lookups (the address as typed, normalised, upper case, first
    letter upper case, each in both id formats). If none exists, one scan of the stored addresses compares them case-insensitively, so an account made under
    an unusual spelling (an id is the hash of the address AS TYPED at registration) is still found and given the permissions, rather than a second account
    being created for the same person. The scan reads only the address field and is bounded; it runs only on an accepted-invitation request, which is
    rate limited."""
    for sid in candidate_subscriber_ids(raw_email):
        if db.collection("subscribers").document(sid).get().exists:
            return sid
    norm = normalise_address(raw_email)
    seen = 0
    for d in db.collection("subscribers").select(["email"]).stream():
        seen += 1
        if seen > SUBSCRIBER_SCAN_CAP:
            break
        if normalise_address((d.to_dict() or {}).get("email")) == norm:
            return d.id
    return None


def accept_invite(db, *, raw_token: str, email: str, new_account_fields: Optional[dict], consent: dict, now: Optional[datetime] = None,
                  ip_hash: Optional[str] = None, request_id: Optional[str] = None) -> Optional[dict]:
    """Spend an invitation. In ONE transaction: check it is unused, unexpired and unrevoked and that BOTH the token and the address hash match; create the
    account (or add the permissions to the existing one); create the membership with the consent record; mark the invitation used; write the events.
    Returns {engine_id, subscriber_id, account_created}, or None for every kind of refusal (unknown, used, expired, revoked, wrong address, wrong token,
    engine closed, already a member): the caller cannot and must not tell which.

    `new_account_fields` is the subscriber document to create when no account exists for the address (it carries the password HASH); an existing account is
    only given the invitation's permissions: its password, address and sessions are never touched."""
    now = now or _utcnow()
    found = find_invite_by_token(db, raw_token)
    norm = normalise_address(email)
    if not found or not address_ok(norm):
        return None
    invite_id, token_hash = found
    subscriber_id = existing_subscriber_id(db, email)
    new_account = None
    if subscriber_id is None:
        subscriber_id = address_hash(norm)
        new_account = dict(new_account_fields or {}, subscriber_id=subscriber_id, email=norm) if new_account_fields else None
    return _run_in_transaction(db, _accept_in, db, invite_id, token_hash, address_hash(norm), subscriber_id, new_account, consent, now, ip_hash, request_id)


# ---- revoking (admin) ------------------------------------------------------------------------------------------------------------------------------
def _revoke_in(transaction, db, invite_id: str, admin_subscriber_id: Optional[str], keep_permissions: bool, now: datetime, ip_hash, request_id):
    invite_ref = db.collection(INVITES).document(invite_id)
    snap = invite_ref.get(transaction=transaction)
    if not snap.exists:
        return None
    inv = snap.to_dict() or {}
    if inv.get("revoked_at"):
        return {"outcome": "already_revoked"}
    engine_id = inv["engine_id"]
    engine_ref = db.collection(ENGINES).document(engine_id)
    engine_snap = engine_ref.get(transaction=transaction)
    engine = engine_snap.to_dict() if engine_snap.exists else {}
    sid = inv.get("used_by_subscriber_id")
    member_ref = sub_ref = None
    member_exists = False
    if inv.get("used_at") and sid:
        member_ref = db.collection(MEMBERS).document(member_id(engine_id, sid))
        member_exists = member_ref.get(transaction=transaction).exists
        sub_ref = db.collection("subscribers").document(sid)
        sub_exists = sub_ref.get(transaction=transaction).exists
    # All reads are done; writes follow.
    transaction.update(invite_ref, {"revoked_at": now.isoformat(), "revoked_by": "admin"})
    updates: Dict[str, Any] = {}
    if engine.get("pending_final_say_invite_id") == invite_id:
        updates["pending_final_say_invite_id"] = None
    outcome = "revoked_unused"
    if inv.get("used_at") and sid:
        outcome = "revoked_member"
        if member_exists:
            transaction.delete(member_ref)
        if engine.get("final_say_subscriber_id") == sid:
            updates["final_say_subscriber_id"] = None
        # Design Q17: revocation also clears can_generate and the quota (the account and its episodes stay). Never on the administrator's own account, and
        # not when the person is still a member of another engine.
        if sub_exists and sid != admin_subscriber_id and not keep_permissions:
            transaction.update(sub_ref, {"can_generate": False, "monthly_quota": firestore.DELETE_FIELD})
    if updates and engine_snap.exists:
        transaction.update(engine_ref, updates)
    _event(transaction, db, engine_id=engine_id, actor="admin", actor_role="admin", action="revoke_invite" if outcome == "revoked_unused" else "revoke_member",
           target=invite_id, before={"invite": "used" if inv.get("used_at") else "unused"}, after={"invite": "revoked", "outcome": outcome}, ip_hash=ip_hash,
           request_id=request_id, now=now)
    return {"outcome": outcome, "engine_id": engine_id}


def revoke_invite(db, invite_id: str, *, admin_subscriber_id: Optional[str] = None, now: Optional[datetime] = None, ip_hash: Optional[str] = None,
                  request_id: Optional[str] = None) -> Optional[dict]:
    """Revoke an invitation. An unused one simply stops working. A used one also removes the engine membership and clears can_generate and the quota (Q17),
    unless the account is the administrator's own or is still a member of another engine. Returns None when there is no such invitation."""
    now = now or _utcnow()
    keep = False
    if isinstance(invite_id, str) and invite_id:
        snap = db.collection(INVITES).document(invite_id).get()
        inv = snap.to_dict() if snap.exists else None
        if inv and inv.get("used_by_subscriber_id"):
            sid, here = inv["used_by_subscriber_id"], inv.get("engine_id")
            others = [d for d in db.collection(MEMBERS).where("subscriber_id", "==", sid).stream() if (d.to_dict() or {}).get("engine_id") != here]
            keep = bool(others)
    return _run_in_transaction(db, _revoke_in, db, invite_id, admin_subscriber_id, keep, now, ip_hash, request_id)


# ---- who is the caller (the membership dependency's data access) -----------------------------------------------------------------------------------
def subscriber_for_token(db, raw_token: Optional[str]) -> Optional[str]:
    """The subscriber id a session token belongs to, or None (unknown, expired or malformed)."""
    from utils.subscriber_helpers import verify_session_token
    if not isinstance(raw_token, str) or not raw_token or len(raw_token) > MAX_TOKEN_LENGTH:
        return None
    for d in db.collection("subscribers").where("session_token_hash", "==", hash_token(raw_token)).limit(1).stream():
        return d.id if verify_session_token(d.to_dict() or {}, raw_token) else None
    return None


def active_membership(db, engine_id: str, subscriber_id: str) -> Optional[dict]:
    """The caller's ACTIVE membership of the engine, or None. Guarded before any lookup: a missing, empty or non-string id or engine would build a key like
    'engine__None' or 'engine__', and a record stored under such a key must never match. The record must also carry exactly this engine and this subscriber."""
    if not (isinstance(subscriber_id, str) and subscriber_id.strip() and isinstance(engine_id, str) and engine_id.strip()):
        return None
    snap = db.collection(MEMBERS).document(member_id(engine_id, subscriber_id)).get()
    m = snap.to_dict() if snap.exists else None
    if not m or m.get("status") != "active" or m.get("subscriber_id") != subscriber_id or m.get("engine_id") != engine_id:
        return None
    return m
