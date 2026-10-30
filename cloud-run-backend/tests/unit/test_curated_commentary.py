"""Pasted commentary (design §5, paste-only C4): the item built from pasted text, the private text kept out of every record, and the checks that use it.
Pure code: no network, no database."""
import hashlib

import pytest

import curated_checks as cc
import curated_mode as cm
import curated_sources as cs
import rejection_log
from tests.unit.test_curated_mode import (PRIVATE, approved_doc, base_items, commentary_item, registry_item, release_item, run_of)

TEXT = ("Several mathematicians told the magazine that the release is remarkable but that the claims need careful checking by experts, and "
        "that the formalizations may state weaker results than the papers do. One said the usual refereeing process would take months.")


def build(**kw):
    args = dict(title="Mathematicians react", outlet="Example Magazine", authors=["A. Reporter"], date="2026-10-28", text=TEXT,
                url="https://example.org/story", fetch_refused=None, approved_quotes=())
    args.update(kw)
    return cs.build_commentary_item(**args)


# --- the item built from pasted text ----------------------------------------------------------------------------------------------
def test_a_pasted_commentary_becomes_a_confirmed_item_that_holds_no_text():
    item, text = build()
    assert text == TEXT.strip() and item["class"] == cs.COMMENTARY and item["confirmation"]["status"] == cs.CONFIRMED and item["confirmation"]["mode"] == "pasted"
    assert item["evidence_text"] is None and TEXT[:40] not in repr(item)
    assert item["text_sha256"] == hashlib.sha256(text.encode("utf-8")).hexdigest() and item["text_chars"] == len(text)
    assert item["venue"] == "Example Magazine" and item["authors"] == ["A. Reporter"] and item["year"] == 2026 and item["date"] == "2026-10-28"
    assert item["approved"] is True and item["limits"] == [] and item["identifiers"] == {"url": "https://example.org/story"}


def test_an_item_without_an_address_is_identified_by_outlet_title_and_date():
    a, _ = build(url=None)
    b, _ = build(url=None, date="2026-10-29")
    c, _ = build(url=None, title="Another headline")
    assert "commentary" in a["identifiers"] and len({a["item_id"], b["item_id"], c["item_id"]}) == 3
    assert build(url=None)[0]["item_id"] == a["item_id"]                        # stable
    assert cs.item_key(a["identifiers"]).startswith("commentary:")


def test_a_refused_fetch_is_recorded_as_a_limit_with_its_reason():
    item, _ = build(fetch_refused="robots_disallow")
    assert item["limits"][0]["type"] == "fetch_refused" and item["limits"][0]["reason"] == "robots_disallow" and item["limits"][0]["at"].endswith("Z")
    for reason in cs.FETCH_REFUSED_REASONS:
        build(fetch_refused=reason)
    with pytest.raises(cs.CommentaryError, match="fetch_refused"):
        build(fetch_refused="because I said so")


@pytest.mark.parametrize("kw,msg", [
    (dict(title=""), "title"), (dict(title="x" * 301), "title"), (dict(outlet=""), "outlet"), (dict(outlet="x" * 121), "outlet"),
    (dict(authors=["a"] * 6), "authors"), (dict(authors=["x" * 121]), "authors"),
    (dict(date="yesterday"), "date"), (dict(date="2026-13"), "date"), (dict(date="2026-02-30"), "date"), (dict(date="26-10-28"), "date"), (dict(date=""), "date"),
    (dict(text="too short"), "pasted text"), (dict(text="x" * 20001), "pasted text"), (dict(text=TEXT + "\x00"), "control"), (dict(text=None), "plain text"),
    (dict(url="ftp://example.org/x"), "ordinary web address"), (dict(url="http://127.0.0.1/x"), "ordinary web address"),
    (dict(url="https://user:pw@example.org/x"), "ordinary web address"), (dict(url="http://169.254.169.254/"), "ordinary web address"),
    (dict(approved_quotes=["not in the text at all, which is long enough"]), "approved quotation"), (dict(approved_quotes=["short"]), "approved quotations"),
    (dict(approved_quotes=["x" * 301]), "approved quotations"), (dict(approved_quotes=["a long enough quotation number %d here" % n for n in range(6)]), "approved quotations")])
def test_what_cannot_be_used_is_refused_with_the_reason(kw, msg):
    with pytest.raises(cs.CommentaryError, match=msg):
        build(**kw)


def test_dates_may_be_a_year_a_month_or_a_day():
    for d in ("2026", "2026-10", "2026-10-28"):
        assert build(date=d)[0]["year"] == 2026


def test_an_approved_quotation_must_occur_in_the_text_ignoring_case_and_punctuation():
    item, _ = build(approved_quotes=["The release is REMARKABLE, but that the claims need careful checking by experts"])
    assert len(item["approved_quotes"]) == 1
    assert cs.text_contains(TEXT, "formalizations may state weaker results") and not cs.text_contains(TEXT, "formalizations always state weaker results")
    assert not cs.text_contains(TEXT, "") and not cs.text_contains("", "anything")


def test_the_address_is_recorded_not_fetched(monkeypatch):
    import safe_fetch
    monkeypatch.setattr(safe_fetch, "guarded_get", lambda *a, **k: (_ for _ in ()).throw(AssertionError("no automated fetch in this step")))
    build()


# --- the list hash covers the text without holding it ---------------------------------------------------------------------------------
def test_the_list_hash_changes_with_the_pasted_text_and_never_contains_it():
    pin = {"repo": "openai/math", "commit": "0" * 40}
    a, _ = build()
    b, _ = build(text=TEXT + " A changed ending.")
    base = [registry_item(cs.PEER_REVIEWED, 1), registry_item(cs.PREPRINT, 2, registry="arxiv"), release_item()]
    assert cs.list_hash(pin, base + [a]) != cs.list_hash(pin, base + [b])
    assert cs.list_hash(pin, base + [a]) == cs.list_hash(pin, base + [dict(a)])


