"""Unit tests for paper_confirmation (gap 3 fix 1, step A). Offline: registries are faked."""
import asyncio
import json
from types import SimpleNamespace

import pytest

import paper_confirmation as pc

ATOM = """<?xml version="1.0"?><feed xmlns="http://www.w3.org/2005/Atom">{entries}</feed>"""
ENTRY = """<entry><id>http://arxiv.org/abs/{id}</id><published>{pub}</published><title>{title}</title>
<summary>  {summary}  </summary><author><name>Ada Lovelace</name></author><author><name>Alan Turing</name></author></entry>"""


def atom(*entries):
    return ATOM.format(entries="".join(ENTRY.format(**e) for e in entries))


PUBMED = """<PubmedArticleSet>{arts}</PubmedArticleSet>"""
ART = """<PubmedArticle><MedlineCitation><PMID>{pmid}</PMID><Article><Journal><JournalIssue><PubDate><Year>{year}</Year></PubDate></JournalIssue>
<Title>{journal}</Title></Journal><ArticleTitle>{title}</ArticleTitle><Abstract><AbstractText>{abstract}</AbstractText></Abstract>
<AuthorList><Author><LastName>Curie</LastName><ForeName>Marie</ForeName></Author></AuthorList></Article></MedlineCitation>
<PubmedData><ArticleIdList><ArticleId IdType="doi">{doi}</ArticleId></ArticleIdList></PubmedData></PubmedArticle>"""


def pubmed(*arts):
    return PUBMED.format(arts="".join(ART.format(**a) for a in arts))


def crossref(title="Some Paper", abstract="<jats:p>An abstract.</jats:p>", year=2024, doi="10.1000/x1"):
    msg = {"title": [title], "DOI": doi, "issued": {"date-parts": [[year]]}, "container-title": ["Journal of Tests"],
           "author": [{"given": "Grace", "family": "Hopper"}]}
    if abstract is not None:
        msg["abstract"] = abstract
    return json.dumps({"message": msg})


class Fake:
    """Routes by URL; records calls."""

    def __init__(self, arxiv=None, pubmed_xml=None, crossref_map=None, esearch=None, status=None):
        self.arxiv, self.pubmed_xml = arxiv, pubmed_xml
        self.crossref_map = crossref_map or {}
        self.esearch = esearch or {}
        self.status = status or {}
        self.calls = []

    async def __call__(self, url, params):
        self.calls.append((url, dict(params)))
        for key, code in self.status.items():
            if key in url:
                return code, ""
        if "export.arxiv.org" in url:
            return 200, self.arxiv or atom()
        if "efetch" in url:
            return 200, self.pubmed_xml or pubmed()
        if "esearch" in url:
            ids = self.esearch.get(params["term"].replace("[AID]", ""), [])
            return 200, json.dumps({"esearchresult": {"idlist": ids}})
        if "api.crossref.org" in url:
            doi = url.split("/works/")[1]
            if doi in self.crossref_map:
                return 200, self.crossref_map[doi]
            return 404, ""
        return 500, ""


def src(title, url="", doi=None, date=""):
    return SimpleNamespace(title=title, url=url, doi=doi, publication_date=date)


def run(coro):
    # Not asyncio.run(): it clears the thread's current event loop, which breaks later tests that call
    # asyncio.get_event_loop() (tests/unit/test_vector_search_engine_scoping.py).
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


# ---------------------------------------------------------------- identifiers
def test_ids_from_arxiv_url_with_version():
    ids = pc.ids_from_fields("http://arxiv.org/abs/2603.28944v1", None)
    assert ids["arxiv"] == "2603.28944" and ids["arxiv_version"] == "v1" and ids["doi"] is None


def test_ids_from_arxiv_url_without_version():
    ids = pc.ids_from_fields("https://arxiv.org/pdf/2509.19320", None)
    assert ids["arxiv"] == "2509.19320" and ids["arxiv_version"] is None


