#!/usr/bin/env python3
"""Load an engine repository's standard onboarding files, at a PINNED commit, into the onboarding collections
(docs/design/ENGINE_ONBOARDING_FORM.md 2.9, 5.6, 8.1 PR 4a). Run by an agent, attended; never by the form.

    python scripts/onboarding/load_engine.py --engine-id ID --repo OWNER/NAME --commit SHA40 [--apply --approval "LINE"] [--project P] [--offline]

NOTHING HERE IS ENGINE-SPECIFIC: the repository, the commit and the engine id are arguments.

FILES READ (raw.githubusercontent.com at the pinned commit, a plain GET, no credential; the fetch limits are onboarding_base's):
  docs/research_focus.json   REQUIRED   active_questions (id, q, terms, since, priority), categories, horizons, mute, frontier, flagged
  docs/seeds.csv             REQUIRED   one row per seed: doi (arxiv_id, pmid optional), question_ids, title, admit_policy, status
  docs/seed_papers.md        REQUIRED   display text for the seeds (citation, reference-list source); every seed it lists must also be a row of seeds.csv
  docs/hold_list.md          OPTIONAL   the review queue: `- TITLE -- `identifier`, reason, cited_by=N` under group headings; a bold [..] marker means likely keep
There are four files. The loader reads nothing else.

WRITES (only with --apply and the typed approval line; one Firestore transaction):
  onboarding_items       one per question, keyword-list entry and seed, UNANSWERED (revision 0, no choice, no author). An item an owner has touched is never changed.
  onboarding_candidates  one per hold-list paper: origin hold_list, flags {group, likely_keep, reason, cited_by, title}, decision null
  onboarding_engines     .source = {repo, commit_sha, loaded_at}  (the engine record must already exist)
  onboarding_events      one `engine_load` event (a no-change re-run writes nothing at all, not even this)

LIMITS: a plan of more than 450 writes (creates + updates + the engine update + the event) is refused with exit 1 and nothing written (Firestore allows 500 per
transaction). A hold-list bullet without ' -- ' is skipped, never silently: the count and the first 60 characters of each are printed.

EVERY ENTRY GETS A DOCUMENT, OR THE LOAD FAILS: an entry the loader silently skipped would be dropped from the next bundle (the mute-list lesson). Seeds are keyed by
identifier (doi:, then arxiv:, then pmid:), never by author name.

DRY RUN (the default) reads Firestore (never writes) to show exactly what --apply would do; --offline skips Firestore and shows the plan alone.

EXIT CODES:  0 loaded, or a dry run with nothing blocking   1 refused (hostile or malformed input, a conflict with an owner's edit, an open bundle on a different base)
             2 usage, no engine record, a file or Firestore that could not be reached, or no valid approval line
"""
import argparse
import csv
import hashlib
import importlib.util
import io
import json
import re
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
BACKEND = ROOT / "cloud-run-backend"
DEFAULT_PROJECT = "regal-scholar-453620-r7"
DATABASE = "copernicusai"


def _load(name):
    spec = importlib.util.spec_from_file_location(name, BACKEND / "utils" / f"{name}.py")
    mod = importlib.util.module_from_spec(spec)
    sys.modules.setdefault(name, mod)
    spec.loader.exec_module(mod)
    return mod


base = _load("onboarding_base")
lint = _load("onboarding_lint")
tpl = _load("onboarding_template")

