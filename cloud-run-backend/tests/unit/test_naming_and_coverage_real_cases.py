"""The three refusals of 2026-11-22, each with the real listed titles.

Five frozen lists could not be voiced. Every refusal was deterministic and none of them was about the script being wrong:

* 197 - "A Counterexample to Kaplansky's Direct-Finiteness Conjecture in Characteristic Two" and "...in Odd Characteristic" differ only in
  "Two" and "Odd". The matcher keeps words of four letters or more, so both titles reduced to the SAME five words, every mention scored 5
  against each, the tie-break refused to choose and two titles that were on the list were reported as unlisted.
* 221 - the topic wrote "Mezard-Parisi" and the listed manuscript "Mézard–Parisi". The name extractor could not start a token at "é", so it
  collected the fragment "zard-Parisi"; the accent and the en dash meant no source was seen to cover it; the coverage check therefore
  demanded a sentence saying the reviewed papers do not cover the formula that the principal listed manuscript is named after, and the
  naming check then refused that very sentence. The same extractor returned "OpenAI" as an uncovered name, which is where 017's
  "The papers reviewed here do not cover OpenAI." came from.
* 287 - "a classical result, known as the free group factor alternative" is the name of a theorem, not a paper, so no listed paper could
  ever match it.
"""
import sys
from pathlib import Path

import named_work_check as nw
from topic_checks import fold, missing_coverage_statements, named_things, uncovered_named_things

BACKEND = Path(__file__).resolve().parents[2]


class P:
    """A confirmed source, as curated_mode supplies one (attached release text arrives as the abstract)."""

    def __init__(self, pid, title, authors=("OpenAI",), year=2026, abstract=""):
        self.pid, self.title, self.authors, self.year, self.abstract = pid, title, list(authors), year, abstract


L197 = [P("P1", "A Torsion-Free Group Algebra That Is Not Directly Finite"),
        P("P2", "A Counterexample to Kaplansky's Direct-Finiteness Conjecture in Characteristic Two"),
        P("P3", "A Counterexample to the Group-Ring Determinant Conjecture"),
        P("P4", "A Counterexample to Kaplansky's Direct-Finiteness Conjecture in Odd Characteristic")]

L221 = [P("P1", "The Mézard–Parisi formula for diluted spin glasses", abstract="We prove the hierarchical cavity formula."),
        P("P2", "Spin glass models from the point of view of spin distributions", ("Dmitry Panchenko",), 2010),
        P("P3", "Spin systems on Bethe lattices", ("Amin Coja-Oghlan", "Will Perkins"), 2018),
        P("P4", "On the Replica Symmetric Solution in General Diluted Spin Glasses", ("Ratul Biswas", "Wei-Kuo Chen"), 2024)]

L287 = [P("P1", "An isomorphism of the free group factors"),
        P("P2", "Free Monotone Transport", ("A. Guionnet", "D. Shlyakhtenko"), 2012),
        P("P3", "On the II$_{1}$ Factors of Fuchsian Groups", ("D. Shlyakhtenko",), 2026)]


def mention(title, authors=(), year=None, quote=None):
    return {"quote": quote if quote is not None else title, "title_words": [title], "authors": list(authors), "year": year,
            "where": "script"}


# --- 197: the tie on "Two" and "Odd" ------------------------------------------------------------------------------------------------
def test_the_two_titles_are_still_identical_to_the_word_matcher():
    """The cause, held in place: if this ever stops being true the tie-break below is not what is protecting us."""
    assert nw._words(L197[1].title) == nw._words(L197[3].title)


def test_each_kaplansky_title_matches_its_own_listed_manuscript():
    assert nw.match_mention(mention(L197[1].title), L197) == "P2"
    assert nw.match_mention(mention(L197[3].title), L197) == "P4"


def test_the_other_two_titles_in_the_family_still_match():
    assert nw.match_mention(mention(L197[0].title), L197) == "P1"
    assert nw.match_mention(mention(L197[2].title), L197) == "P3"


