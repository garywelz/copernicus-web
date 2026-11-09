"""The change bundle (onboarding PR 3b-2; docs/design/ENGINE_ONBOARDING_FORM.md 5.2 option (ii), 5.3, 5.4, 6): the approved sections, rendered into the files they
change, packaged as ONE JSON document that Gary's agent re-verifies (scripts/onboarding/verify_bundle.py) and turns into a pull request. The web backend holds no
repository credential: it reads the public repository with no token and never writes to it.

BUILT FROM APPROVED REVISIONS ONLY. A section is included only if its status is `approved` and its content still hashes to the hash that was approved. A final
section that Gary has not approved is not in a bundle. With no sections named, every approved section is included.

THE BASE IS RECORDED. For an engine with a repository the bundle names the commit of `main` the files were diffed against and carries each file's git blob sha
(null for an add), so the agent can tell whether anything moved. If the commit or a base file cannot be read, no bundle is built (503): an honest base or none.

BLOCKED. A bundle whose linter checks (utils/onboarding_lint.py) do not all pass is STORED with status `blocked` and its failed checks, and cannot be downloaded as
ready (409). The reasons name a file or an item, never the offending text.

STATES (onboarding_bundles.status): created -> exported (first download) -> merged (Gary pastes the pull request URL); `blocked` and `superseded` are terminal
(`superseded`: the repository's main moved on). Every change writes its onboarding_events record in the same transaction.

THE FORMAT, as built (engine_onboarding_bundle v1; design 5.3, with `format`/`version`/`notes` added and `public_safe` the AND of the four checks):
  format, version, bundle_id, engine_id, template_version, created_at, created_by ("gary"),
  base:       {repo, branch: "main", commit_sha}                       repo and commit_sha are null for an engine with no repository
  sections:   [{section, revision, content_sha256, final_by_role ("final_say" | "delegate"), final_at, approved_at, approver_note}]
  files:      [{path, action ("add" | "modify"), base_blob_sha, proposed_sha256, proposed_content}]
  core_tasks: [{kind, payload}]            kind: ingest_seed | retag     (design 5.4; scope_change is not emitted: README only, no Core task)
  checks:     {public_safe, no_email, no_not_yet_public, names_ok, schema_ok}
  pr_text:    {title, body}
  notes:      [text]                       what was not exported (for example frontier / flagged entries: "not exported in v1")
"""
import hashlib
import json
import re
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

from utils import onboarding as ob
from utils import onboarding_base as base
from utils import onboarding_form as form
from utils import onboarding_lint as lint
from utils import onboarding_render as render
from utils import onboarding_template as tpl
from utils.onboarding_form import FormError

BUNDLES = "onboarding_bundles"
PREFIX = "onboarding/bundles/"
FORMAT, VERSION = "engine_onboarding_bundle", 1
ID_RE = re.compile(r"^[0-9a-f]{32}$")
OPEN_STATES = ("created", "exported")


# ---- the private bucket (tests replace these two) ---------------------------------------------------------------------------------------------------
def _store_put(object_path: str, data: bytes) -> None:
    import media_store
    media_store._client().bucket(media_store.PRIVATE_BUCKET).blob(object_path).upload_from_string(data, content_type="application/json")


def _store_get(object_path: str) -> Optional[bytes]:
    import media_store
    blob = media_store._client().bucket(media_store.PRIVATE_BUCKET).get_blob(object_path)
    return blob.download_as_bytes() if blob is not None else None


def object_path(engine_id: str, bundle_id: str) -> str:
    return f"{PREFIX}{engine_id}/{bundle_id}.json"


def _bundle_ref(db, bundle_id: str):
    return db.collection(BUNDLES).document(bundle_id)


# ---- what goes in ---------------------------------------------------------------------------------------------------------------------------------------
def core_tasks(items_by_section: Dict[str, List[dict]]) -> List[dict]:
    """What Gary's Core agent does AFTER the pull request merges (design 5.4, 6.2). The form never does it."""
    tasks = []
    for i in items_by_section.get("seeds", []):
        if i.get("choice") == "yes" and (i.get("context") or {}).get("identifier"):
            tasks.append({"kind": "ingest_seed", "payload": {"identifier": i["context"]["identifier"], "question_ids": (i["context"].get("question_ids") or [])}})
    qs = items_by_section.get("questions")
    if qs is not None:
        added = [i["item_id"] for i in qs if i.get("choice") == "add"]
        retired = [i["item_id"] for i in qs if i.get("choice") in ("drop", "split")]
        if added or retired:
            tasks.append({"kind": "retag", "payload": {"added": added, "retired": retired}})
    return tasks


