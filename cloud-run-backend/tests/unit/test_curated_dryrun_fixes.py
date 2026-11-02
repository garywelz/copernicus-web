"""The fixes after the first real dry runs of episode 1: speakable titles and abstracts, the narrow naming exemption for reporting attributions, the
total-length rule with explicit repairs, full diagnostics on failure, and the withdrawn-paper instruction. Offline: every model call is a scripted fake."""
import json
import sys
from unittest.mock import MagicMock

import pytest

try:
    import psutil  # noqa: F401
except ImportError:
    sys.modules["psutil"] = MagicMock()

import curated_mode as cm
import curated_pipeline as cp
import curated_script as csr
import curated_sources as cs
from speakable import speakable, speak_math
from speech_text import find_unspeakable
from tests.unit.test_curated_mode import PRIVATE, approved_doc, base_items, commentary_item, release_item
from tests.unit.test_curated_pipeline import (LABEL, NOTES, PLAN, REQUEST, SECRET, TEXT, Checker, Writer, context, filler, generate, run)

LATEX_TITLE = "The Quasi-Riemann Hypothesis: A Zero-Free Half-Plane $`\\Re s\\gt 7/8`$"
LATEX_ABSTRACT = ("We prove that all finite-order Hecke L-functions over $`\\mathbb Q(\\sqrt{-3})`$ and all Dirichlet L-functions are zero-free in the "
                  "half-plane $`\\Re s\\gt 7/8`$, with the principal pole at s = 1 allowed.")


# --- 1. titles and abstracts in speakable form --------------------------------------------------------------------------------------------------
def test_latex_in_a_title_or_an_abstract_becomes_words():
    assert speakable(LATEX_TITLE) == "The Quasi-Riemann Hypothesis: A Zero-Free Half-Plane real part of s greater than 7 over 8"
    spoken = speakable(LATEX_ABSTRACT)
    assert "Q(square root of minus 3)" in spoken and "real part of s greater than 7 over 8" in spoken and "s = 1" in spoken
    for text in (LATEX_TITLE, LATEX_ABSTRACT):
        out = speakable(text)
        assert find_unspeakable(out) == [] and not any(ch in out for ch in "$`\\")


def test_text_without_mathematics_is_returned_unchanged_and_the_pieces_work():
    assert speakable("A plain title: 7/8 of the zeros.") == "A plain title: 7/8 of the zeros." and speakable("") == "" and speakable(None) == ""
    assert speak_math("x^2") == "x squared" and speak_math("x^{n+1}") == "x to the n+1" and speak_math("a_n") == "a sub n"
    assert speak_math("\\frac{1}{2}") == "1 over 2" and speak_math("\\sqrt[3]{x}") == "3-th root of x" and speak_math("\\alpha \\to \\infty") == "alpha to infinity"
    assert "$" not in speakable("The bound $x\\le y$ and $$z\\ge 1$$ hold.")


def curated_run_with_latex():
    items = [release_item(title=LATEX_TITLE, evidence_text=LATEX_ABSTRACT)] + base_items()[:2] + [commentary_item(evidence_text=TEXT)]
    return cm.CuratedRun.from_list_doc(approved_doc(items), private_texts=PRIVATE)


def test_no_prompt_carries_latex_and_the_prompt_says_titles_are_spoken_in_words():
    r = curated_run_with_latex()
    notes = [csr.Note("P4", "Example Magazine", "2026-10-19", NOTES[0]["claim"])]
    system = csr.system_prompt(r, csr.plan_sections(100, 140), notes)
    for bad in ("$`", "\\Re", "\\gt", "\\mathbb"):
        assert bad not in system and bad not in r.prompt_block(include_excerpts=False)
    assert "real part of s greater than 7 over 8" in system and "SPOKEN IN WORDS" in csr.allowed_works_block(r) and "never with symbols, LaTeX" in csr.allowed_works_block(r)
    assert "square root of minus 3" in csr.facts_block(r)


def test_the_script_checks_still_know_the_raw_title():
    r = curated_run_with_latex()
    assert r.results()[0]["title"] == LATEX_TITLE                                   # the stored title is untouched: only what the model reads is converted


