"""Isolated Node.js + npm tarball compatibility consumer checks.

The fixtures live in `tools/_lib/compat_ts_consumers.py`; this task packs the
tarballs, installs each fixture, and turns a failure into a check result.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from tasknest import ToolError

from tools._lib.compat_ts_consumers import consumer_cases, run_consumer_cases
from tools._lib.status import CheckResult, passed
from tools._lib.status import skipped as skipped_result
from tools._lib.toolchain import missing_toolchain

if TYPE_CHECKING:
    from pathlib import Path

_NODE = "node"
_NPM = "npm"
_NAME = "ts-node-consumers"


@dataclass(frozen=True)
class ConsumerSetup:
    """Where the packed tarballs are and which platform package this host built.

    `tarballs` maps a package name onto its packed tarball; `platform_packages`
    maps the per-platform addon package onto the tarball for this host, which a
    `file:` install cannot reach through `optionalDependencies`.
    """

    tarballs: dict[str, Path]
    platform_packages: dict[str, Path]


def verify_node_consumers(
    tmp_path: Path,
    setup: ConsumerSetup,
    *,
    require_node: bool,
) -> CheckResult:
    """Install the packed tarballs and run every consumer fixture."""
    if absence := missing_toolchain(
        _NAME,
        (_NODE, _NPM),
        hint="install Node.js or run via `pixi run -e js ...`",
        required=require_node,
    ):
        return absence.as_result()
    cases = consumer_cases(setup.tarballs, platform_packages=setup.platform_packages)
    try:
        skipped = run_consumer_cases(
            cases,
            tmp_path / "consumers",
            native_addon_available=bool(setup.platform_packages),
        )
    except (RuntimeError, ToolError) as err:
        raise ToolError(f"{_NAME}: {err}") from err
    ran = len(cases) - len(skipped)
    if skipped:
        return skipped_result(
            _NAME,
            "no compiled addon for this host, so "
            f"{', '.join(skipped)} could not run; the other {ran} fixtures passed. "
            "Build one with `pixi run -e full tools run bindings build --target napi`.",
        )
    return passed(
        _NAME,
        evidence=f"npm installed each of the {ran} fixtures and the smoke tests ran",
    )
