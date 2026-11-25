"""The four limits found by check-script on the edited revolutions script (list 66c1f6b6, 2026-11-25), tested with that script's sentences:

  1. the content judge saw 2,500 characters of each source, labelled an abstract;
  2. a chapter's authors were one string, so the router never knew Dauben was a listed author;
  3. the router read people and events named in a credited source's passage (Lagarias, Claude, the Glorious Revolution) as unlisted sources;
  4. the title exemption missed a title with a word or two beside it.
"""
import asyncio
import hashlib
import json

import attribution_check as ac
import curated_attribution as ca
import curated_chapter as cch
import curated_mode as cm
import curated_script as csr
import curated_sources as cs
from tests.unit.test_curated_mode import PRIVATE, base_items, run_of
from tests.unit.test_curated_passage_checks import CROWE, CROWE_PASSAGE, passage_source

HALES = "A Formal Proof of the Kepler Conjecture"
HALES_PASSAGE = (HALES.upper() + "\n\n1. Introduction\n\n" + "The booklet describes the conjecture at some length. " * 60 +
                 "The delay in publication was caused by the difficulties that the referees had in verifying a complex computer proof. "
                 "Lagarias has described the review process. In the end, the proof was published without complete certification from the referees.")
ZETA = "More than two thirds of the zeta zeros are simple and on the critical line"
ZETA_PASSAGE = (ZETA + "\n\nThe mathematical argument in this paper was discovered and written by Claude, an AI developed by Anthropic. "
                "Jarred Sumner posed the problem and guided the investigation; the accompanying Lean 4 formalisation was orchestrated by Eric Easley.")
ABERDEIN = "Redefining Revolutions"
ABERDEIN_PASSAGE = ("REDEFINING REVOLUTIONS\n\n3. Mathematical Revolutions?\n\nDauben likens mathematical revolutions to the Glorious Revolution "
                    "of 1688, in the persistence of the old order. New theories cannot displace the old (Dauben 1984, 62).")
DAUBEN = "Abraham Robinson and Nonstandard Analysis: History, Philosophy, and Foundations of Mathematics"
DAUBEN_EXCERPT = (DAUBEN + "\n\n[...]\n\nWith an eye on the future of nonstandard analysis, Robinson was impressed by the fate of another theory "
                  "devised late in the nineteenth century. In the 1890s, Kurt Hensel introduced his now familiar p-adic numbers, which many "
                  "mathematicians came to regard as a pleasant game.")


def chapter():
    c = cch.confirm("hdl:11299/185659", DAUBEN, DAUBEN_EXCERPT, book_title="History and Philosophy of Modern Mathematics",
                    authors="Joseph W. Dauben", year="1988", source_note="pp. 177-200")
    ids = cch.identifiers_of(c)
    item = {"item_id": cs.item_id(ids), "input": "hdl:11299/185659", "class": cs.SCHOLARLY_CHAPTER, "added_by": "gary", "identifiers": ids,
            "title": c["title"], "authors": c["authors"], "year": c["year"], "confirmation": c, "evidence_text": "", "approved": True,
            "result_status": None}
    PRIVATE[item["item_id"]] = DAUBEN_EXCERPT
    return item


def the_run():
    return run_of(base_items() + [
        passage_source(HALES, ["Thomas Hales", "Mark Adams"], HALES_PASSAGE, n=11, abstract="This article describes a formal proof of the Kepler conjecture."),
        passage_source(ZETA, ["Levent Alpöge", "Ralph Furman"], ZETA_PASSAGE, cls=cs.PREPRINT, n=12, registry="arxiv",
                       abstract="We prove unconditionally that at least two thirds of the nontrivial zeros are simple."),
        passage_source(ABERDEIN, ["Andrew Aberdein"], ABERDEIN_PASSAGE, cls=cs.PREPRINT, n=13, registry="arxiv",
                       abstract="In their account of theory change in logic, Aberdein and Read distinguish glorious from inglorious revolutions."),
        passage_source(CROWE, ["Michael J Crowe"], CROWE_PASSAGE, n=14),
        chapter(),
    ])


def run(coro):
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


# --- 1. the content judge sees each source whole ----------------------------------------------------------------------------------------
def test_in_curated_mode_the_judge_is_given_the_whole_source_text_labelled_as_such():
    r = the_run()
    paper = next(p for p in r.confirmed_papers() if p.title == HALES)
    assert len(paper.abstract) > ac.MAX_ABSTRACT_CHARS                       # the Lagarias sentence is beyond the old cut
    seen = {}

    async def llm(system, user):
        seen["system"], seen["user"] = system, user
        return json.dumps({"attributions": []})
    run(ac.check_attributions("EXPERT: Hales and his co-authors quote Lagarias on the review.", [paper], llm, source_text=True))
    assert "without complete certification from the referees" in seen["user"]
    assert "SOURCE TEXT:" in seen["user"] and "ABSTRACT:" not in seen["user"] and "abstract" not in seen["system"]
    run(ac.check_attributions("EXPERT: Hales and his co-authors quote Lagarias on the review.", [paper], llm))
    assert "without complete certification from the referees" not in seen["user"] and "ABSTRACT:" in seen["user"]    # ordinary mode unchanged


