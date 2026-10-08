"""Tests for named_work_check (gap 3 fix 1, C5): matching, link phrases, fail-closed behaviour. Offline."""
import asyncio
import json

import pytest

import named_work_check as nw
import paper_confirmation as pc


def run(coro):
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


def paper(pid, title, authors, year):
    return pc.ConfirmedPaper(pid=pid, title=title, authors=authors, year=year, venue=None,
                             ids={"arxiv": None, "arxiv_version": None, "pmid": None, "doi": f"10.1/{pid}"},
                             url="https://doi.org/x", abstract="Abs.", registry="crossref", confirmed_at="t", title_match=1.0)


LOVELACE = paper("P1", "Analytical engines and the first algorithms", ["Ada Lovelace", "Alan Turing"], 2025)
CURIE = paper("P2", "Radioactivity in unaligned samples of pitchblende", ["Marie Skłodowska Curie"], 2024)
CONFIRMED = [LOVELACE, CURIE]


def fake_llm(mentions_by_script):
    """llm_call that returns the mentions registered for any substring present in the prompt."""
    async def call(system, user):
        out = []
        for key, ms in mentions_by_script.items():
            if key in user:
                out += ms
        return json.dumps({"mentions": out})
    return call


def m(quote, authors=(), year=None, title_words=()):
    return {"quote": quote, "authors": list(authors), "year": year, "title_words": list(title_words)}


# ---------------------------------------------------------------- matching
def test_match_by_surname_and_year():
    assert nw.match_mention(m("q", ["Lovelace"], 2025), CONFIRMED) == "P1"
    assert nw.match_mention(m("q", ["Lovelace", "Turing"], None), CONFIRMED) == "P1"


def test_year_off_by_one_still_matches_but_two_does_not():
    assert nw.match_mention(m("q", ["Lovelace"], 2024), CONFIRMED) == "P1"
    assert nw.match_mention(m("q", ["Lovelace"], 2019), CONFIRMED) is None


def test_year_far_off_but_title_words_match():
    assert nw.match_mention(m("q", ["Lovelace"], 2019, ["analytical", "engines", "algorithms"]), CONFIRMED) == "P1"


def test_accents_and_case_are_ignored():
    assert nw.match_mention(m("q", ["CURIE"], 2024), CONFIRMED) == "P2"
    assert nw.match_mention(m("q", ["Skłodowska"], 2024), CONFIRMED) is None  # only the last name of a listed author is used


def test_unknown_author_does_not_match():
    assert nw.match_mention(m("q", ["Zorblatt"], 2025), CONFIRMED) is None


def test_title_only_mention_needs_three_words():
    assert nw.match_mention(m("q", [], None, ["radioactivity", "unaligned", "samples"]), CONFIRMED) == "P2"
    assert nw.match_mention(m("q", [], None, ["radioactivity"]), CONFIRMED) is None


# ---------------------------------------------------------------- the check
def test_listed_work_passes_and_is_named():
    script = "ADAM: According to Lovelace and Turing in 2025, engines compute. The link is in the description."
    llm = fake_llm({"According to Lovelace": [m("According to Lovelace and Turing in 2025", ["Lovelace", "Turing"], 2025)]})
    r = run(nw.check_naming(script, "", CONFIRMED, llm))
    assert r.passed and r.named_pids == ["P1"]


def test_unlisted_work_is_a_violation():
    script = "ADAM: Zorblatt and Quux showed in 2019 that engines compute."
    llm = fake_llm({"Zorblatt": [m("Zorblatt and Quux showed in 2019", ["Zorblatt", "Quux"], 2019)]})
    r = run(nw.check_naming(script, "", CONFIRMED, llm))
    assert not r.passed and r.violations[0]["kind"] == "unlisted_work" and r.violations[0]["authors"] == ["Zorblatt", "Quux"]


def test_mention_with_no_author_and_no_title_is_ignored():
    script = "ADAM: Some study says engines compute."
    llm = fake_llm({"Some study": [m("Some study says engines compute")]})
    assert run(nw.check_naming(script, "", CONFIRMED, llm)).passed


