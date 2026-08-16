#!/usr/bin/env python3
"""
Scoped discussion-board paper harvest (MathOverflow + BioStars).

Official APIs only. Harvests paper IDs (DOI / PMID / arXiv) from
scoped threads. Does not ingest Q&A as papers.

MathOverflow: Stack Exchange API, site=mathoverflow.net.
BioStars: official RSS + GET /api/post/{id}/. Bioinformatics Stack
Exchange is the locked GLMP fallback when BioStars is blocked
(decided 2026-08-15) — same official SE API family, not a scrape.

Channel: discussion_board. Production paper-scout cron is not touched.
"""

from __future__ import annotations

import argparse
import html
import importlib.util
import json
import os
import re
import sys
import time
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple
from urllib.parse import urlparse

import requests
from google.cloud import firestore

SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = Path(os.environ.get("COPERNICUS_WEB_ROOT") or SCRIPT_DIR.parents[2])
A1_PATH = SCRIPT_DIR / "a1_resolve_and_ingest.py"
INGEST_PATH = REPO_ROOT / "cloud-run-backend" / "scripts" / "ingest_papers_from_metadata_json.py"
FOCUS_PATH = REPO_ROOT / "research_focus.json"
DEFAULT_REPORT = SCRIPT_DIR / "discussion_board_scout_report.jsonl"

UA = "CopernicusAI/1.0 (mailto:gary@copernicusai.fyi)"
SE_API = "https://api.stackexchange.com/2.3"
BIOSTARS = "https://www.biostars.org"

THREAD_CAP_PER_SITE = 20
PAPER_CAP = 50
PER_THREAD_CAP = 8
MIN_SE_SCORE = 2
SE_PAGE_SIZE = 8

# ATAP-scoped MathOverflow tags. Dropped ct.category-theory after the
# first run pulled measure theory / von Neumann / K-theory as noise.
MO_TAGS = [
    "lo.logic",
    "proof-theory",
    "type-theory",
    "homotopy-type-theory",
    "set-theory",
]

# ATAP terms that actually live on MathOverflow (not graph-similarity / biology).
MO_TERMS = [
    "proof nets",
    "natural deduction",
    "curry-howard",
    "incompleteness",
]

# Thread title must hit a keep token and must not hit a drop token.
MO_THREAD_KEEP = (
    "proof", "type theor", "logic", "incompleteness", "independence",
    "curry-howard", "curry howard", "natural deduction", "proof net",
    "homotopy type", "hott", "zfc", "continuum", "foundation",
    "formalized", "deduction",
)
MO_THREAD_DROP = (
    "probability", "measure space", "measure theor", "notation",
    "homotopical algebra", "turing undecidable", "k-theory",
    "von neumann", "kervaire",
)

# Resolved paper titles: skip ATAP-adjacent noise that still appears
# inside an otherwise on-topic thread (e.g. vector bundles on a ZFC post).
ATAP_PAPER_KEEP = (
    "identity type", "omega-groupoid", "type theor", "set theor",
    "continuum", "independence", "incompleteness", "proof", "zfc",
    "power set", "woodin", "martin", "curry", "deduction",
    "homotopy type", "hott", "diagonal", "formal", "definable",
)
ATAP_PAPER_DROP = (
    "kervaire", "von neumann", "measure space", "measure theor",
    "vector bundle", "k-theory", "language of physics",
    "language of math", "unsolvability",
)

# GLMP-scoped BioStars tags. Tag search API is unreliable; RSS by tag is official.
BIOSTARS_TAGS = [
    "gene-regulation",
    "transcription-factor",
    "motif",
    "chip-seq",
    "systems-biology",
    "jaspar",
    "pwm",
]

# Bioinformatics SE tags used only when BioStars is blocked.
BIOSE_TAGS = [
    "rna-seq",
    "chip-seq",
    "gene-expression",
    "transcription",
    "motif",
    "systems-biology",
    "network",
    "genomics",
]

GLMP_MUTE = ["crispr clinical", "clinical trial"]

ARXIV_IN_TEXT_RE = re.compile(
    r"(?:arxiv\.org/(?:abs|pdf)/|arxiv:)(\d{4}\.\d{4,5}(?:v\d+)?|[a-z-]+(?:\.[A-Z]{2})?/\d{7})",
    re.IGNORECASE,
)
PMID_IN_TEXT_RE = re.compile(r"\bpmid[:\s#]+(\d{5,9})\b", re.IGNORECASE)
PMID_URL_RE = re.compile(r"pubmed\.ncbi\.nlm\.nih\.gov/(\d+)", re.IGNORECASE)


