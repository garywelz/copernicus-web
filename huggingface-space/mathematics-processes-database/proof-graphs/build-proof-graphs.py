#!/usr/bin/env python3
"""Build Proof Graph Pilot HTML pages from local Markdown sources.

The pilot source files intentionally keep Mermaid blocks simple. This builder
converts those blocks into browser-rendered Mermaid diagrams, adds runtime
node-role coloring based on label prefixes, and appends the shared legend.
"""

from __future__ import annotations

import html
import re
from pathlib import Path


BASE = Path(__file__).resolve().parent

PAGES = [
    "README.md",
    "pilot-summary.md",
    "schema.md",
    "proof-graph-schema-v2.md",
    "design-notes.md",
    "infinitely-many-primes-v2-demo.md",
    "euclid-book-i-pilot.md",
    "infinitely-many-primes.md",
    "pythagorean-comparison.md",
    "fundamental-theorem-arithmetic.md",
    "cantor-diagonal-proofs.md",
]


STYLE = r"""    :root {
      color-scheme: light dark;
      --bg: #0f172a;
      --panel: #111827;
      --text: #e5e7eb;
      --muted: #9ca3af;
      --accent: #60a5fa;
      --border: #334155;
      --code-bg: #020617;
    }
    @media (prefers-color-scheme: light) {
      :root {
        --bg: #f8fafc;
        --panel: #ffffff;
        --text: #111827;
        --muted: #4b5563;
        --accent: #2563eb;
        --border: #d1d5db;
        --code-bg: #f1f5f9;
      }
    }
    * { box-sizing: border-box; }
    body {
      margin: 0;
      font-family: system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
      background: var(--bg);
      color: var(--text);
      line-height: 1.6;
    }
    main {
      max-width: 1120px;
      margin: 0 auto;
      padding: 36px 20px 64px;
    }
    article {
      border: 1px solid var(--border);
      background: var(--panel);
      border-radius: 14px;
      padding: 28px;
    }
    nav {
      display: flex;
      flex-wrap: wrap;
      gap: 14px;
      margin-bottom: 18px;
      color: var(--muted);
      font-size: 0.95rem;
    }
    nav a, a { color: var(--accent); }
    h1 { margin-top: 0; font-size: 2rem; line-height: 1.2; }
    h2 { margin-top: 2rem; border-top: 1px solid var(--border); padding-top: 1.2rem; }
    h3 { margin-top: 1.6rem; }
    p, li { color: var(--text); }
    ul, ol { padding-left: 1.35rem; }
    code {
      background: var(--code-bg);
      border: 1px solid var(--border);
      border-radius: 4px;
      padding: 0.05rem 0.25rem;
      font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, "Liberation Mono", monospace;
      font-size: 0.92em;
    }
    pre {
      overflow-x: auto;
      background: var(--code-bg);
      border: 1px solid var(--border);
      border-radius: 10px;
      padding: 16px;
    }
    pre code { background: transparent; border: 0; padding: 0; }
    .mermaid {
      background: #ffffff;
      color: #111827;
      border: 1px solid var(--border);
      border-radius: 12px;
      margin: 18px 0;
      padding: 18px;
      overflow-x: auto;
    }
    .mermaid svg { max-width: 100%; height: auto; }
    .proof-legend {
      margin-top: 28px;
      border: 1px solid var(--border);
      border-radius: 12px;
      padding: 16px;
      background: color-mix(in srgb, var(--panel) 88%, var(--accent));
    }
    .proof-legend h2 {
      border-top: 0;
      margin: 0 0 12px;
      padding-top: 0;
      font-size: 1.05rem;
    }
    .proof-legend-grid {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
      gap: 10px 14px;
    }
    .proof-legend-item {
      display: flex;
      align-items: center;
      gap: 8px;
      color: var(--text);
      font-size: 0.92rem;
    }
    .proof-legend-swatch {
      width: 18px;
      height: 18px;
      border-radius: 5px;
      border: 2px solid currentColor;
      flex: 0 0 auto;
    }
    .legend-source { background: #f2c879; color: #7a4f12; }
    .legend-assumption { background: #c084fc; color: #6d28d9; }
    .legend-construction { background: #8fbc5a; color: #3f6212; }
    .legend-assertion { background: #8ecae6; color: #25637a; }
    .legend-inference { background: #f4a261; color: #9a3412; }
    .legend-algorithm { background: #818cf8; color: #3730a3; }
    .legend-contradiction { background: #ef4444; color: #991b1b; }
    .legend-conclusion { background: #2dd4bf; color: #0f766e; }
    .source-note {
      margin-top: 32px;
      color: var(--muted);
      font-size: 0.95rem;
    }
"""


