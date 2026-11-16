"""Unit, property, and Python-specific BDD tests for `polylib`."""

from __future__ import annotations

import math
from pathlib import Path
from typing import Any

import pytest
from hypothesis import given as hypothesis_given
from hypothesis import strategies as st
from pytest_bdd import given, parsers, scenario, then, when

import polylib

_FEATURE_PATH = Path(__file__).resolve().parents[1] / "features" / "python_bindings.feature"
_TOLERANCE = 1e-12


@pytest.fixture
def bdd_state() -> dict[str, Any]:
    """Per-scenario mutable state for pytest-bdd steps."""
    return {}


@scenario(str(_FEATURE_PATH), "Normalize a title through the PyO3 extension")
def test_bdd_normalize_slug() -> None:
    """Execute the slug normalization Gherkin scenario."""


@scenario(str(_FEATURE_PATH), "Summarize scores through the PyO3 extension")
def test_bdd_summarize_scores() -> None:
    """Execute the score summary Gherkin scenario."""


@given(parsers.parse('a raw title "{title}"'))
def step_given_title(bdd_state: dict[str, Any], title: str) -> None:
    """Store raw title for normalization."""
    bdd_state["title"] = title


@when("Python normalizes the title")
def step_when_normalize(bdd_state: dict[str, Any]) -> None:
    """Call `polylib.normalize_slug` via PyO3."""
    bdd_state["slug"] = polylib.normalize_slug(bdd_state["title"])


@then(parsers.parse('the Python slug is "{expected}"'))
def step_then_slug(bdd_state: dict[str, Any], expected: str) -> None:
    """Assert normalized slug matches expected value."""
    assert bdd_state["slug"] == expected


@given(parsers.parse('numeric scores "{raw}"'))
def step_given_scores(bdd_state: dict[str, Any], raw: str) -> None:
    """Parse numeric score sequence."""
    bdd_state["scores"] = [float(item.strip()) for item in raw.split(",")]


@when("Python summarizes the scores")
def step_when_summarize(bdd_state: dict[str, Any]) -> None:
    """Call `polylib.summarize_scores` via PyO3."""
    bdd_state["summary"] = polylib.summarize_scores(bdd_state["scores"])


@then(parsers.parse("the Python summary has count {count:d} and mean {mean:f}"))
def step_then_summary(bdd_state: dict[str, Any], count: int, mean: float) -> None:
    """Assert count and arithmetic mean."""
    summary = bdd_state["summary"]
    assert summary.count == count
    assert math.isclose(summary.mean, mean, abs_tol=_TOLERANCE)


def test_version_exports_match() -> None:
    """Verify Python package version matches the compiled Rust extension version."""
    assert polylib.__version__ == polylib.VERSION
    assert polylib.VERSION


def test_non_finite_scores_raise_typed_error() -> None:
    """Reject NaN and Infinity with the `non_finite_value` conformance code."""
    with pytest.raises(polylib.PolylibError) as exc_info:
        polylib.summarize_scores([1.0, float("nan")])
    assert exc_info.value.code == "non_finite_value"


@pytest.mark.property
@hypothesis_given(st.text(alphabet="abcdefghijklmnopqrstuvwxyz0123456789 _-.", min_size=1))
def test_slug_normalization_is_idempotent(raw: str) -> None:
    """Normalizing an already normalized slug returns the exact same string."""
    try:
        slug = polylib.normalize_slug(raw)
    except polylib.PolylibError:
        return
    assert polylib.normalize_slug(slug) == slug
    assert "--" not in slug
