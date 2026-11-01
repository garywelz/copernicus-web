"""The deterministic curated-sources checks (design §4.1, §5, §7; decisions Q3 and Q4). Pure functions: no model, no network."""
import pytest

import curated_checks as cc

ETH = {"pid": "P1", "title": "The Exponential Time Hypothesis is False", "family_title": "Disproof of the Exponential Time Hypothesis",
       "status": cc.STATUS_HAS_LEAN, "class": "company_release"}
HADWIGER = {"pid": "P2", "title": "A counterexample to Hadwiger's conjecture", "family_title": "Graph coloring, clique minors, and Colin de Verdiere invariants",
            "status": cc.STATUS_UNVERIFIED, "class": "company_release"}
WEIL = {"pid": "P3", "title": "Algebraicity of Weil classes on split abelian eightfolds", "family_title": None, "status": cc.STATUS_WITHDRAWN,
        "class": "company_release"}
PRINT = {"pid": "P4", "title": "Attention Is All You Need", "family_title": None, "status": None, "class": "preprint"}
RESULTS = [ETH, HADWIGER, WEIL]


def kinds(v):
    return sorted(x["kind"] for x in v)


def status(script, results=RESULTS):
    return cc.check_status_wording(script, results)


# --- mentions -------------------------------------------------------------------------------------------------------------------
def test_a_result_is_found_by_its_title_or_most_of_its_distinctive_words():
    assert cc.mentions("OpenAI's manuscript, The Exponential Time Hypothesis is False, appeared in October.", ETH)
    assert cc.mentions("Their paper on the exponential time hypothesis says it is false.", ETH)          # family title words
    assert cc.mentions("A counterexample to Hadwiger's conjecture was posted.", HADWIGER)
    assert not cc.mentions("The weather was exponential today.", ETH)
    assert not cc.mentions("A counterexample was posted.", HADWIGER)


# --- status wording ---------------------------------------------------------------------------------------------------------------
@pytest.mark.parametrize("sentence,term", [
    ("The exponential time hypothesis result was verified by the Lean formalization.", "verified"),
    ("The exponential time hypothesis proof has been formally verified.", "formally verified"),
    ("The exponential time hypothesis disproof is machine-checked.", "machine-checked"),
    ("OpenAI proved that the exponential time hypothesis is false.", "proved"),
    ("The exponential time hypothesis disproof has been proven.", "proved"),
    ("The exponential time hypothesis proof is confirmed correct.", "confirmed correct"),
])
def test_forbidden_terms_about_a_named_result_are_flagged(sentence, term):
    v = status("HOST: Tell me about it.\nEXPERT: " + sentence)
    assert [x["term"] for x in v] == [term] and v[0]["kind"] == "forbidden_term" and v[0]["pid"] == "P1"


@pytest.mark.parametrize("sentence", [
    "The exponential time hypothesis result has not been independently verified.",
    "Nobody has verified the exponential time hypothesis disproof.",
    "The exponential time hypothesis result is unverified.",
    "OpenAI says the exponential time hypothesis proof was verified in Lean.",                 # attributed
    "OpenAI claims to have proved that the exponential time hypothesis is false.",
    "According to OpenAI the exponential time hypothesis disproof is machine-checked.",
    "OpenAI's catalogue lists a Lean formalization for the exponential time hypothesis manuscript.",
    "The exponential time hypothesis result was not formally verified, as far as anyone knows.",
    "It is not yet machine-checked: the exponential time hypothesis disproof is new.",
])
def test_negated_attributed_and_plain_catalogue_wording_is_allowed(sentence):
    assert status("EXPERT: " + sentence) == []


