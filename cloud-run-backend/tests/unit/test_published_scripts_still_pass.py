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
]


def load(name):
    script = (FIXTURES / f"{name}.txt").read_text(encoding="utf-8")
    doc = json.loads((FIXTURES / f"{name}.list.json").read_text(encoding="utf-8"))
    return script, doc


@pytest.mark.parametrize("name,duration,title", PUBLISHED)
def test_a_published_script_raises_no_unattributed_claim(name, duration, title):
    script, doc = load(name)
    run = curated_mode.CuratedRun.from_list_doc(doc)
    violations = uc.check(script, run.confirmed_papers())
    assert violations == [], f"{title}: " + "; ".join(f"[{v['kind']}] {v['find']}" for v in violations)


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
    script, doc = load(name)
    run = curated_mode.CuratedRun.from_list_doc(doc)
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