def test_ids_from_pubmed_url_and_doi():
    ids = pc.ids_from_fields("https://pubmed.ncbi.nlm.nih.gov/12345678/", "https://doi.org/10.1016/ABC.1")
    assert ids["pmid"] == "12345678" and ids["doi"] == "10.1016/abc.1"


def test_arxiv_doi_maps_to_arxiv_id():
    ids = pc.ids_from_fields("", "10.48550/arXiv.2601.01234v2")
    assert ids["arxiv"] == "2601.01234" and ids["arxiv_version"] == "v2" and ids["doi"] is None


def test_no_identifier():
    assert not any(pc.ids_from_fields("https://www.youtube.com/watch?v=abc", None).values())
    assert not any(pc.ids_from_fields("", "not-a-doi").values())


def test_normalize_doi_strips_wrappers():
    assert pc.normalize_doi("doi: 10.1000/ABC.") == "10.1000/abc"
    assert pc.normalize_doi("https://doi.org/10.1000/abc") == "10.1000/abc"
    assert pc.normalize_doi("hello") is None


def test_title_match_scores():
    assert pc.title_match("Deep learning for protein folding", "Deep Learning for Protein Folding") == 1.0
    assert pc.title_match("Deep learning for protein folding", "Quantum error correction codes") < 0.2
    assert pc.title_match("", "x") == 0.0


# ---------------------------------------------------------------- confirmation
def test_arxiv_version_pinned_and_one_batched_request():
    f = Fake(arxiv=atom(
        dict(id="2603.28944v1", pub="2026-03-30T00:00:00Z", title="AI prediction leads people to forgo guaranteed rewards", summary="Newcomb."),
        dict(id="2509.19320v1", pub="2025-09-20T00:00:00Z", title="Introduction to some of the simplest topological phases of matter", summary="Phases.")))
    res = run(pc.confirm_sources([
        src("AI prediction leads people to forgo guaranteed rewards", "http://arxiv.org/abs/2603.28944v1", None, "2026-03-30"),
        src("Introduction to some of the simplest topological phases of matter", "http://arxiv.org/abs/2509.19320v1", None, "2025-09-20"),
    ], http_get=f))
    assert [p.pid for p in res.confirmed] == ["P1", "P2"]
    assert res.confirmed[0].ids["arxiv"] == "2603.28944" and res.confirmed[0].ids["arxiv_version"] == "v1"
    assert res.confirmed[0].url.endswith("2603.28944v1")
    arxiv_calls = [c for c in f.calls if "export.arxiv.org" in c[0]]
    assert len(arxiv_calls) == 1 and arxiv_calls[0][1]["id_list"] == "2603.28944v1,2509.19320v1"


def test_registry_title_of_cited_version_wins_over_search_record():
    f = Fake(arxiv=atom(dict(id="2603.28944v1", pub="2026-03-30T00:00:00Z", title="Version one title words", summary="A.")))
    res = run(pc.confirm_sources([src("Version one title words", "http://arxiv.org/abs/2603.28944v1", None, "2026")], http_get=f))
    assert res.confirmed[0].title == "Version one title words"
    assert res.confirmed[0].authors == ["Ada Lovelace", "Alan Turing"]


def test_pubmed_batched_and_fields_from_registry():
    f = Fake(pubmed_xml=pubmed(
        dict(pmid="111111", year=2020, journal="Nature", title="Protein binding sites", abstract="Binding.", doi="10.1/A"),
        dict(pmid="222222", year=2021, journal="Science", title="Gene regulation networks", abstract="Genes.", doi="10.1/B")))
    res = run(pc.confirm_sources([
        src("Protein binding sites", "https://pubmed.ncbi.nlm.nih.gov/111111/", None, "2020"),
        src("Gene regulation networks", "https://pubmed.ncbi.nlm.nih.gov/222222/", None, "2021")], http_get=f))
    assert len(res.confirmed) == 2 and res.confirmed[0].venue == "Nature" and res.confirmed[0].ids["doi"] == "10.1/a"
    assert res.confirmed[0].authors == ["Marie Curie"]
    assert len([c for c in f.calls if "efetch" in c[0]]) == 1


