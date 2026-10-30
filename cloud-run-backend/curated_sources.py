"""Curated source lists (curated-sources design §2 and §3): classes, intake parsing, confirmation, the minimum rule and the list hash.

A source list is what Gary approves before anything is generated. Each item has one class, assigned by code from evidence:

  peer_reviewed   a DOI or PMID whose registry record is a journal article (Crossref "journal-article") or a PubMed record
  preprint        an arXiv id (with its version), a Crossref "posted-content" record (bioRxiv, medRxiv ...), or a DataCite record
                  (arXiv DOIs; Zenodo records of a publication type)
  company_release a manuscript of github.com/openai/math at a recorded commit (openai_math_index)
  commentary      any other web address; it can only be retrieved, never confirmed, and retrieval is not built yet (C4), so an
                  item of this class is held as pending and blocks approval until Gary removes it

Confirmation reuses the existing registry confirmation (paper_confirmation) unchanged; nothing is taken from a model. A confirmation
that fails is refused with its reason and cannot be overridden. Nothing in this module touches Firestore or the network except through
the injected functions, so it is tested offline.
"""
from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Sequence, Tuple

import paper_confirmation as pc
import openai_math_index as omi
import openai_math_status as oms

PEER_REVIEWED, PREPRINT, COMPANY_RELEASE, COMMENTARY = "peer_reviewed", "preprint", "company_release", "commentary"
CLASSES = (PEER_REVIEWED, PREPRINT, COMPANY_RELEASE, COMMENTARY)

MIN_NON_COMMENTARY = 3        # design §2.1, decision Q1: commentary never counts toward it
MAX_ITEMS_PER_LIST = 60
MAX_ITEMS_PER_REQUEST = 40
MAX_ITEM_CHARS = 500

CONFIRMED, REFUSED, PENDING = "confirmed", "refused", "pending"

_ARXIV_BARE = re.compile(r"^(?:arxiv:\s*)?(\d{4}\.\d{4,5})(v\d+)?$", re.I)
_ARXIV_OLD_URL = re.compile(r"arxiv\.org/(?:abs|pdf)/", re.I)
_DOI_BARE = re.compile(r"^(?:doi:\s*)?(10\.\d{4,9}/\S+)$", re.I)
_PMID_BARE = re.compile(r"^(?:pmid:?\s*)?(\d{5,9})$", re.I)


@dataclass
class Parsed:
    kind: str            # arxiv | doi | pmid | repo | url | invalid
    raw: str
    ids_url: str = ""    # what to hand the registry confirmation as the address
    ids_doi: str = ""
    repo_kind: str = ""  # family | path (kind == repo)
    repo_value: str = ""
    reason: str = ""     # for kind == invalid


def parse_item(raw: Any) -> Parsed:
    """Classify one pasted item by its shape alone (no network)."""
    if not isinstance(raw, str):
        return Parsed("invalid", str(raw)[:50], reason="not_text")
    s = raw.strip()
    if not s:
        return Parsed("invalid", "", reason="empty")
    if len(s) > MAX_ITEM_CHARS:
        return Parsed("invalid", s[:50], reason="too_long")
    if omi.is_repo_reference(s):
        try:
            kind, value = omi.parse_reference(s)
        except ValueError as e:
            return Parsed("invalid", s, reason=str(e))
        return Parsed("repo", s, repo_kind=kind, repo_value=value)
    m = _ARXIV_BARE.match(s)
    if m:
        return Parsed("arxiv", s, ids_url=f"https://arxiv.org/abs/{m.group(1)}{m.group(2) or ''}")
    low = s.lower()
    if low.startswith(("http://", "https://")):
        ids = pc.ids_from_fields(s, None)
        if ids.get("arxiv"):
            return Parsed("arxiv", s, ids_url=f"https://arxiv.org/abs/{ids['arxiv']}{ids.get('arxiv_version') or ''}")
        if ids.get("pmid") and ("pubmed" in low or "ncbi.nlm.nih.gov" in low):
            return Parsed("pmid", s, ids_url=f"https://pubmed.ncbi.nlm.nih.gov/{ids['pmid']}/")
        if re.match(r"^https?://(dx\.)?doi\.org/", low) and ids.get("doi"):
            return Parsed("doi", s, ids_doi=ids["doi"])
        return Parsed("url", s)
    m = _DOI_BARE.match(s)
    if m:
        doi = pc.normalize_doi(m.group(1))
        return Parsed("doi", s, ids_doi=doi) if doi else Parsed("invalid", s, reason="bad_doi")
    m = _PMID_BARE.match(s)
    if m:
        return Parsed("pmid", s, ids_url=f"https://pubmed.ncbi.nlm.nih.gov/{m.group(1)}/")
    return Parsed("invalid", s[:80], reason="not_recognised")