def test_a_title_that_fits_neither_is_still_refused():
    """The tie-break may not become a way in for a work that is not listed."""
    assert nw.match_mention(mention("A Counterexample to Kaplansky's Quasitrace Conjecture"), L197) is None


# --- 221: accents, dashes, and the coverage deadlock ----------------------------------------------------------------------------------
TOPIC_221 = ("OpenAI's manuscript claiming a proof of the Mézard-Parisi formula for diluted spin glasses, and the status of "
             "the claim")


def test_a_name_is_collected_whole_even_when_it_starts_outside_ascii():
    assert "Mézard-Parisi" in named_things("a proof of the Mézard-Parisi formula")
    assert not any(n.startswith("zard") for n in named_things(TOPIC_221)), "no truncated fragments"


def test_a_company_is_never_a_thing_the_papers_must_not_cover():
    """017 said "The papers reviewed here do not cover OpenAI." because the check asked for it."""
    assert "OpenAI" not in named_things(TOPIC_221)
    assert uncovered_named_things("a claim by OpenAI and by DeepMind", []) == []


def test_the_listed_manuscript_is_seen_to_cover_the_formula_it_is_named_after():
    """The deadlock: the coverage check demanded the script deny coverage of its own principal source."""
    assert uncovered_named_things(TOPIC_221, L221) == []


def test_every_dash_and_accent_form_compares_equal():
    assert fold("Mézard–Parisi") == fold("Mezard-Parisi") == "mezard-parisi"
    for spelling in ("Mezard-Parisi", "Mézard–Parisi", "Mézard-Parisi", "Mezard—Parisi"):
        assert uncovered_named_things(f"a proof of the {spelling} formula", L221) == [], spelling


def test_a_name_no_source_covers_is_still_demanded():
    assert uncovered_named_things("a proof of the Collatz conjecture", L221) == ["Collatz"]


def test_the_required_sentence_counts_whichever_spelling_the_script_uses():
    said = "The papers reviewed here do not cover Mezard-Parisi."
    assert missing_coverage_statements(said, ["Mézard–Parisi"]) == []
    assert missing_coverage_statements("A long discussion of spin glasses.", ["Mézard–Parisi"]) == ["Mézard–Parisi"]


def test_a_shortened_form_of_a_listed_title_is_the_episodes_own_subject():
    m = mention("Mézard–Parisi formula")
    assert nw.is_own_subject(m, L221, "and the Mézard–Parisi formula is the subject here")


# --- 287: a named result is not a work ------------------------------------------------------------------------------------------------
ALTERNATIVE = ("A classical result for these algebras, the free group factor alternative, says that if two of the factors are "
               "isomorphic then all of the interpolated ones are.")


def test_a_phrase_ending_in_a_result_noun_is_read_as_a_result():
    for phrase in ("the free group factor alternative", "the Mézard–Parisi formula", "Kaplansky's direct-finiteness conjecture",
                   "the quasi-Riemann hypothesis", "Szemeredi's theorem", "the Cauchy-Schwarz inequality"):
        assert nw.names_a_result(phrase), phrase
    for phrase in ("An isomorphism of the free group factors", "A Torsion-Free Group Algebra That Is Not Directly Finite",
                   "Spin systems on Bethe lattices"):
        assert not nw.names_a_result(phrase), phrase


def test_a_listed_title_that_ends_in_a_result_noun_is_matched_before_the_result_rule_is_reached():
    """P3 is "A Counterexample to the Group-Ring Determinant Conjecture", which ends in a result noun. The result rule is only reached when
    no listed paper matched, so a listed title is never diverted into it."""
    assert nw.names_a_result(L197[2].title), "it does end in a result noun"
    assert nw.match_mention(mention(L197[2].title), L197) == "P3", "and it still matches its own manuscript first"


