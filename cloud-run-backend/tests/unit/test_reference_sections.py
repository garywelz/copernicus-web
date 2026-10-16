"""Tests for reference_sections (gap 3 fix 1, C6): the lists are built by code from registry records. Offline."""
import pytest

import paper_confirmation as pc
import reference_sections as rs


def paper(pid, title, authors, year, venue="Journal of Tests", arxiv=None, ver=None, doi=None, pmid=None):
    return pc.ConfirmedPaper(pid=pid, title=title, authors=authors, year=year, venue=venue,
                             ids={"arxiv": arxiv, "arxiv_version": ver, "pmid": pmid, "doi": doi},
                             url=f"https://arxiv.org/abs/{arxiv}{ver or ''}" if arxiv else f"https://doi.org/{doi}",
                             abstract="Abs.", registry="arxiv" if arxiv else "crossref", confirmed_at="t", title_match=1.0)


P1 = paper("P1", "Requested paper title", ["Ada Lovelace"], 2025, doi="10.1/p1")
P2 = paper("P2", "AI prediction leads people to forgo guaranteed rewards", ["Aoi Naito", "Hirokazu Shirado"], 2026, venue=None, arxiv="2603.28944", ver="v1")
P3 = paper("P3", "Third paper on cells", ["Grace Hopper", "Alan Turing", "Marie Curie", "Ada Lovelace"], 2023, pmid="12345678", doi="10.1/p3")
P4 = paper("P4", "Fourth paper unnamed", ["Edsger Dijkstra"], 2022, doi="10.1/p4")
ALL = [P1, P2, P3, P4]

DESC = "Opening.\n\n## Key ideas\n\n- one\n\n## References\n\n- Model Wrote This (2019). Fake Paper. DOI: 10.9/fake\n\n## Hashtags\n#a #b\n"


def test_strip_removes_model_reference_sections_and_keeps_the_rest():
    out = rs.strip_model_reference_sections(DESC)
    assert "Fake Paper" not in out and "## References" not in out
    assert "## Key ideas" in out and "## Hashtags" in out and "#a #b" in out


def test_strip_handles_other_headings_and_end_of_text():
    out = rs.strip_model_reference_sections("Body\n\n### Bibliography\n\n- x\n\n# Sources\n\n- y\n")
    assert out.strip() == "Body"


def test_references_are_one_compact_line_per_paper_from_registry_fields():
    md = rs.build_sections(ALL, named_pids=["P3", "P2"], requested_pid="P1")
    refs = md.split(rs.FURTHER_READING_POINTER)[0]
    lines = [l for l in refs.splitlines() if l.startswith("- ")]
    assert len(lines) == 3
    assert refs.index("Requested paper title") < refs.index("Third paper on cells") < refs.index("AI prediction leads")  # requested, then order of mention
    assert lines[0] == "- Lovelace (2025). Requested paper title. Journal of Tests. DOI: 10.1/p1"
    assert lines[1] == "- Hopper et al. (2023). Third paper on cells. Journal of Tests. DOI: 10.1/p3"
    assert lines[2] == "- Naito and Shirado (2026). AI prediction leads people to forgo guaranteed rewards. arXiv:2603.28944v1"
    assert "http" not in refs and all(len(l) < 200 for l in lines)


def test_further_reading_is_not_in_the_description_only_one_pointer_line():
    md = rs.build_sections(ALL, named_pids=["P3", "P2"], requested_pid="P1")
    assert "## Further reading" not in md and "Fourth paper unnamed" not in md and "Dijkstra" not in md
    assert md.rstrip().endswith(rs.FURTHER_READING_POINTER) and md.count("Further reading") == 1
    assert "episode page" in rs.FURTHER_READING_POINTER


def test_no_pointer_when_every_confirmed_paper_is_listed():
    assert rs.FURTHER_READING_POINTER not in rs.build_sections([P1, P2], ["P2"], "P1")


def test_further_reading_list_for_the_web_page():
    assert [c.pid for c in rs.further_reading(ALL, ["P3", "P2"], "P1")] == ["P4"]
    assert [c.pid for c in rs.further_reading(ALL, [], None)] == ["P1", "P2", "P3", "P4"]


def test_long_titles_and_venues_are_shortened_in_compact_lines():
    long = paper("P9", "Word " * 60, ["A B"], 2024, venue="The Very Long Journal Name " * 5, doi="10.1/z")
    line = rs.compact_line(long)
    assert len(line) < 260 and "…" in line


def test_zenodo_type_shows_in_the_reference_line():
    z = paper("P8", "A deposited preprint", ["Grace Hopper"], 2026, venue="Zenodo preprint", doi="10.5281/zenodo.1")
    assert rs.compact_line(z) == "- Hopper (2026). A deposited preprint. Zenodo preprint. DOI: 10.5281/zenodo.1"
    assert "Zenodo preprint" in rs.full_line(z)


