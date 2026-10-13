"""When arXiv cannot be reached, arXiv-hosted works are searched through OpenAlex and confirmed through DataCite (fix 1b, stage d).
Offline: every HTTP call is faked."""
import asyncio
import json
from types import SimpleNamespace

import pytest

import paper_confirmation as pc
import research_pipeline as rp

A = "10.48550/arxiv."


def run(coro):
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


def oa_work(arxiv_id, title="Formalizing proofs at scale", year=2026, words=None, doi=None):
    words = words or {"Machine": [0], "proofs": [1], "need": [2], "structure.": [3]}
    return {"id": "https://openalex.org/W1", "doi": doi or f"https://doi.org/{A}{arxiv_id}", "title": title, "publication_year": year,
            "authorships": [{"author": {"display_name": "Ada Lovelace"}}, {"author": {"display_name": "Alan Turing"}}],
            "abstract_inverted_index": words}


def pipeline(monkeypatch, arxiv_replies, openalex_replies):
    p = rp.ComprehensiveResearchPipeline()
    sleeps, calls = [], {"arxiv": 0, "openalex": 0, "openalex_params": []}
    aq, oq = list(arxiv_replies), list(openalex_replies)

    async def fake_arxiv(params):
        calls["arxiv"] += 1
        return aq.pop(0)

    async def fake_openalex(params):
        calls["openalex"] += 1
        calls["openalex_params"].append(params)
        r = oq.pop(0)
        if isinstance(r, Exception):
            raise r
        return r

    async def fake_sleep(d):
        sleeps.append(d)
    monkeypatch.setattr(p, "_arxiv_request", fake_arxiv)
    monkeypatch.setattr(p, "_openalex_request", fake_openalex)
    monkeypatch.setattr(rp.asyncio, "sleep", fake_sleep)
    return p, sleeps, calls


DOWN = [(429, "", None)] * 4


def test_the_abstract_is_put_back_in_order():
    assert rp.ComprehensiveResearchPipeline._openalex_abstract({"world": [1], "Hello": [0], "again": [2, 3]}) == "Hello world again again"
    assert rp.ComprehensiveResearchPipeline._openalex_abstract(None) == ""


def test_arxiv_down_falls_back_to_openalex_and_flags_the_sources_for_datacite(monkeypatch):
    p, sleeps, calls = pipeline(monkeypatch, DOWN, [(200, {"results": [oa_work("2606.03743"), oa_work("2505.02735", "Benchmarking proofs", 2025)]})])
    out = run(p._search_arxiv("formal proofs", "comprehensive"))
    assert calls["arxiv"] == 4 and calls["openalex"] == 1
    assert [s.title for s in out] == ["Formalizing proofs at scale", "Benchmarking proofs"]
    s = out[0]
    assert s.url == "https://arxiv.org/abs/2606.03743" and s.doi == "10.48550/arXiv.2606.03743" and s.source == "arxiv" and s.confirm_via == "datacite"
    assert s.abstract == "Machine proofs need structure." and s.authors == ["Ada Lovelace", "Alan Turing"] and s.publication_date == "2026"
    prm = calls["openalex_params"][0]
    assert prm["filter"] == "primary_location.source.id:S4306400194" and prm["search"] == "formal proofs"
    assert prm["mailto"] == "copernicusai.verify@gmail.com"                       # the polite pool, with the project mailbox


def test_no_personal_address_is_ever_in_the_search_code():
    from pathlib import Path
    src = Path(rp.__file__).read_text(encoding="utf-8")
    assert "copernicusai.verify@gmail.com" in src
    for personal in ("garywelz", "gwelz", "gc.cuny.edu"):
        assert personal not in src


def test_when_arxiv_answers_openalex_is_not_used(monkeypatch):
    atom = ('<feed xmlns="http://www.w3.org/2005/Atom"><entry><id>http://arxiv.org/abs/2601.00001v1</id><title>A</title><summary>S</summary>'
            '<published>2026-01-01T00:00:00Z</published><author><name>A B</name></author></entry></feed>')
    p, sleeps, calls = pipeline(monkeypatch, [(200, atom, None)], [])
    assert len(run(p._search_arxiv("x", "comprehensive"))) == 1 and calls["openalex"] == 0


def test_both_down_fails_as_registry_unavailable_naming_both(monkeypatch):
    p, sleeps, calls = pipeline(monkeypatch, DOWN, [(503, None), asyncio.TimeoutError(), (429, None)])
    with pytest.raises(pc.RegistryUnavailable) as e:
        run(p._search_arxiv("x", "comprehensive"))
    assert e.value.registries == ["arxiv", "openalex"] and calls["openalex"] == 3 and sleeps[-2:] == [2.0, 4.0]


def test_openalex_retries_then_succeeds(monkeypatch):
    p, sleeps, calls = pipeline(monkeypatch, DOWN, [(429, None), (200, {"results": [oa_work("2606.03743")]})])
    assert len(run(p._search_arxiv("x", "comprehensive"))) == 1 and calls["openalex"] == 2


