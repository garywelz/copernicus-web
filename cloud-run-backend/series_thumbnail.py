"""The series thumbnail ("CopernicusAI.fyi", direction C, "split field") drawn with Pillow, for the job to use when an episode has no
subject artwork of its own. The layout, colours and slots are those of docs/design/SERIES_THUMBNAIL.md (and of the SVG generator beside it); only the
title, the subtitle and the motif change. Pure code: no network, no model, no database.

The font is Inter (SIL Open Font License 1.1), stored at assets/fonts/Inter-Variable.ttf with its licence.
"""
from __future__ import annotations

import io
import os
from typing import List, Optional, Sequence, Tuple

from PIL import Image, ImageDraw, ImageFont

from channel import CHANNEL_NAME

INK, WHITE, GOLD = (0x1B, 0x2A, 0x41), (0xFF, 0xFF, 0xFF), (0xD9, 0xA4, 0x41)
LINE, BAND = (0xE8, 0xEC, 0xF2), (0x2B, 0x3C, 0x58)
SERIES_MARK = CHANNEL_NAME
FONT_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets", "fonts", "Inter-Variable.ttf")
MAX_TITLE_WORDS = 5            # a title of up to this many words keeps the template's classic layout; a longer one is wrapped (no word is ever dropped)
MIN_TITLE_SIZE = 64            # px on the 1280-wide thumbnail (scaled for the square): a smaller title is not legible on a podcast app's small image
MIN_SUBTITLE_SIZE = 16         # the same, for the subtitle (its normal size is 32)
WRAP_MAX_SIZE = 116            # the largest a wrapped title is set (the classic layout's size for its second and third lines)
WRAP_MAX_LINES = 4
WRAP_SIZE_TOLERANCE = 0.10      # see _wrap
LINE_PITCH = 1.08              # line spacing, as a multiple of the font size
MOTIFS = ("lattice",)


class TitleDoesNotFit(ValueError):
    """The title or the subtitle cannot be set on the series template without cutting a word or making it illegible. The message says so in plain words; the
    thumbnail step fails with it (the episode still generates, with the default artwork) rather than the template cutting anything."""

_font_cache = {}


def font(size: float, weight: int) -> ImageFont.FreeTypeFont:
    key = (round(size, 1), weight)
    if key not in _font_cache:
        f = ImageFont.truetype(FONT_PATH, max(1, round(size)))
        f.set_variation_by_axes([32, weight])                 # optical size 32, as the SVG generator; then the weight
        _font_cache[key] = f
    return _font_cache[key]


def title_parts(title: str, subtitle: Optional[str] = None) -> Tuple[List[str], str]:
    """An episode title as (title lines, subtitle). With no `subtitle` given, 'Main words: the subtitle' splits at the first colon; with one given, the title
    is used whole (a colon in it stays) and the subtitle is the one given. NO WORD IS EVER DROPPED. A main part of up to five words is split in the template's
    classic way, into at most three lines (the first word alone on line 1, the rest balanced over lines 2 and 3); a longer one comes back as ONE line, which the
    renderer wraps and sizes to fit (or refuses, see TitleDoesNotFit)."""
    if subtitle is None:
        main, _, sub = (title or "").partition(":")
    else:
        main, sub = (title or ""), subtitle
    words = main.split() or ["CopernicusAI"]
    if len(words) > MAX_TITLE_WORDS:
        return [" ".join(words)], sub.strip()
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


def _line_width(text: str, size: float, tracking: float = -0.01) -> float:
    f = font(size, 800)
    return sum(f.getlength(c) + tracking * size for c in text)


def _wrap(words: List[str], max_width: float, block_height: float, max_size: float, min_size: float) -> Tuple[List[str], float]:
    """The words of a title (never fewer) set in 2 to WRAP_MAX_LINES lines of one size: for each line count, the split that makes the widest line narrowest, and
    the largest size at which that line fits the width and the lines fit the height. The fewest lines whose size is within WRAP_SIZE_TOLERANCE of the largest
    size found win (a few pixels of font are not worth an extra line). Raises TitleDoesNotFit when even the best is smaller than `min_size`."""
    ref = 100.0
    candidates = []
    for n_lines in range(2, min(WRAP_MAX_LINES, len(words)) + 1):
        # dynamic programme: split the words into n_lines contiguous groups, minimising the widest group (measured at the reference size)
        m = len(words)
        w = lambda a, b: _line_width(" ".join(words[a:b]), ref)
        INF = float("inf")
        cost = [[INF] * (m + 1) for _ in range(n_lines + 1)]
        cut = [[0] * (m + 1) for _ in range(n_lines + 1)]
        cost[0][0] = 0.0
        for k_ in range(1, n_lines + 1):
            for j in range(k_, m + 1):
                for i in range(k_ - 1, j):
                    c = max(cost[k_ - 1][i], w(i, j))
                    if c < cost[k_][j]:
                        cost[k_][j], cut[k_][j] = c, i
        groups, j = [], m
        for k_ in range(n_lines, 0, -1):
            i = cut[k_][j]
            groups.append(" ".join(words[i:j]))
            j = i
        groups.reverse()
        size = min(max_size, max_width / cost[n_lines][m] * ref, block_height / ((n_lines - 1) * LINE_PITCH + 0.93))
        size = float(int(size))
        while size >= min_size and max(_line_width(g, size) for g in groups) > max_width:       # the real width is not exactly linear in the size
            size -= 1
        if size >= min_size:
            candidates.append((groups, size))
    if candidates:
        top = max(size for _, size in candidates)
        best = next(c for c in candidates if c[1] >= top * (1 - WRAP_SIZE_TOLERANCE))          # candidates are in order of line count, fewest first
    else:
        best = None
    if best is None:
        raise TitleDoesNotFit(f'The thumbnail title "{" ".join(words)}" ({len(words)} words) is too long to set legibly on the series template without cutting words. '
                              f'Give a shorter thumbnail_title; the episode still generates, with the default artwork.')
    return best


