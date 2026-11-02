"""Curated attribution BY TARGET (curated_attribution.py): each attributed sentence is routed by code to the thing it credits and tested against that
thing. Offline: the model is a scripted fake; the routing and the status check are the real code."""
import asyncio
import json

import pytest

import attribution_check as ac
import curated_attribution as ca
import curated_mode as cm
import curated_script as csr
import curated_sources as cs
from tests.unit.test_curated_mode import PRIVATE, PIN, approved_doc, commentary_item, release_item

QUANTA_TEXT = ("Maksym Radziwill said the vast majority of consequences of the Riemann hypothesis already follow from the quasi version. "
               "These experts largely agree that the result is correct. Peter Sarnak said he would not call it a theorem until humans check every detail.")
SCIAM_TEXT = ("One result proves the quasi-Riemann hypothesis, which is a huge step toward the holy grail of proving the full thing. "
              "Hector Pasten said the quasi version is way more than enough for many applications. The second result shows there is no Siegel zero.")
Q_TITLE = "The Quasi-Riemann Hypothesis: A Zero-Free Half-Plane $`\\Re s\\gt 7/8`$"
LEAN = {"in_lean_catalogue": True, "withdrawal_notice": False}


def make_run():
    items = [
        release_item(title=Q_TITLE, path="preprints/Q78", family="101", status="has_lean_formalization", status_basis=dict(LEAN),
                     evidence_text="We prove that Dirichlet L-functions are zero-free in the half-plane real part of s greater than 7/8."),
        release_item(title="The Quasi-Riemann Hypothesis (alternate 11/12 proof)", path="preprints/Q1112", family="102", status="checked_by_experts",
                     status_basis={"in_lean_catalogue": False, "withdrawal_notice": False}, evidence_text="We establish the quasi-Riemann hypothesis for 11/12."),
        release_item(title="The Exponential Time Hypothesis is False", path="preprints/ETH", family="103", status="has_lean_formalization",
                     status_basis=dict(LEAN), evidence_text="We give a deterministic algorithm for counting satisfying assignments of a k-CNF formula."),
        release_item(title="Algebraicity of Weil classes on split abelian eightfolds", path="preprints/Weil", family="104", status="withdrawn",
                     status_basis={"withdrawal_notice": True, "withdrawal": {"explanation": "The proof contains a sign error in the stabilization-trace argument.",
                                                                            "withdrawn_on": "October 6, 2026"}}, evidence_text="Withdrawn."),
        commentary_item(identifiers={"url": "https://example.org/quanta"}, evidence_text=QUANTA_TEXT, venue="Quanta Magazine", authors=["Konstantin Kakaes"]),
        commentary_item(identifiers={"url": "https://example.org/sciam"}, evidence_text=SCIAM_TEXT, venue="Scientific American", authors=["Peter Hall"]),
    ]
    return cm.CuratedRun.from_list_doc(approved_doc(items), private_texts=PRIVATE)


def run_(coro):
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


class Judge:
    """The model: judges each numbered sentence by a substring table (default supported) and counts its calls; answers the abstract check with `abstracts`."""

    def __init__(self, table=None, abstracts=None):
        self.table, self.abstracts, self.calls = table or {}, abstracts or [], []

    async def __call__(self, system, user):
        self.calls.append((system, user))
        if system.startswith(ca.SYSTEM[:30]):
            out = []
            for line in user.split("SENTENCES:", 1)[1].strip().split("\n"):
                n, sentence = line.split(". ", 1)
                v = next((val for key, val in self.table.items() if key in sentence), {})
                out.append({"n": int(n), "verdict": v.get("verdict", "supported"), "credited_person": v.get("person"),
                            "person_words_belong_to_someone_else": v.get("else", False), "reason": v.get("reason", "ok")})
            return json.dumps({"verdicts": out})
        return json.dumps({"attributions": self.abstracts})


def check(script, judge=None, run=None):
    run = run or make_run()
    judge = judge or Judge()
    named = run.confirmed_papers()
    return run_(ca.check_curated_attributions(script, run, named, judge)), judge


def routes(result):
    return {r.sentence: r for r in result.routing}


