"""A journal article printed without an abstract may be evidenced by a passage the producer transcribed from it: confirmed against Crossref
as usual, pinned by the passage's hash, held privately, labelled, and refused in every case the supplied-abstract route refuses.

Also the two places where a chapter confirmed by its passage (curated_chapter) could not reach a run: the private text was loaded by no
route, and the paper could not be rebuilt from its record. Offline: the registries are faked.
"""
import hashlib

import pytest

import curated_mode as cm
import curated_sources as cs
import paper_confirmation as pc
from tests.unit.test_curated_chapter import EXCERPT, chapter_item
from tests.unit.test_curated_mode import PRIVATE, approved_doc, base_items, run_of
from tests.unit.test_curated_sources import crossref
from tests.unit.test_curated_supplied_abstract import DOI, Registries, no_abstract, run

TITLE = "On the Complexity of k-SAT"
PASSAGE = (
    "On the Complexity of k-SAT. The problem of deciding whether a formula in conjunctive normal form with at most k literals per clause is "
    "satisfiable is the canonical hard problem. We ask how its exact complexity grows with k, and we show that, unless the Exponential Time "
    "Hypothesis fails, the exponents of the best algorithms for k-SAT form an increasing sequence."
)


def attach(regs, doi=DOI, passage=PASSAGE, note="pp. 367-375"):
    return run(cs.confirm_with_passage(doi, passage, note, http_get=regs))


def passage_item(**extra):
    item = attach(Registries(crossref_by_doi={DOI: no_abstract()}))
    text = item.pop("private_text")
    item.update(extra)
    PRIVATE[item["item_id"]] = text
    return item


# --- confirmation ---------------------------------------------------------------------------------------------------------------------
def test_a_passage_confirms_a_journal_article_without_an_abstract_and_keeps_its_class():
    item = attach(Registries(crossref_by_doi={DOI: no_abstract()}))
    assert item["confirmation"]["status"] == cs.CONFIRMED and item["class"] == cs.PEER_REVIEWED
    assert item["title"] == TITLE and item["identifiers"]["doi"] == DOI          # title and identity come from Crossref, not the producer
    sha = hashlib.sha256(PASSAGE.encode()).hexdigest()
    assert item["passage"]["sha256"] == sha == item["limits"][0]["sha256"] and item["passage"]["chars"] == len(PASSAGE)
    assert item["passage"]["source_note"] == "pp. 367-375"
    assert item["limits"][0]["type"] == "passage_supplied" and item["limits"][0]["label"] == "passage transcribed by the producer"


def test_the_passage_is_never_in_the_record_only_handed_to_the_caller():
    item = attach(Registries(crossref_by_doi={DOI: no_abstract()}))
    text = item.pop("private_text")
    assert text == PASSAGE
    assert PASSAGE[:60] not in repr(item)                                     # not the evidence text, not the confirmation's abstract
    assert item["evidence_text"] == "" and item["confirmation"]["abstract"] == ""
    assert item["confirmation"]["abstract_source"] == cs.PASSAGE_SOURCE


def test_a_passage_from_the_wrong_article_is_refused():
    item = attach(Registries(crossref_by_doi={DOI: no_abstract()}), passage=PASSAGE.replace("On the Complexity of k-SAT.", "Elsewhere."))
    assert item["confirmation"]["reason"] == "title_not_in_passage" and "private_text" not in item


def test_the_title_is_found_through_typographic_quotes_a_registry_mangled():
    """Crossref holds Crowe 1975's title as 'Ten �Laws� concerning ...'; the printed title has curly quotes. Both flatten alike."""
    doi = "10.1016/0315-0860(75)90142-1"
    rec = no_abstract(doi=doi).replace(TITLE, "Ten \\ufffdLaws\\ufffd concerning patterns of change in the history of mathematics")
    text = ("TEN “LAWS” CONCERNING PATTERNS OF CHANGE IN THE HISTORY OF MATHEMATICS. " + PASSAGE)
    item = attach(Registries(crossref_by_doi={doi: rec}), doi=doi, passage=text)
    assert item["confirmation"]["status"] == cs.CONFIRMED, item["confirmation"]


def test_it_is_refused_when_the_registry_already_has_an_abstract():
    item = attach(Registries(crossref_by_doi={DOI: crossref("journal-article", doi=DOI)}))
    assert item["confirmation"]["reason"] == "registry_has_abstract" and not item.get("passage")


def test_only_a_journal_article_takes_a_passage():
    for rtype in ("posted-content", "book-chapter"):
        doi = f"10.1000/{rtype}"
        item = attach(Registries(crossref_by_doi={doi: no_abstract(rtype, doi)}), doi=doi)
        assert item["confirmation"]["status"] == cs.REFUSED, rtype
        assert not item.get("passage")


