"""The writer is given every transcribed passage and chapter excerpt in full, in a marked block, while a registry abstract keeps its
700-character cap; the rule against copying eight words in a row is checked against the passages; their text is kept out of the job and
episode records; and a Crossref title or author name entirely in capitals is shown in normal case without changing the stored record.

The first dry run of the revolutions list (2026-11-25) was written from each passage's first 700 characters, though the attribution
check read all of it. Offline: the registries are faked.
"""
import pytest

import curated_mode as cm
import curated_script as cscript
import curated_sources as cs
from tests.unit.test_curated_chapter import EXCERPT, chapter_item
from tests.unit.test_curated_mode import PRIVATE, approved_doc, base_items, run_of
from tests.unit.test_curated_supplied_abstract import DOI, Registries, no_abstract, run

TAIL = "THE SURVEYABILITY ARGUMENT AT THE END OF THE PASSAGE"
LONG_PASSAGE = ("On the Complexity of k-SAT. " + "The opening paragraph sets out the problem and its history at some length. " * 20
                + "And here, far past the first seven hundred characters, is " + TAIL + ".")
LONG_ABSTRACT = "A registry abstract that runs long. " * 40 + "ABSTRACT TAIL BEYOND THE CAP."


def passage_item(passage=LONG_PASSAGE):
    item = run(cs.confirm_with_passage(DOI, passage, "pp. 1-9", http_get=Registries(crossref_by_doi={DOI: no_abstract()})))
    PRIVATE[item["item_id"]] = item.pop("private_text")
    return item


def preprint_with_passage(abstract=LONG_ABSTRACT, passage=None):
    passage = passage or ("Redefining Revolutions. " + "Section three opens. " * 40 + "Dauben likens mathematical revolutions to the "
                          "Glorious Revolution of 1688, in the persistence of the old order.")
    ids = {"arxiv": "1810.07038", "arxiv_version": "v1"}
    item = {"item_id": cs.item_id(ids), "input": "arXiv:1810.07038", "class": cs.PREPRINT, "added_by": "gary", "identifiers": ids,
            "title": "Redefining Revolutions", "authors": ["Andrew Aberdein"], "year": 2018, "venue": None, "url": "https://arxiv.org/abs/1810.07038v1",
            "evidence_text": abstract, "approved": True, "result_status": None,
            "confirmation": {"status": cs.CONFIRMED, "pid": "", "title": "Redefining Revolutions", "authors": ["Andrew Aberdein"], "year": 2018,
                             "venue": None, "ids": {"arxiv": "1810.07038", "arxiv_version": "v1", "pmid": None, "doi": None},
                             "url": "https://arxiv.org/abs/1810.07038v1", "abstract": abstract, "registry": "arxiv", "confirmed_at": "",
                             "title_match": 1.0, "record_type": None, "source_class": cs.PREPRINT, "pin": None, "abstract_source": None}}
    rec = cs.passage_for_item(item, passage)
    item["passage"], item["limits"] = rec["passage"], [rec["limit"]]
    PRIVATE[item["item_id"]] = passage
    return item, passage


# --- the writer sees every passage in full -----------------------------------------------------------------------------------------------
def test_a_journal_passage_reaches_the_writer_whole_in_a_marked_block():
    item = passage_item()
    block = cscript.facts_block(run_of(base_items() + [item]))
    assert TAIL in block and LONG_PASSAGE.replace("  ", " ")[-200:] in block
    assert cscript.PASSAGE_OPEN in block and "Never copy eight or more consecutive words from a passage" in block
    assert "(no abstract; see its passage below)" in block


def test_a_chapter_excerpt_reaches_the_writer_whole():
    block = cscript.facts_block(run_of(base_items() + [chapter_item()]))
    assert EXCERPT[-120:] in block and cscript.PASSAGE_OPEN in block


def test_a_registry_abstract_keeps_its_cap_while_the_attached_passage_is_whole():
    item, passage = preprint_with_passage()
    block = cscript.facts_block(run_of(base_items() + [item]))
    assert "ABSTRACT TAIL BEYOND THE CAP" not in block                      # the abstract is still cut at 700 characters
    assert "Glorious Revolution of 1688" in block                          # the passage, far past 700 characters, is there
    assert block.count("Glorious Revolution of 1688") == 1                 # once, in its block, not again inside the abstract line


def test_sources_without_passages_are_listed_as_before():
    block = cscript.facts_block(run_of(base_items()))
    assert cscript.PASSAGE_OPEN not in block and "PASSAGES FROM THE SOURCES" not in block


# --- the copying rule covers passages -------------------------------------------------------------------------------------------------
def test_eight_words_copied_from_a_passage_are_refused():
    item, passage = preprint_with_passage()
    r = run_of(base_items() + [item])
    copied = "EXPERT: Dauben likens mathematical revolutions to the Glorious Revolution of 1688, in a striking image."
    kinds = [v["kind"] for v in r.checks(copied)]
    assert "verbatim_run" in kinds
    fine = "EXPERT: As quoted by Aberdein, Dauben compares such changes with England's revolution of 1688, when the old order survived."
    assert "verbatim_run" not in [v["kind"] for v in r.checks(fine)]


