"""The curated pipeline wired to the real checks (curated_pipeline.py): notes, plan, sections, repair, metadata, the records it leaves, and that the
raw pasted text reaches only the notes step. Offline: both model calls are scripted fakes; the checks are the real ones."""
import asyncio
import json
import sys
from unittest.mock import MagicMock

import pytest

try:
    import psutil  # noqa: F401
except ImportError:
    sys.modules["psutil"] = MagicMock()

import curated_checks as cc
import curated_mode as cm
import curated_pipeline as cp
import curated_script as csr
import curated_sources as cs
import paper_confirmation as pc
import podcast_research_integrator as pri
from models.podcast import PodcastRequest
from tests.unit.test_curated_mode import PRIVATE, approved_doc, base_items, commentary_item

SECRET = "zebra quartz marmalade lantern orbit velvet cinnamon harbour"
TEXT = ("The reporter wrote that " + SECRET + " was how one mathematician described the mood. Another expert said the proofs need careful reading "
        "before anyone can say what they establish, and a third said the release was surprising in its scale and timing.")
NOTES = [{"claim": "A mathematician quoted in the report described the mood among number theorists after the release as one of cautious surprise."},
         {"claim": "Another expert told the reporter that nobody can say what the proofs establish until they have been read carefully."}]
REQUEST = PodcastRequest(topic="t", duration="1-2 minutes", expertise_level="general")
PLAN = csr.plan_sections(120, 240)


def run(coro):
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


def context():
    r = cm.CuratedRun.from_list_doc(approved_doc(base_items() + [commentary_item(evidence_text=TEXT)]), private_texts=PRIVATE, title=None)
    conf = r.confirmed_papers()
    return pri.PodcastResearchContext(
        topic=r.topic, research_sources=[pc.as_research_source(c) for c in conf if c.source_class != cs.COMMENTARY], paper_analyses=[], significance=["s"],
        interdisciplinary_connections=[], key_findings=[], real_citations=[], research_quality_score=5.0, recommended_expertise_level="general",
        confirmed_papers=conf, dropped_candidates=[], requested_pid=None, curated=r)


def filler(section, n=None, line=None):
    """A clean section of exactly n words (default: its budget); `line` replaces the second line."""
    n = n or section.budget
    half = n // 2
    first = "HOST: " + " ".join(f"{section.key}a{i}" for i in range(half - 1)) + "."
    rest = n - half
    second = line or ("EXPERT: " + " ".join(f"{section.key}b{i}" for i in range(rest - 1)) + ".")
    if line:
        second += " " + " ".join(f"{section.key}c{i}" for i in range(max(0, rest - len(line.split()) - 1))) + ("." if rest - len(line.split()) - 1 > 0 else "")
    return first + "\n" + second


LABEL = filler(PLAN[1], line="EXPERT: A company release has not been peer reviewed.")     # naming a company release needs this somewhere in the script


class Writer:
    def __init__(self, bad=None):
        self.bad, self.calls, self.repairs = bad or {}, [], []

    async def __call__(self, system, user):
        self.calls.append((system, user))
        if system.startswith(csr.REPAIR_SYSTEM):
            title = user.split("SECTION: ", 1)[1].split(" (", 1)[0]
            section = next(s for s in PLAN if s.title == title)
            self.repairs.append(section.key)
            old = user.split("THE SECTION AS IT IS:\n", 1)[1].split("\n")
            fixed = [ln if not any(m in ln for m in ("formally verified", "Matilda", SECRET[:30])) else
                     "EXPERT: " + " ".join(f"{section.key}z{i}" for i in range(len(ln.split()) - 1)) + "." for ln in old]
            return json.dumps({"dialogue": "\n".join(fixed)})
        title = user.split("WRITE SECTION: ", 1)[1].split("\n", 1)[0]
        section = next(s for s in PLAN if s.title == title)
        return json.dumps({"dialogue": self.bad.get(section.key) or filler(section)})


class Checker:
    """The temperature-0 JSON model: notes, naming, attribution, metadata."""

    def __init__(self, notes=None, metadata=None):
        self.notes, self.metadata, self.calls = notes if notes is not None else NOTES, metadata, []

    async def __call__(self, system, user):
        self.calls.append((system, user))
        if system.startswith("You turn ONE pasted"):
            return json.dumps({"notes": self.notes})
        if system.startswith(csr.METADATA_SYSTEM[:30]):
            return json.dumps(self.metadata or {"title": "Model title", "description": "A plain summary of the episode.", "keywords": ["maths"]})
        return json.dumps({"attributions": []}) if ("PAPERS:" in user and "SCRIPT:" in user) else json.dumps({"mentions": []})