@pytest.mark.parametrize("sentence", [
    "Quanta reports that experts largely agree the exponential time hypothesis result was verified.",
    "Quanta reported that the exponential time hypothesis proof was formally verified in Lean.",
    "Scientific American said the exponential time hypothesis disproof is proven.",
    "The Washington Times wrote that the exponential time hypothesis result was verified in Lean.",
    "Experts say the exponential time hypothesis proof is confirmed correct.",
    "Mathematicians told Nature the exponential time hypothesis disproof is machine-checked.",
    "The exponential time hypothesis result was verified in Lean, which Quanta says.",
])
def test_a_named_source_reporting_is_an_attribution_in_any_tense(sentence):
    assert status("EXPERT: " + sentence) == []


@pytest.mark.parametrize("sentence", [
    "The exponential time hypothesis result was verified.",
    "The exponential time hypothesis proof is proven, which Quanta covered.",              # a name, but no reporting verb
    "The exponential time hypothesis proof says it is proven.",                            # a lower-case subject is not a named source
    "Quanta reports on the exponential time hypothesis story. The proof was verified.",    # the next sentence is the episode's own voice
])
def test_the_episodes_own_voice_still_may_not_say_verified_proven_or_confirmed(sentence):
    assert status("EXPERT: " + sentence) != []


def test_the_sentence_after_a_named_result_is_in_the_window():
    v = status("EXPERT: The exponential time hypothesis manuscript is new. It was machine-checked last week.")
    assert [x["term"] for x in v] == ["machine-checked"]


def test_a_sentence_about_lean_is_checked_even_if_no_result_is_named_in_it():
    assert [x["term"] for x in status("EXPERT: The Lean proof is verified.")] == ["verified"]
    assert [x["term"] for x in status("EXPERT: The formalization is machine-checked.")] == ["machine-checked"]
    assert status("EXPERT: The Lean library has been around for years.") == []


def test_ordinary_sentences_that_name_nothing_are_not_checked():
    assert status("EXPERT: Euler proved many things and the theorem was verified long ago.") == []


def test_speaker_labels_are_not_part_of_what_is_checked():
    assert status("MATILDA: The exponential time hypothesis manuscript says what it says.") == []
    assert cc.dialogue_text("HOST: Hello there.\nEXPERT: Hi.") == "Hello there.\nHi."
    assert cc.dialogue_text("MATILDA: a\nADAM: b") == "a\nb"


def test_a_withdrawn_manuscript_must_be_said_to_be_withdrawn_in_every_sentence_that_names_it():
    bad = status("EXPERT: The paper on algebraicity of Weil classes on split abelian eightfolds is a key result.")
    assert kinds(bad) == ["withdrawn_not_stated"] and bad[0]["pid"] == "P3"
    assert status("EXPERT: The paper on algebraicity of Weil classes on split abelian eightfolds was withdrawn in October.") == []
    assert status("EXPERT: OpenAI withdrew the algebraicity of Weil classes on split abelian eightfolds paper.") == []
    assert status("EXPERT: The algebraicity of Weil classes on split abelian eightfolds paper carries a withdrawal notice.") == []
    assert status("EXPERT: The algebraicity of Weil classes on split abelian eightfolds paper was retracted.") == []


def test_a_withdrawn_paper_called_verified_is_flagged_twice_over():
    v = status("EXPERT: The algebraicity of Weil classes on split abelian eightfolds paper was verified.")
    assert kinds(v) == ["forbidden_term", "withdrawn_not_stated"]


def test_results_without_a_status_are_not_checked():
    assert cc.check_status_wording("EXPERT: The attention transformer paper was verified.", [{**PRINT, "title": "The attention transformer paper"}]) == []


# --- verbatim runs ---------------------------------------------------------------------------------------------------------------
TEXT = "The proof, according to several mathematicians, relies on a delicate counting argument that nobody had tried before this year."


def test_eight_consecutive_words_from_a_commentary_text_are_flagged():
    script = "HOST: What happened?\nEXPERT: Reportedly it relies on a delicate counting argument that nobody had tried, and that is why it matters."
    v = cc.check_verbatim_runs(script, [TEXT])
    assert len(v) == 1 and v[0]["words"] >= 8 and "delicate counting argument" in v[0]["quote"] and v[0]["kind"] == "verbatim_run"


