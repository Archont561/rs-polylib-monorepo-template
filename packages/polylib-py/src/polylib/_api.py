"""Typed Python wrapper over the compiled `polylib._native` PyO3 extension."""

from __future__ import annotations

from typing import TYPE_CHECKING

from polylib import _native

if TYPE_CHECKING:
    from collections.abc import Sequence

VERSION: str = _native.VERSION
__version__: str = VERSION
ScoreSummary = _native.ScoreSummary


class PolylibError(ValueError):
    """Typed error raised when `polylib-core` rejects an invalid input."""

    def __init__(self, code: str, message: str) -> None:
        """Create a typed error carrying the cross-language conformance error code."""
        super().__init__(message)
        self.code = code


def _wrap_value_error(error: ValueError) -> PolylibError:
    raw = str(error)
    code, separator, detail = raw.partition(": ")
    if separator:
        return PolylibError(code=code, message=detail)
    return PolylibError(code="invalid_input", message=raw)


def normalize_slug(text: str) -> str:
    """Normalize free-form text into a lowercase hyphen-separated ASCII slug."""
    try:
        return _native.normalize_slug(text)
    except ValueError as err:
        raise _wrap_value_error(err) from err


def summarize_scores(values: Sequence[float]) -> ScoreSummary:
    """Compute summary statistics over a non-empty sequence of finite scores."""
    try:
        return _native.summarize_scores(list(values))
    except ValueError as err:
        raise _wrap_value_error(err) from err