FILES = {"focus": "docs/research_focus.json", "seeds": "docs/seeds.csv", "papers": "docs/seed_papers.md", "hold": "docs/hold_list.md"}
REQUIRED = ("focus", "seeds", "papers")
ITEMS, CANDIDATES, ENGINES, EVENTS, BUNDLES = "onboarding_items", "onboarding_candidates", "onboarding_engines", "onboarding_events", "onboarding_bundles"
OPEN_BUNDLE_STATUSES = ("created", "exported")
MAX_ENTRIES = 2000                       # design 9: 2,000 entries per file
MAX_QUESTIONS = 30
WRITE_LIMIT = 450                        # Firestore allows 500 writes in a transaction; the loader refuses a plan over 450 and leaves the margin
HTML_RE = re.compile(r"<\s*/?\s*[A-Za-z!?]|javascript\s*:|vbscript\s*:|data\s*:\s*text/html", re.I)
CONTROL_RE = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")
DOI_RE = re.compile(r"^10\.\d{4,9}/\S+$")
ARXIV_RE = re.compile(r"^(?:\d{4}\.\d{4,5}|[a-z][a-z\-]*(?:\.[a-z]{2})?/\d{7})$")
PMID_RE = re.compile(r"^\d{1,9}$")
STATUS_RE = re.compile(r"^[a-z][a-z_]{0,19}$")
HOLD_ENTRY_RE = re.compile(r"^- (?P<title>.+?) -- `(?P<ident>[^`]+)`(?P<rest>.*)$")
LIKELY_KEEP_RE = re.compile(r"\*\*\[[^\]]*\]\*\*")
LIST_KEYS = ("categories", "horizons", "mute", "frontier", "flagged")


class Refused(Exception):
    """Exit 1: the input or the state is not one to load from."""


class Unreachable(Exception):
    """Exit 2: a file, the engine record or Firestore could not be reached or does not exist."""


def sha(obj):
    return hashlib.sha256(json.dumps(obj, sort_keys=True, default=str, ensure_ascii=False).encode("utf-8")).hexdigest()


# ---- reading --------------------------------------------------------------------------------------------------------------------------------------
def fetch(repo, commit, files_dir=None):
    """{key: text or None}. A required file that is missing refuses; one that cannot be reached, or whose answer is not a plain 200/404, is Unreachable."""
    out = {}
    for key, path in FILES.items():
        if files_dir is not None:
            p = Path(files_dir) / path
            if not p.is_file():
                status, body = 404, b""
            else:
                status, body = 200, p.read_bytes()[: base.MAX_BYTES + 1]
        else:
            try:
                status, body = base._http_get(f"{base.RAW_HOST}/{repo}/{commit}/{path}")
            except Exception as e:                                                 # noqa: BLE001
                raise Unreachable(f"{path}: could not be fetched ({type(e).__name__})")
        if status == 404:
            if key in REQUIRED:
                raise Refused(f"{path}: not found at {commit[:12]} (required)")
            out[key] = None
            continue
        if status != 200:
            raise Unreachable(f"{path}: the host answered {status}")
        if len(body) > base.MAX_BYTES:
            raise Refused(f"{path}: larger than {base.MAX_BYTES} bytes")
        try:
            out[key] = body.decode("utf-8").replace("\r\n", "\n")
        except UnicodeDecodeError:
            raise Refused(f"{path}: not UTF-8 text")
    return out


def value_text(raw, cap, field, required=True):
    """A stored string: plain text only. Hostile content is REFUSED, never cleaned; an over-cap value is refused, never cut."""
    if not isinstance(raw, str):
        raise Refused(f"{field}: must be text")
    text = raw.strip()
    if CONTROL_RE.search(text):
        raise Refused(f"{field}: contains control characters")
    if lint.EMAIL_RE.search(text):
        raise Refused(f"{field}: contains an email-shaped string")
    if HTML_RE.search(text):
        raise Refused(f"{field}: contains HTML or a script")
    if required and not text:
        raise Refused(f"{field}: is empty")
    if len(text) > cap:
        raise Refused(f"{field}: longer than {cap} characters")
    return text


def scan_strings(node, where):
    """Every string anywhere in a parsed JSON document is checked, including the ones the loader does not store."""
    if isinstance(node, str):
        value_text(node, 10_000, where, required=False)
    elif isinstance(node, list):
        for n in node:
            scan_strings(n, where)
    elif isinstance(node, dict):
        for k, v in node.items():
            scan_strings(k, where)
            scan_strings(v, where)


def norm_key(text):
    return " ".join(text.split()).casefold()