@pytest.mark.parametrize("kw,reason", [
    (dict(doi="1810.07038"), "passage_needs_a_doi"),
    (dict(passage="Too short to write from. On the Complexity of k-SAT."), "passage_length"),
    (dict(passage=PASSAGE * 200), "passage_length"),
    (dict(passage=PASSAGE + "\x00"), "passage_length"),
    (dict(note="x" * 301), "source_note_too_long"),
])
def test_bad_input_is_refused_before_any_registry_is_asked(kw, reason):
    regs = Registries(crossref_by_doi={DOI: no_abstract()})
    assert attach(regs, **kw)["confirmation"]["reason"] == reason and regs.calls == []


def test_a_down_registry_raises():
    with pytest.raises(pc.RegistryUnavailable):
        attach(Registries(down=True))


# --- the hash ---------------------------------------------------------------------------------------------------------------------------
def test_a_different_passage_changes_the_list_hash_and_lists_without_one_hash_as_before():
    a = attach(Registries(crossref_by_doi={DOI: no_abstract()}))
    b = attach(Registries(crossref_by_doi={DOI: no_abstract()}), passage=PASSAGE + " One more sentence.")
    pin = {"repo": "r", "commit": "c"}
    assert cs.list_hash(pin, [a]) != cs.list_hash(pin, [b])
    plain = base_items()
    before = cs.list_hash(pin, plain)
    assert all(not cs.has_passage(i) for i in plain) and cs.list_hash(pin, [dict(i) for i in plain]) == before


# --- the run ----------------------------------------------------------------------------------------------------------------------------
def test_the_passage_becomes_the_evidence_and_the_abstract_the_writer_sees():
    item = passage_item()
    r = run_of(base_items() + [item])
    got = next(i for i in r.items if i["item_id"] == item["item_id"])
    assert got["evidence_text"] == PASSAGE
    paper = next(p for p in r.confirmed_papers() if p.ids.get("doi") == DOI)
    assert paper.abstract == PASSAGE and paper.source_class == cs.PEER_REVIEWED
    assert item["confirmation"]["abstract"] == ""                           # the stored record is not changed by the run


def test_a_run_refuses_a_missing_or_swapped_passage():
    item = passage_item()
    doc = approved_doc(base_items() + [item])
    without = {k: v for k, v in PRIVATE.items() if k != item["item_id"]}
    with pytest.raises(cm.CuratedListError) as e:
        cm.CuratedRun.from_list_doc(doc, private_texts=without, topic="k-SAT")
    assert "missing from the private store" in str(e.value)
    swapped = dict(PRIVATE)
    swapped[item["item_id"]] = PASSAGE.replace("increasing", "decreasing")
    with pytest.raises(cm.CuratedListError) as e:
        cm.CuratedRun.from_list_doc(doc, private_texts=swapped, topic="k-SAT")
    assert "not the passage the list was approved with" in str(e.value)


def test_the_reference_line_is_labelled():
    item = passage_item()
    r = run_of(base_items() + [item])
    paper = next(p for p in r.confirmed_papers() if p.ids.get("doi") == DOI)
    line = cm.source_line(paper, cs.PEER_REVIEWED, None, None, item["limits"])
    assert line.endswith("(passage transcribed by the producer)") and f"DOI: {DOI}" in line


def test_every_item_whose_text_is_private_is_named_for_loading():
    assert cs.needs_private_text(passage_item())
    assert cs.needs_private_text(chapter_item())
    assert cs.needs_private_text({"class": cs.COMMENTARY, "approved": True})
    assert not cs.needs_private_text({"class": cs.COMMENTARY, "approved": False})
    assert cs.needs_private_text({"class": cs.COMPANY_RELEASE, "release_text": {"sha256": "x"}})
    assert not any(cs.needs_private_text(i) for i in base_items())


# --- a chapter confirmed by its passage reaches the writer ------------------------------------------------------------------------------
def test_a_chapter_confirmed_by_its_passage_becomes_a_paper_with_its_address_and_book():
    item = chapter_item()
    r = run_of(base_items() + [item])
    paper = next(p for p in r.confirmed_papers() if p.source_class == cs.SCHOLARLY_CHAPTER)
    assert paper.abstract == EXCERPT and paper.title == item["title"] and paper.year == 1995 and paper.authors == ["Joseph W. Dauben"]
    assert paper.venue == "Abraham Robinson: The Creation of Nonstandard Analysis" and paper.url == "https://www.jstor.org/stable/j.ctt5vkmnr.8"
    line = cm.source_line(paper, cs.SCHOLARLY_CHAPTER, None, None, item.get("limits"))
    assert line.startswith("- Dauben (1995). Marx, Hegel, and the Calculus.") and "https://www.jstor.org/stable/j.ctt5vkmnr.8" in line
