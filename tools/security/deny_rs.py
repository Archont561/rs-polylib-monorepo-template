"""Run cargo-deny dependency policy checks."""

from __future__ import annotations

from tasknest import ToolContext, tool

_DEFAULT_OFFLINE_TARGET = "x86_64-unknown-linux-gnu"


@tool(
    marks=("security", "rust"),
    description="Run cargo-deny (bans, licenses, sources, and optionally online advisories).",
)
def deny_rs(
    ctx: ToolContext,
    online: bool = False,
    target: str = _DEFAULT_OFFLINE_TARGET,
) -> None:
    """Check Cargo dependency policy via `cargo-deny`."""
    if online:
        ctx.run(["cargo", "deny", "check"], cwd=ctx.repo_root)
        return
    # Offline Linux CI and sandboxes only ship Linux-target crates; online security scans retain
    # the full target matrix declared in deny.toml.
    argv = ["cargo", "deny", "--offline"]
    if target:
        argv.extend(["--target", target])
    argv.extend(["check", "bans", "licenses", "sources"])
    ctx.run(argv, cwd=ctx.repo_root)
