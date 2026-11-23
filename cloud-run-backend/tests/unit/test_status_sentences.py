"""Each source's status, once, in the sentence the code wrote.

The model was given the wording as a constraint and reproduced it loosely and often twice. One episode said "A company release has not been
peer reviewed. OpenAI's own manuscript, not independently checked, is titled ..." where one sentence would do; another said the same thing
three times about the same manuscript; a third attached the wording to the wrong manuscript. All of it passed, because the checks asked only
that forbidden terms were absent.

The sentence is now built from the item's record - class, company, Lean entry, withdrawal notice - and the script must carry it, per source,
exactly once. Nothing here calls a model, so the verdict on a script never moves.
"""
import curated_checks as cc
import curated_sources as cs
import pytest
import status_sentences as ss


def item(item_id, klass, title, **kw):
    d = {"item_id": item_id, "class": klass, "title": title, "authors": kw.get("authors", ["OpenAI"]), "year": 2026,
         "identifiers": {}, "url": "", "evidence_text": "", "venue": kw.get("venue"), "status_basis": kw.get("basis", {})}
    d.update({k: v for k, v in kw.items() if k not in ("authors", "venue", "basis")})
    return d


class FakeRun:
    def __init__(self, items):
        self.items = items
        self.pids = {i["item_id"]: f"P{n}" for n, i in enumerate(items, start=1)}

    def status_of(self, i):
        basis = i.get("status_basis") or {}
        if basis.get("withdrawal"):
            return cc.STATUS_WITHDRAWN
        if basis.get("in_lean_catalogue"):
            return cc.STATUS_HAS_LEAN
        return cc.STATUS_UNVERIFIED

    def results(self):
        return [{"pid": self.pids[i["item_id"]], "item_id": i["item_id"], "class": i["class"], "title": i.get("title"),
                 "authors": i.get("authors"), "year": i.get("year"), "status": self.status_of(i)} for i in self.items]


PLAIN = item("i1", cs.COMPANY_RELEASE, "The irrationality exponent of pi is 2")
WITH_LEAN = item("i2", cs.COMPANY_RELEASE, "A Counterexample to the Group-Ring Determinant Conjecture",
                 basis={"in_lean_catalogue": True})
WITHDRAWN = item("i3", cs.COMPANY_RELEASE, "A withdrawn manuscript",
                 basis={"withdrawal": {"withdrawn_on": "2026-10-12", "explanation": "a sign error"}})
PREPRINT = item("i4", cs.PREPRINT, "Spin systems on Bethe lattices", authors=["Will Perkins"])
JOURNAL = item("i5", cs.PEER_REVIEWED, "De novo design of cysteine proteases", authors=["A Lab"], venue="Nature")
COMMENTARY = item("i6", cs.COMMENTARY, "A blog post about the claim")


def script_of(*sentences):
    return "\n".join(f"EXPERT: {s}" for s in sentences)


# --- the sentence comes from the record ---------------------------------------------------------------------------------------------
def test_each_warning_status_gets_its_own_clause():
    run = FakeRun([PLAIN, WITH_LEAN, WITHDRAWN, PREPRINT, JOURNAL])
    got = {r["pid"]: r["clause"] for r in ss.required(run)}
    assert got["P1"] == "has not been peer reviewed or independently checked"
    assert got["P2"] == ("has not been peer reviewed, and OpenAI's catalogue lists a Lean formalization for it with its review status "
                         "unchecked")
    assert got["P3"] == "withdrawn by OpenAI on 2026-10-12"
    assert got["P4"] == "a preprint, so it has not been peer reviewed"
    assert "P5" not in got, "a peer-reviewed paper needs no status sentence of its own"


def test_the_clause_also_reads_as_a_sentence_on_its_own():
    assert ss.sentence_for(PLAIN, cc.STATUS_UNVERIFIED) == \
        "“The irrationality exponent of pi is 2” has not been peer reviewed or independently checked."
    assert ss.sentence_for(PREPRINT, cc.STATUS_UNVERIFIED) == \
        "“Spin systems on Bethe lattices” is a preprint, so it has not been peer reviewed."
    assert ss.sentence_for(WITHDRAWN, cc.STATUS_WITHDRAWN) == \
        "“A withdrawn manuscript” was withdrawn by OpenAI on 2026-10-12."


def test_commentary_and_peer_review_are_given_no_status_sentence():
    """A journal paper's status is the ordinary case, and four of them in a row produced four stilted lines."""
    assert ss.sentence_for(COMMENTARY, cc.STATUS_UNVERIFIED) is None
    assert ss.sentence_for(JOURNAL, cc.STATUS_UNVERIFIED) is None
    assert ss.required(FakeRun([COMMENTARY, JOURNAL])) == []


def test_another_company_is_named_as_itself():
    other = item("i7", cs.COMPANY_RELEASE, "A release", authors=["Anthropic"], company="Anthropic",
                 basis={"in_lean_catalogue": True})
    assert "Anthropic's catalogue" in ss.clause_for(other, cc.STATUS_HAS_LEAN)


