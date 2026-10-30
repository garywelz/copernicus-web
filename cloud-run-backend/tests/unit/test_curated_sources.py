"""Curated source lists: intake parsing, class assignment, confirmation, the minimum rule and the list hash (design §2, §3).
Offline: the registries and the repository are faked."""
import asyncio
import copy
import json
import os

import pytest

import curated_sources as cs
import openai_math_index as omi
import openai_math_status as oms
from tests.unit.repo_fake import FakeRepo, standard_trees, WEIL, OLD_EDITION, QRH_SEPT, QRH_OCT
import paper_confirmation as pc
from safe_fetch import FetchResult

PIN = omi.DEFAULT_COMMIT
FIXTURE = os.path.join(os.path.dirname(os.path.dirname(__file__)), "fixtures", "openai_math_contents_excerpt.md")


def run(coro):
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


# --- fakes (same shapes as tests/unit/test_paper_confirmation.py) ----------------------------------------------------------------
ATOM = """<?xml version="1.0"?><feed xmlns="http://www.w3.org/2005/Atom">{entries}</feed>"""
ENTRY = """<entry><id>http://arxiv.org/abs/{id}</id><published>{pub}</published><title>{title}</title>
<summary>  {summary}  </summary><author><name>Ada Lovelace</name></author></entry>"""
ART = """<PubmedArticleSet><PubmedArticle><MedlineCitation><PMID>{pmid}</PMID><Article><Journal><JournalIssue><PubDate><Year>2024</Year></PubDate></JournalIssue>
<Title>Journal of Tests</Title></Journal><ArticleTitle>{title}</ArticleTitle><Abstract><AbstractText>{abstract}</AbstractText></Abstract>
<AuthorList><Author><LastName>Curie</LastName><ForeName>Marie</ForeName></Author></AuthorList></Article></MedlineCitation>
<PubmedData><ArticleIdList><ArticleId IdType="doi">10.1000/pm</ArticleId></ArticleIdList></PubmedData></PubmedArticle></PubmedArticleSet>"""


def crossref(rtype, title="A Crossref Paper", doi="10.1000/x1"):
    return json.dumps({"message": {"title": [title], "DOI": doi, "type": rtype, "issued": {"date-parts": [[2024]]},
                                   "container-title": ["Some Venue"], "abstract": "<jats:p>An abstract.</jats:p>",
                                   "author": [{"given": "Grace", "family": "Hopper"}]}})


def datacite(rtype, doi, title="A DataCite Record"):
    return json.dumps({"data": {"attributes": {"doi": doi, "titles": [{"title": title}], "publicationYear": 2025,
                                               "creators": [{"familyName": "Lee", "givenName": "Sam"}],
                                               "descriptions": [{"descriptionType": "Abstract", "description": "An abstract."}],
                                               "types": {"resourceTypeGeneral": rtype}}}})


class Registries:
    def __init__(self, crossref_by_doi=None, datacite_by_doi=None, arxiv_status=200, down=False):
        self.crossref_by_doi, self.datacite_by_doi = crossref_by_doi or {}, datacite_by_doi or {}
        self.arxiv_status, self.down = arxiv_status, down
        self.calls = []

    async def __call__(self, url, params):
        self.calls.append(url)
        if self.down:
            return 503, ""
        if "export.arxiv.org" in url:
            ids = params["id_list"].split(",")
            entries = "".join(ENTRY.format(id=i, pub="2025-01-02T00:00:00Z", title="An arXiv Preprint", summary="An arXiv abstract.") for i in ids)
            return self.arxiv_status, ATOM.format(entries=entries)
        if "efetch" in url:
            return 200, ART.format(pmid=params["id"], title="A PubMed Paper", abstract="A PubMed abstract.")
        if "api.crossref.org" in url:
            doi = url.split("/works/")[1]
            return (200, self.crossref_by_doi[doi]) if doi in self.crossref_by_doi else (404, "")
        if "api.datacite.org" in url:
            doi = url.split("/dois/")[1]
            return (200, self.datacite_by_doi[doi]) if doi in self.datacite_by_doi else (404, "")
        return 500, ""


def RepoFetch(trees=None, status=200):
    """The pinned repository, with the standard trees unless others are given (a map status other than 200 makes the repository unreadable)."""
    return FakeRepo(trees=trees if trees is not None else standard_trees(), map_status=status)


