"""Run the published tarballs' consumer fixtures from pre-packed artifacts.

`ts compat` packs the tarballs itself, which is what a developer wants and what a
single CI job can do. The cross-platform matrix cannot: each runner downloads the
tarballs one job packed, and the platform addon another job compiled. This task
takes those directories as arguments and runs the same fixtures against them, so
the matrix and the local gate exercise identical code.
"""

from __future__ import annotations

import json
import tarfile
from typing import TYPE_CHECKING, Literal, get_args

from tasknest import ToolContext, ToolError, tool

from tools._lib.compat_ts_consumers import (
    ConsumerCase,
    consumer_cases,
    run_consumer_cases,
    verify_facade_peer_declaration,
)
from tools._lib.status import CheckResult, not_run, passed
from tools._lib.verification import reports_verification

if TYPE_CHECKING:
    from pathlib import Path

_UTF8 = "utf-8"
_TGZ = ".tgz"
_FACADE_GLOB = "polylib-polylib-[0-9]*.tgz"
_JS_GLOB = "polylib-polylib-js-[0-9]*.tgz"
_WASM_GLOB = "polylib-polylib-wasm-*.tgz"
_PLATFORM_PREFIX = "polylib-polylib-js-"
_FACADE_PKG = "@polylib/polylib"
_JS_PKG = "@polylib/polylib-js"
_WASM_PKG = "@polylib/polylib-wasm"
_MANIFEST_IN_TARBALL = "package/package.json"
_CHECK_NAME = "ts-consumers"

CaseSet = Literal["all", "native"]
_ALL_CASES: CaseSet = "all"
# The two fixtures that need a compiled addon, and so the only two whose result
# can differ between operating systems.
_NATIVE_CASE_NAMES: frozenset[str] = frozenset({"server-only", "cjs-require"})


def _single(directory: Path, pattern: str, *, what: str) -> Path:
    """Find exactly one tarball matching `pattern`, or explain what is missing."""
    matches = sorted(directory.glob(pattern))
    if len(matches) == 1:
        return matches[0]
    if not matches:
        raise ToolError(f"No {what} tarball matching {pattern!r} in {directory}.")
    names = ", ".join(match.name for match in matches)
    raise ToolError(f"More than one {what} tarball in {directory}: {names}.")


def _platform_tarballs(platform_dir: Path) -> dict[str, Path]:
    """Map each per-platform package onto the tarball the build matrix produced.

    The name comes from the tarball's own manifest, not from its filename: a
    filename carries the version too (`…-linux-x64-gnu-0.1.0.tgz`), so splitting
    on the suffix yields a package name npm cannot install.
    """
    if not platform_dir.is_dir():
        return {}
    found: dict[str, Path] = {}
    for tarball in sorted(platform_dir.glob(f"{_PLATFORM_PREFIX}*{_TGZ}")):
        name = _packed_manifest(tarball).get("name")
        if not isinstance(name, str) or not name.startswith(_JS_PKG):
            raise ToolError(f"{tarball.name} does not declare a {_JS_PKG}-* package name.")
        found[name] = tarball
    return found


def _select(cases: tuple[ConsumerCase, ...], case_set: CaseSet) -> tuple[ConsumerCase, ...]:
    """Restrict to the cases a matrix entry asks for."""
    if case_set == _ALL_CASES:
        return cases
    return tuple(case for case in cases if case.name in _NATIVE_CASE_NAMES)


def _packed_manifest(tarball: Path) -> dict[str, object]:
    """Read the `package.json` npm will see, straight out of the tarball."""
    with tarfile.open(tarball) as archive:
        member = archive.extractfile(_MANIFEST_IN_TARBALL)
        if member is None:
            raise ToolError(f"{tarball.name} has no {_MANIFEST_IN_TARBALL}.")
        manifest: dict[str, object] = json.loads(member.read().decode(_UTF8))
    return manifest


@tool(
    marks=("ts", "ci"),
    description=(
        "Run the published-tarball consumer fixtures (`--tarball-dir`, `--platform-dir`)."
    ),
)
@reports_verification("TypeScript consumer fixtures")
def ts_consumers(
    ctx: ToolContext,
    tarball_dir: str,
    platform_dir: str = "",
    cases: CaseSet = _ALL_CASES,
) -> CheckResult:
    """Install the packed tarballs into isolated fixtures and run them.

    `--cases native` restricts to the fixtures that need a compiled addon, which
    is what an OS-specific matrix entry runs; `all` adds the browser, CommonJS
    bundle, and missing-package fixtures.
    """
    if cases not in get_args(CaseSet):
        expected = ", ".join(get_args(CaseSet))
        raise ToolError(f"Unsupported case set {cases!r}; expected one of: {expected}.")
    tarball_path = ctx.repo_root / tarball_dir
    if not tarball_path.is_dir():
        raise ToolError(f"No tarball directory at {tarball_path}.")
    tarballs = {
        _FACADE_PKG: _single(tarball_path, _FACADE_GLOB, what="facade"),
        _JS_PKG: _single(tarball_path, _JS_GLOB, what="@polylib/polylib-js"),
        _WASM_PKG: _single(tarball_path, _WASM_GLOB, what="@polylib/polylib-wasm"),
    }
    problems = verify_facade_peer_declaration(_packed_manifest(tarballs[_FACADE_PKG]))
    if problems:
        raise ToolError("The packed facade manifest is wrong:\n  " + "\n  ".join(problems))
    platform = _platform_tarballs(ctx.repo_root / platform_dir) if platform_dir else {}
    selected = _select(consumer_cases(tarballs, platform_packages=platform), cases)
    skipped = run_consumer_cases(
        selected,
        ctx.repo_root / "dist-artifacts" / "consumers",
        native_addon_available=bool(platform),
    )
    ran = len(selected) - len(skipped)
    if skipped:
        return not_run(
            _CHECK_NAME,
            "no addon package staged, so "
            f"{', '.join(skipped)} could not run; {ran} fixture(s) passed.",
        )
    return passed(
        _CHECK_NAME,
        evidence=f"{ran} fixture(s) installed and ran against the packed tarballs",
    )
