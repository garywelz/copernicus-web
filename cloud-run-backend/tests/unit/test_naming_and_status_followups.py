"""The five refusals left standing by the dry runs of 2026-11-22, each with the sentence that produced it.

197 failed five times on naming, 221 seven times and 003 four times on attribution. Two of 197's, two of 003's and two of 221's were
false; the rest were right and stay right.

  197  "This manuscript claims to disprove Kaplansky's direct-finiteness conjecture..."     possessive surname never matched its author
  197  "For A Counterexample to ... in Characteristic Two, OpenAI's catalogue lists..."     exact listed title, author misattributed
  003  "Another manuscript, "...A Zero-Free Half-Plane...", has a Lean formalization..."    an alias matched both manuscripts in a family
  003  "...its correctness has not been independently confirmed by the catalogue itself."   a negated attesting word read as a verdict
  221  "However, as a preprint, it also has not yet undergone the full peer-review..."      a status the item's class already records
"""
import curated_attribution as ca
import curated_checks as cc
import curated_sources as cs
import named_work_check as nw
import pytest

from tests.unit.test_status_gloss_and_lean_scope import L003, L197, checker, release


# ---------------------------------------------------------------- 197: the possessive surname
class P:
    def __init__(self, pid, title, authors=("OpenAI",), year=2026, abstract=""):
        self.pid, self.title, self.authors, self.year, self.abstract = pid, title, list(authors), year, abstract


K197 = [P("P1", "A Torsion-Free Group Algebra That Is Not Directly Finite"),
        P("P2", "A Counterexample to Kaplansky's Direct-Finiteness Conjecture in Characteristic Two"),
        P("P3", "A Counterexample to the Group-Ring Determinant Conjecture"),
        P("P4", "A Counterexample to Kaplansky's Direct-Finiteness Conjecture in Odd Characteristic")]

POSSESSIVE_SENTENCES = [
    "This manuscript claims to disprove Kaplansky's direct-finiteness conjecture by constructing a specific scenario where the "
    "conjecture fails.",
    "This manuscript also addresses Kaplansky's direct-finiteness conjecture.",
    "Similar to the characteristic two case, it finds elements that multiply to one in one order but not in the reverse, again "
    "challenging Kaplansky's conjecture.",
]


@pytest.mark.parametrize("sentence", POSSESSIVE_SENTENCES)
def test_a_possessive_surname_matches_its_own_author(sentence):
    """"Kaplansky's" normalises to "kaplanskys", which never equalled the author "kaplansky"."""
    m = {"quote": sentence, "title_words": [], "authors": ["Kaplansky"], "year": None, "where": "script"}
    name = nw.result_name(m, sentence)
    assert name and name.endswith("conjecture"), name
    assert nw.result_is_sourced(name, K197), f"the listed titles name the conjecture: {name}"


def test_depossess_leaves_a_short_or_double_s_word_alone():
    assert nw.depossess("kaplanskys") == "kaplansky"
    assert nw.depossess("openais") == "openai"
    for keep in ("gauss", "bess", "sens", "glass"):
        assert nw.depossess(keep) == keep, keep


# ---------------------------------------------------------------- 197: an exact title with the wrong author
def test_an_exact_listed_title_is_matched_although_the_author_is_wrong():
    """The model credited the conjecture's namesake. The title is exact, so it decides, and the author is recorded as misattributed."""
    # the title words exactly as the dry run of 2026-11-22 returned them for each sentence
    cases = ((K197[1].title, ["Counterexample", "Kaplansky's", "Direct-Finiteness", "Conjecture", "Characteristic", "Two"], "P2"),
             (K197[3].title, ["Counterexample", "Kaplansky's", "Direct-Finiteness", "Conjecture", "Odd", "Characteristic"], "P4"))
    for title, words, want in cases:
        m = {"quote": f"For {title}, OpenAI's catalogue lists a Lean formalization for this manuscript.",
             "title_words": words, "authors": ["Kaplansky"], "year": None, "where": "script"}
        assert nw.match_mention(m, K197) == want, (title, m)
        assert m.get("author_misattributed") is True


def test_a_title_that_only_shares_words_is_still_unlisted_whoever_is_credited():
    m = {"quote": "Kaplansky's Direct-Finiteness Conjecture for Group Algebras of Characteristic Zero",
         "title_words": ["Kaplansky's", "Direct-Finiteness", "Conjecture", "Group", "Algebras", "Characteristic", "Zero"],
         "authors": ["Kaplansky"], "year": None, "where": "script"}
    assert nw.match_mention(m, K197) is None
    assert "author_misattributed" not in m


def test_a_correctly_credited_mention_is_not_marked_misattributed():
    m = {"quote": "OpenAI's A Counterexample to the Group-Ring Determinant Conjecture", "title_words": K197[2].title.split(),
         "authors": ["OpenAI"], "year": None, "where": "script"}
    assert nw.match_mention(m, K197) == "P3"
    assert "author_misattributed" not in m


