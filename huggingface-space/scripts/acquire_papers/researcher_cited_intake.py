#!/usr/bin/env python3
"""
Researcher-cited intake (item #43).

A front door, not a pipeline: accepts a single citation a project participant
sent (DOI, PMID, arXiv ID, ADS bibcode, publisher URL — including Cell Press
PII form — or free text), resolves it using the existing per-source acquirers
in this directory, stamps it with who/when/why it was cited, validates it
against metadata_schema.json, checks it against the corpus, and — only with
--write — saves a record for the existing ingest script
(cloud-run-backend/scripts/ingest_papers_from_metadata_json.py) to pick up.

Manual invocation only. No cron, no interface. See
43-researcher-cited-intake.md in this directory for the design rationale.

Failure behavior (deliberate, not an oversight): on ambiguous or failed
resolution, the original input is preserved verbatim in a review-queue JSONL
and the script exits non-zero. It never emits a best-effort/guessed match —
a confidently wrong canonical record is worse than a visible gap.
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

SCRIPT_DIR = Path(__file__).resolve().parent

# The sibling acquirer modules print emoji at import time (e.g. the missing-
# biopython warning); on a default-cp1252 Windows console that raises
# UnicodeEncodeError before this script gets a chance to run at all.
for _stream in (sys.stdout, sys.stderr):
    if hasattr(_stream, "reconfigure"):
        _stream.reconfigure(encoding="utf-8")

try:
    import requests
except ImportError:
    requests = None

CROSSREF_WORKS_URL = "https://api.crossref.org/works"
CROSSREF_HEADERS = {"User-Agent": "CopernicusAI/1.0 (mailto:gary@copernicusai.fyi)"}
CROSSREF_MAILTO = "gary@copernicusai.fyi"

DOI_RE = re.compile(r'10\.\d{4,9}/[^\s"<>\]]+', re.IGNORECASE)
PII_RE = re.compile(r'S\d{4}-?\d{3}[\dXx]\(\d{2}\)\d{5}-?\d')


def _trim_doi_match(doi: str) -> str:
    """Strip trailing prose punctuation, and a trailing ')' only when it has
    no matching '(' within the match — a real DOI suffix can legitimately
    contain a balanced parenthesis (e.g. old Elsevier PII-derived DOIs like
    10.1016/S0022-2836(61)80072-7), but a DOI embedded in a parenthetical
    aside ("...see 10.1234/abc)") ends with an unmatched one."""
    doi = doi.rstrip('.,;')
    while doi.endswith(')') and doi.count('(') < doi.count(')'):
        doi = doi[:-1].rstrip('.,;')
    return doi


ARXIV_URL_RE = re.compile(r'arxiv\.org/abs/([^\s/?#]+)', re.IGNORECASE)
ARXIV_BARE_RE = re.compile(r'^(?:arxiv:)?(\d{4}\.\d{4,5})(v\d+)?$', re.IGNORECASE)
ARXIV_OLD_RE = re.compile(r'^(?:arxiv:)?([a-z-]+(?:\.[A-Z]{2})?/\d{7})(v\d+)?$', re.IGNORECASE)
PMID_URL_RE = re.compile(r'pubmed\.ncbi\.nlm\.nih\.gov/(\d+)', re.IGNORECASE)
PMID_PREFIX_RE = re.compile(r'^pmid:?\s*(\d+)$', re.IGNORECASE)
ADS_URL_RE = re.compile(r'ui\.adsabs\.harvard\.edu/abs/([^\s/?#]+)', re.IGNORECASE)


def _load_module(name: str, filename: str):
    path = SCRIPT_DIR / filename
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)  # type: ignore[union-attr]
    return mod


def _crossref_get(params: Dict[str, Any]) -> Optional[Dict]:
    if requests is None:
        return None
    params = {**params, "mailto": CROSSREF_MAILTO}
    try:
        resp = requests.get(CROSSREF_WORKS_URL, params=params, timeout=30, headers=CROSSREF_HEADERS)
        if resp.status_code != 200:
            return None
        return resp.json()
    except Exception:
        return None


# ---------------------------------------------------------------------------
# Input classification
# ---------------------------------------------------------------------------

def classify(raw: str, id_type_override: Optional[str]) -> Tuple[str, str]:
    """Returns (kind, value). kind in {doi, pii, pmid, arxiv, bibcode, freetext, unresolvable_url}."""
    raw = raw.strip()

    if id_type_override:
        override = id_type_override.lower()
        if override == "doi":
            m = DOI_RE.search(raw)
            return "doi", (_trim_doi_match(m.group(0)) if m else raw)
        return override, raw

    m = PMID_URL_RE.search(raw)
    if m:
        return "pmid", m.group(1)
    m = PMID_PREFIX_RE.match(raw)
    if m:
        return "pmid", m.group(1)

    m = ADS_URL_RE.search(raw)
    if m:
        return "bibcode", m.group(1)

    m = ARXIV_URL_RE.search(raw)
    if m:
        return "arxiv", m.group(1)
    m = ARXIV_BARE_RE.match(raw)
    if m:
        return "arxiv", m.group(1)
    m = ARXIV_OLD_RE.match(raw)
    if m:
        return "arxiv", m.group(1)

    m = DOI_RE.search(raw)
    if m:
        return "doi", _trim_doi_match(m.group(0))

    m = PII_RE.search(raw)
    if m:
        return "pii", m.group(0)

    if raw.lower().startswith("http"):
        return "unresolvable_url", raw

    return "freetext", raw


# ---------------------------------------------------------------------------
# Per-kind resolvers — each reuses the existing acquirer's parser, never
# reimplements the underlying database query logic.
# ---------------------------------------------------------------------------

def resolve_doi(doi: str, mods: Dict[str, Any]) -> Tuple[Optional[Dict], Optional[str]]:
    doi = doi.strip()

    if doi.lower().startswith("10.1101/"):
        biorxiv_mod = mods["biorxiv"]
        for server in ("biorxiv", "medrxiv"):
            try:
                data = biorxiv_mod._fetch_json(f"{biorxiv_mod.API_BASE_URL}/{server}/{doi}/na/json")
            except Exception:
                data = {}
            collection = data.get("collection") or []
            if len(collection) == 1:
                rec = biorxiv_mod.parse_record(collection[0])
                if rec:
                    return rec, None
            elif len(collection) > 1:
                # A DOI-scoped /details/{server}/{doi}/ query only ever
                # returns one entry per revision of that same DOI, never a
                # different paper — "ambiguous" was never the right read
                # here. Use the latest version's metadata.
                try:
                    latest = max(collection, key=lambda c: int(c.get("version") or 0))
                except (TypeError, ValueError):
                    latest = collection[-1]
                rec = biorxiv_mod.parse_record(latest)
                if rec:
                    return rec, None
                return None, f"matched {len(collection)} {server} revisions for {doi} but failed to parse the latest"
        # Not found on either preprint server — fall through to Crossref,
        # since the DOI may have a published (not just preprint) record.

    crossref_mod = mods["crossref"]
    papers = crossref_mod.acquire_by_doi_list([doi])
    if len(papers) == 1:
        return papers[0], None
    if len(papers) == 0:
        return None, f"DOI not found via Crossref: {doi}"
    return None, f"ambiguous: Crossref returned {len(papers)} records for {doi}"


def resolve_pii(pii_raw: str, mods: Dict[str, Any]) -> Tuple[Optional[Dict], Optional[str]]:
    """Elsevier/Cell Press PII -> Crossref 'alternative-id' (PII with punctuation
    stripped) -> exactly one match or it's ambiguous/failed, never guessed."""
    alt_id = re.sub(r"[^A-Za-z0-9]", "", pii_raw)
    data = _crossref_get({"filter": f"alternative-id:{alt_id}"})
    if data is None:
        return None, "Crossref request failed while resolving PII"
    items = data.get("message", {}).get("items", [])
    if len(items) == 1:
        rec = mods["crossref"].parse_crossref_item(items[0])
        if rec:
            return rec, None
        return None, "matched a Crossref record but failed to parse it"
    if len(items) == 0:
        return None, (
            f"no Crossref record found for alternative-id {alt_id} "
            f"(derived from PII {pii_raw})"
        )
    return None, f"ambiguous: {len(items)} Crossref records share alternative-id {alt_id}"


