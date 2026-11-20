"""A section template is a shape, never an episode's facts.

The templates are handed to the writer on every curated run, whatever the source list. When one of them asserted a particular event
("hundreds of manuscripts released overnight", a named company's withdrawn paper, a "sign error in a key step"), the writer followed it:
the same sentences appeared in episodes whose lists held no such source, where no check could catch them, because the status and
attribution checks only examine a sentence that names a listed source. Every particular must come from the list and from each item's
status record instead.
"""
import re

import curated_script as cs

FORBIDDEN_PHRASES = ("withdrawn", "withdrew", "sign error", "overnight", "hundreds of manuscripts", "unchecked", "within a day")
# Bodies that release work, and anything shaped like a person's name or a specific paper's nickname, belong to a list, not to a template.
FORBIDDEN_NAMES = ("openai", "anthropic", "google", "deepmind", "eth", "meta", "microsoft", "nvidia", "stanford", "mit", "baker lab")


def templates():
    return {t[0]: t[3] for t in cs.SECTION_TEMPLATES}


def test_no_template_asserts_a_particular_event_or_status():
    for key, text in templates().items():
        low = text.lower()
        for phrase in FORBIDDEN_PHRASES:
            if phrase == "withdrawn":
                continue                      # the rule "never name a withdrawn source without the word" is a shape, tested below
            assert phrase not in low, f"the {key} template asserts an episode's facts: {phrase!r}"


def test_no_template_names_a_company_a_person_or_a_release():
    for key, text in templates().items():
        low = text.lower()
        for name in FORBIDDEN_NAMES:
            assert not re.search(rf"\b{re.escape(name)}\b", low), f"the {key} template names {name!r}"
        quoted = re.findall(r"\"([^\"]+)\"", text)
        for q in quoted:
            assert not re.match(r"^the \S+ paper$", q.strip().lower()), f"the {key} template names a particular release: {q!r}"


def test_withdrawal_wording_is_conditional_on_the_notes():
    """The templates may still require the word "withdrawn" of a withdrawn source, but only where the notes record one."""
    trust = templates()["trust"].lower()
    assert "withdrawn" in trust, "the rule about naming a withdrawn source should survive"
    assert "where the notes record" in trust or "only where the notes record" in trust, \
        "the trust template must make any withdrawal conditional on the notes"
    assert "sign error" not in trust and "within a day" not in trust, "the trust template must not assert a particular withdrawal"


def test_the_show_rules_assert_no_particular_event_and_name_nobody():
    """SHOW_RULES goes to the writer with every section, so an example there is an instruction too: rule 3 once required the script to say a
    withdrawn manuscript was withdrawn "within a day of the release because of a sign error in a key step", and rules 2, 6 and 7 named
    particular people, outlets and papers as the names to use."""
    rules = cs.SHOW_RULES
    low = rules.lower()
    for phrase in ("sign error", "within a day", "overnight", "hundreds of manuscripts", "unchecked"):
        assert phrase not in low, f"SHOW_RULES asserts an episode's facts: {phrase!r}"
    for name in FORBIDDEN_NAMES + ("tao", "quanta", "wikipedia", "scientific american", "washington times", "fields medalist"):
        assert not re.search(rf"\b{re.escape(name)}\b", low), f"SHOW_RULES names {name!r}"
    assert not re.search(r"the \S+ paper\"", low), "SHOW_RULES names a particular release as the short name to use"
    assert "withdrawn" in low and "says no more than that record says" in low, \
        "the withdrawal rule should survive, bounded by the record"


def test_opening_requires_every_particular_to_come_from_the_notes():
    opening = templates()["opening"].lower()
    assert "from the notes" in opening, "the opening template must say its particulars come from the notes"
    assert "hundreds" not in opening and "overnight" not in opening
