"""Scripted fakes for the sandbox harness (--stub): the whole flow runs offline, with no network, keys or models.

Scenarios are chosen by the topic spec's "scenario" field:
  ok             three confirmable papers, a clean script that names two of them
  bad_then_good  the first script names an unlisted work; the regenerated one is clean
  never_good     every script names an unlisted work, so the episode fails after two regenerations
  thin           only two papers can be confirmed, so research fails early
  registry_down  the arXiv registry is unreachable
  paper_request  a directly requested paper (confirmed by DOI) plus three arXiv papers
  long_body      like ok, with a description long enough that the 4000-character limit trims the body
"""
from __future__ import annotations

import json
import os
import sys
from typing import Any, Dict

import paper_confirmation as pc
import named_work_check as nw

ATOM = '<?xml version="1.0"?><feed xmlns="http://www.w3.org/2005/Atom">{}</feed>'
ENTRY = ('<entry><id>http://arxiv.org/abs/{id}</id><published>2026-01-01T00:00:00Z</published><title>{title}</title>'
         '<summary>{summary}</summary><author><name>{a1}</name></author><author><name>{a2}</name></author></entry>')

AUTHORS = {1: ("Ada Lovelace", "Alan Turing"), 2: ("Grace Hopper", "Edsger Dijkstra"), 3: ("Marie Curie", "Pierre Curie")}


def _paper_title(i: int) -> str:
    return f"Sandbox paper number {i} about neural computation"


class FakeRegistries:
    def __init__(self, down: bool = False, crossref_title: str = ""):
        self.down, self.crossref_title = down, crossref_title

    async def __call__(self, url: str, params: Dict[str, str]):
        if "export.arxiv.org" in url:
            if self.down:
                return 503, ""
            ids = [x.split("v")[0] for x in params["id_list"].split(",")]
            entries = ""
            for aid in ids:
                i = int(aid.split(".")[1])
                a1, a2 = AUTHORS.get(i, ("Some Author", "Other Author"))
                entries += ENTRY.format(id=aid + "v1", title=_paper_title(i), summary=f"Abstract of paper {i}.", a1=a1, a2=a2)
            return 200, ATOM.format(entries)
        if "api.crossref.org" in url and self.crossref_title:
            return 200, json.dumps({"message": {"title": [self.crossref_title], "DOI": url.split("/works/")[1], "issued": {"date-parts": [[2025]]},
                                                 "container-title": ["Journal of Sandbox"], "author": [{"given": "Rosalind", "family": "Franklin"}],
                                                 "abstract": "<p>Requested paper abstract.</p>"}})
        return 404, ""


def _src(i: int):
    from types import SimpleNamespace
    return SimpleNamespace(title=_paper_title(i), url=f"http://arxiv.org/abs/2601.0000{i}v1", doi=None, publication_date="2026", authors=["x"],
                           abstract="x", source="arxiv", journal=None, pid=None)


def _words(n: int) -> str:
    return " ".join(["cells"] * n)


def build_stub(spec: Dict[str, Any]):
    import services.podcast_generation_service as svc
    import podcast_research_integrator as pri
    scenario = spec.get("scenario", "ok")
    pc._default_http_get = FakeRegistries(down=(scenario == "registry_down"), crossref_title="Requested sandbox paper title" if scenario == "paper_request" else "")

    integrator = pri.PodcastResearchIntegrator("fake-key")
    n_sources = 2 if scenario == "thin" else 3
    candidates = [_src(i) for i in range(1, n_sources + 1)]

    async def fake_search(**kw):
        return list(candidates)

    class _Analysis:
        def __init__(self, title):
            self.title, self.analysis_failed, self.paradigm_shift_potential = title, False, "high"
            self.interdisciplinary_connections, self.key_findings, self.technical_complexity = ["x"], [f"finding about {title}"], "low"

    class _Gemini:
        paradigm_shifts, interdisciplinary_connections, key_findings, citations = ["shift"], [], ["gemini finding"], ["MODEL-WRITTEN CITATION"]

    async def fake_multi(srcs, complexity=None):
        return [_Analysis(s.title) for s in srcs]

    async def fake_gemini(paper, options, key):
        return _Gemini()
    integrator.research_pipeline.comprehensive_search = fake_search
    integrator.enhanced_research_service.analyze_multiple_papers = fake_multi
    pri.analyze_paper_with_gemini = fake_gemini

    service = svc.PodcastGenerationService()
    min_words = svc.calculate_minimum_words_for_duration(spec.get("duration", "5-10 minutes"))
    clean = ("ADAM: According to Lovelace and Turing in 2026, neural computation works. The link is in the description. "
             "MATILDA: And Hopper and Dijkstra in 2026 agree. " + _words(min_words + 20))
    bad = clean + " ADAM: Zorblatt and Quux showed in 2019 that it does not."
    body = "Overview of the episode. " + ("A long paragraph about neural computation and its history. " * (60 if scenario == "long_body" else 5))
    desc = body + "\n\n## References\n\n- Model Wrote This (2019). Fake Paper. DOI: 10.9/fake\n\n## Hashtags\n#neural #cells\n"
    scripts = {"ok": [clean], "long_body": [clean], "paper_request": [clean], "thin": [clean], "registry_down": [clean],
               "bad_then_good": [bad, clean], "never_good": [bad, bad, bad]}[scenario]
    state = {"n": 0}

    async def fake_generate(request, ctx, key, retry_attempt=0, naming_feedback=""):
        text = scripts[min(state["n"], len(scripts) - 1)]
        state["n"] += 1
        return {"title": "Sandbox episode", "script": text, "description": desc}
    service.generate_content_from_research_context = fake_generate

    async def llm(system, user):
        ms = []
        if "Lovelace and Turing" in user:
            ms.append({"quote": "Lovelace and Turing in 2026", "authors": ["Lovelace", "Turing"], "year": 2026, "title_words": []})
        if "Hopper and Dijkstra" in user:
            ms.append({"quote": "Hopper and Dijkstra in 2026", "authors": ["Hopper", "Dijkstra"], "year": 2026, "title_words": []})
        if "Zorblatt" in user:
            ms.append({"quote": "Zorblatt and Quux showed in 2019", "authors": ["Zorblatt", "Quux"], "year": 2019, "title_words": []})
        return json.dumps({"mentions": ms})
    svc.make_gemini_llm_call = lambda key: llm

    async def no_sleep(*a, **k):
        return None
    svc.asyncio.sleep = no_sleep
    return service, integrator, "fake-key", (lambda key: llm)
