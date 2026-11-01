"""The notes rule for quote-heavy commentary: a note may carry short quoted fragments, in quotation marks, attributed; text outside the marks follows the
script's own eight-word rule; the script keeps its own check, so a quoted fragment is for meaning only and is never reproduced."""
import asyncio
import json

import pytest

import curated_checks as cc
import curated_pipeline as cp
import curated_script as csr
from tests.unit.test_curated_pipeline import LABEL, NOTES, PLAN, TEXT, Checker, SECRET, Writer, filler, generate
from tests.unit.test_curated_script import make_run

OUTLET = "Example Magazine"
SEVEN = " ".join(SECRET.split()[:7])          # seven words of the text: below the eight-word rule when unmarked


def run(coro):
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


def violations(*claims, text=TEXT, outlet=OUTLET):
    """The kinds of violation of these claims, leaving out the count rule (a single claim is the unit under test)."""
    return [v["kind"] for v in csr.note_violations(list(claims), text, outlet) if v["kind"] != "note_count"]


QUOTE_HEAVY = [
    f"Example Magazine reported that one mathematician called the mood “{SECRET}” while others urged caution before reading the proofs.",
    "Maksym Radziwill said the proofs “need careful reading before anyone can say what they establish”, according to the reporter.",
    "A third mathematician described the release as “surprising in its scale and timing”, Example Magazine reported."]


# --- a quote-heavy fixture passes ------------------------------------------------------------------------------------------------------------
def test_a_quote_heavy_set_of_attributed_notes_passes_the_notes_step_in_one_call():
    assert violations(*QUOTE_HEAVY) == []
    calls = []

    async def llm(system, user):
        calls.append(user)
        return json.dumps({"notes": [{"claim": c} for c in QUOTE_HEAVY]})
    notes, trace = run(csr.distill_notes(llm, [{"pid": "P4", "outlet": OUTLET, "date": "2026-10-19", "title": "t", "text": TEXT}]))
    assert len(calls) == 1 and len(notes) == 3 and trace == [{"stage": "notes", "pid": "P4", "attempt": 1, "violations": [], "attributed_in_code": 0, "dropped": 0}]


def test_the_notes_prompt_asks_for_paraphrase_by_default_and_quotation_marks_whenever_exact_words_are_kept():
    system = csr.NOTES_SYSTEM.format(lo=2, hi=6, wlo=6, whi=45, n=csr.NOTE_VERBATIM_WORDS, q=csr.QUOTE_MAX_WORDS)
    assert "PARAPHRASE by default" in system and "inside quotation marks" in system and "25 words or fewer" in system and "8 or more consecutive words" in system
    assert "Never put words in quotation marks that are not in the text" in system and "attribute it" in system


def test_a_note_may_say_what_a_quotation_says_even_in_the_forbidden_words_if_it_is_marked_and_attributed():
    claim = "Example Magazine reported that an expert said the first version was “formally verified in Lean”, which the magazine did not check itself."
    assert "formally verified" not in cc.dialogue_text(csr.split_quotes(claim)[0]) and violations(claim, text=TEXT + " formally verified in Lean") == []
    unmarked = "Example Magazine reported that an expert said the first version was formally verified in Lean."
    assert violations(unmarked) == ["note_forbidden_term"]


# --- unmarked overlap fails; marked overlap does not ------------------------------------------------------------------------------------------
def test_an_unmarked_run_of_eight_words_fails_and_seven_words_do_not():
    eight = f"The writer noted that {SECRET} captured the mood among number theorists."
    seven = f"The writer noted {SEVEN} captured the mood among number theorists."
    assert violations(eight) == ["note_verbatim_run"] and violations(seven) == []
    message = next(v["message"] for v in csr.note_violations([eight], TEXT, OUTLET) if v["kind"] == "note_verbatim_run")
    assert "outside quotation marks" in message and "at most 25" in message


def test_the_same_eight_words_inside_quotation_marks_with_an_attribution_pass():
    marked = f"The writer noted that “{SECRET}” captured the mood among number theorists."
    assert violations(marked, outlet="Another Outlet") == ["note_quote_unattributed"]
    assert violations("Example Magazine said that " + marked.split("noted that ", 1)[1]) == []