def test_crossref_doi_confirmed_and_jats_stripped():
    f = Fake(crossref_map={"10.1000/x1": crossref("Some Paper Title", "<jats:p>An abstract here.</jats:p>")})
    res = run(pc.confirm_sources([src("Some Paper Title", "", "10.1000/X1", "2024")], http_get=f))
    assert res.confirmed[0].abstract == "An abstract here." and res.confirmed[0].registry == "crossref"
    assert res.confirmed[0].venue == "Journal of Tests"


def test_crossref_without_abstract_falls_back_to_pubmed_by_doi():
    f = Fake(crossref_map={"10.1000/x1": crossref("Some Paper Title", None)}, esearch={"10.1000/x1": ["333333"]},
             pubmed_xml=pubmed(dict(pmid="333333", year=2024, journal="J", title="Some Paper Title", abstract="From PubMed.", doi="10.1000/x1")))
    res = run(pc.confirm_sources([src("Some Paper Title", "", "10.1000/x1", "2024")], http_get=f))
    assert res.confirmed[0].abstract == "From PubMed." and res.confirmed[0].registry == "pubmed"


def test_no_abstract_anywhere_is_dropped():
    f = Fake(crossref_map={"10.1000/x1": crossref("Some Paper Title", None)})
    res = run(pc.confirm_sources([src("Some Paper Title", "", "10.1000/x1", "2024")], http_get=f))
    assert res.confirmed == [] and res.drop_counts() == {"no_abstract": 1}


def test_not_found_dropped():
    res = run(pc.confirm_sources([src("Ghost Paper", "", "10.9999/nope", "2024")], http_get=Fake()))
    assert res.drop_counts() == {"not_found": 1}


def test_identifier_that_is_a_different_paper_is_dropped():
    f = Fake(arxiv=atom(dict(id="2601.00001v1", pub="2026-01-01T00:00:00Z", title="Completely unrelated quantum gravity", summary="X.")))
    res = run(pc.confirm_sources([src("Protein folding with neural networks", "http://arxiv.org/abs/2601.00001v1", None, "2026")], http_get=f))
    assert res.drop_counts() == {"identifier_mismatch": 1}


def test_year_far_from_registry_year_is_a_mismatch():
    f = Fake(crossref_map={"10.1000/x1": crossref("Some Paper Title", "<p>A.</p>", year=2015)})
    res = run(pc.confirm_sources([src("Some Paper Title", "", "10.1000/x1", "2024")], http_get=f))
    assert res.drop_counts() == {"identifier_mismatch": 1}


def test_candidates_without_identifier_are_dropped_and_never_looked_up():
    f = Fake()
    res = run(pc.confirm_sources([src("A talk", "https://www.youtube.com/watch?v=1"), src("A news item", "https://example.com/n")], http_get=f))
    assert res.drop_counts() == {"no_identifier": 2} and f.calls == []


def test_duplicates_across_registries_keep_first_by_rank():
    f = Fake(pubmed_xml=pubmed(dict(pmid="111111", year=2020, journal="N", title="Binding sites in DNA", abstract="B.", doi="10.1/a")),
             crossref_map={"10.1/a": crossref("Binding sites in DNA", "<p>B.</p>", 2020, "10.1/a")})
    res = run(pc.confirm_sources([
        src("Binding sites in DNA", "https://pubmed.ncbi.nlm.nih.gov/111111/", "10.1/a", "2020"),
        src("Binding sites in DNA", "", "10.1/A", "2020")], http_get=f))
    # the DOI-only duplicate is a PubMed paper already (same DOI) -> second is dropped as duplicate
    assert len(res.confirmed) == 1 and res.drop_counts() == {"duplicate": 1}