# --- 2. the narrow naming exemption ------------------------------------------------------------------------------------------------------------------
REPORTING = csr._norm("Example Magazine A. Reporter Maksym Radziwill said the proofs need careful reading Hector Pasten told Nature")


def flag(**kw):
    base = {"kind": "unlisted_work", "where": "script", "quote": "Maksym Radziwill said the proofs need careful reading", "authors": ["Radziwill"], "year": None,
            "title_words": []}
    base.update(kw)
    return base


def test_a_name_used_as_a_reporting_attribution_is_exempt_only_when_it_is_recorded_on_the_list_or_in_the_notes():
    assert csr.is_reporting_attribution(flag(), REPORTING)                                                                    # a person named in the notes
    assert csr.is_reporting_attribution(flag(quote="Example Magazine reported that the release was large", authors=["Example Magazine"]), REPORTING)   # an outlet on the list
    assert csr.is_reporting_attribution(flag(quote="according to Hector Pasten, the proofs matter", authors=["Pasten"], where="description"), REPORTING)
    assert not csr.is_reporting_attribution(flag(authors=["Quimby"], quote="Pat Quimby said the release was big"), REPORTING)              # not named anywhere
    assert not csr.is_reporting_attribution(flag(authors=["Radziwill", "Quimby"]), REPORTING)                                                  # one unknown name spoils it


def test_a_title_a_year_et_al_or_no_reporting_verb_keeps_the_flag():
    assert not csr.is_reporting_attribution(flag(title_words=["Quasi", "Riemann"]), REPORTING)                                                # a title attached
    assert not csr.is_reporting_attribution(flag(year=2021, quote="Radziwill said in 2021 the proofs matter"), REPORTING)                     # an author-year citation
    assert not csr.is_reporting_attribution(flag(quote="Radziwill et al. said the proofs matter"), REPORTING)                                 # et al.
    assert not csr.is_reporting_attribution(flag(authors=["Radziwill et al."]), REPORTING)
    assert not csr.is_reporting_attribution(flag(quote="the paper by Radziwill on the proofs"), REPORTING)                                    # not used as a reporting attribution
    assert not csr.is_reporting_attribution(flag(kind="link_phrase_unattached"), REPORTING) and not csr.is_reporting_attribution(flag(authors=[]), REPORTING)
    assert not csr.is_reporting_attribution(flag(where="topic"), REPORTING)


def test_the_exemption_splits_a_naming_result_and_reports_what_it_took_out():
    kept, exempt = csr.exempt_reporting_attributions([flag(), flag(authors=["Quimby"], quote="Pat Quimby said it"), flag(year=2020)], REPORTING)
    assert len(kept) == 2 and len(exempt) == 1 and exempt[0]["authors"] == ["Radziwill"]


def test_reporting_text_is_built_from_the_commentary_on_the_list_and_the_approved_notes_only():
    r = cm.CuratedRun.from_list_doc(approved_doc(base_items() + [commentary_item(evidence_text=TEXT)]), private_texts=PRIVATE)
    text = csr.reporting_text(r, [csr.Note("P4", "Example Magazine", "2026-10-19", "Maksym Radziwill said the proofs need careful reading before anyone judges them.")])
    words = set(text.split())
    assert {"example", "magazine", "reporter", "maksym", "radziwill"} <= words and "marie" not in words and "curie" not in words     # a peer-reviewed paper's authors are not in it
    assert SECRET.split()[0] not in words                                                                                           # and neither is the pasted text


class MentionChecker(Checker):
    """The JSON model, extracting a named mention from the script when it contains the marker."""

    def __init__(self, marker, mention, **kw):
        super().__init__(**kw)
        self.marker, self.mention = marker, mention

    async def __call__(self, system, user):
        if "TEXT (script)" in user and self.marker in user and not system.startswith("You turn ONE"):
            self.calls.append((system, user))
            return json.dumps({"mentions": [self.mention]})
        return await super().__call__(system, user)


NAMED_NOTES = [{"claim": "Maksym Radziwill said the proofs deserve slow and careful study before any firm conclusion is drawn."}, NOTES[1]]


