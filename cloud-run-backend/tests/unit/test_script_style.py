"""Banned-phrase check (fix 4, stage a): deterministic, case-insensitive, one config file. Offline."""
import json

import pytest

import script_style as ss

# Sentences from the ever-math-260008 script (2026-10-13) that Gary rejected for hype.
EP8 = [
    "MATILDA: Welcome to Copernicus AI: Frontiers of Science. I'm Matilda, and today we're exploring a truly revolutionary development: Proof dependency graphs in formal mathematics libraries.",
    "MATILDA: So, we're talking about a profound paradigm shift in how we conceive of mathematical truth and proof, moving from human consensus to machine verification?",
    "ADAM: It fundamentally challenges the millennia-old paradigm of human-centric mathematical verification. This introduces an unprecedented level of certainty and reproducibility to mathematics itself.",
    "MATILDA: Thank you, Adam, for breaking down this truly revolutionary research.",
]
SCRIPT = "\n\n".join(EP8)


def test_the_config_holds_gary_s_six_examples_and_is_the_only_list():
    phrases = ss.load_banned_phrases()
    for p in ("revolutionary", "groundbreaking", "unprecedented", "paradigm shift", "absolute certainty", "millennia-old"):
        assert p in phrases
    from pathlib import Path
    src = Path(ss.__file__).read_text(encoding="utf-8")
    assert '"unprecedented"' not in src and '"groundbreaking"' not in src       # the list is not copied into the code


def test_an_empty_or_missing_list_is_an_error_not_a_silent_pass(tmp_path):
    f = tmp_path / "b.json"
    f.write_text(json.dumps({"banned_phrases": []}), encoding="utf-8")
    with pytest.raises(ValueError):
        ss.load_banned_phrases(f)
    with pytest.raises(FileNotFoundError):
        ss.load_banned_phrases(tmp_path / "nope.json")


def test_the_ep8_script_is_caught_five_times():
    hits = ss.banned_phrase_hits(SCRIPT)
    assert sorted((h["phrase"], h["matched"]) for h in hits) == sorted([
        ("revolutionary", "revolutionary"), ("revolutionary", "revolutionary"), ("paradigm shift", "paradigm shift"),
        ("millennia-old", "millennia-old"), ("unprecedented", "unprecedented")])
    assert all(h["where"] == "script" for h in hits)


def test_matching_ignores_case_and_treats_space_and_hyphen_alike_and_allows_longer_forms():
    assert ss.banned_phrase_hits("A REVOLUTIONARY idea.")
    assert ss.banned_phrase_hits("A Paradigm-Shifting result.")
    assert ss.banned_phrase_hits("paradigm   shifts happen")
    assert ss.banned_phrase_hits("millennia old claims")
    assert ss.banned_phrase_hits("Absolute Certainty is rare.")
    assert ss.banned_phrase_hits("Groundbreaking work.")


def test_ordinary_words_are_not_hits():
    assert ss.banned_phrase_hits("They reported a shift in the paradigm of proof, a certain result, and an earlier revolution in printing.") == []
    assert ss.banned_phrase_hits("The antirevolutionary pamphlet.") == []       # inside another word
    assert ss.banned_phrase_hits("") == []


def test_the_description_body_is_checked_but_the_code_built_sections_are_not():
    desc = "An unprecedented overview.\n\n## References\n\n- A. (2020). A revolutionary title. arXiv:1\n\n## Hashtags\n#paradigmshift"
    hits = ss.banned_phrase_hits("", desc)
    assert [(h["where"], h["phrase"]) for h in hits] == [("description", "unprecedented")]


def test_feedback_quotes_each_sentence_once_and_lists_every_banned_phrase():
    hits = ss.banned_phrase_hits(SCRIPT)
    fb = ss.banned_feedback(hits)
    assert "REJECTED" in fb and fb.count("truly revolutionary development") == 1 and "millennia-old paradigm" in fb
    assert '"paradigm shift"' in fb and '"absolute certainty"' in fb and "plain, precise language" in fb
    assert fb.count("this truly revolutionary research") == 1


def test_error_message_names_the_phrases():
    e = ss.BannedPhraseError(ss.banned_phrase_hits(SCRIPT))
    assert "no episode was published" in str(e) and "unprecedented" in str(e)


def test_a_very_long_sentence_is_quoted_around_the_match_not_from_its_start():
    text = "word " * 200 + "this is a revolutionary claim " + "tail " * 200 + "."
    h = ss.banned_phrase_hits(text)[0]
    assert "revolutionary" in h["sentence"] and len(h["sentence"]) < 330 and h["sentence"].startswith("...") and h["sentence"].endswith("...")