def test_numbering_follows_rank_and_limit_is_enforced():
    entries = [dict(id=f"2601.{i:05d}v1", pub="2026-01-01T00:00:00Z", title=f"Paper number {i} about topic", summary="S.") for i in range(1, 16)]
    f = Fake(arxiv=atom(*entries))
    srcs = [src(f"Paper number {i} about topic", f"http://arxiv.org/abs/2601.{i:05d}v1", None, "2026") for i in range(1, 16)]
    res = run(pc.confirm_sources(srcs, http_get=f))
    assert [p.pid for p in res.confirmed] == [f"P{i}" for i in range(1, 13)]
    assert res.confirmed[0].ids["arxiv"] == "2601.00001"
    assert res.drop_counts() == {"over_limit": 3}


def test_registry_outage_raises_not_too_few():
    f = Fake(status={"export.arxiv.org": 503})
    with pytest.raises(pc.RegistryUnavailable) as e:
        run(pc.confirm_sources([src("X", "http://arxiv.org/abs/2601.00001v1")], http_get=f))
    assert e.value.registries == ["arxiv"]


def test_network_exception_is_retried_then_raises():
    n = {"c": 0}

    async def boom(url, params):
        n["c"] += 1
        raise TimeoutError()
    with pytest.raises(pc.RegistryUnavailable):
        run(pc.confirm_sources([src("X", "", "10.1000/x1")], http_get=boom))
    assert n["c"] == 1 + pc.HTTP_RETRIES


def test_confirmed_record_has_required_fields():
    f = Fake(arxiv=atom(dict(id="2601.00001v1", pub="2026-01-01T00:00:00Z", title="A fine paper title", summary="S.")))
    p = run(pc.confirm_sources([src("A fine paper title", "http://arxiv.org/abs/2601.00001v1", None, "2026")], http_get=f)).confirmed[0].to_dict()
    for k in ("pid", "title", "authors", "year", "venue", "ids", "url", "abstract", "registry", "confirmed_at", "title_match"):
        assert k in p
    assert p["confirmed_at"].endswith("Z") and p["title_match"] == 1.0


# ---------------------------------------------------------------- requested paper and user links
def test_requested_paper_confirmed_by_doi():
    f = Fake(crossref_map={"10.1000/x1": crossref("Requested Paper Title", "<p>A.</p>", 2025)})
    p = run(pc.confirm_requested_paper("10.1000/x1", "Requested Paper Title", http_get=f))
    assert p.pid == "P1" and p.title == "Requested Paper Title"


def test_requested_paper_without_doi_fails_clearly():
    with pytest.raises(pc.PaperNotConfirmed, match="no usable DOI"):
        run(pc.confirm_requested_paper(None, "T", http_get=Fake()))


def test_requested_paper_not_found_fails_clearly():
    with pytest.raises(pc.PaperNotConfirmed, match="not_found"):
        run(pc.confirm_requested_paper("10.9999/none", "T", http_get=Fake()))


def test_user_link_identifier_from_url():
    assert pc.discover_identifiers_in_page("https://arxiv.org/abs/2603.28944v1", "")["arxiv"] == "2603.28944"
    assert pc.discover_identifiers_in_page("https://doi.org/10.1000/abc", "")["doi"] == "10.1000/abc"


def test_user_link_identifier_from_page_metadata():
    html = '<meta name="citation_doi" content="10.1234/Journal.567">'
    assert pc.discover_identifiers_in_page("https://publisher.example/article", html)["doi"] == "10.1234/journal.567"
    html2 = '<meta name="citation_pmid" content="12345678">'
    assert pc.discover_identifiers_in_page("https://publisher.example/a", html2)["pmid"] == "12345678"


def test_user_link_with_no_identifier_yields_none():
    assert not any(pc.discover_identifiers_in_page("https://blog.example/post", "<p>nothing here</p>").values())