def generate(writer=None, checker=None, **kw):
    writer, checker = writer or Writer(), checker or Checker()

    async def no_sleep(_):
        return None
    ctx = context()
    kw.setdefault("sleep", no_sleep)
    return run(cp.generate_curated_content(REQUEST, ctx, checker, writer, job_id="j", **kw)), writer, checker


def test_a_clean_run_writes_each_section_once_and_returns_the_content_the_job_needs():
    gen, writer, checker = generate()
    c = gen.content
    assert c["title"] == "Model title" and c["description"].startswith("A plain summary") and c["keywords"] == ["maths"]
    assert 120 <= len(c["script"].split()) <= 240 and c["research_quality_score"] == 5.0 and c["research_sources_used"] == 3
    assert len([x for x in writer.calls if not x[0].startswith(csr.REPAIR_SYSTEM)]) == len(PLAN) and writer.repairs == []
    assert gen.naming_result.passed and len(gen.naming_attempts) == 1 and gen.naming_attempts[0]["curated_checks"] == {}
    assert [n["pid"] for n in gen.notes] == ["P4", "P4"] and [p["key"] for p in gen.plan] == [s.key for s in PLAN]


def test_the_raw_pasted_text_reaches_only_the_notes_step_never_the_section_writer_or_the_metadata():
    gen, writer, checker = generate()
    assert all(SECRET not in s + u for s, u in writer.calls)
    notes_calls = [x for x in checker.calls if x[0].startswith("You turn ONE pasted")]
    assert len(notes_calls) == 1 and SECRET in notes_calls[0][1]
    assert all(SECRET not in s + u for s, u in checker.calls if not s.startswith("You turn ONE pasted"))
    assert SECRET not in json.dumps(gen.trace) and SECRET not in json.dumps(gen.rejections) and SECRET not in json.dumps(gen.naming_attempts)


def test_the_producers_title_is_used_and_the_model_does_not_choose_one():
    ctx = context()
    ctx.curated.title = "722 papers overnight: OpenAI's mathematics release"

    async def no_sleep(_):
        return None
    gen = run(cp.generate_curated_content(REQUEST, ctx, Checker(), Writer(), sleep=no_sleep))
    assert gen.content["title"] == "722 papers overnight: OpenAI's mathematics release"


def test_a_status_wording_violation_is_repaired_in_its_section_and_the_other_sections_are_untouched():
    bad_line = "EXPERT: The Exponential Time Hypothesis is False was formally verified in Lean."
    bad = {"status": filler(PLAN[3], line=bad_line), "sources": LABEL}
    gen, writer, _ = generate(Writer(bad))
    assert writer.repairs == ["status"] and "formally verified" not in gen.content["script"]
    for s in PLAN:
        if s.key != "status":
            assert gen.sections[s.key] == (bad.get(s.key) or filler(s))
    assert any(r["check"] == "status_wording" for r in gen.rejections) and gen.naming_attempts[0]["curated_checks"] and gen.naming_attempts[1]["curated_checks"] == {}
    assert len([x for x in writer.calls if not x[0].startswith(csr.REPAIR_SYSTEM)]) == len(PLAN)         # nothing was regenerated


def test_a_spoken_name_and_a_copied_run_are_both_repaired_without_regenerating():
    bad = {"opening": filler(PLAN[0], line="EXPERT: Hello, I'm Matilda."), "reception": filler(PLAN[4], line="EXPERT: " + SECRET + " and so on.")}
    gen, writer, _ = generate(Writer(bad))
    assert sorted(writer.repairs) == ["opening", "reception"] and "Matilda" not in gen.content["script"] and SECRET not in gen.content["script"]
    kinds = {r["check"] for r in gen.rejections}
    assert {"spoken_name", "verbatim_run"} <= kinds


def test_a_script_that_cannot_be_repaired_fails_closed_with_the_violations_and_a_repair_record():
    class Stubborn(Writer):
        async def __call__(self, system, user):
            if system.startswith(csr.REPAIR_SYSTEM):
                self.calls.append((system, user))
                return "not json"
            return await super().__call__(system, user)
    writer = Stubborn({"status": filler(PLAN[3], line="EXPERT: The Exponential Time Hypothesis is False was formally verified in Lean."), "sources": LABEL})
    stored = []
    with pytest.raises(csr.ScriptRepairFailed) as e:
        generate(writer, on_rejection=stored.extend)
    assert {v["kind"] for v in e.value.violations} == {"forbidden_term"}
    assert any(r["check"] == "script_repair" and r["kind"] == "repair_failed" for r in stored) and any(r["check"] == "status_wording" for r in stored)


