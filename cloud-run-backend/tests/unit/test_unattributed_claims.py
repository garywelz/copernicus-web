"""A claim that credits no source is still a claim.

These cases are the ones the pipeline actually produced on 2026-11-19, when every check passed and the script still asserted a company's
withdrawn manuscript and widened a phage paper to cells.
"""
from types import SimpleNamespace

import pytest

import unattributed_claims as uc
from endpoints.curated import routes as curated_routes


def paper(pid, title, abstract):
    return SimpleNamespace(pid=pid, title=title, abstract=abstract, authors=["A"], year=2026, venue="Science")


PHAGE = [paper("P1", "Generative design of bacteriophages with genome language models",
               "We report the first generative design of complete bacteriophage genomes using genome language models. A cocktail of generated "
               "phages rapidly overcomes phage-resistant Escherichia coli strains.")]


def kinds(violations):
    return sorted(v["kind"] for v in violations)


def test_a_withdrawal_asserted_with_no_record_is_refused():
    script = ("HOST: Overnight, hundreds of new manuscripts appeared.\n"
              "EXPERT: One manuscript was withdrawn within a day of its release because of a sign error in a key step.\n")
    v = uc.check(script, PHAGE)
    assert "withdrawal_without_record" in kinds(v)
    assert "sign error" in v[0]["find"] or "withdrawn" in v[0]["find"]


def test_a_withdrawal_on_record_is_allowed():
    script = "EXPERT: The paper was withdrawn, according to its own record.\n"
    assert uc.check(script, PHAGE, withdrawal_on_record=True) == []


def test_saying_there_is_no_withdrawal_is_not_a_claim_of_one():
    script = "EXPERT: There is no record of any of these papers being withdrawn.\n"
    assert uc.check(script, PHAGE) == []


def test_widening_a_phage_paper_to_cells_is_refused():
    script = "HOST: How does an AI create a functional biological entity like a virus, or even a cell, from digital instructions?\n"
    v = uc.check(script, PHAGE)
    assert kinds(v) == ["scope_widened"]
    assert "cell" in v[0]["message"]


def test_a_term_the_sources_do_use_is_not_widening():
    sources = PHAGE + [paper("P2", "Designed enzymes in human cells", "We express the designed enzymes in human cells and in patient tissue.")]
    script = "EXPERT: The enzymes were expressed in human cells.\n"
    assert uc.check(script, sources) == []


def test_naming_a_company_no_source_names_is_refused():
    script = "EXPERT: OpenAI released these manuscripts as company releases.\n"
    v = uc.check(script, PHAGE)
    assert kinds(v) == ["named_body_without_source"]


def test_a_sentence_the_attribution_check_already_read_is_left_to_it():
    script = "EXPERT: A cocktail of them overcame resistant cells.\n"
    quoted = ["A cocktail of them overcame resistant cells."]
    assert uc.check(script, PHAGE, attributed_quotes=quoted) == []



def test_summary_and_feedback_name_each_kind():
    v = uc.check("EXPERT: One manuscript was withdrawn for a sign error. HOST: Could this work in a cell?\n", PHAGE)
    s = uc.summary(v)
    assert s["passed"] is False and s["count"] >= 1
    assert "withdrawal_without_record" in s["kinds"]
    assert "no listed source" in uc.feedback(v)


def test_feedback_is_none_when_nothing_is_wrong():
    assert uc.feedback([]) is None


# --- what the check-script route reports ------------------------------------------------------------------------------------------
class _Doc:
    def __init__(self, data):
        self._d, self.exists = data, True

    def to_dict(self):
        return self._d


def test_check_script_reports_the_job_outcome_not_the_check_outcome(monkeypatch):
    """The checks passing does not mean an episode exists: job 036f703c passed every check and then failed in research, and the route
    answered passed/generated true, which would have a caller believe an episode had been made."""
    answer = {"passed": True, "status": "pass", "written": "nothing", "generated": False, "published": False}
    failed_job = {"status": "failed", "error": "Research failed: the analysis of an approved source could not be read (P3)",
                  "error_type": "curated_analysis_failed", "result": {}}
    reported = curated_routes._supplied_answer(answer, "job-1", failed_job) if hasattr(curated_routes, "_supplied_answer") else None
    assert reported is not None, "the route must build its answer from the job through a function the tests can call"
    assert reported["generated"] is False
    assert reported["status"] == "failed_after_checks"
    assert reported["written"] == "nothing"
    assert "could not be read" in reported["error"]


def test_check_script_says_where_private_media_actually_is():
    """The answer carried a public URL for a private episode, which 404s; it now carries where the audio really is."""
    done = {"status": "completed", "tts_characters": 6235,
            "result": {"audio_url": "https://storage.googleapis.com/regal-scholar-453620-r7-podcast-storage/audio/ever-bio-260014.mp3",
                       "canonical_filename": "ever-bio-260014", "media_state": "private"}}
    reported = curated_routes._supplied_answer({"passed": True}, "job-3", done)
    assert reported["media_state"] == "private"
    assert reported["audio_location"] == "gs://regal-scholar-453620-r7-private-media/audio/ever-bio-260014.mp3"


def test_check_script_keeps_the_public_address_once_an_episode_is_public():
    done = {"status": "completed",
            "result": {"audio_url": "https://storage.googleapis.com/regal-scholar-453620-r7-podcast-storage/audio/ever-bio-260013.mp3",
                       "canonical_filename": "ever-bio-260013", "media_state": "public"}}
    reported = curated_routes._supplied_answer({"passed": True}, "job-4", done)
    assert reported["audio_location"].startswith("https://storage.googleapis.com/")


def test_a_real_episode_is_reported_as_generated():
    done = {"status": "completed", "tts_characters": 6235,
            "result": {"audio_url": "https://storage.googleapis.com/regal-scholar-453620-r7-podcast-storage/audio/ever-bio-260014.mp3",
                       "canonical_filename": "ever-bio-260014"}}
    reported = curated_routes._supplied_answer({"passed": True}, "job-2", done)
    assert reported["generated"] is True and reported["status"] == "pass"
    assert reported["canonical_filename"] == "ever-bio-260014" and reported["tts_characters"] == 6235
    assert "error" not in reported


# --- where private media really is --------------------------------------------------------------------------------------------------
def test_a_private_record_does_not_hand_out_a_public_url():
    import media_store
    rec = {"audio_url": "https://storage.googleapis.com/regal-scholar-453620-r7-podcast-storage/audio/ever-bio-260012.mp3",
           "media_state": "private"}
    uri = media_store.media_uri(rec)
    assert uri == "gs://regal-scholar-453620-r7-private-media/audio/ever-bio-260012.mp3"
    assert "storage.googleapis.com" not in uri


def test_a_public_record_keeps_its_public_url():
    import media_store
    url = "https://storage.googleapis.com/regal-scholar-453620-r7-podcast-storage/audio/ever-bio-260013.mp3"
    assert media_store.media_uri({"audio_url": url, "media_state": "public"}) == url


def test_private_uri_names_the_private_bucket():
    import media_store
    assert media_store.private_uri("audio/x.mp3") == "gs://regal-scholar-453620-r7-private-media/audio/x.mp3"


@pytest.mark.parametrize("field", ["audio_url", "transcript_url", "thumbnail_url"])
def test_media_uri_works_for_every_media_field(field):
    import media_store
    rec = {field: f"https://storage.googleapis.com/regal-scholar-453620-r7-podcast-storage/x/{field}.bin", "media_state": "private"}
    assert media_store.media_uri(rec, field).startswith("gs://regal-scholar-453620-r7-private-media/")
