"""Every packaged-artifact smoke script must compare the artifact's version.

A smoke test that installs the built package and exercises it, but never
checks the version, still passes when the package bundles a stale native
library. That is exactly how the Ruby gem lost its parity assertion: the
verifier moved modules and the line did not come with it, and no test noticed.
"""

from __future__ import annotations

import pytest

from tools._lib.smoke_sources import (
    PARITY_FRAGMENTS,
    SMOKE_SOURCES,
    missing_parity,
    parity_fragment,
)


def test_every_ecosystem_has_a_smoke_source() -> None:
    """A new ecosystem must appear here, which is what forces a parity check."""
    assert set(SMOKE_SOURCES) == set(PARITY_FRAGMENTS)
    assert len(SMOKE_SOURCES) >= 7


@pytest.mark.parametrize("ecosystem", sorted(SMOKE_SOURCES))
def test_smoke_source_asserts_version_parity(ecosystem: str) -> None:
    """The packaged script must compare the artifact version to the release version."""
    source = SMOKE_SOURCES[ecosystem]
    fragment = parity_fragment(ecosystem)
    assert fragment in source, (
        f"{ecosystem} smoke script no longer compares the packaged version "
        f"({fragment!r} missing); a stale native library would pass verification."
    )


def test_missing_parity_is_empty_for_the_shipped_scripts() -> None:
    """The aggregate check agrees with the per-ecosystem checks."""
    assert missing_parity() == []


def test_missing_parity_detects_a_removed_assertion(monkeypatch: pytest.MonkeyPatch) -> None:
    """Removing one assertion must be reported, not silently tolerated."""
    mutated = dict(SMOKE_SOURCES)
    mutated["ruby"] = "require 'polylib'; raise 'slug' unless 1 == 1"
    monkeypatch.setattr("tools._lib.smoke_sources.SMOKE_SOURCES", mutated)
    assert missing_parity() == ["ruby"]
