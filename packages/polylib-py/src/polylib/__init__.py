"""Public Python facade for `polylib`, powered by the `polylib-core` Rust extension."""

from polylib._api import (
    VERSION,
    PolylibError,
    ScoreSummary,
    __version__,
    normalize_slug,
    summarize_scores,
)

__all__ = [
    "VERSION",
    "PolylibError",
    "ScoreSummary",
    "__version__",
    "normalize_slug",
    "summarize_scores",
]