def normalise_identifier(kind, raw):
    """'doi:..', 'arxiv:..' or 'pmid:..' (lower case; prefixes and a version suffix removed), or None when the text is not a valid identifier of that kind."""
    s = (raw or "").strip().strip("`").strip()
    if kind == "doi":
        s = re.sub(r"^(?:https?://(?:dx\.)?doi\.org/|doi:\s*)", "", s, flags=re.I).lower()
        return "doi:" + s if DOI_RE.match(s) else None
    if kind == "arxiv":
        s = re.sub(r"^(?:https?://arxiv\.org/(?:abs|pdf)/|arxiv:\s*)", "", s, flags=re.I).lower()
        s = re.sub(r"v\d+$", "", s)
        return "arxiv:" + s if ARXIV_RE.match(s) else None
    if kind == "pmid":
        s = re.sub(r"^pmid:\s*", "", s, flags=re.I)
        return "pmid:" + s if PMID_RE.match(s) else None
    return None


def identifiers(doi="", arxiv="", pmid="", where="entry"):
    """({'doi':..,'arxiv':..,'pmid':..} of the ones present, the key by priority doi, arxiv, pmid). A present but invalid identifier refuses; none at all refuses."""
    found = {}
    for kind, raw in (("doi", doi), ("arxiv", arxiv), ("pmid", pmid)):
        if (raw or "").strip():
            n = normalise_identifier(kind, raw)
            if n is None:
                raise Refused(f"{where}: {kind} {raw.strip()[:40]!r} is not a valid identifier")
            found[kind] = n
    if not found:
        raise Refused(f"{where}: has no doi, arxiv id or pmid (a seed or paper is identified by its identifier, never by an author name)")
    return found, found.get("doi") or found.get("arxiv") or found["pmid"]


# ---- parsing --------------------------------------------------------------------------------------------------------------------------------------
def make_item(section, item_type, item_id, order, value, context):
    context = {**context, "loaded_by": "load_engine"}
    context["source_sha256"] = sha({"value": value, "context": {k: v for k, v in context.items() if k != "source_sha256"}})
    return {"section": section, "type": item_type, "item_id": item_id, "order": order, "value": value, "context": context}


def parse_focus(text):
    try:
        doc = json.loads(text)
    except ValueError as e:
        raise Refused(f"{FILES['focus']}: does not parse ({type(e).__name__})")
    if not isinstance(doc, dict):
        raise Refused(f"{FILES['focus']}: is not a JSON object")
    scan_strings(doc, FILES["focus"])
    items, ids = [], set()
    qs = doc.get("active_questions", [])
    if not isinstance(qs, list) or len(qs) > MAX_QUESTIONS:
        raise Refused(f"{FILES['focus']}: active_questions must be a list of at most {MAX_QUESTIONS}")
    for n, q in enumerate(qs):
        where = f"{FILES['focus']}: question {n}"
        if not isinstance(q, dict):
            raise Refused(f"{where} is not an object")
        qid = value_text(q.get("id"), 61, f"{where} id")
        if not tpl.ID_RE.match(qid):
            raise Refused(f"{where}: id {qid!r} is not a valid item id")
        if qid in ids:
            raise Refused(f"{where}: id {qid!r} appears twice")
        ids.add(qid)
        terms = q.get("terms", [])
        if not isinstance(terms, list) or len(terms) > tpl.TERMS_MAX:
            raise Refused(f"{where}: terms must be a list of at most {tpl.TERMS_MAX}")
        value = {"wording": value_text(q.get("q"), tpl.WORDING_CAP, f"{where} q"),
                 "terms": [{"text": value_text(t, tpl.TERM_CAP, f"{where} term")} for t in terms]}
        if "priority" in q:
            if q["priority"] not in tpl.CENTRALITY:
                raise Refused(f"{where}: priority must be central or background")
            value["centrality"] = q["priority"]
        context = {"since": value_text(q.get("since"), 40, f"{where} since")}
        items.append(make_item("questions", "question", qid, n, value, context))
    for key in LIST_KEYS:
        entries = doc.get(key, [])
        if not isinstance(entries, list) or len(entries) > MAX_ENTRIES:
            raise Refused(f"{FILES['focus']}: {key} must be a list of at most {MAX_ENTRIES}")
        seen = set()
        for n, e in enumerate(entries):
            text = " ".join(value_text(e, tpl.ENTRY_CAP, f"{FILES['focus']}: {key}[{n}]").split())
            nk = norm_key(text)
            if nk in seen:
                continue                                   # the same entry twice is one item (the second is not lost: it is the same entry)
            seen.add(nk)
            items.append(make_item("keywords", "keyword_entry", f"{key}-{hashlib.sha256(nk.encode('utf-8')).hexdigest()[:10]}", n, {"list": key, "text": text}, {}))
    return items, {i["item_id"] for i in items if i["section"] == "questions"}