@pytest.fixture(autouse=True)
def _clear_cache():
    omi._INDEX_CACHE.clear(); oms._LEAN_CACHE.clear(); oms._HISTORY_CACHE.clear()
    yield
    omi._INDEX_CACHE.clear(); oms._LEAN_CACHE.clear(); oms._HISTORY_CACHE.clear()


ETH = "The-Exponential-Time-Hypothesis-is-False-October-25-2026"
HADWIGER = "A-counterexample-to-Hadwigers-conjecture-September-23-2026"


def confirm(raw, regs=None, repo=None):
    return run(cs.confirm_pasted(raw, PIN, http_get=regs or Registries(), fetch=repo or RepoFetch()))


# --- parsing what Gary pastes ---------------------------------------------------------------------------------------------------------
@pytest.mark.parametrize("raw,kind", [
    ("2501.01234", "arxiv"), ("arXiv:2501.01234v2", "arxiv"), ("https://arxiv.org/abs/2501.01234v1", "arxiv"), ("https://arxiv.org/pdf/2501.01234", "arxiv"),
    ("https://doi.org/10.48550/arXiv.2501.01234", "arxiv"),
    ("10.1000/abc.123", "doi"), ("doi:10.1000/abc.123", "doi"), ("https://doi.org/10.1000/abc.123", "doi"), ("https://dx.doi.org/10.1000/abc.123", "doi"),
    ("12345678", "pmid"), ("PMID: 12345678", "pmid"), ("https://pubmed.ncbi.nlm.nih.gov/12345678/", "pmid"),
    ("family 378", "repo"), ("preprints/Foo-October-1-2026", "repo"), ("https://github.com/openai/math/tree/x/preprints/Foo-October-1-2026", "repo"),
    ("https://www.quantamagazine.org/some-story/", "url"), ("http://example.org/post", "url"),
    ("", "invalid"), ("   ", "invalid"), ("378", "invalid"), ("not a source", "invalid"), ("x" * 600, "invalid"), (12345, "invalid"), (None, "invalid")])
def test_what_gary_pastes_is_recognised_by_shape(raw, kind):
    assert cs.parse_item(raw).kind == kind


def test_an_arxiv_version_is_kept():
    assert cs.parse_item("arXiv:2501.01234v3").ids_url == "https://arxiv.org/abs/2501.01234v3"


def test_a_doi_is_normalised():
    assert cs.parse_item("DOI:10.1000/ABC").ids_doi == pc.normalize_doi("10.1000/ABC")


# --- classes from registry records ---------------------------------------------------------------------------------------------------------
def test_an_arxiv_id_is_a_preprint_and_keeps_its_version():
    items = confirm("arXiv:2501.01234v2")
    assert len(items) == 1 and items[0]["class"] == cs.PREPRINT and items[0]["confirmation"]["status"] == cs.CONFIRMED
    assert items[0]["identifiers"]["arxiv"] == "2501.01234" and items[0]["identifiers"]["arxiv_version"] == "v2"
    assert items[0]["confirmation"]["source_class"] == cs.PREPRINT and items[0]["evidence_text"] == "An arXiv abstract."


def test_a_pubmed_record_is_peer_reviewed():
    items = confirm("PMID: 12345678")
    assert items[0]["class"] == cs.PEER_REVIEWED and items[0]["identifiers"]["pmid"] == "12345678"


def test_a_crossref_journal_article_is_peer_reviewed_and_posted_content_is_a_preprint():
    regs = Registries(crossref_by_doi={"10.1000/j": crossref("journal-article", doi="10.1000/j"), "10.1101/p": crossref("posted-content", doi="10.1101/p")})
    assert confirm("10.1000/j", regs)[0]["class"] == cs.PEER_REVIEWED
    assert confirm("https://doi.org/10.1101/p", regs)[0]["class"] == cs.PREPRINT


@pytest.mark.parametrize("rtype", ["dataset", "report", "book", "proceedings-article", "component", "peer-review", None])
def test_other_crossref_record_types_are_refused_with_the_type_named(rtype):
    regs = Registries(crossref_by_doi={"10.1000/o": crossref(rtype, doi="10.1000/o")})
    it = confirm("10.1000/o", regs)[0]
    assert it["confirmation"]["status"] == cs.REFUSED and it["confirmation"]["reason"].startswith("unsupported_record_type")
    assert it["item_id"] is None and it["approved"] is False