def resolve_pmid(pmid: str, mods: Dict[str, Any]) -> Tuple[Optional[Dict], Optional[str]]:
    pubmed_mod = mods["pubmed"]
    if not getattr(pubmed_mod, "BIOENTREZ_AVAILABLE", False):
        return None, "biopython (Bio.Entrez) not installed in this environment — cannot resolve PMIDs here"
    pubmed_mod.setup_entrez()
    papers = pubmed_mod.fetch_pubmed_details([pmid])
    if len(papers) == 1:
        return papers[0], None
    if len(papers) == 0:
        return None, f"PMID not found via PubMed/Entrez: {pmid}"
    return None, f"ambiguous: Entrez returned {len(papers)} records for PMID {pmid}"


def resolve_arxiv(arxiv_id: str, mods: Dict[str, Any]) -> Tuple[Optional[Dict], Optional[str]]:
    arxiv_mod = mods["arxiv"]
    if requests is None:
        return None, "the 'requests' library is not available in this environment"
    ns = {
        "atom": "http://www.w3.org/2005/Atom",
        "opensearch": "http://a9.com/-/spec/opensearch/1.1/",
        "arxiv": "http://arxiv.org/schemas/atom",
    }
    try:
        resp = requests.get(arxiv_mod.ARXIV_API_URL, params={"id_list": arxiv_id}, timeout=30)
        resp.raise_for_status()
        import xml.etree.ElementTree as ET
        root = ET.fromstring(resp.content)
    except Exception as e:
        return None, f"arXiv API request failed: {e}"

    entries = root.findall("atom:entry", ns)
    if len(entries) == 1:
        entry_id = entries[0].find("atom:id", ns)
        if entry_id is not None and "api/errors" in (entry_id.text or ""):
            return None, f"arXiv ID not found: {arxiv_id}"
        rec = arxiv_mod.parse_arxiv_entry(entries[0], ns)
        if rec:
            return rec, None
        return None, "matched an arXiv entry but failed to parse it"
    if len(entries) == 0:
        return None, f"arXiv ID not found: {arxiv_id}"
    return None, f"ambiguous: arXiv returned {len(entries)} entries for {arxiv_id}"


