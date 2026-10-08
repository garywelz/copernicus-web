"""Service wiring for gap 3 fix 1 stage 2. The service module needs psutil, which is absent in some environments;
a stub is installed for the import only. Skipped if the module cannot be imported at all."""
import asyncio
import sys
from unittest.mock import MagicMock

import pytest

try:
    import psutil  # noqa: F401
except ImportError:
    sys.modules["psutil"] = MagicMock()
try:
    import services.podcast_generation_service as svc
except Exception as e:  # pragma: no cover - environment without the service's dependencies
    pytest.skip(f"service module not importable here: {e}", allow_module_level=True)

import paper_confirmation as pc
import podcast_research_integrator as pri
from models.podcast import PodcastRequest


def run(coro):
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


class _Stop(Exception):
    pass


def _confirmed(pid="P1", title="Registry Title Of The Requested Paper", venue="Registry Journal"):
    return pc.ConfirmedPaper(pid=pid, title=title, authors=["Ada Lovelace", "Alan Turing"], year=2025, venue=venue,
                             ids={"arxiv": None, "arxiv_version": None, "pmid": None, "doi": "10.1000/x1"},
                             url="https://doi.org/10.1000/x1", abstract="Registry abstract.", registry="crossref",
                             confirmed_at="2026-10-08T00:00:00Z", title_match=1.0)


def test_research_failure_types_cover_the_new_exceptions():
    names = {c.__name__ for c in (pc.InsufficientConfirmedPapers, pc.RegistryUnavailable, pc.PaperNotConfirmed)}
    assert set(svc.RESEARCH_FAILURE_TYPES) == names
    assert len(set(svc.RESEARCH_FAILURE_TYPES.values())) == 3


def test_requested_paper_venue_line_comes_from_the_confirmed_record_and_nothing_is_injected(monkeypatch):
    captured = {}

    def fake_prompt(self, **kw):
        captured.update(kw)
        raise _Stop()
    monkeypatch.setattr(pri.PodcastResearchIntegrator, "build_2_speaker_research_prompt", fake_prompt)
    req = PodcastRequest(topic="t", paper_title="Request Title", paper_doi="10.1000/x1", paper_journal="Wrong Journal From Request",
                         paper_authors=["Someone Else"], paper_year="1999")
    conf = _confirmed()
    sources = [pc.as_research_source(conf)]
    ctx = pri.PodcastResearchContext(
        topic="t", research_sources=sources, paper_analyses=[], paradigm_shifts=[], interdisciplinary_connections=[],
        key_findings=[], real_citations=[], research_quality_score=5.0, recommended_expertise_level="intermediate",
        confirmed_papers=[conf], dropped_candidates=[], requested_pid="P1")
    service = svc.PodcastGenerationService()
    with pytest.raises(_Stop):
        run(service.generate_content_from_research_context(req, ctx, "fake-key"))
    cite = captured["source_paper_citation"]
    assert "Registry Journal" in cite and "Registry Title Of The Requested Paper" in cite and "(2025)" in cite
    assert "Wrong Journal" not in cite and "Someone Else" not in cite and "1999" not in cite
    assert "[P1]" in captured["additional_instructions"] and "Wrong Journal" not in captured["additional_instructions"]
    assert ctx.research_sources == sources and len(ctx.research_sources) == 1  # no injected duplicate