MERMAID_SCRIPT = r"""  <script type="module">
    import mermaid from 'https://cdn.jsdelivr.net/npm/mermaid@10/dist/mermaid.esm.min.mjs';

    const roleStyles = `
classDef proofSource fill:#f2c879,stroke:#7a4f12,color:#0f172a,stroke-width:2px;
classDef proofAssumption fill:#c084fc,stroke:#6d28d9,color:#0f172a,stroke-width:2px;
classDef proofConstruction fill:#8fbc5a,stroke:#3f6212,color:#0f172a,stroke-width:2px;
classDef proofAssertion fill:#8ecae6,stroke:#25637a,color:#0f172a,stroke-width:2px;
classDef proofInference fill:#f4a261,stroke:#9a3412,color:#0f172a,stroke-width:2px;
classDef proofAlgorithm fill:#818cf8,stroke:#3730a3,color:#0f172a,stroke-width:2px;
classDef proofContradiction fill:#ef4444,stroke:#991b1b,color:#ffffff,stroke-width:3px;
classDef proofConclusion fill:#2dd4bf,stroke:#0f766e,color:#0f172a,stroke-width:3px;
classDef proofNeutral fill:#f8fafc,stroke:#64748b,color:#0f172a,stroke-width:1.5px;
`;

    const roleRules = [
      ['proofConclusion', /^(Conclusion:|Discharge assumption:|Discharge:)/i],
      ['proofContradiction', /^Contradiction:/i],
      ['proofAssumption', /^(Assumption:|Assume:|Methodological assumption:)/i],
      ['proofAlgorithm', /^(Algorithm capsule:|Input:|Output:|Start |Set |For each |Read |Choose output|Put |List |Skip |Increase |Arrange |Make |Find |Factor |Concatenate|Multiply )/i],
      ['proofConstruction', /^Construction:/i],
      ['proofAssertion', /^Assertion:/i],
      ['proofInference', /^(Inference:|Branch:|Join:)/i],
      ['proofSource', /^(Given:|Definition|Postulate|Common Notion|Euclid |Lemma:|Arithmetic fact:|Strong induction|Cancellation law|Bezout)/i]
    ];

    function classify(label, shape) {
      const normalized = label.trim().replace(/\s+/g, ' ');
      if (shape === '{') return 'proofInference';
      if (/^Target:/i.test(normalized)) return 'proofConclusion';
      for (const [role, pattern] of roleRules) {
        if (pattern.test(normalized)) return role;
      }
      return 'proofNeutral';
    }

    function addRoleClasses(source) {
      if (source.includes('classDef proofSource')) return source;
      const assignments = new Map();
      const nodePattern = /(?:^|\s)([A-Za-z][\w-]*)\s*(?:\[\s*"([^"]+)"\s*\]|\{\s*"([^"]+)"\s*\}|\(\s*"([^"]+)"\s*\)|\(\[\s*"([^"]+)"\s*\]\)|\[\[\s*"([^"]+)"\s*\]\]|\[\/\s*"([^"]+)"\s*\/\]|\(\(\s*"([^"]+)"\s*\)\))/gm;
      let match;
      while ((match = nodePattern.exec(source)) !== null) {
        const nodeId = match[1];
        const label = match.slice(2).find(Boolean);
        const shape = match[3] ? '{' : '';
        assignments.set(nodeId, classify(label, shape));
      }
      const classLines = Array.from(assignments.entries()).map(([nodeId, role]) => `class ${nodeId} ${role};`);
      if (classLines.length === 0) return `${source}\n${roleStyles}`;
      return `${source}\n${roleStyles}\n${classLines.join('\n')}`;
    }

    document.querySelectorAll('pre.mermaid').forEach((block) => {
      block.textContent = addRoleClasses(block.textContent);
    });

    mermaid.initialize({
      startOnLoad: false,
      securityLevel: 'loose',
      theme: 'base',
      themeVariables: {
        background: '#ffffff',
        primaryColor: '#f8fafc',
        primaryTextColor: '#0f172a',
        primaryBorderColor: '#64748b',
        lineColor: '#475569',
        fontFamily: 'system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif'
      },
      flowchart: {
        htmlLabels: true,
        curve: 'basis',
        nodeSpacing: 42,
        rankSpacing: 58
      }
    });
    await mermaid.run({ querySelector: 'pre.mermaid' });
  </script>"""