def test_notes_that_cannot_be_made_neutral_stop_the_run_before_any_script_is_written():
    verified = [{"claim": "An expert said the first proof had been formally verified by the Lean checker in October."}, NOTES[1]]
    writer = Writer()
    with pytest.raises(csr.NotesError):
        generate(writer, Checker(notes=verified))
    assert writer.calls == []


def test_a_model_error_is_retried_and_does_not_use_a_repair_or_regeneration():
    class Flaky(Checker):
        failed = False

        async def __call__(self, system, user):
            if not self.failed and not system.startswith("You turn ONE") and not system.startswith(csr.METADATA_SYSTEM[:30]):
                self.failed = True
                raise RuntimeError("the model was down")
            return await super().__call__(system, user)
    stored = []
    gen, writer, _ = generate(checker=Flaky(), on_rejection=stored.extend)
    assert writer.repairs == [] and gen.naming_result.passed
    assert len([x for x in writer.calls if not x[0].startswith(csr.REPAIR_SYSTEM)]) == len(PLAN)
    assert any(r["check"] == "transient_error" and r["stage"] == "naming_check" for r in stored)


def test_without_metadata_the_run_still_returns_a_script_and_a_fallback_title():
    gen, _, checker = generate(with_metadata=False)
    assert gen.content["title"] == "t" and gen.content["description"].startswith("This episode looks at t.")
    assert not any(s.startswith(csr.METADATA_SYSTEM[:30]) for s, _ in checker.calls)


def test_the_writer_call_has_temperature_and_room_and_uses_the_check_request_shape():
    seen = {}

    class R:
        status_code = 200

        @staticmethod
        def json():
            return {"candidates": [{"finishReason": "STOP", "content": {"parts": [{"text": "{\"dialogue\": \"HOST: Hi.\"}"}]}}]}

    def post(url, headers, json, timeout):
        seen.update(url=url, body=json, headers=headers)
        return R()
    call = cp.make_writer_llm("k", post=post)
    assert run(call("sys", "user")) == "{\"dialogue\": \"HOST: Hi.\"}"
    gc = seen["body"]["generationConfig"]
    assert gc["temperature"] == cp.WRITER_TEMPERATURE and gc["maxOutputTokens"] == cp.WRITER_MAX_OUTPUT_TOKENS and gc["responseMimeType"] == "application/json"
    assert seen["headers"]["x-goog-api-key"] == "k" and "gemini" in seen["url"]


def test_a_model_error_in_the_section_writer_or_the_notes_step_is_repeated_not_fatal():
    class FlakyWriter(Writer):
        n = 0

        async def __call__(self, system, user):
            FlakyWriter.n += 1
            if FlakyWriter.n in (2, 4):
                raise RuntimeError("HTTP 503")
            return await super().__call__(system, user)

    class FlakyNotes(Checker):
        n = 0

        async def __call__(self, system, user):
            if system.startswith("You turn ONE pasted") and FlakyNotes.n == 0:
                FlakyNotes.n += 1
                raise RuntimeError("HTTP 429")
            return await super().__call__(system, user)
    stored = []
    gen, writer, _ = generate(FlakyWriter(), FlakyNotes(), on_rejection=stored.extend)
    assert gen.naming_result.passed and [r["stage"] for r in stored if r["check"] == "transient_error"] == ["notes", "section_writer", "section_writer"]


def test_notes_that_are_not_json_are_asked_for_again_and_a_pipeline_error_is_never_retried_as_a_model_error():
    class Garbled(Checker):
        n = 0

        async def __call__(self, system, user):
            if system.startswith("You turn ONE pasted") and Garbled.n == 0:
                Garbled.n += 1
                return "not json at all"
            return await super().__call__(system, user)
    gen, _, _ = generate(checker=Garbled())
    assert [t["violations"] for t in gen.trace if t["stage"] == "notes"] == [["notes_not_json"], []]
    stored = []
    with pytest.raises(csr.NotesError):
        generate(checker=Checker(notes=[{"claim": "Too short."}]), on_rejection=stored.extend)
    assert not any(r["check"] == "transient_error" for r in stored)
