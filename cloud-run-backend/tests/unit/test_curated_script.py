"""The curated script pipeline (curated_script.py): notes first, a section plan with word budgets, repair instead of regeneration, the allowed-works
list. Offline: every model call is a scripted fake, and the checker is a function of the script."""
import asyncio
import json

import pytest

import curated_checks as cc
import curated_mode as cm
import curated_script as csr
import curated_sources as cs
from tests.unit.test_curated_mode import PRIVATE, approved_doc, base_items, commentary_item

SECRET = "zebra quartz marmalade lantern orbit velvet cinnamon harbour"      # a distinctive run in the pasted text


def run(coro):
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


def make_run():
    text = ("The reporter wrote that " + SECRET + " was how one mathematician described the mood. Another expert said the proofs need careful reading "
            "before anyone can say what they establish, and a third said the release was surprising in its scale and timing.")
    items = base_items() + [commentary_item(evidence_text=text)]
    return cm.CuratedRun.from_list_doc(approved_doc(items), private_texts=PRIVATE)


# --- 2. the section plan ---------------------------------------------------------------------------------------------------------------------
@pytest.mark.parametrize("lo,hi", [(960, 1200), (1440, 1800), (600, 700), (300, 400), (100, 140)])
def test_the_budgets_sum_to_the_target_and_any_sections_inside_their_tolerances_are_inside_the_window(lo, hi):
    plan = csr.plan_sections(lo, hi)
    assert sum(s.budget for s in plan) == csr.target_words(lo, hi)
    assert sum(s.lo for s in plan) >= lo and sum(s.hi for s in plan) <= hi          # the property: every combination of sections in tolerance is in the window
    assert all(s.lo <= s.budget <= s.hi for s in plan) and [s.key for s in plan][0] == "opening" and [s.key for s in plan][-1] == "closing"


def test_without_commentary_the_reception_section_is_dropped_and_the_budgets_still_sum():
    plan = csr.plan_sections(960, 1200, has_commentary=False)
    assert "reception" not in [s.key for s in plan] and sum(s.budget for s in plan) == 1080


def test_the_tolerance_is_never_wider_than_the_window_allows():
    assert csr.tolerance_fraction(960, 1200) <= csr.MAX_TOLERANCE
    assert csr.tolerance_fraction(100, 101) < 0.01 and csr.tolerance_fraction(0, 0) == 0.0


# --- 1. notes first ----------------------------------------------------------------------------------------------------------------------------
def commentary():
    return [{"pid": "P4", "outlet": "Example Magazine", "date": "2026-10-19", "title": "Reaction", "text": PRIVATE[make_run().items[-1]["item_id"]]}]


class NotesLLM:
    def __init__(self, replies):
        self.replies, self.calls = list(replies), []

    async def __call__(self, system, user):
        self.calls.append((system, user))
        return self.replies[min(len(self.calls) - 1, len(self.replies) - 1)]


def notes_reply(*claims):
    return json.dumps({"notes": [{"claim": c} for c in claims]})


GOOD = ["A mathematician quoted in the report described the mood among number theorists after the release as one of cautious surprise.",
        "Another expert told the reporter that nobody can say what the proofs establish until they have been read carefully."]


def test_notes_are_short_attributed_and_the_trace_never_holds_the_text():
    llm = NotesLLM([notes_reply(*GOOD)])
    notes, trace = run(csr.distill_notes(llm, commentary()))
    assert [n.pid for n in notes] == ["P4", "P4"] and notes[0].outlet == "Example Magazine" and notes[0].date == "2026-10-19"
    assert len(llm.calls) == 1 and trace == [{"stage": "notes", "pid": "P4", "attempt": 1, "violations": []}]
    assert SECRET not in json.dumps(trace) and "cautious surprise" not in json.dumps(trace)