# ---------------------------------------------------------------- C3 wiring: user links and the requested paper
def test_required_first_becomes_p1_and_its_duplicate_is_dropped():
    f = Fake(crossref_map={"10.1000/x1": crossref("Requested Paper Title", "<p>A.</p>", 2025)},
             arxiv=atom(dict(id="2601.00002v1", pub="2026-01-01T00:00:00Z", title="Another paper about things", summary="S.")))
    req = run(pc.confirm_requested_paper("10.1000/x1", "Requested Paper Title", http_get=f))
    res = run(pc.confirm_sources([
        src("Another paper about things", "http://arxiv.org/abs/2601.00002v1", None, "2026"),
        src("Requested Paper Title", "", "10.1000/X1", "2025")], http_get=f, required_first=req))
    assert [p.pid for p in res.confirmed] == ["P1", "P2"]
    assert res.confirmed[0].title == "Requested Paper Title" and res.confirmed[1].ids["arxiv"] == "2601.00002"
    assert res.drop_counts() == {"duplicate": 1}


def test_insufficient_confirmed_papers_message_is_clear():
    e = pc.InsufficientConfirmedPapers("dark matter", 9, 2, 3, {"no_identifier": 5, "not_found": 2})
    msg = str(e)
    assert "dark matter" in msg and "9 candidate sources" in msg and "2 were confirmed" in msg and "at least 3" in msg
    assert "5 no identifier" in msg and "2 not found" in msg and "No episode was generated or published" in msg


def test_registry_unavailable_message_is_not_the_too_few_message():
    msg = str(pc.RegistryUnavailable(["pubmed", "arxiv"]))
    assert "arxiv, pubmed" in msg and "try again" in msg and "Not enough" not in msg


def test_as_research_source_and_citation_line_use_registry_fields_only():
    f = Fake(arxiv=atom(dict(id="2603.28944v1", pub="2026-03-30T00:00:00Z", title="AI prediction leads people to forgo guaranteed rewards", summary="Abs.")))
    c = run(pc.confirm_sources([src("AI prediction leads people to forgo guaranteed rewards", "http://arxiv.org/abs/2603.28944v1", None, "2026")], http_get=f)).confirmed[0]
    rs = pc.as_research_source(c)
    assert rs.pid == "P1" and rs.title == c.title and rs.abstract == "Abs." and rs.url.endswith("2603.28944v1")
    line = pc.format_citation_line(c)
    assert "arXiv:2603.28944v1" in line and "AI prediction leads people to forgo guaranteed rewards." in line
    assert line.startswith("Ada Lovelace, Alan Turing (2026).") and line.endswith("https://arxiv.org/abs/2603.28944v1")


# ---------------------------------------------------------------- integrator (C2, C4, C7) with every outside call faked
def _integrator(monkeypatch, sources, http):
    import podcast_research_integrator as pri
    monkeypatch.setattr(pc, "_default_http_get", http)

    class _Analysis:
        def __init__(self, title):
            self.title, self.analysis_failed = title, False
            self.paradigm_shift_potential, self.interdisciplinary_connections = "high", ["links to physics"]
            self.technical_complexity = "low"
            self.key_findings = [f"finding about {title}"]

    class _Gemini:
        paradigm_shifts, interdisciplinary_connections, key_findings = ["gemini shift"], [], ["gemini finding"]
        citations = ["FAKE MODEL-WRITTEN CITATION, Nature 1999"]

    async def fake_multi(srcs, complexity=None):
        return [_Analysis(x.title) for x in srcs]

    async def fake_gemini(paper, options, key):
        return _Gemini()

    async def fake_search(**kw):
        return list(sources)
    it = pri.PodcastResearchIntegrator("fake-key")
    monkeypatch.setattr(it.research_pipeline, "comprehensive_search", fake_search)
    monkeypatch.setattr(it.enhanced_research_service, "analyze_multiple_papers", fake_multi)
    monkeypatch.setattr(pri, "analyze_paper_with_gemini", fake_gemini)
    return it


