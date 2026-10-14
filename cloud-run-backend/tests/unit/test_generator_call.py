"""The script generator's call to Gemini and what counts as a broken reply (fix 6). Offline."""
import asyncio
import json
import sys
from types import SimpleNamespace as NS
from unittest.mock import MagicMock

import pytest
import requests

try:
    import psutil  # noqa: F401
except ImportError:
    sys.modules["psutil"] = MagicMock()

import gemini_generate as gg
from utils.script_validation import check_model_reply, MalformedModelReply, MALFORMED_BELOW_FRACTION


def run(coro):
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


GOOD = {"title": "T", "script": "MATILDA: Hello.", "description": "About it.", "keywords": ["a"]}


def payload(text=None, finish="STOP", parts=None):
    return {"candidates": [{"finishReason": finish, "content": {"parts": parts if parts is not None else [{"text": text if text is not None else json.dumps(GOOD)}]}}]}


# ---------------------------------------------------------------- the request
def test_the_call_sets_temperature_limit_thinking_and_a_schema_that_requires_every_field():
    cfg = gg.build_request("PROMPT")["generationConfig"]
    assert cfg["temperature"] == 0.8 and cfg["topP"] == 0.95 and cfg["maxOutputTokens"] == 16384
    assert cfg["thinkingConfig"] == {"thinkingBudget": 4096} and cfg["responseMimeType"] == "application/json"
    assert cfg["responseSchema"]["required"] == ["title", "script", "description", "keywords"]
    assert gg.build_request("PROMPT")["contents"][0]["parts"][0]["text"] == "PROMPT"


def test_the_key_goes_in_a_header_not_in_the_url():
    seen = {}

    def post(url, headers, json, timeout):
        seen.update(url=url, headers=headers, timeout=timeout)
        return NS(status_code=200, json=lambda: payload(), text="")
    assert json.loads(gg.generate_json_reply("p", "SECRET", "gemini-2.5-flash", post=post)) == GOOD
    assert seen["url"].endswith("/models/gemini-2.5-flash:generateContent") and "SECRET" not in seen["url"] and seen["headers"]["x-goog-api-key"] == "SECRET"


# ---------------------------------------------------------------- what is a usable reply
def test_a_good_reply_is_returned_as_its_json_text_and_thought_parts_are_ignored():
    assert json.loads(gg.parse_reply(payload())) == GOOD
    text = gg.parse_reply(payload(parts=[{"text": "thinking...", "thought": True}, {"text": json.dumps(GOOD)}]))
    assert json.loads(text) == GOOD


@pytest.mark.parametrize("bad,why", [
    (payload(finish="MAX_TOKENS"), "MAX_TOKENS"),
    (payload(finish="SAFETY"), "SAFETY"),
    ({"candidates": [], "promptFeedback": {"blockReason": "OTHER"}}, "blocked"),
    ({}, "no candidate"),
    (payload(parts=[]), "no text"),
    (payload(text="   "), "no text"),
    (payload(text="I could not do that."), "not valid JSON"),
    (payload(text='{"title": "T", "script": "MATILDA: unfinished'), "not valid JSON"),
    (payload(text="[1, 2]"), "not a JSON object"),
    (payload(text=json.dumps({"title": "T", "script": "S", "keywords": []})), "description"),
    (payload(text=json.dumps({"title": "T", "script": "", "description": "D", "keywords": []})), "script"),
    (payload(text=json.dumps({"title": "T", "script": "S", "description": "D"})), "keywords"),
])
def test_every_kind_of_broken_reply_is_a_model_reply_error(bad, why):
    with pytest.raises(gg.ModelReplyError) as e:
        gg.parse_reply(bad)
    assert why.lower() in str(e.value).lower()


def test_http_errors_and_network_errors_are_model_reply_errors():
    with pytest.raises(gg.ModelReplyError, match="HTTP 503"):
        gg.generate_json_reply("p", "k", post=lambda *a, **k: NS(status_code=503, json=lambda: {}, text="overloaded"))

    def boom(*a, **k):
        raise requests.ConnectionError("dns")
    with pytest.raises(gg.ModelReplyError, match="ConnectionError"):
        gg.generate_json_reply("p", "k", post=boom)

    def not_json():
        raise ValueError("no")
    with pytest.raises(gg.ModelReplyError, match="not JSON"):
        gg.generate_json_reply("p", "k", post=lambda *a, **k: NS(status_code=200, json=not_json, text="x"))


