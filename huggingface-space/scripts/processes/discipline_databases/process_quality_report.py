#!/usr/bin/env python3
"""Generate quality reports for process database graph metadata."""

from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

from normalize_graph_metrics import BASE_DIR, GRAPH_METRIC_KEYS, PROFILE_FILE, build_process_index, read_json, write_json


REPORT_DIR = BASE_DIR / "process_quality_reports"


def process_html_path(database_dir: Path, process: Dict[str, Any]) -> Path:
    subcategory = str(process.get("subcategory") or "processes")
    return database_dir / "processes" / subcategory / f"{process.get('id')}.html"


def mermaid_hash(process: Dict[str, Any]) -> str:
    mermaid = str(process.get("mermaid") or "").strip()
    if not mermaid:
        return ""
    return hashlib.sha256(mermaid.encode("utf-8")).hexdigest()[:16]


def evaluate_process(database_dir: Path, process: Dict[str, Any], metadata_ids: set[str]) -> List[Dict[str, Any]]:
    findings: List[Dict[str, Any]] = []
    metrics = process.get("graphMetrics") or {}
    process_id = str(process.get("id") or "")

    if any(key not in metrics for key in GRAPH_METRIC_KEYS):
        findings.append({"severity": "high", "code": "missing_metrics", "message": "Missing one or more normalized metric keys."})
    if not metrics.get("nodes") and not metrics.get("edges"):
        findings.append({"severity": "medium", "code": "zero_nodes_edges", "message": "Node and edge counts are both zero."})
    if process.get("metricSource") == "missing":
        findings.append({"severity": "medium", "code": "metric_source_missing", "message": "No direct or inferred metrics were found."})
    if not process.get("domainContext"):
        findings.append({"severity": "medium", "code": "missing_context", "message": "Missing discipline context field."})
    if not process.get("graphType"):
        findings.append({"severity": "medium", "code": "missing_graph_type", "message": "Missing graph type."})
    if process_id not in metadata_ids and process.get("_sourceJsonPath"):
        findings.append({"severity": "info", "code": "supplemental_json", "message": "Process comes from JSON outside metadata.json."})
    if process_id in metadata_ids and not process_html_path(database_dir, process).exists():
        findings.append({"severity": "medium", "code": "missing_html", "message": "Expected process HTML page is missing."})

    if database_dir.name == "physics-processes-database":
        text = " ".join(str(process.get(key) or "") for key in ("id", "name", "subcategory", "category")).lower()
        if "nuclear" in text and process.get("subcategory") == "solid_state":
            findings.append({"severity": "medium", "code": "physics_domain_drift", "message": "Nuclear topic appears under solid_state."})

    return findings


def generate_for_discipline(discipline: str, profile: Dict[str, Any]) -> Dict[str, Any]:
    database_dir = BASE_DIR / profile["databaseDir"]
    metadata = read_json(database_dir / "metadata.json")
    metadata_ids = {str(process.get("id")) for process in metadata.get("processes") or []}
    process_index = build_process_index(database_dir, profile)

    findings_by_process: Dict[str, List[Dict[str, Any]]] = {}
    hash_to_processes: Dict[str, List[str]] = defaultdict(list)

    for process in process_index.get("processes") or []:
        process_id = str(process.get("id") or "")
        findings = evaluate_process(database_dir, process, metadata_ids)
        if findings:
            findings_by_process[process_id] = findings
        digest = mermaid_hash(process)
        if digest:
            hash_to_processes[digest].append(process_id)

    duplicate_groups = [ids for ids in hash_to_processes.values() if len(ids) > 1]
    for ids in duplicate_groups:
        for process_id in ids:
            findings_by_process.setdefault(process_id, []).append(
                {"severity": "medium", "code": "duplicate_mermaid", "message": f"Mermaid diagram duplicates: {', '.join(ids)}"}
            )

    counts = Counter()
    for findings in findings_by_process.values():
        for finding in findings:
            counts[finding["code"]] += 1

    return {
        "discipline": discipline,
        "databaseDir": profile["databaseDir"],
        "generatedAt": datetime.now(timezone.utc).isoformat(),
        "processCount": len(process_index.get("processes") or []),
        "findingCount": sum(counts.values()),
        "findingCounts": dict(sorted(counts.items())),
        "duplicateMermaidGroups": duplicate_groups,
        "findingsByProcess": findings_by_process,
    }


def write_markdown(report_path: Path, reports: List[Dict[str, Any]]) -> None:
    lines = [
        "# Process Quality Report",
        "",
        f"Generated: {datetime.now(timezone.utc).isoformat()}",
        "",
    ]
    for report in reports:
        lines.extend(
            [
                f"## {report['discipline'].replace('_', ' ').title()}",
                "",
                f"- Processes checked: {report['processCount']}",
                f"- Findings: {report['findingCount']}",
            ]
        )
        for code, count in report["findingCounts"].items():
            lines.append(f"- {code}: {count}")
        if not report["findingCounts"]:
            lines.append("- No findings.")
        lines.append("")
    report_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate process quality audit reports.")
    parser.add_argument("disciplines", nargs="*", default=["biology", "chemistry", "physics", "computer_science", "mathematics"])
    args = parser.parse_args()

    profiles = read_json(PROFILE_FILE)
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    reports = [generate_for_discipline(discipline, profiles[discipline]) for discipline in args.disciplines]
    combined = {
        "generatedAt": datetime.now(timezone.utc).isoformat(),
        "reports": reports,
    }
    write_json(REPORT_DIR / "latest-process-quality-report.json", combined)
    write_markdown(REPORT_DIR / "latest-process-quality-report.md", reports)
    for report in reports:
        write_json(REPORT_DIR / f"{report['discipline']}-quality-report.json", report)
        print(f"{report['discipline']}: {report['findingCount']} findings across {report['processCount']} processes")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
