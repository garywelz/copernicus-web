"""Three things that stopped 017 being made, and one that stopped every earlier list being used at all.

1. Adding `release_text_sha256` to every row of `list_hash` changed the hash of lists that have no attached text, so every list approved
   before that change stopped matching its stored hash — and a frozen list cannot be re-approved. Eleven lists were unusable.
2. `unattributed_claims` read a source's title, abstract, evidence text and venue, but not the body that released it, so naming OpenAI in
   an episode built from OpenAI's own manuscript counted as naming a company no source names. The writer retreated to "this company's own
   manuscript", which the naming check then refused, and the coverage statement — which must name the company — became unwritable.
3. A mention naming no author needed three content words of a title to match one. "The irrationality exponent of pi is 2" keeps two once
   stopwords and short words are dropped, so naming it exactly could never match, and a listed manuscript was reported as unlisted.
"""
import hashlib
from types import SimpleNamespace

import curated_sources as cs
import named_work_check as nw
import unattributed_claims as uc

TEXT = "ABSTRACT. We prove the conjecture. THEOREM. The exponent is two."


def item(item_id, cls=cs.PREPRINT, title="A prior result", with_text=False):
    it = {"item_id": item_id, "class": cls, "title": title, "authors": ["A"], "year": 2011, "approved": True,
          "evidence_text": "An abstract.", "identifiers": {"arxiv": "1104.5100", "arxiv_version": "v1", "pmid": None, "doi": None},
          "confirmation": {"status": cs.CONFIRMED, "registry": "arxiv", "confirmed_at": "2026-11-20T00:00:00Z"}}
    if with_text:
        it["release_text"] = {"sha256": hashlib.sha256(TEXT.encode()).hexdigest(), "chars": len(TEXT),
                              "source_path": "preprints/x/build/main.tex"}
    return it


PIN = {"repo": "openai/math", "commit": "4eaee87548250b2682affda7d05d947c05554bae"}


