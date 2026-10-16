"""Attribution check (fix 4, stage b): offline. The model's replies are faked; one fixture is the reply the real model gave on the
ever-math-260008 script (live run 2026-10-13), where the mathlib 'explicitly highlights this shift' sentence must fail."""
import asyncio
import json
from types import SimpleNamespace as NS

import pytest

import attribution_check as ac


def run(coro):
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


MATHLIB = NS(pid="P1", title="The Lean mathematical library", authors=["The mathlib Community"], year=2019,
             abstract="This paper describes mathlib, a community-driven effort to build a unified library of mathematics formalized in the Lean proof assistant.")
ALAMA = NS(pid="P2", title="mizar-items", authors=["Jesse Alama"], year=2011,
           abstract="We describe mizar-items, a system for decomposing the Mizar Mathematical Library into fine-grained items and computing their dependencies.")
NO_ABSTRACT = NS(pid="P3", title="T", authors=["A B"], year=2020, abstract="")

EP8_SENTENCES = [
    "According to The mathlib Community in their 2019 paper, 'The Lean mathematical library'—link in the description—mathlib is a community-driven project to build a unified library of mathematics formalized in the Lean proof assistant.",
    "That paper by The mathlib Community in 2019 explicitly highlights this shift.",
    "It fundamentally challenges the millennia-old paradigm of human-centric mathematical verification.",
]
EP8_SCRIPT = "ADAM: Thanks, Matilda. " + EP8_SENTENCES[0] + " This is not just about digitizing.\n\nMATILDA: Really?\n\nADAM: Precisely. " + " ".join(EP8_SENTENCES[1:])


def llm_returning(items, seen=None):
    async def call(system, user):
        if seen is not None:
            seen.append(user)
        return json.dumps({"attributions": items})
    return call


def item(quote, pid="P1", verdict="unsupported", reason="The abstract does not say this."):
    return {"quote": quote, "pid": pid, "verdict": verdict, "reason": reason}


def test_the_ep8_mathlib_sentence_fails_and_the_supported_one_passes():
    reply = [item(EP8_SENTENCES[0], verdict="supported", reason="The abstract says this."),
             item(EP8_SENTENCES[1], reason="The abstract does not mention highlighting a shift."),
             item(EP8_SENTENCES[2], reason="The abstract does not claim this.")]
    res = run(ac.check_attributions(EP8_SCRIPT, [MATHLIB], llm_returning(reply)))
    assert not res.passed and [v["quote"] for v in res.violations] == EP8_SENTENCES[1:]
    assert len(res.checked) == 3 and res.violations[0]["label"] == "The mathlib Community (2019)" or res.violations[0]["label"].endswith("(2019)")
    fb = ac.attribution_feedback(res)
    assert "explicitly highlights this shift" in fb and "REJECTED" in fb and "(2019)" in fb and "Attribute to a paper only what its abstract states" in fb


def test_a_fully_supported_script_passes():
    res = run(ac.check_attributions(EP8_SCRIPT, [MATHLIB], llm_returning([item(EP8_SENTENCES[0], verdict="supported")])))
    assert res.passed and len(res.checked) == 1 and res.summary()["unsupported"] == 0


def test_the_model_gets_the_abstracts_of_the_named_papers_only_and_the_script():
    seen = []
    run(ac.check_attributions("Alama showed it works fine here.", [ALAMA, NO_ABSTRACT], llm_returning([], seen)))
    prompt = seen[0]
    assert "[P2]" in prompt and "decomposing the Mizar Mathematical Library" in prompt and "[P3]" not in prompt and "Alama showed it works fine here." in prompt


def test_nothing_to_check_makes_no_model_call():
    called = []

    async def llm(system, user):
        called.append(1)
        return "{}"
    assert run(ac.check_attributions("script", [NO_ABSTRACT], llm)).skipped_reason
    assert run(ac.check_attributions("", [MATHLIB], llm)).skipped_reason and not called


def test_the_code_not_the_model_decides_what_counts():
    reply = [item("A sentence the model invented that is not in the script at all.", reason="x"),     # not in the script
             item(EP8_SENTENCES[1], pid="P9"),                                                         # a paper it was not given
             item(EP8_SENTENCES[1], verdict="maybe"),                                                  # not a verdict
             "not a dict", item("short", pid="P1")]
    res = run(ac.check_attributions(EP8_SCRIPT, [MATHLIB], llm_returning(reply)))
    assert res.checked == [] and res.passed


def test_quotes_match_across_whitespace_and_case():
    script = "ADAM: That paper\nexplicitly   highlights this SHIFT, he said."
    res = run(ac.check_attributions(script, [MATHLIB], llm_returning([item("That paper explicitly highlights this shift")])))
    assert len(res.violations) == 1


def test_fails_closed_when_the_model_errors_or_answers_garbage():
    async def boom(system, user):
        raise RuntimeError("quota")

    async def garbage(system, user):
        return "I could not do that."

    async def wrong_shape(system, user):
        return json.dumps({"mentions": []})
    for llm in (boom, garbage, wrong_shape):
        with pytest.raises(ac.AttributionCheckUnavailable):
            run(ac.check_attributions(EP8_SCRIPT, [MATHLIB], llm))


def test_a_fenced_reply_is_read():
    async def fenced(system, user):
        return "```json\n" + json.dumps({"attributions": [item(EP8_SENTENCES[1])]}) + "\n```"
    assert len(run(ac.check_attributions(EP8_SCRIPT, [MATHLIB], fenced)).violations) == 1


def test_error_message_quotes_the_sentences():
    res = run(ac.check_attributions(EP8_SCRIPT, [MATHLIB], llm_returning([item(EP8_SENTENCES[1])])))
    e = ac.AttributionError(res.violations)
    assert "explicitly highlights this shift" in str(e) and "no episode was published" in str(e)


def test_records_carry_the_paper_and_its_abstract_and_the_whole_sentence():
    long_quote = ("That paper by The mathlib Community in 2019 explicitly highlights this shift " + "and then goes on at length " * 8).strip()
    script = "ADAM: " + long_quote + "."
    res = run(ac.check_attributions(script, [MATHLIB], llm_returning([item(long_quote)])))
    v = res.violations[0]
    assert v["quote"] == long_quote and len(long_quote) > 160                      # not cut to 160 characters
    assert v["title"] == "The Lean mathematical library" and v["authors"] == ["The mathlib Community"] and v["year"] == 2019
    assert v["abstract"] == MATHLIB.abstract and v["pid"] == "P1" and v["reason"]
    assert res.summary()["unsupported_quotes"] == [long_quote]