def resolve_bibcode(bibcode: str, mods: Dict[str, Any]) -> Tuple[Optional[Dict], Optional[str]]:
    ads_mod = mods["nasa_ads"]
    result = ads_mod.search_nasa_ads(f"bibcode:{bibcode}", max_results=5)
    if result is None:
        return None, "NASA ADS request failed (missing/invalid NASA_ADS_API_TOKEN or network error)"
    docs = result.get("docs", [])
    if len(docs) == 1:
        rec = ads_mod.parse_nasa_ads_doc(docs[0])
        if rec:
            return rec, None
        return None, "matched an ADS record but failed to parse it"
    if len(docs) == 0:
        return None, f"bibcode not found via NASA ADS: {bibcode}"
    return None, f"ambiguous: NASA ADS returned {len(docs)} records for bibcode {bibcode}"


def resolve_freetext(text: str, mods: Dict[str, Any]) -> Tuple[Optional[Dict], Any]:
    """Free-text citations are NEVER auto-accepted — this is priority-4,
    'resolvable, less reliably' in the design doc. Always queue, with
    candidates attached so a human can pick."""
    data = _crossref_get({"query.bibliographic": text, "rows": 5})
    candidates = []
    if data:
        for item in data.get("message", {}).get("items", [])[:5]:
            candidates.append({
                "doi": item.get("DOI"),
                "title": (item.get("title") or [""])[0],
                "score": item.get("score"),
            })
    return None, {
        "reason": "free-text citations are never auto-accepted; candidates are suggestions only",
        "candidates": candidates,
    }


def resolve_unresolvable_url(url: str, mods: Dict[str, Any]) -> Tuple[Optional[Dict], str]:
    return None, (
        "URL contains neither a recognizable DOI nor a Cell Press/Elsevier PII, and "
        "this script deliberately does not scrape publisher landing pages (most are "
        "behind bot-detection anyway). Send the DOI or PII directly if you have it."
    )


DISPATCH = {
    "doi": resolve_doi,
    "pii": resolve_pii,
    "pmid": resolve_pmid,
    "arxiv": resolve_arxiv,
    "bibcode": resolve_bibcode,
    "freetext": resolve_freetext,
    "unresolvable_url": resolve_unresolvable_url,
}


# ---------------------------------------------------------------------------
# Dedup checks
# ---------------------------------------------------------------------------

