"""Dry-run tests for the gap 3 fix 1 sandbox harness. The harness runs in --stub mode in a subprocess (it patches
module globals), with scripted fakes: no network, no keys, no models, no spend."""
import json
import os
import subprocess
import sys

import pytest

BACKEND = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
HARNESS = os.path.join(BACKEND, "scripts", "fix1_sandbox.py")

SCENARIOS = ["ok", "bad_then_good", "never_good", "thin", "registry_down", "paper_request", "long_body"]


def spec(scenario):
    s = {"id": scenario, "scenario": scenario, "topic": f"Topic for {scenario}", "category": "Computer Science", "duration": "5-10 minutes",
         "expertise_level": "expert", "format_type": "interview", "additional_instructions": "", "source_links": []}
    if scenario == "paper_request":
        s.update(paper_title="Requested sandbox paper title", paper_doi="10.1234/requested.1", paper_journal="Wrong Journal")
    return s


@pytest.fixture(scope="module")
def run_dir(tmp_path_factory):
    d = tmp_path_factory.mktemp("sandbox")
    topics = d / "topics.json"
    topics.write_text(json.dumps([spec(s) for s in SCENARIOS]))
    out, ledger = d / "out", d / "ledger.jsonl"
    p = subprocess.run([sys.executable, HARNESS, "--topics", str(topics), "--out", str(out), "--ledger", str(ledger), "--stub"],
                       cwd=BACKEND, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=300)
    assert p.returncode == 0, p.stdout[-2000:] + p.stderr[-2000:]
    return d, out, ledger, p


def result(out, name):
    return json.load(open(out / name / "result.json", encoding="utf-8"))


def test_every_topic_ends_with_a_recorded_outcome_and_nothing_is_spent(run_dir):
    d, out, ledger, p = run_dir
    summary = json.load(open(out / "summary.json"))
    assert [r["id"] for r in summary["results"]] == SCENARIOS and summary["stub"] is True and summary["spent"] == 0.0
    assert not ledger.exists() or ledger.read_text().strip() == ""


def test_ok_topic_builds_references_and_further_reading_by_code(run_dir):
    d, out, ledger, p = run_dir
    r = result(out, "ok")
    assert r["outcome"] == "generated" and r["research"]["confirmed"] == 3 and r["regenerations"] == 0 and r["pre_publish_gate"] == "ok"
    final = (out / "ok" / "description_final.md").read_text(encoding="utf-8")
    assert "Model Wrote This" not in final and "MODEL-WRITTEN CITATION" not in final
    assert final.index("## References") < final.index("## Further reading") < final.index("## Hashtags")
    assert r["named_pids"] == ["P1", "P2"] and r["reference_lines"] == 2 and r["further_reading_lines"] == 1
    assert "Sandbox paper number 3" in final.split("## Further reading")[1]
    assert (out / "ok" / "script.txt").exists() and (out / "ok" / "description_raw.md").exists()


def test_a_bad_first_script_is_regenerated_and_the_attempts_are_recorded(run_dir):
    d, out, ledger, p = run_dir
    r = result(out, "bad_then_good")
    assert r["outcome"] == "generated" and r["regenerations"] == 1
    assert [a["passed"] for a in r["naming_attempts"]] == [False, True]
    assert r["naming_attempts"][0]["violations"][0]["authors"] == ["Zorblatt", "Quux"]


def test_a_script_that_never_passes_fails_the_episode_and_writes_no_content(run_dir):
    d, out, ledger, p = run_dir
    r = result(out, "never_good")
    assert r["outcome"] == "failed_naming" and "no episode was published" in r["message"] and len(r["naming_attempts"]) == 3
    assert not (out / "never_good" / "script.txt").exists() and not (out / "never_good" / "description_final.md").exists()


def test_a_thin_topic_fails_early_with_the_clear_message(run_dir):
    d, out, ledger, p = run_dir
    r = result(out, "thin")
    assert r["outcome"] == "failed_research" and r["kind"] == "InsufficientConfirmedPapers"
    assert "Not enough confirmed research papers" in r["message"] and "at least 3" in r["message"]
    assert r["research"]["candidates_found"] == 2 and r["research"]["confirmed"] == 2


