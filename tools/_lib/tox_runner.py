"""Shared helper to run `tox` compatibility matrices for Python and npm."""

from __future__ import annotations

import sys
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from tasknest import ToolContext


def current_python_tox_env(factor: str = "core") -> str:
    """Return the tox environment matching the active Python interpreter (e.g. `py312-core`)."""
    major, minor = sys.version_info[:2]
    return f"py{major}{minor}-{factor}"


def run_tox(
    ctx: ToolContext,
    *,
    env: str = "",
    label: str = "",
    list_only: bool = False,
    skip_missing: bool = False,
) -> None:
    """Invoke `tox` from the repository root with optional env, label, or list mode."""
    argv: list[str] = ["tox"]
    if list_only:
        argv.append("list")
    elif label:
        argv.extend(["-m", label])
    elif env:
        argv.extend(["-e", env])
    if skip_missing and not list_only:
        argv.append("--skip-missing-interpreters=true")
    ctx.run(argv, cwd=ctx.repo_root)