LEGEND = """      <section class="proof-legend" aria-label="Proof graph color legend">
        <h2>Proof Graph Color Legend</h2>
        <div class="proof-legend-grid">
          <div class="proof-legend-item"><span class="proof-legend-swatch legend-source"></span><span>Amber: source / given / definition / lemma</span></div>
          <div class="proof-legend-item"><span class="proof-legend-swatch legend-assumption"></span><span>Violet: assumption or temporary hypothesis</span></div>
          <div class="proof-legend-item"><span class="proof-legend-swatch legend-construction"></span><span>Moss: construction or introduced object</span></div>
          <div class="proof-legend-item"><span class="proof-legend-swatch legend-assertion"></span><span>Steel: assertion established in the proof</span></div>
          <div class="proof-legend-item"><span class="proof-legend-swatch legend-inference"></span><span>Copper: inference, branch, or proof move</span></div>
          <div class="proof-legend-item"><span class="proof-legend-swatch legend-algorithm"></span><span>Indigo: algorithm or procedural step</span></div>
          <div class="proof-legend-item"><span class="proof-legend-swatch legend-contradiction"></span><span>Crimson: contradiction</span></div>
          <div class="proof-legend-item"><span class="proof-legend-swatch legend-conclusion"></span><span>Teal: discharge or final conclusion</span></div>
        </div>
      </section>
"""


def inline(text: str) -> str:
    escaped = html.escape(text)
    escaped = re.sub(r"`([^`]+)`", r"<code>\1</code>", escaped)
    escaped = re.sub(r"\*\*([^*]+)\*\*", r"<strong>\1</strong>", escaped)
    escaped = re.sub(r"\*([^*]+)\*", r"<em>\1</em>", escaped)
    return escaped


def flush_paragraph(parts: list[str], out: list[str]) -> None:
    if parts:
        out.append(f"<p>{inline(' '.join(parts))}</p>")
        parts.clear()


def convert_markdown(md: str) -> tuple[str, bool]:
    out: list[str] = []
    paragraph: list[str] = []
    in_list = False
    in_mermaid = False
    mermaid_lines: list[str] = []
    has_mermaid = False

    for raw in md.splitlines():
        line = raw.rstrip()
        if in_mermaid:
            if line.strip() == "```":
                out.append(f'<pre class="mermaid">{html.escape(chr(10).join(mermaid_lines))}</pre>')
                mermaid_lines = []
                in_mermaid = False
                has_mermaid = True
            else:
                mermaid_lines.append(line)
            continue

        if line.strip() == "```mermaid":
            flush_paragraph(paragraph, out)
            if in_list:
                out.append("</ul>")
                in_list = False
            in_mermaid = True
            continue

        if not line.strip():
            flush_paragraph(paragraph, out)
            if in_list:
                out.append("</ul>")
                in_list = False
            continue

        heading = re.match(r"^(#{1,3})\s+(.+)$", line)
        if heading:
            flush_paragraph(paragraph, out)
            if in_list:
                out.append("</ul>")
                in_list = False
            level = len(heading.group(1))
            out.append(f"<h{level}>{inline(heading.group(2))}</h{level}>")
            continue

        bullet = re.match(r"^-\s+(.+)$", line)
        if bullet:
            flush_paragraph(paragraph, out)
            if not in_list:
                out.append("<ul>")
                in_list = True
            out.append(f"<li>{inline(bullet.group(1))}</li>")
            continue

        paragraph.append(line.strip())

    flush_paragraph(paragraph, out)
    if in_list:
        out.append("</ul>")
    if in_mermaid:
        raise ValueError("Unclosed mermaid block")
    return "\n".join(out), has_mermaid


def render_page(markdown_path: Path) -> None:
    md = markdown_path.read_text(encoding="utf-8")
    title = next((line[2:].strip() for line in md.splitlines() if line.startswith("# ")), markdown_path.stem)
    body, has_mermaid = convert_markdown(md)
    legend = LEGEND if has_mermaid else ""
    script = MERMAID_SCRIPT if has_mermaid else ""
    output = BASE / f"{markdown_path.stem}.html"
    output.write_text(
        f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{html.escape(title)} - Proof Graph Pilot</title>
  <style>
{STYLE}</style>
</head>
<body>
  <main>
    <nav>
      <a href="index.html">Proof Graph Pilot</a>
      <span>/</span>
      <a href="../mathematics-database-table.html">Mathematics Database</a>
      <span>/</span>
      <a href="{markdown_path.name}">View Markdown source</a>
    </nav>
    <article>
{body}
{legend}      <p class="source-note">Rendered from <code>{markdown_path.name}</code>. Mermaid diagrams are rendered in the browser from the source graph blocks.</p>
    </article>
  </main>
{script}
</body>
</html>
""",
        encoding="utf-8",
    )
    print(f"wrote {output.name}")


def main() -> None:
    for page in PAGES:
        render_page(BASE / page)


if __name__ == "__main__":
    main()
