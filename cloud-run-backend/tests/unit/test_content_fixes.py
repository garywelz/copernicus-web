"""Tests for podcast description citation/hashtag/formatting cleanup."""

from content_fixes import (
    sanitize_reference_placeholders,
    validate_academic_references,
    limit_description_length,
    join_description_sections,
    generate_relevant_hashtags,
    make_reference_links_clickable,
    validate_description_before_publish,
    DescriptionValidationError,
)
from services.paper_resolver import paper_year_text
import pytest


class TestSanitizeReferencePlaceholders:
    def test_strips_placeholder_doi(self):
        text = "Stormo (1989). Title. DOI: 10.xxxx/xxxx"
        assert "10.xxxx/xxxx" not in sanitize_reference_placeholders(text)

    def test_strips_section_placeholder_line(self):
        text = "section DOI: 10.xxxx/xxxx\n* Stormo (1989). Title."
        out = sanitize_reference_placeholders(text)
        assert "10.xxxx/xxxx" not in out
        assert "Stormo" in out

    def test_recent_replaced_when_year_known(self):
        out = sanitize_reference_placeholders(
            "G D Stormo (Recent). Identifying sites.", known_year="1989"
        )
        assert "(1989)" in out
        assert "(Recent)" not in out

    def test_recent_dropped_when_year_unknown(self):
        out = sanitize_reference_placeholders("G D Stormo (Recent). Identifying sites.")
        assert "(Recent)" not in out

    def test_mashed_header_gets_newlines(self):
        mashed = "predictions more accurate and...## References\n- Stormo"
        out = sanitize_reference_placeholders(mashed)
        assert "...\n\n## References" in out

    def test_bare_hashtags_header(self):
        out = sanitize_reference_placeholders("body\n Hashtags\n#Biology")
        assert "## Hashtags" in out


class TestValidateAcademicReferences:
    def test_does_not_invent_placeholder_doi(self):
        out = validate_academic_references(
            "- Stormo, G D. Identifying protein-binding sites."
        )
        assert "10.xxxx" not in out
        assert "Stormo" in out

    def test_keeps_real_doi(self):
        out = validate_academic_references(
            "- Stormo (1989). Title. DOI: 10.1073/pnas.86.4.1183"
        )
        assert "10.1073/pnas.86.4.1183" in out


class TestLimitDescriptionLength:
    def test_truncation_does_not_mash_references(self):
        body = "A" * 3900
        desc = body + "## References\n- Stormo 1989. DOI: 10.1073/pnas.86.4.1183\n## Hashtags\n#Biology"
        out = limit_description_length(desc, max_length=4000)
        assert "## References" in out
        assert not out.split("## References")[0].endswith("## References")
        assert "\n\n## References" in out or out.strip().endswith("#Biology")


class TestJoinDescriptionSections:
    def test_blank_line_between_body_and_refs(self):
        out = join_description_sections("body...", "## References\n- Stormo")
        assert out == "body...\n\n## References\n- Stormo"


class TestHashtagsDoNotInventApplications:
    def test_stormo_title_does_not_add_crispr_or_cancer(self):
        tags = generate_relevant_hashtags(
            "Identifying protein-binding sites from unaligned DNA fragments.",
            "Biology",
            "Unraveling Life's Code: The Paradigm Shift in Identifying Protein-DNA Binding Sites from Unaligned Fragments",
            "This episode discusses CRISPR and cancer therapy applications of the 1989 method.",
        )
        assert "#CRISPR" not in tags
        assert "#CancerResearch" not in tags
        assert "#GeneEditing" not in tags
        assert "#Unraveling" not in tags
        assert "#Life's" not in tags
        assert "#Biology" in tags
        assert "#Identifying" not in tags
        assert "#Protein-binding" not in tags
        assert "#Protein-bindingSites" not in tags
        assert "#Paradigm" not in tags
        assert "#Shift" not in tags


