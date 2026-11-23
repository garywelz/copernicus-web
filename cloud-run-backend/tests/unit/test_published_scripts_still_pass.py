"""Two published episodes, kept as they went out, with the source lists they were approved against.

Every check that does not need a model is run over each script. A change that would refuse a script already published — as the scope check
did on 2026-11-21, when "diseases" failed to match a source saying "disease-associated" — fails here instead of in production.

The model-backed checks (naming and attribution) are not run: they need a model call. What is covered is everything deterministic: the
scope and unattributed-claim rules, greetings and sign-offs, banned wording, notation that cannot be read aloud, the line format, the
status wording, and the length window the episode was made in.
"""
import json
from pathlib import Path

import pytest

import curated_checks as cc
import curated_mode
import curated_script as csr
import unattributed_claims as uc
from curated_pipeline import script_format_problems
from script_style import banned_phrase_hits, greeting_hits
from speech_text import notation_problems
from utils.script_validation import calculate_maximum_words_for_duration, calculate_minimum_words_for_duration

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures" / "published_scripts"
PUBLISHED = [
    # (canonical name, the duration it was made for, what it is)
    ("ever-bio-260013", "7-10 minutes", "Designing an enzyme from scratch: AI-made proteases"),
    ("ever-bio-260014", "7-10 minutes", "Can an AI write a working genome?"),
    # The two mathematics episodes, which carry a company release with its manuscript text attached. Their lists are the first fixtures
    # with release text: it is inlined as the item's evidence_text, which is where curated_mode puts it at run time.
    ("ever-math-260016", "6-8 minutes", "OpenAI says the irrationality exponent of pi is 2. Is it?"),
    ("ever-math-260017", "4-6 minutes", "OpenAI says the free group factors are isomorphic. Are they?"),
]


# The three phrase classes added on 2026-11-23. These four episodes went out before the rule existed and each one contains some; the
# sentences are kept here as a matter of record. The rule is NOT relaxed for anything written from now on, and the fixtures are exactly
# as the episodes went out. An episode already published cannot be unpublished by a test.
PUBLISHED_BEFORE_THE_PHRASE_RULE = ("unsourced_history", "unsourced_consensus", "unsourced_evaluation")

HISTORY_ON_RECORD = {
    "ever-bio-260013": [
        ("unsourced_history",
         "For decades, scientists have aimed to design enzymes from scratch, building proteins that can perform specific chemical reactions not found in nature."),
        ("unsourced_consensus",
         "It doesn't guarantee absolute truth, but it does mean the scientific community has evaluated the claims and found them to be supported by the presented data and methodology."),
        ("unsourced_evaluation",
         "So, with these promising results, what are the next steps for this field?"),
        ("unsourced_evaluation",
         "Demonstrating the ability to design enzymes for a wider range of chemical reactions, especially those with high energy barriers, would be a significant advance."),
        ("unsourced_evaluation",
         "Also, the ability to design enzymes that are stable and function reliably under various real-world conditions would be crucial."),
    ],
    "ever-bio-260014": [
        ("unsourced_history",
         "For decades, scientists have been able to read and edit the genetic code of life."),
        ("unsourced_evaluation",
         "It's a significant step beyond simply understanding existing life."),
        ("unsourced_evaluation",
         "The peer-review process is a crucial step in scientific validation, where experts scrutinize the methods, results, and conclusions."),
    ],
    "ever-math-260016": [
        ("unsourced_history",
         "OpenAI has released a manuscript claiming a proof of a long-standing conjecture about the mathematical constant pi."),
    ],
    "ever-math-260017": [
        ("unsourced_history",
         "A long-standing problem in mathematics, known as the free group factor isomorphism problem, has recently seen a claimed solution."),
        ("unsourced_consensus",
         "What would be the next steps for the mathematical community to confirm or refute these claims?"),
    ],
}


def load(name):
    script = (FIXTURES / f"{name}.txt").read_text(encoding="utf-8")
    doc = json.loads((FIXTURES / f"{name}.list.json").read_text(encoding="utf-8"))
    return script, doc


