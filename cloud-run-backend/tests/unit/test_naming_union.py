"""The References are built from the union of every naming pass (job 4be6927a: the final check recognised a listed paper the first pass had missed and
the episode failed closed). Only a listed paper can enter the union; an unlisted work recognised by any pass still fails the episode."""
import copy
from types import SimpleNamespace

import pytest

import attribution_check as ac
import named_work_check as nw
from models.podcast import PodcastRequest
from tests.unit.test_curated_generation import CLEAN, context, padded, run, svc

REQ = PodcastRequest(topic="t")


def sequence(monkeypatch, passes):
    """The naming check answers with each result in `passes` in turn (then the last one again)."""
    seen = {"n": 0}

    async def fake_naming(script, description, confirmed, llm, topic=""):
        res = passes[min(seen["n"], len(passes) - 1)]
        seen["n"] += 1
        return nw.NamingResult(violations=list(res.get("violations", [])), named_pids=list(res.get("named", [])), mentions=[])

    async def fake_attr(script, named, llm, curated_run=None):
        return ac.AttributionResult()
    monkeypatch.setattr(svc, "check_naming", fake_naming)
    monkeypatch.setattr(svc, "check_attributions_for", fake_attr)
    monkeypatch.setattr(svc, "make_gemini_llm_call", lambda key: None)
    return seen


def built(ctx, named):
    """What the job holds just before the final check: the content before the References were built, and the content after they were built from `named`."""
    service = svc.PodcastGenerationService()
    pre = {"title": "A title that is long enough", "script": padded(CLEAN), "description": "Intro.\n\n## References\n\n- invented line\n"}
    content = copy.deepcopy(pre)
    naming_result = SimpleNamespace(named_pids=list(named))
    metrics = service._finalize_content(content, REQ, ctx, naming_result)
    return service, pre, content, metrics, naming_result


def pids(ctx):
    return [c.pid for c in ctx.confirmed_papers]


def title_of(ctx, pid):
    return next(c.title for c in ctx.confirmed_papers if c.pid == pid)


def test_a_paper_recognised_only_by_the_second_pass_ends_up_in_the_references_and_the_run_passes(monkeypatch):
    ctx = context()
    a, b = pids(ctx)[:2]
    service, pre, content, metrics, naming_result = built(ctx, [a])
    assert content["papers_named"] == [a] and title_of(ctx, b) not in content["description"]
    seen = sequence(monkeypatch, [{"named": [a, b]}])                      # the final pass names one more listed paper
    out = run(service._verify_with_union(content, pre, metrics, REQ, ctx, naming_result, "k", "job"))
    assert content["papers_named"] == [a, b] and naming_result.named_pids == [a, b]
    assert title_of(ctx, b) in content["description"] and "invented line" not in content["description"]
    assert content["final_text_checks"]["named_pids"] == [a, b] and seen["n"] == 2 and "description_chars_before_limit" in out


def test_the_union_can_grow_over_two_rounds_and_stays_in_the_confirmed_order(monkeypatch):
    ctx = context()
    p = pids(ctx)
    service, pre, content, metrics, naming_result = built(ctx, [p[2]])
    sequence(monkeypatch, [{"named": [p[2], p[0]]}, {"named": [p[2], p[0], p[1]]}])
    run(service._verify_with_union(content, pre, metrics, REQ, ctx, naming_result, "k", "job"))
    assert content["papers_named"] == [x for x in p if x in (p[0], p[1], p[2])]


def test_a_paper_that_is_not_listed_never_enters_the_union():
    ctx = context()
    assert svc.naming_union(ctx.confirmed_papers, ["P99", "nonsense"], None, []) == []
    assert svc.naming_union(ctx.confirmed_papers, [pids(ctx)[1]], [pids(ctx)[0], "P99"]) == pids(ctx)[:2]


def violation():
    return {"kind": "unlisted_work", "where": "script", "quote": "Pat Quimby showed it in 2021", "authors": ["Quimby"], "year": 2021, "title_words": []}


def test_an_unlisted_work_recognised_by_the_final_pass_still_fails_the_episode(monkeypatch):
    ctx = context()
    service, pre, content, metrics, naming_result = built(ctx, [pids(ctx)[0]])
    sequence(monkeypatch, [{"named": [pids(ctx)[0]], "violations": [violation()]}])
    with pytest.raises(nw.NamingViolationError):
        run(service._verify_with_union(content, pre, metrics, REQ, ctx, naming_result, "k", "job"))


def test_an_unlisted_work_recognised_only_after_the_references_were_rebuilt_still_fails(monkeypatch):
    ctx = context()
    a, b = pids(ctx)[:2]
    service, pre, content, metrics, naming_result = built(ctx, [a])
    sequence(monkeypatch, [{"named": [a, b]}, {"named": [a, b], "violations": [violation()]}])
    with pytest.raises(nw.NamingViolationError):
        run(service._verify_with_union(content, pre, metrics, REQ, ctx, naming_result, "k", "job"))


def test_every_pass_of_the_generation_loop_counts_not_only_the_last():
    ctx = context()
    a, b, c = pids(ctx)[:3]
    attempts = [{"named_pids": [a]}, {"named_pids": [b]}, "not a dict", {"named_pids": None}]
    union = svc.naming_union(ctx.confirmed_papers, [c], *[x.get("named_pids") for x in attempts if isinstance(x, dict)])
    assert union == [a, b, c]


def test_the_job_builds_the_union_before_the_references_and_checks_against_it():
    import inspect
    src = inspect.getsource(svc.PodcastGenerationService.run_podcast_generation_job)
    assert src.index("naming_union(") < src.index("self._finalize_content(") < src.index("self._verify_with_union(")
    assert "pre_final_content = copy.deepcopy(content)" in src
