"""Composite polyglot test suite."""

from __future__ import annotations

from tasknest import tool


@tool(
    depends=("rust.test", "python.test", "ts.test"),
    marks=("ci",),
    description="Run Rust, Python, and TypeScript tests including shared conformance.",
)
def test() -> None:
    """Run all language test suites declared in `depends`."""