def _load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _session() -> requests.Session:
    s = requests.Session()
    s.headers.update({"User-Agent": UA, "Accept": "application/json, application/atom+xml, text/xml, */*"})
    return s


def load_mute() -> List[str]:
    mute = list(GLMP_MUTE)
    if FOCUS_PATH.is_file():
        data = json.loads(FOCUS_PATH.read_text(encoding="utf-8"))
        mute.extend(str(x).lower() for x in (data.get("mute") or []))
    return [m.lower() for m in mute if m]


def is_muted(text: str, mute: List[str]) -> bool:
    blob = (text or "").lower()
    return any(term in blob for term in mute)


def _hits(text: str, tokens: Iterable[str]) -> bool:
    blob = (text or "").lower()
    return any(token in blob for token in tokens)


def mo_thread_on_topic(title: str) -> bool:
    """Keep logic / type-theory / proof threads; drop categorical-probability noise."""
    if _hits(title, MO_THREAD_DROP):
        return False
    return _hits(title, MO_THREAD_KEEP)


def atap_paper_on_topic(title: str) -> bool:
    if _hits(title, ATAP_PAPER_DROP):
        return False
    return _hits(title, ATAP_PAPER_KEEP)


def extract_ids(text: str, intake) -> List[Tuple[str, str]]:
    """Return unique (kind, value) paper IDs from thread HTML/text."""
    blob = html.unescape(text or "")
    found: List[Tuple[str, str]] = []
    seen = set()

    def add(kind: str, value: str) -> None:
        key = (kind, value.lower() if kind == "doi" else value)
        if key in seen:
            return
        seen.add(key)
        found.append(key)

    for m in intake.DOI_RE.finditer(blob):
        doi = clean_doi(intake._trim_doi_match(m.group(0)).split("#", 1)[0])
        if looks_like_real_doi(doi):
            add("doi", doi)
    for m in ARXIV_IN_TEXT_RE.finditer(blob):
        add("arxiv", m.group(1).rstrip(".pdf"))
    for m in PMID_URL_RE.finditer(blob):
        add("pmid", m.group(1))
    for m in PMID_IN_TEXT_RE.finditer(blob):
        add("pmid", m.group(1))
    return found


def clean_doi(doi: str) -> str:
    """Strip landing-page suffixes that DOI_RE picks up from hrefs."""
    d = (doi or "").strip()
    d = re.sub(r"(?i)/+(?:full|pdf|epdf|abstract|html|xml)(?:[/?#].*)?$", "", d)
    d = re.sub(r"(?i)(10\.1101/\d+)v\d+$", r"\1", d)
    # Oxford and similar append an extra numeric article id after the real DOI.
    d = re.sub(r"/(\d{5,})$", "", d)
    return d


def looks_like_real_doi(doi: str) -> bool:
    d = (doi or "").lower()
    if len(d) < 8 or not d.startswith("10."):
        return False
    if d.startswith("10.1000/") or "example" in d:
        return False
    if any(ch in d for ch in " \n\t"):
        return False
    return True


def se_get(sess: requests.Session, path: str, params: Dict[str, Any]) -> Dict[str, Any]:
    r = sess.get(f"{SE_API}{path}", params=params, timeout=30)
    r.raise_for_status()
    data = r.json()
    if data.get("backoff"):
        time.sleep(int(data["backoff"]) + 1)
    return data


