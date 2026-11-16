#!/usr/bin/env python3
"""Report which parts of the repository a change touches.

The workflow-level `paths` key answers a single question for the whole
workflow: should any of it run. GitHub offers no per-job equivalent, so the
jobs that a change cannot affect are gated on the outputs this script writes
instead. Skipping a job that way still reports a status for it, which a
workflow-level filter does not, so a required check never sits pending.

Usage:
    detect_changes.py --profile ci [--filters PATH] [--changed PATH]

The `changed` file holds one path per line. When it is omitted the script
derives the list from the pull request or push that started the run.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

_GIT = shutil.which("git") or "git"


def to_regex(pattern: str) -> re.Pattern[str]:
    """Translate a workflow path-filter pattern into a regular expression.

    `**` crosses directory boundaries while `*` and `?` stop at one, which is
    what the workflow-level `paths` filter accepts.
    """
    out: list[str] = []
    index = 0
    while index < len(pattern):
        if pattern.startswith("**/", index):
            out.append("(?:.*/)?")
            index += 3
        elif pattern.startswith("**", index):
            out.append(".*")
            index += 2
        elif pattern[index] == "*":
            out.append("[^/]*")
            index += 1
        elif pattern[index] == "?":
            out.append("[^/]")
            index += 1
        else:
            out.append(re.escape(pattern[index]))
            index += 1
    return re.compile("^" + "".join(out) + "$")


def _diff(*args: str) -> list[str] | None:
    """Return the paths a git diff reports, or None when the range is unknown."""
    result = subprocess.run(  # noqa: S603 - fixed argv, no untrusted input
        [_GIT, "diff", "--name-only", *args],
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        return None
    return [line.strip() for line in result.stdout.splitlines() if line.strip()]


def changed_paths() -> list[str]:
    """Return the paths the pull request or push changed."""
    base = os.environ.get("PR_BASE_SHA") or ""
    head = os.environ.get("PR_HEAD_SHA") or ""
    before = os.environ.get("PUSH_BEFORE_SHA") or ""

    if not base:
        base = before if before and set(before) != {"0"} else "HEAD~1"

    if not head:
        head = "HEAD"

    # The three-dot form compares against the merge base, which is what the
    # workflow-level filter does for a pull request.
    for args in ((f"{base}...{head}",), (base, head), ("HEAD~1", "HEAD")):
        paths = _diff(*args)
        if paths is not None:
            return paths
    return []


def main() -> int:
    """Write one output per filter and return the process status."""
    parser = argparse.ArgumentParser()
    parser.add_argument("--profile", required=True, help="Filters section to use.")
    parser.add_argument(
        "--filters",
        default=str(Path(__file__).with_name("filters.json")),
        help="Path to the filters file.",
    )
    parser.add_argument("--changed", help="File with one changed path per line.")
    parser.add_argument(
        "--github-output",
        default=os.environ.get("GITHUB_OUTPUT"),
        help="File that receives the step outputs.",
    )
    args = parser.parse_args()

    filters = json.loads(Path(args.filters).read_text(encoding="utf-8"))[args.profile]

    if args.changed:
        text = Path(args.changed).read_text(encoding="utf-8")
        changed = [line.strip() for line in text.splitlines() if line.strip()]
    else:
        changed = changed_paths()

    print("Changed files:")
    for path in changed:
        print(f"  {path}")

    results: dict[str, bool] = {}
    for name, patterns in filters.items():
        candidates = [patterns] if isinstance(patterns, str) else patterns
        regexes = [to_regex(pattern) for pattern in candidates]
        results[name] = any(regex.match(path) for regex in regexes for path in changed)

    print("Detected:")
    for name, hit in results.items():
        print(f"  {name}={'true' if hit else 'false'}")

    if args.github_output:
        with open(args.github_output, "a", encoding="utf-8") as handle:
            for name, hit in results.items():
                handle.write(f"{name}={'true' if hit else 'false'}\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
