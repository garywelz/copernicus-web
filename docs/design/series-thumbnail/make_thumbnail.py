"""CopernicusAI · Frontiers of Science: series thumbnail generator (direction C, "split field").

Only the title, the subtitle and the motif change from one episode to the next; everything else (colours, grid, type, safe areas) is fixed here and
described in docs/design/SERIES_THUMBNAIL.md. The text is written as outlines (paths), so the output SVG does not depend on an installed font.

    python make_thumbnail.py --font Inter.ttf --out out_dir --slug ever-math-260015 \
        --title "722" "papers" "overnight" --subtitle "OpenAI's mathematics release" --motif critical_strip

Font: Inter (SIL Open Font License 1.1), the variable file from https://github.com/google/fonts/tree/main/ofl/inter. Needs fontTools.
Writes <slug>-16x9.svg (1280 x 720) and <slug>-square.svg (3000 x 3000); render PNGs from them with any SVG renderer.
"""
import argparse
import io
import os

from fontTools.pens.svgPathPen import SVGPathPen
from fontTools.pens.transformPen import TransformPen
from fontTools.ttLib import TTFont
from fontTools.varLib import instancer

INK, WHITE, GOLD = "#1B2A41", "#FFFFFF", "#D9A441"        # the whole palette: two neutrals and one accent
LINE, BAND = "#E8ECF2", "#2B3C58"                          # line colour on the dark panel; the inner band's fill (a lifted ink)
SERIES_MARK = "CopernicusAI · Frontiers of Science"

# (height fraction along the strip, offset across the inner band): the zeros of the episode 1 motif
ZEROS = [(0.10, -0.2), (0.22, 0.35), (0.33, -0.5), (0.47, 0.1), (0.60, -0.3), (0.72, 0.5), (0.85, -0.1), (0.94, 0.3)]


class Face:
    """One weight of the pinned font, as outlines."""

    def __init__(self, path, weight):
        vf = TTFont(path)
        axes = {a.axisTag: a.defaultValue for a in vf["fvar"].axes}
        axes.update({"wght": weight, "opsz": 32} if "opsz" in axes else {"wght": weight})
        inst = instancer.instantiateVariableFont(vf, axes)
        buf = io.BytesIO()
        inst.save(buf)
        buf.seek(0)
        self.font = TTFont(buf)
        self.glyphs = self.font.getGlyphSet()
        self.cmap = self.font.getBestCmap()
        self.upm = self.font["head"].unitsPerEm

    def width(self, text, size, tracking=0.0):
        return sum(self.glyphs[self.cmap[ord(c)]].width for c in text) * size / self.upm + tracking * size * len(text)

    def path(self, text, size, x, baseline, tracking=0.0):
        """The SVG path data of `text` with its left edge at x and its baseline at `baseline`."""
        k, pen_x, parts = size / self.upm, x, []
        for c in text:
            g = self.glyphs[self.cmap[ord(c)]]
            pen = SVGPathPen(self.glyphs)
            g.draw(TransformPen(pen, (k, 0, 0, -k, pen_x, baseline)))
            parts.append(pen.getCommands())
            pen_x += g.width * k + tracking * size
        return " ".join(p for p in parts if p)


def text(face, s, size, x, baseline, fill, tracking=0.0, opacity=1.0):
    extra = f' fill-opacity="{opacity}"' if opacity != 1.0 else ""
    return f'<path d="{face.path(s, size, x, baseline, tracking)}" fill="{fill}"{extra}/>'


