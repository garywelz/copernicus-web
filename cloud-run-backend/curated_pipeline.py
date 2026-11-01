"""Wiring of the curated script pipeline (curated_script.py) to the checks the episode must pass. Used by the generation service for a curated
run and by the admin script-only dry run. Nothing here writes to a database, a bucket or a feed: the caller decides what to store."""
from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from typing import Any, Awaitable, Callable, Dict, List, Optional

import curated_checks as cc
import curated_script as csr
import curated_sources as cs
import rejection_log
from attribution_check import check_attributions
from named_work_check import check_naming, check_reply_text, check_request
from script_style import banned_phrase_hits, prompt_list
from speech_text import notation_problems
from topic_checks import missing_coverage_statements, read_aloud_sentences, uncovered_named_things
from utils.script_validation import calculate_maximum_words_for_duration, calculate_minimum_words_for_duration

MAX_TRANSIENT_RETRIES = 6      # model errors for the whole run (it makes many more calls than one script did); each is repeated, none counts against the script
WRITER_TEMPERATURE = 0.6
WRITER_MAX_OUTPUT_TOKENS = 8192


def make_writer_llm(api_key: str, model: str = "gemini-2.5-flash", temperature: float = WRITER_TEMPERATURE, post=None) -> csr.LlmCall:
    """The section writer: the same key and REST call as the checks, but with a little temperature and room for a section."""
    import requests
    send = post or requests.post

    async def call(system: str, user: str) -> str:
        def run() -> str:
            body = check_request(system, user)
            body["generationConfig"]["temperature"] = temperature
            body["generationConfig"]["maxOutputTokens"] = WRITER_MAX_OUTPUT_TOKENS
            r = send(f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent",
                     headers={"x-goog-api-key": api_key, "Content-Type": "application/json"}, json=body, timeout=180)
            if r.status_code != 200:
                raise RuntimeError(f"{model} answered HTTP {r.status_code}: {r.text[:200]}")
            return check_reply_text(r.json())
        return await asyncio.to_thread(run)
    return call


@dataclass
class CuratedGeneration:
    content: Dict[str, Any]
    naming_result: Any
    naming_attempts: List[Dict[str, Any]]
    rejections: List[Dict[str, Any]]
    trace: List[Dict[str, Any]]
    sections: Dict[str, str]
    notes: List[Dict[str, str]]
    plan: List[Dict[str, Any]]
    final_violations: List[Dict[str, Any]] = field(default_factory=list)


def commentary_inputs(run) -> List[Dict[str, Any]]:
    out = []
    for i in run.items:
        if i["class"] == cs.COMMENTARY and i.get("evidence_text"):
            out.append({"pid": run.pids[i["item_id"]], "outlet": i.get("venue") or "", "date": i.get("date") or str(i.get("year") or ""),
                        "title": i.get("title") or "", "text": i["evidence_text"]})
    return out