def test_a_citation_with_a_year_is_a_paper_even_when_it_ends_in_a_result_noun():
    """"Smith's 2019 paper 'The Kadison-Singer Problem'" is a work. The exemption may not be a way to name an unlisted paper by calling it
    a result, so a year disqualifies it however many of its words are in the sources."""
    sourced = [P("P1", "The Kadison-Singer Problem and the paving conjecture",
                 abstract="On the Kadison-Singer problem, the paving conjecture and Smith's approach.")]
    text = "Smith's 2019 paper \"The Kadison-Singer Problem\" is often cited here."
    m = mention("The Kadison-Singer Problem", authors=["Smith"], year=2019, quote=text)
    assert nw.result_is_sourced("The Kadison-Singer Problem", sourced), "its words ARE in the sources"
    assert not nw.reads_as_a_result(m, "The Kadison-Singer Problem", text), "and it is still not a result"


def test_a_quoted_title_is_a_work_even_with_no_year():
    """Quotation marks give something AS a title."""
    text = 'the manuscript "The Kadison-Singer Problem" claims a proof'
    m = mention("The Kadison-Singer Problem", quote=text)
    assert not nw.reads_as_a_result(m, "The Kadison-Singer Problem", text)


def test_an_author_alone_does_not_disqualify_a_result():
    """A result is often named after someone: "Kaplansky's direct-finiteness conjecture" is a conjecture, not a paper by Kaplansky."""
    text = "the proof settles Kaplansky's direct-finiteness conjecture for torsion-free groups"
    m = mention("Kaplansky's direct-finiteness conjecture", authors=["Kaplansky"])
    assert nw.reads_as_a_result(m, "Kaplansky's direct-finiteness conjecture", text)
    assert nw.result_is_sourced("Kaplansky's direct-finiteness conjecture", L197), "P2 and P4 name it in their titles"


def test_the_free_group_factor_alternative_is_still_read_as_a_result():
    m = mention("the free group factor alternative", quote=ALTERNATIVE)
    assert nw.reads_as_a_result(m, "the free group factor alternative", ALTERNATIVE)


def test_the_named_result_passes_when_an_attached_manuscript_names_it():
    listed = [P("P1", "An isomorphism of the free group factors",
                abstract="We settle the problem using the free group factor alternative of the interpolated factors.")] + L287[1:]
    assert nw.result_is_sourced("the free group factor alternative", listed)


def test_the_same_result_is_refused_when_no_source_names_it():
    assert not nw.result_is_sourced("the free group factor alternative", L287), \
        "no listed title or abstract contains 'alternative'"


def test_an_invented_result_is_refused():
    for invented in ("the Smith-Jones conjecture", "the Smith–Jones conjecture", "the Harbinger theorem",
                     "the diagonal exclusion principle"):
        assert not nw.result_is_sourced(invented, L221), invented


def test_an_unsourced_result_is_its_own_violation_kind():
    """It is not reported as an unlisted work: the fix for it is different wording, not a different list."""
    import curated_script
    v = {"check": "naming", "kind": "unsourced_result", "find": "the Smith-Jones conjecture",
         "raw": {"authors": [], "year": None, "title_words": ["the Smith-Jones conjecture"], "quote": "x", "where": "script"}}
    out = curated_script.reported_violation(v)
    assert out["kind"] == "unsourced_result"
    assert out["mention"]["title_words"] == ["the Smith-Jones conjecture"]


# --- item 6: a refusal can be diagnosed from the response --------------------------------------------------------------------------
def test_a_naming_refusal_reports_what_the_extractor_found():
    import curated_script
    v = {"check": "naming", "kind": "unlisted_work", "find": "q", "message": "m",
         "raw": {"authors": ["OpenAI"], "year": 2026, "title_words": ["A Counterexample"], "quote": "q", "where": "script"}}
    out = curated_script.reported_violation(v)
    assert out["mention"] == {"authors": ["OpenAI"], "year": 2026, "title_words": ["A Counterexample"], "quote": "q",
                             "where": "script"}


def test_both_routes_report_violations_through_the_one_helper():
    source = (BACKEND / "endpoints" / "curated" / "routes.py").read_text(encoding="utf-8")
    assert source.count("curated_script.reported_violation(x)") == 2
    assert '("check", "kind", "find", "message")} for x in' not in source, "the lossy filter is gone"