def _owners(db, engine_id: str) -> List[dict]:
    """Every active owner as {naming, role, name}: used to write the attribution line and to check no name is used beyond the owner's consent. Never stored."""
    out = []
    for d in db.collection(ob.MEMBERS).where("engine_id", "==", engine_id).stream():
        m = d.to_dict() or {}
        sid = m.get("subscriber_id")
        if m.get("status") != "active" or m.get("role") != "owner" or not sid:
            continue
        snap = db.collection("subscribers").document(sid).get()
        out.append({"naming": (m.get("consent") or {}).get("naming") or "role", "role": "advisor" if m.get("final_say") else "owner",
                    "name": ((snap.to_dict() or {}).get("name") if snap.exists else "") or ""})
    return out


def _sha_bytes(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


# ---- create ---------------------------------------------------------------------------------------------------------------------------------------------
def create_bundle(db, *, engine_id: str, wanted: Optional[List[str]], now: Optional[datetime] = None, ip_hash: Optional[str] = None,
                  request_id: Optional[str] = None) -> Dict[str, Any]:
    now = now or ob._utcnow()
    engine = form._engine(db, engine_id)
    secs = form._section_docs(db, engine_id)
    if wanted is not None:
        if not wanted or len(set(wanted)) != len(wanted) or any(w not in tpl.SECTION_KEYS for w in wanted):
            raise FormError(400, "sections must name one or more distinct sections: " + ", ".join(tpl.SECTION_KEYS))
        not_approved = [w for w in wanted if (secs.get(w) or {}).get("status") != "approved"]
        if not_approved:
            raise FormError(409, "Only approved sections can go in a bundle", not_approved=not_approved)
        chosen = [k for k in tpl.SECTION_KEYS if k in wanted]
    else:
        chosen = [k for k in tpl.SECTION_KEYS if (secs.get(k) or {}).get("status") == "approved"]
    if not chosen:
        raise FormError(409, "No section is approved yet", not_approved=[])
    items_by_section, section_rows = {}, []
    for key in chosen:
        sec, items = secs[key], form._items_of(db, engine_id, key)
        digest = form.content_sha256(items)
        if digest != sec.get("approved_content_sha256"):
            raise FormError(409, "A section no longer matches what was approved", changed=[key])
        items_by_section[key] = items
        section_rows.append({"section": key, "revision": sec.get("approved_revision", sec.get("revision", 1)), "content_sha256": digest,
                             "final_by_role": "delegate" if sec.get("final_via_delegation") else "final_say", "final_at": sec.get("final_at"),
                             "approved_at": sec.get("approved_at"), "approver_note": sec.get("approver_note")})
    paths = render.files_for(chosen)
    if "README.md" not in paths:
        paths.insert(0, "README.md")                                     # the attribution line lives there
    fetched = base.fetch_bases(engine, paths, None)
    if not fetched["no_repo"] and (fetched["commit_state"] != "ok" or any(s == "unavailable" for s, _ in fetched["files"].values())):
        raise FormError(503, "The repository's current state could not be read; no bundle was built. Please try again shortly.")
    owners = _owners(db, engine_id)
    rendered = render.render_files(items_by_section, {p: t for p, (s, t) in fetched["files"].items()}, now.date().isoformat(), attribution=owners)
    files, preview, notes = [], [], []
    for r in rendered:
        state, current = fetched["files"][r["path"]]
        if state == "ok" and current == r["content"]:
            continue                                                       # nothing to change in this file
        if state != "ok" and not r["content"].strip():
            continue
        action = "modify" if state == "ok" else "add"
        files.append({"path": r["path"], "action": action, "base_blob_sha": fetched["blobs"].get(r["path"]) if state == "ok" else None, "proposed_sha256": r["sha256"],
                      "proposed_content": r["content"]})
        preview.append({"path": r["path"], "action": action, **(base.unified(current, r["content"]) if state == "ok" else base.plain_lines(r["content"]))})
        notes += r["notes"]
    all_items = [i for its in items_by_section.values() for i in its]
    result = lint.run_checks(files, owners, all_items, {path: text for path, (state, text) in fetched["files"].items() if state == "ok"})
    checks = {**result["checks"], "public_safe": all(result["checks"].values())}
    bundle_id = uuid.uuid4().hex
    titles = [tpl.section_title(k) for k in chosen]
    bundle = {"format": FORMAT, "version": VERSION, "bundle_id": bundle_id, "engine_id": engine_id, "template_version": tpl.TEMPLATE_VERSION, "created_at": now.isoformat(),
              "created_by": "gary", "base": {"repo": fetched["repo"], "branch": "main", "commit_sha": fetched["commit_sha"]}, "sections": section_rows, "files": files,
              "core_tasks": core_tasks(items_by_section), "checks": checks,
              "pr_text": {"title": f"Onboarding: {engine.get('label') or engine_id}: {', '.join(titles)}",
                          "body": "Changes proposed by the engine's research owners through the onboarding form and approved by the reviewer.\n\nSections: " + "; ".join(titles) +
                                  ".\n\nGenerated from an approved change bundle; the bundle's checks and the base commit were re-verified before this pull request was opened."},
              "notes": notes}
    data = json.dumps(bundle, indent=2, sort_keys=True, ensure_ascii=False).encode("utf-8")
    status = "created" if checks["public_safe"] else "blocked"
    record = {"bundle_id": bundle_id, "engine_id": engine_id, "status": status, "base_commit_sha": fetched["commit_sha"], "repo": fetched["repo"],
              "bundle_sha256": _sha_bytes(data), "object_path": object_path(engine_id, bundle_id), "pr_url": None, "created_at": now.isoformat(),
              "sections": chosen, "checks": checks, "problems": result["problems"], "files": [f["path"] for f in files]}
    _store_put(record["object_path"], data)                                # before the record: no record ever points at nothing
    ob._run_in_transaction(db, _create_in, db, record, now, ip_hash, request_id)
    return {**public_record(record), "preview": preview, "notes": notes}


def _create_in(transaction, db, record, now, ip_hash, request_id):
    transaction.set(_bundle_ref(db, record["bundle_id"]), record)
    ob._event(transaction, db, engine_id=record["engine_id"], actor="admin", actor_role="admin", action="bundle_create", target=record["bundle_id"], before=None,
              after={"status": record["status"], "bundle_sha256": record["bundle_sha256"]}, ip_hash=ip_hash, request_id=request_id, now=now,
              extra={"bundle_id": record["bundle_id"], "sections": record["sections"], "status": record["status"], "failed_checks": sorted(record["problems"]),
                     "base_commit_sha": record["base_commit_sha"], "bundle_sha256": record["bundle_sha256"]})


def public_record(r: dict) -> Dict[str, Any]:
    keys = ("bundle_id", "engine_id", "status", "base_commit_sha", "repo", "bundle_sha256", "pr_url", "created_at", "merged_at", "exported_at", "sections", "checks", "problems", "files")
    return {k: r.get(k) for k in keys}


# ---- read ---------------------------------------------------------------------------------------------------------------------------------------------
def _load(db, engine_id: str, bundle_id: str, transaction=None) -> dict:
    if not isinstance(bundle_id, str) or not ID_RE.match(bundle_id):
        raise FormError(404, "Not found")
    snap = _bundle_ref(db, bundle_id).get(transaction=transaction) if transaction is not None else _bundle_ref(db, bundle_id).get()
    r = snap.to_dict() if snap.exists else None
    if not r or r.get("engine_id") != engine_id:
        raise FormError(404, "Not found")
    return r


def list_bundles(db, engine_id: str) -> List[Dict[str, Any]]:
    form._engine(db, engine_id)
    rows = [d.to_dict() or {} for d in db.collection(BUNDLES).where("engine_id", "==", engine_id).stream()]
    return [public_record(r) for r in sorted(rows, key=lambda r: r.get("created_at", ""), reverse=True)]


def owner_view(db, engine_id: str) -> List[Dict[str, Any]]:
    """What the owners may see, read only: a bundle that exists ('created') or was merged, with the sections it carries. No file, check, reason or address."""
    out = []
    for r in list_bundles(db, engine_id):
        if r["status"] in OPEN_STATES or r["status"] == "merged":
            out.append({"status": "merged" if r["status"] == "merged" else "created", "at": r.get("merged_at") if r["status"] == "merged" else r["created_at"],
                        "sections": [tpl.section_title(k) for k in r["sections"]]})
    return out[:10]


def download(db, *, engine_id: str, bundle_id: str, now: Optional[datetime] = None, ip_hash: Optional[str] = None, request_id: Optional[str] = None) -> bytes:
    """The stored JSON, byte for byte. A blocked or superseded bundle is refused (409); the first download marks it exported (audited)."""
    r = _load(db, engine_id, bundle_id)
    if r["status"] == "blocked":
        raise FormError(409, "This bundle is blocked by a failed check and cannot be downloaded as ready", failed_checks=sorted(r.get("problems") or {}))
    if r["status"] == "superseded":
        raise FormError(409, "This bundle was superseded; create a new one")
    data = _store_get(r["object_path"])
    if data is None or _sha_bytes(data) != r.get("bundle_sha256"):
        raise FormError(500, "The stored bundle is missing or does not match its record")
    ob._run_in_transaction(db, _export_in, db, engine_id, bundle_id, now or ob._utcnow(), ip_hash, request_id)
    return data


def _export_in(transaction, db, engine_id, bundle_id, now, ip_hash, request_id):
    r = _load(db, engine_id, bundle_id, transaction)
    new = {**r, "status": "exported", "exported_at": r.get("exported_at") or now.isoformat()} if r["status"] == "created" else r
    if new is not r:
        transaction.set(_bundle_ref(db, bundle_id), new)
    ob._event(transaction, db, engine_id=engine_id, actor="admin", actor_role="admin", action="export", target=bundle_id, before={"status": r["status"]}, after={"status": new["status"]},
              ip_hash=ip_hash, request_id=request_id, now=now, extra={"bundle_id": bundle_id, "bundle_sha256": r.get("bundle_sha256")})


# ---- close ----------------------------------------------------------------------------------------------------------------------------------------------
def pr_url_ok(repo: Optional[str], url: Any) -> bool:
    return bool(repo) and isinstance(url, str) and re.fullmatch(r"https://github\.com/%s/pull/[1-9][0-9]{0,8}" % re.escape(repo), url) is not None


def _merged_in(transaction, db, engine_id, bundle_id, pr_url, now, ip_hash, request_id):
    r = _load(db, engine_id, bundle_id, transaction)
    if r["status"] not in OPEN_STATES:
        raise FormError(409, "Only a bundle that was created and not blocked or superseded can be marked merged", status_now=r["status"])
    transaction.set(_bundle_ref(db, bundle_id), {**r, "status": "merged", "pr_url": pr_url, "merged_at": now.isoformat()})
    ob._event(transaction, db, engine_id=engine_id, actor="admin", actor_role="admin", action="bundle_merged", target=bundle_id, before={"status": r["status"]}, after={"status": "merged"},
              ip_hash=ip_hash, request_id=request_id, now=now, extra={"bundle_id": bundle_id, "pr_url": pr_url})
    return {**r, "status": "merged", "pr_url": pr_url, "merged_at": now.isoformat()}


def mark_merged(db, *, engine_id: str, bundle_id: str, pr_url: Any, now: Optional[datetime] = None, ip_hash: Optional[str] = None, request_id: Optional[str] = None) -> dict:
    """Close a bundle with the URL of the pull request that merged it. The URL must be https://github.com/<the engine's repository>/pull/<n>."""
    repo = base.engine_repo(form._engine(db, engine_id))
    if not repo:
        raise FormError(409, "This engine has no repository, so no pull request can be recorded")
    if not pr_url_ok(repo, pr_url):
        raise FormError(400, f"The pull request URL must look like https://github.com/{repo}/pull/<number>")
    return public_record(ob._run_in_transaction(db, _merged_in, db, engine_id, bundle_id, pr_url, now or ob._utcnow(), ip_hash, request_id))


def _superseded_in(transaction, db, engine_id, bundle_id, tip, now, ip_hash, request_id):
    r = _load(db, engine_id, bundle_id, transaction)
    if r["status"] not in OPEN_STATES + ("blocked",):
        raise FormError(409, "Only a bundle that is not merged or already superseded can be superseded", status_now=r["status"])
    if tip == r.get("base_commit_sha"):
        raise FormError(409, "The repository's main has not moved since this bundle was made")
    transaction.set(_bundle_ref(db, bundle_id), {**r, "status": "superseded", "superseded_at": now.isoformat()})
    ob._event(transaction, db, engine_id=engine_id, actor="admin", actor_role="admin", action="bundle_superseded", target=bundle_id, before={"status": r["status"]},
              after={"status": "superseded"}, ip_hash=ip_hash, request_id=request_id, now=now, extra={"bundle_id": bundle_id, "old_base": r.get("base_commit_sha"), "new_tip": tip})
    return {**r, "status": "superseded"}


def supersede(db, *, engine_id: str, bundle_id: str, now: Optional[datetime] = None, ip_hash: Optional[str] = None, request_id: Optional[str] = None) -> dict:
    """Mark a bundle superseded because the repository's main moved on (design 6.3); the sections are still approved, so a new bundle can be created."""
    r = _load(db, engine_id, bundle_id)
    repo = base.engine_repo(form._engine(db, engine_id))
    if not repo or not r.get("base_commit_sha"):
        raise FormError(409, "This bundle has no repository base to compare with")
    tip = base.base_commit(repo)
    if not tip:
        raise FormError(503, "The repository's current commit could not be read. Please try again shortly.")
    return public_record(ob._run_in_transaction(db, _superseded_in, db, engine_id, bundle_id, tip, now or ob._utcnow(), ip_hash, request_id))