def _good_http():
    return Fake(arxiv=atom(*[dict(id=f"2601.0000{i}v1", pub="2026-01-01T00:00:00Z", title=f"Paper number {i} about cells", summary=f"Abstract {i}.") for i in (1, 2, 3)]))


def _srcs(n=3, extra=()):
    out = [src(f"Paper number {i} about cells", f"http://arxiv.org/abs/2601.0000{i}v1", None, "2026") for i in range(1, n + 1)]
    for s_ in out:
        s_.authors, s_.abstract, s_.source, s_.journal = ["A One"], "x", "arxiv", None
    return out + list(extra)


def test_integrator_uses_only_confirmed_papers_and_no_model_citations(monkeypatch):
    junk = src("A talk on YouTube", "https://www.youtube.com/watch?v=1")
    junk.authors, junk.abstract, junk.source, junk.journal = [], "", "youtube", None
    it = _integrator(monkeypatch, _srcs(3, [junk]), _good_http())
    ctx = run(it.comprehensive_research_for_podcast("cells"))
    assert [s_.pid for s_ in ctx.research_sources] == ["P1", "P2", "P3"]
    assert [p.pid for p in ctx.confirmed_papers] == ["P1", "P2", "P3"] and ctx.dropped_candidates[0].reason == "no_identifier"
    joined = " ".join(ctx.real_citations + ctx.key_findings + ctx.paradigm_shifts)
    assert "FAKE MODEL-WRITTEN" not in joined
    assert all("arXiv:2601.0000" in c for c in ctx.real_citations) and len(ctx.real_citations) == 3
    assert any(f.startswith("[P1] ") for f in ctx.key_findings) and "[P1] gemini finding" in ctx.key_findings


def test_integrator_fails_early_with_too_few_confirmed_papers(monkeypatch):
    junk = [src(f"Talk {i}", f"https://www.youtube.com/watch?v={i}") for i in range(4)]
    for j in junk:
        j.authors, j.abstract, j.source, j.journal = [], "", "youtube", None
    it = _integrator(monkeypatch, _srcs(2, junk), _good_http())
    called = {"n": 0}

    async def boom(*a, **k):
        called["n"] += 1
        return []
    monkeypatch.setattr(it.enhanced_research_service, "analyze_multiple_papers", boom)
    with pytest.raises(pc.InsufficientConfirmedPapers) as e:
        run(it.comprehensive_research_for_podcast("cells"))
    assert e.value.found == 6 and e.value.confirmed == 2 and e.value.drop_counts == {"no_identifier": 4}
    assert called["n"] == 0  # no analysis, no generation, nothing spent


def test_integrator_registry_outage_is_not_reported_as_too_few(monkeypatch):
    it = _integrator(monkeypatch, _srcs(3), Fake(status={"export.arxiv.org": 503}))
    with pytest.raises(pc.RegistryUnavailable):
        run(it.comprehensive_research_for_podcast("cells"))


def test_requested_paper_is_p1_in_the_integrator(monkeypatch):
    http = _good_http()
    http.crossref_map = {"10.1000/x1": crossref("Requested Paper Title", "<p>Abs.</p>", 2025)}
    it = _integrator(monkeypatch, _srcs(3), http)
    ctx = run(it.comprehensive_research_for_podcast("cells", required_paper={"doi": "10.1000/x1", "title": "Requested Paper Title"}))
    assert ctx.requested_pid == "P1" and ctx.confirmed_papers[0].title == "Requested Paper Title"
    assert [p.pid for p in ctx.confirmed_papers] == ["P1", "P2", "P3", "P4"]