def harvest_stackexchange(
    sess: requests.Session,
    site: str,
    tags: List[str],
    terms: List[str],
    project: str,
    mute: List[str],
    thread_cap: int,
    thread_gate=None,
) -> List[Dict[str, Any]]:
    threads: List[Dict[str, Any]] = []
    seen_ids = set()

    def take(item: Dict[str, Any], via: str) -> None:
        qid = item.get("question_id")
        if not qid or qid in seen_ids or len(threads) >= thread_cap:
            return
        if int(item.get("score") or 0) < MIN_SE_SCORE:
            return
        title = html.unescape(item.get("title") or "")
        body = item.get("body") or ""
        if is_muted(f"{title}\n{body}", mute):
            return
        if thread_gate and not thread_gate(title):
            return
        seen_ids.add(qid)
        threads.append({
            "site": site,
            "project": project,
            "via": via,
            "thread_id": str(qid),
            "url": item.get("link") or f"https://{site}/questions/{qid}",
            "title": title,
            "body": body,
            "score": item.get("score"),
        })

    for tag in tags:
        if len(threads) >= thread_cap:
            break
        data = se_get(sess, "/questions", {
            "order": "desc",
            "sort": "votes",
            "tagged": tag,
            "site": site,
            "pagesize": SE_PAGE_SIZE,
            "filter": "withbody",
        })
        for item in data.get("items") or []:
            take(item, f"tag:{tag}")
        time.sleep(0.2)

    for term in terms:
        if len(threads) >= thread_cap:
            break
        data = se_get(sess, "/search/advanced", {
            "order": "desc",
            "sort": "votes",
            "q": term,
            "site": site,
            "pagesize": SE_PAGE_SIZE,
            "filter": "withbody",
        })
        for item in data.get("items") or []:
            take(item, f"term:{term}")
        time.sleep(0.2)

    if threads:
        ids = ";".join(t["thread_id"] for t in threads)
        data = se_get(sess, f"/questions/{ids}/answers", {
            "site": site,
            "pagesize": 100,
            "filter": "withbody",
            "sort": "votes",
            "order": "desc",
        })
        by_q: Dict[str, List[str]] = {t["thread_id"]: [] for t in threads}
        for ans in data.get("items") or []:
            qid = str(ans.get("question_id") or "")
            if qid in by_q:
                by_q[qid].append(ans.get("body") or "")
        for t in threads:
            extra = by_q.get(t["thread_id"] or [])
            if extra:
                t["body"] = t["body"] + "\n" + "\n".join(extra)
    return threads


def harvest_biostars(
    sess: requests.Session,
    tags: List[str],
    mute: List[str],
    thread_cap: int,
) -> Tuple[List[Dict[str, Any]], Optional[str]]:
    """Official RSS by tag, then GET /api/post/{id}/. Returns (threads, error)."""
    post_ids: List[Tuple[str, str]] = []
    seen = set()
    for tag in tags:
        url = f"{BIOSTARS}/feeds/tag/{tag}/"
        try:
            r = sess.get(url, timeout=30)
        except Exception as e:
            return [], f"BioStars RSS failed: {e}"
        if r.status_code == 403 or "Just a moment" in (r.text or ""):
            return [], f"BioStars Cloudflare-blocked (HTTP {r.status_code})"
        if r.status_code != 200:
            return [], f"BioStars RSS HTTP {r.status_code} for tag {tag}"
        try:
            root = ET.fromstring(r.content)
        except ET.ParseError as e:
            return [], f"BioStars RSS parse failed: {e}"
        for item in root.findall(".//item"):
            link = (item.findtext("link") or "").strip()
            title = (item.findtext("title") or "").strip()
            pid = biostars_id_from_url(link)
            if not pid or pid in seen:
                continue
            seen.add(pid)
            post_ids.append((pid, title or tag))
        time.sleep(0.2)

    threads: List[Dict[str, Any]] = []
    for pid, rss_title in post_ids:
        if len(threads) >= thread_cap:
            break
        r = sess.get(f"{BIOSTARS}/api/post/{pid}/", timeout=30)
        if r.status_code == 403 or "Just a moment" in (r.text or ""):
            return [], f"BioStars API Cloudflare-blocked (HTTP {r.status_code})"
        if r.status_code != 200:
            continue
        try:
            post = r.json()
        except ValueError:
            continue
        title = post.get("title") or rss_title
        parts = [post.get("xhtml") or post.get("content") or post.get("html") or ""]
        for child in post.get("children") or post.get("answers") or []:
            if isinstance(child, dict):
                parts.append(child.get("xhtml") or child.get("content") or "")
        body = "\n".join(str(p) for p in parts if p)
        if is_muted(f"{title}\n{body}", mute):
            continue
        threads.append({
            "site": "biostars.org",
            "project": "glmp",
            "via": f"tag-rss:{pid}",
            "thread_id": str(pid),
            "url": post.get("url") or f"{BIOSTARS}/p/{pid}/",
            "title": title,
            "body": body,
            "score": post.get("vote_count") or post.get("vote"),
        })
        time.sleep(0.2)
    return threads, None


def biostars_id_from_url(url: str) -> Optional[str]:
    path = urlparse(url).path.strip("/")
    # /p/12345/ or /post/12345/
    parts = [p for p in path.split("/") if p]
    if len(parts) >= 2 and parts[1].isdigit():
        return parts[1]
    if parts and parts[-1].isdigit():
        return parts[-1]
    return None


