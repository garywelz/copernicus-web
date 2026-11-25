"""Three checks that misfired on dry run 2 of the revolutions list (66c1f6b6, 2026-11-25), tested with that run's own sentences:

  - the copying check refused every listed title of eight words or more, because a passage must contain its source's title;
  - the coverage check did not see "four-colour" in a source spelt "Four-Color", and made the writer say the sources did not cover it;
  - the naming check refused people a listed passage discusses ("Crowe cites Fourier and Hankel") as if they were unlisted works.
"""
import hashlib

import curated_mode as cm
import curated_script as csr
import curated_sources as cs
import topic_checks as tc
from tests.unit.test_curated_mode import PRIVATE, base_items, run_of

ZETA = "More than two thirds of the zeta zeros are simple and on the critical line"
ZETA_PASSAGE = (ZETA + "\n\nComments: 21 pages. Proof discovered autonomously by Claude (Anthropic); verified and communicated by the listed "
                "authors. See §1 for provenance. Lean formalization available. The listed authors verified the proof and take responsibility for "
                "its content. Jarred Sumner posed the problem and guided the investigation.")
CROWE = "Ten “Laws” concerning patterns of change in the history of mathematics"
CROWE_PASSAGE = ("TEN \"LAWS\" CONCERNING PATTERNS OF CHANGE IN THE HISTORY OF MATHEMATICS\n\n10. Revolutions never occur in mathematics. "
                 "Surprising as this \"law\" may seem to some, it is the conclusion of mathematicians as widely separated in time as J.B. Fourier, "
                 "H. Hankel, and C. Truesdell. Hankel wrote no less forcefully when in 1869 he stated: \"In mathematics alone each generation "
                 "builds a new story to the old structure\".")
DAUBEN = "Abraham Robinson and Nonstandard Analysis: History, Philosophy, and Foundations of Mathematics"
DAUBEN_PASSAGE = (DAUBEN + "\n\n[...]\n\nThere was an important lesson to be learned, Robinson believed, in the eventual acceptance of new ideas of "
                  "number, despite their novelty or the controversies they might provoke. In the 1890s, Kurt Hensel introduced a whole series of "
                  "new number systems, his now familiar p-adic numbers.")


def passage_source(title, authors, passage, cls=cs.PEER_REVIEWED, n=1, registry="crossref", abstract=""):
    ids = {"doi": f"10.9999/passage{n}"}
    sha = hashlib.sha256(passage.encode()).hexdigest()
    conf = {"status": cs.CONFIRMED, "pid": "", "title": title, "authors": list(authors), "year": 2000, "venue": "V",
            "ids": {"arxiv": None, "arxiv_version": None, "pmid": None, "doi": ids["doi"]}, "url": f"https://doi.org/{ids['doi']}",
            "abstract": abstract, "registry": registry, "confirmed_at": "", "title_match": 1.0, "record_type": "journal-article",
            "source_class": cls, "pin": None, "abstract_source": cs.PASSAGE_SOURCE if not abstract else None}
    item = {"item_id": cs.item_id(ids), "input": ids["doi"], "class": cls, "added_by": "gary", "identifiers": ids, "title": title,
            "authors": list(authors), "year": 2000, "venue": "V", "url": conf["url"], "evidence_text": abstract, "approved": True,
            "result_status": None, "confirmation": conf, "passage": {"sha256": sha, "chars": len(passage), "source_note": None},
            "limits": [{"type": "passage_supplied", "label": cs.PASSAGE_SUPPLIED_LABEL, "sha256": sha}]}
    PRIVATE[item["item_id"]] = passage
    return item


def the_run():
    return run_of(base_items() + [
        passage_source(ZETA, ["Levent Alpöge", "Ralph Furman"], ZETA_PASSAGE, cls=cs.PREPRINT, n=1, registry="arxiv",
                       abstract="We prove unconditionally that at least two thirds of the nontrivial zeros are simple."),
        passage_source(CROWE, ["Michael J Crowe"], CROWE_PASSAGE, n=2),
        passage_source(DAUBEN, ["Joseph W. Dauben"], DAUBEN_PASSAGE, n=3),
    ])


def verbatim(run_, script):
    return [v for v in run_.checks(script) if v["kind"] == "verbatim_run"]


# --- 1. a listed title is not copied text -----------------------------------------------------------------------------------------------
def test_saying_a_listed_title_is_not_copying_its_passage():
    r = the_run()
    said = ("EXPERT: Yes. A recent preprint, “More than two thirds of the zeta zeros are simple and on the critical line”, is a preprint, "
            "so it has not been peer reviewed. Michael J. Crowe, in \"Ten “Laws” concerning patterns of change in the history of "
            "mathematics,\" states that revolutions never occur in mathematics.")
    assert verbatim(r, said) == []