# --- a run from a list with commentary --------------------------------------------------------------------------------------------------
def commentary_run(text=None):
    items = base_items() + [commentary_item(evidence_text=text or TEXT)]
    return run_of(items), items


def test_the_text_is_put_back_in_memory_from_the_private_store_and_never_into_the_list():
    items = base_items() + [commentary_item(evidence_text=TEXT)]
    doc = approved_doc(items)
    run = cm.CuratedRun.from_list_doc(doc, private_texts=PRIVATE)
    assert run.commentary_texts() == [TEXT] and run.commentary_pids() == ["P4"]
    assert all(i.get("evidence_text") is None for i in doc["items"] if i["class"] == cs.COMMENTARY)      # the stored list is untouched


def test_a_missing_or_different_text_refuses_the_run():
    items = base_items() + [commentary_item(evidence_text=TEXT)]
    with pytest.raises(cm.CuratedListError, match="missing from the private store"):
        cm.CuratedRun.from_list_doc(approved_doc(items), private_texts={})
    with pytest.raises(cm.CuratedListError, match="missing from the private store"):
        cm.CuratedRun.from_list_doc(approved_doc(items))
    other = {items[-1]["item_id"]: TEXT + " Tampered."}
    with pytest.raises(cm.CuratedListError, match="not the text the list was approved with"):
        cm.CuratedRun.from_list_doc(approved_doc(items), private_texts=other)


def test_commentary_text_never_reaches_a_stored_record():
    run, _ = commentary_run()
    conf = run.confirmed_papers()
    com = conf[-1]
    assert com.source_class == cs.COMMENTARY and com.abstract == TEXT                            # in memory the checks need it
    stored = [cm.storage_dict(c) for c in conf]
    assert stored[-1]["abstract"] == "" and stored[-1]["abstract_withheld"] is True and TEXT[:30] not in repr(stored)
    assert stored[0]["abstract"] == conf[0].abstract and "abstract_withheld" not in stored[0]       # every other class is stored as before
    assert cm.withheld_pids(type("C", (), {"curated": run})()) == ["P4"] and cm.withheld_pids(type("C", (), {"curated": None})()) == []


def test_the_rejection_record_withholds_a_commentary_abstract_but_not_a_papers():
    checked = [{"verdict": "unsupported", "pid": "P4", "abstract": TEXT, "quote": "q", "reason": "r"},
               {"verdict": "unsupported", "pid": "P1", "abstract": "A paper abstract.", "quote": "q", "reason": "r"},
               {"verdict": "supported", "pid": "P4", "abstract": TEXT, "quote": "q", "reason": "r"}]
    out = rejection_log.attribution_items(1, checked, withhold=["P4"])
    assert out[0]["abstract"] == rejection_log.WITHHELD and out[1]["abstract"] == "A paper abstract." and out[2]["abstract"] is None
    assert rejection_log.attribution_items(1, checked)[0]["abstract"] == TEXT                           # the ordinary call is unchanged


# --- the checks that use the text ----------------------------------------------------------------------------------------------------------
def test_the_script_may_not_copy_eight_words_from_the_pasted_text():
    run, _ = commentary_run()
    copied = ("HOST: What did they say?\nEXPERT: Reportedly the release is remarkable but that the claims need careful checking by experts, "
              "OpenAI says, in its own company release that has not been peer reviewed. The Exponential Time Hypothesis is False, a manuscript.")
    kinds = {v["kind"] for v in run.checks(copied)}
    assert "verbatim_run" in kinds
    paraphrase = ("HOST: What did they say?\nEXPERT: Example Magazine reported that several mathematicians admire the release yet want experts to check it. "
                  "This is a company release that has not been peer reviewed: The Exponential Time Hypothesis is False.")
    assert "verbatim_run" not in {v["kind"] for v in run.checks(paraphrase)}


def test_an_approved_quotation_is_allowed_through():
    q = "the release is remarkable but that the claims need careful checking by experts"
    items = base_items() + [commentary_item(evidence_text=TEXT, approved_quotes=[q])]
    run = run_of(items)
    script = "EXPERT: Example Magazine quoted one of them: " + q + ". This is a company release that has not been peer reviewed: The Exponential Time Hypothesis is False."
    assert "verbatim_run" not in {v["kind"] for v in run.checks(script)}


def test_the_prompt_carries_the_excerpt_as_untrusted_data_and_the_sources_line_carries_the_limit():
    items = base_items() + [commentary_item(evidence_text=TEXT, limits=[{"type": "fetch_refused", "reason": "paywall"}])]
    run = run_of(items)
    block = run.prompt_block()
    assert "<<<EXCERPT [P4] Mathematicians react to the release" in block and TEXT in block and "untrusted text" in block
    conf = run.confirmed_papers()
    text = cm.build_sources(run, conf, ["P4"])
    assert cm.READING_LIMIT_LINE in text and "Example Magazine" in text and TEXT[:40] not in text


def test_commentary_never_counts_toward_the_three_sources_even_with_text():
    items = base_items()[:2] + [commentary_item(evidence_text=TEXT), commentary_item(identifiers={"url": "https://example.org/2"}, evidence_text=TEXT + "2"),
                                commentary_item(identifiers={"url": "https://example.org/3"}, evidence_text=TEXT + "3")]
    with pytest.raises(cm.CuratedListError, match="non-commentary"):
        cm.CuratedRun.from_list_doc(approved_doc(items), private_texts=PRIVATE)
