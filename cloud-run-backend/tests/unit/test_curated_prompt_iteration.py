"""The prompt-only iteration after the second pair of real dry runs: what the section and repair prompts now say. No check changed."""
import asyncio

import curated_mode as cm
import curated_script as csr
import curated_sources as cs
from tests.unit.test_curated_mode import PRIVATE, approved_doc, base_items, commentary_item
from tests.unit.test_curated_pipeline import TEXT

PLAN = csr.plan_sections(960, 1200)


def make_run():
    return cm.CuratedRun.from_list_doc(approved_doc(base_items() + [commentary_item(evidence_text=TEXT)]), private_texts=PRIVATE)


def test_the_sentence_rules_name_each_failure_the_dry_runs_showed():
    rules = csr.SHOW_RULES
    assert "SENTENCE RULES" in rules and "each one is checked by a program" in rules
    assert "A work's title and a person's name never share a sentence" in rules                                    # the false unlisted-work flags
    assert "Never say the title of an article" in rules and "Quanta's report" in rules                            # an article title that contained "Proved"
    assert "ONE sentence that says it was withdrawn" in rules and 'by "it" or "that paper"' in rules               # a withdrawn paper named again by its subject
    assert "company releases that have not been peer reviewed in ONE general sentence" in rules and "the company release <title> is" in rules   # the class label read as an attribution
    assert "eight or more words in a row from a note" in rules and "never reproduce a quoted fragment" in rules    # copied runs
    assert "a section over its upper limit is rejected" in rules


def test_a_section_prompt_states_the_ceiling_the_running_total_the_window_and_the_banned_words():
    s = PLAN[1]
    prompt = csr.section_user_prompt(s, {"opening": "HOST: one two three.\nEXPERT: four five."}, (960, 1200), '"remarkable", "groundbreaking"')
    assert f"aim for {s.budget} words; never fewer than {s.lo} and NEVER MORE THAN {s.hi}" in prompt
    assert "The script so far has 7 words and the whole script must end between 960 and 1200." in prompt
    assert 'Never use these words or phrases: "remarkable", "groundbreaking"' in prompt
    plain = csr.section_user_prompt(s, {})
    assert "(this is the first section)" in plain and "whole script must end" not in plain and "Never use these words" not in plain


def test_the_builder_sends_the_window_and_the_banned_words_with_every_section(monkeypatch):
    seen = []

    async def llm(system, user):
        seen.append(user)
        raise RuntimeError("stop")
    b = csr.ScriptBuilder(llm, make_run(), PLAN, [], lambda script: [], banned='"remarkable"', window=(960, 1200))
    loop = asyncio.new_event_loop()
    try:
        loop.run_until_complete(b.write_section(PLAN[0], {}))
    except RuntimeError:
        pass
    finally:
        loop.close()
    assert "between 960 and 1200" in seen[0] and '"remarkable"' in seen[0]


def test_commentary_is_listed_by_its_outlet_and_never_by_its_title_in_every_prompt():
    r = make_run()
    title = next(i["title"] for i in r.items if i["class"] == cs.COMMENTARY)
    block = r.prompt_block(include_excerpts=False)
    assert title not in block and "(commentary) a report in Example Magazine" in block and "never its title" in block
    system = csr.system_prompt(r, PLAN, [])
    assert title not in system and "do NOT say its title" in system
    assert "[P3] (company release)" in block                                    # the other classes are listed by title as before


def test_the_notes_say_never_to_use_eight_words_in_a_row_and_the_repair_repeats_the_rules():
    block = csr.notes_block([csr.Note("P4", "Example Magazine", "2026-10-19", "Example Magazine reported that some mathematicians urged caution.")])
    assert "Never use eight or more words in a row from any note" in block
    prompt = csr.repair_user_prompt(PLAN[2], "HOST: a b.", [{"message": "fix it"}], "ALLOWED")
    assert "withdrawn manuscript is named in one sentence" in prompt and "never share a sentence" in prompt and "never say an article's title" in prompt
    assert "eight words in a row from a note" in prompt and "1. fix it" in prompt
