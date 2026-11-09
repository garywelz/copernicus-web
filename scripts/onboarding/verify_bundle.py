#!/usr/bin/env python3
"""Re-verify an engine_onboarding_bundle against a LOCAL clone of the engine's repository, before anyone opens a pull request from it
(docs/design/ENGINE_ONBOARDING_FORM.md 5.2 option (ii), 5.3).

    python scripts/onboarding/verify_bundle.py BUNDLE.json CLONE_DIR [--apply] [--branch main] [--deny-name NAME ...]

CHECKS (all are run and reported; the exit code is the worst result):
  1. the bundle is an engine_onboarding_bundle v1 with safe, relative file paths, and its own checks (public_safe) are all true;
  2. every proposed_sha256 matches its proposed_content;
  3. the clone's `main` tip equals base.commit_sha. If it does not, the REGENERATED DIFF (each proposed file against the clone's current main) is printed and
     the script exits 1: the agent shows Gary the difference before anything else (design 6.3);
  4. every base_blob_sha equals git's blob sha of that file on the clone's main (an `add` must not exist there yet);
  5. docs/research_focus.json parses with the A2 fields, a docs/seeds.csv parses with its header, and no email-shaped string is in any proposed file: the SAME
     linter the server ran (cloud-run-backend/utils/onboarding_lint.py, loaded from this checkout by path). Names cannot be checked without the owners' names, which
     only the server has; pass --deny-name for each name that must not appear.

WRITES NOTHING to the clone unless --apply, and then only after every check passed: --apply writes the proposed files into the WORKING TREE (no commit, no push, no
branch, no network); a file with uncommitted changes in the clone is refused. The agent reviews the result and commits under the usual rules.

EXIT CODES:  0 verified (and applied, if --apply)   1 verification failed or the base moved (nothing was written)   2 usage, unreadable bundle or not a git clone
"""
import argparse
import difflib
import hashlib
import importlib.util
import json
import re
import subprocess
import sys
from pathlib import Path

PATH_RE = re.compile(r"^[A-Za-z0-9_][A-Za-z0-9_./-]*$")
LINT = Path(__file__).resolve().parents[2] / "cloud-run-backend" / "utils" / "onboarding_lint.py"


def git(clone, *args, check=False):
    return subprocess.run(["git", "-C", str(clone), *args], capture_output=True, text=True, encoding="utf-8", check=check)


def load_lint():
    spec = importlib.util.spec_from_file_location("onboarding_lint", LINT)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def safe_path(p):
    return isinstance(p, str) and bool(PATH_RE.match(p)) and ".." not in p.split("/") and not p.startswith(".git") and "//" not in p


def main(argv=None):
    ap = argparse.ArgumentParser(description="Re-verify a change bundle against a local clone (see the module docstring).")
    ap.add_argument("bundle")
    ap.add_argument("clone")
    ap.add_argument("--apply", action="store_true", help="write the proposed files into the working tree (no commit)")
    ap.add_argument("--branch", default="main")
    ap.add_argument("--deny-name", action="append", default=[], help="a name that must not appear in any proposed file (repeatable)")
    args = ap.parse_args(argv)
    try:
        bundle = json.loads(Path(args.bundle).read_text(encoding="utf-8"))
        assert bundle["format"] == "engine_onboarding_bundle" and bundle["version"] == 1 and isinstance(bundle["files"], list)
        base, files = bundle["base"], bundle["files"]
    except Exception as e:                                     # noqa: BLE001
        print(f"ERROR: not a readable engine_onboarding_bundle v1 ({type(e).__name__})", file=sys.stderr)
        return 2
    clone = Path(args.clone)
    if git(clone, "rev-parse", "--is-inside-work-tree").stdout.strip() != "true":
        print(f"ERROR: {clone} is not a git clone", file=sys.stderr)
        return 2

    failures = []

    def fail(msg):
        failures.append(msg)
        print("FAIL:", msg)

    if not all(safe_path(f.get("path")) for f in files):
        print("FAIL: a file path is absolute, climbs out of the repository, or touches .git; nothing else was checked")
        return 1
    if not (bundle.get("checks") or {}).get("public_safe") or not all((bundle.get("checks") or {}).get(k) for k in ("no_email", "no_not_yet_public", "names_ok", "schema_ok")):
        fail("the bundle's own checks are not all true (it is blocked)")
    for f in files:
        if hashlib.sha256(f.get("proposed_content", "").encode("utf-8")).hexdigest() != f.get("proposed_sha256"):
            fail(f"{f['path']}: proposed_sha256 does not match proposed_content")

    tip = git(clone, "rev-parse", "--verify", args.branch + "^{commit}").stdout.strip()
    moved = not base.get("commit_sha") or tip != base.get("commit_sha")
    if not tip:
        fail(f"the clone has no branch {args.branch}")
    elif moved:
        fail(f"the clone's {args.branch} is {tip[:12]}, the bundle was made against {str(base.get('commit_sha'))[:12]}: the base moved. Regenerated diff follows")
        for f in files:
            cur = git(clone, "show", f"{tip}:{f['path']}").stdout if git(clone, "cat-file", "-e", f"{tip}:{f['path']}").returncode == 0 else ""
            sys.stdout.writelines(difflib.unified_diff(cur.splitlines(True), f["proposed_content"].splitlines(True), f"a/{f['path']}", f"b/{f['path']}"))
    else:
        for f in files:
            exists = git(clone, "cat-file", "-e", f"{tip}:{f['path']}").returncode == 0
            blob = git(clone, "rev-parse", f"{tip}:{f['path']}").stdout.strip() if exists else None
            if f["action"] == "modify" and blob != f.get("base_blob_sha"):
                fail(f"{f['path']}: the base file changed (blob {str(blob)[:12]}, the bundle expects {str(f.get('base_blob_sha'))[:12]})")
            if f["action"] == "add" and exists:
                fail(f"{f['path']}: the bundle adds this file but it already exists on {args.branch}")
            if f["action"] not in ("add", "modify"):
                fail(f"{f['path']}: unknown action")

    result = load_lint().run_checks(files, [{"naming": "role", "name": n} for n in args.deny_name], [])
    for name, reasons in result["problems"].items():
        for r in reasons:
            fail(f"{name}: {r}")

    if failures:
        print(f"NOT VERIFIED: {len(failures)} problem(s). Nothing was written.")
        return 1
    print(f"VERIFIED: {len(files)} file(s) against {args.branch} {tip[:12]}; sha256 and blob shas match; the linter passes.")
    if args.apply:
        dirty = [f["path"] for f in files if git(clone, "status", "--porcelain", "--", f["path"]).stdout.strip()]
        if dirty:
            print("REFUSED: these files have uncommitted changes in the clone: " + ", ".join(dirty) + ". Nothing was written.")
            return 1
        for f in files:
            target = clone / f["path"]
            target.parent.mkdir(parents=True, exist_ok=True)
            with open(target, "w", encoding="utf-8", newline="") as fh:
                fh.write(f["proposed_content"])
        print(f"APPLIED to the working tree of {clone} (no commit, no push). Review with `git diff`, then commit under the usual rules.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
