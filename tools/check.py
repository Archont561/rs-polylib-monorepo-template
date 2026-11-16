"""Composite offline repository quality gate."""

from __future__ import annotations

from tasknest import tool


@tool(
    depends=(
        "repo.alint",
        "repo.policy",
        "docs.check",
        "repo.sandbox",
        "repo.format",
        "python.lint",
        "ts.lint",
        "docs.md",
        "repo.gherkin",
        "docs.links",
        "docs.prose",
        "repo.actions",
    ),
    marks=("ci",),
    description="Run all offline repository policy, docs, formatting, and lint checks.",
)
def check() -> None:
    """Run all offline quality gates declared in `depends`."""