def test_the_curated_check_asks_for_source_text():
    import inspect
    assert "source_text=True" in inspect.getsource(ca)


# --- 2. a chapter's authors are a list in the run ----------------------------------------------------------------------------------------
def test_a_chapter_author_is_a_listed_author_to_the_router():
    r = the_run()
    ch = next(i for i in r.items if i["class"] == cs.SCHOLARLY_CHAPTER)
    assert ch["authors"] == ["Joseph W. Dauben"]
    assert "dauben" in ca.Router(r).vocab
    routed = ca.Router(r).route("Dauben notes that Robinson was impressed by the fate of Hensel's p-adic numbers, which many first took for "
                                "a \"pleasant game\" and which are now held to be coequal with the real numbers.")
    assert routed.route != "unlisted_source", routed.reason
    paper = next(p for p in r.confirmed_papers() if p.source_class == cs.SCHOLARLY_CHAPTER)
    assert paper.authors == ["Joseph W. Dauben"]


# --- 3. people and events a credited passage names ----------------------------------------------------------------------------------------
def test_people_named_in_a_credited_passage_are_not_unlisted_sources():
    router = ca.Router(the_run())
    for sentence in (
        "Hales and his co-authors explain why it was needed by quoting Lagarias's account of the review: the nature of the proof made checking "
        "each step reliably hard for humans, and in the end it went to print without the referees' complete certification.",
        "Alpöge and Furman write that the argument was found and written by Claude, an AI model, over two interactive sessions.",
    ):
        routed = router.route(sentence)
        assert routed.route != "unlisted_source", (sentence, routed.reason)


def test_a_person_with_no_credited_source_or_in_no_passage_is_still_an_unlisted_source():
    router = ca.Router(the_run())
    assert router.route("Lagarias said the proof was hard to check.").route == "unlisted_source"      # no source credited
    assert router.route("Tao said, as Hales and his co-authors report, that the proof was hard to check.").route == "unlisted_source"   # in no passage


def test_a_named_event_in_a_credited_passage_may_be_named():
    r = the_run()
    s = ("EXPERT: As Aberdein reports, Dauben compared revolutions in mathematics with England's Glorious Revolution of 1688, when the old order "
         "persisted under different terms.")
    v = {"kind": "unlisted_work", "where": "script", "quote": s[8:], "authors": [], "year": 1688, "title_words": ["England's", "Glorious", "Revolution"]}
    kept, exempt = csr.exempt_naming([v], r, s)
    assert kept == [] and exempt
    bare = "EXPERT: Dauben compared revolutions with the Glorious Revolution of 1688."
    v2 = dict(v, quote=bare[8:])
    kept, _ = csr.exempt_naming([v2], r, bare)
    assert kept == [v2] or not any(cm.sentence_credits_item(bare, i) and cm.passage_words(i) and "glorious" in cm.passage_words(i)
                                   for i in r.items if i["title"] == ABERDEIN)
    wrong_year = dict(v, year=1689)
    kept, _ = csr.exempt_naming([wrong_year], r, s)
    assert kept == [wrong_year]                                               # not the event the passage names


# --- 4. a title with a word or two beside it ---------------------------------------------------------------------------------------------
def test_a_title_with_its_adjoining_words_is_not_copying():
    """The real passage prints the byline under the title, so "<title> by Michael" is the title and two adjoining words of the passage."""
    bylined = CROWE_PASSAGE.replace("HISTORY OF MATHEMATICS\n\n", "HISTORY OF MATHEMATICS\n\nBY MICHAEL J. CROWE\nUNIVERSITY OF NOTRE DAME\n\n", 1)
    assert bylined != CROWE_PASSAGE
    r = run_of(base_items() + [passage_source(CROWE, ["Michael J Crowe"], bylined, n=21)])
    said = ("EXPERT: That's a complex question. \"Ten “Laws” concerning patterns of change in the history of mathematics\" by Michael "
            "Crowe suggests that revolutions never occur in mathematics.")
    assert [v for v in r.checks(said) if v["kind"] == "verbatim_run"] == []


def test_a_title_with_eight_copied_words_beside_it_is_still_copying():
    r = the_run()
    copied = ("EXPERT: The paper “More than two thirds of the zeta zeros are simple and on the critical line” says Jarred Sumner posed "
              "the problem and guided the investigation; the accompanying Lean 4 formalisation was orchestrated by Eric Easley.")
    assert [v for v in r.checks(copied) if v["kind"] == "verbatim_run"]