def test_a_note_that_copies_six_words_or_says_verified_is_repaired():
    copied = "The reporter wrote that " + SECRET[:50] + " was how one mathematician described the mood."
    verified = "An expert said the first proof had been formally verified by the Lean checker in October."
    llm = NotesLLM([notes_reply(copied, verified), notes_reply(*GOOD)])
    notes, trace = run(csr.distill_notes(llm, commentary()))
    assert len(llm.calls) == 2 and [n.claim for n in notes] == GOOD
    assert trace[0]["violations"] == ["note_forbidden_term", "note_verbatim_run"] and trace[1]["violations"] == []
    assert "REJECTED" in llm.calls[1][1] and "neutral wording" in llm.calls[1][1]


def test_notes_that_cannot_be_made_to_pass_fail_closed_after_two_repairs():
    bad = notes_reply("An expert said the first proof had been formally verified by the Lean checker in October.", GOOD[1])
    llm = NotesLLM([bad])
    with pytest.raises(csr.NotesError) as e:
        run(csr.distill_notes(llm, commentary()))
    assert len(llm.calls) == csr.MAX_NOTE_REPAIRS + 1 and e.value.pid == "P4" and "note_forbidden_term" in str(e.value)


def test_the_note_count_and_length_rules():
    assert {v["kind"] for v in csr.note_violations(["Too short."], "text")} >= {"note_count", "note_length"}
    assert csr.note_violations(GOOD, "an unrelated text about something else entirely") == []
    with pytest.raises(csr.ScriptPipelineError):
        csr.parse_notes_reply("not json")


def test_the_script_prompt_carries_the_notes_and_never_the_pasted_text():
    r = make_run()
    notes = [csr.Note("P4", "Example Magazine", "2026-10-19", GOOD[0])]
    system = csr.system_prompt(r, csr.plan_sections(100, 140), notes, banned="\"remarkable\"")
    assert GOOD[0] in system and "Example Magazine, 2026-10-19" in system and SECRET not in system and "COMMENTARY EXCERPTS" not in system
    assert SECRET in r.prompt_block() and "COMMENTARY EXCERPTS" in r.prompt_block()           # the older prompt still carries excerpts
    assert SECRET not in r.prompt_block(include_excerpts=False)


# --- 4. the allowed works ------------------------------------------------------------------------------------------------------------------------
def test_the_allowed_works_list_names_every_listed_source_and_forbids_every_other_title():
    r = make_run()
    block = csr.allowed_works_block(r)
    for item in r.items:
        assert item["title"] in block
    assert "NO title" in block and "generically" in block and "ALLOWED WORKS" in csr.system_prompt(r, csr.plan_sections(100, 140), [])
    assert "Another Paper That Is Not Listed" not in block


# --- locating and keeping ----------------------------------------------------------------------------------------------------------------------
def test_a_violation_is_located_in_the_section_that_holds_its_sentence():
    sections = {"a": "HOST: Alpha beta gamma.\nEXPERT: Delta epsilon zeta eta.", "b": "HOST: Theta iota kappa lambda mu."}
    by, lost = csr.locate([{"find": "Delta epsilon zeta eta.", "kind": "k", "check": "c", "message": "m"},
                           {"find": "theta iota kappa lambda mu", "kind": "k2", "check": "c", "message": "m"},
                           {"find": None, "section": "b", "kind": "k3", "check": "c", "message": "m"},
                           {"find": "never said", "kind": "k4", "check": "c", "message": "m"}], sections)
    assert sorted(by) == ["a", "b"] and len(by["b"]) == 2 and [v["kind"] for v in lost] == ["k4"]


def test_preserved_fraction_counts_only_the_sentences_that_did_not_need_changing():
    before = "HOST: One two three four.\nEXPERT: Five six seven eight. Nine ten eleven twelve."
    viol = [{"find": "Nine ten eleven twelve."}]
    assert csr.preserved_fraction(before, "HOST: One two three four.\nEXPERT: Five six seven eight. Something new entirely here.", viol) == 1.0
    assert csr.preserved_fraction(before, "HOST: Completely different.\nEXPERT: Words all over.", viol) == 0.0
    assert csr.preserved_fraction(before, "HOST: One two three four.\nEXPERT: Words all over.", viol) == 0.5