# --- the other rules of a quotation -------------------------------------------------------------------------------------------------------------------
def test_only_a_named_source_attributes_a_quotation():
    quoted = f"“{SECRET}”"
    for unnamed in (f"An expert said {quoted} about the mood.", f"The mood was {quoted}, the magazine reported.", f"The mood was {quoted}, according to the reporter."):
        assert violations(unnamed, outlet="Another Outlet") == ["note_quote_unattributed"], unnamed
    for named in (f"Radziwill said {quoted} about the mood.", f"The mood was {quoted}, according to Quanta.", f"Quanta reported {quoted} as the mood.",
                  f"Scientific American said the mood was {quoted}.", f"The mood was {quoted}, Example Magazine wrote."):
        assert violations(named, outlet="Another Outlet") == [], named


def test_an_unattributed_quotation_fails():
    claim = f"The general mood was summed up as “{SECRET}” in many circles today."
    assert violations(claim, outlet="Another Outlet") == ["note_quote_unattributed"]
    assert violations(claim, outlet=OUTLET) == ["note_quote_unattributed"]            # no outlet and no named source in the note
    assert violations(claim.replace("The general mood was summed up as", "Radziwill said the mood was"), outlet="") == []
    assert violations(claim.replace("The general mood", "Example Magazine says the mood"), outlet=OUTLET) == []


def test_a_quotation_over_twenty_five_words_fails_and_so_does_one_that_is_not_in_the_text():
    long_text = " ".join(f"w{i}" for i in range(30))
    long_claim = f"Example Magazine reported that the writer said “{long_text}” about the release overall."
    assert "note_quote_too_long" in violations(long_claim, text=TEXT + " " + long_text)
    invented = "Example Magazine reported that an expert said “this exact sentence was never printed anywhere” about the release."
    assert violations(invented) == ["note_quote_not_in_text"]
    assert violations("Example Magazine reported that an expert said “the proofs need careful reading before anyone can say what they establish.") == ["note_quote_unbalanced"] \
        or "note_quote_unbalanced" in violations("Example Magazine reported that an expert said “the proofs need careful reading before anyone can say what they establish.")


def test_straight_quotation_marks_count_too():
    claim = f'Example Magazine reported that one mathematician called the mood "{SECRET}" while others urged caution before reading.'
    assert violations(claim) == []
    assert violations(claim.replace(SECRET, "words that the text never contained at all anywhere")) == ["note_quote_not_in_text"]


def test_a_notes_failure_returns_the_kinds_and_never_the_draft_notes():
    bad = f"The writer noted that {SECRET} captured the mood among number theorists."

    async def llm(system, user):
        return json.dumps({"notes": [{"claim": bad}, {"claim": NOTES[1]["claim"]}]})
    with pytest.raises(csr.NotesError) as e:
        run(csr.distill_notes(llm, [{"pid": "P4", "outlet": OUTLET, "date": "d", "title": "t", "text": TEXT}]))
    shown = json.dumps(e.value.violations) + str(e.value)
    assert SECRET not in shown and "captured the mood" not in shown and e.value.violations[0]["kind"] == "note_verbatim_run" and e.value.violations[0]["find"] is None


# --- the script keeps its own check ---------------------------------------------------------------------------------------------------------------------
def test_the_script_notes_say_that_quoted_fragments_are_for_meaning_only():
    block = csr.notes_block([csr.Note("P4", OUTLET, "2026-10-19", QUOTE_HEAVY[0])])
    assert "for its MEANING only" in block and "Paraphrase it" in block and "Never reproduce it in the script" in block and SECRET in block


def test_a_script_that_reproduces_a_quoted_fragment_still_fails_the_script_check():
    r = make_run()
    script = f"HOST: What did people say?\nEXPERT: One mathematician called the mood {SECRET} after the release."
    v = [x for x in r.checks(script) if x["kind"] == "verbatim_run"]
    assert v and v[0]["words"] >= 8
    paraphrase = "HOST: What did people say?\nEXPERT: One mathematician described a cautious, curious mood after the release."
    assert [x for x in r.checks(paraphrase) if x["kind"] == "verbatim_run"] == []


def test_in_the_pipeline_a_quote_that_passed_the_notes_is_repaired_out_of_the_script():
    notes = [{"claim": QUOTE_HEAVY[0]}, {"claim": NOTES[1]["claim"]}]
    bad = {"reception": filler(PLAN[4], line="EXPERT: " + SECRET + " and so on."), "sources": LABEL}
    writer = Writer(bad)
    gen, writer, _ = generate(writer, Checker(notes=notes))
    assert sorted(set(writer.repairs)) == ["reception"] and SECRET not in gen.content["script"]
    assert any(r["check"] == "verbatim_run" for r in gen.rejections) and [n["claim"] for n in gen.notes][0] == QUOTE_HEAVY[0]