def hash_as_before_release_text(pin, items):
    """`list_hash` as it was before attached text existed: no release_text key at all."""
    import json
    rows = sorted(({"id": i["item_id"], "class": i["class"], "key": cs.item_key(i["identifiers"]), "title": i.get("title"),
                    "evidence_sha256": i.get("text_sha256") or hashlib.sha256((i.get("evidence_text") or "").encode()).hexdigest(),
                    "blob_sha": cs._pin_of(i), "status": i.get("result_status"), "checked_by": i.get("checked_by")}
                   for i in cs.approved_items(items)), key=lambda r: r["id"])
    body = json.dumps({"pin": {"repo": pin.get("repo"), "commit": pin.get("commit")}, "items": rows},
                      sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(body.encode()).hexdigest()


def test_a_list_with_no_attached_text_hashes_as_it_always_did():
    items = [item("i1"), item("i2"), item("i3")]
    assert cs.list_hash(PIN, items) == hash_as_before_release_text(PIN, items)


def test_frontier_a_s_stored_hash_recomputes():
    """The real list, as it was approved on 2026-11-19: four confirmed peer-reviewed papers, no attached text."""
    papers = [
        ("i1", "De novo design of cysteine proteases.", "10.1038/s41586-026-11143-w"),
        ("i2", "Computational design of metalloproteases.", "10.1038/s41586-026-11167-2"),
        ("i3", "Computational design of metallohydrolases", "10.1038/s41586-025-09746-w"),
        ("i4", "Atom-level enzyme active site scaffolding using RFdiffusion2.", "10.1038/s41592-025-02975-x"),
    ]
    items = []
    for iid, title, doi in papers:
        it = item(iid, cls=cs.PEER_REVIEWED, title=title)
        it["identifiers"] = {"arxiv": None, "arxiv_version": None, "pmid": None, "doi": doi}
        items.append(it)
    # the two hashes must agree, whatever their value: that is what a frozen list depends on
    assert cs.list_hash(PIN, items) == hash_as_before_release_text(PIN, items)


def test_attached_text_still_changes_the_hash():
    plain = [item("i1"), item("i2", cls=cs.COMPANY_RELEASE, title="A release")]
    attached = [item("i1"), item("i2", cls=cs.COMPANY_RELEASE, title="A release", with_text=True)]
    assert cs.list_hash(PIN, plain) != cs.list_hash(PIN, attached), "swapping attached text must change what was approved"


# --- the company counts as named ---------------------------------------------------------------------------------------------------
def release(company="OpenAI"):
    return SimpleNamespace(pid="P1", title="The irrationality exponent of pi is 2", authors=[company], year=2026,
                           abstract="We prove the conjecture that the irrationality exponent of pi is 2.", venue=None,
                           record_type="company_release", source_class="company_release",
                           pin={"repo": "openai/math", "commit": "4eaee87", "company": company})


def test_naming_the_company_whose_release_is_listed_passes():
    script = "EXPERT: OpenAI's manuscripts are company releases that have not been peer reviewed.\n"
    assert uc.check(script, [release()]) == []


def test_the_coverage_statement_can_name_the_company():
    script = "EXPERT: The peer-reviewed papers reviewed here do not cover OpenAI's manuscript.\n"
    assert uc.check(script, [release()]) == []


def test_naming_an_unrelated_company_still_fails():
    script = "EXPERT: DeepMind built the model behind it.\n"
    kinds = [v["kind"] for v in uc.check(script, [release()])]
    assert kinds == ["named_body_without_source"]


def test_a_company_named_only_in_a_pin_is_enough():
    r = SimpleNamespace(pid="P1", title="A web release", authors=[], year=2026, abstract="A statement.", venue=None,
                        record_type="company_release", source_class="company_release", pin={"company": "Anthropic"})
    assert uc.check("EXPERT: Anthropic published the statement.\n", [r]) == []


# --- a title of two content words --------------------------------------------------------------------------------------------------
def test_a_title_of_two_content_words_can_be_named():
    paper = SimpleNamespace(pid="P1", title="The irrationality exponent of pi is 2", authors=["OpenAI"], year=2026,
                            abstract="We prove it.", venue=None, record_type="company_release", source_class="company_release")
    mention = {"quote": 'This company\'s own manuscript is titled "The irrationality exponent of pi is 2".', "authors": [],
               "year": None, "title_words": ["The", "irrationality", "exponent", "of", "pi", "is", "2"], "where": "script"}
    assert nw.match_mention(mention, [paper]) == "P1"
    assert len(nw._words(paper.title)) == 2, "the title really does reduce to two content words"


def test_a_different_title_containing_both_words_is_still_unlisted():
    """The short-title match is exact. A work whose title merely contains "irrationality exponent" must be reported as unlisted, not read
    as the listed manuscript."""
    listed = SimpleNamespace(pid="P1", title="The irrationality exponent of pi is 2", authors=["OpenAI"], year=2026,
                             abstract="We prove it.", venue=None, record_type="company_release", source_class="company_release")
    for other in ("Bounds on the irrationality exponent of other constants",
                  "An irrationality exponent survey",
                  "Irrationality, exponent growth and continued fractions"):
        mention = {"quote": f'a paper titled "{other}"', "authors": [], "year": None,
                   "title_words": other.split(), "where": "script"}
        assert nw.match_mention(mention, [listed]) is None, other


def test_the_exact_short_title_still_matches_whatever_order_it_is_given_in():
    listed = SimpleNamespace(pid="P1", title="The irrationality exponent of pi is 2", authors=["OpenAI"], year=2026,
                             abstract="We prove it.", venue=None, record_type="company_release", source_class="company_release")
    for words in (["The", "irrationality", "exponent", "of", "pi", "is", "2"], ["irrationality", "exponent"],
                  ["exponent", "of", "irrationality"]):
        mention = {"quote": "the manuscript on the irrationality exponent", "authors": [], "year": None,
                   "title_words": words, "where": "script"}
        assert nw.match_mention(mention, [listed]) == "P1", words


def test_a_partial_title_of_a_longer_work_still_does_not_match():
    paper = SimpleNamespace(pid="P1", title="Generative design of bacteriophages with genome language models", authors=["King"],
                            year=2026, abstract="We report it.", venue="Science", record_type="journal", source_class="peer_reviewed")
    mention = {"quote": "some work on bacteriophages", "authors": [], "year": None, "title_words": ["bacteriophages"],
               "where": "script"}
    assert nw.match_mention(mention, [paper]) is None, "one word of a long title is not enough to name it"
