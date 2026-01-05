#!/usr/bin/env python3
"""
Sanitize Mermaid blocks in the Mathematics Processes HTML pages.

What it fixes (based on observed failures in math-processes-database pages):
- Inline/concatenated `style ...` directives mixed into node/edge statements
  (Mermaid parses more reliably when style statements are separate lines).
- Pretty-prints Mermaid so `graph TD` is on its own line and edge statements are
  split to one-per-line (easier debugging, more reliable parsing).
- A common typo for decision nodes: `{[` ... `]}` -> `{` ... `}`.
- Raw HTML-significant characters inside Mermaid source (`<`, `>`, `&`) that can be
  interpreted by the browser as tags/entities, corrupting the Mermaid text content.
  (e.g., `C < n?`, `<br>`, `<sup>...</sup>`).

Typical usage (downloads from GCS and writes sanitized copies):
  python3 scripts/sanitize_math_mermaid.py --download --output-dir ./sanitized_processes

Typical usage (sanitize local folder in-place):
  python3 scripts/sanitize_math_mermaid.py --input-dir ./processes --in-place
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import urllib.request
from collections import OrderedDict
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Optional, Tuple


DEFAULT_METADATA_URL = (
    "https://storage.googleapis.com/regal-scholar-453620-r7-podcast-storage/"
    "math-processes-database/metadata.json"
)
DEFAULT_PROCESS_HTML_URL_TEMPLATE = (
    "https://storage.googleapis.com/regal-scholar-453620-r7-podcast-storage/"
    "math-processes-database/processes/{process_id}.html"
)


MERMAID_BLOCK_RE = re.compile(
    r'(<div\s+class="mermaid"\s*>\s*)([\s\S]*?)(\s*</div>)',
    re.IGNORECASE,
)

# Observed style directive shape in the math pages.
STYLE_RE = re.compile(
    r"\bstyle\s+([A-Za-z]\w*)\s+fill:(#[0-9A-Fa-f]{3,6})\s*,\s*color:(#[0-9A-Fa-f]{3,6})\b"
)

BR_TAG_RE = re.compile(r"<br\s*/?>", re.IGNORECASE)
SUP_TAG_RE = re.compile(r"<sup>([\s\S]*?)</sup>", re.IGNORECASE)

# HTML entity detection to avoid double-escaping.
KNOWN_ENTITY_RE = re.compile(r"&(?:[a-zA-Z]+|#\d+|#x[0-9A-Fa-f]+);")

# Mermaid "graph"/"flowchart" header, often incorrectly glued to the first statement.
GRAPH_HEADER_RE = re.compile(r"^\s*(graph|flowchart)\s+(TD|LR|TB|RL)\b", re.IGNORECASE | re.MULTILINE)


def _pretty_print_mermaid_edges(src: str) -> Tuple[str, int]:
    """
    Best-effort pretty printer: puts Mermaid "graph/flowchart" header on its own line
    and splits concatenated edge chains so each edge starts on its own line.

    This is intentionally heuristic (not a full Mermaid parser), tuned for the
    observed math-process pages.
    """
    changes = 0
    before = src

    # Ensure the first "graph TD"/"flowchart TD" header is on its own line.
    # Example: "graph TD A1[...]" -> "graph TD\nA1[...]"
    def _split_header_line(m: re.Match) -> str:
        return f"{m.group(1)} {m.group(2)}"

    # Normalize any header to "graph|flowchart DIR", then insert newline after it
    # if more content follows on the same line.
    src = GRAPH_HEADER_RE.sub(_split_header_line, src)
    src2, n = re.subn(
        r"^\s*((?:graph|flowchart)\s+(?:TD|LR|TB|RL)\b)\s+",
        r"\1\n",
        src,
        flags=re.IGNORECASE | re.MULTILINE,
    )
    if n:
        src = src2
        changes += 1

    # Split concatenated statements before the start of an edge statement.
    # Insert a newline when we see: <punctuation-ending-a-node-or-label> <ID> <edge-op>
    # e.g. "]) B1 -- Yes -->" or '" C1 -- Yes -->' or "} I1 -- Yes -->"
    src2, n = re.subn(
        r'([\]\)\}"]) +(?=[A-Za-z]\w*\s*--)',
        r"\1\n",
        src,
    )
    if n:
        src = src2
        changes += 1

    # Also split edge chains where one edge ends with a bare node id and the next edge starts.
    # e.g. "G1 --> H1 H1 --> I1" -> "G1 --> H1\nH1 --> I1"
    src2, n = re.subn(
        r"(\b[A-Za-z]\w*\b)\s+(?=[A-Za-z]\w*\s*--)",
        r"\1\n",
        src,
    )
    if n:
        src = src2
        changes += 1

    # Cleanup: trim spaces around newlines.
    src2 = re.sub(r"[ \t]+\n", "\n", src)
    src2 = re.sub(r"\n[ \t]+", "\n", src2)
    if src2 != src:
        src = src2
        changes += 1

    if src != before:
        changes = max(changes, 1)
    return src, changes


@dataclass(frozen=True)
class ProcessSource:
    process_id: str
    html: str
    origin: str


def _http_get_text(url: str, timeout_seconds: int = 60) -> str:
    req = urllib.request.Request(
        url,
        headers={
            # Some CDNs behave better with an explicit UA.
            "User-Agent": "math-mermaid-sanitizer/1.0",
        },
    )
    with urllib.request.urlopen(req, timeout=timeout_seconds) as resp:
        raw = resp.read()
    return raw.decode("utf-8", errors="replace")


def _read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace")


def _write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8", newline="\n")


def _load_metadata(metadata_url: str) -> dict:
    if metadata_url.startswith("http://") or metadata_url.startswith("https://"):
        text = _http_get_text(metadata_url)
    else:
        text = _read_text(Path(metadata_url))
    return json.loads(text)


def _iter_process_ids(metadata: dict) -> Iterable[str]:
    processes = metadata.get("processes") or []
    for p in processes:
        pid = p.get("id")
        if pid:
            yield str(pid)


def _escape_html_for_mermaid(text: str) -> str:
    """
    Make Mermaid source safe to embed inside an HTML element without being parsed
    as markup, while preserving Mermaid semantics.
    """
    # Preserve explicit Mermaid line breaks represented as <br> tags in the source.
    br_token = "__MERMAID_BR__"
    text = BR_TAG_RE.sub(br_token, text)

    # Convert <sup>...</sup> to caret notation. (Keeps exponent visible and avoids HTML tags.)
    text = SUP_TAG_RE.sub(lambda m: "^" + m.group(1).strip(), text)

    # Escape raw < and > so the browser doesn't treat them as tags.
    text = text.replace("<", "&lt;").replace(">", "&gt;")

    # Escape bare ampersands (but avoid double-escaping entities).
    # Any '&' that does NOT begin a valid entity is converted to '&amp;'.
    text = re.sub(r"&(?![a-zA-Z]+;|#\d+;|#x[0-9A-Fa-f]+;)", "&amp;", text)

    # Re-introduce Mermaid-readable <br/> by embedding as escaped text.
    text = text.replace(br_token, "&lt;br/&gt;")
    return text


def _sanitize_mermaid_source(src: str) -> Tuple[str, int]:
    """
    Returns (sanitized_src, changes_count).
    """
    changes = 0
    original = src

    # Normalize newlines.
    src = src.replace("\r\n", "\n").replace("\r", "\n")

    # Fix `{[` ... `]}` decision-node typo.
    if "{[" in src:
        src = src.replace("{[", "{")
        changes += 1
    if "]}" in src:
        src = src.replace("]}", "}")
        changes += 1

    # Replace semicolon statement separators with newlines (seen in some pages).
    if ";" in src:
        src = src.replace(";", "\n")
        changes += 1

    # Extract style directives (even if already on their own lines) and re-emit them cleanly.
    styles: "OrderedDict[str, Tuple[str, str]]" = OrderedDict()
    for m in STYLE_RE.finditer(src):
        node_id, fill, color = m.group(1), m.group(2), m.group(3)
        # Keep last style for a node, preserve first-seen order for stability.
        if node_id in styles:
            styles[node_id] = (fill, color)
        else:
            styles[node_id] = (fill, color)

    if styles:
        src2, n = STYLE_RE.subn("", src)
        if n:
            src = src2
            changes += 1

    # Cleanup whitespace after removing style statements.
    src = re.sub(r"[ \t]+", " ", src)
    src = re.sub(r" *\n *", "\n", src)
    src = re.sub(r"\n{3,}", "\n\n", src).strip() + "\n"

    # Pretty-print edges onto separate lines (done before HTML-escaping).
    src2, pretty_changes = _pretty_print_mermaid_edges(src)
    if pretty_changes and src2 != src:
        src = src2
        changes += 1

    # HTML-sanitize the Mermaid text so it doesn't get corrupted by HTML parsing.
    escaped = _escape_html_for_mermaid(src)
    if escaped != src:
        src = escaped
        changes += 1

    # Append extracted style directives as separate lines at the end.
    if styles:
        src = src.rstrip("\n") + "\n\n"
        for node_id, (fill, color) in styles.items():
            src += f"style {node_id} fill:{fill},color:{color}\n"
        changes += 1

    if src != original:
        # Even if change counter missed some transformations.
        changes = max(changes, 1)
    return src, changes


def _sanitize_html_mermaid_blocks(html: str) -> Tuple[str, int, int]:
    """
    Returns (new_html, blocks_sanitized, total_changes_applied).
    """
    blocks = 0
    changes_total = 0

    def _repl(m: re.Match) -> str:
        nonlocal blocks, changes_total
        prefix, inner, suffix = m.group(1), m.group(2), m.group(3)
        sanitized, changes = _sanitize_mermaid_source(inner)
        blocks += 1
        changes_total += changes
        return prefix + sanitized + suffix

    new_html, n = MERMAID_BLOCK_RE.subn(_repl, html)
    return new_html, n, changes_total


def _get_process_source(
    process_id: str,
    *,
    input_dir: Optional[Path],
    process_html_url_template: str,
    download: bool,
) -> ProcessSource:
    if input_dir is not None:
        local_path = input_dir / f"{process_id}.html"
        if local_path.exists():
            return ProcessSource(process_id=process_id, html=_read_text(local_path), origin=str(local_path))
        if not download:
            raise FileNotFoundError(f"Missing local file and --download not set: {local_path}")

    url = process_html_url_template.format(process_id=process_id)
    return ProcessSource(process_id=process_id, html=_http_get_text(url), origin=url)


def main(argv: Optional[Iterable[str]] = None) -> int:
    p = argparse.ArgumentParser(description="Sanitize Mermaid blocks in math process HTML pages.")
    p.add_argument("--metadata", default=DEFAULT_METADATA_URL, help="Metadata JSON path or URL.")
    p.add_argument(
        "--process-html-url-template",
        default=DEFAULT_PROCESS_HTML_URL_TEMPLATE,
        help="URL template for process HTML pages (use {process_id}).",
    )
    p.add_argument(
        "--input-dir",
        default=None,
        help="Directory containing <process_id>.html files (optional).",
    )
    p.add_argument(
        "--output-dir",
        default=None,
        help="Directory to write sanitized HTML files (defaults to input-dir when --in-place, otherwise ./sanitized_processes).",
    )
    p.add_argument(
        "--download",
        action="store_true",
        help="Download missing process HTML files from --process-html-url-template.",
    )
    p.add_argument(
        "--in-place",
        action="store_true",
        help="Overwrite files in --input-dir. (Requires --input-dir.)",
    )
    p.add_argument(
        "--dry-run",
        action="store_true",
        help="Do not write files; just report what would change.",
    )
    p.add_argument(
        "--limit",
        type=int,
        default=0,
        help="Only process first N processes (0 = all).",
    )

    args = p.parse_args(list(argv) if argv is not None else None)

    input_dir = Path(args.input_dir).resolve() if args.input_dir else None
    if args.in_place and input_dir is None:
        print("ERROR: --in-place requires --input-dir", file=sys.stderr)
        return 2

    if args.output_dir:
        output_dir = Path(args.output_dir).resolve()
    else:
        if args.in_place and input_dir is not None:
            output_dir = input_dir
        else:
            output_dir = Path("./sanitized_processes").resolve()

    metadata = _load_metadata(args.metadata)
    ids = list(_iter_process_ids(metadata))
    if args.limit and args.limit > 0:
        ids = ids[: args.limit]

    total = len(ids)
    if total == 0:
        print("No processes found in metadata.", file=sys.stderr)
        return 1

    written = 0
    changed_files = 0
    total_blocks = 0
    total_changes = 0
    errors = 0

    for i, pid in enumerate(ids, start=1):
        try:
            src = _get_process_source(
                pid,
                input_dir=input_dir,
                process_html_url_template=args.process_html_url_template,
                download=args.download,
            )
            new_html, blocks, changes = _sanitize_html_mermaid_blocks(src.html)

            total_blocks += blocks
            total_changes += changes

            out_path = (output_dir / f"{pid}.html")
            is_changed = new_html != src.html
            if is_changed:
                changed_files += 1

            if args.dry_run:
                status = "CHANGED" if is_changed else "ok"
                print(f"[{i}/{total}] {pid}: {status} (blocks={blocks}, changes={changes}) [{src.origin}]")
                continue

            if args.in_place and input_dir is not None:
                # Always write into output_dir which equals input_dir in in-place mode.
                _write_text(out_path, new_html)
                written += 1
            else:
                # Write sanitized copies into output_dir.
                _write_text(out_path, new_html)
                written += 1

            status = "wrote" if is_changed else "wrote (no changes)"
            print(f"[{i}/{total}] {status}: {out_path}")

        except Exception as e:
            errors += 1
            print(f"[{i}/{total}] ERROR {pid}: {e}", file=sys.stderr)

    print("\nSummary:")
    print(f"- Processes attempted: {total}")
    print(f"- Files written: {written}" + (" (dry-run)" if args.dry_run else ""))
    print(f"- Files changed: {changed_files}")
    print(f"- Mermaid blocks found: {total_blocks}")
    print(f"- Total change operations: {total_changes}")
    print(f"- Errors: {errors}")

    return 0 if errors == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())

