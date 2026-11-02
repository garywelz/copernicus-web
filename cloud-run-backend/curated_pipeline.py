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
    model_calls: Dict[str, int] = field(default_factory=dict)


def commentary_inputs(run) -> List[Dict[str, Any]]:
    out = []
    for i in run.items:
        if i["class"] == cs.COMMENTARY and i.get("evidence_text"):
            out.append({"pid": run.pids[i["item_id"]], "outlet": i.get("venue") or "", "date": i.get("date") or str(i.get("year") or ""),
                        "title": i.get("title") or "", "text": i["evidence_text"]})
    return out


def diagnostics(diag: Dict[str, Any]) -> Dict[str, Any]:
    """What a failed run leaves for the administrator: model calls, rounds, each section's words against its budget, every check's result. It holds
    no pasted text and no draft note (the trace and the checks never carry them)."""
    builder = diag.get("builder")
    plan = diag.get("plan") or []
    sections = (builder.sections if builder is not None else {}) or {}
    return {"model_calls": dict(diag.get("calls") or {}), "model_calls_total": sum((diag.get("calls") or {}).values()),
            "trace": (diag.get("notes_trace") or []) + (builder.trace if builder is not None else []),
            "section_words": {k: {"words": len(v.split()), **next(({"budget": p["budget"], "lo": p["lo"], "hi": p["hi"]} for p in plan if p["key"] == k), {})}
                              for k, v in sections.items()},
            "checks": diag.get("attempts") or [], "plan": plan, "rejection_count": len(diag.get("rejections") or [])}


async def generate_curated_content(request, research_context, check_llm: csr.LlmCall, writer_llm: csr.LlmCall, job_id: str = "", on_rejection=None,
                                   with_metadata: bool = True, sleep: Callable[[float], Awaitable[Any]] = asyncio.sleep) -> CuratedGeneration:
    """Notes, plan, sections, repair, metadata. Raises csr.NotesError / csr.ScriptRepairFailed (fail closed) or any model error that outlasts the
    transient retries; a pipeline error carries `.diagnostics` (see `diagnostics`). `check_llm` is the temperature-0 JSON call the existing checks use;
    `writer_llm` writes the sections."""
    diag: Dict[str, Any] = {}
    try:
        return await _generate(request, research_context, check_llm, writer_llm, job_id, on_rejection, with_metadata, sleep, diag)
    except csr.ScriptPipelineError as e:
        e.diagnostics = diagnostics(diag)
        raise