def test_a_zenodo_record_of_a_publication_type_is_a_preprint_and_a_dataset_is_refused():
    regs = Registries(datacite_by_doi={"10.5281/zenodo.1": datacite("Preprint", "10.5281/zenodo.1"),
                                       "10.5281/zenodo.2": datacite("Dataset", "10.5281/zenodo.2")})
    assert confirm("10.5281/zenodo.1", regs)[0]["class"] == cs.PREPRINT
    refused = confirm("10.5281/zenodo.2", regs)[0]
    assert refused["confirmation"]["status"] == cs.REFUSED and refused["confirmation"]["reason"] == "not_publication_type"


def test_an_unknown_doi_is_refused_not_found_and_an_unreachable_registry_raises():
    it = confirm("10.1000/nothing", Registries())[0]
    assert it["confirmation"] == {"status": cs.REFUSED, "reason": "not_found", "detail": "", "directories": []}
    with pytest.raises(pc.RegistryUnavailable):
        confirm("10.1000/nothing", Registries(down=True))


def test_a_confirmed_registry_item_carries_registry_fields_not_pasted_ones():
    it = confirm("PMID: 12345678")[0]
    assert it["title"] == "A PubMed Paper" and it["authors"] == ["Marie Curie"] and it["year"] == 2024 and it["venue"] == "Journal of Tests"
    assert it["confirmation"]["registry"] == "pubmed" and it["added_by"] == "gary" and it["approved"] is True


# --- company releases -------------------------------------------------------------------------------------------------------------------------
def test_a_named_manuscript_is_a_company_release_with_its_pin():
    it = confirm(f"preprints/{ETH}")[0]
    assert it["class"] == cs.COMPANY_RELEASE and it["confirmation"]["status"] == cs.CONFIRMED
    assert it["identifiers"] == {"repo": "openai/math", "commit": PIN, "path": f"preprints/{ETH}", "family": "378"}
    assert it["confirmation"]["blob_sha"] == "a" * 40 and it["evidence_text"] and it["title"] == "The Exponential Time Hypothesis is False"
    assert it["result_status"] == "has_lean_formalization" and it["status_basis"]["in_lean_catalogue"] is True


def test_a_family_number_expands_to_its_manuscripts_and_each_is_confirmed():
    items = confirm("family 157")
    assert len(items) == 3 and all(i["class"] == cs.COMPANY_RELEASE for i in items)
    statuses = {i["confirmation"]["status"] for i in items}
    assert cs.CONFIRMED in statuses                        # the Hadwiger manuscript exists in the fake tree
    refused = [i for i in items if i["confirmation"]["status"] == cs.REFUSED]
    assert all(i["confirmation"]["reason"] == "file_missing_at_commit" for i in refused)


def test_an_ambiguous_family_is_refused_and_names_the_directories():
    items = confirm("family 003")
    assert len(items) == 1 and items[0]["confirmation"]["reason"] == "ambiguous_family"
    assert len(items[0]["confirmation"]["directories"]) == 2


def test_an_old_edition_is_refused_as_not_standing_and_a_withdrawn_manuscript_is_content_with_its_status():
    old = confirm(f"preprints/{OLD_EDITION}")[0]
    assert old["confirmation"]["reason"] == "not_a_standing_manuscript"
    withdrawn = confirm(f"preprints/{WEIL}")[0]
    assert withdrawn["confirmation"]["status"] == cs.CONFIRMED and withdrawn["result_status"] == "withdrawn"


def test_an_unknown_family_is_refused():
    assert confirm("family 999")[0]["confirmation"]["reason"] == "unknown_family"


def test_a_repository_that_cannot_be_read_raises_rather_than_refusing():
    with pytest.raises(omi.RepoUnavailable):
        confirm(f"preprints/{ETH}", repo=RepoFetch(status=503))


def test_another_repository_is_not_a_company_release_here():
    it = confirm("https://github.com/someone/else/tree/main/preprints/Foo")[0]
    assert it["class"] == cs.COMMENTARY and it["confirmation"]["status"] == cs.PENDING


# --- commentary is held, not confirmed ----------------------------------------------------------------------------------------------------------
def test_a_web_address_becomes_pending_commentary_that_cannot_be_approved():
    it = confirm("https://www.quantamagazine.org/some-story/")[0]
    assert it["class"] == cs.COMMENTARY and it["confirmation"]["status"] == cs.PENDING and it["approved"] is False


