#!/usr/bin/env python3
"""
Build a PDF from knowledge_engine_vision_revised.md in a single run.

Must run end-to-end in one invocation: figures are rendered to FRESH filenames
(PNG/MMD produced by earlier sandbox runs are not readable in later runs) and
then embedded by pandoc via pdfLaTeX. A small header maps the one non-ASCII
math glyph (>=) that pdfLaTeX's inputenc does not handle by default.
"""

from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

PAPERS_DIR = Path(__file__).resolve().parent.parent
# Optional output suffix; intermediates always use a fresh timestamp because
# files written by earlier sandbox runs become read-only/locked.
import time
SUFFIX = ("_" + sys.argv[1]) if len(sys.argv) > 1 else ""
STAMP = str(int(time.time()))
SOURCE_MD = PAPERS_DIR / "knowledge_engine_vision_revised.md"
PROCESSED_MD = PAPERS_DIR / f"knowledge_engine_vision_revised_pdfbuild_{STAMP}.md"
PDF_FILE = PAPERS_DIR / f"knowledge_engine_vision_revised{SUFFIX}.pdf"
HEADER_TEX = PAPERS_DIR / f"pdf_header_{STAMP}.tex"
PUPPETEER_CFG = PAPERS_DIR / f"puppeteer-config-pdf_{STAMP}.json"

CAP_MMD = PAPERS_DIR / f"fig_cap_{STAMP}.mmd"
CAP_PNG = PAPERS_DIR / f"fig_cap_{STAMP}.png"
LIFE_MMD = PAPERS_DIR / f"fig_life_{STAMP}.mmd"
LIFE_PNG = PAPERS_DIR / f"fig_life_{STAMP}.png"
ARCH_MMD = PAPERS_DIR / "copernicusai_architecture.mmd"  # repo source, readable
ARCH_PNG = PAPERS_DIR / f"fig_arch_{STAMP}.png"

MERMAID_BLOCK_RE = re.compile(r"```mermaid\n(.*?)\n```", re.DOTALL)


def find_chrome() -> str | None:
    """Locate a Chromium/Chrome binary for mermaid-cli (puppeteer)."""
    env = os.environ.get("PUPPETEER_EXECUTABLE_PATH") or os.environ.get("CHROME_PATH")
    candidates: list[str] = []
    if env:
        candidates.append(env)
    for name in (
        "chromium-browser",
        "chromium",
        "google-chrome-stable",
        "google-chrome",
        "chrome",
    ):
        found = shutil.which(name)
        if found:
            candidates.append(found)
    cache = Path.home() / ".cache" / "puppeteer"
    if cache.is_dir():
        for pattern in ("chrome-headless-shell", "chrome"):
            for exe in cache.rglob(pattern):
                if exe.is_file() and os.access(exe, os.X_OK):
                    candidates.append(str(exe))
    for path in candidates:
        if path and Path(path).is_file():
            return path
    return None


def write_puppeteer_config(path: Path) -> str | None:
    chrome = find_chrome()
    cfg: dict[str, object] = {
        "args": ["--no-sandbox", "--disable-setuid-sandbox", "--disable-dev-shm-usage"],
    }
    if chrome:
        cfg["executablePath"] = chrome
        print(f"Using Chrome/Chromium: {chrome}")
    path.write_text(json.dumps(cfg, indent=2) + "\n", encoding="utf-8")
    return chrome


def render_mermaid(mmd_path: Path, png_path: Path) -> bool:
    cmd = [
        "npx", "-y", "@mermaid-js/mermaid-cli",
        "-i", str(mmd_path),
        "-o", str(png_path),
        "-b", "white",
        "-s", "4",
        "-p", str(PUPPETEER_CFG),
    ]
    result = subprocess.run(cmd, cwd=str(PAPERS_DIR), capture_output=True, text=True, timeout=180)
    if result.returncode != 0 or not png_path.exists():
        print(f"mermaid-cli failed for {mmd_path.name}:\n{result.stderr}", file=sys.stderr)
        return False
    print(f"Rendered {png_path.name}")
    return True


def main() -> int:
    if not SOURCE_MD.exists():
        print(f"Error: {SOURCE_MD} not found", file=sys.stderr)
        return 1
    text = SOURCE_MD.read_text(encoding="utf-8")

    chrome = write_puppeteer_config(PUPPETEER_CFG)
    if not chrome:
        print(
            "Error: no Chrome/Chromium found for mermaid-cli.\n"
            "  WSL/Linux: sudo apt install -y chromium-browser\n"
            "  Or: npx puppeteer browsers install chrome-headless-shell\n"
            "  Or: export PUPPETEER_EXECUTABLE_PATH=/path/to/chromium",
            file=sys.stderr,
        )
        return 1

    blocks = MERMAID_BLOCK_RE.findall(text)
    if len(blocks) < 2:
        print(f"Warning: expected 2 Mermaid blocks, found {len(blocks)}", file=sys.stderr)
    CAP_MMD.write_text(blocks[0] + "\n", encoding="utf-8")
    LIFE_MMD.write_text(blocks[1] + "\n", encoding="utf-8")
    ok = render_mermaid(CAP_MMD, CAP_PNG) and render_mermaid(LIFE_MMD, LIFE_PNG)
    if ARCH_MMD.exists():
        ok = ok and render_mermaid(ARCH_MMD, ARCH_PNG)
    else:
        print(f"Error: {ARCH_MMD.name} not found", file=sys.stderr)
        return 1
    if not ok or not all(p.exists() for p in (CAP_PNG, LIFE_PNG, ARCH_PNG)):
        print(
            "Error: one or more figure PNGs missing (mermaid-cli renders Figures 1–3).",
            file=sys.stderr,
        )
        return 1

    # Swap Mermaid blocks (in order) and the architecture image ref for the PNGs.
    repl = iter([f"![]({CAP_PNG.name})", f"![]({LIFE_PNG.name})"])
    processed = MERMAID_BLOCK_RE.sub(lambda m: next(repl, m.group(0)), text)
    processed = processed.replace(
        "![CopernicusAI Architecture](copernicusai_architecture.png)",
        f"![]({ARCH_PNG.name})",
    )
    PROCESSED_MD.write_text(processed, encoding="utf-8")

    HEADER_TEX.write_text(
        "\\usepackage{amssymb}\n"
        "\\DeclareUnicodeCharacter{2265}{\\ensuremath{\\geq}}\n",
        encoding="utf-8",
    )

    cmd = [
        "pandoc",
        str(PROCESSED_MD),
        "-o", str(PDF_FILE),
        "--resource-path", str(PAPERS_DIR),
        "--from", "markdown-implicit_figures",
        "--pdf-engine=pdflatex",
        "-H", str(HEADER_TEX),
        "-V", "geometry:margin=1in",
        "-V", "colorlinks=true",
        "-V", "linkcolor=blue",
        "-V", "urlcolor=blue",
    ]
    result = subprocess.run(cmd, cwd=str(PAPERS_DIR), capture_output=True, text=True, timeout=280)
    if result.returncode != 0:
        print("pandoc/pdflatex failed:", file=sys.stderr)
        print(result.stdout[-4000:], file=sys.stderr)
        print(result.stderr[-2000:], file=sys.stderr)
        return 1
    print(f"Wrote {PDF_FILE}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
