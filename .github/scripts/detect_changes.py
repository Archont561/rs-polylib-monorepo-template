#!/usr/bin/env python3
"""Report which parts of the repository a change touches.

The workflow-level `paths` key answers a single question for the whole
workflow: should any of it run. GitHub offers no per-job equivalent, so the
jobs that a change cannot affect are gated on the outputs this script writes
instead. Skipping a job that way still reports a status for it, which a
workflow-level filter does not, so a required check never sits pending.

Usage:
    detect_changes.py --profile ci [--filters PATH] [--changed PATH]

The `changed` file is a newline-separated list of paths. When it is omitted the
script computes it from the pull-request or push that triggered the run.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
from pathlib import Path


def to_regex(pattern: str) -> re.Pattern[str]:
    """Translate a workflow path-filter pattern into a regular expression.

    `**` crosses directory boundaries, `*` and `?` stop at one, which is what
    the workflow-level `paths` filter accepts.
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


def changed_paths() -> list[str]:
    """Return the paths a pull request or push changed."""
    base = os.environ.get("PR_BASE_SHA") or ""
    head = os.environ.get("PR_HEAD_SHA") or ""
    before = os.environ.get("PUSH_BEFORE_SHA") or ""

    if not base:
        if before and set(before) != {"0"}:
            base = before
        else:
            base = "HEAD~1"

    if not head:
        head = "HEAD"

    # The three-dot form compares against the merge base, which is what the
    # workflow-level filter does for a pull request.
    for args in (["git", "diff", "--name-only", f"{base}...{head}"],):
        result = subprocess.run(args, capture_output=True, text=True, check=False)
        if result.returncode == 0:
            return [line.strip() for line in result.stdout.splitlines() if line.strip()]

    result = subprocess.run(
        ["git", "diff", "--name-only", base, head],
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode == 0:
        return [line.strip() for line in result.stdout.splitlines() if line.strip()]

    result = subprocess.run(
        ["git", "diff", "--name-only", "HEAD~1", "HEAD"],
        capture_output=True,
        text=True,
        check=False,
    )
    return [line.strip() for line in result.stdout.splitlines() if line.strip()]


def main() -> int:
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
        changed = [
            line.strip()
            for line in Path(args.changed).read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]
    else:
        changed = changed_paths()

    print("Changed files:")
    for path in changed:
        print(f"  {path}")

    results: dict[str, bool] = {}
    for name, patterns in filters.items():
        if isinstance(patterns, str):
            patterns = [patterns]
        regexes = [to_regex(pattern) for pattern in patterns]
        results[name] = any(
            regex.match(path) for regex in regexes for path in changed
        )

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
