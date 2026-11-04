"""A listed work whose whole title is quoted in the script is counted as named even when the model-based extraction reports nothing for it (episode 2,
2026-11-04: OpenAI's manuscript was never named, so the References left it out and its sentences were not checked against its abstract).

The sentences below are the ones of episode 2's script that name OpenAI's paper by its title. The whole script is not kept here: the repository is public
and the episode is private until Gary publishes it. Offline: the model call is faked, and it reports no mention for the OpenAI paper, as the real one did."""
import asyncio
import json

import named_work_check as nw
import paper_confirmation as pc


def run(coro):
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


def paper(pid, title, authors, year, cls=None):
    p = pc.ConfirmedPaper(pid=pid, title=title, authors=authors, year=year, venue=None,
                          ids={"arxiv": None, "arxiv_version": None, "pmid": None, "doi": None}, url="https://example.org/" + pid, abstract="Abstract.",
                          registry="openai_math", confirmed_at="t", title_match=1.0)
    p.source_class = cls
    return p


OPENAI = paper("P1", "The Exponential Time Hypothesis is False", ["OpenAI"], 2026, "company_release")
ANTHROPIC = paper("P2", "A 2^{o(n)} Time Algorithm for 3-SAT", ["Anthropic"], 2026, "company_release")
WIKI = paper("P7", "Exponential time hypothesis", [], 2026, "commentary")
SHORT = paper("P9", "Short title", ["Someone"], 2026, "peer_reviewed")
CONFIRMED = [OPENAI, ANTHROPIC, WIKI, SHORT]

# sentences of episode 2's script (revision 4), as the check saw them
SCRIPT = (
    'HOST: At the end of October, two artificial intelligence companies each released a paper with the same startling claim. '
    'OpenAI\'s paper is titled "The Exponential Time Hypothesis is False". Anthropic\'s paper presents a fast new algorithm for a classic logic puzzle called 3-SAT.\n'
    'EXPERT: OpenAI\'s catalogue lists a Lean formalization for "The Exponential Time Hypothesis is False", and the catalogue\'s own review status is unchecked. '
    'Two companies claim that the Exponential Time Hypothesis is false, and the people who proposed it are now among those checking.'
)


def silent_llm():
    async def call(system, user):
        return json.dumps({"mentions": []})          # the extraction returned nothing for the OpenAI paper
    return call


def check(script, confirmed=CONFIRMED, topic="The Exponential Time Hypothesis is false?"):
    return run(nw.check_naming(script, "", confirmed, silent_llm(), topic=topic))


def test_the_openai_manuscript_is_named_when_its_whole_title_is_quoted_even_if_the_model_reports_nothing():
    r = check(SCRIPT)
    assert r.named_pids == ["P1"] and r.passed
    hit = [m for m in r.mentions if m.get("pid") == "P1"]
    assert hit and hit[0]["matched_by"] == "the whole title, quoted" and hit[0]["quote"] == '"The Exponential Time Hypothesis is False"'


def test_the_title_in_running_prose_does_not_name_it():
    r = check("EXPERT: Two companies claim that the Exponential Time Hypothesis is false, and the people who proposed it are now among those checking.")
    assert r.named_pids == []


def test_a_commentary_title_and_a_short_title_never_name_anything_this_way():
    r = check('EXPERT: Wikipedia has an article called "Exponential time hypothesis". Another is called "Short title".')
    assert r.named_pids == []


def test_it_ignores_case_accents_spaces_and_punctuation_but_needs_the_whole_title():
    assert check('EXPERT: The paper "the exponential time hypothesis IS false!" is a claim.').named_pids == ["P1"]
    assert check("EXPERT: The paper “The Exponential Time Hypothesis is False” is a claim.").named_pids == ["P1"]
    assert check('EXPERT: The paper "The Exponential Time Hypothesis" is a claim.').named_pids == []


def test_it_only_adds_to_the_named_works_and_never_excuses_a_violation():
    mention = {"quote": "Impagliazzo and Paturi showed in 2001", "authors": ["Impagliazzo", "Paturi"], "year": 2001, "title_words": []}

    async def llm(system, user):
        return json.dumps({"mentions": [mention]})
    r = run(nw.check_naming(SCRIPT + " Impagliazzo and Paturi showed in 2001 that it matters.", "", CONFIRMED, llm, topic=None))
    assert [v["kind"] for v in r.violations] == ["unlisted_work"] and "P1" in r.named_pids


def test_a_work_the_model_did_report_is_not_listed_twice():
    mention = {"quote": 'OpenAI\'s paper is titled "The Exponential Time Hypothesis is False"', "authors": ["OpenAI"], "year": 2026,
               "title_words": ["Exponential", "Time", "Hypothesis", "False"]}

    async def llm(system, user):
        return json.dumps({"mentions": [mention]})
    r = run(nw.check_naming(SCRIPT, "", CONFIRMED, llm, topic=None))
    assert r.named_pids == ["P1"] and sum(1 for m in r.mentions if m.get("pid") == "P1") == 1