async def generate_curated_content(request, research_context, check_llm: csr.LlmCall, writer_llm: csr.LlmCall, job_id: str = "", on_rejection=None,
                                   with_metadata: bool = True, sleep: Callable[[float], Awaitable[Any]] = asyncio.sleep) -> CuratedGeneration:
    """Notes, plan, sections, repair, metadata. Raises csr.NotesError / csr.ScriptRepairFailed (fail closed) or any model error that outlasts the
    transient retries. `check_llm` is the temperature-0 JSON call the existing checks use; `writer_llm` writes the sections."""
    run = research_context.curated
    confirmed = research_context.confirmed_papers
    min_words = calculate_minimum_words_for_duration(request.duration)
    max_words = calculate_maximum_words_for_duration(request.duration)
    commentary = commentary_inputs(run)
    plan = csr.plan_sections(min_words, max_words, has_commentary=bool(commentary))
    rejections: List[Dict[str, Any]] = []
    attempts: List[Dict[str, Any]] = []
    transient = {"n": 0}
    state: Dict[str, Any] = {"naming": None, "checks": 0}
    uncovered = uncovered_named_things(request.topic, confirmed)
    withheld = run.commentary_pids()

    def reject(items):
        for i, item in enumerate(items):
            item["seq"] = len(rejections) + i
        rejections.extend(items)
        if on_rejection:
            try:
                on_rejection(items)
            except Exception:
                pass

    async def model_call(stage: str, factory):
        while True:
            try:
                return await factory()
            except csr.ScriptPipelineError:               # the pipeline's own fail-closed errors are never retried
                raise
            except Exception as e:                       # a model error is repeated, not counted against the script
                transient["n"] += 1
                reject([rejection_log.transient_item(state["checks"], stage, e)])
                if transient["n"] > MAX_TRANSIENT_RETRIES:
                    raise
                await sleep(2)

    def retrying(llm: csr.LlmCall, stage: str) -> csr.LlmCall:
        async def call(system: str, user: str) -> str:
            return await model_call(stage, lambda: llm(system, user))
        return call

    notes, notes_trace = await csr.distill_notes(retrying(check_llm, "notes"), commentary) if commentary else ([], [])

    async def checker(script: str) -> List[Dict[str, Any]]:
        state["checks"] += 1
        n = state["checks"]
        naming = await model_call("naming_check", lambda: check_naming(script, "", confirmed, check_llm, topic=request.topic))
        state["naming"] = naming
        bad_notation = notation_problems(script, "")
        banned = banned_phrase_hits(script, "")
        read_aloud = read_aloud_sentences(script, request.topic)
        missing_cov = missing_coverage_statements(script, uncovered)
        curated = run.checks(script)
        attribution = None
        if naming.passed:
            named = [c for c in confirmed if c.pid in naming.named_pids]
            attribution = await model_call("attribution_check", lambda: check_attributions(script, named, check_llm))
            reject(rejection_log.attribution_items(n, attribution.checked, withheld))
        entry = {"attempt": n, **naming.summary(), "unspeakable_notation": bad_notation,
                 "banned_phrases": [{"phrase": h["phrase"], "matched": h["matched"], "where": h["where"]} for h in banned],
                 "curated_checks": cc.summary(curated), "topic_read_aloud": len(read_aloud), "coverage_statement_missing": missing_cov,
                 "words": len(script.split())}
        if attribution is not None:
            entry["attribution"] = attribution.summary()
        attempts.append(entry)
        viol = csr.collect_violations(naming, attribution, bad_notation, banned, read_aloud, missing_cov, curated)
        reject(rejection_log.naming_items(n, naming.violations) + rejection_log.notation_items(n, bad_notation) + rejection_log.banned_items(n, banned)
               + rejection_log.read_aloud_items(n, read_aloud) + rejection_log.coverage_items(n, missing_cov) + rejection_log.curated_items(n, curated))
        return viol

    builder = csr.ScriptBuilder(retrying(writer_llm, "section_writer"), run, plan, notes, checker, banned=prompt_list())
    try:
        result = await builder.build()
    except csr.ScriptRepairFailed as e:
        reject([{"check": "script_repair", "kind": "repair_failed", "attempt": state["checks"],
                 "remaining": sorted({f"{v['check']}:{v['kind']}" for v in e.violations})}])
        raise
    script = result.script

    description_fallback = f"This episode looks at {request.topic}. The sources are listed under References."

    def validate(title: str, description: str) -> List[str]:
        problems = [f"banned wording \"{h['matched']}\": {h['sentence']}" for h in banned_phrase_hits("", description)]
        problems += [f"notation that cannot be read aloud: {p}" for p in notation_problems("", description)]
        problems += [f"status wording \"{v['term']}\": {v['sentence']}" for v in cc.check_status_wording(description, run.results()) if v["kind"] == "forbidden_term"]
        return problems

    meta: Dict[str, Any] = {"title": request.topic, "description": description_fallback, "keywords": []}
    meta_trace: List[Dict[str, Any]] = []
    if with_metadata:
        meta, meta_trace = await csr.write_metadata(
            retrying(check_llm, "metadata"), script, csr.allowed_works_block(run), validate, title_override=run.title,
            fallback_description=description_fallback)
        meta["title"] = meta.get("title") or request.topic
    content = {"title": meta["title"], "script": script, "description": meta["description"], "keywords": meta.get("keywords") or [],
               "research_quality_score": research_context.research_quality_score, "research_sources_used": len(research_context.research_sources),
               "significance": research_context.significance}
    return CuratedGeneration(content=content, naming_result=state["naming"], naming_attempts=attempts, rejections=rejections,
                             trace=notes_trace + result.trace + meta_trace, sections=result.sections, notes=[n.to_dict() for n in notes],
                             plan=[s.to_dict() for s in plan], final_violations=result.checks_final)
