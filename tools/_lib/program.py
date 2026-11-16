"""Resolve command line programs to something the OS can actually spawn."""

from __future__ import annotations

import shutil


def resolve_program(program: str) -> str:
    """Return the path of `program` as it can actually be spawned.

    On Windows `npm` ships as a batch shim (`npm.cmd`). `CreateProcess` only
    appends `.exe` to a bare program name and never consults `PATHEXT`, so
    spawning `"npm"` fails with `[WinError 2] The system cannot find the file
    specified` even though `shutil.which("npm")` finds the shim. Resolving the
    program first hands the spawn call a real file. On POSIX the resolved path
    is the same program the bare name already found.
    """
    return shutil.which(program) or program
