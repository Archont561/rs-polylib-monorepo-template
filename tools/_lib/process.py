"""Shared subprocess helpers for Python Tasknest tools."""

from __future__ import annotations

import subprocess
from dataclasses import dataclass
from typing import TYPE_CHECKING

from tasknest import ToolError

if TYPE_CHECKING:
    from collections.abc import Mapping, Sequence
    from pathlib import Path


@dataclass(frozen=True)
class CommandSpec:
    """Subprocess invocation parameters."""

    argv: Sequence[str]
    cwd: Path
    env: Mapping[str, str] | None = None


def run_ok(argv: Sequence[str], cwd: Path, *, env: Mapping[str, str] | None = None) -> bool:
    """Run a command, echoing its invocation, and return True when exit code is zero."""
    return run_spec_ok(CommandSpec(argv=argv, cwd=cwd, env=env))


def run_spec_ok(spec: CommandSpec) -> bool:
    """Run a CommandSpec, echoing its invocation, and return True on zero exit."""
    print("+ " + " ".join(spec.argv), flush=True)
    completed = subprocess.run(spec.argv, cwd=spec.cwd, env=spec.env, check=False)
    return completed.returncode == 0


def run_checked(argv: Sequence[str], cwd: Path, *, env: Mapping[str, str] | None = None) -> None:
    """Run a command and raise ToolError when exit code is non-zero."""
    if not run_spec_ok(CommandSpec(argv=argv, cwd=cwd, env=env)):
        raise ToolError(f"Command failed: {' '.join(argv)}")


def run_capture(spec: CommandSpec) -> subprocess.CompletedProcess[str]:
    """Run a CommandSpec and capture UTF-8 stdout/stderr without raising."""
    return subprocess.run(
        spec.argv,
        cwd=spec.cwd,
        env=spec.env,
        capture_output=True,
        text=True,
        check=False,
    )
