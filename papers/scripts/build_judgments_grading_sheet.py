#!/usr/bin/env python3
"""
Merge judgments_TEMPLATE.csv + appendix_queries.json + frozen research_papers JSONL.gz
into one CSV so an author-assessor sees query_text + title + abstract per row.

Usage (from repo):
  cd papers && python3 scripts/build_judgments_grading_sheet.py \\
    judgments_TEMPLATE \\
    appendix_queries.json \\
    /path/to/research_papers_20260526.jsonl.gz \\
    judgments_grading_sheet.csv

positional args default to files under papers/ when names have no slashes.
"""

from __future__ import annotations

import argparse
import csv
import gzip
import json
import sys
from pathlib import Path


def load_corpus(meta_path: Path) -> dict[str, dict[str, str]]:
    out: dict[str, dict[str, str]] = {}
    opener = gzip.open if str(meta_path).endswith(".gz") else open
    mode = "rt" if str(meta_path).endswith(".gz") else "r"
    encoding = "utf-8"
    with opener(meta_path, mode, encoding=encoding) as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            o = json.loads(line)
            did = str(o["doc_id"])
            out[did] = {
                "title": (o.get("title") or "").strip(),
                "abstract": (o.get("abstract") or "").strip(),
            }
    return out


def load_queries(path: Path) -> dict[int, str]:
    raw = json.loads(path.read_text(encoding="utf-8"))
    out: dict[int, str] = {}
    for entry in raw["queries"]:
        out[int(entry["id"])] = (entry.get("text") or "").strip()
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    papers_dir = Path(__file__).resolve().parent.parent
    ap.add_argument(
        "template_csv",
        nargs="?",
        default=str(papers_dir / "judgments_TEMPLATE.csv"),
        help="judgments_TEMPLATE.csv path",
    )
    ap.add_argument(
        "appendix_json",
        nargs="?",
        default=str(papers_dir / "appendix_queries.json"),
        help="appendix_queries.json from Colab §4",
    )
    ap.add_argument(
        "corpus_jsonl_gz",
        nargs="?",
        default="",
        help="Frozen export .jsonl or .jsonl.gz",
    )
    ap.add_argument(
        "output_csv",
        nargs="?",
        default=str(papers_dir / "judgments_grading_sheet.csv"),
        help="Output CSV path",
    )
    args = ap.parse_args()

    template_path = Path(args.template_csv)
    appendix_path = Path(args.appendix_json)
    out_path = Path(args.output_csv)
    corpus_str = args.corpus_jsonl_gz.strip()
    if not corpus_str:
        print(
            "Error: corpus path required (positional or set default). Example:\n"
            "  python3 scripts/build_judgments_grading_sheet.py "
            "judgments_TEMPLATE.csv appendix_queries.json "
            "~/exports/research_papers_20260526.jsonl.gz",
            file=sys.stderr,
        )
        return 1

    corpus_path = Path(corpus_str)
    if not template_path.is_file():
        print("Missing:", template_path, file=sys.stderr)
        return 1
    if not appendix_path.is_file():
        print("Missing appendix_queries.json:", appendix_path, file=sys.stderr)
        return 2
    if not corpus_path.is_file():
        print("Missing corpus:", corpus_path, file=sys.stderr)
        return 3

    queries = load_queries(appendix_path)
    meta = load_corpus(corpus_path)

    missing_docs: list[str] = []

    with template_path.open("r", encoding="utf-8", newline="") as f_in:
        reader = csv.DictReader(f_in)
        fieldnames = list(reader.fieldnames or [])
        for c in ["query_text", "title", "abstract"]:
            if c not in fieldnames:
                fieldnames.append(c)
        rows = list(reader)

    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("w", encoding="utf-8", newline="") as f_out:
        writer = csv.DictWriter(f_out, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()

        for row in rows:
            qid = int(row["query_id"])
            did = str(row["doc_id"])
            m = meta.get(did)
            if m is None:
                missing_docs.append(did)
            row_out = dict(row)
            row_out["query_text"] = queries.get(qid, "")
            row_out["title"] = (m or {}).get("title", "")
            row_out["abstract"] = (m or {}).get("abstract", "")
            writer.writerow(row_out)

    if missing_docs:
        print(
            f"Warn: {len(missing_docs)} doc_id(s) not in corpus "
            f"(first 15): {missing_docs[:15]}",
            file=sys.stderr,
        )
    print("Wrote", out_path.resolve(), "rows", len(rows))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