def check_firestore_duplicate(record: Dict[str, Any]) -> Tuple[Optional[Dict[str, Any]], str]:
    """Returns (dup_info or None, status note). dup_info, when not None, is
    {"doc_id", "field", "title"} — enough for the caller to act on (merge the
    citation onto that doc) without a second query. Non-fatal on any
    failure — this is a bonus authoritative check on top of the local-mirror
    dedup tool, not a hard requirement."""
    try:
        from google.cloud import firestore
    except ImportError:
        return None, "skipped (google-cloud-firestore not installed)"

    checks = []
    doi = record.get("doi")
    if doi:
        checks.append(("doi", doi))
    if record.get("pmid"):
        checks.append(("pmid", str(record["pmid"])))
    if record.get("arxiv_id"):
        checks.append(("arxiv_id", record["arxiv_id"]))
    if record.get("bibcode"):
        checks.append(("bibcode", record["bibcode"]))

    try:
        db = firestore.Client(project="regal-scholar-453620-r7", database="copernicusai")
        col = db.collection("research_papers")
        for field, value in checks:
            docs = list(col.where(field, "==", value).limit(3).stream())
            if docs:
                d = docs[0]
                title = d.to_dict().get("title", "?")
                return {"doc_id": d.id, "field": field, "title": title}, "checked live"
        return None, "checked live against research_papers — no match"
    except Exception as e:
        return None, f"skipped (Firestore check failed: {type(e).__name__}: {e})"


def merge_citation_onto_firestore_doc(doc_id: str, cited_record: Dict[str, Any], write: bool) -> Dict[str, Any]:
    """A re-citation of a paper already in research_papers — item #45's
    original open question, no longer speculative once #47's batch actually
    hit it 8 times. Reuses merge_citation()'s exact logic (same `citations`
    shape as the local-mirror and fresh-ingest paths), but writes only the
    provenance fields back via Firestore update() — the paper's real
    metadata (title/authors/abstract/etc) is never touched.
    Returns {"citations": [...], "would_write": bool} for the caller to
    report; the live update only happens when write=True."""
    from google.cloud import firestore
    db = firestore.Client(project="regal-scholar-453620-r7", database="copernicusai")
    doc_ref = db.collection("research_papers").document(doc_id)
    existing = doc_ref.get().to_dict() or {}

    merged = merge_citation(cited_record, existing)
    update_fields = {"citations": merged["citations"], "acquisition_channel": merged.get("acquisition_channel")}
    for f in CITATION_EVENT_FIELDS:
        if f in merged:
            update_fields[f] = merged[f]

    if write:
        doc_ref.update(update_fields)

    return {"citations": merged["citations"], "would_write": not write}


SOURCE_TO_LOCAL_DIR = {
    "crossref": "crossref",
    "pubmed": "biology",
    "arxiv": None,  # split across arxiv_classic/arxiv_recent; skip local scan, Firestore check covers it
    "nasa_ads": None,
    "biorxiv": "biorxiv",
    "medrxiv": "medrxiv",
}


def check_local_duplicate(record: Dict[str, Any], output_root: Path, dedup_mod) -> Tuple[Optional[str], str]:
    source = record.get("source", "")
    subdir = SOURCE_TO_LOCAL_DIR.get(source)
    if not subdir:
        return None, f"skipped (no single local mirror directory for source={source!r})"
    local_dir = output_root / subdir
    if not local_dir.exists():
        return None, f"skipped (local mirror dir not found: {local_dir})"

    existing = dedup_mod.load_all_papers([local_dir])
    for _pid, other in existing.items():
        is_dup, reason, confidence = dedup_mod.are_duplicates(record, other)
        if is_dup:
            return (
                f"matches local mirror file (reason={reason}, confidence={confidence:.2f}, "
                f"title={other.get('title')!r})",
                f"checked {len(existing)} local files in {local_dir}",
            )
    return None, f"checked {len(existing)} local files in {local_dir} — no match"


# ---------------------------------------------------------------------------
# Review queue
# ---------------------------------------------------------------------------

def write_review_queue(output_root: Path, raw_input: str, kind: str, reason: Any, cited: Dict[str, Any]) -> Path:
    path = output_root / "researcher_cited_review_queue.jsonl"
    path.parent.mkdir(parents=True, exist_ok=True)
    entry = {
        "queued_at": datetime.now(timezone.utc).isoformat(),
        "raw_input": raw_input,
        "detected_kind": kind,
        "reason": reason,
        **{k: v for k, v in cited.items() if v},
    }
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")
    return path


