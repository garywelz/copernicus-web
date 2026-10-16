"""The script generator's call to Gemini (fix 6).

Until now the live path called ``genai.GenerativeModel(...).generate_content(prompt)`` with no generation config at all (the 0.8 temperature
and 16,384-token limit written elsewhere in the service belong to the Vertex branch, which is disabled): the model's default temperature, an
output limit it chooses, dynamic thinking of up to about 15,000 hidden tokens, and a reply that was free text which sometimes stopped after
the script (no description) or inside an unterminated string. This module makes the call explicitly:

- temperature 0.8 and top_p 0.95, as the other branches of the service intend;
- JSON mode with a schema that requires title, script, description and keywords, so a reply is valid JSON that has every field;
- maxOutputTokens 16,384 (a normal reply is 1,500 to 5,000 tokens) and a thinking budget of 4,096 tokens, set the way the paper-analysis
  calls set theirs (REST thinkingConfig; the older SDK has no field for it). A reply that does not end with STOP is an error.

Nothing here knows about podcasts; a failure raises ModelReplyError, which the caller treats as a model error (retried without using a
content attempt).
"""
from __future__ import annotations

import json
from typing import Any, Dict

import requests

GENERATOR_MODEL = "gemini-2.5-flash"
FALLBACK_MODEL = "gemini-2.5-pro"
TEMPERATURE = 0.8
TOP_P = 0.95
MAX_OUTPUT_TOKENS = 16384
THINKING_BUDGET = 4096
REQUIRED_KEYS = ("title", "script", "description", "keywords")
SCHEMA: Dict[str, Any] = {
    "type": "OBJECT",
    "properties": {
        "title": {"type": "STRING"},
        "script": {"type": "STRING"},
        "description": {"type": "STRING"},
        "keywords": {"type": "ARRAY", "items": {"type": "STRING"}},
    },
    "required": list(REQUIRED_KEYS),
}


class ModelReplyError(Exception):
    """The model did not give a usable reply (HTTP error, blocked, cut off, not JSON, a field missing)."""


def generation_config() -> Dict[str, Any]:
    return {
        "temperature": TEMPERATURE,
        "topP": TOP_P,
        "maxOutputTokens": MAX_OUTPUT_TOKENS,
        "responseMimeType": "application/json",
        "responseSchema": SCHEMA,
        "thinkingConfig": {"thinkingBudget": THINKING_BUDGET},
    }


def build_request(prompt: str) -> Dict[str, Any]:
    return {"contents": [{"parts": [{"text": prompt}]}], "generationConfig": generation_config()}


def parse_reply(payload: Dict[str, Any]) -> str:
    """The JSON text of a successful reply, or ModelReplyError."""
    cands = payload.get("candidates") or []
    if not cands:
        raise ModelReplyError("no candidate in the reply" + (f" (blocked: {payload['promptFeedback']})" if payload.get("promptFeedback") else ""))
    cand = cands[0]
    finish = cand.get("finishReason")
    if finish not in (None, "STOP"):
        raise ModelReplyError(f"the reply ended with {finish}, not STOP")
    parts = ((cand.get("content") or {}).get("parts")) or []
    text = "".join(p.get("text", "") for p in parts if not p.get("thought"))
    if not text.strip():
        raise ModelReplyError("the reply has no text")
    try:
        data = json.loads(text)
    except json.JSONDecodeError as e:
        raise ModelReplyError(f"the reply is not valid JSON: {e}")
    if not isinstance(data, dict):
        raise ModelReplyError("the reply is not a JSON object")
    missing = [k for k in ("title", "script", "description") if not str(data.get(k) or "").strip()] + [k for k in ("keywords",) if k not in data]
    if missing:
        raise ModelReplyError("the reply lacks " + ", ".join(missing))
    return text


def generate_json_reply(prompt: str, api_key: str, model: str = GENERATOR_MODEL, timeout: int = 300, post=requests.post) -> str:
    """One generateContent call (blocking). Returns the reply's JSON text or raises ModelReplyError."""
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
    try:
        r = post(url, headers={"x-goog-api-key": api_key, "Content-Type": "application/json"}, json=build_request(prompt), timeout=timeout)
    except requests.RequestException as e:
        raise ModelReplyError(f"{type(e).__name__}: {e}")
    if r.status_code != 200:
        raise ModelReplyError(f"{model} answered HTTP {r.status_code}: {r.text[:200]}")
    try:
        payload = r.json()
    except ValueError:
        raise ModelReplyError("the reply is not JSON")
    return parse_reply(payload)
