"""Read-only sanity check: run validate_description_before_publish over the
current description_markdown of every live Firestore episode. All should
pass. Any failure is reported by episode id -- it means either a false
positive in the validator, or genuinely missed content that should have
been caught by today's cleanup (bulletin entry 008) or the generator
fixes in this PR.

This test only reads Firestore; it never writes anything. It requires
`gcloud auth print-access-token` to succeed (application-default or user
credentials for the regal-scholar-453620-r7 project) and network access;
it skips itself cleanly when neither is available, so a normal `pytest`
run with no cloud credentials configured is unaffected.
"""
import json
import subprocess
import urllib.request
import urllib.error

import pytest

from content_fixes import validate_description_before_publish, DescriptionValidationError

PROJECT_ID = "regal-scholar-453620-r7"
DATABASE_ID = "copernicusai"
EXCLUDED_DOC_IDS = {
    "news-bio-28032025", "news-chem-28032025", "news-compsci-28032025",
    "news-math-28032025", "news-phys-28032025",
}


def _get_access_token():
    try:
        result = subprocess.run(
            ["gcloud", "auth", "print-access-token"],
            capture_output=True, text=True, timeout=15, shell=True,
        )
    except Exception:
        return None
    if result.returncode != 0:
        return None
    token = result.stdout.strip()
    return token or None


def _fetch_all_episodes(token):
    base = (
        f"https://firestore.googleapis.com/v1/projects/{PROJECT_ID}"
        f"/databases/{DATABASE_ID}/documents/episodes"
    )
    docs = []
    page_token = None
    while True:
        url = base + "?pageSize=100"
        if page_token:
            url += "&pageToken=" + page_token
        req = urllib.request.Request(url, headers={"Authorization": f"Bearer {token}"})
        with urllib.request.urlopen(req, timeout=30) as resp:
            data = json.load(resp)
        docs.extend(data.get("documents", []))
        page_token = data.get("nextPageToken")
        if not page_token:
            break
    return docs


@pytest.mark.integration
def test_validator_passes_on_every_live_episode_description():
    token = _get_access_token()
    if not token:
        pytest.skip("No gcloud credentials available -- skipping live Firestore check.")

    try:
        docs = _fetch_all_episodes(token)
    except (urllib.error.URLError, OSError) as e:
        pytest.skip(f"Could not reach Firestore -- skipping live check ({e}).")

    failures = []
    checked = 0
    for doc in docs:
        doc_id = doc["name"].rsplit("/", 1)[-1]
        if doc_id in EXCLUDED_DOC_IDS:
            continue
        fields = doc.get("fields", {})
        for field_name in ("description_markdown", "description_html"):
            text = fields.get(field_name, {}).get("stringValue", "")
            if not text:
                continue
            checked += 1
            try:
                validate_description_before_publish(text)
            except DescriptionValidationError as e:
                failures.append((doc_id, field_name, str(e)))

    if failures:
        detail = "\n".join(f"  {doc_id} [{field}]: {msg}" for doc_id, field, msg in failures)
        pytest.fail(
            f"{len(failures)} of {checked} live description fields failed "
            f"validation (should be 0):\n{detail}"
        )