async def _generate(request, research_context, check_llm, writer_llm, job_id, on_rejection, with_metadata, sleep, diag) -> CuratedGeneration:
    run = research_context.curated
    confirmed = research_context.confirmed_papers
    min_words = calculate_minimum_words_for_duration(request.duration)
    max_words = calculate_maximum_words_for_duration(request.duration)
    commentary = commentary_inputs(run)
    plan = csr.plan_sections(min_words, max_words, has_commentary=bool(commentary))
    rejections: List[Dict[str, Any]] = []
    attempts: List[Dict[str, Any]] = []
    calls: Dict[str, int] = {"notes": 0, "section_writer": 0, "checks": 0, "metadata": 0}
    diag.update(calls=calls, attempts=attempts, rejections=rejections, plan=[p.to_dict() for p in plan])
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

    def counting(llm: csr.LlmCall, key: str) -> csr.LlmCall:
        async def call(system: str, user: str) -> str:
            calls[key] += 1
            return await llm(system, user)
        return call

    def retrying(llm: csr.LlmCall, stage: str) -> csr.LlmCall:
        counted = counting(llm, stage)

        async def call(system: str, user: str) -> str:
            return await model_call(stage, lambda: counted(system, user))
        return call

    check_counted = counting(check_llm, "checks")
    try:
        notes, notes_trace = await csr.distill_notes(retrying(check_llm, "notes"), commentary) if commentary else ([], [])
    except csr.NotesError as e:
        diag["notes_trace"] = [{"stage": "notes", "pid": e.pid, "failed": True, "kinds": sorted({v["kind"] for v in e.violations})}]
        raise
    diag["notes_trace"] = notes_trace
    run.reporting_text = csr.reporting_text(run, notes)         # whose names may be used as a reporting attribution

    async def checker(script: str) -> List[Dict[str, Any]]:
        state["checks"] += 1
        n = state["checks"]
        naming = await model_call("naming_check", lambda: check_naming(script, "", confirmed, check_counted, topic=request.topic))
        naming.violations, exempted = csr.exempt_reporting_attributions(naming.violations, run.reporting_text)     # only a name used as a reporting attribution
        state["naming"] = naming
        bad_notation = notation_problems(script, "")
        banned = banned_phrase_hits(script, "")
        read_aloud = read_aloud_sentences(script, request.topic)
        missing_cov = missing_coverage_statements(script, uncovered)
        curated = run.checks(script)
        attribution = None
        if naming.passed:
            named = [c for c in confirmed if c.pid in naming.named_pids]
            attribution = await model_call("attribution_check", lambda: check_attributions(script, named, check_counted))
            reject(rejection_log.attribution_items(n, attribution.checked, withheld))
        entry = {"attempt": n, **naming.summary(), "unspeakable_notation": bad_notation,
                 "banned_phrases": [{"phrase": h["phrase"], "matched": h["matched"], "where": h["where"]} for h in banned],
                 "curated_checks": cc.summary(curated), "topic_read_aloud": len(read_aloud), "coverage_statement_missing": missing_cov,
                 "words": len(script.split()), "naming_reporting_attributions_exempt": len(exempted)}
        if attribution is not None:
            entry["attribution"] = attribution.summary()
        attempts.append(entry)
        viol = csr.collect_violations(naming, attribution, bad_notation, banned, read_aloud, missing_cov, curated)
        reject(rejection_log.naming_items(n, naming.violations) + rejection_log.notation_items(n, bad_notation) + rejection_log.banned_items(n, banned)
               + rejection_log.read_aloud_items(n, read_aloud) + rejection_log.coverage_items(n, missing_cov) + rejection_log.curated_items(n, curated))
        return viol

    builder = csr.ScriptBuilder(retrying(writer_llm, "section_writer"), run, plan, notes, checker, banned=prompt_list(), window=(min_words, max_words))
    diag["builder"] = builder
    try:
        result = await builder.build()
    except csr.ScriptRepairFailed as e:
        reject([{"check": "script_repair", "kind": "repair_failed", "attempt": state["checks"],
                 "remaining": sorted({f"{v['check']}:{v['kind']}" for v in e.violations})}])
        raise
    script = result.script

    description_fallback = f"This episode looks at {request.topic}. The sources are listed under References."

    async def validate(title: str, description: str) -> List[str]:
        problems = [f"banned wording \"{h['matched']}\": {h['sentence']}" for h in banned_phrase_hits("", description)]
        problems += [f"notation that cannot be read aloud: {p}" for p in notation_problems("", description)]
        problems += [f"status wording \"{v['term']}\": {v['sentence']}" for v in cc.check_status_wording(description, run.results()) if v["kind"] == "forbidden_term"]
        naming = await model_call("naming_check", lambda: check_naming(script, description, confirmed, check_counted, topic=request.topic))
        kept, _ = csr.exempt_reporting_attributions(naming.violations, run.reporting_text)
        problems += [f"the description names a work that is not allowed: {v['quote'][:120]}" for v in kept if v.get("where") == "description"]
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
                             plan=[s.to_dict() for s in plan], final_violations=result.checks_final, model_calls=dict(calls))


# --- a script supplied by an editor -------------------------------------------------------------------------------------------------------------
class SuppliedScriptRejected(csr.ScriptPipelineError):
    def __init__(self, violations: List[Dict[str, Any]]):
        self.violations = list(violations)
        super().__init__("The supplied script failed the checks (" + ", ".join(sorted({f"{v['check']}:{v['kind']}" for v in self.violations})) + "), so no episode was generated.")


@dataclass
class SuppliedCheck:
    passed: bool
    words: int
    min_words: int
    max_words: int
    format_problems: List[str]
    violations: List[Dict[str, Any]]
    entry: Dict[str, Any]
    naming_result: Any = None
    content: Optional[Dict[str, Any]] = None
    model_calls: Dict[str, int] = field(default_factory=dict)

    @property
    def length_ok(self) -> bool:
        return self.min_words <= self.words <= self.max_words


def supplied_reporting_text(run) -> str:
    """Whose NAMES may be used as a reporting attribution in a supplied script. A generated script has approved notes; a supplied one has none, so
    the text is what the notes are made from: the venue and authors recorded on the list's commentary, and the pasted commentary itself. The
    exemption's own conditions are unchanged (a reporting verb, no title, no year, no "et al.")."""
    texts = " ".join(i.get("evidence_text") or "" for i in run.items if i["class"] == cs.COMMENTARY)
    return csr.reporting_text(run, []) + " " + csr._norm(texts)


def script_format_problems(script: str) -> List[str]:
    lines = [ln.strip() for ln in (script or "").replace("\r", "").split("\n") if ln.strip()]
    if not lines:
        return ["the script is empty"]
    bad = [ln for ln in lines if not csr.SPEAKER_LINE.match(ln)]
    return [f"every line must start with HOST: or EXPERT: ({len(bad)} do not; the first is: {bad[0][:60]})"] if bad else []


