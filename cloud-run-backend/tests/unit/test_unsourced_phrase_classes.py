"""History, consensus and verdicts the sources never give.

On 2026-11-23 all four curated lists produced scripts that passed every check and every one of them opened with a history no source dates
and filled its closing with judgements no source makes: "For decades, mathematicians have studied...", "proposed by a mathematician in the
1950s", "a problem that has challenged mathematicians for over a century", "the mathematical community has not yet confirmed its
correctness", "would be a significant step", "could significantly advance our understanding", "offering a partial resolution". All of it had
to be cut by hand from three scripts at once.

These three classes are refused by the rule the scope check already uses: the term is allowed where a listed source uses it, and refused
where none does. So an abstract that calls its own problem long-standing lets the script call it long-standing, and an abstract that reports
a significant improvement lets the script say so.
"""
import unattributed_claims as uc


class S:
    def __init__(self, title, abstract=""):
        self.title, self.abstract = title, abstract
        self.pid, self.authors, self.year = "P1", ["OpenAI"], 2026


PLAIN = [S("The irrationality exponent of pi is 2", "We prove that the irrationality exponent of pi is 2.")]


def kinds(script, sources=None):
    return {v["kind"]: v.get("terms") for v in uc.check(script, sources or PLAIN) if v["kind"].startswith("unsourced_")}


# --- undated history ----------------------------------------------------------------------------------------------------------------
def test_an_undated_history_is_refused():
    for line in ("HOST: For decades, mathematicians have studied this question.",
                 "HOST: The problem has challenged mathematicians for over a century.",
                 "HOST: This is a long-standing conjecture about pi.",
                 "HOST: The conjecture was proposed in the 1950s.",
                 "HOST: The question has puzzled mathematicians.",
                 "HOST: For some time, this has been open."):
        assert "unsourced_history" in kinds(line), line


def test_a_history_a_source_dates_is_allowed():
    """The sources decide. A source that calls its own problem long-standing lets the script say so."""
    sourced = [S("The irrationality exponent of pi is 2",
                 "We settle a long-standing conjecture, open for decades, on the irrationality exponent of pi.")]
    assert kinds("HOST: This is a long-standing conjecture, open for decades.", sourced) == {}


def test_a_common_word_in_the_phrase_does_not_make_it_sourced():
    """"for decades" must not count as sourced because every abstract contains the word "for"."""
    assert "for" in uc.source_words(PLAIN) or True          # the point is the phrase test, not this word
    assert "unsourced_history" in kinds("HOST: For decades, this was open.")


# --- consensus ----------------------------------------------------------------------------------------------------------------------
def test_a_consensus_no_source_reports_is_refused():
    for line in ("EXPERT: The mathematical community has not yet confirmed it.",
                 "EXPERT: It is widely accepted that the bound is sharp.",
                 "EXPERT: Experts believe the proof will hold.",
                 "EXPERT: The scientific community is still assessing the work.",
                 "HOST: What would the mathematical community look for?"):
        assert "unsourced_consensus" in kinds(line), line


def test_an_impersonal_statement_of_the_same_fact_is_allowed():
    """The replacement a script should write: the fact without the crowd."""
    assert kinds("EXPERT: Its correctness has not been independently confirmed.") == {}


# --- evaluation ---------------------------------------------------------------------------------------------------------------------
def test_a_verdict_no_source_gives_is_refused():
    for line in ("EXPERT: This would be a significant step.",
                 "EXPERT: It is an important contribution to the field.",
                 "EXPERT: The result is a breakthrough.",
                 "EXPERT: It offers a partial resolution to the problem.",
                 "HOST: So, with these promising results, what comes next?",
                 "EXPERT: That the regime is independent of temperature is particularly interesting.",
                 "EXPERT: Peer review is crucial here."):
        assert "unsourced_evaluation" in kinds(line), line


def test_a_judgement_a_source_makes_is_allowed():
    sourced = [S("A significant improvement on the bound",
                 "This is a significant improvement, and a promising route to the full conjecture.")]
    assert kinds("EXPERT: The authors call it a significant improvement, and a promising route.", sourced) == {}


def test_saying_what_was_done_is_not_a_verdict():
    assert kinds("EXPERT: The manuscript states that the irrationality exponent of pi is two.") == {}


# --- the rule's shape ---------------------------------------------------------------------------------------------------------------
def test_a_sentence_can_fail_more_than_one_class():
    got = kinds("HOST: For decades the mathematical community has called this a breakthrough.")
    assert set(got) == {"unsourced_history", "unsourced_consensus", "unsourced_evaluation"}, got


def test_the_violation_names_the_phrases_and_says_the_sources_decide():
    v = [x for x in uc.check("HOST: For decades, this was open.", PLAIN) if x["kind"] == "unsourced_history"][0]
    assert v["terms"] == ["for decades"]
    assert "no listed source uses" in v["message"] and "The sources decide" in v["message"]


def test_a_sentence_the_attribution_check_already_read_is_left_alone():
    """An attributed sentence has been judged against its source already; this check never second-guesses it."""
    line = "EXPERT: The authors call the result a breakthrough."
    assert uc.check(line, PLAIN, attributed_quotes=[line]) == []


def test_the_classes_are_lists_that_can_grow():
    for name in ("UNDATED_HISTORY", "CONSENSUS", "EVALUATION"):
        assert isinstance(getattr(uc, name), tuple) and len(getattr(uc, name)) >= 10


def test_the_templates_tell_the_writer_not_to_write_them():
    import curated_script
    rules = curated_script.SHOW_RULES
    for phrase in ("for decades", "long-standing", "the mathematical community", "widely accepted", "breakthrough",
                   "significant step forward", "partial resolution"):
        assert phrase in rules, phrase
    assert "only where a source's own words use it" in rules