# --- routing -----------------------------------------------------------------------------------------------------------------------------------------
def test_each_sentence_is_routed_to_the_thing_it_credits():
    script = ("EXPERT: Quanta reports that experts largely agree the result is correct. "
              "Maksym Radziwill said the consequences follow from the quasi version. "
              "OpenAI's catalogue lists a Lean formalization for the seven-eighths paper and the ETH paper. "
              "OpenAI's paper titled \"The Exponential Time Hypothesis is False\" describes an algorithm for counting satisfying assignments. "
              "The Guardian reported that the release was a stunt.")
    result, judge = check(script)
    r = routes(result)
    by = {s[:12]: x for s, x in r.items()}
    assert by["Quanta repor"].route == "commentary" and by["Quanta repor"].sources == ["Quanta"]
    assert by["Maksym Radzi"].route == "commentary"                                  # a person who appears in a listed text: that text
    assert by["OpenAI's cat"].route == "status" and by["OpenAI's cat"].passed
    assert by["OpenAI's pap"].route == "content"
    assert by["The Guardian"].route == "unlisted_source" and not by["The Guardian"].passed
    assert [v["route"] for v in result.violations] == ["unlisted_source"]


def test_a_person_named_in_a_text_is_checked_against_that_text_and_an_outlet_named_wins():
    result, judge = check("EXPERT: Hector Pasten said the quasi version is more than enough for many applications.")
    only = result.routing[0]
    assert only.route == "commentary" and only.sources == ["Scientific American"]
    user = judge.calls[0][1]
    assert "Hector Pasten said the quasi version is way more than enough" in user and "Maksym Radziwill said" not in user     # only the text that names him


# --- the commentary route, and the model's verdicts -----------------------------------------------------------------------------------------------
def test_a_correct_commentary_attribution_passes_and_keeps_its_excerpt_privately():
    result, judge = check("EXPERT: Quanta reports that experts largely agree the result is correct.")
    r = result.routing[0]
    assert r.passed and r.verdict == "supported" and "largely agree" in r.excerpt and len(r.excerpt.split()) <= ca.EXCERPT_WORDS
    rec = result.checked[0]
    assert r.excerpt not in json.dumps(rec) and rec["reason"] == "the source text supports it"          # the log-bound record carries no source text
    assert result.detail()[0]["excerpt"] == r.excerpt                                                       # the administrator's detail does
    assert result.summary()["by_target"] is True and result.passed


def test_a_reporters_phrase_credited_to_an_expert_fails_the_pasten_case():
    sentence = "EXPERT: Scientific American reported that Hector Pasten called the proof a huge step toward the holy grail."
    judge = Judge({"huge step": {"verdict": "partly", "person": "Hector Pasten", "else": True, "reason": "the phrase is the reporters' own"}})
    result, _ = check(sentence, judge)
    r = result.routing[0]
    assert not r.passed and r.person_misattributed and not result.passed
    assert result.violations[0]["route"] == "commentary" and "the source text gives to someone else" in result.violations[0]["reason"]
    assert "reporters" not in json.dumps(result.checked)                                                      # the model's reason stays private
    assert "reporters' own" in result.detail()[0]["model_reason"]


def test_partly_fails_only_when_a_person_is_credited_with_someone_elses_words():
    judge = Judge({"largely agree": {"verdict": "partly", "person": None, "else": False}})
    ok, _ = check("EXPERT: Quanta reports that experts largely agree the result is correct.", judge)
    assert ok.passed and ok.routing[0].verdict == "partly"
    judge = Judge({"largely agree": {"verdict": "partly", "person": "Peter Sarnak", "else": True}})
    bad, _ = check("EXPERT: Quanta reports that Peter Sarnak says experts largely agree the result is correct.", judge)
    assert not bad.passed
    judge = Judge({"largely agree": {"verdict": "partly", "person": "Peter Sarnak", "else": False}})
    fine, _ = check("EXPERT: Quanta reports that Peter Sarnak says experts largely agree the result is correct.", judge)
    assert fine.passed


def test_an_unsupported_commentary_sentence_fails_and_a_wrong_source_is_unsupported():
    judge = Judge({"experts checked": {"verdict": "unsupported", "reason": "that is in another source"}})
    result, _ = check("EXPERT: Scientific American reported that experts checked it.", judge)
    assert not result.passed and result.violations[0]["label"] == "Scientific American" and result.violations[0]["verdict"] == "unsupported"


def test_a_model_answer_that_misses_a_sentence_or_is_unreadable_fails_closed():
    async def short(system, user):
        return json.dumps({"verdicts": []})
    with pytest.raises(ac.AttributionCheckUnavailable):
        run_(ca.check_curated_attributions("EXPERT: Quanta reports that experts largely agree.", make_run(), [], short))

    async def junk(system, user):
        return "not json"
    with pytest.raises(ac.AttributionCheckUnavailable):
        run_(ca.check_curated_attributions("EXPERT: Quanta reports that experts largely agree.", make_run(), [], junk))


# --- the status route: deterministic, no model call ----------------------------------------------------------------------------------------------
def status(sentence):
    result, judge = check("EXPERT: " + sentence)
    return result.routing[0], judge


