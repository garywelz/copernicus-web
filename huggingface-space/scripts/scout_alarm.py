#!/usr/bin/env python3
"""Open one GitHub issue when a scout source has stalled, or the status file is old.

Reads the public knowledge-engine-status.json. No mailer and no stored credential:
`gh` uses the workflow's built-in GITHUB_TOKEN. An issue that is already open for
the same alarm-key is left alone. Closing it is what allows a later failure to
open a new one.

    python scripts/scout_alarm.py --dry-run
    python scripts/scout_alarm.py
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import urllib.request
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence

SCRIPTS = Path(__file__).resolve().parent
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import scout_acquire_counts as counts  # noqa: E402

LABEL = "scout-alarm"


def fetch_status(url: str, timeout: int = 30) -> Dict[str, Any]:
    request = urllib.request.Request(url, headers={"Accept": "application/json"})
    with urllib.request.urlopen(request, timeout=timeout) as response:
        data = json.loads(response.read().decode("utf-8"))
    if not isinstance(data, dict):
        raise ValueError("status file is not a JSON object")
    return data


def pending_problems(problems: Sequence[Dict[str, str]], open_keys: Sequence[str]) -> List[Dict[str, str]]:
    open_set = set(open_keys)
    return [item for item in problems if item["key"] not in open_set]


def issue_body(problem: Dict[str, str]) -> str:
    detail = problem.get("detail") or ""
    return (
        f"alarm-key: {problem['key']}\n\n"
        f"{problem['sentence']}\n\n"
        f"{detail}\n\n"
        f"Status file: {counts.STATUS_URL}\n\n"
        "This is the only open issue for this problem. Close it when the source "
        "has recovered. A later failure opens a new issue.\n"
    )


def _gh(args: List[str], check: bool = True) -> subprocess.CompletedProcess:
    repo = os.environ.get("GITHUB_REPOSITORY", "")
    command = ["gh", *args]
    if repo and "--repo" not in args:
        command.extend(["--repo", repo])
    return subprocess.run(command, check=check, capture_output=True, text=True)


def open_alarm_keys() -> List[str]:
    result = _gh([
        "issue", "list",
        "--state", "open",
        "--label", LABEL,
        "--limit", "50",
        "--json", "body",
    ])
    keys = []
    for issue in json.loads(result.stdout or "[]"):
        body = issue.get("body") or ""
        for line in body.splitlines():
            if line.startswith("alarm-key:"):
                keys.append(line.split(":", 1)[1].strip())
    return keys


def ensure_label() -> None:
    listed = _gh(["label", "list", "--limit", "100", "--json", "name"], check=False)
    names = []
    if listed.returncode == 0 and listed.stdout.strip():
        names = [item.get("name") for item in json.loads(listed.stdout)]
    if LABEL in names:
        return
    _gh([
        "label", "create", LABEL,
        "--color", "B60205",
        "--description", "A scout source acquired nothing, or the status file is stale",
    ], check=False)


def open_issue(problem: Dict[str, str]) -> None:
    body_path = Path(os.environ.get("RUNNER_TEMP", ".")) / f"scout-alarm-{problem['key']}.md"
    body_path.write_text(issue_body(problem), encoding="utf-8")
    _gh([
        "issue", "create",
        "--label", LABEL,
        "--title", f"[scout] {problem['sentence']}",
        "--body-file", str(body_path),
    ])


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Open a GitHub issue when a scout source has stalled")
    parser.add_argument("--dry-run", action="store_true", help="Print the problems. Open nothing.")
    parser.add_argument("--status-url", default=counts.STATUS_URL)
    parser.add_argument("--status-file", type=Path, default=None, help="Read a local JSON instead of the public URL")
    args = parser.parse_args(argv)

    if args.status_file:
        status = json.loads(args.status_file.read_text(encoding="utf-8"))
    else:
        try:
            status = fetch_status(args.status_url)
        except Exception as exc:
            status = {}
            print(f"status file unreadable: {exc}", file=sys.stderr)

    now = datetime.now(counts.NEW_YORK)
    problems = counts.alarm_problems(status if isinstance(status, dict) else {}, now)
    if args.dry_run:
        if not problems:
            print("no scout alarm")
            return 0
        for problem in problems:
            print(f"{problem['key']}: {problem['sentence']}")
        return 0

    ensure_label()
    already = open_alarm_keys()
    to_open = pending_problems(problems, already)
    if not to_open:
        print("no new scout alarm")
        return 0
    for problem in to_open:
        print(f"opening {problem['key']}")
        open_issue(problem)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