def test_a_withdrawal_with_no_date_on_record_says_no_date():
    nodate = item("i8", cs.COMPANY_RELEASE, "A withdrawn manuscript", basis={"withdrawal": {"explanation": "x"}})
    assert ss.clause_for(nodate, cc.STATUS_WITHDRAWN) == "withdrawn by OpenAI"


def test_the_clause_may_sit_inside_the_sentence_that_introduces_the_claim():
    """The form the published episodes use, and the reason containment replaced whole-sentence equality."""
    run = FakeRun([PLAIN])
    integrated = ('OpenAI\'s manuscript "The irrationality exponent of pi is 2", which has not been peer reviewed or independently '
                  'checked, claims to prove that the exponent is two.')
    assert ss.check(script_of("An opening.", integrated), run) == []


def test_the_words_themselves_may_not_be_changed():
    run = FakeRun([PLAIN])
    reworded = 'OpenAI\'s manuscript "The irrationality exponent of pi is 2" has not been peer reviewed nor checked independently.'
    kinds = [x["kind"] for x in ss.check(script_of(reworded), run)]
    assert "status_not_stated" in kinds and "status_in_other_words" in kinds, kinds


def test_a_sentence_is_charged_to_the_source_it_names_not_a_sibling():
    """Two titles in a family share most of their words, and both answer to `cc.mentions`; a sentence about one was charged to the other."""
    evo1 = item("e1", cs.PEER_REVIEWED, "Sequence modeling and design from molecular to genome scale with Evo", venue="Science")
    evo2 = item("e2", cs.PREPRINT, "Genome modeling and design across all domains of life with Evo 2")
    run = FakeRun([evo1, evo2])
    said = 'The peer-reviewed paper "Sequence modeling and design from molecular to genome scale with Evo" has not been retracted.'
    charged = [x["pid"] for x in ss.check(script_of(said, ss.required(run)[0]["sentence"]), run)]
    assert charged == [], charged


# --- stated once, in those words ----------------------------------------------------------------------------------------------------
def test_the_right_sentence_once_passes():
    run = FakeRun([PLAIN])
    assert ss.check(script_of("Here is the topic.", ss.required(run)[0]["sentence"], "And here is what it claims."), run) == []


def test_straight_quotes_and_rewrapping_do_not_matter():
    run = FakeRun([PLAIN])
    said = ss.required(run)[0]["sentence"].replace("“", '"').replace("”", '"')
    assert ss.check(script_of(f"  {said}  "), run) == []


def test_a_status_never_stated_is_refused_with_the_sentence_to_use():
    run = FakeRun([PLAIN])
    v = ss.check(script_of("The manuscript claims a proof."), run)
    assert [x["kind"] for x in v] == ["status_not_stated"]
    assert ss.required(run)[0]["sentence"] in v[0]["message"]


def test_the_same_status_twice_is_refused():
    run = FakeRun([PLAIN])
    s = ss.required(run)[0]["sentence"]
    v = ss.check(script_of(s, "A sentence between.", s), run)
    assert [x["kind"] for x in v] == ["status_stated_twice"]
    assert "stated 2 times" in v[0]["message"]


def test_the_same_standing_in_other_words_is_refused():
    """What the model used to write beside the required sentence."""
    run = FakeRun([PLAIN])
    s = ss.required(run)[0]["sentence"]
    v = ss.check(script_of(s, "The irrationality exponent of pi is 2 has not been peer reviewed."), run)
    assert [x["kind"] for x in v] == ["status_in_other_words"]


def test_a_sentence_about_the_source_that_makes_no_status_claim_is_left_alone():
    run = FakeRun([PLAIN])
    s = ss.required(run)[0]["sentence"]
    ok = script_of(s, "The irrationality exponent of pi is 2 states that the exponent is exactly two.")
    assert ss.check(ok, run) == []


def test_a_status_claim_about_a_source_it_does_not_name_is_not_charged_to_that_source():
    """Only a sentence that names the source is its status sentence; a general remark is governed by the other checks."""
    run = FakeRun([PLAIN])
    s = ss.required(run)[0]["sentence"]
    assert ss.check(script_of(s, "A company release has not been peer reviewed."), run) == []


def test_every_source_needs_its_own_sentence():
    run = FakeRun([PLAIN, PREPRINT])
    v = ss.check(script_of(ss.required(run)[0]["sentence"]), run)
    assert [x["kind"] for x in v] == ["status_not_stated"]
    assert v[0]["pid"] == "P2"