# ---------------------------------------------------------------- a broken reply is not a short script
def test_check_model_reply():
    ok = {"script": "word " * 200, "description": "D"}
    check_model_reply(ok, 600)                                                 # 200 words of 600 is short, but it is a script
    with pytest.raises(MalformedModelReply, match="no description"):
        check_model_reply({"script": "word " * 900, "description": "  "}, 600)
    with pytest.raises(MalformedModelReply, match="quarter"):
        check_model_reply({"script": "word " * 144, "description": "D"}, 600)   # the 2026-10-14 reply
    with pytest.raises(MalformedModelReply):
        check_model_reply({"script": "word " * 23, "description": "D"}, 600)    # and the next one
    with pytest.raises(MalformedModelReply):
        check_model_reply("a string", 600)
    check_model_reply({"script": "word " * 150, "description": "D"}, 600)       # exactly a quarter: still a content failure
    assert MALFORMED_BELOW_FRACTION == 0.25


# ---------------------------------------------------------------- in the service
import services.podcast_generation_service as svc  # noqa: E402
from tests.unit import test_fix1_service_wiring as wiring  # noqa: E402
from models.podcast import PodcastRequest  # noqa: E402


def generator_service(monkeypatch, replies):
    """The live branch of generate_content_from_research_context with the Gemini call replaced by the given replies (JSON text or errors)."""
    service = svc.PodcastGenerationService()
    service.vertex_ai_model = None
    calls = []

    def fake(prompt, key, model="gemini-2.5-flash", **k):
        calls.append((model, key))
        r = replies[min(len(calls) - 1, len(replies) - 1)]
        if isinstance(r, Exception):
            raise r
        return r
    monkeypatch.setattr(gg, "generate_json_reply", fake)
    return service, calls


def test_the_live_branch_uses_the_explicit_call_and_falls_back_to_the_other_model(monkeypatch):
    service, calls = generator_service(monkeypatch, [gg.ModelReplyError("flash broke"), json.dumps(GOOD)])
    out = run(service.generate_content_from_research_context(PodcastRequest(topic="t"), wiring._ctx(), "THE-KEY"))
    assert out["script"] == GOOD["script"] and calls == [("gemini-2.5-flash", "THE-KEY"), ("gemini-2.5-pro", "THE-KEY")]


def test_if_both_models_fail_the_last_error_is_raised(monkeypatch):
    service, calls = generator_service(monkeypatch, [gg.ModelReplyError("flash broke"), gg.ModelReplyError("pro broke")])
    with pytest.raises(gg.ModelReplyError, match="pro broke"):
        run(service.generate_content_from_research_context(PodcastRequest(topic="t"), wiring._ctx(), "k"))


def test_the_service_no_longer_calls_the_sdk_without_a_config():
    import inspect
    src = inspect.getsource(svc.PodcastGenerationService.generate_content_from_research_context)
    assert "model.generate_content(prompt)" not in src and "generate_json_reply" in src


def test_a_reply_without_a_description_or_with_a_tiny_script_does_not_use_a_content_attempt(monkeypatch):
    req = PodcastRequest(topic="t")
    good = wiring._script(" Lovelace and Turing showed it.", req)
    service, req, calls = wiring._harness(monkeypatch, [good])
    state = {"n": 0}

    async def fake_generate(r, ctx, key, retry_attempt=0, naming_feedback=""):
        state["n"] += 1
        calls["feedback"].append(naming_feedback)
        if state["n"] == 1:
            return {"title": "T", "script": good}                                  # stopped after the script
        if state["n"] == 2:
            return {"title": "T", "script": "word " * 23, "description": "D"}       # a 23-word "script"
        return {"title": "T", "script": good, "description": "Body."}
    monkeypatch.setattr(service, "generate_content_from_research_context", fake_generate)
    content, result, attempts = run(service._generate_checked_content(req, wiring._ctx(), "k", "job1"))
    assert state["n"] == 3 and content["script"] == good and len(attempts) == 1       # only one content attempt was used
    kinds = [(r["check"], r["error_type"]) for r in service._last_rejections if r["check"] == "transient_error"]
    assert kinds == [("transient_error", "MalformedModelReply")] * 2
    assert calls["feedback"] == ["", "", ""]


def test_a_merely_short_script_is_still_a_content_failure(monkeypatch):
    req = PodcastRequest(topic="t")
    short = "word " * 400
    service, req, calls = wiring._harness(monkeypatch, [short, wiring._script(" Lovelace and Turing showed it.", req)])
    run(service._generate_checked_content(req, wiring._ctx(), "k", "job1"))
    assert [r["check"] for r in service._last_rejections][:1] == ["too_short"] and "too short" in calls["feedback"][1]