def test_the_repair_names_the_failing_notes_and_the_shared_words_and_asks_for_the_others_back_unchanged():
    bad = f"Example Magazine noted that {SECRET} captured the mood among number theorists."
    good = QUOTE_HEAVY[1]
    calls = []

    async def llm(system, user):
        calls.append(user)
        return json.dumps({"notes": [{"claim": bad}, {"claim": good}]}) if len(calls) == 1 else json.dumps({"notes": [{"claim": QUOTE_HEAVY[0]}, {"claim": good}]})
    notes, trace = run(csr.distill_notes(llm, [{"pid": "P4", "outlet": OUTLET, "date": "d", "title": "t", "text": TEXT}]))
    assert len(calls) == 2 and trace[0]["violations"] == ["note_verbatim_run"] and trace[1]["violations"] == []
    second = calls[1]
    assert "1. " + bad in second and "2. " + good in second                                # the previous notes, numbered
    assert "note 1:" in second and "note 2:" not in second                                 # only the failing note is named
    assert SECRET in second and "copy every other note exactly as it is" in second          # the shared words are shown to the model (and only to the model)
    assert csr.NOTES_SYSTEM.count("Begin every note by naming its source") == 1


# --- what the code does so that a note's rule is never a reason to fail when a note can simply be fixed or left out ---------------------------------
def text_item():
    return [{"pid": "P4", "outlet": OUTLET, "date": "d", "title": "t", "text": TEXT}]


def test_a_quotation_with_no_named_source_is_attributed_to_the_outlet_in_code():
    unnamed = f"The general mood was summed up as \u201c{SECRET}\u201d in many circles today."
    fixed, changed = csr.ensure_attribution(unnamed, OUTLET)
    assert changed and fixed.startswith("According to Example Magazine, the general mood") and violations(fixed) == []
    assert csr.ensure_attribution(QUOTE_HEAVY[0], OUTLET) == (QUOTE_HEAVY[0], False)               # already attributed: untouched
    assert csr.ensure_attribution("A paraphrase with no quotation marks at all.", OUTLET) == ("A paraphrase with no quotation marks at all.", False)
    assert csr.ensure_attribution(unnamed, "") == (unnamed, False)

    async def llm(system, user):
        return json.dumps({"notes": [{"claim": unnamed}, {"claim": NOTES[1]["claim"]}]})
    notes, trace = run(csr.distill_notes(llm, text_item()))
    assert len(notes) == 2 and notes[0].claim.startswith("According to Example Magazine,") and trace[0]["attributed_in_code"] == 1 and trace[0]["violations"] == []


def test_on_the_last_attempt_a_note_that_still_breaks_a_rule_is_dropped_if_enough_notes_remain():
    bad = f"The writer noted that {SECRET} captured the mood among number theorists."
    replies = [json.dumps({"notes": [{"claim": bad}, {"claim": NOTES[0]["claim"]}, {"claim": NOTES[1]["claim"]}]})]
    calls = []

    async def llm(system, user):
        calls.append(user)
        return replies[0]
    notes, trace = run(csr.distill_notes(llm, text_item()))
    assert len(calls) == csr.MAX_NOTE_REPAIRS + 1 and [n.claim for n in notes] == [NOTES[0]["claim"], NOTES[1]["claim"]]
    assert [t["violations"] for t in trace] == [["note_verbatim_run"], ["note_verbatim_run"], []] and trace[-1]["dropped"] == 1


def test_a_note_is_never_dropped_when_that_leaves_fewer_than_two_or_when_the_problem_is_not_one_note():
    bad = f"The writer noted that {SECRET} captured the mood among number theorists."

    async def two(system, user):
        return json.dumps({"notes": [{"claim": bad}, {"claim": NOTES[1]["claim"]}]})
    with pytest.raises(csr.NotesError):
        run(csr.distill_notes(two, text_item()))

    async def count(system, user):
        return json.dumps({"notes": [{"claim": NOTES[0]["claim"]}]})                     # one note: the count rule belongs to no note
    with pytest.raises(csr.NotesError) as e:
        run(csr.distill_notes(count, text_item()))
    assert e.value.violations[0]["kind"] == "note_count"


def test_dropped_and_attributed_counts_never_carry_text():
    bad = f"The writer noted that {SECRET} captured the mood among number theorists."

    async def llm(system, user):
        return json.dumps({"notes": [{"claim": bad}, {"claim": NOTES[0]["claim"]}, {"claim": NOTES[1]["claim"]}]})
    _, trace = run(csr.distill_notes(llm, text_item()))
    assert SECRET not in json.dumps(trace) and set(trace[0]) == {"stage", "pid", "attempt", "violations", "attributed_in_code", "dropped"}