def test_in_the_pipeline_a_named_expert_attributed_by_reporting_does_not_fail_the_naming_check():
    line = "EXPERT: Maksym Radziwill said the proofs need careful reading."
    mention = {"quote": "Maksym Radziwill said the proofs need careful reading", "authors": ["Radziwill"], "year": None, "title_words": []}
    gen, writer, _ = generate(Writer({"reaction": filler(PLAN[3], line=line), "claims": LABEL}), MentionChecker("Maksym Radziwill", mention, notes=NAMED_NOTES))
    assert writer.repairs == [] and gen.naming_result.passed and gen.naming_attempts[0]["naming_reporting_attributions_exempt"] == 1
    assert "Maksym Radziwill said" in gen.content["script"]


def test_in_the_pipeline_a_person_named_nowhere_is_still_an_unlisted_work_and_is_repaired_out():
    class Fixing(Writer):
        async def __call__(self, system, user):
            if system.startswith(csr.REPAIR_SYSTEM):
                title = user.split("SECTION: ", 1)[1].split(" (", 1)[0]
                section = next(s for s in PLAN if s.title == title)
                self.repairs.append(section.key)
                old = user.split("THE SECTION AS IT IS:\n", 1)[1].split("\n")
                fixed = ["EXPERT: " + " ".join(f"{section.key}z{i}" for i in range(len(ln.split()) - 1)) + "." if "Pat Quimby" in ln else ln for ln in old]
                return json.dumps({"dialogue": "\n".join(fixed)})
            return await super().__call__(system, user)
    mention = {"quote": "Pat Quimby said the release was big", "authors": ["Quimby"], "year": None, "title_words": []}
    gen, writer, _ = generate(Fixing({"reaction": filler(PLAN[3], line="EXPERT: Pat Quimby said the release was big."), "claims": LABEL}),
                              MentionChecker("Pat Quimby", mention, notes=NAMED_NOTES))
    assert writer.repairs == ["reaction"] and "Pat Quimby" not in gen.content["script"] and any(r["check"] == "naming" for r in gen.rejections)
    assert gen.naming_attempts[0]["violations"] and gen.naming_attempts[1]["violations"] == []


def test_a_title_or_a_year_in_a_mention_is_never_exempt_in_the_pipeline():
    class Stubborn(Writer):
        async def __call__(self, system, user):
            if system.startswith(csr.REPAIR_SYSTEM):
                self.calls.append((system, user))
                return "not json"
            return await super().__call__(system, user)
    mention = {"quote": "Maksym Radziwill said in his 2021 paper that the proofs need careful reading", "authors": ["Radziwill"], "year": 2021, "title_words": []}
    with pytest.raises(csr.ScriptRepairFailed) as e:
        generate(Stubborn({"reaction": filler(PLAN[3], line="EXPERT: Maksym Radziwill said in his 2021 paper that the proofs need careful reading."), "claims": LABEL}),
                 MentionChecker("Maksym Radziwill", mention, notes=NAMED_NOTES))
    assert {v["kind"] for v in e.value.violations} == {"unlisted_work"}


def test_the_final_text_check_applies_the_same_exemption_in_the_curated_mode_only(monkeypatch):
    import services.podcast_generation_service as svc
    from named_work_check import NamingViolationError
    mention = {"quote": "Maksym Radziwill said the proofs need careful reading", "authors": ["Radziwill"], "year": None, "title_words": []}

    async def llm(system, user):
        if "PAPERS:" in user and "SCRIPT:" in user:
            return json.dumps({"attributions": []})
        return json.dumps({"mentions": [mention]})
    monkeypatch.setattr(svc, "make_gemini_llm_call", lambda key: llm)

    async def no_sleep(*a, **k):
        return None
    monkeypatch.setattr(svc.asyncio, "sleep", no_sleep)
    service = svc.PodcastGenerationService()
    req = REQUEST.__class__(topic="t", duration="1-2 minutes")
    script = "HOST: " + " ".join(["word"] * 150) + " Maksym Radziwill said the proofs need careful reading."
    content = {"title": "T", "script": script, "description": "Body.", "papers_named": []}
    ctx = context()
    ctx.curated.reporting_text = REPORTING
    run(service._verify_final_text(dict(content), req, ctx, "k", "job-a"))                       # exempt: passes
    ctx.curated.reporting_text = csr._norm("Example Magazine")
    with pytest.raises(NamingViolationError):
        run(service._verify_final_text(dict(content), req, ctx, "k", "job-b"))                   # the name is not recorded: still a violation
    plain = context()
    plain.curated = None
    with pytest.raises(NamingViolationError):
        run(service._verify_final_text(dict(content), req, plain, "k", "job-c"))                 # the ordinary mode is untouched


