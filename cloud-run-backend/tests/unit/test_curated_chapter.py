"""A chapter in a scholarly book: the identifiers accepted, the passage that evidences it, the class the record names, the status the
script must give it, and the places a chapter's passage must behave exactly as attached release text does.

Pure code: no network, no database. The real case these tests are written from is a historian's chapter reachable only by a JSTOR stable
number, which is the kind of source the podcast could not cite at all before this class existed.
"""
import hashlib

import pytest

import curated_chapter as cch
import curated_checks as cc
import curated_mode as cm
import curated_sources as cs
import status_sentences as ss
from tests.unit.test_curated_mode import PRIVATE, approved_doc, base_items, registry_item, run_of

TITLE = "Marx, Hegel, and the Calculus"
EXCERPT = (
    "Marx, Hegel, and the Calculus. The mathematical manuscripts that Marx left unpublished show him working through the foundations of "
    "the differential calculus as they stood in the eighteenth and nineteenth centuries. He was dissatisfied with the appeal to "
    "infinitesimals, and he read Lagrange's attempt to found the calculus on power series as an advance precisely because it dispensed "
    "with them. What the manuscripts record is not a contribution to mathematics but a philosopher's reading of a mathematical practice "
    "in transition, and that is how they should be judged."
)


def chapter_confirmation(**kw):
    args = dict(identifier="https://www.jstor.org/stable/j.ctt5vkmnr.8", title=TITLE, excerpt=EXCERPT,
                book_title="Abraham Robinson: The Creation of Nonstandard Analysis", authors="Joseph W. Dauben",
                year="1995", source_note="pp. 81-94")
    args.update(kw)
    return cch.confirm(**args)


def chapter_item(**extra):
    c = chapter_confirmation()
    ids = cch.identifiers_of(c)
    item = {"item_id": cs.item_id(ids), "input": "https://www.jstor.org/stable/j.ctt5vkmnr.8", "class": cs.SCHOLARLY_CHAPTER,
            "added_by": "gary", "identifiers": ids, "title": c["title"], "authors": c["authors"], "year": c["year"],
            "confirmation": c, "evidence_text": "", "approved": True, "result_status": None}
    item.update(extra)
    PRIVATE[item["item_id"]] = EXCERPT
    return item


# --- which identifiers a chapter may be cited by -----------------------------------------------------------------------------------
@pytest.mark.parametrize("raw,scheme,value", [
    ("https://www.jstor.org/stable/j.ctt5vkmnr.8", "jstor", "j.ctt5vkmnr.8"),
    ("https://jstor.org/stable/2695643", "jstor", "2695643"),
    ("https://hdl.handle.net/2027/heb.00743", "handle", "2027/heb.00743"),
    ("hdl:2027/heb.00743", "handle", "2027/heb.00743"),
    ("isbn: 978-0-691-60078-5", "isbn", "9780691600785"),
])
def test_a_stable_identifier_is_accepted_and_normalised(raw, scheme, value):
    assert cch.parse_identifier(raw) == (scheme, value)


@pytest.mark.parametrize("raw", [
    "https://www.amazon.com/dp/0691600783",                 # a copy for sale, not a work
    "https://library.example.edu/search?q=dauben",          # a search result, which changes
    "https://books.google.com/books?id=abcdef",             # a viewer, and not a citation
    "https://example.org/dauben-chapter.pdf",               # an ordinary address: that is a company release or commentary, not a chapter
    "see my bookshelf",
])
def test_an_identifier_that_will_not_resolve_later_is_refused(raw):
    with pytest.raises(cch.ChapterRefused) as e:
        cch.parse_identifier(raw)
    assert e.value.reason in ("identifier_not_stable", "isbn_wrong_length")


def test_the_identifier_becomes_an_address_a_listener_can_follow():
    assert cch.identifier_url("jstor", "2695643") == "https://www.jstor.org/stable/2695643"
    assert cch.identifier_url("handle", "2027/heb.00743") == "https://hdl.handle.net/2027/heb.00743"
    assert cch.identifier_url("isbn", "9780691600785") == "isbn:9780691600785"


# --- the passage is the evidence, and it is checked ---------------------------------------------------------------------------------
def test_a_confirmed_chapter_records_its_identity_and_pins_its_passage():
    c = chapter_confirmation()
    assert c["status"] == "confirmed"
    assert c["registry"] == "chapter_excerpt"
    assert c["scheme"] == "jstor" and c["identifier"] == "j.ctt5vkmnr.8"
    assert c["title"] == TITLE and c["authors"] == "Joseph W. Dauben" and c["year"] == "1995"
    assert c["excerpt_sha256"] == hashlib.sha256(EXCERPT.encode()).hexdigest()
    assert c["excerpt_chars"] == len(EXCERPT)


def test_the_passage_itself_is_never_in_the_record():
    """The list says what was attached and how long it was; the words live only in the private store."""
    c = chapter_confirmation()
    assert EXCERPT[:40] not in repr(c)
    assert not any(isinstance(v, str) and len(v) > 400 for v in c.values())


def test_a_passage_from_the_wrong_chapter_is_refused():
    with pytest.raises(cch.ChapterRefused) as e:
        chapter_confirmation(title="A Chapter With Another Name Entirely")
    assert e.value.reason == "title_not_in_excerpt"


def test_the_title_is_found_through_retyped_punctuation_and_accents():
    """A passage read out of a PDF or retyped loses spacing, dashes and accents; the comparison must survive that and nothing more."""
    assert cch.title_in_excerpt("Marx, Hegel, and the Calculus", "...MARX HEGEL AND THE CALCULUS...")
    assert cch.title_in_excerpt("Cauchy's Theoreme", "Cauchy’s Théorème is proved here")
    assert not cch.title_in_excerpt("Marx and the Calculus", "Hegel and the Calculus")


