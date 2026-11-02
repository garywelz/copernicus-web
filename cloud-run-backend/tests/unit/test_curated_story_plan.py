"""The story plan and the prompt changes decided on 2026-11-01 after run A passed every check but read as a compliance report. No check changed."""
import curated_mode as cm
import curated_script as csr
from speakable import spoken_source
from tests.unit.test_curated_mode import PRIVATE, approved_doc, base_items, commentary_item
from tests.unit.test_curated_pipeline import TEXT

PLAN = csr.plan_sections(960, 1200)


def make_run():
    return cm.CuratedRun.from_list_doc(approved_doc(base_items() + [commentary_item(evidence_text=TEXT)]), private_texts=PRIVATE)


def test_the_plan_is_a_story_in_five_sections_with_no_sources_section():
    assert [s.key for s in PLAN] == ["opening", "claims", "trust", "reaction", "closing"]
    assert [s.title for s in PLAN] == ["The hook", "What is claimed", "How far to trust it", "The reaction", "What to watch"]
    assert sum(s.budget for s in PLAN) == 1080
    budgets = {s.key: s.budget for s in PLAN}
    assert 110 <= budgets["opening"] <= 130 and 290 <= budgets["claims"] <= 330 and 270 <= budgets["trust"] <= 310 and 270 <= budgets["reaction"] <= 310 and 70 <= budgets["closing"] <= 90


def test_the_reaction_section_is_the_one_dropped_without_commentary():
    plan = csr.plan_sections(960, 1200, has_commentary=False)
    assert "reaction" not in [s.key for s in plan] and sum(s.budget for s in plan) == 1080


def test_the_goals_tell_the_story():
    goals = {t[0]: t[3] for t in csr.SECTION_TEMPLATES}
    assert "within a day of the release" in goals["opening"] and "a question" in goals["opening"] and "will or will not cover" in goals["opening"]
    assert "HOST asks" in goals["claims"] and "ONE general sentence" in goals["claims"] and "short name" in goals["claims"] and "No formulas" in goals["claims"]
    assert "formally verified" in goals["trust"] and "unchecked" in goals["trust"] and "within a day of the release" in goals["trust"] and "NEVER named" in goals["trust"]
    assert "A reporter's own phrase belongs to the outlet" in goals["reaction"]


def test_the_rules_say_no_formulas_one_full_title_spoken_names_person_attribution_and_real_dialogue():
    rules = csr.SHOW_RULES
    assert "never read a formula or symbolic statement aloud" in rules
    assert "full title at most once" in rules and "the 7/8 paper" in rules and "the ETH paper" in rules
    assert "SPOKEN NAME" in rules and "Tao's own web page" in rules and "the Fields Medalists' declaration" in rules and "do not list the sources" in rules
    assert "Attribute to a person only the words the source attributes to that person" in rules and "attributed to the outlet" in rules
    assert "the HOST asks what a curious listener would ask" in rules and "Never say what the episode will not cover" in rules
    assert "within a day of the release because of a sign error in a key step" in rules and "no technical detail" in rules.replace("Give no", "give no")


def test_each_commentary_outlet_has_a_short_spoken_name_and_never_zenodo():
    assert spoken_source("Quanta Magazine") == "Quanta" and spoken_source("Wikipedia") == "Wikipedia" and spoken_source("Nature") == "Nature"
    assert spoken_source("Scientific American") == "Scientific American" and spoken_source("The Washington Times") == "the Washington Times"
    assert spoken_source("tao-web (AI-assisted summary reviewed by Terence Tao)") == "Tao's own web page"
    assert spoken_source("Zenodo") == "the Fields Medalists' declaration"
    assert spoken_source("Some Outlet (a label)") == "Some Outlet" and spoken_source("") == "the outlet"


def test_the_prompts_carry_the_spoken_names_not_the_labels():
    run = make_run()
    block = csr.allowed_works_block(run)
    assert "SPOKEN NAME" in block
    prompt = run.prompt_block(include_excerpts=False)
    assert "SPOKEN NAME" in prompt
    note = csr.Note(pid="P9", outlet="Zenodo", date="2026-10-20", claim="Signatories said the pace harms the field.")
    assert "the Fields Medalists' declaration, 2026-10-20" in csr.notes_block([note]) and "Zenodo" not in csr.notes_block([note])


def test_a_missing_class_label_is_repaired_in_the_claims_section():
    out = csr.collect_violations(curated=[{"kind": "preprint_not_labelled"}, {"kind": "company_release_not_labelled"}], missing_cov=["Goldbach"])
    assert {v["section"] for v in out} == {"claims", "trust"}
