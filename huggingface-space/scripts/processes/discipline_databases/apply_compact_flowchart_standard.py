#!/usr/bin/env python3
"""Apply the compact vertical flowchart standard across discipline databases.

Standard:
- Mermaid flowcharts render top-down (`graph TD`), not wide left-to-right.
- Long node and edge labels are shortened in Mermaid.
- Full pre-compaction node labels are preserved in JSON `nodeDetails`.
- Viewer HTML disables horizontal scrolling and keeps responsive SVG sizing.
"""

from __future__ import annotations

import json
import re
import sys
from datetime import date
from pathlib import Path
from typing import Any


BASE_DIR = Path(__file__).resolve().parents[3]
SCRIPTS_DIR = BASE_DIR / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from create_process_viewers import create_process_viewer  # noqa: E402


DATABASES = {
    "biology": BASE_DIR / "biology-processes-database",
    "chemistry": BASE_DIR / "chemistry-processes-database",
    "computer-science": BASE_DIR / "computer-science-processes-database",
    "physics": BASE_DIR / "physics-processes-database",
}

SKIP_SUBCATEGORIES = {"graph_type_pilots"}
MAX_NODE_LABEL = 28
MAX_EDGE_LABEL = 16


def compact_words(text: str, max_len: int) -> str:
    text = re.sub(r"\s+", " ", text.strip())
    text = re.sub(r"^(Observable readouts|Prediction layer|Feedback|Output):\s*", "", text)
    if len(text) <= max_len:
        return text
    separators = [":", ";", ",", " or ", " and ", " with ", " from ", " using "]
    candidates = []
    for sep in separators:
        if sep in text:
            candidates.append(text.split(sep, 1)[0])
    for candidate in candidates:
        candidate = candidate.strip()
        if 8 <= len(candidate) <= max_len:
            return candidate
    words = text.split()
    output: list[str] = []
    for word in words:
        trial = " ".join([*output, word])
        if len(trial) > max_len - 3:
            break
        output.append(word)
    return (" ".join(output) or text[: max_len - 3]).rstrip(",;:") + "..."


def compact_node_label(label: str) -> str:
    return compact_words(label, MAX_NODE_LABEL)


def compact_edge_label(label: str) -> str:
    common = {
        "yes": "yes",
        "no": "no",
        "true": "true",
        "false": "false",
        "iterate": "iterate",
        "recover": "recover",
        "repeat": "repeat",
    }
    lower = label.strip().lower()
    if lower in common:
        return common[lower]
    return compact_words(label, MAX_EDGE_LABEL)


NODE_PATTERN = re.compile(
    r"(?P<prefix>^\s*(?P<id>[A-Za-z][A-Za-z0-9_]*)\s*)"
    r"(?P<open>\[\(|\[\[|\[|\{|\()"
    r"(?P<label>\"[^\"]*\"|[^\]\}\)]*)"
    r"(?P<close>\)\]|\]\]|\]|\}|\))",
    flags=re.MULTILINE,
)

EDGE_LABEL_PATTERN = re.compile(r"(?P<open>-->\|)(?P<label>[^|]+)(?P<close>\|)")


def unquote(label: str) -> str:
    label = label.strip()
    if len(label) >= 2 and label[0] == '"' and label[-1] == '"':
        return label[1:-1]
    return label


def quote(label: str) -> str:
    return '"' + label.replace('"', "'") + '"'