async def check_supplied_script(request, research_context, check_llm: csr.LlmCall, script: str, title: str = "", job_id: str = "",
                                with_metadata: bool = False, sleep: Callable[[float], Awaitable[Any]] = asyncio.sleep) -> SuppliedCheck:
    """Every check a generated curated script passes, on a script somebody else wrote: the same checks in the same order as `_generate`'s checker
    (naming with the reporting-attribution exemption, attribution, notation, banned wording, topic read aloud, coverage, every curated check), plus
    the duration window and the line format. Nothing is repaired or rewritten; a violation is reported. With `with_metadata` and a clean script it also
    writes the description and keywords (a model call), as for a generated script. Writes nothing."""
    run = research_context.curated
    confirmed = research_context.confirmed_papers
    min_words = calculate_minimum_words_for_duration(request.duration)
    max_words = calculate_maximum_words_for_duration(request.duration)
    calls: Dict[str, int] = {"checks": 0, "metadata": 0}
    transient = {"n": 0}

    async def model_call(factory):
        while True:
            try:
                return await factory()
            except csr.ScriptPipelineError:
                raise
            except Exception:
                transient["n"] += 1
                if transient["n"] > MAX_TRANSIENT_RETRIES:
                    raise
                await sleep(2)

    async def counted(system: str, user: str) -> str:
        calls["checks"] += 1
        return await check_llm(system, user)

    words = len(script.split())
    fmt = script_format_problems(script)
    run.reporting_text = supplied_reporting_text(run)
    uncovered = uncovered_named_things(request.topic, confirmed)
    naming = await model_call(lambda: check_naming(script, "", confirmed, counted, topic=request.topic))
    naming.violations, exempted = csr.exempt_reporting_attributions(naming.violations, run.reporting_text)
    bad_notation = notation_problems(script, "")
    banned = banned_phrase_hits(script, "")
    read_aloud = read_aloud_sentences(script, request.topic)
    missing_cov = missing_coverage_statements(script, uncovered)
    curated = run.checks(script)
    attribution = None
    if naming.passed:
        named = [c for c in confirmed if c.pid in naming.named_pids]
        attribution = await model_call(lambda: check_attributions(script, named, counted))
    entry = {"attempt": 1, **naming.summary(), "unspeakable_notation": bad_notation,
             "banned_phrases": [{"phrase": h["phrase"], "matched": h["matched"], "where": h["where"]} for h in banned],
             "curated_checks": cc.summary(curated), "topic_read_aloud": len(read_aloud), "coverage_statement_missing": missing_cov,
             "words": words, "naming_reporting_attributions_exempt": len(exempted)}
    if attribution is not None:
        entry["attribution"] = attribution.summary()
    violations = csr.collect_violations(naming, attribution, bad_notation, banned, read_aloud, missing_cov, curated)
    if words > max_words:
        violations.append({"check": "length", "kind": "too_long", "find": None, "message": f"The script has {words} words; the most for this duration is {max_words}."})
    if words < min_words:
        violations.append({"check": "length", "kind": "too_short", "find": None, "message": f"The script has {words} words; the least for this duration is {min_words}."})
    for p in fmt:
        violations.append({"check": "format", "kind": "line_format", "find": None, "message": p})
    result = SuppliedCheck(passed=not violations, words=words, min_words=min_words, max_words=max_words, format_problems=fmt, violations=violations,
                           entry=entry, naming_result=naming, model_calls=calls)
    if result.passed and with_metadata:
        description_fallback = f"This episode looks at {request.topic}. The sources are listed under References."

        async def validate(t: str, description: str) -> List[str]:
            problems = [f"banned wording \"{h['matched']}\": {h['sentence']}" for h in banned_phrase_hits("", description)]
            problems += [f"notation that cannot be read aloud: {p}" for p in notation_problems("", description)]
            problems += [f"status wording \"{v['term']}\": {v['sentence']}" for v in cc.check_status_wording(description, run.results()) if v["kind"] == "forbidden_term"]
            n2 = await model_call(lambda: check_naming(script, description, confirmed, counted, topic=request.topic))
            kept, _ = csr.exempt_reporting_attributions(n2.violations, run.reporting_text)
            problems += [f"the description names a work that is not allowed: {v['quote'][:120]}" for v in kept if v.get("where") == "description"]
            return problems

        async def metadata_llm(system: str, user: str) -> str:
            calls["metadata"] += 1
            return await check_llm(system, user)

        meta, _ = await csr.write_metadata(metadata_llm, script, csr.allowed_works_block(run), validate, title_override=title or run.title,
                                           fallback_description=description_fallback)
        result.content = {"title": title or meta.get("title") or request.topic, "script": script, "description": meta["description"],
                          "keywords": meta.get("keywords") or [], "research_quality_score": research_context.research_quality_score,
                          "research_sources_used": len(research_context.research_sources), "significance": research_context.significance}
    return result