def split_question_ids(raw, where):
    ids = [p for p in re.split(r"[;,|\s]+", (raw or "").strip()) if p]
    for p in ids:
        if not tpl.ID_RE.match(p):
            raise Refused(f"{where}: question id {p!r} is not valid")
    return ids


def parse_papers(text):
    """{identifier key: {'citation', 'reference_source'}} for every row of a seed table of seed_papers.md. Display text only."""
    rows, header = {}, None
    for line in text.split("\n"):
        if not line.startswith("|"):
            header = None
            continue
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        low = [c.lower() for c in cells]
        if header is None:
            header = low if "paper" in low and "doi" in low else False
            continue
        if header is False or set("".join(cells)) <= set("-: "):
            continue
        if len(cells) != len(header):
            raise Refused(f"{FILES['papers']}: a seed table row has {len(cells)} cells, its header {len(header)}")
        row = dict(zip(header, cells))
        ident = {k: row.get(c, "") for k, c in (("doi", "doi"), ("arxiv", "arxiv id"))}
        ident = {k: v.strip("`—– -") for k, v in ident.items()}
        found, key = identifiers(ident["doi"], ident["arxiv"], where=f"{FILES['papers']}: row {row.get('paper', '')[:40]!r}")
        if key in rows:
            raise Refused(f"{FILES['papers']}: {key} is listed twice")
        rows[key] = {"citation": value_text(row.get("paper"), 600, f"{FILES['papers']} citation"),
                     "reference_source": value_text(row.get("reference-list source", ""), 600, f"{FILES['papers']} source", required=False), "all": found}
    return rows


def parse_seeds(csv_text, papers_text, question_ids):
    try:
        rows = list(csv.reader(io.StringIO(csv_text, newline=""), strict=True))
    except csv.Error as e:
        raise Refused(f"{FILES['seeds']}: does not parse ({type(e).__name__})")
    if not rows or not rows[0]:
        raise Refused(f"{FILES['seeds']}: has no header")
    header = [h.strip() for h in rows[0]]
    if len(set(header)) != len(header):
        raise Refused(f"{FILES['seeds']}: the header repeats a column")
    if "doi" not in header:
        raise Refused(f"{FILES['seeds']}: the header has no doi column")
    if len(rows) - 1 > MAX_ENTRIES:
        raise Refused(f"{FILES['seeds']}: more than {MAX_ENTRIES} rows")
    papers = parse_papers(papers_text)
    items, seen, notes = [], {}, []
    for n, r in enumerate(rows[1:], start=2):
        if not r:
            continue
        where = f"{FILES['seeds']} line {n}"
        if len(r) != len(header):
            raise Refused(f"{where}: has {len(r)} fields, the header {len(header)}")
        row = {h: c for h, c in zip(header, r)}
        for c in r:
            value_text(c, 2000, where, required=False)
        found, key = identifiers(row.get("doi", ""), row.get("arxiv_id", ""), row.get("pmid", ""), where=where)
        if key in seen:
            raise Refused(f"{where}: {key} is also on line {seen[key]}")
        seen[key] = n
        qids = split_question_ids(row.get("question_ids"), where)
        for q in qids:
            if q not in question_ids:
                notes.append(f"{where}: question id {q!r} is not an active question in research_focus.json")
        status = value_text(row.get("status", ""), 20, f"{where} status", required=False)
        if status and not STATUS_RE.match(status):
            raise Refused(f"{where}: status {status!r} is not a plain word")
        shown = papers.get(key) or next((papers[v] for v in found.values() if v in papers), None) or {}
        context = {"identifier": key, "identifiers": found, "question_ids": qids, "title": value_text(row.get("title", ""), 600, f"{where} title", required=False),
                   "admit_policy": value_text(row.get("admit_policy", ""), 60, f"{where} admit_policy", required=False), "status_in_repo": status or None,
                   "citation": shown.get("citation"), "reference_source": shown.get("reference_source")}
        items.append(make_item("seeds", "seed_confirm", "seed-" + hashlib.sha256(key.encode("utf-8")).hexdigest()[:12], len(items), {"comment": ""}, context))
    csv_keys = set()
    for it in items:
        csv_keys.update(it["context"]["identifiers"].values())
    for key, p in papers.items():
        if key not in csv_keys and not any(v in csv_keys for v in p["all"].values()):
            raise Refused(f"{FILES['papers']}: lists {key} but {FILES['seeds']} has no row for it (loading would drop it)")
    return items, notes