class TestRewriteIndexVenues:
    def test_published_in_pubmed_becomes_journal(self):
        from content_fixes import rewrite_index_venues
        out = rewrite_index_venues(
            "pioneering work published in *pubmed* laid the groundwork.",
            "Proceedings of the National Academy of Sciences",
        )
        assert "pubmed" not in out.lower()
        assert "Proceedings of the National Academy of Sciences" in out

    def test_reference_dot_pubmed_dropped(self):
        from content_fixes import rewrite_index_venues, format_research_source_line
        out = rewrite_index_venues(
            "* Stormo. Title. pubmed. Available: https://pubmed.ncbi.nlm.nih.gov/2919167/"
        )
        assert ". pubmed." not in out.lower()
        line = format_research_source_line({
            "authors": ["G D Stormo", "G W Hartzell"],
            "title": "Identifying protein-binding sites from unaligned DNA fragments.",
            "journal": "Proceedings of the National Academy of Sciences",
            "publication_date": "1989",
            "source": "pubmed",
            "doi": "10.1073/pnas.86.4.1183",
        })
        assert "pubmed" not in line.lower()
        assert "1989" in line
        assert "Proceedings of the National Academy of Sciences" in line
        assert "10.1073/pnas.86.4.1183" in line


class TestDalleThumbnailAttempts:
    def test_standard_quality_first_not_hd(self):
        from content_fixes import dalle_thumbnail_attempts
        attempts = dalle_thumbnail_attempts("Stormo 1989", "protein-binding sites")
        assert attempts
        assert all(a["quality"] in {"low", "medium", "high"} for a in attempts)
        assert all(a["model"].startswith("gpt-image") for a in attempts)
        assert all("dall-e" not in a["model"] for a in attempts)
        assert all("no text" in a["prompt"].lower() for a in attempts)


class TestTtsPronunciationHints:
    def test_godel_and_kleene_respelled_for_tts(self):
        from content_fixes import apply_tts_pronunciation_hints
        src = (
            "Kurt Gödel and Stephen Kleene; also Godel, Goedel, "
            "Gödel's theorem and Kleene's recursion."
        )
        out = apply_tts_pronunciation_hints(src)
        assert "Gödel" not in out
        assert "Godel" not in out
        assert "Goedel" not in out
        assert "Kleene" not in out
        assert "Girdle" in out
        assert "Girdle's" in out
        assert "Klaynee" in out
        assert "Klaynee's" in out

    def test_nfd_umlaut_godel_is_respelled(self):
        from content_fixes import apply_tts_pronunciation_hints
        nfd = "G" + "o\u0308" + "del met Kleene"
        out = apply_tts_pronunciation_hints(nfd)
        assert "Girdle" in out
        assert "Klaynee" in out

    def test_does_not_touch_unrelated_words(self):
        from content_fixes import apply_tts_pronunciation_hints
        src = "Godelian methods and Kleenean algebra stay put."
        assert apply_tts_pronunciation_hints(src) == src

    def test_apply_content_fixes_keeps_scholarly_spelling(self):
        from content_fixes import apply_content_fixes
        script = "HOST: Gödel met Kleene.\nEXPERT: Godel's paper."
        out = apply_content_fixes(script, "math")
        assert "Gödel" in out
        assert "Kleene" in out
        assert "Godel" in out
        assert "Girdle" not in out
        assert "Klaynee" not in out