def test_unconfirmable_requested_paper_fails_the_research_phase(monkeypatch):
    it = _integrator(monkeypatch, _srcs(3), _good_http())
    with pytest.raises(pc.PaperNotConfirmed):
        run(it.comprehensive_research_for_podcast("cells", required_paper={"doi": "10.9999/none", "title": "Nope"}))


def test_prompt_lists_confirmed_papers_and_forbids_others(monkeypatch):
    it = _integrator(monkeypatch, _srcs(3), _good_http())
    ctx = run(it.comprehensive_research_for_podcast("cells"))
    prompt = it.build_2_speaker_research_prompt(ctx, "10 minutes", "interview")
    for pid in ("[P1]", "[P2]", "[P3]"):
        assert pid in prompt
    assert "You may name ONLY the papers in the numbered list" in prompt
    assert "citations_used" not in prompt and "REAL CITATIONS" not in prompt
    assert "Stormo" not in prompt  # the old worked example named a real paper that kept reappearing
    assert "Do NOT write a References section" in prompt
    assert "Say \"the link is in the description\" ONLY right after naming a paper from the list" in prompt


def test_model_written_citations_are_gone_from_the_other_stages():
    import inspect
    import paper_processor
    import enhanced_research_service as ers
    assert "Properly formatted academic citations" not in inspect.getsource(paper_processor)
    assert ers.EnhancedResearchService._extract_citations(object(), [object()]) == []


def _pipeline():
    from research_pipeline import ComprehensiveResearchPipeline
    return ComprehensiveResearchPipeline()


class _FakePage:
    def __init__(self, status, text):
        self.status, self._text = status, text

    async def __aenter__(self):
        return self

    async def __aexit__(self, *a):
        return False

    async def text(self):
        return self._text


def _patch_session(monkeypatch, page_text):
    import aiohttp

    class _Session:
        def __init__(self, *a, **k):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *a):
            return False

        def get(self, url, timeout=None):
            return _FakePage(200, page_text)
    monkeypatch.setattr(aiohttp, "ClientSession", _Session)


def test_user_link_with_arxiv_url_becomes_a_registry_sourced_source(monkeypatch):
    f = Fake(arxiv=atom(dict(id="2603.28944v1", pub="2026-03-30T00:00:00Z", title="AI prediction leads people to forgo guaranteed rewards", summary="Newcomb abstract.")))
    monkeypatch.setattr(pc, "_default_http_get", f)
    out = run(_pipeline()._process_user_links(["https://arxiv.org/abs/2603.28944v1"], "ai"))
    assert len(out) == 1 and out[0].source == "user_provided"
    assert out[0].title == "AI prediction leads people to forgo guaranteed rewards" and out[0].abstract == "Newcomb abstract."


def test_user_link_found_by_page_metadata(monkeypatch):
    f = Fake(crossref_map={"10.1234/journal.567": crossref("Page Paper Title", "<p>Abs.</p>", 2024, "10.1234/journal.567")})
    monkeypatch.setattr(pc, "_default_http_get", f)
    _patch_session(monkeypatch, '<meta name="citation_doi" content="10.1234/Journal.567">')
    out = run(_pipeline()._process_user_links(["https://publisher.example/article"], "x"))
    assert len(out) == 1 and out[0].title == "Page Paper Title" and out[0].doi == "10.1234/journal.567"


def test_user_link_without_identifier_is_dropped_and_no_model_is_used(monkeypatch):
    monkeypatch.setattr(pc, "_default_http_get", Fake())
    _patch_session(monkeypatch, "<p>just a blog</p>")
    pipe = _pipeline()
    assert not hasattr(pipe, "_extract_metadata_with_ai")
    assert run(pipe._process_user_links(["https://blog.example/post"], "x")) == []


def test_user_link_with_unconfirmable_identifier_is_dropped(monkeypatch):
    monkeypatch.setattr(pc, "_default_http_get", Fake())
    assert run(_pipeline()._process_user_links(["https://doi.org/10.9999/none"], "x")) == []