def test_dialogue_must_be_json_with_a_speaker_on_every_line():
    assert csr.parse_dialogue(json.dumps({"dialogue": "HOST: Hello there.\nEXPERT: Hi."})) == "HOST: Hello there.\nEXPERT: Hi."
    for bad in ("nope", json.dumps({"dialogue": ""}), json.dumps({"dialogue": "HOST: ok.\nNARRATOR: no."}), json.dumps({"dialogue": "Matilda: hi"})):
        with pytest.raises(csr.SectionFormatError):
            csr.parse_dialogue(bad)


# --- 3. repair, not regenerate -----------------------------------------------------------------------------------------------------------------------
PLAN = csr.plan_sections(100, 140)          # budgets 12, 24, 30, 24, 24, 6


def section_text(section, bad=False, n=None):
    n = n or section.budget
    half = n // 2
    first = f"HOST: " + " ".join(f"{section.key}a{i}" for i in range(half - 1)) + "."
    second = f"EXPERT: " + ("BADWORD " if bad else "") + " ".join(f"{section.key}b{i}" for i in range(n - half - 1 - (1 if bad else 0))) + "."
    return first + "\n" + second


def dialogue(text):
    return json.dumps({"dialogue": text})


class PipelineLLM:
    """Writes each section from a scripted list of versions; revises by replacing every BADWORD sentence with a clean one of the same length."""

    def __init__(self, versions=None, repair="fix"):
        self.versions = versions or {}
        self.repair, self.writes, self.repairs, self.calls = repair, [], [], []

    async def __call__(self, system, user):
        self.calls.append((system, user))
        if system.startswith(csr.REPAIR_SYSTEM):
            title = user.split("SECTION: ", 1)[1].split(" (", 1)[0]
            section = next(s for s in PLAN if s.title == title)
            self.repairs.append(section.key)
            old = user.split("THE SECTION AS IT IS:\n", 1)[1]
            if self.repair == "rewrite":
                return dialogue(section_text(section, n=section.budget).replace(section.key, "zz"))
            if self.repair == "garbage":
                return "not json"
            fixed = [(ln.replace("BADWORD ", "") + "") if "BADWORD" in ln else ln for ln in old.split("\n")]
            fixed = ["EXPERT: " + " ".join(ln.replace("EXPERT: ", "").split() + ["pad"]) if "BADWORD" in old and ln.startswith("EXPERT") and i == 1 else ln
                     for i, ln in enumerate(fixed)]
            return dialogue("\n".join(fixed))
        title = user.split("WRITE SECTION: ", 1)[1].split("\n", 1)[0]
        section = next(s for s in PLAN if s.title == title)
        self.writes.append(section.key)
        vs = self.versions.get(section.key) or [section_text(section)]
        return dialogue(vs[min(self.writes.count(section.key) - 1, len(vs) - 1)])


async def checker(script):
    return [{"check": "fake", "kind": "badword", "find": s, "message": f"fix this sentence: {s}"}
            for s in cc.split_sentences(cc.dialogue_text(script)) if "BADWORD" in s]


def builder(llm, chk=checker):
    return csr.ScriptBuilder(llm, make_run(), PLAN, [csr.Note("P4", "Example Magazine", "2026-10-19", GOOD[0])], chk)


def test_a_clean_script_is_written_once_section_by_section_and_checked_once():
    llm = PipelineLLM()
    res = run(builder(llm).build())
    assert llm.writes == [s.key for s in PLAN] and llm.repairs == []
    assert csr.words_in(res.script) == sum(s.budget for s in PLAN) and 100 <= csr.words_in(res.script) <= 140
    assert [t["stage"] for t in res.trace] == ["write", "check"]


def test_a_violation_repairs_only_its_section_and_everything_else_is_kept_word_for_word():
    bad = section_text(PLAN[2], bad=True)
    llm = PipelineLLM({"claims": [bad]})
    res = run(builder(llm).build())
    assert llm.writes == [s.key for s in PLAN]                       # no section was written twice: nothing was regenerated
    assert llm.repairs == ["claims"] and "BADWORD" not in res.script
    for s in PLAN:
        if s.key != "claims":
            assert res.sections[s.key] == section_text(s)             # untouched sections are byte for byte what they were
    assert res.sections["claims"].split("\n")[0] == bad.split("\n")[0]    # and so is the sentence that passed, inside the repaired section
    assert [t["stage"] for t in res.trace] == ["write", "check", "repair", "check"] and res.trace[2]["repaired"] == ["claims"]