def test_seven_words_are_allowed():
    script = "EXPERT: It relies on a delicate counting argument, I would say, and it is neat."          # 'relies on a delicate counting argument' = 6
    assert cc.check_verbatim_runs(script, [TEXT]) == []
    seven = "EXPERT: Others said it relies on a delicate counting argument that is clever."             # 'relies on a delicate counting argument that' = 7
    assert cc.check_verbatim_runs(seven, [TEXT]) == []


def test_exactly_eight_is_the_threshold():
    eight = "EXPERT: It relies on a delicate counting argument that nobody?"                              # relies...nobody = 8 words
    assert len(cc.check_verbatim_runs(eight, [TEXT])) == 1
    assert cc.check_verbatim_runs(eight, [TEXT], n=9) == []


def test_case_punctuation_accents_and_quotes_do_not_hide_a_copy():
    script = 'EXPERT: "RELIES on a delicate counting argument... that nobody had tried" is what they wrote.'
    assert len(cc.check_verbatim_runs(script, [TEXT])) == 1
    assert len(cc.check_verbatim_runs("EXPERT: Café résumé naïve façade über déjà vu cliché fiancé", ["cafe resume naive facade uber deja vu cliche fiance"])) == 1


def test_a_run_is_reported_once_with_its_whole_length_and_each_text_is_searched():
    long_copy = "EXPERT: " + " ".join(TEXT.split()[:15]) + " and then more."
    v = cc.check_verbatim_runs(long_copy, [TEXT])
    assert len(v) == 1 and v[0]["words"] == 15
    other = "A second commentary text says that the whole thing was overhyped by everyone involved in it."
    v2 = cc.check_verbatim_runs("EXPERT: They say that the whole thing was overhyped by everyone involved in it, sadly.", [TEXT, other])
    assert len(v2) == 1 and v2[0]["source_index"] == 1


def test_a_quotation_the_producer_approved_is_excused_but_only_that_one():
    q = "relies on a delicate counting argument that nobody had tried before"
    script = "EXPERT: It " + q + ". Elsewhere: nobody had tried before this year, which is what the article says again."
    assert cc.check_verbatim_runs(script, [TEXT], approved_quotes=[q]) == []
    script2 = "EXPERT: It " + q + ". Later, according to several mathematicians, relies on a delicate counting argument that nobody had tried before this year."
    assert len(cc.check_verbatim_runs(script2, [TEXT], approved_quotes=["something unrelated entirely here"])) >= 1


def test_no_commentary_text_means_nothing_to_check():
    assert cc.check_verbatim_runs("EXPERT: anything at all, including a long run of words that could be copied from somewhere else.", []) == []
    assert cc.check_verbatim_runs("", [TEXT]) == []
    assert cc.check_verbatim_runs("EXPERT: short", [TEXT]) == []


# --- spoken names --------------------------------------------------------------------------------------------------------------------
@pytest.mark.parametrize("line", [
    "EXPERT: Hello, I'm Adam, and I study complexity.", "HOST: I am Matilda and this is the show.", "HOST: My name is Bella.",
    "HOST: Thanks, Adam.", "HOST: Thank you Daniel for that.", "HOST: Adam, what should listeners take from this?",
    "EXPERT: Good question, Matilda.", "HOST: Welcome back. This is Sam.", "EXPERT: Well, Bryan and I disagree.",
    "HOST: Great, thanks. Hello Lily!", "EXPERT: It is a hard problem, Bill."])
def test_a_voice_name_used_as_an_introduction_or_form_of_address_is_flagged(line):
    v = cc.check_spoken_names(line)
    assert len(v) == 1 and v[0]["kind"] == "spoken_name"


