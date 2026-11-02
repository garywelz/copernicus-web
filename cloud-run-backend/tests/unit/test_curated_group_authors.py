"""A commentary item credited through its group author or its description ("Fields medalists signed a statement", "the declaration") routes to that item's
private text, is attribution-checked and is listed in the References. The aliases are recorded on the list item (they are not part of the list hash)."""
import curated_attribution as ca
import curated_mode as cm
import curated_sources as cs
from tests.unit.test_curated_attribution import Judge, check, make_run, run_
from tests.unit.test_curated_mode import PRIVATE, approved_doc, commentary_item, release_item

DECL_TEXT = ("A Severe Misalignment of AI in Mathematics. Twenty-five Fields medalists signed this statement. It argues that AI companies and the "
             "mathematical community are pursuing badly misaligned goals, and that solving problems is only a tool for reaching conceptual understanding.")
SENTENCE = "Weeks before the release, twenty-five Fields medalists signed a statement arguing that AI companies and the mathematical community are pursuing badly misaligned goals."
ALIASES = ["Fields medalists", "declaration"]


def declaration_item(aliases=ALIASES):
    extra = {"aliases": list(aliases)} if aliases is not None else {}
    return commentary_item(identifiers={"url": "https://zenodo.org/records/1"}, evidence_text=DECL_TEXT, venue="Zenodo", title="A Severe Misalignment of AI in Mathematics",
                           authors=["25 initial Fields Medallist signatories"], **extra)


def run_with(aliases=ALIASES):
    base = make_run()
    items = [dict(i) for i in base.items] + [declaration_item(aliases)]
    return cm.CuratedRun.from_list_doc(approved_doc(items), private_texts=PRIVATE)


def pid_of(run, venue):
    return next(run.pids[i["item_id"]] for i in run.items if i.get("venue") == venue)


def test_the_group_author_sentence_routes_to_the_declaration_and_passes():
    run = run_with()
    result, judge = check("EXPERT: " + SENTENCE, run=run)
    r = result.routing[0]
    assert r.route == "commentary" and r.pids == [pid_of(run, "Zenodo")] and r.passed and r.verdict == "supported"
    assert "twenty-five Fields medalists signed this statement".lower() in judge.calls[0][1].lower()          # judged against the declaration's own text


def test_the_description_alias_routes_too():
    run = run_with()
    result, _ = check("EXPERT: The declaration says that solving problems is only a tool for reaching conceptual understanding.", run=run)
    assert result.routing[0].route == "commentary" and result.routing[0].pids == [pid_of(run, "Zenodo")]


def test_a_misattributed_group_claim_fails():
    run = run_with()
    result, _ = check("EXPERT: Fields medalists signed a statement saying that OpenAI proved the Riemann hypothesis.", run=run,
                      judge=Judge({"Fields medalists": {"verdict": "unsupported", "reason": "the declaration says no such thing"}}))
    assert not result.passed and result.violations[0]["route"] == "commentary" and result.violations[0]["pid"] == pid_of(run, "Zenodo")


def test_without_the_aliases_the_sentence_is_not_routed_and_the_singular_does_not_match():
    plain = run_with(aliases=None)
    result, _ = check("EXPERT: " + SENTENCE, run=plain)
    assert result.routing[0].route == "content"                          # the gap this fixes
    with_aliases = run_with()
    result, _ = check("EXPERT: The Fields medalist Hugo Duminil-Copin spoke about it.", run=with_aliases)
    assert result.routing[0].pids != [pid_of(with_aliases, "Zenodo")]


def test_the_declaration_is_listed_in_the_references_once_credited():
    run = run_with()
    script = "EXPERT: " + SENTENCE
    assert ca.credited_commentary_pids(script, run) == [pid_of(run, "Zenodo")]
    text = cm.apply_curated_sources("Intro.", run, run.confirmed_papers(), [], script=script)
    assert "https://zenodo.org/records/1" in text and "25 initial Fields Medallist signatories, Zenodo" in text


def test_the_aliases_are_not_part_of_the_list_hash():
    a, b = [declaration_item(x) for x in (ALIASES, None)]
    assert cs.list_hash({"repo": "r", "commit": "c"}, [a]) == cs.list_hash({"repo": "r", "commit": "c"}, [b])