def parse_hold(text):
    """(candidates, skipped): `skipped` is every "- " bullet without " -- " (legend and notes, not papers); they are skipped but REPORTED, so a paper written in a
    different shape cannot vanish without being seen."""
    candidates, seen, group, skipped = [], {}, None, []
    for n, line in enumerate(text.split("\n"), start=1):
        if line.startswith("#"):
            group = value_text(line.lstrip("#"), 200, f"{FILES['hold']} line {n} heading", required=False)
            continue
        if line.startswith("- ") and " -- " not in line:
            skipped.append(CONTROL_RE.sub(" ", line)[:60])
            continue
        if not line.startswith("- "):
            continue
        where = f"{FILES['hold']} line {n}"
        m = HOLD_ENTRY_RE.match(line)
        if not m:
            raise Refused(f"{where}: an entry without an identifier (loading would drop it)")
        if group is None:
            raise Refused(f"{where}: an entry before any group heading")
        title_raw = m.group("title")
        likely = bool(LIKELY_KEEP_RE.search(title_raw))
        title = value_text(title_raw.replace("**", ""), 600, f"{where} title")
        ident = m.group("ident").strip()
        kind = "arxiv" if re.match(r"^(?:arxiv:|\d{4}\.\d{4,5})", ident, re.I) else "pmid" if re.match(r"^pmid:", ident, re.I) else "doi"
        found, key = identifiers(**{kind: ident}, where=where)
        if key in seen:
            raise Refused(f"{where}: {key} is also on line {seen[key]}")
        seen[key] = n
        parts = [p.strip() for p in m.group("rest").split(",") if p.strip()]
        cited = next((int(p.split("=", 1)[1]) for p in parts if re.match(r"^cited_by=\d{1,9}$", p)), None)
        reason = next((p for p in parts if re.match(r"^[a-z0-9_]{1,60}$", p)), None)
        flags = {"group": group, "likely_keep": likely, "reason": reason, "cited_by": cited, "title": title}
        candidates.append({"key": key, "identifiers": found, "flags": flags})
        if len(candidates) > MAX_ENTRIES:
            raise Refused(f"{FILES['hold']}: more than {MAX_ENTRIES} entries")
    return candidates, skipped


def build_plan(engine_id, texts):
    items, qids = parse_focus(texts["focus"])
    seed_items, notes = parse_seeds(texts["seeds"], texts["papers"], qids)
    items += seed_items
    cands, skipped = [], []
    found, skipped = parse_hold(texts["hold"]) if texts["hold"] is not None else ([], [])
    for c in found:
        doc = {"candidate_id": f"{engine_id}__{hashlib.sha256(c['key'].encode('utf-8')).hexdigest()[:12]}", "engine_id": engine_id, "origin": "hold_list",
               "identifier": c["key"], "identifiers": c["identifiers"], "registry_record": None, "abstract": None, "decision": None, "question_ids": [], "flags": c["flags"]}
        doc["source_sha256"] = sha({k: doc[k] for k in ("identifier", "identifiers", "flags")})
        cands.append(doc)
    ids = [i["item_id"] for i in items]
    if len(ids) != len(set(ids)):
        raise Refused("two entries produced the same item id: " + ", ".join(sorted({i for i in ids if ids.count(i) > 1})))
    return {"items": items, "candidates": cands, "notes": notes, "skipped_hold": skipped if texts["hold"] is not None else None}


# ---- comparing with what is stored ----------------------------------------------------------------------------------------------------------------
def item_key(engine_id, section, item_id):
    return f"{engine_id}__{section}__{item_id}"


