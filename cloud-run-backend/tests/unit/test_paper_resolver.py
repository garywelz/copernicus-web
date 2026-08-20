"""Unit tests for the Knowledge Engine -> podcast paper resolver helpers.

These cover identifier parsing and the generate-from-paper safety gates.
They do not hit Firestore or the generation pipeline.
"""

from services.paper_resolver import (
    parse_identifier,
    paper_abstract_text,
    paper_external_url,
    podcast_category_for_paper,
    is_unambiguous_generation_match,
)


class TestParseIdentifier:
    def test_doi_url(self):
        assert parse_identifier("https://doi.org/10.1093/nar/17.18.7293") == {
            "doi": "10.1093/nar/17.18.7293"
        }

    def test_doi_dx_url_uppercased(self):
        assert parse_identifier("https://dx.doi.org/10.1093/NAR/17.18.7293") == {
            "doi": "10.1093/nar/17.18.7293"
        }

    def test_bare_doi(self):
        assert parse_identifier("10.1093/nar/17.18.7293") == {
            "doi": "10.1093/nar/17.18.7293"
        }

    def test_pmid_url_trailing_slash(self):
        assert parse_identifier("https://pubmed.ncbi.nlm.nih.gov/2679306/") == {
            "pmid": "2679306"
        }

    def test_bare_pmid(self):
        assert parse_identifier("2679306") == {"pmid": "2679306"}

    def test_arxiv_url(self):
        assert parse_identifier("https://arxiv.org/abs/2301.12345") == {
            "arxiv_id": "2301.12345"
        }

    def test_bare_arxiv(self):
        assert parse_identifier("2301.12345v2") == {"arxiv_id": "2301.12345v2"}

    def test_title_is_not_an_identifier(self):
        assert parse_identifier(
            "Identification of a contact between arginine-180 of the catabolite gene "
            "activator protein (CAP) and base pair 5 of the DNA site"
        ) is None

    def test_empty_query(self):
        assert parse_identifier("   ") is None


class TestPaperAbstractText:
    def test_strips_whitespace(self):
        assert paper_abstract_text({"abstract": "  DNase footprinting.  "}) == "DNase footprinting."

    def test_missing_or_blank_is_empty(self):
        assert paper_abstract_text({}) == ""
        assert paper_abstract_text({"abstract": "   "}) == ""
        assert paper_abstract_text({"abstract": None}) == ""


class TestPaperExternalUrl:
    def test_doi_wins_over_pmid(self):
        assert paper_external_url({
            "doi": "10.1093/nar/17.18.7293",
            "pmid": "2679306",
        }) == "https://doi.org/10.1093/nar/17.18.7293"

    def test_pmid_when_no_doi(self):
        assert paper_external_url({"pmid": 2679306}) == (
            "https://pubmed.ncbi.nlm.nih.gov/2679306"
        )

    def test_arxiv(self):
        assert paper_external_url({"arxiv_id": "arxiv:2301.12345"}) == (
            "https://arxiv.org/abs/2301.12345"
        )

    def test_http_url_fallback(self):
        assert paper_external_url({
            "url": "https://example.org/paper"
        }) == "https://example.org/paper"

    def test_firestore_id_is_not_a_url(self):
        assert paper_external_url({"paper_id": "pubmed_2679306"}) is None


class TestPodcastCategoryForPaper:
    def test_discipline_biology(self):
        assert podcast_category_for_paper({"discipline": "biology"}) == "Biology"

    def test_discipline_computer_science(self):
        assert podcast_category_for_paper(
            {"discipline": "computer_science"}
        ) == "Computer Science"

    def test_glmp_without_discipline_is_biology(self):
        assert podcast_category_for_paper({}, cited_project="glmp") == "Biology"

    def test_unknown_without_glmp_keeps_legacy_default(self):
        assert podcast_category_for_paper({}) == "Computer Science"

    def test_discipline_wins_over_glmp_default(self):
        assert podcast_category_for_paper(
            {"discipline": "chemistry"}, cited_project="glmp"
        ) == "Chemistry"


class TestUnambiguousGenerationMatch:
    one = [{"paper_id": "p1"}]
    two = [{"paper_id": "p1"}, {"paper_id": "p2"}]

    def test_identifier_is_enough(self):
        assert is_unambiguous_generation_match("identifier", self.one) is True

    def test_single_exact_title_is_enough(self):
        assert is_unambiguous_generation_match("exact_title", self.one) is True

    def test_duplicate_exact_title_is_not(self):
        assert is_unambiguous_generation_match("exact_title", self.two) is False

    def test_text_search_never_generates_even_with_one_hit(self):
        assert is_unambiguous_generation_match("text_search", self.one) is False

    def test_wrong_project_and_not_found_are_rejected(self):
        assert is_unambiguous_generation_match("identifier_wrong_project", self.one) is False
        assert is_unambiguous_generation_match("identifier_not_found", []) is False
        assert is_unambiguous_generation_match("exact_title_wrong_project", self.one) is False
