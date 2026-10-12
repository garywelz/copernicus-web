"""Mathematical notation must be spoken as words, and notation the table cannot convert must trigger regeneration (gap 3 fix 1)."""
import asyncio
import json
import sys
from unittest.mock import MagicMock

import pytest

try:
    import psutil  # noqa: F401
except ImportError:
    sys.modules["psutil"] = MagicMock()

import paper_confirmation as pc
from speech_text import (UnspeakableNotationError, find_unspeakable, latex_display, notation_feedback, notation_problems, speak_text)

BS = chr(92)  # a real backslash
TAB = chr(9)


def say(latex):
    return speak_text("$" + latex + "$")[0].strip()


# ---------------------------------------------------------------- conversion
def test_the_requested_example():
    assert say("D_s^+ " + BS + "to K_S^0 K_L^0 " + BS + "pi^+") == "D sub s plus to K short K long pi plus"


@pytest.mark.parametrize("latex,words", [
    ("K_S^0", "K short"), ("K_L^0", "K long"), ("K^0", "K zero"), ("D^0", "D zero"), ("e^+e^-", "e plus e minus"),
    (BS + "pi^{+}" + BS + "pi^{-}", "pi plus pi minus"), (BS + "mu^+" + BS + "mu^-", "mu plus mu minus"),
    (BS + "Lambda_c^+", "Lambda sub c plus"), (BS + "bar{D}^0", "D zero bar"),
    ("K_{" + BS + "mathrm{S(L)}}^{0}", "K short or long"), ("pK_{L,S}^0", "p K long or short"),
    ("E = mc^2", "E equals m c squared"), ("10^{-3}", "10 to the minus 3"), ("x_1 + x_2", "x sub 1 plus x sub 2"),
    (BS + "alpha " + BS + "approx 0.5", "alpha approximately 0.5"), ("a " + BS + "leq b", "a less than or equal to b"),
    (BS + "frac{1}{2}", "1 over 2"), (BS + "sqrt{x}", "square root of x"), ("Λ_c^+", "Lambda sub c plus"),
])
def test_common_notation_becomes_words(latex, words):
    assert say(latex) == words


def test_doubled_backslashes_and_json_corrupted_escapes_are_repaired():
    assert say("D^{+} " + BS + BS + "rightarrow K_{S}^{0}" + BS + BS + "pi^{+}") == "D plus to K short pi plus"
    assert say("D^0 " + BS + TAB + "o K_{L}^{0}" + BS + BS + "omega") == "D zero to K long omega"
    assert say("D^0 " + TAB + "o K_{L}^{0}") == "D zero to K long"


def test_a_sentence_keeps_its_prose():
    out, unknown = speak_text("The decay $D_s^+ " + BS + "to K_S^0 K_L^0 " + BS + "pi^+$ was measured, and $K_S^0$ is short-lived.")
    assert out == "The decay D sub s plus to K short K long pi plus was measured, and K short is short-lived." and unknown == []


def test_text_without_math_is_untouched():
    assert speak_text("plain words, no markup") == ("plain words, no markup", [])


# ---------------------------------------------------------------- unknown notation is reported, never dropped
@pytest.mark.parametrize("latex,marker", [(BS + "oint F " + BS + "cdot dl", "oint"), (BS + "mathfrak{g}", "mathfrak"), (BS + "weirdmacro x", "weirdmacro")])
def test_unknown_notation_is_reported_and_the_span_is_left_as_written(latex, marker):
    out, unknown = speak_text("so $" + latex + "$ holds")
    assert any(marker in u for u in unknown) and ("$" + latex + "$") in out


def test_a_stray_macro_outside_dollars_and_an_unclosed_dollar_are_reported():
    assert find_unspeakable("a " + BS + "weird macro") == [BS + "weird"]
    assert find_unspeakable("broken $D_s^+ " + BS + "to K\nnext line") != []


