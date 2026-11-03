"""A peer-reviewed paper whose Crossref record has no abstract may carry the paper's own published abstract, supplied by the producer from the
publisher's page: stored with its hash and page address, labelled, and checked exactly like a registry abstract. Offline: the registries are faked."""
import asyncio
import json

import pytest

import curated_mode as cm
import curated_sources as cs
import paper_confirmation as pc
from tests.unit import test_curated_sources as tcs
from tests.unit.test_curated_sources import crossref

DOI = "10.1006/jcss.2000.1727"
PAGE = "https://www.sciencedirect.com/science/article/pii/S0022000000917274"
ABSTRACT = ("We first present a family of algorithms for k-SAT and then show that the complexity of k-SAT grows with k, and that the exponent of the best "
            "known algorithms is an increasing sequence of numbers, unless the Exponential Time Hypothesis fails. This is the paper's own abstract text.")


class Registries(tcs.Registries):
    """The shared fake, plus PubMed's search by DOI (the ordinary confirmation asks it when Crossref has no abstract): it knows no such paper."""
    async def __call__(self, url, params):
        if "esearch" in url and not self.down:
            self.calls.append(url)
            return 200, json.dumps({"esearchresult": {"idlist": []}})
        return await super().__call__(url, params)


def run(coro):
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


def no_abstract(rtype="journal-article", doi=DOI):
    return json.dumps({"message": {"title": ["On the Complexity of k-SAT"], "DOI": doi, "type": rtype, "issued": {"date-parts": [[2001, 3]]},
                                   "container-title": ["Journal of Computer and System Sciences"],
                                   "author": [{"given": "Russell", "family": "Impagliazzo"}, {"given": "Ramamohan", "family": "Paturi"}]}})


def supply(regs, doi=DOI, abstract=ABSTRACT, url=PAGE):
    return run(cs.confirm_with_supplied_abstract(doi, abstract, url, http_get=regs))


def test_the_ordinary_route_still_refuses_a_record_without_an_abstract():
    item = run(cs.confirm_registry_item(cs.parse_item(DOI), http_get=Registries(crossref_by_doi={DOI: no_abstract()})))
    assert item["confirmation"]["reason"] == "no_abstract"


def test_a_supplied_abstract_confirms_a_journal_article_and_is_stored_with_its_hash_and_page():
    item = supply(Registries(crossref_by_doi={DOI: no_abstract()}))
    assert item["confirmation"]["status"] == cs.CONFIRMED and item["class"] == cs.PEER_REVIEWED
    assert item["evidence_text"] == ABSTRACT and item["confirmation"]["abstract_source"] == "producer_supplied"
    import hashlib
    assert item["confirmation"]["abstract_sha256"] == hashlib.sha256(ABSTRACT.encode()).hexdigest() == item["limits"][0]["sha256"]
    assert item["confirmation"]["abstract_source_url"] == PAGE == item["limits"][0]["url"]
    assert item["limits"][0]["type"] == "abstract_supplied" and item["limits"][0]["label"] == "abstract supplied by the producer"
    assert item["title"] == "On the Complexity of k-SAT" and item["identifiers"]["doi"] == DOI      # the title and identity come from Crossref, not the producer


def test_the_supplied_abstract_is_what_the_attribution_check_reads_and_the_reference_line_is_labelled():
    item = supply(Registries(crossref_by_doi={DOI: no_abstract()}))
    c = cm.confirmed_from_item(item, "P3")
    assert c.abstract == ABSTRACT and c.source_class == cs.PEER_REVIEWED and c.abstract_source == "producer_supplied"
    line = cm.source_line(c, cs.PEER_REVIEWED, None, None, item["limits"])
    assert line.endswith("(abstract supplied by the producer)")
    assert "(abstract supplied by the producer)" not in cm.source_line(c, cs.PEER_REVIEWED, None, None, [])


def test_a_different_abstract_changes_the_list_hash():
    a = supply(Registries(crossref_by_doi={DOI: no_abstract()}))
    b = supply(Registries(crossref_by_doi={DOI: no_abstract()}), abstract=ABSTRACT + " Extra sentence.")
    pin = {"repo": "r", "commit": "c"}
    assert cs.list_hash(pin, [a]) != cs.list_hash(pin, [b]) and cs.list_hash(pin, [a]) == cs.list_hash(pin, [dict(a)])


def test_it_is_refused_when_the_registry_already_has_an_abstract():
    item = supply(Registries(crossref_by_doi={DOI: crossref("journal-article", doi=DOI)}))
    assert item["confirmation"]["reason"] == "registry_has_abstract" and not item.get("limits")


@pytest.mark.parametrize("kw,reason", [
    (dict(doi="2401.01234"), "supplied_abstract_needs_a_doi"),
    (dict(abstract="Too short."), "supplied_abstract_length"),
    (dict(abstract="x" * 4001), "supplied_abstract_length"),
    (dict(abstract=ABSTRACT + "\x00"), "supplied_abstract_length"),
    (dict(url="http://publisher.example/paper"), "supplied_abstract_page"),
    (dict(url="https://nodots"), "supplied_abstract_page"),
    (dict(url=""), "supplied_abstract_page"),
])
def test_bad_input_is_refused_before_any_registry_is_asked(kw, reason):
    regs = Registries(crossref_by_doi={DOI: no_abstract()})
    assert supply(regs, **kw)["confirmation"]["reason"] == reason and regs.calls == []


def test_only_a_journal_article_takes_a_supplied_abstract():
    doi = "10.1101/p"
    item = supply(Registries(crossref_by_doi={doi: no_abstract("posted-content", doi)}), doi=doi)
    assert item["confirmation"]["status"] == cs.REFUSED
    doi = "10.1000/b"
    item = supply(Registries(crossref_by_doi={doi: no_abstract("book", doi)}), doi=doi)
    assert item["confirmation"]["reason"].startswith("unsupported_record_type")


def test_a_doi_the_registry_does_not_know_is_refused_and_a_down_registry_raises():
    assert supply(Registries())["confirmation"]["reason"] == "not_found"
    with pytest.raises(pc.RegistryUnavailable):
        supply(Registries(down=True))


def test_the_ordinary_confirmation_ignores_supplied_abstracts_for_other_dois_and_leaves_no_trace_on_normal_records():
    regs = Registries(crossref_by_doi={DOI: no_abstract(), "10.1000/j": crossref("journal-article", doi="10.1000/j")})
    other = run(cs.confirm_registry_item(cs.parse_item(DOI), http_get=regs, supplied_abstracts={"10.9999/other": ABSTRACT}))
    assert other["confirmation"]["reason"] == "no_abstract"
    normal = run(cs.confirm_registry_item(cs.parse_item("10.1000/j"), http_get=regs, supplied_abstracts={"10.1000/j": ABSTRACT}))
    assert normal["evidence_text"] != ABSTRACT and normal["confirmation"]["abstract_source"] is None      # a registry abstract always wins
