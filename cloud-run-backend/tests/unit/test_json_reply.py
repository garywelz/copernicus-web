"""Model replies wrapped in a code fence must parse; replies that are not JSON (or cut off) must still fail."""
import json
import sys
from unittest.mock import MagicMock

import pytest

try:
    import psutil  # noqa: F401
except ImportError:
    sys.modules["psutil"] = MagicMock()

from json_reply import parse_json_reply

FENCE = chr(96) * 3


def test_plain_json():
    assert parse_json_reply('{"a": 1}') == {"a": 1}


def test_fenced_json_with_and_without_language():
    assert parse_json_reply(FENCE + 'json\n{"a": [1, 2]}\n' + FENCE) == {"a": [1, 2]}
    assert parse_json_reply("  " + FENCE + '\n{"a": 1}\n' + FENCE + "  \n") == {"a": 1}


def test_prose_around_the_object():
    assert parse_json_reply('Here is the analysis:\n{"a": "x"}\nHope this helps.') == {"a": "x"}


@pytest.mark.parametrize("bad", ["", "no json here", FENCE + 'json\n{"a": "cut off mid-str', '{"a": 1', "[1, 2"])
def test_text_that_is_not_complete_json_still_raises(bad):
    with pytest.raises(json.JSONDecodeError):
        parse_json_reply(bad)


def test_the_analysis_callers_use_it_and_thinking_is_off():
    import inspect
    import enhanced_research_service as ers
    import paper_processor
    assert "parse_json_reply(response)" in inspect.getsource(ers.EnhancedResearchService._analyze_single_paper)
    assert "parse_json_reply(response.text)" in inspect.getsource(paper_processor.analyze_paper_with_gemini)
    assert '"thinkingBudget": 0' in inspect.getsource(ers.EnhancedResearchService._call_google_ai)