def test_catalogue_statements_that_agree_with_the_records_pass_without_a_model_call():
    for s in ("OpenAI's catalogue lists a Lean formalization for the seven-eighths paper, the ETH paper and the Unique Games paper.".replace(" and the Unique Games paper", ""),
              "But the catalogue's own review status for each of those entries is unchecked.",
              "The catalogue's own review status for the ETH paper is unchecked.",
              "OpenAI's own notice says the proof in the withdrawn paper contains a sign error.",
              "OpenAI's notice says the withdrawn paper was withdrawn on October sixth."):
        r, judge = status(s)
        assert r.route == "status" and r.passed, (s, r.reason)
        assert judge.calls == []


def test_catalogue_statements_that_disagree_with_the_records_fail():
    cases = [("OpenAI's catalogue lists a Lean formalization for the eleven-twelfths paper.", "does not list a Lean formalization"),
             ("The catalogue's own review status for the eleven-twelfths paper is unchecked.", "not 'has a Lean formalization, unchecked'"),
             ("OpenAI's notice says the proof in the withdrawn paper contains a wrong sign mistake.", "does not mention a mistake"),
             ("OpenAI's notice says the withdrawn paper was withdrawn on October twelfth.", "date given is not the one"),
             ("OpenAI's catalogue lists a Lean formalization for the paper.", "names no listed paper"),
             ("OpenAI's catalogue says the ETH paper was formally verified.", "verifying or confirming"),
             ("OpenAI's notice says the ETH paper was withdrawn.", "do not say that the paper named was withdrawn"),
             ("The catalogue has many entries.", "cannot confirm")]
    for s, why in cases:
        r, judge = status(s)
        assert r.route == "status" and not r.passed and why in r.reason, (s, r.reason)
        assert judge.calls == []


# --- an unlisted source --------------------------------------------------------------------------------------------------------------------------------
def test_a_source_that_is_not_on_the_list_fails_and_every_listed_outlet_does_not():
    result, _ = check("EXPERT: The New Yorker reported that the release was a stunt.")
    assert not result.passed and result.violations[0]["route"] == "unlisted_source" and "New Yorker" in result.violations[0]["label"]
    ok, _ = check("EXPERT: Quanta reports that the result is correct. Scientific American said so too. Nature reported nothing here.")
    assert [r.route for r in ok.routing][:2] == ["commentary", "commentary"]


# --- content claims about a paper: the abstract, by the existing check, on the sentences that were not routed elsewhere -------------------------------
def test_a_content_claim_is_checked_against_the_abstract_and_routed_sentences_are_not_sent_to_that_check():
    script = ("EXPERT: Quanta reports that experts largely agree the result is correct. "
              "OpenAI's catalogue lists a Lean formalization for the ETH paper. "
              "OpenAI's paper titled \"The Exponential Time Hypothesis is False\" describes an algorithm for counting satisfying assignments.")
    bad = [{"quote": "OpenAI's paper titled \"The Exponential Time Hypothesis is False\" describes an algorithm for counting satisfying assignments.",
            "pid": "P3", "verdict": "unsupported", "reason": "invented"}]
    result, judge = check(script, Judge(abstracts=bad))
    abstract_call = next(u for s, u in judge.calls if not s.startswith(ca.SYSTEM[:30]))
    assert "Quanta reports" not in abstract_call.split("SCRIPT:", 1)[1] and "catalogue" not in abstract_call.split("SCRIPT:", 1)[1]
    assert not result.passed and result.violations[0]["route"] == "content" and result.violations[0]["pid"] == "P3"


def test_the_ordinary_mode_is_unchanged():
    judge = Judge()
    got = run_(ca.check_attributions_for("EXPERT: Quanta reports that experts largely agree.", [], judge, curated_run=None))
    assert isinstance(got, ac.AttributionResult) and not hasattr(got, "routing") and judge.calls == []
    result = run_(ca.check_attributions_for("EXPERT: Quanta reports it.", [], judge, curated_run=make_run()))
    assert hasattr(result, "routing")


# --- how a failure reads to the repair --------------------------------------------------------------------------------------------------------------
def test_the_violation_message_names_the_source_it_was_tested_against_not_the_abstract():
    judge = Judge({"experts checked": {"verdict": "unsupported"}})
    result, _ = check("EXPERT: Scientific American reported that experts checked it.", judge)
    out = csr.collect_violations(attribution=result)
    assert "the text of that source does not support it as credited" in out[0]["message"] and "abstract" not in out[0]["message"]
    status_result, _ = check("EXPERT: OpenAI's catalogue lists a Lean formalization for the eleven-twelfths paper.")
    assert "status records do not agree" in csr.collect_violations(attribution=status_result)[0]["message"]