def _title_lines(lines: List[str], kind: str, ss: int) -> List[Tuple[str, float, float]]:
    """(text, size, baseline) for each title line, in the units of the canvas being drawn (`kind` is '16x9' or 'square'; `ss` is the supersampling)."""
    sq = kind == "square"
    scale = (3000 / 1280) if sq else 1.0
    floor = MIN_TITLE_SIZE * scale
    if len(lines) <= 3:                              # the classic layout, unchanged
        if not sq:
            sizes, baselines = [176, 116, 116][:len(lines)], [300, 440, 560][:len(lines)]
            fitted = [_fit(l, 800, s * ss, 694 * ss, -0.01) for l, s in zip(lines, sizes)]
            if all(f / ss >= floor for f in fitted):
                return [(l, f, b * ss) for l, f, b in zip(lines, fitted, baselines)]
        else:
            out = [f"{lines[0]} {lines[1]}"] + lines[2:] if len(lines) > 2 else lines
            size = min(430 * ss, min(_fit(l, 800, 430 * ss, 2600 * ss, -0.01) for l in out))
            if size / ss >= floor:
                return [(l, size, (700 * ss) + i * size * 1.08) for i, l in enumerate(out)]
    words = " ".join(lines).split()
    if sq:
        groups, size = _wrap(words, 2600, 1220, 430, floor)
        top = 380
    else:
        groups, size = _wrap(words, 694, 435, WRAP_MAX_SIZE, floor)
        top = 150
    return [(g, size * ss, (top + 0.74 * size + i * size * LINE_PITCH) * ss) for i, g in enumerate(groups)]


def _subtitle_size(sub: str, base: float, max_width: float, ss: int, scale: float) -> float:
    size = _fit(sub, 500, base * ss, max_width * ss, 0.0)
    if size / ss < MIN_SUBTITLE_SIZE * scale:
        raise TitleDoesNotFit(f'The thumbnail subtitle "{sub}" is too long to set legibly on the series template without cutting words. '
                              f'Give a shorter thumbnail_subtitle; the episode still generates, with the default artwork.')
    return size


def render_16x9(title: str, ss: int = 2, subtitle: Optional[str] = None) -> bytes:
    """1280 x 720 PNG. Grid: white title panel x 0-800, ink motif panel x 800-1280; the bottom-right 220 x 90 px is kept clear (panel colour only). No word of the
    title or the subtitle is ever cut: a title is shrunk and wrapped to fit, and one that cannot be set legibly raises TitleDoesNotFit before anything is drawn."""
    lines, sub = title_parts(title, subtitle)
    placed = _title_lines(lines, "16x9", ss)
    sub_size = _subtitle_size(sub, 32, 690, ss, 1.0) if sub else None
    W, H = 1280 * ss, 720 * ss
    img = Image.new("RGB", (W, H), WHITE)
    d = ImageDraw.Draw(img)
    d.rectangle([800 * ss, 0, W, H], fill=INK)
    _text(d, (70 * ss, 76 * ss), SERIES_MARK, font(25 * ss, 500), INK, tracking=0.1)
    for i, (line, size, baseline) in enumerate(placed):
        _text(d, ((66 if i == 0 else 68) * ss, baseline), line, font(size, 800), INK, tracking=-0.01)
    if sub:
        _text(d, (72 * ss, 630 * ss), sub, font(sub_size, 500), INK, alpha=0.8)
    lattice(d, 900 * ss, 60 * ss, 280 * ss, 540 * ss, ss)
    return _png(img.resize((1280, 720), Image.BOX) if ss != 1 else img)


def render_square(title: str, ss: int = 1, subtitle: Optional[str] = None) -> bytes:
    """3000 x 3000 PNG. Grid: white title panel y 0-1830, ink motif panel y 1830-3000, 200 px margin. No word is ever cut (see render_16x9)."""
    lines, sub = title_parts(title, subtitle)
    placed = _title_lines(lines, "square", ss)
    sub_font_size = _subtitle_size(sub, 130, 2600, ss, 3000 / 1280) if sub else None
    W = 3000 * ss
    img = Image.new("RGB", (W, W), WHITE)
    d = ImageDraw.Draw(img)
    d.rectangle([0, 1830 * ss, W, W], fill=INK)
    _text(d, (200 * ss, 250 * ss), SERIES_MARK, font(78 * ss, 500), INK, tracking=0.1)
    for line, size, baseline in placed:
        _text(d, (190 * ss, baseline), line, font(size, 800), INK, tracking=-0.01)
    if sub:
        _text(d, (200 * ss, 1720 * ss), sub, font(sub_font_size, 500), INK, alpha=0.8)
    lattice(d, 300 * ss, 1990 * ss, 2400 * ss, 780 * ss, 2.3 * ss)
    return _png(img.resize((3000, 3000), Image.BOX) if ss != 1 else img)


def _png(img: Image.Image) -> bytes:
    buf = io.BytesIO()
    img.save(buf, format="PNG", optimize=True)
    return buf.getvalue()