class TestMakeReferenceLinksClickable:
    def test_idempotent_on_already_linked_urls(self):
        """B3 fixture: the repeatedly-re-linked URLs from ever-phys-250026
        (Online Resources bullets), now in their correct single-link form
        (as R8 fixed them). Running the linkifier a second time on
        already-linked text must be a no-op -- this is the exact bug that
        produced the original corruption.
        """
        text = (
            "## References\n"
            "### Online Resources\n"
            "- Quantum Computing Report: [https://quantumcomputingreport.com/](https://quantumcomputingreport.com/)\n"
            "- IBM Quantum Experience: [https://quantum-computing.ibm.com/](https://quantum-computing.ibm.com/)\n"
            "\n## Hashtags\n#Physics"
        )
        once = make_reference_links_clickable(text)
        twice = make_reference_links_clickable(once)
        assert once == twice
        assert "[[" not in once
        assert "](https://quantumcomputingreport](" not in once

    def test_does_not_truncate_doi_with_parentheses(self):
        """B4 fixture: the 1992 J. Mol. Biol. DOI (Cardon & Stormo), which
        contains a literal '(92)'. The old regex stopped at that internal
        ')' and cut the DOI in half.
        """
        text = (
            "## References\n"
            "- Cardon, Stormo (1992). Expectation maximization algorithm. "
            "Journal of molecular biology. DOI: 10.1016/0022-2836(92)90723-w\n"
        )
        out = make_reference_links_clickable(text)
        assert "[10.1016/0022-2836(92)90723-w](https://doi.org/10.1016/0022-2836(92)90723-w)" in out
        # the old bug's exact broken signature must not appear
        assert "[10.1016/0022-2836(92]" not in out
        assert "))90723-w" not in out

    def test_idempotent_on_parenthetical_doi_link(self):
        """B3 + B4 together: once correctly linked, a DOI-with-parentheses
        link must also survive a second pass unchanged."""
        text = "## References\n- DOI: 10.1016/0022-2836(92)90723-w\n"
        once = make_reference_links_clickable(text)
        twice = make_reference_links_clickable(once)
        assert once == twice


class TestValidateDescriptionBeforePublish:
    def test_clean_text_passes(self):
        text = (
            "## References\n- Stormo (1989). Title. "
            "DOI: [10.1073/pnas.86.4.1183](https://doi.org/10.1073/pnas.86.4.1183)\n"
        )
        validate_description_before_publish(text)  # must not raise

    def test_empty_text_passes(self):
        validate_description_before_publish("")
        validate_description_before_publish(None)

    def test_rejects_placeholder_doi(self):
        """B1"""
        with pytest.raises(DescriptionValidationError, match="placeholder DOI"):
            validate_description_before_publish("- Author (2024). Title. DOI: 10.xxxx/xxxx")

    def test_rejects_recent_placeholder(self):
        """B2"""
        with pytest.raises(DescriptionValidationError, match="Recent"):
            validate_description_before_publish("- Stormo (Recent). Title.")

    def test_rejects_malformed_pubmed_url(self):
        with pytest.raises(DescriptionValidationError, match="PubMed"):
            validate_description_before_publish("Available: https://pubmed.ncbi.nlm.nlm.nih.gov/12345/")

    def test_rejects_boilerplate_finding(self):
        with pytest.raises(DescriptionValidationError, match="boilerplate"):
            validate_description_before_publish("- Research findings require further analysis")

    def test_rejects_literal_unknown_value(self):
        """B5"""
        with pytest.raises(DescriptionValidationError, match="unknown"):
            validate_description_before_publish(
                "Deep Reinforcement Learning with Communication: unknown "
                "The methodological advances driving these discoveries..."
            )

    def test_does_not_reject_ordinary_prose_use_of_unknown(self):
        # "remains largely unknown" is normal English, not a placeholder --
        # must not false-positive on this (it's not colon-prefixed).
        validate_description_before_publish("Dark matter remains largely unknown to physicists.")

    def test_rejects_unfilled_author_template(self):
        """B5"""
        with pytest.raises(DescriptionValidationError, match="Author et al"):
            validate_description_before_publish("- [Author et al. (2023). Title. DOI: 10.1038/x]")

    def test_rejects_example_doi_template(self):
        """B5"""
        with pytest.raises(DescriptionValidationError, match="Example DOI"):
            validate_description_before_publish(
                "- Some Title. DOI: [10.1038/x](https://doi.org/10.1038/x) (Example DOI)"
            )

    def test_rejects_nested_link_from_double_linkification(self):
        """B3"""
        with pytest.raises(DescriptionValidationError, match="nested"):
            validate_description_before_publish(
                "DOI: [10.1016/0022-2836(92](https://doi.org/10.1016/0022-2836(92))90723-w"
            )


class TestPaperYearText:
    def test_year_field(self):
        assert paper_year_text({"year": "1989"}) == "1989"

    def test_published_date_prefix(self):
        assert paper_year_text({"published_date": "1989-02-01"}) == "1989"

    def test_missing(self):
        assert paper_year_text({}) is None
