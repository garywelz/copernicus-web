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


BS = chr(92)


def test_latex_backslashes_inside_json_strings_are_kept_as_text():
    raw = '{"summary": "The ' + BS + 'alpha parameter and ' + BS + 'beta decay of ' + BS + 'nu_e with ' + BS + 'frac{1}{2} spin", "n": 1}'
    got = parse_json_reply(FENCE + "json\n" + raw + "\n" + FENCE)
    assert got["n"] == 1 and BS + "alpha" in got["summary"] and BS + "beta" in got["summary"] and BS + "frac" in got["summary"]


def test_a_lone_backslash_before_a_symbol_is_repaired():
    got = parse_json_reply('{"a": "cost is 5 ' + BS + '% of ' + BS + '(x' + BS + ')"}')
    assert BS + "%" in got["a"]


def test_valid_escapes_are_untouched():
    assert parse_json_reply('{"a": "line1' + BS + 'nline2 ' + BS + '"q' + BS + '" ' + BS + BS + ' ok"}')["a"] == "line1\nline2 \"q\" " + BS + " ok"


def test_repair_does_not_turn_truncated_json_into_success():
    with pytest.raises(json.JSONDecodeError):
        parse_json_reply('{"a": "' + BS + 'alpha cut off')


def test_the_reply_that_failed_in_the_2026_10_13_verification_run():
    """Already-doubled LaTeX backslashes next to a lone '\!' (from 'C\!P'): the pair must be left alone, the lone one fixed."""
    raw = ('{"s": "decays of $' + BS + BS + 'bar{D}^0$ and $K^0_{S/L}$ and $' + BS + BS + 'pi^+' + BS + BS + 'pi^-$ violate $C' + BS + '!P$ and '
           '$' + BS + BS + 'to$ also ' + BS + 'alpha", "n": 2}')
    got = parse_json_reply(FENCE + "json\n" + raw + "\n" + FENCE)
    assert got["n"] == 2
    assert BS + "bar{D}" in got["s"] and BS + "pi^+" in got["s"] and BS + "to" in got["s"]   # doubled pairs read back as one backslash
    assert "C" + BS + "!P" in got["s"] and BS + "alpha" in got["s"]                          # lone ones kept as text
    assert "\b" not in got["s"]                                                              # no backspace made from '\bar'
