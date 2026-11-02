"""check_supplied_script (curated_pipeline.py): a script an editor wrote is put through every check a generated curated script passes, nothing is
repaired, nothing is written, and no section writer is ever called. Offline: the model calls are scripted fakes; the checks are the real ones."""
import json
from types import SimpleNamespace as NS

import attribution_check as ac
import curated_pipeline as cp
import curated_script as csr
from models.podcast import PodcastRequest
from tests.unit.test_curated_dryrun_fixes import MentionChecker
from tests.unit.test_curated_pipeline import NOTES, REQUEST, SECRET, Checker, Writer, context, generate, run


def clean_script():
    gen, _, _ = generate()
    return gen.content["script"]


def check(script, checker=None, request=REQUEST, ctx=None, **kw):
    checker = checker or Checker()

    async def no_sleep(_):
        return None
    result = run(cp.check_supplied_script(request, ctx or context(), checker, script, title="A title", sleep=no_sleep, **kw))
    return result, checker


def kinds(result):
    return {f"{v['check']}:{v['kind']}" for v in result.violations}


def with_line(script, line):
    lines = script.split("\n")
    lines[-1] = line
    return "\n".join(lines)


def test_a_clean_script_passes_every_check_and_no_writer_is_involved():
    script = clean_script()
    result, checker = check(script)
    assert result.passed and result.violations == [] and result.length_ok and result.format_problems == [] and result.content is None
    assert result.words == len(script.split()) and result.entry["words"] == result.words and result.entry["curated_checks"] == {}
    assert result.model_calls["checks"] >= 1 and not any(c[0].startswith(csr.REPAIR_SYSTEM) for c in checker.calls)


def test_with_metadata_a_clean_script_also_gets_its_description_and_the_given_title():
    script = clean_script()
    result, _ = check(script, with_metadata=True)
    assert result.passed and result.content["title"] == "A title" and result.content["script"] == script
    assert result.content["description"].startswith("A plain summary") and result.content["keywords"] == ["maths"] and result.model_calls["metadata"] == 1


def test_a_script_that_fails_is_reported_not_repaired_and_gets_no_metadata():
    script = with_line(clean_script(), "EXPERT: The Exponential Time Hypothesis is False was formally verified in Lean.")
    result, checker = check(script, with_metadata=True)
    assert not result.passed and result.content is None and "status_wording:forbidden_term" in kinds(result) and result.model_calls["metadata"] == 0
    assert not any(c[0].startswith(csr.METADATA_SYSTEM[:30]) for c in checker.calls)


# --- one failing script for each check family ---------------------------------------------------------------------------------------------------
def test_status_wording_family():
    result, _ = check(with_line(clean_script(), "EXPERT: The Exponential Time Hypothesis is False was formally verified in Lean."))
    assert "status_wording:forbidden_term" in kinds(result)


def test_verbatim_run_family():
    result, _ = check(with_line(clean_script(), "EXPERT: As it was put, " + SECRET + " is the mood."))
    assert "verbatim_run:verbatim_run" in kinds(result)


def test_spoken_name_family():
    result, _ = check(with_line(clean_script(), "EXPERT: Hello, I'm Matilda."))
    assert "spoken_name:spoken_name" in kinds(result)


def test_naming_family_an_unlisted_work_with_a_year_is_not_exempt():
    line = "EXPERT: Pat Quimby said in 2021 that the proofs matter."
    mention = {"quote": line, "authors": ["Quimby"], "year": 2021, "title_words": [], "kind": "work"}
    checker = MentionChecker("Pat Quimby", mention, notes=NOTES)
    result, _ = check(with_line(clean_script(), line), checker)
    assert any(v["check"] == "naming" for v in result.violations) and result.entry["passed"] is False


def test_a_name_only_in_the_pasted_text_counts_as_recorded_but_only_for_a_pure_reporting_attribution():
    ctx = context()
    ctx.curated.items[-1]["evidence_text"] = "The reporter wrote that Pat Quimby said the proofs matter. " + SECRET
    text = cp.supplied_reporting_text(ctx.curated)
    assert "quimby" in text.split()
    line = "EXPERT: Pat Quimby said the proofs matter."
    mention = {"quote": line, "authors": ["Quimby"], "year": None, "title_words": [], "kind": "work"}
    ok, _ = check(with_line(clean_script(), line), MentionChecker("Pat Quimby", mention, notes=NOTES), ctx=ctx)
    assert ok.passed and ok.entry["naming_reporting_attributions_exempt"] == 1
    line2 = "EXPERT: Pat Quimby said in 2021 that the proofs matter."
    bad, _ = check(with_line(clean_script(), line2), MentionChecker("Pat Quimby", {**mention, "quote": line2, "year": 2021}, notes=NOTES), ctx=ctx)
    assert not bad.passed


def test_attribution_family(monkeypatch):
    script = clean_script()
    async def unsupported(script, named, llm):
        res = ac.AttributionResult()
        res.checked = [{"quote": "OpenAI proved it", "pid": "P1", "verdict": "unsupported", "reason": "not in the abstract"}]
        res.violations = list(res.checked)
        return res
    monkeypatch.setattr(cp, "check_attributions", unsupported)
    result, _ = check(script)
    assert "attribution:unsupported_attribution" in kinds(result) or any(v["check"] == "attribution" for v in result.violations)


def test_notation_family():
    result, _ = check(with_line(clean_script(), "EXPERT: The bound is \\foobar here."))
    assert "notation:unspeakable_notation" in kinds(result) or any(v["kind"] == "unspeakable_notation" for v in result.violations)


def test_banned_wording_family():
    result, _ = check(with_line(clean_script(), "EXPERT: This is a groundbreaking result."))
    assert any(v["check"] == "banned_wording" for v in result.violations)


def test_topic_read_aloud_family():
    request = PodcastRequest(topic="Seven hundred papers released overnight by one company", duration="1-2 minutes", expertise_level="general")
    ctx = context()
    result, _ = check(with_line(clean_script(), "HOST: Seven hundred papers released overnight by one company."), request=request, ctx=ctx)
    assert any(v["check"] == "read_aloud" for v in result.violations)


def test_length_family_too_short_and_too_long():
    short, _ = check("HOST: Hello there.\nEXPERT: Hi.")
    assert "length:too_short" in kinds(short) and not short.length_ok
    long_, _ = check(clean_script() + "\n" + "HOST: " + " ".join(["word"] * 400) + ".")
    assert "length:too_long" in kinds(long_)


def test_format_family_a_line_without_a_speaker_fails():
    result, _ = check(clean_script() + "\nA line with no speaker.")
    assert "format:line_format" in kinds(result) and result.format_problems


def test_the_supplied_check_runs_the_same_families_as_the_generated_checker():
    """Every key the generated checker records in its per-check entry is recorded here too."""
    gen, _, _ = generate()
    result, _ = check(gen.content["script"])
    assert set(gen.naming_attempts[0]) <= set(result.entry)
