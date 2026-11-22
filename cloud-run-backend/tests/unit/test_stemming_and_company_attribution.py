"""A plural is the same subject as its singular, and a company's name is its own release's name.

Both came from refusing good text. The scope check compared exact tokens, so a script saying "diseases" was refused although its source
said "disease-associated", and "therapeutic" was refused against "therapeutics" — on a script already published. The attribution check
read "OpenAI's" as a credited source it did not know, because the tokeniser keeps the apostrophe and the company was hard-coded as the
bare word; the required coverage statement, which must name the company, could never pass.
"""
from types import SimpleNamespace

import pytest

import curated_attribution as ca
import curated_sources as cs
import unattributed_claims as uc


def source(title="Computational design of metalloproteases", abstract=None, authors=("Chen",), venue="Nature"):
    return SimpleNamespace(pid="P1", title=title, authors=list(authors), year=2026, venue=venue,
                           abstract=abstract or ("We design metalloproteases that selectively cleave the human disease-associated "
                                                 "proteins TDP-43, amyloid-beta and serum amyloid A. Thus de novo design can yield "
                                                 "proteases with applications in therapeutics, biotechnology and bioremediation."),
                           record_type="journal", source_class=cs.PEER_REVIEWED)


# --- stemming ---------------------------------------------------------------------------------------------------------------------
def test_a_plural_matches_a_singular_the_sources_use():
    """The published proteases episode asks "could target proteins involved in diseases?"; its source says "disease-associated"."""
    assert uc.check("EXPERT: So, these could target proteins involved in diseases?\n", [source()]) == []


def test_a_singular_matches_a_plural_the_sources_use():
    """And it says "new therapeutic targets" where the source says "applications in therapeutics"."""
    assert uc.check("EXPERT: Watch for industrial processes or new therapeutic targets.\n", [source()]) == []


def test_a_word_the_sources_never_use_is_still_refused():
    assert [v["kind"] for v in uc.check("EXPERT: The designs work in a cell.\n", [source()])] == ["scope_widened"]
    assert [v["kind"] for v in uc.check("EXPERT: It was tested in patients.\n", [source()])] == ["scope_widened"]


def test_a_longer_word_is_not_a_source_for_a_shorter_one():
    """Stemming must not reopen the substring hole: "excellent" is not a source for "cell"."""
    excellent = source(title="An excellent result", abstract="The result was excellent and the process transmitted onward.")
    assert [v["kind"] for v in uc.check("EXPERT: The designs work in a cell.\n", [excellent])] == ["scope_widened"]
    assert [v["kind"] for v in uc.check("EXPERT: MIT built it.\n", [excellent])] == ["named_body_without_source"]


@pytest.mark.parametrize("word,expected", [("diseases", "disease"), ("disease", "disease"), ("therapeutics", "therapeutic"),
                                           ("therapeutic", "therapeutic"), ("cells", "cell"), ("cell", "cell"),
                                           ("bodies", "body"), ("excellent", "excellent"), ("process", "process"), ("ss", "ss")])
def test_the_stem_is_the_same_from_either_side(word, expected):
    assert uc.stem(word) == expected


# --- a listed company is a listed source ---------------------------------------------------------------------------------------
def release_list_doc():
    pin = {"repo": "openai/math", "commit": "4eaee87548250b2682affda7d05d947c05554bae"}
    items = [{"item_id": "i1", "class": cs.COMPANY_RELEASE, "title": "The irrationality exponent of pi is 2", "authors": ["OpenAI"],
              "year": 2026, "url": "https://example.invalid/p.pdf", "approved": True, "evidence_text": "We prove the conjecture.",
              "result_status": "unverified", "company": "OpenAI",
              "identifiers": {"repo": "openai/math", "commit": "4eaee87", "path": "preprints/x"},
              "confirmation": {"status": cs.CONFIRMED, "registry": "openai_math", "confirmed_at": "2026-11-20T00:00:00Z",
                               "repo": "openai/math", "commit": "4eaee87", "path": "preprints/x", "company": "OpenAI"}}]
    for n, (t, arx) in enumerate([("A prior bound", "1912.06345"), ("A second prior bound", "1104.5100"),
                                  ("A third prior bound", "2609.11276")], start=2):
        items.append({"item_id": f"i{n}", "class": cs.PREPRINT, "title": t, "authors": ["A"], "year": 2019, "approved": True,
                      "evidence_text": "An abstract.", "url": f"https://arxiv.org/abs/{arx}",
                      "identifiers": {"arxiv": arx, "arxiv_version": "v1", "pmid": None, "doi": None},
                      "confirmation": {"status": cs.CONFIRMED, "registry": "arxiv", "confirmed_at": "2026-11-20T00:00:00Z",
                                       "title": t, "authors": ["A"], "year": 2019, "venue": None, "abstract": "An abstract.",
                                       "ids": {"arxiv": arx, "arxiv_version": "v1", "pmid": None, "doi": None},
                                       "url": f"https://arxiv.org/abs/{arx}", "title_match": 1.0}})
    doc = {"list_id": "L1", "status": "approved", "pin": pin, "topic": "A topic", "items": items}
    doc["list_hash"] = cs.list_hash(pin, items)
    return doc


def router():
    import curated_mode
    return ca.Router(curated_mode.CuratedRun.from_list_doc(release_list_doc()))


def test_the_coverage_statement_naming_the_company_is_not_an_unknown_source():
    r = router()
    _, unknown = r.persons_credited("The papers reviewed here do not cover OpenAI's claims.")
    assert unknown == [], unknown


def test_a_possessive_company_in_any_sentence_resolves():
    r = router()
    for sentence in ("The key is independent verification of OpenAI's claim that the exponent is exactly two.",
                     "OpenAI's manuscript has not been peer reviewed.",
                     "OpenAI says the exponent is two."):
        _, unknown = r.persons_credited(sentence)
        assert unknown == [], f"{sentence}: {unknown}"


def test_another_company_on_the_same_list_still_fails():
    r = router()
    _, unknown = r.persons_credited("DeepMind's claim is the one to watch.")
    assert unknown, "a company with no release on the list is still an uncited source"


def test_the_companies_come_from_the_list_not_from_a_hard_coded_name():
    r = router()
    assert "openai" in r.companies
    src = (__import__("pathlib").Path(ca.__file__)).read_text(encoding="utf-8")
    assert '{"openai", "lean"}' not in src, "the company must be read from the list, so another company's release works too"
