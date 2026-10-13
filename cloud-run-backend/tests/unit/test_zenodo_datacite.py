"""Zenodo records are confirmed through DataCite, publication types only, abstract required. Offline."""
import asyncio
import json
from types import SimpleNamespace

import paper_confirmation as pc


def run(coro):
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


def record(doi, rtype, title="A study of things", abstract="An abstract.", year=2026, desc_type="Abstract"):
    attrs = {"doi": doi, "titles": [{"title": title}], "publicationYear": year, "types": {"resourceTypeGeneral": rtype},
             "creators": [{"name": "Hopper, Grace", "givenName": "Grace", "familyName": "Hopper"}, {"name": "Turing, Alan"}],
             "descriptions": ([{"description": "<p>" + abstract + "</p>", "descriptionType": desc_type}] if abstract is not None else [])}
    return json.dumps({"data": {"attributes": attrs}})


class Fake:
    def __init__(self, datacite=None, crossref=None):
        self.datacite, self.crossref, self.calls = datacite or {}, crossref or {}, []

    async def __call__(self, url, params):
        self.calls.append(url)
        if "api.crossref.org" in url:
            doi = url.split("/works/")[1]
            return (200, self.crossref[doi]) if doi in self.crossref else (404, "")
        if "api.datacite.org" in url:
            doi = url.split("/dois/")[1]
            return (200, self.datacite[doi]) if doi in self.datacite else (404, "")
        return 500, ""


def src(title, doi):
    return SimpleNamespace(title=title, url="", doi=doi, publication_date="2026")


Z = "10.5281/zenodo."


def test_publication_types_are_confirmed_and_marked_with_their_type():
    types = {"Preprint": "Zenodo preprint", "JournalArticle": "Zenodo journal article", "ConferencePaper": "Zenodo conference paper",
             "Report": "Zenodo report", "Text": "Zenodo text"}
    dc = {Z + str(i): record(Z + str(i), t) for i, t in enumerate(types, 1)}
    f = Fake(datacite=dc)
    res = run(pc.confirm_sources([src("A study of things", d) for d in dc], http_get=f))
    assert [c.venue for c in res.confirmed] == list(types.values())
    c = res.confirmed[0]
    assert c.registry == "datacite" and c.authors == ["Grace Hopper", "Alan Turing"] and c.abstract == "An abstract." and c.year == 2026
    line = pc.format_citation_line(c)
    assert "Zenodo preprint." in line and "DOI: " + Z + "1." in line


def test_other_resource_types_are_dropped():
    dc = {Z + "10": record(Z + "10", "Dataset"), Z + "11": record(Z + "11", "Software"), Z + "12": record(Z + "12", "Image")}
    res = run(pc.confirm_sources([src("A study of things", d) for d in dc], http_get=Fake(datacite=dc)))
    assert not res.confirmed and [d.reason for d in res.dropped] == ["not_publication_type"] * 3


def test_a_record_without_an_abstract_is_dropped_as_for_other_sources():
    dc = {Z + "20": record(Z + "20", "Preprint", abstract=None), Z + "21": record(Z + "21", "Preprint", desc_type="Other")}
    res = run(pc.confirm_sources([src("A study of things", d) for d in dc], http_get=Fake(datacite=dc)))
    assert not res.confirmed and [d.reason for d in res.dropped] == ["no_abstract"] * 2


def test_title_and_year_mismatch_still_drops():
    dc = {Z + "30": record(Z + "30", "Preprint", title="Something entirely different")}
    res = run(pc.confirm_sources([src("A study of things", Z + "30")], http_get=Fake(datacite=dc)))
    assert [d.reason for d in res.dropped] == ["identifier_mismatch"]


def test_unknown_zenodo_doi_is_not_found_and_other_dois_never_go_to_datacite():
    f = Fake()
    res = run(pc.confirm_sources([src("A study of things", Z + "99"), src("Other", "10.1000/xyz")], http_get=f))
    assert [d.reason for d in res.dropped] == ["not_found", "not_found"]
    assert sum("datacite" in u for u in f.calls) == 1