def owner_touched(d):
    return bool(d.get("revision", 0) >= 1 or d.get("comment_count") or d.get("history") or d.get("choice") is not None or d.get("author_subscriber_id")
                or d.get("decision") is not None)


def diff(db, engine_id, plan):
    """{'create': [..], 'update': [..], 'unchanged': [..], 'conflict': [..], 'removed': [..]} for items and candidates; documents are the planned ones.
    update is an untouched loader item whose source changed; conflict is a document an owner touched (or that is not the loader's) AND whose source changed."""
    out = {k: [] for k in ("create", "update", "unchanged", "conflict", "removed")}
    seen = set()
    for kind, col, docs in (("item", ITEMS, plan["items"]), ("candidate", CANDIDATES, plan["candidates"])):
        for p in docs:
            doc_id = item_key(engine_id, p["section"], p["item_id"]) if kind == "item" else p["candidate_id"]
            seen.add((col, doc_id))
            snap = db.collection(col).document(doc_id).get()
            have = snap.to_dict() if snap.exists else None
            new_hash = p["context"]["source_sha256"] if kind == "item" else p["source_sha256"]
            row = {"kind": kind, "col": col, "doc_id": doc_id, "planned": p, "label": p.get("item_id") or p.get("candidate_id")}
            if have is None:
                out["create"].append(row)
                continue
            old_hash = (have.get("context") or {}).get("source_sha256") if kind == "item" else have.get("source_sha256")
            mine = ((have.get("context") or {}).get("loaded_by") == "load_engine") if kind == "item" else bool(have.get("source_sha256"))
            row["old_hash"] = old_hash
            if mine and old_hash == new_hash:
                out["unchanged"].append(row)
            elif not mine:
                out["conflict"].append({**row, "why": "the document exists and was not written by the loader"})
            elif owner_touched(have):
                out["conflict"].append({**row, "why": "an owner has edited it and the repository changed it too"})
            else:
                out["update"].append(row)
    for col, kind in ((ITEMS, "item"), (CANDIDATES, "candidate")):
        for s in db.collection(col).where("engine_id", "==", engine_id).stream():
            d = s.to_dict() or {}
            mine = ((d.get("context") or {}).get("loaded_by") == "load_engine") if kind == "item" else bool(d.get("source_sha256"))
            if mine and (col, s.id) not in seen:
                out["removed"].append({"kind": kind, "col": col, "doc_id": s.id, "label": d.get("item_id") or d.get("candidate_id"), "touched": owner_touched(d)})
    return out


def blocking_bundles(db, engine_id, commit):
    return sorted((s.id, (s.to_dict() or {}).get("status"), str((s.to_dict() or {}).get("base_commit_sha"))[:12]) for s in db.collection(BUNDLES).where("engine_id", "==", engine_id).stream()
                  if (s.to_dict() or {}).get("status") in OPEN_BUNDLE_STATUSES and (s.to_dict() or {}).get("base_commit_sha") != commit)


def counts(plan):
    return {"questions": sum(i["section"] == "questions" for i in plan["items"]), "keyword_entries": sum(i["section"] == "keywords" for i in plan["items"]),
            "seeds": sum(i["section"] == "seeds" for i in plan["items"]), "candidates": len(plan["candidates"]),
            "likely_keep": sum(c["flags"]["likely_keep"] for c in plan["candidates"])}


# ---- applying -------------------------------------------------------------------------------------------------------------------------------------
def approval_line(engine_id, repo, commit, project):
    return f"Approved: load {engine_id} from {repo}@{commit[:12]} into {project}"


