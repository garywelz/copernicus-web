"""Read a JSON object from a model's reply. Gemini often wraps JSON in a Markdown code fence (```json ... ```) or adds a line of
prose around it; json.loads on the raw text then fails even though the answer is fine. A reply that is genuinely not JSON
(or was cut off) still raises, so callers keep their failure handling."""
import json
import re

_FENCE = re.compile(r"^\s*```[a-zA-Z0-9_-]*\s*\n?(.*?)\n?```\s*$", re.DOTALL)


def parse_json_reply(text: str):
    t = (text or "").strip()
    m = _FENCE.match(t)
    if m:
        t = m.group(1).strip()
    try:
        return json.loads(t)
    except json.JSONDecodeError:
        start, end = t.find("{"), t.rfind("}")
        if start != -1 and end > start:
            return json.loads(t[start:end + 1])  # raises if the object is still not valid JSON
        raise
