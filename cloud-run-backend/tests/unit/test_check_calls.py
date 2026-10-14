"""The model calls behind the naming check, the attribution check and the focused-query writer (fix 8). Offline."""
import asyncio
import json
import sys
from types import SimpleNamespace as NS
from unittest.mock import MagicMock

import pytest

try:
    import psutil  # noqa: F401
except ImportError:
    sys.modules["psutil"] = MagicMock()

import named_work_check as nw
import rejection_log


def run(coro):
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


def test_the_request_is_deterministic_json_with_thinking_off():
    body = nw.check_request("SYS", "USER")
    cfg = body["generationConfig"]
    assert body["systemInstruction"]["parts"][0]["text"] == "SYS" and body["contents"][0]["parts"][0]["text"] == "USER"
    assert cfg == {"temperature": 0, "maxOutputTokens": 8192, "responseMimeType": "application/json", "thinkingConfig": {"thinkingBudget": 0}}


def test_reply_text_and_the_replies_that_are_errors():
    ok = {"candidates": [{"finishReason": "STOP", "content": {"parts": [{"text": '{"mentions": []}'}]}}]}
    assert nw.check_reply_text(ok) == '{"mentions": []}'
    assert nw.check_reply_text({"candidates": [{"content": {"parts": [{"text": "a"}, {"text": "b", "thought": True}, {"text": "c"}]}}]}) == "ac"
    for bad in ({"candidates": [{"finishReason": "MAX_TOKENS", "content": {"parts": [{"text": '{"men'}]}}]}, {"candidates": []}, {},
                {"candidates": [{"finishReason": "SAFETY"}]}):
        with pytest.raises(RuntimeError):
            nw.check_reply_text(bad)


def test_the_wrapper_posts_the_request_with_the_key_in_a_header_and_returns_the_text():
    seen = {}

    def post(url, headers, json, timeout):
        seen.update(url=url, headers=headers, body=json, timeout=timeout)
        return NS(status_code=200, json=lambda: {"candidates": [{"finishReason": "STOP", "content": {"parts": [{"text": "{}"}]}}]}, text="")
    call = nw.make_gemini_llm_call("SECRET", post=post)
    assert run(call("S", "U")) == "{}"
    assert seen["url"].endswith("/models/gemini-2.5-flash:generateContent") and "SECRET" not in seen["url"]
    assert seen["headers"]["x-goog-api-key"] == "SECRET" and seen["body"] == nw.check_request("S", "U")


def test_an_http_error_is_an_error_the_check_turns_into_check_unavailable():
    call = nw.make_gemini_llm_call("k", post=lambda *a, **k: NS(status_code=429, json=lambda: {}, text="quota"))
    with pytest.raises(RuntimeError, match="HTTP 429"):
        run(call("S", "U"))
    llm = nw.make_gemini_llm_call("k", post=lambda *a, **k: NS(status_code=500, json=lambda: {}, text="oops"))
    with pytest.raises(nw.NamingCheckUnavailable):
        run(nw._extract(llm, "script", "text"))


def test_transient_records_carry_what_the_model_answered_when_it_could_not_be_read():
    item = rejection_log.transient_item(1, "naming_check", nw.NamingCheckUnavailable("unparseable", raw='{"mentions": [{"quote": "cut o'))
    assert item["raw_head"] == '{"mentions": [{"quote": "cut o' and item["error_type"] == "NamingCheckUnavailable"
    assert "raw_head" not in rejection_log.transient_item(1, "generation", ValueError("x"))


def test_identical_records_stay_distinct_on_the_job(monkeypatch):
    from tests.unit import test_fix1_service_wiring as wiring
    from models.podcast import PodcastRequest
    req = PodcastRequest(topic="t")
    good = wiring._script(" Lovelace and Turing showed it.", req)
    service, req, calls = wiring._harness(monkeypatch, [ValueError("x"), ValueError("x"), good])
    stored = []
    run(service._generate_checked_content(req, wiring._ctx(), "k", "job1", on_rejection=stored.extend))
    seqs = [r["seq"] for r in stored]
    transient = [r for r in stored if r["check"] == "transient_error"]
    assert len(transient) == 2 and transient[0]["error"] == transient[1]["error"]      # identical records ...
    assert len(set(seqs)) == len(seqs)                                                   # ... that stay distinct for Firestore's ArrayUnion