def standardize_mermaid(mermaid: str) -> tuple[str, list[dict[str, str]], bool]:
    if not mermaid.strip():
        return mermaid, [], False
    output = re.sub(r"^\s*graph\s+(TD|LR|TB|BT|RL)\b", "graph TD", mermaid.strip(), count=1, flags=re.IGNORECASE)
    changed = output != mermaid.strip()
    node_details: list[dict[str, str]] = []

    def replace_node(match: re.Match[str]) -> str:
        nonlocal changed
        original = unquote(match.group("label"))
        compact = compact_node_label(original)
        node_details.append(
            {
                "id": match.group("id"),
                "label": compact,
                "detail": original,
                "type": "decision" if match.group("open") == "{" else "process",
            }
        )
        if compact != original or not match.group("label").startswith('"'):
            changed = True
        return f"{match.group('prefix')}{match.group('open')}{quote(compact)}{match.group('close')}"

    output = NODE_PATTERN.sub(replace_node, output)

    def replace_edge(match: re.Match[str]) -> str:
        nonlocal changed
        original = match.group("label").strip()
        compact = compact_edge_label(original)
        if compact != original:
            changed = True
        return f"{match.group('open')}{compact}{match.group('close')}"

    output = EDGE_LABEL_PATTERN.sub(replace_edge, output)
    return output, node_details, changed


def process_json_files() -> tuple[int, int]:
    visited = 0
    updated = 0
    today = date.today().isoformat()
    for discipline, database_dir in DATABASES.items():
        for path in sorted((database_dir / "processes").rglob("*.json")):
            if path.parent.name in SKIP_SUBCATEGORIES:
                continue
            data = json.loads(path.read_text(encoding="utf-8"))
            mermaid = data.get("mermaid")
            if not isinstance(mermaid, str) or not mermaid.strip():
                continue
            visited += 1
            standardized, details, changed = standardize_mermaid(mermaid)
            if changed:
                data["mermaid"] = standardized
                data["nodeDetails"] = details
                data["flowchartStandard"] = {
                    "name": "compact_vertical",
                    "applied": today,
                    "preservesFullLabelsIn": "nodeDetails",
                }
                data["lastUpdated"] = today
                path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
                updated += 1
            create_process_viewer(path, path.parent, discipline=discipline)
    return visited, updated


def patch_html_viewer(path: Path) -> bool:
    text = path.read_text(encoding="utf-8")
    original = text
    text = re.sub(r"overflow-x:\s*auto;", "overflow-x: hidden;", text)
    text = re.sub(r"overflow:\s*auto;", "overflow-x: hidden;\n            overflow-y: auto;", text)
    text = re.sub(r"max-height:\s*\d+vh;", "max-height: 78vh;", text)
    if ".flowchart-container {" in text and "max-height: 78vh;" not in text:
        text = text.replace(
            "overflow-x: hidden;",
            "overflow-x: hidden;\n            overflow-y: auto;\n            max-height: 78vh;",
            1,
        )
    text = re.sub(r"useMaxWidth:\s*false", "useMaxWidth: true", text)
    text = re.sub(r"nodeSpacing:\s*\d+", "nodeSpacing: 18", text)
    text = re.sub(r"rankSpacing:\s*\d+", "rankSpacing: 24", text)
    text = re.sub(r"padding:\s*10", "padding: 6", text)
    text = re.sub(r"^\s*graph\s+LR\b", "graph TD", text, flags=re.MULTILINE)
    if ".mermaid svg" not in text and ".mermaid {" in text:
        text = text.replace(
            "        .color-legend {",
            "        .mermaid svg {\n"
            "            max-width: 100% !important;\n"
            "            height: auto !important;\n"
            "            display: block;\n"
            "            margin: 0 auto;\n"
            "        }\n"
            "\n"
            "        .color-legend {",
            1,
        )
    if text != original:
        path.write_text(text, encoding="utf-8")
        return True
    return False


def patch_html_files() -> tuple[int, int]:
    visited = 0
    updated = 0
    for database_dir in DATABASES.values():
        for path in sorted((database_dir / "processes").rglob("*.html")):
            visited += 1
            if patch_html_viewer(path):
                updated += 1
    return visited, updated


def main() -> int:
    json_seen, json_updated = process_json_files()
    html_seen, html_updated = patch_html_files()
    print(f"JSON flowcharts standardized: {json_updated}/{json_seen}")
    print(f"HTML viewers patched: {html_updated}/{html_seen}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