def test_the_naming_check_now_reports_the_title_words_of_a_mention():
    import named_work_check as nwc
    mention = {"quote": "Pat Quimby's “A Title Of Note”", "authors": ["Quimby"], "year": None, "title_words": ["Title", "Note"], "where": "script"}

    async def llm(system, user):
        return json.dumps({"mentions": [{"quote": mention["quote"], "authors": ["Quimby"], "year": None, "title_words": ["Title", "Note"]}]})
    result = run(nwc.check_naming("Pat Quimby wrote A Title Of Note.", "", [], llm))
    assert result.violations and result.violations[0]["title_words"] == ["Title", "Note"]


# --- 4. a failed run says what happened ----------------------------------------------------------------------------------------------------------------------
def test_a_failed_run_carries_the_calls_the_rounds_the_section_words_and_every_check():
    class Stubborn(Writer):
        async def __call__(self, system, user):
            if system.startswith(csr.REPAIR_SYSTEM):
                self.calls.append((system, user))
                return "not json"
            return await super().__call__(system, user)
    bad = {"trust": filler(PLAN[2], line="EXPERT: The Exponential Time Hypothesis is False was formally verified in Lean."), "claims": LABEL}
    with pytest.raises(csr.ScriptRepairFailed) as e:
        generate(Stubborn(bad))
    d = e.value.diagnostics
    assert d["model_calls"]["notes"] == 1 and d["model_calls"]["section_writer"] >= 2 * len(PLAN) and d["model_calls"]["checks"] >= 2 and d["model_calls"]["metadata"] == 0
    assert d["model_calls_total"] == sum(d["model_calls"].values())
    stages = [(t["stage"], t.get("full_attempt")) for t in d["trace"]]
    assert ("write", 1) in stages and ("write", 2) in stages and any(t["stage"] == "repair" for t in d["trace"]) and any(t["stage"] == "notes" for t in d["trace"])
    assert d["section_words"]["trust"]["budget"] == PLAN[2].budget and set(d["section_words"]["trust"]) == {"words", "budget", "lo", "hi"}
    assert d["checks"] and d["checks"][0]["curated_checks"] and [p["key"] for p in d["plan"]] == [s.key for s in PLAN]
    assert SECRET not in json.dumps(d) and "Maksym" not in json.dumps(d)


def test_a_failed_notes_step_carries_its_trace_without_the_notes():
    with pytest.raises(csr.NotesError) as e:
        generate(Writer(), Checker(notes=[{"claim": "Too short."}]))
    d = e.value.diagnostics
    assert d["model_calls"]["notes"] == csr.MAX_NOTE_REPAIRS + 1 and d["model_calls"]["section_writer"] == 0 and d["trace"][0]["stage"] == "notes" and d["trace"][0]["failed"]
    assert d["section_words"] == {} and "Too short" not in json.dumps(d)


def test_a_successful_run_counts_its_model_calls():
    gen, writer, checker = generate()
    assert gen.model_calls["section_writer"] == len(PLAN) and gen.model_calls["notes"] == 1 and gen.model_calls["metadata"] == 1 and gen.model_calls["checks"] >= 2
    assert sum(gen.model_calls.values()) == len(writer.calls) + len(checker.calls)


# --- 5. the withdrawn-paper instruction ------------------------------------------------------------------------------------------------------------------------
def test_the_trust_section_says_a_withdrawn_paper_is_never_named_without_the_word():
    goals = {t[0]: t[3] for t in csr.SECTION_TEMPLATES}
    assert 'NEVER named' in goals["trust"] and '"withdrawn" in the same sentence' in goals["trust"]
    system = csr.system_prompt(cm.CuratedRun.from_list_doc(approved_doc(base_items() + [release_item(title="A withdrawn paper", path="preprints/A-Withdrawn-Paper-September-1-2026", status="withdrawn")]), private_texts=PRIVATE),
                               csr.plan_sections(100, 140), [])
    assert "Every sentence that mentions a WITHDRAWN manuscript must say it was withdrawn" in system
