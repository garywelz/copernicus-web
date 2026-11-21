"""A company release's own text belongs to its own item.

Attaching a manuscript's statement of its result as a separate COMMENTARY item was the only way to give the checks something to trace a
claim to. It cost three things: the list then held "commentary", so `plan_sections` kept a reaction section with no reaction material and the
writer invented reactions; the company was described as a commentator on its own work; and two items whose titles matched one mention made
the naming check fail closed, reporting a listed manuscript as an unlisted work.
"""
import hashlib
import re
from pathlib import Path

import curated_checks as cc
import curated_mode
import curated_script as csr
import curated_sources as cs

BACKEND = Path(__file__).resolve().parents[2]
TEXT = "ABSTRACT. We prove the conjecture. THEOREM. The exponent is two. The argument does not give the threshold effectively."


def release_item(item_id="i1", with_text=True):
    item = {"item_id": item_id, "class": cs.COMPANY_RELEASE, "title": "The irrationality exponent of pi is 2",
            "authors": ["OpenAI"], "year": 2026, "url": "https://example.invalid/paper.pdf", "approved": True,
            "identifiers": {"repo": "openai/math", "commit": "4eaee87", "path": "preprints/x"},
            "evidence_text": "A one-paragraph abstract from the catalogue.",
            "result_status": cc.STATUS_UNVERIFIED,
            "confirmation": {"status": cs.CONFIRMED, "registry": "openai_math", "confirmed_at": "2026-11-20T00:00:00Z",
                             "repo": "openai/math", "commit": "4eaee87", "path": "preprints/x"}}
    if with_text:
        item["release_text"] = {"sha256": hashlib.sha256(TEXT.encode()).hexdigest(), "chars": len(TEXT),
                                "source_path": "preprints/x/build/main.tex", "note": "statement of the main result"}
    return item


def paper_item(item_id="i2"):
    return {"item_id": item_id, "class": cs.PREPRINT, "title": f"A prior result {item_id}", "authors": ["A"], "year": 2011,
            "url": "https://arxiv.org/abs/1104.5100", "approved": True, "evidence_text": "An abstract.",
            "identifiers": {"arxiv": f"1104.510{item_id[-1]}", "arxiv_version": "v1", "pmid": None, "doi": None},
            # a registry paper is rebuilt from its confirmation record, so the fixture carries what that record holds
            "confirmation": {"status": cs.CONFIRMED, "registry": "arxiv", "confirmed_at": "2026-11-20T00:00:00Z",
                             "title": f"A prior result {item_id}", "authors": ["A"], "year": 2011, "venue": None,
                             "ids": {"arxiv": f"1104.510{item_id[-1]}", "arxiv_version": "v1", "pmid": None, "doi": None},
                             "url": "https://arxiv.org/abs/1104.5100", "abstract": "An abstract.", "title_match": 1.0}}


def list_doc(items):
    pin = {"repo": "openai/math", "commit": "4eaee87548250b2682affda7d05d947c05554bae"}
    doc = {"list_id": "L1", "status": "approved", "pin": pin, "topic": "A topic", "items": items}
    doc["list_hash"] = cs.list_hash(pin, items)
    return doc


def test_attached_text_reaches_the_checks_as_the_manuscript_s_own_words():
    items = [release_item(), paper_item("i2"), paper_item("i3"), paper_item("i4")]
    run = curated_mode.CuratedRun.from_list_doc(list_doc(items), private_texts={"i1": TEXT})
    paper = next(p for p in run.confirmed_papers() if p.pid == "P1")
    assert "THEOREM" in paper.abstract and "catalogue" in paper.abstract, "the attached text is added to what the item already offered"
    assert paper.source_class == cs.COMPANY_RELEASE
    assert paper.record_type == "company_release"


def test_attaching_text_does_not_make_the_list_hold_commentary():
    items = [release_item(), paper_item("i2"), paper_item("i3"), paper_item("i4")]
    run = curated_mode.CuratedRun.from_list_doc(list_doc(items), private_texts={"i1": TEXT})
    assert all(i["class"] != cs.COMMENTARY for i in run.items)
    has_commentary = any(i["class"] == cs.COMMENTARY for i in run.items)
    plan = [s.key for s in csr.plan_sections(840, 1200, has_commentary=has_commentary)]
    assert "reaction" not in plan, "with no commentary there is no reaction section to invent reactions for"


def test_attached_text_has_no_title_of_its_own():
    """A separate item with a title like the manuscript's made the naming check fail closed on a tie."""
    items = [release_item(), paper_item("i2"), paper_item("i3"), paper_item("i4")]
    run = curated_mode.CuratedRun.from_list_doc(list_doc(items), private_texts={"i1": TEXT})
    titles = [p.title for p in run.confirmed_papers()]
    assert titles.count("The irrationality exponent of pi is 2") == 1, "only the manuscript carries its title"
    assert len(run.items) == 4


def test_text_that_does_not_match_the_approved_hash_refuses_the_run():
    items = [release_item(), paper_item("i2"), paper_item("i3"), paper_item("i4")]
    try:
        curated_mode.CuratedRun.from_list_doc(list_doc(items), private_texts={"i1": TEXT + " tampered"})
    except curated_mode.CuratedListError as e:
        assert "not the text the list was approved with" in str(e)
    else:
        raise AssertionError("a run must refuse attached text whose hash is not the approved one")


def test_missing_text_refuses_the_run():
    items = [release_item(), paper_item("i2"), paper_item("i3"), paper_item("i4")]
    try:
        curated_mode.CuratedRun.from_list_doc(list_doc(items), private_texts={})
    except curated_mode.CuratedListError as e:
        assert "missing from the private store" in str(e)
    else:
        raise AssertionError("a run must refuse when the attached text is gone")


def test_a_release_with_no_attached_text_is_unaffected():
    items = [release_item(with_text=False), paper_item("i2"), paper_item("i3"), paper_item("i4")]
    run = curated_mode.CuratedRun.from_list_doc(list_doc(items), private_texts={})
    assert next(p for p in run.confirmed_papers() if p.pid == "P1").abstract == "A one-paragraph abstract from the catalogue."


def test_the_route_exists_and_is_for_company_releases_only():
    text = (BACKEND / "endpoints" / "curated" / "routes.py").read_text(encoding="utf-8")
    assert re.search(r'@router\.post\("/api/admin/curated/lists/\{list_id\}/items/\{item_id\}/release-text"\)', text)
    assert re.search(r'@router\.delete\("/api/admin/curated/lists/\{list_id\}/items/\{item_id\}/release-text"\)', text)
    assert "Only a company release carries attached text" in text
    assert 'i.get("release_text")' in text, "every path that reads private texts must pass attached text too"


def test_the_request_model_records_where_the_text_came_from():
    from models.curated import AttachReleaseText
    body = AttachReleaseText(text=TEXT, source_path="preprints/x/build/main.tex", note="statement of the main result")
    assert body.source_path.endswith("main.tex") and body.note
    assert AttachReleaseText.model_fields["text"].metadata, "the text is bounded"