def test_notation_problems_look_at_the_script_and_the_description_body_only():
    desc = "Body with $K_S^0$.\n\n## References\n\n- Study of $" + BS + "mathfrak{g}$ decays.\n"
    assert notation_problems("ADAM: plain.", desc) == []
    assert notation_problems("ADAM: $" + BS + "mathfrak{g}$", "") != []


def test_feedback_names_the_problem_and_the_rule():
    fb = notation_feedback([BS + "oint"])
    assert BS + "oint" in fb and "plain words" in fb and "K short" in fb


def test_error_message_is_clear():
    msg = str(UnspeakableNotationError([BS + "oint"]))
    assert "cannot be read aloud" in msg and "no episode was published" in msg


# ---------------------------------------------------------------- spans from the real maths scripts
def test_every_notation_span_in_the_real_math_scripts_converts():
    spans = [
        "$K_{" + BS + "mathrm{S(L)}}^{0} " + BS + "rightarrow " + BS + BS + "pi^{+}" + BS + "pi^{-}" + BS + "mu^{+}" + BS + "mu^{-}$",
        "$D^{+} " + BS + BS + "rightarrow K_{S}^{0}K_{L}^{0}" + BS + BS + "pi^{+}$",
        "$D_{s}^{+} " + BS + TAB + "o K_{S}^{0}K_{L}^{0}" + BS + BS + "pi^{+}$", "$K_S^0$", "$K_L^0$", "$Λ_c^+$",
        "$Λ_c^+ " + BS + TAB + "o pK_{L,S}^0$", "$D^0 " + BS + TAB + "o K_{S}^{0}" + BS + BS + "omega$",
        "$" + BS + "bar{D}^0 " + BS + "to K^{0}_{S/L}" + BS + "pi^+" + BS + "pi^-$",
    ]
    for sp in spans:
        out, unknown = speak_text(sp)
        assert unknown == [] and "$" not in out and BS not in out, (sp, out, unknown)


# ---------------------------------------------------------------- display of registry titles
def test_titles_are_made_readable_for_display_only():
    assert latex_display("Study of $" + BS + "phi" + BS + "to K" + BS + "bar{K}$") == "Study of φ→ KK̄"
    assert latex_display("Search for $K^{0}_{S}" + BS + "rightarrow " + BS + "pi^{+}" + BS + "pi^{-}$ decays").endswith("π⁺π⁻ decays")
    assert latex_display("A plain title") == "A plain title"


def test_reference_lines_use_the_readable_title_but_the_stored_title_is_unchanged():
    title = "Study of $" + BS + "phi" + BS + "to K" + BS + "bar{K}$"
    c = pc.ConfirmedPaper(pid="P1", title=title, authors=["A B"], year=2025, venue=None,
                          ids={"arxiv": "2601.00001", "arxiv_version": "v1", "pmid": None, "doi": None},
                          url="https://arxiv.org/abs/2601.00001v1", abstract="a", registry="arxiv", confirmed_at="t", title_match=1.0)
    line = pc.format_citation_line(c)
    assert "φ→" in line and "$" not in line and BS not in line and c.title == title


# ---------------------------------------------------------------- the speech safety net and the failure notice
def test_speech_preprocessing_speaks_leftover_notation_and_strips_markup_it_cannot_convert():
    from elevenlabs_voice_service import ElevenLabsVoiceService
    f = ElevenLabsVoiceService._preprocess_text_for_natural_speech
    assert "D sub s plus to K short" in f(None, "The $D_s^+ " + BS + "to K_S^0$ decay.")
    out = f(None, "An odd $" + BS + "oint F$ term")
    assert "$" not in out and BS not in out


def test_failure_notice_for_unspeakable_notation():
    from failure_notice import describe_failure
    n = describe_failure(UnspeakableNotationError([BS + "oint"]))
    assert n["kind"] == "unspeakable_notation" and "oint" not in n["summary"] and n["what_to_do"]