# --- classes -------------------------------------------------------------------------------------------------------
def class_from_record(c: "pc.ConfirmedPaper") -> Tuple[Optional[str], Optional[str]]:
    """(class, None) from a registry confirmation, or (None, refusal reason) when the record's type is not one the design supports.

    arXiv records are preprints; PubMed records are peer reviewed; a Crossref record is peer reviewed only if it is a journal
    article and a preprint only if it is posted content; a DataCite record (arXiv DOIs, Zenodo publication types) is a preprint:
    a repository record is never presented as peer reviewed."""
    reg = c.registry
    if reg == "arxiv":
        return PREPRINT, None
    if reg == "pubmed":
        return PEER_REVIEWED, None
    if reg == "crossref":
        t = (c.record_type or "").lower()
        if t == "journal-article":
            return PEER_REVIEWED, None
        if t == "posted-content":
            return PREPRINT, None
        return None, f"unsupported_record_type:{t or 'unknown'}"
    if reg == "datacite":
        return PREPRINT, None
    return None, f"unsupported_registry:{reg}"


def allowed_class_overrides(item: Dict[str, Any]) -> List[str]:
    """Classes Gary may change an item to. Only toward LESS assurance: a peer-reviewed record may be labelled a preprint. Nothing
    raises a class, and a failed confirmation can never be overridden (design §3.2). Widening this is Gary's decision."""
    if item.get("confirmation", {}).get("status") != CONFIRMED:
        return []
    return [PREPRINT] if item.get("class") == PEER_REVIEWED else []


# --- confirming one item -------------------------------------------------------------------------------------------
def item_key(identifiers: Dict[str, Any]) -> str:
    """A stable text key for an item's identity (what makes two entries 'the same source')."""
    if identifiers.get("repo"):
        return f"{identifiers['repo']}@{identifiers['commit']}:{identifiers['path']}"
    ids = identifiers
    if ids.get("arxiv"):
        return "arxiv:" + ids["arxiv"] + (ids.get("arxiv_version") or "")
    if ids.get("pmid"):
        return "pmid:" + ids["pmid"]
    if ids.get("doi"):
        return "doi:" + ids["doi"]
    return "url:" + (ids.get("url") or "")


def item_id(identifiers: Dict[str, Any]) -> str:
    return hashlib.sha256(item_key(identifiers).encode()).hexdigest()[:12]


def _refused(parsed: Parsed, reason: str, detail: str = "", directories: Optional[List[str]] = None, cls: Optional[str] = None) -> Dict[str, Any]:
    return {"item_id": None, "input": parsed.raw[:MAX_ITEM_CHARS], "class": cls, "added_by": "gary",
            "confirmation": {"status": REFUSED, "reason": reason, "detail": detail, "directories": directories or []}, "approved": False}


def _registry_item(c: "pc.ConfirmedPaper", cls: str, parsed: Parsed) -> Dict[str, Any]:
    c.source_class = cls
    ids = {k: v for k, v in c.ids.items() if v}
    identifiers = dict(ids)
    return {"item_id": item_id(identifiers), "input": parsed.raw[:MAX_ITEM_CHARS], "class": cls, "added_by": "gary",
            "identifiers": identifiers, "title": c.title, "authors": list(c.authors), "year": c.year, "venue": c.venue, "url": c.url,
            "evidence_text": c.abstract, "confirmation": {"status": CONFIRMED, **c.to_dict()}, "relevance_score": None, "approved": True}


