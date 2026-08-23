#!/usr/bin/env python3
"""Stability + predicate checks for ingest_papers_from_metadata_json helpers.

Critical: id stability is asserted across *separate processes* (PYTHONHASHSEED
was the original bug — same-process tests can false-pass the old hash() code).

Run: python scripts/test_ingest_papers_id_stability.py
"""
from __future__ import annotations

import importlib.util
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

SCRIPT = Path(__file__).resolve().parent / "ingest_papers_from_metadata_json.py"


def _load():
    spec = importlib.util.spec_from_file_location("ingest_papers_from_metadata_json", SCRIPT)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _id_in_subprocess(paper: dict, hash_seed: str) -> str:
    with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False, encoding="utf-8") as fh:
        json.dump(paper, fh)
        paper_path = fh.name
    try:
        code = (
            "import importlib.util, json, sys\n"
            f"p = r'''{SCRIPT}'''\n"
            f"paper = json.load(open(r'''{paper_path}''', encoding='utf-8'))\n"
            "spec = importlib.util.spec_from_file_location('ing', p)\n"
            "mod = importlib.util.module_from_spec(spec)\n"
            "spec.loader.exec_module(mod)\n"
            "sys.stdout.write(mod._doc_id_for_paper(paper))\n"
        )
        env = {**os.environ, "PYTHONHASHSEED": hash_seed}
        out = subprocess.check_output([sys.executable, "-c", code], env=env, text=True)
        return out.strip()
    finally:
        Path(paper_path).unlink(missing_ok=True)


def main() -> int:
    m = _load()
    # No native id / pmid / arxiv — forces last-resort sha256 path
    base = {
        "title": "Untitled",
        "abstract": "",
        "source": "",
        "acquired_date": "2026-07-17T10:30:00",
    }

    # 1) Cross-process + cross-seed (old abs(hash) would diverge)
    ids = [
        _id_in_subprocess(base, "0"),
        _id_in_subprocess({**base, "acquired_date": "2026-07-18T20:15:00"}, "1"),
        _id_in_subprocess(base, "42"),
    ]
    assert len(set(ids)) == 1, f"id varied across processes/seeds: {ids}"
    id_a = ids[0]
    assert id_a.startswith("paper_") and len(id_a) == len("paper_") + 32

    # 2) Unexpected fetch metadata must NOT change id
    with_extra = {
        **base,
        "scout_run_ts": "2026-07-17T14:30:00Z",
        "fetch_id": "abc123",
        "source_batch": 99,
    }
    assert _id_in_subprocess(with_extra, "7") == id_a

    # 3) Title normalization (trailing period / case / whitespace)
    titled = {
        "title": "A Study of Widgets.",
        "authors": ["Doe, Jane", "Smith, John"],
        "year": "2024",
    }
    titled_var = {
        "title": "  a study of widgets  ",
        "authors": ["Jane Doe", "John Smith"],  # surname still Doe
        "year": "2024",
        "authors_reordered_irrelevant": True,
    }
    id_t = _id_in_subprocess(titled, "3")
    id_tv = _id_in_subprocess(titled_var, "4")
    assert id_t == id_tv, f"title/author form changed id: {id_t} vs {id_tv}"

    # 4) Enrichment must NOT change id (abstract/categories/sources/urls)
    sparse = {
        "title": "Quantum Widgets",
        "authors": ["Alice Rivest"],
        "year": "2021",
    }
    enriched = {
        **sparse,
        "abstract": "We study widgets in Hilbert space.",
        "categories": ["cs.AI", "quant-ph"],
        "subcategories": ["cs.LG"],
        "sources": ["arxiv", "crossref"],
        "pdf_url": "https://example.com/a.pdf",
        "journal_full": "Journal of Example Studies",
        "published_date": "2021-06-01",
    }
    id_s = _id_in_subprocess(sparse, "5")
    id_e = _id_in_subprocess(enriched, "6")
    assert id_s == id_e, f"enrichment changed id: {id_s} vs {id_e}"

    # 5) All empty Untitled stubs collapse to one last-resort id
    stub2 = {"title": "untitled", "abstract": "later filled", "categories": ["biology"]}
    assert _id_in_subprocess(stub2, "8") == id_a

    # Conjunctive predicate
    assert m._reject_stub_reason({"title": "Untitled"}) is not None
    assert m._reject_stub_reason({"title": "", "pmid": "123"}) is None
    assert m._reject_stub_reason({"title": "Real title", "doi": None}) is None
    assert m._reject_stub_reason({"title": "glmp experiment", "source": "glmp_flowchart_experiment"}) is None
    assert m._reject_stub_reason({"title": "Untitled", "doi": "10.1/x"}) is None

    # 6) Flat cited_* fields must become citations[] so resolve can scope
    flat = {
        "title": "MAP kinase pathways.",
        "pmid": "16105880",
        "cited_by": "Gary Welz",
        "cited_date": "2026-08-23",
        "cited_project": "GLMP",
        "cited_context": "leftover pick 4a",
    }
    mapped = m._to_firestore_paper(flat, Path("biology/researcher_cited_pubmed_16105880.json"))
    assert mapped.get("cited_project") == "GLMP"
    cites = mapped.get("citations") or []
    assert len(cites) == 1, cites
    assert cites[0].get("cited_project") == "glmp"
    assert cites[0].get("cited_by") == "Gary Welz"
    assert cites[0].get("cited_date") == "2026-08-23"

    already = {
        **flat,
        "citations": [
            {"cited_by": "Gary Welz", "cited_date": "2026-08-22", "cited_project": "glmp"},
            {"cited_by": "Gary Welz", "cited_date": "2026-08-23", "cited_project": "atap"},
        ],
    }
    mapped_keep = m._to_firestore_paper(already, Path("biology/x.json"))
    assert mapped_keep["citations"] == already["citations"]

    scout = {"title": "Untitled scout", "pmid": "1"}
    mapped_scout = m._to_firestore_paper(scout, Path("biology/y.json"))
    assert "citations" not in mapped_scout

    print("OK: cross-process; extra-key; title norm; enrichment-stable; stub collapse; predicate; citations fallback")
    return 0


if __name__ == "__main__":
    sys.exit(main())
