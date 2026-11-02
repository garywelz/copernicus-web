"""Titles and abstracts in a form a script can say aloud. The OpenAI release writes its titles and abstracts in GitHub-flavoured Markdown, with
mathematics inside `$` followed by a backtick (for example the real part of s greater than 7 over 8). A model shown that raw text copies it into the
script, and the notation check then refuses the script. `speakable` turns the mathematics into words and leaves every other character alone.

It is deliberately small: the notation that the release's titles and abstracts use, a fallback that drops a backslash from any other command, and
nothing cleverer. Anything it cannot say is left as plain letters, never as markup, so the result never contains `$`, a backtick or a backslash.
"""
from __future__ import annotations

import re

_SPAN = re.compile(r"\$`([^`]*)`\$|\$\$([^$]*)\$\$|\$([^$\n]+)\$")
_WORDS = {
    "Re": "real part of", "Im": "imaginary part of", "gt": "greater than", "lt": "less than", "ge": "at least", "geq": "at least", "le": "at most",
    "leq": "at most", "neq": "not equal to", "ne": "not equal to", "to": "to", "infty": "infinity", "in": "in", "cdot": "times", "times": "times",
    "pm": "plus or minus", "approx": "approximately", "sim": "of the order of", "equiv": "equivalent to", "subset": "subset of", "subseteq": "subset of",
    "cup": "union", "cap": "intersection", "sum": "sum", "prod": "product", "int": "integral", "log": "log", "ln": "log", "exp": "exp", "bmod": "mod",
    "mod": "mod", "pmod": "mod", "left": "", "right": "", "mathrm": "", "mathcal": "", "mathbf": "", "operatorname": "", "text": "",
}
_BLACKBOARD = re.compile(r"\\mathbb\s*\{?\s*([A-Za-z])\s*\}?")
_SQRT = re.compile(r"\\sqrt\s*(?:\[([^\]]*)\])?\s*\{([^{}]*)\}")
_FRAC = re.compile(r"\\[dt]?frac\s*\{([^{}]*)\}\s*\{([^{}]*)\}")
_SUP = re.compile(r"\^\s*(?:\{([^{}]*)\}|(\w))")
_SUB = re.compile(r"_\s*(?:\{([^{}]*)\}|(\w))")


def _sup(m: "re.Match") -> str:
    p = (m.group(1) or m.group(2) or "").strip()
    return {"2": " squared", "3": " cubed"}.get(p, f" to the {p}")


def speak_math(span: str) -> str:
    """The words for ONE mathematical span (the text between the dollar signs)."""
    s = span
    s = _BLACKBOARD.sub(lambda m: m.group(1), s)
    for _ in range(3):                                           # nested roots and fractions
        s = _SQRT.sub(lambda m: (f"{m.group(1)}-th root of " if m.group(1) else "square root of ") + m.group(2), s)
        s = _FRAC.sub(lambda m: f"{m.group(1)} over {m.group(2)}", s)
    s = _SUP.sub(_sup, s)
    s = _SUB.sub(lambda m: f" sub {(m.group(1) or m.group(2) or '').strip()}", s)
    s = re.sub(r"\\([A-Za-z]+)", lambda m: " " + _WORDS.get(m.group(1), m.group(1)) + " ", s)
    s = re.sub(r"(?<![\w)])-\s*(?=\d)", " minus ", s)               # "-3" is "minus 3"; "a-b" keeps its hyphen
    s = re.sub(r"(?<=\d)\s*/\s*(?=\d)", " over ", s)
    s = s.replace("<=", " at most ").replace(">=", " at least ").replace("<", " less than ").replace(">", " greater than ")
    s = s.replace("\\", " ").replace("{", " ").replace("}", " ").replace("`", " ").replace("$", " ")
    s = re.sub(r"\s*([(),;])\s*", lambda m: m.group(1) + (" " if m.group(1) in ",;" else ""), s)
    return re.sub(r"\s+", " ", s).strip()


def speakable(text: str) -> str:
    """`text` with every mathematical span replaced by the words for it. Text without a span is returned unchanged."""
    if not text or "$" not in text:
        return text or ""
    out = _SPAN.sub(lambda m: " " + speak_math(next(g for g in m.groups() if g is not None)) + " ", text)
    return re.sub(r"[ \t]{2,}", " ", re.sub(r"\s+([.,;:])", r"\1", out)).strip()


# How each commentary outlet is SAID aloud. The venue on a list item is a label for the record ("tao-web (AI-assisted summary reviewed by Terence
# Tao)", "Zenodo"); a listener should hear the outlet's ordinary name. An outlet not listed is said as its label with any bracket removed.
_SPOKEN_SOURCES = (
    ("quanta", "Quanta"), ("wikipedia", "Wikipedia"), ("scientific american", "Scientific American"), ("washington times", "the Washington Times"),
    ("tao", "Tao's own web page"), ("zenodo", "the Fields Medalists' declaration"), ("nature", "Nature"),
)


def spoken_source(venue: str) -> str:
    v = (venue or "").strip()
    low = v.lower()
    for key, said in _SPOKEN_SOURCES:
        if key in low:
            return said
    return re.sub(r"\s*\([^)]*\)", "", v).strip() or "the outlet"
