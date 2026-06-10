#!/usr/bin/env python3
"""
Generate discipline-specific Programming Framework database viewers.

The generator keeps the existing public folder layout intact and writes:
- discipline-profile.json
- collections.json
- the discipline database table HTML file
"""

from __future__ import annotations

import argparse
import json
import re
from copy import deepcopy
from pathlib import Path
from typing import Any, Dict, Iterable, List, Set

from normalize_graph_metrics import build_process_index


BASE_DIR = Path(__file__).resolve().parents[3]
GENERATOR_DIR = Path(__file__).resolve().parent
PROFILE_FILE = GENERATOR_DIR / "discipline_profiles.json"
PRESET_DIR = GENERATOR_DIR / "collection_presets"
TEMPLATE_FILE = GENERATOR_DIR / "templates" / "enhanced-database-table.html"


def read_json(path: Path) -> Any:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def write_json(path: Path, data: Any) -> None:
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
        f.write("\n")


def normalize(value: Any) -> str:
    return str(value or "").replace("_", " ").replace("-", " ").lower()


def process_search_text(process: Dict[str, Any], extra: Dict[str, Any] | None = None) -> str:
    parts: List[str] = [
        process.get("id", ""),
        process.get("name", ""),
        process.get("subcategory", ""),
        process.get("subcategory_name", ""),
        process.get("complexity", ""),
        " ".join(process.get("namedCollections") or []),
    ]
    if extra:
        parts.extend(
            [
                extra.get("description", ""),
                " ".join(extra.get("keywords") or []),
                " ".join(extra.get("subcategories") or []),
                extra.get("notes", ""),
            ]
        )
    return normalize(" ".join(str(p) for p in parts if p))


def load_process_details(database_dir: Path) -> Dict[str, Dict[str, Any]]:
    details: Dict[str, Dict[str, Any]] = {}
    processes_dir = database_dir / "processes"
    if not processes_dir.exists():
        return details
    for path in processes_dir.rglob("*.json"):
        if path.name.endswith(".backup"):
            continue
        try:
            data = read_json(path)
        except Exception:
            continue
        details[path.stem] = data
        if data.get("id"):
            details[str(data["id"])] = data
    return details


def collection_matches(process: Dict[str, Any], detail: Dict[str, Any] | None, preset: Dict[str, Any]) -> bool:
    text = process_search_text(process, detail)
    for term in preset.get("match", []):
        normalized_term = normalize(term)
        if not normalized_term:
            continue
        pattern = r"(?<![a-z0-9])" + re.escape(normalized_term) + r"(?![a-z0-9])"
        if re.search(pattern, text):
            return True
    return False


def derive_collections(metadata: Dict[str, Any], presets: List[Dict[str, Any]], details: Dict[str, Dict[str, Any]]) -> List[Dict[str, Any]]:
    processes = metadata.get("processes") or []
    by_id: Dict[str, Dict[str, Any]] = {
        preset["id"]: {
            "id": preset["id"],
            "label": preset["label"],
            "description": preset.get("description", ""),
            "processIds": [],
        }
        for preset in presets
    }

    # Include existing named collections even if no explicit preset exists.
    for process in processes:
        for collection_id in process.get("namedCollections") or []:
            by_id.setdefault(
                collection_id,
                {
                    "id": collection_id,
                    "label": collection_id.replace("-", " ").replace("_", " ").title(),
                    "description": "Existing collection from metadata.",
                    "processIds": [],
                },
            )

    for process in processes:
        process_id = process.get("id")
        if not process_id:
            continue
        assigned: Set[str] = set(process.get("namedCollections") or [])
        detail = details.get(str(process_id)) or details.get(str(process_id).split("/")[-1])
        for preset in presets:
            if collection_matches(process, detail, preset):
                assigned.add(preset["id"])
        if not assigned and process.get("subcategory"):
            fallback_id = str(process["subcategory"])
            by_id.setdefault(
                fallback_id,
                {
                    "id": fallback_id,
                    "label": str(process.get("subcategory_name") or fallback_id).replace("_", " ").title(),
                    "description": "Generated from process subcategory.",
                    "processIds": [],
                },
            )
            assigned.add(fallback_id)
        for collection_id in assigned:
            if collection_id in by_id:
                by_id[collection_id]["processIds"].append(process_id)

    collections = [collection for collection in by_id.values() if collection["processIds"]]
    collections.sort(key=lambda item: (-len(item["processIds"]), item["label"]))
    return collections


def add_collection_memberships(metadata: Dict[str, Any], collections: List[Dict[str, Any]]) -> Dict[str, Any]:
    output = deepcopy(metadata)
    membership: Dict[str, Set[str]] = {}
    for collection in collections:
        for process_id in collection.get("processIds", []):
            membership.setdefault(process_id, set()).add(collection["id"])
    for process in output.get("processes") or []:
        process_id = process.get("id")
        if process_id in membership:
            existing = set(process.get("namedCollections") or [])
            process["collections"] = sorted(existing | membership[process_id])
    return output


def render_html(profile: Dict[str, Any]) -> str:
    template = TEMPLATE_FILE.read_text(encoding="utf-8")
    embedded_profile = json.dumps(profile, ensure_ascii=False)
    replacements = {
        "__TITLE__": f"{profile['displayName']} Processes Database",
        "__DISPLAY_NAME__": profile["displayName"],
        "__SUBTITLE__": profile["subtitle"],
        "__ACCENT__": profile["accent"],
        "__PROFILE_JSON__": embedded_profile,
    }
    for key, value in replacements.items():
        template = template.replace(key, value)
    return template


def generate_one(discipline: str, profile: Dict[str, Any]) -> None:
    database_dir = BASE_DIR / profile["databaseDir"]
    metadata_path = database_dir / "metadata.json"
    if not metadata_path.exists():
        raise FileNotFoundError(f"metadata.json not found: {metadata_path}")

    metadata = read_json(metadata_path)
    process_index = build_process_index(database_dir, profile)
    presets = read_json(PRESET_DIR / f"{discipline}.json")
    details = load_process_details(database_dir)
    collections = derive_collections(process_index, presets, details)
    public_profile = deepcopy(profile)
    public_profile["generatedFrom"] = "scripts/processes/discipline_databases/enhanced_database_table.py"
    public_profile["collectionCount"] = len(collections)

    write_json(database_dir / "discipline-profile.json", public_profile)
    write_json(database_dir / "collections.json", collections)
    write_json(database_dir / "process-index.json", add_collection_memberships(process_index, collections))

    enriched_metadata = add_collection_memberships(metadata, collections)
    # Keep metadata.json untouched; enriched data is emitted through process-index.json.
    _ = enriched_metadata

    output_path = database_dir / profile["tableFile"]
    output_path.write_text(render_html(public_profile), encoding="utf-8")
    print(f"Generated {discipline}: {output_path} ({len(collections)} collections)")


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate enhanced discipline process database viewers.")
    parser.add_argument(
        "disciplines",
        nargs="*",
        default=["biology", "chemistry", "physics", "computer_science"],
        help="Discipline keys to generate",
    )
    args = parser.parse_args()

    profiles = read_json(PROFILE_FILE)
    for discipline in args.disciplines:
        if discipline not in profiles:
            raise KeyError(f"Unknown discipline: {discipline}")
        generate_one(discipline, profiles[discipline])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
