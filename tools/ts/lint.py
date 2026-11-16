"""Lint and type-check TypeScript packages with Biome and TypeScript."""

from __future__ import annotations

from tasknest import ToolContext, tool

_TS_PACKAGES: tuple[str, ...] = ("polylib-wasm", "polylib-js", "polylib-ts")


@tool(
    marks=("fast", "ci", "ts"),
    description="Run Biome checks and TypeScript strict type-checking.",
)
def lint_ts(ctx: ToolContext, fix: bool = False, typecheck: bool = True) -> None:
    """Run Biome across the workspace and optional strict `tsc --noEmit` in TS packages."""
    biome_argv = ["bun", "x", "--bun", "--no-install", "biome", "check"]
    if fix:
        biome_argv.append("--write")
    biome_argv.append(".")
    ctx.run(biome_argv, cwd=ctx.repo_root)
    if typecheck:
        for pkg in _TS_PACKAGES:
            ctx.run(["bun", "run", "typecheck"], cwd=ctx.repo_root / "packages" / pkg)
