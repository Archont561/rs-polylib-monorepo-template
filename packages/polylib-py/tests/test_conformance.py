"""Shared Gherkin conformance suite (`conformance/*.feature`) executed via `pytest-bdd`."""

from __future__ import annotations

import math
from pathlib import Path
from typing import Any

import pytest
from pytest_bdd import given, parsers, scenarios, then, when

import polylib

_CONFORMANCE_DIR = Path(__file__).resolve().parents[3] / "conformance"
_TOLERANCE = 1e-12

scenarios(str(_CONFORMANCE_DIR / "slug.feature"))
scenarios(str(_CONFORMANCE_DIR / "scores.feature"))


@pytest.fixture
def conformance_state() -> dict[str, Any]:
    """Per-scenario state for cross-language conformance steps."""
    return {}


@given(parsers.parse('the raw slug input "{raw_input}"'))
def step_given_slug_input(conformance_state: dict[str, Any], raw_input: str) -> None:
    """Capture raw slug input from a conformance example row."""
    conformance_state["raw_input"] = raw_input


@given("an empty slug input")
def step_given_empty_slug_input(conformance_state: dict[str, Any]) -> None:
    """Capture an empty slug input string."""
    conformance_state["raw_input"] = ""


@when("I normalize the slug")
def step_when_normalize_slug(conformance_state: dict[str, Any]) -> None:
    """Execute `polylib.normalize_slug`, recording either value or `PolylibError`."""
    try:
        conformance_state["slug"] = polylib.normalize_slug(conformance_state["raw_input"])
        conformance_state["slug_error"] = None
    except polylib.PolylibError as err:
        conformance_state["slug"] = None
        conformance_state["slug_error"] = err


@then(parsers.parse('the normalized slug should be "{expected}"'))
def step_then_slug_equals(conformance_state: dict[str, Any], expected: str) -> None:
    """Assert normalized slug matches the conformance expectation."""
    assert conformance_state["slug_error"] is None
    assert conformance_state["slug"] == expected


@then(parsers.parse('slug normalization should fail with error code "{error_code}"'))
def step_then_slug_fails(conformance_state: dict[str, Any], error_code: str) -> None:
    """Assert slug normalization raised a `PolylibError` with the expected code."""
    err = conformance_state["slug_error"]
    assert isinstance(err, polylib.PolylibError)
    assert err.code == error_code


@given(parsers.parse('the score list "{values}"'))
def step_given_score_list(conformance_state: dict[str, Any], values: str) -> None:
    """Parse comma-separated numeric scores from a conformance example row."""
    conformance_state["scores"] = [float(item.strip()) for item in values.split(",")]


@given("an empty score list")
def step_given_empty_score_list(conformance_state: dict[str, Any]) -> None:
    """Store an empty score sequence."""
    conformance_state["scores"] = []


@when("I summarize the scores")
def step_when_summarize_scores(conformance_state: dict[str, Any]) -> None:
    """Execute `polylib.summarize_scores`, recording either summary or `PolylibError`."""
    try:
        conformance_state["summary"] = polylib.summarize_scores(conformance_state["scores"])
        conformance_state["score_error"] = None
    except polylib.PolylibError as err:
        conformance_state["summary"] = None
        conformance_state["score_error"] = err


@then(
    parsers.parse(
        "the summary should have count {count:d}, min {min_val:f}, "
        "max {max_val:f}, and mean {mean_val:f}"
    )
)
def step_then_summary_stats(
    conformance_state: dict[str, Any],
    count: int,
    min_val: float,
    max_val: float,
    mean_val: float,
) -> None:
    """Assert computed summary statistics match the conformance expectation."""
    assert conformance_state["score_error"] is None
    summary = conformance_state["summary"]
    assert summary.count == count
    assert math.isclose(summary.min, min_val, abs_tol=_TOLERANCE)
    assert math.isclose(summary.max, max_val, abs_tol=_TOLERANCE)
    assert math.isclose(summary.mean, mean_val, abs_tol=_TOLERANCE)


@then(parsers.parse('score summarization should fail with error code "{error_code}"'))
def step_then_score_fails(conformance_state: dict[str, Any], error_code: str) -> None:
    """Assert score summarization raised a `PolylibError` with the expected code."""
    err = conformance_state["score_error"]
    assert isinstance(err, polylib.PolylibError)
    assert err.code == error_code