def test_link_phrase_without_a_listed_paper_is_a_violation():
    script = "ADAM: Engines are old. The link is in the description. MATILDA: Great."
    r = run(nw.check_naming(script, "", CONFIRMED, fake_llm({})))
    assert [v["kind"] for v in r.violations] == ["link_phrase_unattached"]


def test_link_phrase_attached_to_a_listed_paper_passes():
    script = "ADAM: Lovelace and Turing, 2025, showed engines compute, and the link is in the description."
    llm = fake_llm({"Lovelace and Turing": [m("Lovelace and Turing, 2025, showed engines compute", ["Lovelace", "Turing"], 2025)]})
    assert run(nw.check_naming(script, "", CONFIRMED, llm)).passed


def test_link_phrase_far_from_the_paper_is_unattached():
    script = "ADAM: Lovelace and Turing, 2025, showed engines compute. " + ("filler words " * 120) + "And the link is in the description."
    llm = fake_llm({"Lovelace and Turing": [m("Lovelace and Turing, 2025, showed engines compute", ["Lovelace", "Turing"], 2025)]})
    r = run(nw.check_naming(script, "", CONFIRMED, llm))
    assert [v["kind"] for v in r.violations] == ["link_phrase_unattached"]


def test_description_mentions_are_checked_too():
    desc = "Overview. Zorblatt (2019) argued otherwise.\n\n## References\n\n- Zorblatt, 2019 (model-written, must be ignored)\n"
    llm = fake_llm({"Overview": [m("Zorblatt (2019) argued otherwise", ["Zorblatt"], 2019)]})
    r = run(nw.check_naming("ADAM: hello", desc, CONFIRMED, llm))
    assert r.violations and r.violations[0]["where"] == "description"


def test_model_written_reference_section_is_not_read_as_mentions():
    seen = {}

    async def llm(system, user):
        seen["prompt"] = user
        return json.dumps({"mentions": []})
    run(nw.check_naming("ADAM: hi", "Body text.\n\n## References\n\n- Zorblatt 2019\n", CONFIRMED, llm))
    assert "Zorblatt" not in seen["prompt"]


def test_named_pids_are_in_order_of_first_mention():
    script = "Curie, 2024 first. Then Lovelace, 2025."
    llm = fake_llm({"Curie, 2024": [m("Curie, 2024 first", ["Curie"], 2024), m("Then Lovelace, 2025", ["Lovelace"], 2025)]})
    assert run(nw.check_naming(script, "", CONFIRMED, llm)).named_pids == ["P2", "P1"]


def test_fail_closed_when_the_model_errors():
    async def boom(system, user):
        raise RuntimeError("quota")
    with pytest.raises(nw.NamingCheckUnavailable):
        run(nw.check_naming("ADAM: hi", "", CONFIRMED, boom))


def test_fail_closed_on_unparseable_answer():
    async def junk(system, user):
        return "I could not do that"
    with pytest.raises(nw.NamingCheckUnavailable):
        run(nw.check_naming("ADAM: hi", "", CONFIRMED, junk))


def test_json_in_code_fences_is_accepted():
    async def fenced(system, user):
        return "```json\n{\"mentions\": []}\n```"
    assert run(nw.check_naming("ADAM: hi", "", CONFIRMED, fenced)).passed


def test_feedback_text_lists_violations_and_allowed_papers():
    r = nw.NamingResult(violations=[{"kind": "unlisted_work", "where": "script", "quote": "Zorblatt and Quux showed", "authors": ["Zorblatt"], "year": 2019},
                                    {"kind": "link_phrase_unattached", "where": "script", "quote": "link is in the description"}])
    fb = nw.feedback_text(r, CONFIRMED)
    assert "Zorblatt" in fb and "link-in-the-description phrase" in fb and "[P1] Ada Lovelace, Alan Turing (2025)" in fb and "ONLY these papers" in fb


def test_violation_error_message_is_clear():
    msg = str(nw.NamingViolationError([{"kind": "unlisted_work", "where": "script", "quote": "Zorblatt showed", "authors": ["Zorblatt"], "year": 2019}]))
    assert "not among the confirmed papers" in msg and "no episode was published" in msg and "Zorblatt" in msg