def resolve_id(kind: str, value: str, intake, a1, mods) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
    if kind == "doi":
        record, err = intake.resolve_doi(value, mods)
        if record is None:
            record, err = a1.resolve_doi_encoded(value, mods["crossref"].parse_crossref_item)
        return record, err
    if kind == "arxiv":
        return intake.resolve_arxiv(value, mods)
    if kind == "pmid":
        record, err = intake.resolve_pmid(value, mods)
        if record is None:
            record, err = a1.resolve_pmid_eutils(value)
            time.sleep(0.35)
        return record, err
    return None, f"unsupported kind {kind}"


def harvest_candidates(threads: Iterable[Dict[str, Any]], intake) -> List[Dict[str, Any]]:
    by_key: Dict[Tuple[str, str], Dict[str, Any]] = {}
    for thread in threads:
        ids = extract_ids(f"{thread.get('title')}\n{thread.get('body')}", intake)[:PER_THREAD_CAP]
        for kind, value in ids:
            key = (kind, value.lower() if kind == "doi" else value)
            row = by_key.get(key)
            if row is None:
                by_key[key] = {
                    "kind": kind,
                    "value": value,
                    "threads": [thread["url"]],
                    "sites": [thread["site"]],
                    "projects": [thread["project"]],
                    "vias": [thread.get("via")],
                    "thread_titles": [thread.get("title")],
                }
            else:
                if thread["url"] not in row["threads"]:
                    row["threads"].append(thread["url"])
                if thread["site"] not in row["sites"]:
                    row["sites"].append(thread["site"])
                if thread["project"] not in row["projects"]:
                    row["projects"].append(thread["project"])
    rows = list(by_key.values())
    rows.sort(key=lambda r: (-len(r["threads"]), r["kind"], r["value"]))
    return rows


def cited_project_for(cand: Dict[str, Any]) -> str:
    projects = cand.get("projects") or []
    if "atap" in projects and "glmp" not in projects:
        return "atap"
    if "glmp" in projects and "atap" not in projects:
        return "glmp"
    return "glmp" if "glmp" in projects else (projects[0] if projects else "atap")


