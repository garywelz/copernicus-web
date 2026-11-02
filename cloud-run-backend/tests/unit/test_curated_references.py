"""The code-built References of a curated episode as a listener reads them: plain-text titles, every commentary item the script credits (by the
attribution routing), a date and an https URL on each commentary line, no empty family, characters that survive, and the 4,000-character
description limit with eight commentary lines. Pure code: no model, no network, no database."""
import json

import pytest

import curated_attribution as ca
import curated_mode as cm
import curated_sources as cs
from content_fixes import limit_description_length
from tests.unit.test_curated_mode import base_items, commentary_item, release_item, run_of

BS = chr(92)
VENUES = ["Quanta Magazine", "Wikipedia", "The Washington Times", "Scientific American", "Nature", "Zenodo", "Example Review", "Sample Times"]


def eight_commentary(**extra):
    items = []
    for n, venue in enumerate(VENUES, start=1):
        items.append(commentary_item(
            identifiers={"url": f"https://example.org/story-{n}"}, venue=venue, title=f"A long headline about the release number {n}, as reported by the desk",
            authors=[f"Reporter Number{n}"], date=f"2026-10-{10 + n:02d}", evidence_text=f"{venue} text {n}. Several mathematicians said the claims need careful checking by experts.",
            **extra))
    return items


# --- titles as plain text --------------------------------------------------------------------------------------------------------------
@pytest.mark.parametrize("title,expected", [
    (f"The Quasi-Riemann Hypothesis: A Zero-Free Half-Plane $`{BS}Re s{BS}gt 7/8`$", "The Quasi-Riemann Hypothesis: A Zero-Free Half-Plane Re s > 7/8"),
    (f"A bound $`{BS}frac{{3}}{{4}}`$ and $`x^{{2}}`$", "A bound 3/4 and x^2"),
    (f"A $$ {BS}Re s {BS}lt 1 $$ title", "A Re s < 1 title"),
    (f"Zeros with $s {BS}geq 1/2$", "Zeros with s >= 1/2"),
    ("A plain title with no markup", "A plain title with no markup"),
])
def test_a_title_is_printed_as_plain_text_never_as_markup(title, expected):
    out = cm.plain_title(title)
    assert out == expected
    assert BS not in out and "$" not in out and "`" not in out and "{" not in out and "}" not in out


def test_the_reference_line_for_a_release_with_a_latex_title_is_plain():
    item = release_item(title=f"The Quasi-Riemann Hypothesis: A Zero-Free Half-Plane $`{BS}Re s{BS}gt 7/8`$")
    run = run_of(base_items()[:2] + [item])
    text = cm.build_sources(run, run.confirmed_papers(), ["P3"])
    assert "Half-Plane Re s > 7/8." in text and BS not in text and "$`" not in text


def test_a_title_that_ends_in_a_question_mark_gets_no_second_stop():
    run = run_of(base_items() + [commentary_item(title="AI Proved the Quasi-Riemann Hypothesis. What Happens Now?")])
    text = cm.build_sources(run, run.confirmed_papers(), ["P4"])
    assert "What Happens Now? [commentary" in text and "?." not in text


# --- the family ------------------------------------------------------------------------------------------------------------------------
def test_a_manuscript_with_no_family_has_no_family_field():
    run = run_of(base_items() + [release_item(title="Withdrawn thing", path="a/b", family=None, result_status="withdrawn")])
    text = cm.build_sources(run, run.confirmed_papers(), ["P4"])
    assert "family" not in text and "None" not in text and ". commit 7ef5c0cc5." in text


def test_a_manuscript_with_a_family_still_shows_it():
    text = cm.build_sources(run_of(), run_of().confirmed_papers(), ["P3"])
    assert "family 378, commit 7ef5c0cc5." in text and "OpenAI mathematics release" not in text


# --- the commentary lines --------------------------------------------------------------------------------------------------------------
def test_a_commentary_line_has_the_author_the_outlet_the_title_the_date_the_url_and_the_label():
    run = run_of(base_items() + [commentary_item(date="2026-10-19")])
    text = cm.build_sources(run, run.confirmed_papers(), ["P4"])
    assert ("- A. Reporter, Example Magazine (19 October 2026). Mathematicians react to the release. "
            "[commentary: reported, not a source for any claim that a result is true] https://example.org/story") in text


def test_an_http_address_is_printed_as_https_and_a_missing_date_falls_back_to_the_year():
    run = run_of(base_items() + [commentary_item(identifiers={"url": "http://example.org/plain"}, url="http://example.org/plain")])
    text = cm.build_sources(run, run.confirmed_papers(), ["P4"])
    assert "https://example.org/plain" in text and "http://" not in text and "(2026)" in text
    assert cm.readable_date("2026-10", 2026) == "October 2026" and cm.readable_date("bad", 2026) == "2026" and cm.readable_date(None) == ""