@pytest.mark.parametrize("line", [
    "MATILDA: Today we look at one preprint.", "ADAM: It is a long story.", "HOST: Daniel Litt wrote about it on social media.",
    "EXPERT: Adam optimization is a standard method.", "EXPERT: Bill Gates is not a mathematician.", "HOST: Sam Altman has commented.",
    "HOST: What does the manuscript claim?\nEXPERT: It claims the hypothesis is false.",
    "EXPERT: This is Sam Altman's essay about it.", "HOST: Thanks, Bill Gates, for the donation.", "EXPERT: Well, Daniel Litt said it needs checking.",
    "EXPERT: Hello, I'm Adam Smith, the economist."])
def test_labels_and_ordinary_uses_of_a_name_are_not_flagged(line):
    assert cc.check_spoken_names(line) == []


# --- class labels --------------------------------------------------------------------------------------------------------------------
def test_a_named_preprint_must_be_called_a_preprint():
    v = cc.check_class_labels("EXPERT: The paper Attention Is All You Need changed the field.", [PRINT])
    assert kinds(v) == ["preprint_not_labelled"]
    assert cc.check_class_labels("EXPERT: The preprint Attention Is All You Need changed the field.", [PRINT]) == []
    assert cc.check_class_labels("EXPERT: Preprints are common, but this episode names none.", [PRINT]) == []   # not named: nothing owed


def test_a_named_company_release_must_be_said_not_to_be_peer_reviewed():
    s = "EXPERT: OpenAI's manuscript, The Exponential Time Hypothesis is False, was posted in October."
    assert kinds(cc.check_class_labels(s, [ETH])) == ["company_release_not_labelled"]
    for ok in ("This is a company release that has not been peer reviewed. ", "It is not peer reviewed. ", "It hasn't been peer reviewed. ",
               "It is not yet peer-reviewed. "):
        assert cc.check_class_labels(s + " " + ok, [ETH]) == [], ok


# --- all of them ---------------------------------------------------------------------------------------------------------------------
GOOD = ("HOST: What is this release?\n"
        "EXPERT: OpenAI posted a company release that has not been peer reviewed. One manuscript, The Exponential Time Hypothesis is False, "
        "comes with a Lean formalization in OpenAI's catalogue, and the catalogue's own review status is unchecked. Nobody has independently verified it.\n"
        "HOST: And the withdrawn one?\n"
        "EXPERT: The algebraicity of Weil classes on split abelian eightfolds paper was withdrawn in October.")


def test_a_clean_script_passes_everything():
    assert cc.run_all(GOOD, RESULTS, items=RESULTS) == []


def test_run_all_collects_every_kind_and_summarises_them():
    bad = ("HOST: Hello, I'm Matilda.\n"
           "EXPERT: The exponential time hypothesis disproof was formally verified. The algebraicity of Weil classes on split abelian eightfolds paper "
           "relies on a delicate counting argument that nobody had tried before this year. The Exponential Time Hypothesis is False is out.")
    v = cc.run_all(bad, RESULTS, commentary_texts=[TEXT], items=RESULTS)
    assert set(cc.summary(v)) == {"status_wording", "verbatim_run", "spoken_name", "class_label"}
    assert {"forbidden_term", "withdrawn_not_stated", "verbatim_run", "spoken_name", "company_release_not_labelled"} <= set(kinds(v))


def test_feedback_names_each_problem_and_quotes_what_to_fix():
    v = cc.run_all("HOST: Hello, I'm Matilda.\nEXPERT: The exponential time hypothesis disproof was formally verified.", [ETH], items=[ETH])
    fb = cc.feedback_text(v)
    assert "formally verified" in fb and "I'm Matilda" in fb and "HOST and EXPERT" in fb and "REJECTED" in fb
    assert cc.feedback_text([]) == ""


def test_the_error_carries_the_violations():
    e = cc.CuratedCheckError([{"check": "spoken_name", "kind": "spoken_name"}, {"check": "verbatim_run", "kind": "verbatim_run"}])
    assert "spoken_name" in str(e) and "verbatim_run" in str(e) and len(e.violations) == 2
