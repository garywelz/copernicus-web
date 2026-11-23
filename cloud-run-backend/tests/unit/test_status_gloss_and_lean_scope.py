"""Explaining a status is not claiming one.

Every sentence mentioning a Lean formalization was read as claiming one for a paper, and refused unless the sentence also named a listed
manuscript. That left two episodes unable to explain a status they are required to explain: 197 and 003 both failed on sentences saying what
a catalogue listing does NOT mean (2026-11-22).

A sentence that credits the catalogue is still judged against the listed items' STATUS RECORDS, never against their abstracts:

* it names a manuscript     -> that manuscript's record must show the Lean entry;
* it takes several together -> every release the list holds must show it, or the sentence overstates;
* it points at one ("this manuscript") with no name -> nothing can be checked, so it is refused and the script must name it;
* it only says what a listing is and is not -> a gloss, and it passes.

The records here are the real ones, read from the frozen lists on 2026-11-22:
  197: P1 no Lean entry, P2 yes, P3 yes, P4 yes
  003: P1 yes,            P2 no,  P3 yes
"""
import curated_attribution as ca
import curated_checks as cc
import curated_mode
import curated_sources as cs
import pytest


def release(item_id, title, in_lean):
    return {"item_id": item_id, "class": cs.COMPANY_RELEASE, "title": title, "authors": ["OpenAI"], "year": 2026,
            "identifiers": {}, "url": "", "evidence_text": "", "venue": None,
            "status_basis": {"in_lean_catalogue": in_lean, "withdrawal_notice": None, "commit": "x", "lean_catalogue_entries": 100,
                             "readme_present": True}}


L197 = [release("i1", "A Torsion-Free Group Algebra That Is Not Directly Finite", False),
        release("i2", "A Counterexample to Kaplansky's Direct-Finiteness Conjecture in Characteristic Two", True),
        release("i3", "A Counterexample to the Group-Ring Determinant Conjecture", True),
        release("i4", "A Counterexample to Kaplansky's Direct-Finiteness Conjecture in Odd Characteristic", True)]

L003 = [release("j1", "The Quasi-Riemann Hypothesis: A Zero-Free Half-Plane", True),
        release("j2", "The Quasi-Riemann Hypothesis (alternate 11/12 proof)", False),
        release("j3", "Uniform exclusion of Landau–Siegel zeros", True)]


class FakeRun:
    """Only what the status check reads: the items, their pids and their status."""

    def __init__(self, items):
        self.items = items
        self.pids = {i["item_id"]: f"P{n}" for n, i in enumerate(items, start=1)}
        self.topic = "the status of the claims"
        self.reporting_text = ""

    def results(self):
        return [{"item_id": i["item_id"], "title": i["title"], "authors": i["authors"], "year": i["year"]} for i in self.items]

    def status_of(self, item):
        basis = item.get("status_basis") or {}
        if (basis.get("withdrawal_notice") or None):
            return cc.STATUS_WITHDRAWN
        return cc.STATUS_HAS_LEAN if basis.get("in_lean_catalogue") else cc.STATUS_UNVERIFIED


def checker(items):
    c = ca.Router.__new__(ca.Router)
    c.run = FakeRun(items)
    c.releases = list(items)
    c.companies = {"openai"}
    c.sources = []                  # no commentary on these lists
    c.person_index = {}
    c.vocab = {"lean"} | c.companies
    return c


# --- the refusal that must survive --------------------------------------------------------------------------------------------------
def test_003_p2_is_still_refused_when_it_is_named():
    """The real error the check caught: a Lean formalization claimed for the one manuscript that has no entry."""
    c = checker(L003)
    ok, why = c.check_status("OpenAI's catalogue lists a Lean formalization for The Quasi-Riemann Hypothesis (alternate 11/12 proof).")
    assert ok is False
    assert "P2" in why, why


def test_a_lean_claim_for_a_manuscript_that_has_the_entry_passes():
    c = checker(L003)
    ok, why = c.check_status("OpenAI's catalogue lists a Lean formalization for Uniform exclusion of Landau–Siegel zeros.")
    assert ok is True, why


