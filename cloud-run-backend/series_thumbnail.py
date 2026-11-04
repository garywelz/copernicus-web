"""The series thumbnail ("CopernicusAI.fyi", direction C, "split field") drawn with Pillow, for the job to use when an episode has no
subject artwork of its own. The layout, colours and slots are those of docs/design/SERIES_THUMBNAIL.md (and of the SVG generator beside it); only the
title, the subtitle and the motif change. Pure code: no network, no model, no database.

The font is Inter (SIL Open Font License 1.1), stored at assets/fonts/Inter-Variable.ttf with its licence.
"""
from __future__ import annotations

import io
import os
from typing import List, Sequence, Tuple

from PIL import Image, ImageDraw, ImageFont

from channel import CHANNEL_NAME

INK, WHITE, GOLD = (0x1B, 0x2A, 0x41), (0xFF, 0xFF, 0xFF), (0xD9, 0xA4, 0x41)
LINE, BAND = (0xE8, 0xEC, 0xF2), (0x2B, 0x3C, 0x58)
SERIES_MARK = CHANNEL_NAME
FONT_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets", "fonts", "Inter-Variable.ttf")
MAX_TITLE_WORDS = 5
MOTIFS = ("lattice",)

_font_cache = {}


def font(size: float, weight: int) -> ImageFont.FreeTypeFont:
    key = (round(size, 1), weight)
    if key not in _font_cache:
        f = ImageFont.truetype(FONT_PATH, max(1, round(size)))
        f.set_variation_by_axes([32, weight])                 # optical size 32, as the SVG generator; then the weight
        _font_cache[key] = f
    return _font_cache[key]


def title_parts(title: str) -> Tuple[List[str], str]:
    """An episode title as (title lines, subtitle): 'Main words: the subtitle' splits at the first colon; the main part keeps at most five words in at
    most three lines (the first word alone on line 1, the rest balanced over lines 2 and 3)."""
    main, _, sub = (title or "").partition(":")
    words = main.split()[:MAX_TITLE_WORDS] or ["CopernicusAI"]
    if len(words) <= 3:
        lines = words
    else:
        rest = words[1:]
        cut = (len(rest) + 1) // 2
        lines = [words[0], " ".join(rest[:cut]), " ".join(rest[cut:])]
    return lines, sub.strip()


def _text(d, xy, s, f, fill, tracking=0.0, alpha=1.0):
    """Draw `s` with its baseline at xy[1] and its left edge at xy[0]; tracking in em."""
    x, y = xy
    if alpha < 1.0:
        fill = tuple(round(c * alpha + 255 * (1 - alpha)) for c in fill)      # on white
    if not tracking:
        d.text((x, y), s, font=f, fill=fill, anchor="ls")
        return
    for ch in s:
        d.text((x, y), ch, font=f, fill=fill, anchor="ls")
        x += f.getlength(ch) + tracking * f.size


def _fit(s: str, weight: int, size: float, max_width: float, tracking: float) -> float:
    w = sum(font(size, weight).getlength(c) + tracking * size for c in s)
    return size if w <= max_width else size * max_width / w


def lattice(d, x, y, w, h, k):
    """Neutral motif for an episode with no subject motif of its own: a drawn grid with a few gold nodes. `k` scales line weights (1 at 1280 wide)."""
    rows = 6
    cell = h / rows
    cols = max(3, round(w / cell))
    cw = w / cols
    for i in range(cols + 1):
        d.line([(x + i * cw, y), (x + i * cw, y + h)], fill=LINE, width=max(1, round(3 * k)))
    for j in range(rows + 1):
        d.line([(x, y + j * cell), (x + w, y + j * cell)], fill=LINE, width=max(1, round(3 * k)))
    nodes = [(1, 1), (2, 2), (cols - 1, 1), (1, 3), (cols - 2, 3), (2, 4), (cols - 1, 5), (cols // 2, 3)]
    r = 13 * k
    for c, rr in nodes:
        cx, cy = x + c * cw, y + rr * cell
        d.ellipse([cx - r - 4 * k, cy - r - 4 * k, cx + r + 4 * k, cy + r + 4 * k], fill=INK)
        d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=GOLD)


def render_16x9(title: str, ss: int = 2) -> bytes:
    """1280 x 720 PNG. Grid: white title panel x 0-800, ink motif panel x 800-1280; the bottom-right 220 x 90 px is kept clear (panel colour only)."""
    lines, sub = title_parts(title)
    W, H = 1280 * ss, 720 * ss
    img = Image.new("RGB", (W, H), WHITE)
    d = ImageDraw.Draw(img)
    d.rectangle([800 * ss, 0, W, H], fill=INK)
    _text(d, (70 * ss, 76 * ss), SERIES_MARK, font(25 * ss, 500), INK, tracking=0.1)
    sizes, baselines = [176, 116, 116][:len(lines)], [300, 440, 560][:len(lines)]
    for i, (line, s, y) in enumerate(zip(lines, sizes, baselines)):
        size = _fit(line, 800, s * ss, 694 * ss, -0.01)
        _text(d, ((66 if i == 0 else 68) * ss, y * ss), line, font(size, 800), INK, tracking=-0.01)
    if sub:
        size = _fit(sub, 500, 32 * ss, 690 * ss, 0.0)
        _text(d, (72 * ss, 630 * ss), sub, font(size, 500), INK, alpha=0.8)
    lattice(d, 900 * ss, 60 * ss, 280 * ss, 540 * ss, ss)
    return _png(img.resize((1280, 720), Image.BOX) if ss != 1 else img)


def render_square(title: str, ss: int = 1) -> bytes:
    """3000 x 3000 PNG. Grid: white title panel y 0-1830, ink motif panel y 1830-3000, 200 px margin."""
    lines, sub = title_parts(title)
    W = 3000 * ss
    img = Image.new("RGB", (W, W), WHITE)
    d = ImageDraw.Draw(img)
    d.rectangle([0, 1830 * ss, W, W], fill=INK)
    _text(d, (200 * ss, 250 * ss), SERIES_MARK, font(78 * ss, 500), INK, tracking=0.1)
    out = [f"{lines[0]} {lines[1]}"] + lines[2:] if len(lines) > 2 else lines
    size = min(430 * ss, min(_fit(l, 800, 430 * ss, 2600 * ss, -0.01) for l in out))
    y = 700 * ss
    for l in out:
        _text(d, (190 * ss, y), l, font(size, 800), INK, tracking=-0.01)
        y += size * 1.08
    if sub:
        _text(d, (200 * ss, 1720 * ss), sub, font(_fit(sub, 500, 130 * ss, 2600 * ss, 0.0), 500), INK, alpha=0.8)
    lattice(d, 300 * ss, 1990 * ss, 2400 * ss, 780 * ss, 2.3 * ss)
    return _png(img.resize((3000, 3000), Image.BOX) if ss != 1 else img)


def _png(img: Image.Image) -> bytes:
    buf = io.BytesIO()
    img.save(buf, format="PNG", optimize=True)
    return buf.getvalue()
