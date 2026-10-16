"""Text hygiene for what is spoken or published as prose (gap 3 fix 1).

1. Paper labels. The numbered list the generator is given labels papers [P1], [P2], ... for the model's reference only. Those
   labels must never reach the audio, the transcript or the reader's description. Fix 3 (inline citation markers) will keep the
   marked text in a separate field and use strip_pn_markers to produce the clean text before audio.

2. Mathematical notation. A script is read aloud, so LaTeX such as $D_s^+ \\to K_S^0 K_L^0 \\pi^+$ must become words. The prompt asks
   the model to write symbols as words; speak_math() converts what remains using a small table of common notation, and
   find_unspeakable() reports notation the table does not cover so the caller can regenerate with feedback and, if that fails,
   fail the episode. Unknown notation is never silently dropped from a script. latex_display() makes registry titles readable on
   screen (Unicode); it is for display only and the stored title is never changed.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import List, Optional, Tuple

# ---------------------------------------------------------------------------------------------- paper labels
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


# ---------------------------------------------------------------------------------------------- notation tables
GREEK_NAMES = ("alpha beta gamma delta epsilon zeta eta theta iota kappa lambda mu nu xi omicron pi rho sigma tau upsilon phi chi psi omega").split()
_GREEK_LOWER = "αβγδεζηθικλμνξοπρστυφχψω"
_GREEK_UPPER = "ΑΒΓΔΕΖΗΘΙΚΛΜΝΞΟΠΡΣΤΥΦΧΨΩ"
_GREEK_UPPER_NAMES = ("Alpha Beta Gamma Delta Epsilon Zeta Eta Theta Iota Kappa Lambda Mu Nu Xi Omicron Pi Rho Sigma Tau Upsilon Phi Chi Psi Omega").split()
UNICODE_GREEK = {}
for _c, _n in zip(_GREEK_LOWER.replace("ς", ""), GREEK_NAMES):
    UNICODE_GREEK[_c] = _n
for _c, _n in zip(_GREEK_UPPER, _GREEK_UPPER_NAMES):
    UNICODE_GREEK[_c] = _n
UNICODE_GREEK["ς"] = "sigma"
UNICODE_GREEK["ϕ"] = "phi"

MACRO_GREEK = {n: n for n in GREEK_NAMES}
MACRO_GREEK.update({n: n for n in _GREEK_UPPER_NAMES if n not in ("Alpha", "Beta", "Epsilon", "Zeta", "Eta", "Iota", "Kappa", "Mu", "Nu", "Omicron", "Rho", "Tau", "Chi")})
MACRO_GREEK.update({"varepsilon": "epsilon", "vartheta": "theta", "varphi": "phi", "varrho": "rho", "varsigma": "sigma", "varpi": "pi"})

MACRO_WORDS = {
    "to": "to", "rightarrow": "to", "longrightarrow": "to", "Rightarrow": "implies", "Longrightarrow": "implies", "leftarrow": "from",
    "leftrightarrow": "and back", "pm": "plus or minus", "mp": "minus or plus", "times": "times", "cdot": "times", "div": "divided by",
    "approx": "approximately", "sim": "about", "simeq": "about", "propto": "proportional to", "neq": "not equal to", "ne": "not equal to",
    "leq": "less than or equal to", "le": "less than or equal to", "geq": "greater than or equal to", "ge": "greater than or equal to",
    "ll": "much less than", "gg": "much greater than", "infty": "infinity", "degree": "degrees", "circ": "degrees", "ldots": "and so on",
    "dots": "and so on", "cdots": "and so on", "ell": "ell", "hbar": "h bar", "prime": "prime", "star": "star", "ast": "star",
    "rightleftharpoons": "in equilibrium with", "gt": "greater than", "lt": "less than", "percent": "percent", "%": "percent",
}
MACRO_WRAP = {"mathrm", "text", "textrm", "mathit", "mathbf", "textbf", "mathsf", "boldsymbol", "operatorname", "mbox", "textit", "rm", "mathbb", "mathcal"}
MACRO_ACCENT = {"bar": "bar", "overline": "bar", "hat": "hat", "tilde": "tilde", "vec": "vector", "dot": "dot"}
SUP_WORDS = {"+": "plus", "-": "minus", "0": "zero", "*": "star", "2": "squared", "3": "cubed", "++": "double plus", "--": "double minus", "'": "prime", "\\prime": "prime"}
KAON_SUB = {"S": "short", "L": "long"}
ALLOWED_PUNCT = set(".,;:()[]'!?%~")


@dataclass
class SpokenMath:
    words: str
    unknown: List[str] = field(default_factory=list)


class _Parser:
    def __init__(self, s: str):
        self.s = re.sub(r"\\\\(?=[A-Za-z])", r"\\", s)  # models sometimes double the backslash: \\pi
        self.i = 0
        self.unknown: List[str] = []

    def parse(self, stop: Optional[str] = None) -> str:
        parts: List[str] = []
        while self.i < len(self.s):
            c = self.s[self.i]
            if stop and c == stop:
                break
            atom = self.atom()
            if atom is None:
                continue
            word, base = atom
            parts.append(self.scripts(word, base))
        return re.sub(r"\s+", " ", " ".join(p for p in parts if p)).strip()

    def peek_ws(self):
        while self.i < len(self.s) and self.s[self.i].isspace():
            self.i += 1

    def group(self) -> str:
        """Read a {...} group or a single token as a sub-expression and return its spoken form."""
        self.peek_ws()
        if self.i >= len(self.s):
            return ""
        if self.s[self.i] == "{":
            self.i += 1
            inner = self.parse(stop="}")
            self.i += 1  # closing brace
            return inner
        atom = self.atom()
        return atom[0] if atom else ""

    def raw_group(self) -> str:
        """The literal text of a {...} group or one character, for scripts (so S(L) and L,S can be recognised)."""
        self.peek_ws()
        if self.i >= len(self.s):
            return ""
        if self.s[self.i] == "{":
            depth, j = 0, self.i
            while j < len(self.s):
                depth += {"{": 1, "}": -1}.get(self.s[j], 0)
                j += 1
                if depth == 0:
                    break
            raw, self.i = self.s[self.i + 1:j - 1], j
            return raw
        if self.s[self.i] == "\\":
            m = re.match(r"\\([A-Za-z]+)", self.s[self.i:])
            if m:
                self.i += m.end()
                return "\\" + m.group(1)
        raw = self.s[self.i]
        self.i += 1
        return raw

    def atom(self):
        s, c = self.s, self.s[self.i]
        if c.isspace():
            self.i += 1
            return None
        if c == "{":
            self.i += 1
            inner = self.parse(stop="}")
            self.i += 1
            return inner, inner
        if c == "\\":
            m = re.match(r"\\([A-Za-z]+|.)", s[self.i:])
            name = m.group(1)
            self.i += m.end()
            if name in MACRO_GREEK:
                return MACRO_GREEK[name], MACRO_GREEK[name]
            if name in MACRO_WORDS:
                return MACRO_WORDS[name], None
            if name in MACRO_WRAP:
                inner = self.group()
                return inner, inner
            if name in MACRO_ACCENT:
                inner = self.group()
                return inner, (inner, MACRO_ACCENT[name])
            if name == "frac":
                a, b = self.group(), self.group()
                return f"{a} over {b}", None
            if name == "sqrt":
                return f"square root of {self.group()}", None
            if name in (",", ";", ":", " ", "!", "quad", "qquad"):
                return None
            if name in ("{", "}", "%", "&", "_", "#", "$"):
                return {"%": "percent", "&": "and", "_": "underscore", "#": "number", "$": "dollars"}.get(name, ""), None
            self.unknown.append("\\" + name)
            return None
        if c in UNICODE_GREEK:
            self.i += 1
            return UNICODE_GREEK[c], UNICODE_GREEK[c]
        if c in "+-=<>/":
            self.i += 1
            if c in "+-" and self.i < len(s) and s[self.i] in "_^":  # a charge on the previous atom, handled in scripts
                pass
            return {"+": "plus", "-": "minus", "=": "equals", "<": "less than", ">": "greater than", "/": "over"}[c], None
        if c.isalpha() or c.isdigit():
            j = self.i
            if c.isdigit():
                while j < len(s) and (s[j].isdigit() or (s[j] in ".," and j + 1 < len(s) and s[j + 1].isdigit())):
                    j += 1
                word = s[self.i:j]
                self.i = j
                return word, word
            self.i += 1
            return c, c
        if c in ALLOWED_PUNCT:
            self.i += 1
            return c, None
        self.unknown.append(c)
        self.i += 1
        return None

    def scripts(self, word: str, base) -> str:
        sub = sup = None
        while True:
            self.peek_ws()
            if self.i < len(self.s) and self.s[self.i] == "_" and sub is None:
                self.i += 1
                sub = self.raw_group()
            elif self.i < len(self.s) and self.s[self.i] == "^" and sup is None:
                self.i += 1
                sup = self.raw_group()
            else:
                break
        accent = None
        if isinstance(base, tuple):
            base, accent = base
        out = word
        kaon = isinstance(base, str) and base == "K" and sub is not None
        kaon_sub = False
        if sub is not None:
            raw = re.sub(r"\\mathrm|\\text|\\rm", "", sub).replace("{", "").replace("}", "").strip()
            letters = re.findall(r"[A-Za-z]", raw)
            kaon_sub = bool(kaon and letters and all(l in KAON_SUB for l in letters) and set(raw) <= set("SL(),/ &"))
            if kaon_sub:
                out += " " + " or ".join(KAON_SUB[l] for l in letters)
            else:
                spoken = _Sub(raw)
                out += " sub " + spoken
                self.unknown += spoken.unknown
        if sup is not None:
            raw = sup.strip()
            key = raw.replace("{", "").replace("}", "").replace(" ", "")
            if key == "0" and kaon_sub:
                pass  # K_S^0 and K_L^0 are just "K short" and "K long"
            elif key in SUP_WORDS:
                out += " " + SUP_WORDS[key]
            elif re.fullmatch(r"[A-Za-z]", key):
                out += " to the " + key
            elif re.fullmatch(r"\d+", key):
                out += " to the " + key
            elif key == "\\prime":
                out += " prime"
            else:
                inner = _Sub(raw)
                if inner.unknown:
                    self.unknown += inner.unknown
                else:
                    out += " to the " + str(inner)
        if accent:
            out += " " + accent
        return out


class _Sub(str):
    """Spoken form of a sub-expression; keeps the unknown tokens it met."""

    def __new__(cls, raw: str):
        p = _Parser(raw)
        words = p.parse()
        obj = super().__new__(cls, words)
        obj.unknown = p.unknown
        return obj


def speak_math(expr: str) -> SpokenMath:
    """Spoken words for one LaTeX math expression (without the dollar signs)."""
    p = _Parser(expr)
    return SpokenMath(p.parse(), p.unknown)


# math spans: $$...$$, $...$, \( ... \)
_SPAN = re.compile(r"\$\$(.+?)\$\$|\$(?!\s)([^$\n]{1,400}?)(?<!\s)\$|\\\((.+?)\\\)", re.S)
_STRAY = re.compile(r"\\\\?([A-Za-z]{2,})")


_CONTROL_MACRO = {"\t": "\\t", "\x08": "\\b", "\x0c": "\\f"}


def _undo_json_escapes(s: str) -> str:
    """A model that writes \\to, \\bar or \\frac inside a JSON string gets a tab, a backspace or a form feed back instead of the
    backslash sequence. Put the macro back (a real tab, backspace or form feed in a script is never wanted anyway)."""
    return re.sub(r"\\?([\t\x08\x0c])", lambda m: _CONTROL_MACRO[m.group(1)], s)


def speak_text(text: str) -> Tuple[str, List[str]]:
    """Convert every math span in ``text`` to words. Returns (text, unknown notation found). A span with unknown notation is
    left exactly as written so the caller can see it; nothing is dropped."""
    if not text:
        return text, []
    unknown: List[str] = []
    text = _undo_json_escapes(text)

    def repl(m: re.Match) -> str:
        body = next(g for g in m.groups() if g is not None)
        r = speak_math(body)
        if r.unknown:
            unknown.extend(r.unknown)
            kept.append(m.group(0))
            return "@@KEEP%d@@" % (len(kept) - 1)
        return " " + r.words + " "
    kept: List[str] = []
    out = _SPAN.sub(repl, text)
    # stray macros outside any $...$ (the model sometimes drops the dollar signs)
    def repl_stray(m: re.Match) -> str:
        name = m.group(1)
        if name in MACRO_GREEK or name in MACRO_WORDS:
            return " " + (MACRO_GREEK.get(name) or MACRO_WORDS[name]) + " "
        unknown.append("\\" + name)
        return m.group(0)
    out = _STRAY.sub(repl_stray, out)
    for i, original in enumerate(kept):  # spans with unknown notation stay exactly as written
        out = out.replace("@@KEEP%d@@" % i, original)
    if re.search(r"\$[^\s$]", out):  # a dollar sign opening math that never closed, or that broke across lines
        unknown.append("unclosed or malformed math ($ ...)")
    out = re.sub(r"[ \t]{2,}", " ", out)
    out = re.sub(r" +([.,;:!?])", r"\1", out)
    return out, sorted(set(unknown))


def find_unspeakable(text: str) -> List[str]:
    """Notation in ``text`` that speak_text cannot convert (empty list = the text can be spoken)."""
    return speak_text(text)[1]


class UnspeakableNotationError(Exception):
    """The script or description still contains notation that cannot be read aloud after the allowed regenerations."""

    def __init__(self, problems):
        self.problems = list(problems)
        super().__init__(
            "The generated script or description kept using mathematical notation that cannot be read aloud (" +
            "; ".join(self.problems[:6]) + ("; ..." if len(self.problems) > 6 else "") +
            "), and regeneration did not remove it, so no episode was published.")


def notation_problems(script: str, description: str) -> List[str]:
    """Unknown notation in the spoken script and in the description body (the reference sections are built by code later)."""
    body = re.split(r"(?im)^#{1,3}\s*(?:references|further reading)\s*$", description or "")[0]
    return sorted(set(find_unspeakable(script) + find_unspeakable(body)))


def notation_feedback(problems) -> str:
    return ("\n\n**YOUR PREVIOUS SCRIPT OR DESCRIPTION WAS REJECTED because it contains mathematical notation that cannot be read aloud: "
            + "; ".join(problems) +
            "**\nWrite every symbol, formula and particle or chemical notation as plain words (for example \"K short\", \"pi plus\", "
            "\"D sub s plus\", \"x squared\"). Do not use LaTeX, dollar signs or backslashes anywhere.\n")


def has_math(text: str) -> bool:
    return bool(text) and (bool(_SPAN.search(text)) or bool(_STRAY.search(text)))


# ---------------------------------------------------------------------------------------------- display (registry titles)
_SUP = str.maketrans("0123456789+-=()ni", "⁰¹²³⁴⁵⁶⁷⁸⁹⁺⁻⁼⁽⁾ⁿⁱ")
_SUB = str.maketrans("0123456789+-=()aehijklmnoprstuvx", "₀₁₂₃₄₅₆₇₈₉₊₋₌₍₎ₐₑₕᵢⱼₖₗₘₙₒₚᵣₛₜᵤᵥₓ")
_DISPLAY_MACROS = {"to": "→", "rightarrow": "→", "longrightarrow": "⟶", "leftarrow": "←", "leftrightarrow": "↔", "Rightarrow": "⇒", "pm": "±", "mp": "∓",
                   "times": "×", "cdot": "·", "approx": "≈", "sim": "∼", "leq": "≤", "le": "≤", "geq": "≥", "ge": "≥", "neq": "≠", "ne": "≠", "infty": "∞",
                   "ldots": "…", "dots": "…", "cdots": "⋯", "degree": "°", "circ": "°", "partial": "∂", "nabla": "∇", "hbar": "ħ", "ell": "ℓ", "prime": "′"}
_GREEK_CHAR = {**{n: c for n, c in zip(GREEK_NAMES, _GREEK_LOWER.replace("ς", ""))}, **{n: c for n, c in zip(_GREEK_UPPER_NAMES, _GREEK_UPPER)},
               "varepsilon": "ε", "vartheta": "ϑ", "varphi": "φ", "varrho": "ϱ", "varsigma": "ς", "varpi": "ϖ"}


def _display_expr(expr: str) -> str:
    expr = re.sub(r"\\\\(?=[A-Za-z])", r"\\", expr)
    expr = re.sub(r"\\(?:mathrm|text|textrm|mathit|mathbf|textbf|mathsf|mathcal|mathbb|operatorname|mbox)\s*\{([^{}]*)\}", r"\1", expr)
    expr = re.sub(r"\\(?:bar|overline)\s*\{([^{}]*)\}", lambda m: m.group(1) + "̄", expr)
    expr = re.sub(r"\\bar\s*([A-Za-z])", lambda m: m.group(1) + "̄", expr)
    expr = re.sub(r"\\(?:hat)\s*\{([^{}]*)\}", lambda m: m.group(1) + "̂", expr)
    expr = re.sub(r"\\(?:tilde)\s*\{([^{}]*)\}", lambda m: m.group(1) + "̃", expr)

    def macro(m: re.Match) -> str:
        n = m.group(1)
        return _GREEK_CHAR.get(n) or _DISPLAY_MACROS.get(n) or ""   # unknown macro: drop the command, keep what follows
    expr = re.sub(r"\\([A-Za-z]+)", macro, expr)

    def sup(m: re.Match) -> str:
        inner = (m.group(1) or m.group(2) or "")
        return inner.translate(_SUP) if all(ch in "0123456789+-=()ni" for ch in inner) else "^" + inner

    def sub(m: re.Match) -> str:
        inner = (m.group(1) or m.group(2) or "")
        return inner.translate(_SUB) if all(ch in "0123456789+-=()aehijklmnoprstuvx" for ch in inner) else "_" + inner
    expr = re.sub(r"\^\{([^{}]*)\}|\^(.)", sup, expr)
    expr = re.sub(r"_\{([^{}]*)\}|_(.)", sub, expr)
    return expr.replace("{", "").replace("}", "").replace("\\", "")


def latex_display(text: str) -> str:
    """Readable (Unicode) form of a title or line that contains LaTeX; for display only."""
    if not text or ("$" not in text and "\\" not in text):
        return text
    out = _SPAN.sub(lambda m: _display_expr(next(g for g in m.groups() if g is not None)), text)
    out = re.sub(r"\\\\?([A-Za-z]+)", lambda m: _GREEK_CHAR.get(m.group(1)) or _DISPLAY_MACROS.get(m.group(1)) or "", out)
    return re.sub(r"\s{2,}", " ", out)
