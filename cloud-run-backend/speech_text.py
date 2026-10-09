"""Text hygiene for what is spoken or published as prose (gap 3 fix 1).

The numbered list the generator is given labels papers [P1], [P2], ... for the model's reference only. Those labels must
never reach the audio, the transcript or the reader's description. Fix 3 (inline citation markers) will keep the marked
text in a separate field and use this same function to produce the clean text before audio.
"""
from __future__ import annotations

import re
from typing import Tuple

# [P3]  [P3, P5]  [P3][P5]  [P3-P5]  [P3 and P5]  (P3)  with optional space before the marker
_ONE = r"P\d{1,2}"
_MORE = r"(?:\s*[,;/&–-]\s*P?\d{1,2}|\s+(?:and|&)\s+P?\d{1,2})*"
PN_MARKER = re.compile(r"[ \t]*[\[(]\s*" + _ONE + _MORE + r"\s*[\])]")


def strip_pn_markers_counted(text: str) -> Tuple[str, int]:
    """Remove paper-label markers, and the space in front of them, so 'works [P3]. Next' reads 'works. Next'."""
    if not text:
        return text, 0
    return PN_MARKER.subn("", text)


def strip_pn_markers(text: str) -> str:
    return strip_pn_markers_counted(text)[0]