# --- the same script, the same verdict ----------------------------------------------------------------------------------------------
def test_the_same_script_gets_the_same_verdict_twice():
    """The old wording came from a model and moved between runs: on 2026-11-23 the same three sentences passed a dry run and failed the
    voicing forty minutes later. This check takes no model, so it cannot do that."""
    run = FakeRun([PLAIN, WITH_LEAN, PREPRINT])
    script = script_of("An opening.", ss.required(run)[0]["sentence"], "A middle.",
                       "The Group-Ring Determinant Conjecture has not been independently checked.",
                       ss.required(run)[2]["sentence"], ss.required(run)[2]["sentence"])
    first = ss.check(script, run)
    second = ss.check(script, FakeRun([PLAIN, WITH_LEAN, PREPRINT]))
    assert first == second
    assert [x["kind"] for x in first] == [x["kind"] for x in second]
    assert len(first) >= 3, first
    for _ in range(5):
        assert ss.check(script, run) == first


def test_the_check_takes_no_model():
    import inspect
    params = set(inspect.signature(ss.check).parameters)
    assert params == {"script", "run"}, params
    source = (__import__("pathlib").Path(ss.__file__)).read_text(encoding="utf-8")
    for forbidden in ("llm", "gemini", "openai_client", "await ", "async def"):
        assert forbidden not in source, forbidden


# --- the writer is told the sentences -----------------------------------------------------------------------------------------------
def test_the_prompt_gives_the_sentences_verbatim_and_says_once():
    run = FakeRun([PLAIN, PREPRINT])
    block = ss.prompt_block(run)
    for r in ss.required(run):
        assert r["sentence"] in block
    assert "ONCE, word for word" in block
    assert "no other sentence about how a source stands" in block


def test_the_pipeline_uses_the_check_and_the_prompt_block():
    from pathlib import Path
    backend = Path(ss.__file__).resolve().parent
    pipeline = (backend / "curated_pipeline.py").read_text(encoding="utf-8")
    assert pipeline.count("status_sentences.check(script, run)") == 2, "both the full run and the supplied-script run"
    script_mod = (backend / "curated_script.py").read_text(encoding="utf-8")
    assert "status_sentences.prompt_block(run)" in script_mod
    assert "status_sentences_found" in script_mod


# --- a clause that speaks for several sources at once --------------------------------------------------------------------------------
PREPRINT_B = item("i9", cs.PREPRINT, "On the Replica Symmetric Solution in General Diluted Spin Glasses", authors=["Arnab Sen"])


def test_a_collective_clause_counts_for_every_preprint_it_covers():
    """221's wording: three preprints, one sentence. Saying it once per source reads as a list."""
    run = FakeRun([PREPRINT, PREPRINT_B])
    assert ss.check(script_of("An opening.", "Both are preprints, so they have not been peer reviewed."), run) == []


def test_a_collective_clause_counts_for_several_company_releases():
    other = item("i10", cs.COMPANY_RELEASE, "A second manuscript")
    run = FakeRun([PLAIN, other])
    said = "These two have not been peer reviewed or independently checked."
    assert ss.check(script_of(said), run) == []


def test_a_collective_clause_that_names_a_peer_reviewed_paper_is_refused():
    """The failure it must catch: a journal paper lumped in with preprints."""
    run = FakeRun([PREPRINT, JOURNAL])
    said = ('Both "Spin systems on Bethe lattices" and "De novo design of cysteine proteases" are preprints, so they have not been '
            "peer reviewed.")
    kinds = [x["kind"] for x in ss.check(script_of(said), run)]
    assert "status_not_stated" in kinds, kinds


def test_the_plural_wording_alone_is_not_collective():
    """Without "both", "these" or "all three" the plural covers only its own subject, so the other source is still unstated."""
    run = FakeRun([PREPRINT, PREPRINT_B])
    kinds = [x["kind"] for x in ss.check(script_of("Some papers are preprints, so they have not been peer reviewed."), run)]
    assert kinds.count("status_not_stated") == 2, kinds


def test_a_lean_entry_and_a_withdrawal_have_no_collective_form():
    assert ss.collective_clause_for(ss.clause_for(WITH_LEAN, cc.STATUS_HAS_LEAN)) is None
    assert ss.collective_clause_for(ss.clause_for(WITHDRAWN, cc.STATUS_WITHDRAWN)) is None


def test_saying_it_collectively_and_again_on_its_own_is_a_repeat():
    run = FakeRun([PREPRINT, PREPRINT_B])
    both = "Both are preprints, so they have not been peer reviewed."
    v = ss.check(script_of(both, ss.required(run)[0]["sentence"]), run)
    assert [x["kind"] for x in v] == ["status_stated_twice"], v


def test_the_prompt_offers_the_collective_wording():
    run = FakeRun([PREPRINT, PREPRINT_B])
    block = ss.prompt_block(run)
    assert "preprints, so they have not been peer reviewed" in block
    assert "must cover only sources that really have that status" in block


def test_the_collective_verdict_is_also_the_same_twice():
    run = FakeRun([PREPRINT, PREPRINT_B, JOURNAL])
    script = script_of("Both are preprints, so they have not been peer reviewed.", "A closing line.")
    first = ss.check(script, run)
    assert first == ss.check(script, FakeRun([PREPRINT, PREPRINT_B, JOURNAL]))
    for _ in range(4):
        assert ss.check(script, run) == first