def main() -> int:
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8")

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--write", action="store_true")
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT)
    parser.add_argument("--thread-cap", type=int, default=THREAD_CAP_PER_SITE)
    parser.add_argument("--paper-cap", type=int, default=PAPER_CAP)
    parser.add_argument("--skip-biostars", action="store_true")
    parser.add_argument("--skip-mathoverflow", action="store_true")
    args = parser.parse_args()

    intake = _load_module("researcher_cited_intake", SCRIPT_DIR / "researcher_cited_intake.py")
    a1 = _load_module("a1_resolve_and_ingest", A1_PATH)
    ingest = _load_module("ingest_papers_from_metadata_json", INGEST_PATH)
    mods = {
        "crossref": intake._load_module("acquire_crossref_batch", "acquire_crossref_batch.py"),
        "pubmed": intake._load_module("acquire_pubmed_batch", "acquire_pubmed_batch.py"),
        "arxiv": intake._load_module("acquire_arxiv_batch", "acquire_arxiv_batch.py"),
        "nasa_ads": intake._load_module("acquire_nasa_ads_batch", "acquire_nasa_ads_batch.py"),
        "biorxiv": intake._load_module("acquire_biorxiv_medrxiv_batch", "acquire_biorxiv_medrxiv_batch.py"),
    }

    mute = load_mute()
    sess = _session()
    threads: List[Dict[str, Any]] = []
    notes: List[str] = []

    if not args.skip_mathoverflow:
        mo = harvest_stackexchange(
            sess, "mathoverflow.net", MO_TAGS, MO_TERMS, "atap", mute, args.thread_cap,
            thread_gate=mo_thread_on_topic,
        )
        threads.extend(mo)
        notes.append(f"mathoverflow threads={len(mo)}")
        print(f"MathOverflow: {len(mo)} threads")

    biostars_ok = False
    if not args.skip_biostars:
        bs, err = harvest_biostars(sess, BIOSTARS_TAGS, mute, args.thread_cap)
        if err:
            notes.append(f"biostars: {err}")
            print(f"BioStars: {err}")
            print("Using locked GLMP fallback: Bioinformatics Stack Exchange (official API).")
            biose = harvest_stackexchange(
                sess, "bioinformatics", BIOSE_TAGS, [], "glmp", mute, args.thread_cap,
            )
            threads.extend(biose)
            notes.append(f"bioinformatics.se fallback threads={len(biose)}")
            print(f"Bioinformatics SE: {len(biose)} threads")
        else:
            biostars_ok = True
            threads.extend(bs)
            notes.append(f"biostars threads={len(bs)}")
            print(f"BioStars: {len(bs)} threads")

    candidates = harvest_candidates(threads, intake)
    print(f"Unique paper IDs in scoped threads: {len(candidates)}")

    db = firestore.Client(project="regal-scholar-453620-r7", database="copernicusai")
    col = db.collection("research_papers")
    cited_date = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    counts = {
        "threads": len(threads),
        "ids_found": len(candidates),
        "already_in_corpus": 0,
        "created": 0,
        "merged": 0,
        "unresolved": 0,
        "title_mismatch": 0,
        "new_capped": 0,
        "would_create": 0,
        "would_merge": 0,
        "off_topic": 0,
        "biostars_ok": biostars_ok,
    }
    args.report.parent.mkdir(parents=True, exist_ok=True)
    new_writes = 0

    with args.report.open("w", encoding="utf-8") as fh:
        fh.write(json.dumps({
            "_meta": {
                "ran_at": datetime.now(timezone.utc).isoformat(),
                "write": bool(args.write),
                "notes": notes,
                "thread_cap": args.thread_cap,
                "paper_cap": args.paper_cap,
            }
        }, ensure_ascii=False) + "\n")

        for i, cand in enumerate(candidates, 1):
            record, err = resolve_id(cand["kind"], cand["value"], intake, a1, mods)
            if record is None:
                counts["unresolved"] += 1
                fh.write(json.dumps({
                    "status": "unresolved",
                    **{k: cand[k] for k in ("kind", "value", "threads")},
                    "error": err,
                }, ensure_ascii=False) + "\n")
                continue

            project = cited_project_for(cand)
            if project == "atap" and not atap_paper_on_topic(record.get("title") or ""):
                counts["off_topic"] += 1
                fh.write(json.dumps({
                    "status": "off_topic",
                    "kind": cand["kind"],
                    "value": cand["value"],
                    "title": record.get("title"),
                    "threads": cand["threads"],
                }, ensure_ascii=False) + "\n")
                continue
            context = (
                "Paper ID harvested from a scoped discussion thread. "
                "The thread is provenance, not a corpus item. "
                f"sites={','.join(cand['sites'])} threads={'; '.join(cand['threads'][:4])}"
            )
            record["acquisition_channel"] = "discussion_board"
            record["parent_thread_urls"] = cand["threads"]
            record["cited_by"] = "discussion_board_scout"
            record["cited_date"] = cited_date
            record["cited_project"] = project
            record["cited_context"] = context

            doc_id = ingest._doc_id_for_paper(record)
            snap = col.document(doc_id).get()
            exists = snap.exists
            if not exists:
                dup, _note = intake.check_firestore_duplicate(record)
                if dup:
                    exists = True
                    doc_id = dup["doc_id"]

            if exists:
                counts["already_in_corpus"] += 1
                if args.write:
                    existing = col.document(doc_id).get().to_dict() or {}
                    update = {
                        "parent_thread_urls": firestore.ArrayUnion(cand["threads"]),
                        "updated_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
                    }
                    if not existing.get("acquisition_channel"):
                        update["acquisition_channel"] = "discussion_board"
                    citations = list(existing.get("citations") or [])
                    event = {
                        "cited_by": "discussion_board_scout",
                        "cited_date": cited_date,
                        "cited_context": context,
                        "cited_project": project,
                    }
                    if event not in citations:
                        citations.append(event)
                        update["citations"] = citations
                    col.document(doc_id).update(update)
                    counts["merged"] += 1
                    action = "merged"
                else:
                    counts["would_merge"] += 1
                    action = "would_merge"
            else:
                if new_writes >= args.paper_cap:
                    counts["new_capped"] += 1
                    action = "capped"
                elif args.write:
                    doc = ingest._to_firestore_paper(record, Path(f"discussion/{record.get('id')}.json"))
                    col.document(doc_id).create(doc)
                    counts["created"] += 1
                    new_writes += 1
                    action = "created"
                else:
                    counts["would_create"] += 1
                    new_writes += 1
                    action = "would_create"

            fh.write(json.dumps({
                "status": action,
                "doc_id": doc_id,
                "kind": cand["kind"],
                "value": cand["value"],
                "title": record.get("title"),
                "project": project,
                "threads": cand["threads"],
            }, ensure_ascii=False) + "\n")
            if i % 10 == 0 or i == len(candidates):
                print(f"  resolve [{i}/{len(candidates)}] {counts}")

    print("============================================================")
    print(json.dumps(counts, indent=2))
    print(f"Report: {args.report}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
