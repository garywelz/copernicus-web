"""Read a JSON object or array from a model's reply. Gemini often wraps JSON in a Markdown code fence (```json ... ```) or adds a line of
prose around it; json.loads on the raw text then fails even though the answer is fine. A reply that is genuinely not JSON
(or was cut off) still raises, so callers keep their failure handling."""
import json
import re

_FENCE = re.compile(r"^\s*```[a-zA-Z0-9_-]*\s*\n?(.*?)\n?```\s*$", re.DOTALL)
# A backslash that does not begin a valid JSON escape, or that begins a LaTeX word such as \alpha, \beta or \nu (LaTeX from an
# abstract copied into a JSON string). Doubled, it reads back as the literal text. Only tried when plain parsing has failed.
_BACKSLASH = re.compile(r'\\\\|\\(?!["/]|u[0-9a-fA-F]{4})(?=[A-Za-z]{2,}|[^bfnrtu"\\/])')  # a pair is matched first, so it is left alone


def parse_json_reply(text: str):
    t = (text or "").strip()
    m = _FENCE.match(t)
    if m:
        t = m.group(1).strip()
    try:
        return json.loads(t)
    except json.JSONDecodeError:
        pass
    # the outermost object or array, whichever opens first (prose may surround it)
    opens = [(t.find(o), o, c) for o, c in (("{", "}"), ("[", "]")) if t.find(o) != -1]
    start, o, c = min(opens) if opens else (-1, "", "")
    end = t.rfind(c) if c else -1
    body = t[start:end + 1] if start != -1 and end > start else t
    try:
        return json.loads(body)
    except json.JSONDecodeError:
        fixed = _BACKSLASH.sub(lambda m: m.group(0) if len(m.group(0)) == 2 else "\\\\", body)
        return json.loads(fixed)  # raises if the object is still not valid JSON
