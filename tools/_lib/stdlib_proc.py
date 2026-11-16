"""Pure-stdlib subprocess helpers for compatibility checks (usable inside isolated tox envs)."""

from __future__ import annotations

import subprocess
from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Mapping, Sequence
    from pathlib import Path


@dataclass(frozen=True)
class StdlibCommand:
    """Subprocess invocation parameters."""

    argv: Sequence[str]
    cwd: Path
    env: Mapping[str, str] | None = None


def run_ok(argv: Sequence[str], cwd: Path, *, env: Mapping[str, str] | None = None) -> bool:
    """Run a command, echoing its invocation, and return True on zero exit."""
    print("+ " + " ".join(argv), flush=True)
    completed = subprocess.run(argv, cwd=cwd, env=env, check=False)
    return completed.returncode == 0


def run_checked(argv: Sequence[str], cwd: Path, *, env: Mapping[str, str] | None = None) -> None:
    """Run a command and raise RuntimeError when exit code is non-zero."""
    if not run_ok(argv, cwd, env=env):
        raise RuntimeError(f"Command failed: {' '.join(argv)}")


def run_capture(spec: StdlibCommand) -> subprocess.CompletedProcess[str]:
    """Run a command and capture UTF-8 stdout/stderr without raising."""
    return subprocess.run(
        spec.argv,
        cwd=spec.cwd,
        env=spec.env,
        capture_output=True,
        text=True,
        check=False,
    )