def test_the_repair_prompt_names_the_sentence_and_the_length_and_forbids_other_changes():
    bad = section_text(PLAN[2], bad=True)
    llm = PipelineLLM({"claims": [bad]})
    run(builder(llm).build())
    system, user = next(c for c in llm.calls if c[0].startswith(csr.REPAIR_SYSTEM))
    assert "word for word" in system and "ONLY the sentences listed" in system
    assert "PROBLEMS TO FIX" in user and "BADWORD" in user and "ALLOWED WORKS" in user and f"{PLAN[2].lo} to {PLAN[2].hi}" in user


def test_a_section_outside_its_budget_is_a_violation_and_is_repaired_for_length():
    short = section_text(PLAN[1], n=PLAN[1].lo - 6)
    v = csr.length_violation(PLAN[1], short)
    assert v["kind"] == "section_too_short" and v["section"] == "sources" and str(PLAN[1].lo) in v["message"]
    assert csr.length_violation(PLAN[1], section_text(PLAN[1])) is None
    assert csr.length_violation(PLAN[1], section_text(PLAN[1], n=PLAN[1].hi + 5))["kind"] == "section_too_long"


def test_a_length_repair_that_does_not_reach_the_budget_is_not_accepted_as_clean():
    short = section_text(PLAN[1], n=PLAN[1].lo - 6)
    llm = PipelineLLM({"sources": [short]}, repair="fix")             # the fake "fixes" only BADWORD, so the length stays wrong
    with pytest.raises(csr.ScriptRepairFailed) as e:
        run(builder(llm).build())
    assert {v["kind"] for v in e.value.violations} == {"section_too_short"}


def test_a_revision_that_rewrites_what_passed_is_refused_and_the_old_text_stays():
    bad = section_text(PLAN[2], bad=True)
    llm = PipelineLLM({"claims": [bad]}, repair="rewrite")
    b = builder(llm)
    with pytest.raises(csr.ScriptRepairFailed):
        run(b.build())
    assert llm.writes.count("claims") == 2                            # written twice in all: the first script and the one full regeneration
    repairs = [t for t in b.trace if t["stage"] == "repair"]
    assert repairs and all(t["refused"] == ["claims"] and t["repaired"] == [] for t in repairs)


def test_regeneration_in_full_happens_only_after_two_failed_repair_rounds_and_only_once():
    bad = section_text(PLAN[2], bad=True)
    llm = PipelineLLM({"claims": [bad]}, repair="garbage")
    b = builder(llm)
    with pytest.raises(csr.ScriptRepairFailed) as e:
        run(b.build())
    stages = [(t["stage"], t.get("full_attempt")) for t in b.trace]
    assert stages.count(("write", 1)) == 1 and stages.count(("write", 2)) == 1 and ("write", 3) not in stages
    assert llm.writes.count("claims") == csr.MAX_FULL_ATTEMPTS and e.value.violations[0]["kind"] == "badword"
    first = [t for t in b.trace if t.get("full_attempt") == 1]
    assert [t["stage"] for t in first] == ["write", "check", "repair"]            # one refused repair round, then nothing changed: no pointless round
    assert first[2]["refused"] == ["claims"] and first[2]["repaired"] == []


def test_a_full_regeneration_that_comes_out_clean_succeeds():
    bad = section_text(PLAN[2], bad=True)
    llm = PipelineLLM({"claims": [bad, section_text(PLAN[2])]}, repair="garbage")
    res = run(builder(llm).build())
    assert llm.writes.count("claims") == 2 and llm.writes.count("opening") == 2 and "BADWORD" not in res.script