# --- class overrides ----------------------------------------------------------------------------------------------------------------------------
def test_only_a_downgrade_is_ever_allowed_and_never_on_a_failed_confirmation():
    pr = confirm("PMID: 12345678")[0]
    assert cs.allowed_class_overrides(pr) == [cs.PREPRINT]
    assert cs.allowed_class_overrides(confirm("2501.01234")[0]) == []
    assert cs.allowed_class_overrides(confirm(f"preprints/{ETH}")[0]) == []
    assert cs.allowed_class_overrides(confirm("https://example.org/post")[0]) == []
    refused = confirm("10.1000/nothing")[0]
    assert cs.allowed_class_overrides(refused) == []


# --- the minimum rule (Q1) -------------------------------------------------------------------------------------------------------------------------
def make(cls, n, status=cs.CONFIRMED, approved=True):
    ids = {"doi": f"10.1000/{cls}{n}"}
    return {"item_id": cs.item_id(ids), "class": cls, "identifiers": ids, "title": f"T{cls}{n}", "evidence_text": "e",
            "confirmation": {"status": status}, "approved": approved}


def test_three_confirmed_non_commentary_sources_meet_the_minimum_and_commentary_never_counts():
    items = [make(cs.PREPRINT, 1), make(cs.PEER_REVIEWED, 2), make(cs.COMPANY_RELEASE, 3)]
    ok, counts = cs.minimum_check(items)
    assert ok and counts["non_commentary"] == 3
    ok, counts = cs.minimum_check(items[:2] + [make(cs.COMMENTARY, 4), make(cs.COMMENTARY, 5), make(cs.COMMENTARY, 6)])
    assert not ok and counts["non_commentary"] == 2 and counts[cs.COMMENTARY] == 3


def test_unconfirmed_or_unapproved_items_do_not_count():
    items = [make(cs.PREPRINT, 1), make(cs.PREPRINT, 2), make(cs.PREPRINT, 3, status=cs.PENDING), make(cs.PREPRINT, 4, approved=False)]
    assert not cs.minimum_check(items)[0]


def test_company_release_manuscripts_count_one_each():
    assert cs.minimum_check([make(cs.COMPANY_RELEASE, i) for i in range(3)])[0]
    assert not cs.minimum_check([make(cs.COMPANY_RELEASE, i) for i in range(2)])[0]


# --- the list hash ---------------------------------------------------------------------------------------------------------------------------------------
PIN_DOC = {"repo": "openai/math", "commit": PIN}


def base_items():
    return [make(cs.PREPRINT, 1), make(cs.PEER_REVIEWED, 2), make(cs.COMPANY_RELEASE, 3)]


def test_the_hash_is_stable_and_independent_of_order_and_timestamps():
    a = base_items()
    b = list(reversed(copy.deepcopy(a)))
    b[0]["confirmation"]["confirmed_at"] = "2030-01-01T00:00:00Z"
    assert cs.list_hash(PIN_DOC, a) == cs.list_hash(PIN_DOC, b) and len(cs.list_hash(PIN_DOC, a)) == 64


def test_any_edit_to_what_is_approved_changes_the_hash():
    base = cs.list_hash(PIN_DOC, base_items())
    edits = {}
    c = base_items(); c[0]["class"] = cs.PREPRINT if c[0]["class"] != cs.PREPRINT else cs.PEER_REVIEWED; edits["class"] = c
    c = base_items(); c[1]["title"] = "other"; edits["title"] = c
    c = base_items(); c[1]["evidence_text"] = "different abstract"; edits["evidence"] = c
    c = base_items(); c.append(make(cs.PREPRINT, 9)); edits["added item"] = c
    c = base_items(); c.pop(); edits["struck item"] = c
    c = base_items(); c[2]["confirmation"]["blob_sha"] = "f" * 40; edits["blob id"] = c
    c = base_items(); c[0]["identifiers"] = {"doi": "10.1000/changed"}; edits["identity"] = c
    for name, items in edits.items():
        assert cs.list_hash(PIN_DOC, items) != base, name
    assert cs.list_hash({"repo": "openai/math", "commit": "0" * 40}, base_items()) != base          # the pin
    c = base_items(); c[0]["approved"] = False
    assert cs.list_hash(PIN_DOC, c) != base                                                         # an item taken out of the approved set


def test_items_that_are_not_approved_or_confirmed_do_not_enter_the_hash():
    base = cs.list_hash(PIN_DOC, base_items())
    extra = base_items() + [make(cs.PREPRINT, 9, status=cs.PENDING), make(cs.PREPRINT, 8, approved=False)]
    assert cs.list_hash(PIN_DOC, extra) == base