def _apply_in(transaction, db, engine_id, repo, commit, planned, plan_hash, counts_, now, run_id, ob):
    engine_ref = db.collection(ENGINES).document(engine_id)
    snap = engine_ref.get(transaction=transaction)
    if not snap.exists:
        raise Unreachable(f"no engine record {engine_id}")
    engine = snap.to_dict() or {}
    reads = []
    for row in planned["create"] + planned["update"]:                                # ALL reads first (Firestore), then every write
        reads.append((row, db.collection(row["col"]).document(row["doc_id"]).get(transaction=transaction)))
    for row, cur in reads:
        have = cur.to_dict() if cur.exists else None
        if row in planned["create"] and have is not None:
            raise Refused(f"{row['doc_id']}: appeared since the plan was made; run again")
        if row in planned["update"]:
            if have is None or owner_touched(have):
                raise Refused(f"{row['doc_id']}: changed since the plan was made; run again")
    for row, _ in reads:
        p, ref = row["planned"], db.collection(row["col"]).document(row["doc_id"])
        if row["kind"] == "item":
            doc = {"engine_id": engine_id, "section": p["section"], "item_id": p["item_id"], "type": p["type"], "value": p["value"], "choice": None, "revision": 0,
                   "author_subscriber_id": None, "updated_at": now.isoformat(), "comment_count": 0, "history": [], "context": p["context"], "order": p["order"]}
            if row in planned["update"]:
                transaction.update(ref, {"value": doc["value"], "context": doc["context"], "order": doc["order"], "updated_at": doc["updated_at"]})
            else:
                transaction.set(ref, doc)
        else:
            if row in planned["update"]:
                transaction.update(ref, {"identifier": p["identifier"], "identifiers": p["identifiers"], "flags": p["flags"], "source_sha256": p["source_sha256"]})
            else:
                transaction.set(ref, {**p, "created_at": now.isoformat()})
    old = engine.get("source")
    transaction.update(engine_ref, {"source": {"repo": repo, "commit_sha": commit, "loaded_at": now.isoformat()}})
    ob._event(transaction, db, engine_id=engine_id, actor="admin", actor_role="admin", action="engine_load", target=f"{repo}@{commit[:12]}",
              before=old, after={"repo": repo, "commit_sha": commit, "plan_sha256": plan_hash}, ip_hash=None, request_id=run_id, now=now,
              extra={"counts": counts_, "created": len(planned["create"]), "updated": len(planned["update"]), "unchanged": len(planned["unchanged"]),
                     "removed_upstream": len(planned["removed"]), "previous_commit_sha": (old or {}).get("commit_sha")})


def default_db(project):
    from google.cloud import firestore
    return firestore.Client(project=project, database=DATABASE)