def test_a_violation_that_cannot_be_located_does_not_start_a_pointless_second_round():
    calls = {"n": 0}

    async def lost_checker(script):
        calls["n"] += 1
        return [{"check": "fake", "kind": "lost", "find": "a sentence that is nowhere", "message": "m"}]
    llm = PipelineLLM()
    with pytest.raises(csr.ScriptRepairFailed):
        run(builder(llm, lost_checker).build())
    assert llm.repairs == [] and calls["n"] == csr.MAX_FULL_ATTEMPTS        # one check per full attempt: nothing could change between rounds


def test_a_reply_that_is_not_dialogue_is_asked_for_again_and_then_fails_closed():
    class Broken(PipelineLLM):
        async def __call__(self, system, user):
            self.calls.append((system, user))
            return "{not json"
    llm = Broken()
    with pytest.raises(csr.ScriptPipelineError) as e:
        run(builder(llm).build())
    assert len(llm.calls) == csr.MAX_WRITE_TRIES and "opening" in str(e.value)
    assert "REJECTED" in llm.calls[1][1]


# --- the checks of the assembled script as violations -------------------------------------------------------------------------------------------
def test_every_check_becomes_a_violation_the_repair_can_act_on():
    from types import SimpleNamespace as NS
    naming = NS(violations=[{"kind": "unlisted_work", "quote": "Smith (2020) showed"}, {"kind": "link_phrase_unattached", "quote": "the link below"}])
    attribution = NS(violations=[{"quote": "OpenAI proved it", "label": "P3", "reason": "not in the abstract"}])
    banned = [{"phrase": "groundbreaking", "matched": "groundbreaking", "where": "script", "sentence": "It is groundbreaking."}]
    curated = [{"kind": "forbidden_term", "term": "verified", "sentence": "It was verified."},
               {"kind": "withdrawn_not_stated", "sentence": "The Weil paper is key."},
               {"kind": "verbatim_run", "words": 9, "quote": "one two three four five six seven eight nine"},
               {"kind": "spoken_name", "sentence": "Hello, I'm Matilda."},
               {"kind": "preprint_not_labelled"}, {"kind": "company_release_not_labelled"}]
    out = csr.collect_violations(naming, attribution, ["x_{i}"], banned, ["The host reads the topic."], ["Goldbach"], curated)
    kinds = [v["kind"] for v in out]
    assert kinds == ["unlisted_work", "link_phrase_unattached", "unsupported_attribution", "unspeakable_notation", "banned_wording", "topic_read_aloud",
                     "coverage_statement_missing", "forbidden_term", "withdrawn_not_stated", "verbatim_run", "spoken_name", "preprint_not_labelled",
                     "company_release_not_labelled"]
    assert all(v["message"] for v in out) and {v["section"] for v in out if v.get("section")} == {"status", "sources"}
    assert csr.collect_violations() == []


# --- the metadata ----------------------------------------------------------------------------------------------------------------------------------
def test_metadata_is_checked_and_falls_back_to_the_code_built_description_never_to_an_unchecked_one():
    replies = [json.dumps({"title": "T one", "description": "It was verified.", "keywords": ["a"]}),
               json.dumps({"title": "T two", "description": "A plain summary.", "keywords": ["a", "b"]})]
    llm = NotesLLM(replies)
    validate = lambda t, d: ["status wording"] if "verified" in d else []
    meta, trace = run(csr.write_metadata(llm, "SCRIPT", "ALLOWED", validate, fallback_description="Fallback."))
    assert meta == {"title": "T two", "description": "A plain summary.", "keywords": ["a", "b"]} and [t["problems"] for t in trace] == [1, 0]
    assert "REJECTED" in llm.calls[1][1]
    bad = NotesLLM([json.dumps({"title": "T", "description": "It was verified."})])
    meta, trace = run(csr.write_metadata(bad, "SCRIPT", "ALLOWED", validate, fallback_description="Fallback."))
    assert meta["description"] == "Fallback." and trace[-1] == {"stage": "metadata", "fallback_description": True} and len(bad.calls) == 3
    own = NotesLLM([json.dumps({"title": "Model title", "description": "Plain."})])
    meta, _ = run(csr.write_metadata(own, "S", "A", lambda t, d: [], title_override="The producer's title"))
    assert meta["title"] == "The producer's title"
