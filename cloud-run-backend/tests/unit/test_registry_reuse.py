"""Confirmation reuses the record the search stage parsed from the same registry; the arXiv timeout is longer. Offline."""
import asyncio
from types import SimpleNamespace

import paper_confirmation as pc
import research_pipeline as rp

ATOM = ('<?xml version="1.0"?><feed xmlns="http://www.w3.org/2005/Atom">'
        '<entry><id>http://arxiv.org/abs/2601.00001v1</id><published>2026-01-02T00:00:00Z</published><title>Protein folding with neural networks</title>'
        '<summary>We fold proteins.</summary><author><name>Ada Lovelace</name></author></entry>'
        '<entry><id>http://arxiv.org/abs/2601.00002v2</id><published>2026-01-03T00:00:00Z</published><title>Graph methods for cells</title>'
        '<summary>We study graphs.</summary><author><name>Alan Turing</name></author></entry></feed>')


def run(coro):
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


class Counting:
    def __init__(self):
        self.calls = []

    async def __call__(self, url, params):
        self.calls.append(url)
        return 404, ""


def test_search_parser_attaches_the_registry_record():
    srcs = rp.ComprehensiveResearchPipeline()._parse_arxiv_xml(ATOM)
    assert [s.registry_record["ids"]["arxiv_version"] for s in srcs] == ["v1", "v2"]
    assert "registry_record" not in repr(srcs[0])


def test_confirmation_reuses_search_records_and_makes_no_arxiv_request():
    srcs = rp.ComprehensiveResearchPipeline()._parse_arxiv_xml(ATOM)
    f = Counting()
    res = run(pc.confirm_sources(srcs, http_get=f))
    assert [c.ids["arxiv"] for c in res.confirmed] == ["2601.00001", "2601.00002"] and f.calls == []
    assert res.stats == {"requests": {}, "reused_from_search": {"arxiv": 2, "pubmed": 0}}
    assert res.confirmed[0].abstract == "We fold proteins." and res.confirmed[0].registry == "arxiv"


def test_a_source_without_a_matching_record_is_looked_up_again():
    s = rp.ComprehensiveResearchPipeline()._parse_arxiv_xml(ATOM)[0]
    other = SimpleNamespace(title=s.title, url="http://arxiv.org/abs/2601.00009v1", doi=None, publication_date="2026", registry_record=s.registry_record)
    wrong_version = SimpleNamespace(title=s.title, url="http://arxiv.org/abs/2601.00001v3", doi=None, publication_date="2026", registry_record=s.registry_record)
    f = Counting()
    res = run(pc.confirm_sources([other, wrong_version], http_get=f))
    assert len(f.calls) >= 1 and res.stats["reused_from_search"]["arxiv"] == 0


def test_arxiv_gets_a_longer_timeout_than_the_other_registries():
    assert pc.ARXIV_TIMEOUT_S > pc.HTTP_TIMEOUT_S >= 15