# --- several taken together ---------------------------------------------------------------------------------------------------------
def test_197s_sentence_about_these_manuscripts_is_judged_against_every_item_in_the_family():
    """"for these specific manuscripts, the Lean formalizations are listed": the two Kaplansky manuscripts do have entries, but the
    family also holds one that does not, and a sentence that takes them together says so of all of them."""
    c = checker(L197)
    ok, why = c.check_status("Yes, for these specific manuscripts, the Lean formalizations are listed in OpenAI's own catalogue, "
                             "and their review status is explicitly stated as 'unchecked'.")
    assert ok is False
    assert "P1" in why, why


def test_the_same_sentence_passes_for_a_family_where_every_item_has_the_entry():
    c = checker([i for i in L197 if i["item_id"] != "i1"])
    ok, why = c.check_status("For these manuscripts the Lean formalizations are listed in OpenAI's own catalogue, and their review "
                             "status is 'unchecked'.")
    assert ok is True, why


def test_all_three_is_judged_the_same_way():
    c = checker(L003)
    ok, why = c.check_status("All three have a Lean formalization listed in the catalogue.")
    assert ok is False and "P2" in why, why


# --- pointing at one without naming it ----------------------------------------------------------------------------------------------
def test_a_lean_claim_for_this_manuscript_with_no_name_is_refused_and_says_what_to_do():
    """003 said this twice. Which manuscript is meant cannot be told, and one of the three has no entry, so it may not be waved through."""
    c = checker(L003)
    ok, why = c.check_status("OpenAI's catalogue lists a Lean formalization for this manuscript.")
    assert ok is False
    assert "does not say for which listed manuscript" in why and "name the manuscript" in why, why


# --- the gloss ----------------------------------------------------------------------------------------------------------------------
GLOSSES = [
    "The presence of a Lean formalization in OpenAI's catalogue does not mean it has been independently checked for correctness.",
    "It is a listing by OpenAI itself, with its own stated review status.",
    "A Lean formalization listed in the catalogue has not been independently checked.",
    "The catalogue records a listing, not a verdict.",
    "A listing says nothing about whether the proof is correct.",
]


@pytest.mark.parametrize("sentence", GLOSSES)
def test_a_gloss_on_the_status_wording_passes(sentence):
    for items in (L197, L003):
        ok, why = checker(items).check_status(sentence)
        assert ok is True, f"{sentence} -> {why}"


def test_a_finding_dressed_as_a_negation_is_not_a_gloss():
    """A bare "is not" made any negative sentence a gloss, so a verdict could be given as one."""
    c = checker(L003)
    for sentence in ("OpenAI's catalogue indicates the result is not in doubt.",
                     "The catalogue shows the proof is not incomplete.",
                     "According to the catalogue the argument is not disputed."):
        ok, why = c.check_status(sentence)
        assert ok is False, f"{sentence} -> passed with: {why}"


def test_the_plain_gloss_still_passes_without_that_alternative():
    c = checker(L003)
    ok, why = c.check_status("A catalogue listing does not mean the formalization has been independently checked.")
    assert ok is True, why


def test_a_gloss_may_not_credit_anyone_with_checking_anything():
    c = checker(L003)
    for sentence in ("The catalogue has independently checked these formalizations.",
                     "A Lean formalization in the catalogue has been verified by OpenAI.",
                     "The formalizations in the catalogue were reviewed before listing."):
        ok, why = c.check_status(sentence)
        assert ok is False, f"{sentence} -> passed with: {why}"


def test_a_limiting_clause_does_not_excuse_a_claim_about_an_item():
    """A sentence may not smuggle a Lean claim in beside a caveat."""
    c = checker(L003)
    ok, why = c.check_status("OpenAI's catalogue lists a Lean formalization for this manuscript, though the catalogue's own review "
                             "status is 'unchecked'.")
    assert ok is False, why


def test_the_gloss_branch_does_not_touch_withdrawals():
    """A withdrawal claim is still judged against the notice, not read as a gloss."""
    c = checker(L003)
    ok, why = c.check_status("The manuscript was withdrawn after a notice was posted.")
    assert ok is False, why