# --- the passages stay out of the records ---------------------------------------------------------------------------------------------
def test_no_passage_reaches_the_job_or_episode_record():
    item, passage = preprint_with_passage()
    j = passage_item()
    ch = chapter_item()
    r = run_of(base_items() + [item, j, ch])
    by_title = {p.title: p for p in r.confirmed_papers()}
    for title in ("Redefining Revolutions", "On the Complexity of k-SAT", ch["title"]):
        d = cm.storage_dict(by_title[title])
        assert d["abstract"] == "" and d["abstract_withheld"] is True, title
    plain = next(p for p in r.confirmed_papers() if p.title not in by_title or p.title == base_items()[0]["title"])
    assert cm.storage_dict(plain).get("abstract_withheld") is None          # an ordinary source is stored as before
    pids = r.private_text_pids()
    assert {r.pids[item["item_id"]], r.pids[j["item_id"]], r.pids[ch["item_id"]]} <= set(pids)
    assert r.pids[base_items()[0]["item_id"]] not in pids


# --- capitals shown in normal case, the record unchanged -------------------------------------------------------------------------------
def hales_item():
    doi = "10.1017/fmp.2017.1"
    authors = ["THOMAS HALES", "SEAN MCLAUGHLIN", "THI HOAI AN TA", "WEI LI", "JOHN SMITH III"]
    ids = {"doi": doi}
    conf = {"status": cs.CONFIRMED, "pid": "", "title": "A FORMAL PROOF OF THE KEPLER CONJECTURE", "authors": list(authors), "year": 2017,
            "venue": "Forum of Mathematics, Pi", "ids": {"arxiv": None, "arxiv_version": None, "pmid": None, "doi": doi},
            "url": f"https://doi.org/{doi}", "abstract": "This article describes a formal proof of the Kepler conjecture.", "registry": "crossref",
            "confirmed_at": "", "title_match": 1.0, "record_type": "journal-article", "source_class": cs.PEER_REVIEWED, "pin": None, "abstract_source": None}
    return {"item_id": cs.item_id(ids), "input": doi, "class": cs.PEER_REVIEWED, "added_by": "gary", "identifiers": ids,
            "title": conf["title"], "authors": list(authors), "year": 2017, "venue": conf["venue"], "url": conf["url"],
            "evidence_text": conf["abstract"], "approved": True, "result_status": None, "confirmation": conf}


def test_a_crossref_title_and_names_in_capitals_are_shown_in_normal_case_and_the_record_is_unchanged():
    item = hales_item()
    doc = approved_doc(base_items() + [item])
    stored = repr(doc)
    r = cm.CuratedRun.from_list_doc(doc, private_texts=dict(PRIVATE), topic="Kepler")
    got = next(i for i in r.items if i["item_id"] == item["item_id"])
    assert got["title"] == "A Formal Proof of the Kepler Conjecture"
    assert got["authors"] == ["Thomas Hales", "Sean McLaughlin", "Thi Hoai An Ta", "Wei Li", "John Smith III"]
    paper = next(p for p in r.confirmed_papers() if p.ids.get("doi") == "10.1017/fmp.2017.1")
    assert paper.title == "A Formal Proof of the Kepler Conjecture" and paper.authors[0] == "Thomas Hales"
    assert cm.source_line(paper, cs.PEER_REVIEWED).startswith("- Hales et al. (2017). A Formal Proof of the Kepler Conjecture.")
    assert repr(doc) == stored                                              # the stored record, and so its hash, is untouched
    assert cs.list_hash(doc["pin"], doc["items"]) == doc["list_hash"]


@pytest.mark.parametrize("title,expected", [
    ("PART II: THE CASE OF A LATTICE", "Part II: The Case of a Lattice"),
    ("ON THE NUMBER OF PRIMES, AND OF TWINS", "On the Number of Primes, and of Twins"),
    ("MIXING TIMES OF MARKOV CHAINS", "Mixing Times of Markov Chains"),
])
def test_title_case(title, expected):
    assert cm.title_case(title) == expected


def test_a_title_only_partly_in_capitals_or_from_another_registry_is_left_alone():
    item = hales_item()
    item["title"] = item["confirmation"]["title"] = "The DNA of KAM Theory"
    r = run_of(base_items() + [item])
    assert next(i for i in r.items if i["item_id"] == item["item_id"])["title"] == "The DNA of KAM Theory"
    other = hales_item()
    other["confirmation"]["registry"] = "arxiv"
    r = run_of(base_items() + [other])
    assert next(i for i in r.items if i["item_id"] == other["item_id"])["title"] == "A FORMAL PROOF OF THE KEPLER CONJECTURE"