# ---------------------------------------------------------------------------
# Multi-citer merge
#
# A paper can be cited more than once — by different people, at different
# times, for different reasons — and that's the steady state, not an edge
# case (found concretely on 2026-08-05: 3 of a 32-record batch collided on
# the same target file and silently overwrote each other's provenance).
# `citations` is a list of individual citation events; the singular
# cited_by/cited_date/cited_context/cited_project fields are kept in sync
# with the latest event only, for any reader that doesn't know about the
# list yet. This is the shared schema for both places a re-citation can be
# found: this script's own local-JSON-mirror collisions (handled here) and
# an already-Firestore-ingested paper (item #45, still unbuilt — should
# reuse this same `citations` shape when it is).
# ---------------------------------------------------------------------------

CITATION_EVENT_FIELDS = ("cited_by", "cited_date", "cited_context", "cited_project")


def _citation_event(record: Dict[str, Any]) -> Dict[str, Any]:
    return {k: record[k] for k in CITATION_EVENT_FIELDS if record.get(k)}


def merge_citation(new_record: Dict[str, Any], existing: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    """Combine a freshly-resolved record with whatever's already on disk at
    its target path (None if nothing's there yet). Never drops an earlier
    citation event — appends unless it's an exact duplicate (same
    cited_by/date/context/project, e.g. an accidental re-run)."""
    new_event = _citation_event(new_record)
    citations: List[Dict[str, Any]] = list((existing or {}).get("citations") or [])

    if not citations and existing and _citation_event(existing):
        # Existing file predates this feature — its own singular fields are
        # citation #1, never previously recorded as a list entry.
        citations.append(_citation_event(existing))

    if new_event and new_event not in citations:
        citations.append(new_event)

    merged = dict(new_record)
    if citations:
        merged["citations"] = citations
        merged.update(citations[-1])  # singular fields mirror the latest event
    return merged


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> int:
    parser = argparse.ArgumentParser(
        description="Researcher-cited intake (item #43) — resolve a citation a "
                     "researcher sent and prepare it for the existing paper-ingest pipeline."
    )
    parser.add_argument("--input", required=True, help="DOI, PMID, arXiv ID, ADS bibcode, publisher URL, or free-text citation")
    parser.add_argument("--cited-by", required=True, help="Which participant cited this (e.g. 'Lents')")
    parser.add_argument("--cited-date", required=True, help="When it was cited, YYYY-MM-DD")
    parser.add_argument("--cited-context", default="", help="Their words on why/when it came up")
    parser.add_argument("--cited-project", default="", help="Which research project (e.g. 'GLMP')")
    parser.add_argument(
        "--id-type", choices=["doi", "pii", "pmid", "arxiv", "bibcode", "freetext"], default=None,
        help="Override automatic input-type detection",
    )
    parser.add_argument(
        "--output-root", default=str(SCRIPT_DIR.parent.parent / "metadata-database" / "papers"),
        help="Root of the acquired-papers tree (default: huggingface-space/metadata-database/papers "
             "next to this checkout — NOT the Jetson-absolute path the batch acquirers hardcode)",
    )
    parser.add_argument(
        "--write", action="store_true",
        help="Actually write the resolved+validated+deduped record. Without this flag the script "
             "always dry-runs: resolve, validate, dedup-check, print the record, write nothing.",
    )
    args = parser.parse_args()

    output_root = Path(args.output_root)
    cited = {
        "cited_by": args.cited_by,
        "cited_date": args.cited_date,
        "cited_context": args.cited_context,
        # Lowercased at the source, not left to whatever casing the operator
        # typed on the command line -- found 2026-08-08 as a 33-vs-4 GLMP/glmp
        # split (ATAP's own invocations happened to stay consistently
        # lowercase, GLMP's didn't), which silently splits any future
        # group-by on this field.
        "cited_project": args.cited_project.lower() if args.cited_project else args.cited_project,
    }

    kind, value = classify(args.input, args.id_type)
    print(f"Detected input kind: {kind} -> {value!r}")

    mods = {
        "crossref": _load_module("acquire_crossref_batch", "acquire_crossref_batch.py"),
        "pubmed": _load_module("acquire_pubmed_batch", "acquire_pubmed_batch.py"),
        "arxiv": _load_module("acquire_arxiv_batch", "acquire_arxiv_batch.py"),
        "nasa_ads": _load_module("acquire_nasa_ads_batch", "acquire_nasa_ads_batch.py"),
        "biorxiv": _load_module("acquire_biorxiv_medrxiv_batch", "acquire_biorxiv_medrxiv_batch.py"),
    }
    validate_mod = _load_module("validate_metadata", "validate_metadata.py")
    dedup_mod = _load_module("deduplicate_papers", "deduplicate_papers.py")

    resolver = DISPATCH[kind]
    record, err = resolver(value, mods)

    if record is None:
        path = write_review_queue(output_root, args.input, kind, err, cited)
        print(f"UNRESOLVED ({kind}): {err}")
        print(f"Queued (original text preserved verbatim) to: {path}")
        return 2

    record = {
        **record,
        **{k: v for k, v in cited.items() if v},
        "acquisition_channel": "researcher_citation",
    }

    print("\n--- Resolved record ---")
    print(json.dumps(record, indent=2, ensure_ascii=False))

    is_valid, errors, quality = validate_mod.validate_paper(record)
    print(f"\n--- Validation (validate_metadata.validate_paper) ---")
    print(f"Valid: {is_valid}   Quality score: {quality:.1%}")
    if errors:
        for e in errors:
            print(f"  - {e}")

    fs_dup, fs_note = check_firestore_duplicate(record)
    print(f"\n--- Dedup check: Firestore research_papers (live) ---")
    print(f"  {fs_note}")
    if fs_dup:
        print(f"  DUPLICATE: already in research_papers as {fs_dup['doc_id']!r} "
              f"(matched on {fs_dup['field']}, title: {fs_dup['title']!r})")

    local_dup, local_note = check_local_duplicate(record, output_root, dedup_mod)
    print(f"\n--- Dedup check: local mirror (deduplicate_papers.are_duplicates) ---")
    print(f"  {local_note}")
    if local_dup:
        print(f"  DUPLICATE: {local_dup}")

    if fs_dup:
        # Item #45: a re-citation of a paper already in the corpus. No
        # longer speculative once #47's batch actually hit it 8 times —
        # merge the citation onto the existing doc rather than discard it.
        merge_result = merge_citation_onto_firestore_doc(fs_dup["doc_id"], record, write=args.write)
        print(f"\n--- Citation merge onto existing Firestore doc ---")
        print(f"  {len(merge_result['citations'])} citation(s) on record "
              f"{'after this merge' if not merge_result['would_write'] else 'would result'}:")
        for c in merge_result["citations"]:
            print(f"    - {c.get('cited_context', '')[:90]}")
        if merge_result["would_write"]:
            print(f"\nRESULT: dry run — duplicate found, nothing merged. "
                  f"Re-run with --write to merge this citation onto {fs_dup['doc_id']!r}.")
            return 0
        print(f"\nRESULT: merged — citation added to existing doc {fs_dup['doc_id']!r}. "
              f"The paper's own metadata (title/authors/etc) was not touched.")
        return 0

    if local_dup:
        print("\nRESULT: duplicate in the local mirror only (not yet in Firestore) — "
              "not writing. This script doesn't merge onto local-mirror files; if this "
              "paper is meant to be ingested, that's a separate acquisition-pipeline "
              "concern, not a researcher-citation one.")
        return 3

    if not is_valid:
        print("\nRESULT: validation failed — not writing. See errors above.")
        return 4

    if not args.write:
        print("\nRESULT: dry run — nothing written. Re-run with --write to save this record.")
        return 0

    category = record.get("category") or "interdisciplinary"
    out_path = output_root / category / f"researcher_cited_{record['id']}.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)

    existing = None
    if out_path.exists():
        try:
            existing = json.loads(out_path.read_text(encoding="utf-8"))
        except Exception as e:
            print(f"\n⚠️  Could not read existing file at {out_path} ({e}); "
                  "overwriting rather than merging — check it manually.")

    merged = merge_citation(record, existing)
    out_path.write_text(json.dumps(merged, indent=2, ensure_ascii=False), encoding="utf-8")

    if existing:
        print(f"\nRESULT: merged into existing {out_path} "
              f"({len(merged.get('citations', []))} citation(s) on record now)")
    else:
        print(f"\nRESULT: wrote {out_path}")
    print("This is a metadata JSON file only — it still needs "
          "cloud-run-backend/scripts/ingest_papers_from_metadata_json.py to reach Firestore.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
