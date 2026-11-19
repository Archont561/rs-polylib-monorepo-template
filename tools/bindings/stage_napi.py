"""Stage the per-platform npm package for one compiled napi target.

Each CI runner compiles exactly one target, so the publishable package for that
target is assembled from the addon it produced. Keeping this out of
`tools/bindings/build.py` matters because a task file registers exactly one
`@tool`, and the build task already holds that slot.
"""

from __future__ import annotations

import json
import shutil
from typing import TYPE_CHECKING

from tasknest import ToolContext, ToolError, tool

from tools._lib.napi_platforms import (
    load_targets,
    platform_manifest,
    verify_platform_package,
)

if TYPE_CHECKING:
    from pathlib import Path

_PACKAGES_DIR = "packages"
_PKG_DIR = "polylib-js"
_MANIFEST = "package.json"
_UTF8 = "utf-8"


@tool(
    marks=("rust", "ts", "writes"),
    description="Stage the per-platform npm package for one napi target (`--suffix`).",
)
def stage_napi_platform(ctx: ToolContext, suffix: str = "") -> None:
    """Stage the addon for `suffix` and report where it landed."""
    package_dir = stage_target(ctx.repo_root, suffix)
    print(f"Staged {package_dir.relative_to(ctx.repo_root)}")


def stage_target(repo_root: Path, suffix: str) -> Path:
    """Copy the compiled addon into `npm/<suffix>/` and write its manifest.

    Returns the staged package directory. A task file registers exactly one
    `@tool`, so this plain function is what the compat fixtures call: they need
    the same layout without a `ToolContext`.
    """
    package_root = repo_root / _PACKAGES_DIR / _PKG_DIR
    manifest_path = package_root / _MANIFEST
    targets = {target.suffix: target for target in load_targets(manifest_path)}
    if not suffix:
        raise ToolError(f"Pass --suffix with one of: {', '.join(sorted(targets))}.")
    target = targets.get(suffix)
    if target is None:
        raise ToolError(
            f"Unknown suffix {suffix!r}; expected one of: {', '.join(sorted(targets))}."
        )
    source = next(
        (
            candidate
            for candidate in (
                package_root / f"polylib.{suffix}.node",
                # `napi build --output-dir` puts the generated loader and the
                # addon beside each other instead of in the package root.
                package_root / "src" / "native" / f"polylib.{suffix}.node",
                package_root / "npm" / suffix / f"polylib.{suffix}.node",
            )
            if candidate.is_file()
        ),
        None,
    )
    if source is None:
        raise ToolError(
            f"No polylib.{suffix}.node under {package_root.relative_to(repo_root)}; "
            "run `napi build --platform` for this target first."
        )
    package_dir = package_root / "npm" / suffix
    package_dir.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, package_dir / source.name)
    base = json.loads(manifest_path.read_text(encoding=_UTF8))
    version = str(base["version"])
    manifest = platform_manifest(base, name=target.package_name, suffix=suffix, version=version)
    (package_dir / _MANIFEST).write_text(json.dumps(manifest, indent=2) + "\n", encoding=_UTF8)
    problems = verify_platform_package(package_dir)
    if problems:
        raise ToolError("The staged package does not match its target:\n  " + "\n  ".join(problems))
    return package_dir