# ---------------------------------------------------------------- 003: the alias that matched two manuscripts
S003_P1 = ('Another manuscript, "The Quasi-Riemann Hypothesis: A Zero-Free Half-Plane real part of s greater than 7 over 8", has a Lean '
           "formalization listed in the company's catalogue.")


def test_an_alias_shared_by_two_manuscripts_resolves_to_the_one_the_sentence_names():
    c = checker(L003)
    named = c.releases_named(S003_P1)
    assert [c.run.pids[i["item_id"]] for i in named] == ["P1"], [i["title"] for i in named]


def test_the_lean_claim_for_that_manuscript_now_passes():
    """P1 has the entry; it was refused because the alias dragged in P2, which has none."""
    ok, why = checker(L003).check_status(S003_P1)
    assert ok is True, why


def test_the_p2_lean_refusal_still_stands():
    c = checker(L003)
    ok, why = c.check_status("OpenAI's catalogue lists a Lean formalization for The Quasi-Riemann Hypothesis (alternate 11/12 proof).")
    assert ok is False and "P2" in why, why


def test_a_sentence_that_names_neither_still_has_to_hold_for_both():
    """When nothing distinguishes them, every matched release must have the record, as before."""
    c = checker(L003)
    ok, why = c.check_status("The Quasi-Riemann Hypothesis manuscripts have Lean formalizations listed in the catalogue.")
    assert ok is False and "P2" in why, why


# ---------------------------------------------------------------- 003: a negated attesting word
def test_a_negated_attesting_word_is_a_limit_not_a_verdict():
    c = checker(L003)
    for sentence in ("This means that while a formalization is listed, its correctness has not been independently confirmed by the "
                     "catalogue itself.",
                     "A listed formalization has not been verified by anyone.",
                     "The catalogue does not mean the result has been proven."):
        ok, why = c.check_status(sentence)
        assert ok is True, f"{sentence} -> {why}"


def test_a_verdict_followed_by_a_caveat_is_still_a_verdict():
    """The limit must open before what it limits, or "confirmed ..., which does not mean much" would pass."""
    c = checker(L003)
    for sentence in ("The catalogue confirmed the proof, which does not mean it is published.",
                     "OpenAI verified the formalization, though that is not a journal review.",
                     "The catalogue has independently checked these formalizations, which does not mean much."):
        ok, why = c.check_status(sentence)
        assert ok is False, f"{sentence} -> passed with: {why}"


def test_the_result_is_not_in_doubt_refusal_still_stands():
    c = checker(L003)
    ok, why = c.check_status("OpenAI's catalogue indicates the result is not in doubt.")
    assert ok is False, why


def test_a_listing_is_not_progress_towards_verification():
    """The record itself settles this: the catalogue gives `scope: "Partial progress."` and `review.status: unchecked`, and it does not
    say the Lean file states the paper's theorem. So a listing is no step towards the result being verified, and "a step towards
    verification" goes beyond the record however carefully the rest of the sentence hedges."""
    c = checker(L003)
    sentence = ("The existence of a formalization for some of these works is a step towards verification, but the 'unchecked' status "
                "from the catalogue means we cannot yet consider them formally confirmed.")
    assert c.is_status_gloss(sentence) is False, "it points at items and claims progress"
    ok, why = c.check_status(sentence)
    assert ok is False, why
    assert "does not say the Lean file states the paper's theorem" in why, why


PROGRESS_CLAIMS = [
    "The listing is a step towards verification.",
    "A Lean entry in the catalogue is progress towards a verified proof.",
    "The formalization brings the proof closer to being verified.",
    "A catalogue listing is evidence that the result is correct.",
    "The entry represents partial verification of the theorem.",
    "Listing the formalization is an advance towards confirming the claim.",
    "That the catalogue lists it moves the result towards validation.",
    "The formalization is a milestone on the way to verification.",
    "Verification is underway, as the catalogue entry shows.",
]


@pytest.mark.parametrize("sentence", PROGRESS_CLAIMS)
def test_progress_towards_verification_fails_in_any_wording(sentence):
    for items in (L003, L197):
        ok, why = checker(items).check_status(sentence)
        assert ok is False, f"{sentence} -> passed with: {why}"


def test_denying_progress_is_still_a_gloss():
    """Saying a listing is NOT a step towards verification states the limit, which is exactly what a script should say."""
    c = checker(L003)
    for sentence in ("A catalogue listing is not a step towards verification.",
                     "A listed formalization is no evidence that the proof is correct.",
                     "A listing does not mean any progress towards verification has been made."):
        ok, why = c.check_status(sentence)
        assert ok is True, f"{sentence} -> {why}"