def main(argv=None, db=None, now=None, out=print):
    ap = argparse.ArgumentParser(description="Load an engine's onboarding files at a pinned commit (see the module docstring).")
    ap.add_argument("--engine-id", required=True)
    ap.add_argument("--repo", required=True)
    ap.add_argument("--commit", required=True)
    ap.add_argument("--apply", action="store_true")
    ap.add_argument("--approval", default="")
    ap.add_argument("--project", default=DEFAULT_PROJECT)
    ap.add_argument("--offline", action="store_true", help="dry run without reading Firestore: the plan alone")
    ap.add_argument("--files-dir", help="dry run against a local directory laid out like the repository (never with --apply)")
    try:
        args = ap.parse_args(argv)
    except SystemExit:
        return 2
    eid = args.engine_id
    if not re.match(r"^[a-z0-9][a-z0-9-]{1,40}$", eid) or not base.REPO_RE.match(args.repo) or ".." in args.repo or not base.SHA_RE.match(args.commit):
        print("ERROR: the engine id, repository or commit is not valid (the commit is the full 40-character sha)", file=sys.stderr)
        return 2
    if args.apply and (args.offline or args.files_dir):
        print("ERROR: --apply cannot be combined with --offline or --files-dir", file=sys.stderr)
        return 2
    line = approval_line(eid, args.repo, args.commit, args.project)
    if args.apply and args.approval.strip() != line:
        print(f"ERROR: --apply needs the exact approval line, typed by Gary:\n  {line}", file=sys.stderr)
        return 2
    now = now or datetime.now(timezone.utc)
    try:
        texts = fetch(args.repo, args.commit, args.files_dir)
        plan = build_plan(eid, texts)
        c = counts(plan)
        plan_hash = sha({"items": [(i["section"], i["item_id"], i["context"]["source_sha256"]) for i in plan["items"]], "candidates": [(x["candidate_id"], x["source_sha256"]) for x in plan["candidates"]]})
        out(f"{'APPLY' if args.apply else 'DRY RUN'}: engine {eid}, {args.repo}@{args.commit[:12]}")
        out(f"  read: " + ", ".join(f"{FILES[k]}{' (absent)' if texts[k] is None else ''}" for k in FILES))
        out(f"  plan: {c['questions']} questions, {c['keyword_entries']} keyword entries, {c['seeds']} seeds, {c['candidates']} hold-list candidates ({c['likely_keep']} likely keep)")
        if plan["skipped_hold"] is not None:
            out(f"  skipped {len(plan['skipped_hold'])} bullet lines in {FILES['hold']} (not papers)")
            for s in plan["skipped_hold"]:
                out(f"    {s}")
        for n in plan["notes"]:
            out(f"  note: {n}")
        if args.files_dir is None:
            tip = base.base_commit(args.repo)
            if tip is None:
                out("  note: the tip of main could not be learned")
            elif tip != args.commit:
                out(f"  WARNING: main is at {tip[:12]}, not the pinned {args.commit[:12]}")
        if args.offline:
            out("  offline: Firestore was not read; every item would be compared against the stored ones on a normal dry run")
            return 0
        if db is None:
            try:
                db = default_db(args.project)
            except Exception as e:                                                 # noqa: BLE001
                raise Unreachable(f"Firestore client: {type(e).__name__}")
        try:
            snap = db.collection(ENGINES).document(eid).get()
        except Exception as e:                                                     # noqa: BLE001
            raise Unreachable(f"Firestore: {type(e).__name__}")
        if not snap.exists:
            raise Unreachable(f"no engine record {eid} (the loader never creates one)")
        engine = snap.to_dict() or {}
        src = engine.get("source") or {}
        if src.get("commit_sha") and src.get("commit_sha") != args.commit:
            out(f"  the engine was loaded from {str(src.get('commit_sha'))[:12]}; this load is a diff against it")
        planned = diff(db, eid, plan)
        out(f"  writes: {len(planned['create'])} create, {len(planned['update'])} update (untouched by owners), {len(planned['unchanged'])} unchanged, "
            f"{len(planned['conflict'])} conflict, {len(planned['removed'])} removed upstream (reported, never deleted)")
        for k in ("create", "update"):
            for r in planned[k]:
                out(f"    {k}: {r['col']}/{r['doc_id']}")
        for r in planned["removed"]:
            out(f"    removed upstream: {r['col']}/{r['doc_id']}{' (owner-touched)' if r['touched'] else ''}")
        blockers = blocking_bundles(db, eid, args.commit)
        for r in planned["conflict"]:
            out(f"    CONFLICT: {r['col']}/{r['doc_id']}: {r['why']}")
        for bid, status, b in blockers:
            out(f"    BLOCKED: bundle {bid} is {status} on base {b}, not {args.commit[:12]}")
        if planned["conflict"] or blockers:
            out("  REFUSED: " + ("conflicts with owners' edits; " if planned["conflict"] else "") + ("open bundles on a different base; " if blockers else "") + "nothing was written")
            return 1
        total = len(planned["create"]) + len(planned["update"]) + 2                  # + the engine update + the event
        out(f"  transaction: {total} writes (limit {WRITE_LIMIT})")
        if total > WRITE_LIMIT:
            out(f"  REFUSED: the plan has {total} writes, over the limit of {WRITE_LIMIT} (Firestore allows 500 per transaction); nothing was written")
            return 1
        if not args.apply:
            out("  nothing was written (dry run). To apply, Gary types the approval line:\n    " + line)
            return 0
        if not (planned["create"] or planned["update"]) and src.get("commit_sha") == args.commit:
            out("  nothing to change at this commit: no write was made")
            return 0
        sys.path.insert(0, str(BACKEND))
        from utils import onboarding as ob
        ob._run_in_transaction(db, _apply_in, db, eid, args.repo, args.commit, planned, plan_hash, c, now, uuid.uuid4().hex, ob)
        out(f"  APPLIED: {len(planned['create'])} created, {len(planned['update'])} updated; engine source and one engine_load event recorded")
        return 0
    except Refused as e:
        print(f"REFUSED: {e}", file=sys.stderr)
        return 1
    except Unreachable as e:
        print(f"ERROR: {e}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