def test_copied_words_that_run_on_past_a_title_are_still_refused():
    r = the_run()
    copied = ("EXPERT: The preprint says the listed authors verified the proof and take responsibility for its content, and that the problem was "
              "set by someone else.")
    assert [v["words"] >= 8 for v in verbatim(r, copied)] == [True]


# --- 2. British and American spellings ----------------------------------------------------------------------------------------------------
TOPIC = "What would count as a revolution in mathematics? From the four-colour theorem to proofs found by AI."


def test_a_british_topic_is_covered_by_an_american_title():
    class Paper:
        title, abstract, evidence_text = "The Four-Color Problem and Its Philosophical Significance", "", ""
    assert tc.uncovered_named_things(TOPIC, [Paper()]) == []
    assert tc.spelling_fold("four-colour") == tc.spelling_fold("Four-Color") == "four-color"


def test_a_coverage_statement_may_be_spelt_either_way():
    for s in ("The sources do not cover the four-color theorem.", "The sources do not cover the four-colour theorem."):
        assert tc.missing_coverage_statements(s, ["four-colour"]) == []
        assert tc.missing_coverage_statements(s, ["four-color"]) == []


def test_spelling_folds_change_only_what_they_should():
    for word in ("four", "hour", "pour", "tour", "your"):
        assert tc.spelling_fold(word) == word
    assert tc.spelling_fold("formalisation") == tc.spelling_fold("formalization")
    assert tc.spelling_fold("analysed") == tc.spelling_fold("analyzed")
    assert tc.spelling_fold("centre") == tc.spelling_fold("center")


# --- 3. people a listed passage discusses, credited to it ---------------------------------------------------------------------------------
def person(quote, *authors):
    return {"kind": "unlisted_work", "where": "script", "quote": quote, "authors": list(authors), "year": None, "title_words": []}


def test_a_person_in_a_passage_may_be_named_in_a_sentence_that_credits_that_source():
    r = the_run()
    s = ("EXPERT: Crowe cites mathematicians like J.B. Fourier and H. Hankel, who believed the science preserves every principle it acquires.")
    v = person("Crowe cites mathematicians like J.B. Fourier and H. Hankel, who believed the science preserves every principle it acquires.",
               "J.B. Fourier", "H. Hankel")
    kept, exempt = csr.exempt_naming([v], r, s)
    assert kept == [] and exempt[0]["credited_pid"] == r.pids[r.items[-2]["item_id"]]


def test_the_dry_runs_uncredited_sentences_are_still_refused():
    r = the_run()
    script = ("EXPERT: Michael Crowe states that revolutions never occur in mathematics. He cites mathematicians like J.B. Fourier and H. Hankel, "
              "who believed the science preserves every principle it acquires and that each generation builds upon the old structure. "
              "Robinson himself believed that new ideas, despite initial controversies, could gain acceptance due to their utility.")
    he = person("He cites mathematicians like J.B. Fourier and H. Hankel, who believed the science preserves every principle it acquires and "
                "that each generation builds upon the old structure.", "J.B. Fourier", "H. Hankel")
    robinson = person("Robinson himself believed that new ideas, despite initial controversies, could gain acceptance due to their utility.",
                      "Robinson")
    kept, exempt = csr.exempt_naming([he, robinson], r, script)
    assert kept == [he, robinson] and exempt == []


def test_crediting_the_chapter_lets_its_subject_be_named():
    r = the_run()
    s = "EXPERT: Dauben writes that Robinson believed new ideas of number would in the end be accepted for their usefulness."
    kept, exempt = csr.exempt_naming([person("Dauben writes that Robinson believed new ideas of number would in the end be accepted", "Robinson")], r, s)
    assert kept == [] and exempt


def test_a_person_in_no_passage_stays_refused_even_when_a_source_is_credited():
    r = the_run()
    s = "EXPERT: Crowe cites Gauss on the matter."
    v = person("Crowe cites Gauss on the matter.", "Gauss")
    kept, exempt = csr.exempt_naming([v], r, s)
    assert kept == [v] and exempt == []


def test_a_work_with_a_title_is_never_exempted_this_way():
    r = the_run()
    s = "EXPERT: Crowe cites Fourier's Analytical Theory of Heat."
    v = {**person("Crowe cites Fourier's Analytical Theory of Heat.", "Fourier"), "title_words": ["Analytical", "Theory", "of", "Heat"]}
    kept, _ = csr.exempt_naming([v], r, s)
    assert kept == [v]