def _repo_item(conf: Dict[str, Any], parsed: Parsed, status: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    identifiers = {"repo": conf["repo"], "commit": conf["commit"], "path": conf["path"], "family": conf["family"]}
    item = {"item_id": item_id(identifiers), "input": parsed.raw[:MAX_ITEM_CHARS], "class": COMPANY_RELEASE, "added_by": "gary",
            "identifiers": identifiers, "title": conf["title"], "authors": list(conf["authors"]), "year": conf["year"], "venue": None,
            "url": conf["url"], "evidence_text": conf["abstract"], "confirmation": dict(conf), "relevance_score": None, "approved": True}
    if status is not None:                       # result status from the pinned commit (design §4), per manuscript
        item["result_status"], item["status_basis"] = status["status"], status["basis"]
    return item


async def confirm_registry_item(parsed: Parsed, http_get=None) -> Dict[str, Any]:
    """Confirm an arXiv id, DOI or PMID against its registry (the existing confirmation) and assign its class.
    Raises pc.RegistryUnavailable when a registry cannot be reached."""
    class _S:
        pass
    s = _S()
    s.title, s.url, s.doi, s.publication_date = "", parsed.ids_url, parsed.ids_doi or None, None
    res = await pc.confirm_sources([s], http_get=http_get, max_papers=1)
    if not res.confirmed:
        reason = res.dropped[0].reason if res.dropped else "not_found"
        return _refused(parsed, reason)
    c = res.confirmed[0]
    cls, why = class_from_record(c)
    if cls is None:
        return _refused(parsed, why or "unsupported")
    return _registry_item(c, cls, parsed)


async def confirm_repo_items(parsed: Parsed, commit: str, fetch=None) -> List[Dict[str, Any]]:
    """Items for a repository reference at the pinned commit: one per manuscript (a family expands to its standing manuscripts),
    or a single refusal. Raises omi.RepoUnavailable when the repository cannot be read."""
    index = await omi.load_index(commit, fetch=fetch)
    manuscripts, refusal = omi.resolve(index, parsed.repo_kind, parsed.repo_value)
    if refusal and refusal.reason == "not_a_standing_manuscript" and parsed.repo_kind == "path":
        # not in the map: a WITHDRAWN manuscript may still be used as content (design §4.2); an older edition or an unknown name may not
        conf, why = await oms.withdrawn_manuscript(commit, parsed.repo_value, fetch=fetch)
        if conf is None:
            return [_refused(parsed, why.reason, why.detail, None, COMPANY_RELEASE)]
        return [_repo_item(conf, parsed, {"status": oms.STATUS_WITHDRAWN, "basis": {"commit": commit, "withdrawal_notice": True,
                                                                                    "withdrawal": conf["withdrawal"]}})]
    if refusal:
        return [_refused(parsed, refusal.reason, refusal.detail, refusal.directories, COMPANY_RELEASE)]
    out = []
    for ms in manuscripts:
        conf, refusal = await omi.confirm_manuscript(ms, commit, fetch=fetch)
        if refusal:
            out.append(_refused(Parsed("repo", f"preprints/{ms.dir}"), refusal.reason, refusal.detail, None, COMPANY_RELEASE))
        else:
            out.append(_repo_item(conf, parsed, await oms.compute_status(commit, ms.dir, fetch=fetch)))
    return out


async def confirm_pasted(raw: Any, commit: str, http_get=None, fetch=None) -> List[Dict[str, Any]]:
    """Everything one pasted item turns into: confirmed items, refused entries, or a pending commentary item."""
    parsed = parse_item(raw)
    if parsed.kind == "invalid":
        return [_refused(parsed, parsed.reason)]
    if parsed.kind == "repo":
        return await confirm_repo_items(parsed, commit, fetch=fetch)
    if parsed.kind in ("arxiv", "doi", "pmid"):
        return [await confirm_registry_item(parsed, http_get=http_get)]
    # any other address: commentary, which can only be retrieved; retrieval is built in C4
    identifiers = {"url": parsed.raw}
    return [{"item_id": item_id(identifiers), "input": parsed.raw[:MAX_ITEM_CHARS], "class": COMMENTARY, "added_by": "gary",
             "identifiers": identifiers, "title": None, "authors": [], "year": None, "venue": None, "url": parsed.raw,
             "evidence_text": None, "confirmation": {"status": PENDING, "reason": "commentary_retrieval_not_built",
                                                     "detail": "commentary is retrieved in a later build step; remove it or wait"},
             "relevance_score": None, "approved": False}]


# --- the list ----------------------------------------------------------------------------------------------------------
def approved_items(items: Sequence[Dict[str, Any]]) -> List[Dict[str, Any]]:
    return [i for i in items if i.get("approved") and i.get("confirmation", {}).get("status") == CONFIRMED]


def minimum_check(items: Sequence[Dict[str, Any]]) -> Tuple[bool, Dict[str, int]]:
    """At least MIN_NON_COMMENTARY confirmed, approved, non-commentary items (design §2.1, Q1). Commentary never counts, and neither does a
    withdrawn manuscript: it is content to talk about, not a source for any claim."""
    counts = {c: 0 for c in CLASSES}
    counts["withdrawn"] = 0
    for i in approved_items(items):
        if i.get("result_status") == "withdrawn":
            counts["withdrawn"] += 1
            continue
        counts[i["class"]] = counts.get(i["class"], 0) + 1
    non_commentary = sum(n for c, n in counts.items() if c not in (COMMENTARY, "withdrawn"))
    counts["non_commentary"] = non_commentary
    return non_commentary >= MIN_NON_COMMENTARY, counts


def list_hash(pin: Dict[str, Any], items: Sequence[Dict[str, Any]]) -> str:
    """sha256 over the pin and the approved items (class, identity, title, evidence text), independent of order and of timestamps.
    Any edit to what is approved changes it; a re-confirmation that changes nothing material does not."""
    rows = sorted(({"id": i["item_id"], "class": i["class"], "key": item_key(i["identifiers"]), "title": i.get("title"),
                    "evidence_sha256": hashlib.sha256((i.get("evidence_text") or "").encode()).hexdigest(),
                    "blob_sha": (i.get("confirmation") or {}).get("blob_sha"), "status": i.get("result_status")}
                   for i in approved_items(items)), key=lambda r: r["id"])
    body = json.dumps({"pin": {"repo": pin.get("repo"), "commit": pin.get("commit")}, "items": rows}, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(body.encode()).hexdigest()
