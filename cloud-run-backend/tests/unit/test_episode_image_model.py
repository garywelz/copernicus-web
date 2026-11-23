"""The episode image model is pinned, and a refusal says what the service said.

Every run asked for "gpt-image-1" and every request came back 400. The handler logged `status_code: 400` and nothing else, so the cause sat
unread for weeks while every episode fell back to the same series artwork and the feed showed one repeating image. Reproducing the request
answered it in one line: "The model 'gpt-image-1' does not exist." - the model had been retired, and the account offers gpt-image-1-mini,
gpt-image-1.5, gpt-image-2 and the gpt-image-2.5/2.6 families instead.

No test here calls the service: an image costs money and CI must not spend it. These check the request this code would make and what it
writes down when the answer is not 200.
"""
import re
from pathlib import Path

# The module imports psutil, which the service has and this environment need not, so the source is read rather than imported. Every
# assertion here is about the request this code makes, which the text shows exactly.
BACKEND = Path(__file__).resolve().parents[2]
SOURCE = (BACKEND / "services" / "podcast_generation_service.py").read_text(encoding="utf-8")
CONSTANTS = (BACKEND / "config" / "constants.py").read_text(encoding="utf-8")
ATTEMPTS = (BACKEND / "content_fixes.py").read_text(encoding="utf-8")
PINNED = re.search(r'EPISODE_IMAGE_MODEL = os\.getenv\("EPISODE_IMAGE_MODEL", "([^"]+)"\)', CONSTANTS).group(1)


def test_the_model_is_pinned_to_a_dated_version():
    assert PINNED == "gpt-image-2-2026-04-21"
    assert re.fullmatch(r"gpt-image-[\d.]+(?:-mini)?-\d{4}-\d{2}-\d{2}", PINNED), \
        "a dated version, so a retirement cannot happen under us"


def test_the_retired_model_is_gone_from_every_request_site():
    """It was in two places: the episode images and the thumbnail attempts."""
    for name, text in (("the service", SOURCE), ("the thumbnail attempts", ATTEMPTS)):
        assert '"gpt-image-1"' not in text, f"{name} still asks for the retired model"


def test_the_thumbnail_attempts_use_the_pinned_model():
    assert "EPISODE_IMAGE_MODEL" in ATTEMPTS and "EPISODE_IMAGE_MODEL_CHEAP" in ATTEMPTS
    assert ATTEMPTS.count("EPISODE_IMAGE_MODEL,") >= 2, "the first two attempts"


def test_one_place_decides_the_model():
    assert "EPISODE_IMAGE_MODEL" in CONSTANTS, "read from config.constants, so both sites agree"


def test_the_request_uses_the_pinned_model_and_keeps_the_size_and_quality():
    """The size and quality were never the problem: the same request with an available model returned 200."""
    block = SOURCE.split('"model": EPISODE_IMAGE_MODEL,', 1)[1].split("}", 1)[0]
    assert '"size": "1536x1024"' in block and '"quality": "medium"' in block and '"n": 1' in block


def test_a_refusal_logs_the_body_at_error_level():
    block = SOURCE.split("Episode image request refused", 1)[1][:600]
    assert "body=response.text[:1000]" in block, "the body, not only the status code"
    assert "status_code=response.status_code" in block and "model=EPISODE_IMAGE_MODEL" in block
    assert "structured_logger.error(\"Episode image request refused\"" in SOURCE, "an error, not a passing warning"


def test_the_key_is_never_logged():
    """The request carries a bearer token; nothing about it may reach a log line."""
    for line in SOURCE.splitlines():
        if "structured_logger" in line and ("api_key" in line or "Authorization" in line or "Bearer" in line):
            raise AssertionError(f"a log line touches the credential: {line.strip()}")
    assert "openai_api_key" not in SOURCE.split("Episode image request refused", 1)[1][:600]


def test_the_model_can_be_overridden_without_a_deploy():
    """An override exists for the next retirement, so a dated pin is not a trap."""
    assert 'os.getenv("EPISODE_IMAGE_MODEL"' in CONSTANTS
