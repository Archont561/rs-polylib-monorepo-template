"""Composite polyglot package compatibility verification."""

from __future__ import annotations

from tasknest import tool


@tool(
    depends=("rust.compat", "python.compat", "ts.compat"),
    marks=("ci", "compat"),
    description="Run Rust, Python, and TypeScript/npm compatibility gates.",
)
def compat() -> None:
    """Run all core ecosystem compatibility suites declared in `depends`."""