def critical_strip(x, y, length, width, k, horizontal=False):
    """Motif slot: the critical strip of the zeta function, drawn as lines. Outer band = two lines, the critical line dashed in the middle, a narrower
    inner band and the zeros inside it. `length` runs along the strip, `width` across it; `k` scales the line weights (1 at 1280 px wide)."""
    def P(across, along):
        return (x + along, y + across) if horizontal else (x + across, y + along)

    def line(a1, l1, a2, l2, extra):
        (x1, y1), (x2, y2) = P(a1, l1), P(a2, l2)
        return f'<line x1="{x1:.1f}" y1="{y1:.1f}" x2="{x2:.1f}" y2="{y2:.1f}" {extra}/>'
    inner = width * 0.34
    mid = width / 2
    (bx, by) = P(mid - inner / 2, 0)
    bw, bh = (length, inner) if horizontal else (inner, length)
    out = [line(0, 0, 0, length, f'stroke="{LINE}" stroke-width="{5*k:.1f}" stroke-linecap="round"'),
           line(width, 0, width, length, f'stroke="{LINE}" stroke-width="{5*k:.1f}" stroke-linecap="round"'),
           f'<rect x="{bx:.1f}" y="{by:.1f}" width="{bw:.1f}" height="{bh:.1f}" fill="{BAND}" stroke="{GOLD}" stroke-width="{4*k:.1f}"/>',
           line(mid, 0, mid, length, f'stroke="{LINE}" stroke-width="{3*k:.1f}" stroke-dasharray="{3*k:.1f} {14*k:.1f}" stroke-linecap="round"')]
    for f, o in ZEROS:
        cx, cy = P(mid + o * inner * 0.38, f * length)
        out.append(f'<circle cx="{cx:.1f}" cy="{cy:.1f}" r="{13*k:.1f}" fill="{GOLD}" stroke="{INK}" stroke-width="{4*k:.1f}"/>')
    return "\n".join(out)


MOTIFS = {"critical_strip": critical_strip}


def svg(w, h, body):
    return f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}">\n{body}\n</svg>\n'


def make_16x9(title, subtitle, motif, bold, medium):
    """1280 x 720. Grid: 70 px margin; white title panel x 0-800; ink motif panel x 800-1280. Keep clear: bottom-right 220 x 90 (the video timestamp)."""
    body = [f'<rect width="1280" height="720" fill="{WHITE}"/>', f'<rect x="800" y="0" width="480" height="720" fill="{INK}"/>',
            text(medium, SERIES_MARK, 25, 70, 76, INK, tracking=0.1)]
    # title slot: x 66-760. Line 1 (a number or one short word) at 176 px, baseline 300; further lines at 116 px, baselines 440 and 560.
    sizes, baselines = [176, 116, 116][:len(title)], [300, 440, 560][:len(title)]
    for i, (line, s_, y) in enumerate(zip(title, sizes, baselines)):
        body.append(text(bold, line, s_, 66 if i == 0 else 68, y, INK, tracking=-0.01))
    body.append(text(medium, subtitle, 32, 72, 630, INK, opacity=0.8))
    body.append(motif(900, 60, 540, 280, 1.0))
    return svg(1280, 720, "\n".join(body))


def make_square(title, subtitle, motif, bold, medium):
    """3000 x 3000. Grid: 200 px margin; white title panel y 0-1830; ink motif panel y 1830-3000 with the strip laid horizontal."""
    body = [f'<rect width="3000" height="3000" fill="{WHITE}"/>', f'<rect x="0" y="1830" width="3000" height="1170" fill="{INK}"/>',
            text(medium, SERIES_MARK, 78, 200, 250, INK, tracking=0.1)]
    line1 = f"{title[0]} {title[1]}" if len(title) > 2 else title[0]
    rest = title[2:] if len(title) > 2 else title[1:]
    lines = [line1] + rest
    size = min(430, (3000 - 400) / max(bold.width(l, 1.0, -0.01) for l in lines))
    y = 700
    for l in lines:
        body.append(text(bold, l, size, 190, y, INK, tracking=-0.01))
        y += size * 1.08
    body.append(text(medium, subtitle, 130, 200, 1720, INK, opacity=0.8))
    body.append(motif(300, 1990, 2400, 780, 2.3, horizontal=True))
    return svg(3000, 3000, "\n".join(body))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--font", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--slug", required=True)
    ap.add_argument("--title", nargs="+", required=True, help="2 to 3 short lines; at most 4 to 5 words in all")
    ap.add_argument("--subtitle", required=True)
    ap.add_argument("--motif", default="critical_strip", choices=sorted(MOTIFS))
    a = ap.parse_args()
    assert len(" ".join(a.title).split()) <= 5, "the title is at most 5 words"
    bold, medium = Face(a.font, 800), Face(a.font, 500)
    motif = MOTIFS[a.motif]
    os.makedirs(a.out, exist_ok=True)
    for name, fn in (("16x9", make_16x9), ("square", make_square)):
        path = os.path.join(a.out, f"{a.slug}-{name}.svg")
        open(path, "w", encoding="utf-8").write(fn(a.title, a.subtitle, lambda *p, **kw: motif(*p, **kw), bold, medium))
        print(path)


if __name__ == "__main__":
    main()