def test_an_unreachable_registry_is_not_reported_as_a_thin_topic(run_dir):
    d, out, ledger, p = run_dir
    r = result(out, "registry_down")
    assert r["outcome"] == "failed_research" and r["kind"] == "RegistryUnavailable" and "Not enough" not in r["message"]


def test_requested_paper_is_p1_and_listed_first_with_registry_fields(run_dir):
    d, out, ledger, p = run_dir
    r = result(out, "paper_request")
    assert r["outcome"] == "generated" and r["research"]["confirmed"] == 4
    final = (out / "paper_request" / "description_final.md").read_text(encoding="utf-8")
    refs = final.split("## References")[1].split("## Further reading")[0]
    assert refs.index("Requested sandbox paper title") < refs.index("Sandbox paper number 1")
    assert "Journal of Sandbox" in refs and "Wrong Journal" not in final


def test_the_length_limit_removal_is_measured_per_topic(run_dir):
    d, out, ledger, p = run_dir
    ok, long = result(out, "ok")["limit"], result(out, "long_body")["limit"]
    assert ok["body_chars_removed_by_limit"] == 0
    assert long["body_chars_removed_by_limit"] > 0 and long["description_chars_after_limit"] <= 4100
    assert long["body_chars_before_limit"] > long["body_chars_after_limit"]
    final = (out / "long_body" / "description_final.md").read_text(encoding="utf-8")
    assert "## References" in final and "## Further reading" in final  # the lists survive the trim


def test_a_second_run_skips_finished_topics(run_dir):
    d, out, ledger, p = run_dir
    again = subprocess.run([sys.executable, HARNESS, "--topics", str(d / "topics.json"), "--out", str(out), "--ledger", str(ledger), "--stub"],
                           cwd=BACKEND, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=300)
    assert again.returncode == 0 and again.stdout.count("already done, skipped") == len(SCENARIOS)


def test_no_write_path_is_imported_by_the_harness():
    src = open(HARNESS, encoding="utf-8").read()
    for forbidden in ("upsert_episode_document", "storage.Client", "elevenlabs", "send_podcast", "update_rss_feed", ".collection("):
        assert forbidden not in src


# ---------------------------------------------------------------- the spend ceiling
def _harness_module():
    sys.path.insert(0, os.path.join(BACKEND, "scripts"))
    import importlib
    return importlib.import_module("fix1_sandbox")


def test_ledger_prices_guards_and_records(tmp_path):
    h = _harness_module()
    led = h.Ledger(str(tmp_path / "l.jsonl"), ceiling=0.01)
    assert led.price("models/gemini-2.5-flash") == (0.30, 2.50) and led.price("something-new") == (1.25, 10.00)
    led.guard("gemini-2.5-flash", 1000, 1000)  # about $0.0028: allowed
    led.record("gemini-2.5-flash", 1000, 2000, "t")
    assert abs(led.spent() - (1000 * 0.30 + 2000 * 2.50) / 1e6) < 1e-9
    with pytest.raises(h.CeilingReached):
        led.guard("gemini-2.5-pro", 1000, 4000)  # about $0.04: over the ceiling


def test_metering_wraps_the_sdk_call_and_stops_at_the_ceiling(tmp_path, monkeypatch):
    h = _harness_module()
    import google.generativeai as genai
    import enhanced_research_service as ers

    class _Usage:
        prompt_token_count, candidates_token_count, thoughts_token_count = 100, 50, 25

    class _Resp:
        usage_metadata = _Usage()
        text = "ok"
    monkeypatch.setattr(genai.GenerativeModel, "generate_content", lambda self, contents, *a, **k: _Resp())
    monkeypatch.setattr(ers.EnhancedResearchService, "_call_google_ai", ers.EnhancedResearchService._call_google_ai)
    led = h.Ledger(str(tmp_path / "l.jsonl"), ceiling=0.05)
    h.install_metering(led, {"tag": "t1"})
    m = genai.GenerativeModel("gemini-2.5-flash")
    assert m.generate_content("hello").text == "ok"
    assert abs(led.spent() - (100 * 0.30 + 75 * 2.50) / 1e6) < 1e-9
    with pytest.raises(h.CeilingReached):
        m.generate_content("x" * 600000, generation_config=genai.types.GenerationConfig(max_output_tokens=20000))