def test_results_without_an_arxiv_doi_or_a_title_are_skipped(monkeypatch):
    results = [oa_work("2606.03743"), oa_work("0000.00000", doi="https://doi.org/10.1000/journal.5"),
               oa_work("2606.03744", title=""), {"id": "x", "doi": None, "title": "No doi"}]
    p, _, _ = pipeline(monkeypatch, DOWN, [(200, {"results": results})])
    assert [s.url for s in run(p._search_arxiv("x", "comprehensive"))] == ["https://arxiv.org/abs/2606.03743"]


def test_comprehensive_search_uses_the_fallback_and_propagates_a_double_failure(monkeypatch):
    async def empty(*a, **k):
        return []
    p, _, calls = pipeline(monkeypatch, DOWN, [(200, {"results": [oa_work("2606.03743")]})])
    for name in ("_search_pubmed", "_search_biorxiv", "_search_core", "_search_youtube", "_search_zenodo"):
        monkeypatch.setattr(p, name, empty)
    assert [s.title for s in run(p.comprehensive_search("proofs"))] == ["Formalizing proofs at scale"]
    p2, _, _ = pipeline(monkeypatch, DOWN, [(500, None)] * 3)
    for name in ("_search_pubmed", "_search_biorxiv", "_search_core", "_search_youtube", "_search_zenodo"):
        monkeypatch.setattr(p2, name, empty)
    with pytest.raises(pc.RegistryUnavailable):
        run(p2.comprehensive_search("proofs"))


# ---------------------------------------------------------------- confirmation through DataCite, with no arXiv request at all
def dc_record(arxiv_id, rtype="Preprint", title="Formalizing proofs at scale", abstract="Machine proofs need structure.", year=2026):
    attrs = {"doi": A + arxiv_id, "titles": [{"title": title}], "publicationYear": year, "types": {"resourceTypeGeneral": rtype},
             "creators": [{"name": "Lovelace, Ada", "givenName": "Ada", "familyName": "Lovelace"}],
             "descriptions": ([{"description": abstract, "descriptionType": "Abstract"}] if abstract is not None else [])}
    return json.dumps({"data": {"attributes": attrs}})


class Fake:
    def __init__(self, datacite):
        self.datacite, self.calls = datacite, []

    async def __call__(self, url, params):
        self.calls.append(url)
        if "api.datacite.org" in url:
            doi = url.split("/dois/")[1]
            return (200, self.datacite[doi]) if doi in self.datacite else (404, "")
        return 500, ""     # arXiv, PubMed and Crossref must not be asked


def fallback_src(arxiv_id, title="Formalizing proofs at scale", year="2026"):
    return SimpleNamespace(title=title, url=f"https://arxiv.org/abs/{arxiv_id}", doi=f"10.48550/arXiv.{arxiv_id}", publication_date=year,
                           confirm_via="datacite", registry_record=None)


def test_fallback_papers_are_confirmed_by_datacite_without_asking_arxiv():
    f = Fake({A + "2606.03743": dc_record("2606.03743")})
    res = run(pc.confirm_sources([fallback_src("2606.03743")], http_get=f))
    assert len(res.confirmed) == 1 and all("datacite" in u for u in f.calls)
    c = res.confirmed[0]
    assert c.registry == "datacite" and c.venue == "arXiv preprint" and c.ids["arxiv"] == "2606.03743" and c.ids["doi"].lower() == A + "2606.03743"
    assert c.abstract == "Machine proofs need structure." and c.authors == ["Ada Lovelace"]
    assert "arXiv:2606.03743" in pc.format_citation_line(c)
    from relevance_gate import is_zenodo, outside_zenodo
    assert not is_zenodo(c) and outside_zenodo([c]) == 1                      # counts toward the minimum of 3 outside Zenodo


def test_fallback_papers_without_a_datacite_record_an_abstract_or_a_preprint_type_are_dropped():
    f = Fake({A + "2606.00001": dc_record("2606.00001", abstract=None), A + "2606.00002": dc_record("2606.00002", rtype="Dataset"),
              A + "2606.00004": dc_record("2606.00004", title="A completely different paper about fungi")})
    res = run(pc.confirm_sources([fallback_src("2606.00001"), fallback_src("2606.00002"), fallback_src("2606.00003"), fallback_src("2606.00004")], http_get=f))
    assert res.confirmed == [] and sorted(d.reason for d in res.dropped) == ["identifier_mismatch", "no_abstract", "not_found", "not_publication_type"]


def test_a_datacite_outage_is_registry_unavailable_not_an_empty_result():
    class Down:
        async def __call__(self, url, params):
            return 503, ""
    with pytest.raises(pc.RegistryUnavailable):
        run(pc.confirm_sources([fallback_src("2606.03743")], http_get=Down(), ))


def test_ordinary_arxiv_papers_still_go_to_arxiv():
    f = Fake({})
    plain = SimpleNamespace(title="A", url="https://arxiv.org/abs/2601.00001v1", doi=None, publication_date="2026")
    with pytest.raises(pc.RegistryUnavailable):                                # the fake answers 500 for arXiv: proves arXiv was asked
        run(pc.confirm_sources([plain], http_get=f))
    assert any("arxiv.org" in u for u in f.calls)