def test_no_pointer_to_an_episode_page_is_printed_even_when_other_sources_were_not_named():
    text = cm.build_sources(run_of(), run_of().confirmed_papers(), ["P1"])
    assert "Other sources reviewed" not in text and "episode page" not in text and "copernicusai.fyi" not in text


def test_the_dash_and_other_characters_survive_the_build_the_limit_and_a_json_round_trip():
    title = "Terence Tao on AI in mathematics (and beyond) " + chr(0x2014) + " excerpts; Maths 2.0 " + chr(0x2018) + "quoted" + chr(0x2019)
    run = run_of(base_items() + [commentary_item(title=title)])
    out = cm.apply_curated_sources("Intro.", run, run.confirmed_papers(), ["P4"])
    out = limit_description_length(out, 4000)
    assert chr(0x2014) in out and chr(0x2018) + "quoted" + chr(0x2019) in out and "?" not in out
    assert json.loads(json.dumps(out, ensure_ascii=False)) == out and json.loads(json.dumps(out)) == out
    assert out.encode("utf-8").decode("utf-8") == out


# --- which commentary is listed --------------------------------------------------------------------------------------------------------
def test_every_commentary_item_the_script_credits_is_listed_even_if_the_naming_check_did_not_name_it():
    run = run_of(base_items() + eight_commentary())
    script = ("HOST: What happened?\nEXPERT: Quanta Magazine reported that the claims need careful checking by experts. "
              "Wikipedia reports that the claims need careful checking by experts. Nature reported that the claims need careful checking by experts.")
    credited = ca.credited_commentary_pids(script, run)
    assert credited == ["P4", "P5", "P8"]
    text = cm.apply_curated_sources("Intro.", run, run.confirmed_papers(), ["P1"], script=script)
    assert "https://example.org/story-1" in text and "https://example.org/story-2" in text and "https://example.org/story-5" in text
    assert "https://example.org/story-3" not in text and "https://example.org/story-4" not in text          # not credited: not listed


def test_without_the_script_only_the_named_items_are_listed():
    run = run_of(base_items() + eight_commentary())
    text = cm.apply_curated_sources("Intro.", run, run.confirmed_papers(), ["P1", "P4"])
    assert "story-1" in text and "story-2" not in text


def test_the_credited_items_keep_the_order_of_the_list():
    run = run_of(base_items() + eight_commentary())
    script = "EXPERT: Nature reported that the claims need careful checking. Quanta Magazine reported that the claims need careful checking."
    assert ca.credited_commentary_pids(script, run) == ["P4", "P8"]


def test_the_job_gives_the_final_script_to_the_builder():
    from pathlib import Path
    text = (Path(__file__).resolve().parents[2] / "services" / "podcast_generation_service.py").read_text(encoding="utf-8")
    start = text.index("def _finalize_content")
    block = text[start:text.index("def _job_rejection_sink", start)]
    assert "_curated.apply_curated_sources(" in block and "script=content.get('script')" in block


# --- the 4,000-character limit ---------------------------------------------------------------------------------------------------------
def test_eight_commentary_lines_and_the_releases_keep_the_references_whole_inside_the_limit():
    items = [release_item(title="First release", path="a/1", family="001"), release_item(title="Second release", path="a/2", family="002"),
             release_item(title="Third release", path="a/3", family="003")]
    run = run_of(items + eight_commentary(limits=[{"type": "fetch_refused", "reason": "paywall"}]))
    script = "EXPERT: " + " ".join(f"{v} reported that the claims need careful checking by experts." for v in VENUES)
    body = "\n\n".join("A paragraph of the narrative that goes on for a while to take up room in the description. " * 4 for _ in range(12))
    full = cm.apply_curated_sources(body + "\n\n## Hashtags\n#CopernicusAI", run, run.confirmed_papers(), ["P1", "P2", "P3"], script=script)
    assert full.count("[commentary: reported, not a source for any claim that a result is true]") == 8
    out = limit_description_length(full, 4000)
    assert len(out) <= 4000 and len(full) > 4000                       # the narrative gave way, the References did not
    assert out.count("[commentary: reported, not a source for any claim that a result is true]") == 8
    assert all(f"https://example.org/story-{n}" in out for n in range(1, 9))
    assert out.rstrip().endswith("#CopernicusAI")
    section = full[full.index("## References"):full.index("## Hashtags")]
    assert section.strip() in out