def test_a_citation_is_not_a_passage():
    with pytest.raises(cch.ChapterRefused) as e:
        chapter_confirmation(excerpt="Dauben, J. W. (1995), ch. 4.")
    assert e.value.reason == "excerpt_too_short"


def test_a_year_that_is_not_a_year_is_refused():
    with pytest.raises(cch.ChapterRefused) as e:
        chapter_confirmation(year="sometime in the nineties")
    assert e.value.reason == "year_not_a_number"


# --- the class the record names ------------------------------------------------------------------------------------------------------
@pytest.mark.parametrize("record_type", ["book-chapter", "book-part", "book-section", "monograph", "reference-entry", "edited-book"])
def test_a_crossref_book_record_is_a_scholarly_chapter(record_type):
    rec = type("C", (), {"registry": "crossref", "record_type": record_type})()
    assert cs.class_from_record(rec) == (cs.SCHOLARLY_CHAPTER, None)


def test_a_journal_article_is_still_peer_reviewed_and_a_dataset_is_still_refused():
    """The new class must not widen what counts as a paper."""
    article = type("C", (), {"registry": "crossref", "record_type": "journal-article"})()
    dataset = type("C", (), {"registry": "crossref", "record_type": "dataset"})()
    assert cs.class_from_record(article) == (cs.PEER_REVIEWED, None)
    assert cs.class_from_record(dataset) == (None, "unsupported_record_type:dataset")


def test_a_chapter_has_its_own_identity_and_its_passage_is_its_pin():
    item = chapter_item()
    assert cs.item_key(item["identifiers"]) == "chapter:jstor:j.ctt5vkmnr.8"
    assert cs._pin_of(item) == hashlib.sha256(EXCERPT.encode()).hexdigest()


def test_changing_the_passage_changes_the_list_hash():
    """A frozen list cannot be quietly re-evidenced: the passage is part of what was approved."""
    item = chapter_item()
    pin = {"repo": "openai/math", "commit": "a" * 40}
    before = cs.list_hash(pin, [item])
    other = dict(item)
    other["confirmation"] = dict(item["confirmation"], excerpt_sha256="f" * 64)
    assert cs.list_hash(pin, [other]) != before


def test_a_chapter_counts_toward_the_minimum():
    """It is a scholarly source, not commentary: an episode may rest on chapters."""
    ok, counts = cs.minimum_check([chapter_item(), chapter_item(), chapter_item()])
    assert ok and counts["non_commentary"] == 3


# --- what the episode must say about it ----------------------------------------------------------------------------------------------
def test_the_status_clause_says_which_kind_of_publication_it_is():
    clause = ss.clause_for({"class": cs.SCHOLARLY_CHAPTER}, "unverified")
    assert clause == "a chapter in a scholarly book rather than a peer-reviewed journal article"


def test_the_clause_neither_claims_peer_review_nor_equates_a_book_with_a_posting():
    clause = ss.clause_for({"class": cs.SCHOLARLY_CHAPTER}, "unverified")
    assert "preprint" not in clause
    assert "has not been peer reviewed" not in clause       # that wording belongs to a company release


def test_a_script_that_names_a_chapter_must_call_it_a_chapter():
    item = chapter_item()
    script = f"HOST: Dauben's {TITLE} argues that the manuscripts record a reading, not a contribution."
    hits = cc.check_class_labels(script, [item])
    assert [h["kind"] for h in hits] == ["scholarly_chapter_not_labelled"]


def test_a_script_that_calls_it_a_chapter_passes():
    item = chapter_item()
    script = f"HOST: In a chapter of his 1995 book, Dauben's {TITLE} argues that the manuscripts record a reading."
    assert cc.check_class_labels(script, [item]) == []


def test_the_plan_announces_the_class_without_calling_it_peer_reviewed():
    heading = cm.CLASS_HEADINGS[cs.SCHOLARLY_CHAPTER]
    tag = cm.CLASS_TAGS[cs.SCHOLARLY_CHAPTER]
    assert "chapter" in heading.lower() and "not a peer-reviewed journal article" in tag


# --- the passage reaches the writer, and only the approved one does -------------------------------------------------------------------
def test_the_attached_passage_becomes_the_evidence_the_episode_is_written_from():
    item = chapter_item()
    run = run_of(base_items() + [item])
    got = next(i for i in run.items if i["class"] == cs.SCHOLARLY_CHAPTER)
    assert EXCERPT in got["evidence_text"]


def test_a_run_refuses_a_passage_that_is_not_the_one_approved():
    item = chapter_item()
    doc = approved_doc(base_items() + [item])
    swapped = dict(PRIVATE)
    swapped[item["item_id"]] = EXCERPT.replace("dissatisfied", "satisfied")
    with pytest.raises(cm.CuratedListError) as e:
        cm.CuratedRun.from_list_doc(doc, private_texts=swapped, topic="Marx and the calculus")
    assert "not the passage the list was approved with" in str(e.value)


def test_a_run_refuses_a_chapter_whose_passage_is_missing():
    item = chapter_item()
    doc = approved_doc(base_items() + [item])
    without = {k: v for k, v in PRIVATE.items() if k != item["item_id"]}
    with pytest.raises(cm.CuratedListError) as e:
        cm.CuratedRun.from_list_doc(doc, private_texts=without, topic="Marx and the calculus")
    assert "missing from the private store" in str(e.value)


def test_a_chapter_is_not_commentary():
    """Commentary keeps the reaction section in the plan and may not support a claim; a chapter is a source like any other."""
    item = chapter_item()
    run = run_of(base_items() + [item])
    assert run.commentary_pids() == [] or item["item_id"] not in [i for i in run.commentary_pids()]
    assert item["class"] != cs.COMMENTARY
