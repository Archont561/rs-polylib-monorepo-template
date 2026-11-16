"""Validate Conventional Commit messages via convco."""

from __future__ import annotations

import subprocess
from pathlib import Path

from tasknest import ToolContext, ToolError, tool


@tool(
    marks=("fast",),
    description="Validate a commit message file against Conventional Commits using convco.",
)
def commit_msg(ctx: ToolContext, message_file: str) -> None:
    """Check `message_file` via `convco check --from-stdin --strip`."""
    path = Path(message_file)
    if not path.is_absolute():
        path = ctx.repo_root / path
    if not path.exists():
        raise ToolError(f"Commit message file not found: {path}")
    text = path.read_text(encoding="utf-8")
    completed = subprocess.run(
        ["convco", "check", "--from-stdin", "--strip"],
        cwd=ctx.repo_root,
        input=text,
        text=True,
        check=False,
    )
    if completed.returncode != 0:
        raise ToolError("Commit message does not satisfy Conventional Commits (convco).")