def private_texts(name):
    """The text the private store holds for this list, by item id: a company release's attached manuscript text. The list document is kept
    exactly as the service returns it, so its list_hash still verifies, and the text arrives the way production supplies it."""
    path = FIXTURES / f"{name}.private.json"
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}


def run_for(name):
    script, doc = load(name)
    return script, curated_mode.CuratedRun.from_list_doc(doc, private_texts=private_texts(name))


@pytest.mark.parametrize("name,duration,title", PUBLISHED)
def test_a_published_script_raises_no_unattributed_claim(name, duration, title):
    script, run = run_for(name)
    violations = [v for v in uc.check(script, run.confirmed_papers()) if v["kind"] not in PUBLISHED_BEFORE_THE_PHRASE_RULE]
    assert violations == [], f"{title}: " + "; ".join(f"[{v['kind']}] {v['find']}" for v in violations)


@pytest.mark.parametrize("name,duration,title", PUBLISHED)
def test_the_phrase_classes_a_published_script_predates_are_exactly_the_ones_on_record(name, duration, title):
    """These four episodes went out before unsourced history, consensus and evaluation were refused, and each one contains some. The
    sentences are listed in HISTORY_ON_RECORD so they are a matter of record rather than a silence: a NEW one in any fixture fails here,
    and the rule itself is not loosened for anything written from now on.

    An episode already published cannot be unpublished by a test, and the fixtures are kept exactly as the episodes went out.
    """
    script, run = run_for(name)
    found = sorted((v["kind"], v["find"]) for v in uc.check(script, run.confirmed_papers())
                   if v["kind"] in PUBLISHED_BEFORE_THE_PHRASE_RULE)
    assert found == sorted(HISTORY_ON_RECORD[name]), (
        f"{title}: the pre-existing phrases have changed.\n  now: " + "\n  now: ".join(f"[{k}] {s}" for k, s in found))


@pytest.mark.parametrize("name,duration,title", PUBLISHED)
def test_a_published_script_greets_nobody_and_uses_no_banned_wording(name, duration, title):
    script, _ = load(name)
    assert greeting_hits(script) == [], f"{title}: {[h['matched'] for h in greeting_hits(script)]}"
    assert banned_phrase_hits(script, "") == [], f"{title}: {[h['matched'] for h in banned_phrase_hits(script, '')]}"


@pytest.mark.parametrize("name,duration,title", PUBLISHED)
def test_a_published_script_reads_aloud_and_is_formatted(name, duration, title):
    script, _ = load(name)
    assert notation_problems(script, "") == [], f"{title}: {notation_problems(script, '')}"
    assert script_format_problems(script) == [], f"{title}: {script_format_problems(script)}"


@pytest.mark.parametrize("name,duration,title", PUBLISHED)
def test_a_published_script_passes_the_curated_checks(name, duration, title):
    script, run = run_for(name)
    found = run.checks(script)
    assert found == [], f"{title}: {cc.summary(found)}"


@pytest.mark.parametrize("name,duration,title", PUBLISHED)
def test_a_published_script_is_inside_the_window_it_was_made_for(name, duration, title):
    script, _ = load(name)
    words = len(script.split())
    assert calculate_minimum_words_for_duration(duration) <= words <= calculate_maximum_words_for_duration(duration), \
        f"{title}: {words} words"


def test_the_fixtures_are_the_episodes_that_were_published():
    """A guard on the fixtures themselves: the text is the voiced text, so its length matches what the episodes recorded."""
    assert len((FIXTURES / "ever-bio-260013.txt").read_text(encoding="utf-8").split()) == 965
    assert len((FIXTURES / "ever-bio-260014.txt").read_text(encoding="utf-8").split()) == 932
    for name, _, _ in PUBLISHED:
        doc = json.loads((FIXTURES / f"{name}.list.json").read_text(encoding="utf-8"))
        assert doc["status"] == "approved" and doc["list_hash"], name