def test_the_plain_glosses_are_untouched_by_the_progress_rule():
    """The wording that must keep passing: none of it claims progress."""
    c = checker(L003)
    for sentence in ("This means that while a formalization is listed, its correctness has not been independently confirmed by the "
                     "catalogue itself.",
                     "A Lean formalization listed in the catalogue has not been independently checked.",
                     "The catalogue records a listing, not a verdict.",
                     "It is a listing by OpenAI itself, with its own stated review status."):
        ok, why = c.check_status(sentence)
        assert ok is True, f"{sentence} -> {why}"


def test_a_review_status_claim_still_fails_where_no_entry_has_one():
    c = checker([release("k1", "A manuscript with no formalization", False)])
    ok, why = c.check_status("The catalogue's review status for these manuscripts is 'unchecked'.")
    assert ok is False, why


# ---------------------------------------------------------------- 221: the status a class already records
def preprint(item_id, title, authors, year):
    return {"item_id": item_id, "class": cs.PREPRINT, "title": title, "authors": list(authors), "year": year,
            "identifiers": {}, "url": "", "evidence_text": "", "venue": None, "status_basis": {}}


L221 = [release("i1", "The Mézard–Parisi formula for diluted spin glasses", False),
        preprint("i2", "Spin glass models from the point of view of spin distributions", ["Dmitry Panchenko"], 2010),
        preprint("i3", "Spin systems on Bethe lattices", ["Amin Coja-Oghlan", "Will Perkins"], 2018),
        preprint("i4", "On the Replica Symmetric Solution in General Diluted Spin Glasses",
                 ["Ratul Biswas", "Wei-Kuo Chen", "Arnab Sen"], 2024)]

CLASS_STATUS = [
    "However, as a preprint, it also has not yet undergone the full peer-review process.",
    "Other preprints, like Spin glass models from the point of view of spin distributions and Spin systems on Bethe lattices, are also "
    "not yet peer-reviewed publications.",
    "These are preprints, so they have not been peer reviewed.",
]


@pytest.mark.parametrize("sentence", CLASS_STATUS)
def test_the_status_a_class_records_is_judged_against_the_record(sentence):
    ok, why = checker(L221).class_status_only(sentence)
    assert ok is True, f"{sentence} -> {why!r}"


@pytest.mark.parametrize("sentence", CLASS_STATUS)
def test_such_a_sentence_routes_to_the_status_records_and_passes(sentence):
    r = checker(L221).route(sentence)
    assert r.route == "status" and r.passed is True, (r.route, r.reason)


UNSUPPORTED = [
    "They offer new theoretical frameworks and rigorous decompositions for certain spin systems, which are important contributions to "
    "the field, but their findings are still undergoing scientific scrutiny.",
    "Its findings contribute to the understanding of certain aspects of diluted spin glasses, but like the others, it awaits "
    "independent verification and broader acceptance within the scientific community.",
    "Further work on related preprints, like Spin glass models from the point of view of spin distributions, could also offer "
    "corroborating evidence or alternative perspectives.",
]


@pytest.mark.parametrize("sentence", UNSUPPORTED)
def test_a_sentence_that_says_more_than_the_record_is_not_exempt(sentence):
    """The three 221 sentences that were refused correctly: each asserts something no source states."""
    ok, why = checker(L221).class_status_only(sentence)
    assert ok is False, f"{sentence} -> passed as {why!r}"


def test_a_peer_reviewed_item_is_not_called_unreviewed():
    peer = [{"item_id": "p1", "class": cs.PEER_REVIEWED, "title": "De novo design of cysteine proteases", "authors": ["A Lab"],
             "year": 2026, "identifiers": {}, "url": "", "evidence_text": "", "venue": "Nature", "status_basis": {}}]
    ok, _ = checker(peer).class_status_only("De novo design of cysteine proteases has not been peer reviewed.")
    assert ok is False


def test_a_class_status_sentence_needs_an_item_of_that_class():
    ok, _ = checker(L003).class_status_only("These are preprints, so they have not been peer reviewed.")
    assert ok is False, "003 holds only company releases"


# ---------------------------------------------------------------- the rejected script is returned
def test_the_failure_carries_the_script_the_checks_refused():
    import curated_script
    e = curated_script.ScriptRepairFailed([{"check": "naming", "kind": "unlisted_work"}], "HOST: a\n\nEXPERT: b\n")
    assert e.script == "HOST: a\n\nEXPERT: b\n"
    assert curated_script.ScriptRepairFailed([{"check": "x", "kind": "y"}]).script == ""


def test_the_dry_run_returns_it():
    from pathlib import Path
    source = (Path(__file__).resolve().parents[2] / "endpoints" / "curated" / "routes.py").read_text(encoding="utf-8")
    assert '"refused_script": refused' in source
    assert 'getattr(e, "script", "")' in source


def test_the_pipeline_passes_the_assembled_script_to_the_failure():
    from pathlib import Path
    source = (Path(__file__).resolve().parents[2] / "curated_script.py").read_text(encoding="utf-8")
    assert "raise ScriptRepairFailed(final, self.assemble(self.sections) if self.sections else \"\")" in source
