"""Tests for podcast description citation/hashtag/formatting cleanup."""

from content_fixes import (
    sanitize_reference_placeholders,
    validate_academic_references,
    limit_description_length,
    join_description_sections,
    generate_relevant_hashtags,
)
from services.paper_resolver import paper_year_text


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


class TestPaperYearText:
    def test_year_field(self):
        assert paper_year_text({"year": "1989"}) == "1989"

    def test_published_date_prefix(self):
        assert paper_year_text({"published_date": "1989-02-01"}) == "1989"

    def test_missing(self):
        assert paper_year_text({}) is None