def test_unnamed_papers_never_appear_under_references():
    md = rs.build_sections(ALL, named_pids=["P2"], requested_pid=None)
    refs = md.split(rs.FURTHER_READING_POINTER)[0]
    assert "AI prediction leads" in refs and "Fourth paper unnamed" not in refs and "Third paper" not in refs


def test_duplicates_in_named_pids_are_listed_once():
    md = rs.build_sections(ALL, named_pids=["P2", "P2", "P1"], requested_pid="P1")
    assert md.count("Requested paper title") == 1 and md.count("AI prediction leads") == 1


def test_no_named_papers_and_no_request_gives_only_the_pointer():
    md = rs.build_sections(ALL, named_pids=[], requested_pid=None)
    assert "## References" not in md and md.startswith("## Further reading") and rs.FURTHER_READING_POINTER in md


def test_nothing_to_list_returns_empty():
    assert rs.build_sections([], [], None) == ""


def test_apply_inserts_before_hashtags_and_replaces_model_text():
    out = rs.apply_reference_sections(DESC, ALL, ["P2"], "P1")
    assert "Fake Paper" not in out
    assert out.index("## References") < out.index(rs.FURTHER_READING_POINTER) < out.index("## Hashtags")
    assert out.count("## References") == 1 and "#a #b" in out


def test_apply_appends_when_there_is_no_hashtag_section():
    out = rs.apply_reference_sections("Opening.\n", ALL, ["P2"], None)
    assert out.startswith("Opening.") and out.rstrip().endswith(rs.FURTHER_READING_POINTER)


def test_apply_is_idempotent():
    once = rs.apply_reference_sections(DESC, ALL, ["P2", "P3"], "P1")
    twice = rs.apply_reference_sections(once, ALL, ["P2", "P3"], "P1")
    assert once == twice


def test_does_not_mutate_the_papers():
    before = P3.venue
    rs.build_sections(ALL, ["P2"], "P1")
    assert P3.venue == before and P3.venue == "Journal of Tests"


def test_survives_the_existing_length_limiter_with_both_sections_intact():
    from content_fixes import limit_description_length
    body = "Paragraph of body text. " * 200
    desc = body + "\n\n## Hashtags\n#a #b\n"
    out = rs.apply_reference_sections(desc, ALL, ["P2", "P3"], "P1")
    limited = limit_description_length(out, 4000)
    assert "## References" in limited and rs.FURTHER_READING_POINTER in limited and "## Hashtags" in limited
    for title in ("Requested paper title", "AI prediction leads"):
        assert title in limited
    assert len(limited) <= 4100


def test_passes_the_existing_pre_publish_placeholder_gate():
    from content_fixes import validate_description_before_publish
    out = rs.apply_reference_sections(DESC, ALL, ["P2", "P3"], "P1")
    validate_description_before_publish(out)  # raises DescriptionValidationError on a placeholder pattern


# ---------------------------------------------------------------- collective authors (ever-math-260008 showed "Community (2019)")
def test_a_collective_author_is_shown_whole_not_by_its_last_word():
    mathlib = paper("P1", "The Lean mathematical library", ["The mathlib Community"], 2019, venue=None, arxiv="1910.09336", ver="v2")
    assert rs.compact_line(mathlib) == "- The mathlib Community (2019). The Lean mathematical library. arXiv:1910.09336v2"
    ligo = paper("P2", "Observation of a signal", ["LIGO Scientific Collaboration", "Virgo Collaboration"], 2016, venue="PRL", doi="10.1/ligo")
    assert rs.compact_line(ligo).startswith("- LIGO Scientific Collaboration and Virgo Collaboration (2016).")
    mixed = paper("P3", "A joint paper", ["The ATLAS Collaboration", "Ada Lovelace", "Alan Turing"], 2024, venue=None, doi="10.1/atlas")
    assert rs.compact_line(mixed).startswith("- The ATLAS Collaboration et al. (2024).")


def test_people_are_still_shown_by_surname():
    assert rs.compact_line(P2).startswith("- Naito and Shirado (2026).")
    assert rs.compact_line(P3).startswith("- Hopper et al. (2023).")
    assert rs.compact_line(paper("P9", "A title", ["Dijkstra, Edsger W."], 2022, venue=None, doi="10.1/d")).startswith("- Dijkstra (2022).")   # Surname, Given order


def test_what_counts_as_collective():
    for name in ("The mathlib Community", "LIGO Scientific Collaboration", "Particle Data Group", "The Lean Team", "OpenAI Contributors", "CMS Collaboration"):
        assert rs.is_collective(name), name
    for name in ("Ada Lovelace", "Dijkstra, Edsger W.", "Maria Skłodowska Curie", "Nicolas Balacheff", "Thierry Bouche", "Jesse Alama"):
        assert not rs.is_collective(name), name
