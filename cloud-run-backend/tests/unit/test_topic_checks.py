"""Topic checks (fix 7): a name the topic gives that no paper covers must be called out as not covered, and the topic title is not read aloud. Offline."""
import asyncio
import json
import sys
from pathlib import Path
from types import SimpleNamespace as NS
from unittest.mock import MagicMock

import pytest

try:
    import psutil  # noqa: F401
except ImportError:
    sys.modules["psutil"] = MagicMock()

import topic_checks as tc

TOPIC = "Proof dependency graphs in formal mathematics libraries: what the network structure of mathlib and Metamath reveals about how mathematics is built"
RUN6 = json.loads((Path(__file__).resolve().parents[1] / "fixtures" / "ever_math_run6_papers.json").read_text(encoding="utf-8"))["papers"]
PAPERS = [NS(title=p["title"], abstract=p["abstract"]) for p in RUN6]


def run(coro):
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


# ---------------------------------------------------------------- names in the topic
def test_the_names_a_topic_gives():
    assert tc.named_things(TOPIC) == ["Metamath"]                       # "Proof" starts the topic; mathlib is lower case and not a proper-noun cue
    assert tc.named_things("Using GPT-4 and Python for CRISPR-Cas9 design") == ["GPT-4", "Python", "CRISPR-Cas9"]
    assert tc.named_things("Chaos: The hidden order of neural networks") == []                     # a capital after a colon starts a clause
    assert tc.named_things("How crows use 'Betty' hooks") == ["Betty"]                             # quoted
    assert tc.named_things("The iPhone and its camera") == ["iPhone"]                              # capital inside
    assert tc.named_things("") == []


def test_metamath_is_the_one_thing_the_last_runs_papers_do_not_cover():
    assert tc.uncovered_named_things(TOPIC, PAPERS) == ["Metamath"]
    with_it = PAPERS + [NS(title="A Metamath proof checker", abstract="We verify set.mm.")]
    assert tc.uncovered_named_things(TOPIC, with_it) == []


def test_a_name_is_covered_by_a_plural_or_possessive_form_in_a_title_or_abstract():
    assert tc.uncovered_named_things("Studying Python programs", [NS(title="x", abstract="The Python programs we wrote")]) == []
    assert tc.uncovered_named_things("Studying Python programs", [NS(title="Pythons of Asia", abstract="")]) == []


# ---------------------------------------------------------------- the statement
@pytest.mark.parametrize("sentence", [
    "The papers reviewed here do not cover Metamath.",
    "While the papers extensively cover Mathlib and Mizar, the broader exploration of how Metamath's structure compares remains an open avenue for future research.",
    "None of the papers we looked at discusses Metamath.",
    "Metamath is outside what was reviewed here.",
    "Metamath has not been covered by any of these papers.",
    "The reviewed papers don't address Metamath at all.",
    "No paper in this set examines Metamath.",
])
def test_sentences_that_say_the_papers_do_not_cover_it_count(sentence):
    assert tc.missing_coverage_statements("ADAM: " + sentence, ["Metamath"]) == []


@pytest.mark.parametrize("script", [
    "Metamath is another proof system with a very large library of verified theorems.",                     # talks about it, says nothing about coverage
    "The papers reviewed here do not cover several things.",                                                # a limitation, but not about it
    "Mathlib is not Metamath.\nThe papers cover Lean.",                                                      # the cue is in another sentence
    "The papers cover Metamath in detail.",                                                                  # claims coverage
    "",
])
def test_scripts_that_do_not_say_it_are_flagged(script):
    assert tc.missing_coverage_statements(script, ["Metamath"]) == ["Metamath"]


def test_the_last_runs_script_never_said_it():
    # lines from the ever-math-260009 script: it covers Mathlib and four loosely related papers and never mentions Metamath
    s = ("MATILDA: Welcome to Copernicus AI. Adam, what do the papers reviewed here tell us about this intricate topic?\n\n"
         "ADAM: A key paper by Xinze Li and colleagues in 2026 provides a deep network analysis of Mathlib, the Lean 4 mathematical library.\n\n"
         "MATILDA: Thank you, Adam. This leaves open questions about optimizing human-AI collaboration.")
    assert tc.missing_coverage_statements(s, ["Metamath"]) == ["Metamath"]


def test_only_the_names_without_a_statement_are_returned():
    s = "The papers reviewed here do not cover Metamath. Zorblatt is another matter."
    assert tc.missing_coverage_statements(s, ["Metamath", "Zorblatt"]) == ["Zorblatt"]


def test_prompt_block_and_feedback():
    block = tc.coverage_prompt_block(["Metamath"])
    assert "none of the numbered papers covers it" in block and "The papers reviewed here do not cover Metamath." in block and "own knowledge" in block
    assert tc.coverage_prompt_block([]) == ""
    fb = tc.coverage_feedback(["Metamath", "Zorblatt"])
    assert "REJECTED" in fb and "Metamath, Zorblatt" in fb and "them" in fb


# ---------------------------------------------------------------- the title read aloud
def test_a_sentence_with_the_whole_topic_is_the_title_read_aloud():
    s = ("MATILDA: Welcome to Copernicus AI. I'm Matilda, and today we're exploring 'Proof dependency graphs in formal mathematics libraries: what the "
         "network structure of mathlib and Metamath reveals about how mathematics is built'. Adam, what do the papers tell us?")
    assert len(tc.read_aloud_sentences(s, TOPIC)) == 1


def test_asking_the_question_in_other_words_is_fine():
    s = ("MATILDA: Welcome to Copernicus AI. Today we ask how the dependencies between theorems in a big formal library are arranged, and what the "
         "shape of that network tells us. Adam, what do the papers say?")
    assert tc.read_aloud_sentences(s, TOPIC) == []
    assert tc.read_aloud_sentences("ADAM: Mathlib is a library of Lean proofs and its network of dependencies has a particular structure.", TOPIC) == []


def test_a_short_topic_is_never_reported():
    assert tc.read_aloud_sentences("Today: Chaos theory in cells.", "Chaos theory in cells") == []
    assert tc.read_aloud_sentences("anything", "") == []


# ---------------------------------------------------------------- in the prompt
def test_the_prompt_asks_for_the_statement_only_when_something_is_uncovered_and_no_longer_quotes_the_topic():
    import inspect
    import podcast_research_integrator as pri
    src = inspect.getsource(pri.PodcastResearchIntegrator.build_2_speaker_research_prompt)
    assert "{coverage_block}" in src and "we're exploring {research_context.topic}" not in src
    assert "do not read the topic title aloud or put it in quotation marks" in src and "never reads the topic title aloud" in src
