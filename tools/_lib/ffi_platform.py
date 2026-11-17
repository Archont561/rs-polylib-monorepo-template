"""Host platform and toolchain helpers shared by the FFI verifiers.

Three modules grew their own copy of these routines, which is how the Ruby
smoke script came to exist twice with different contents. There is one copy
of each here so a change reaches every caller.
"""

from __future__ import annotations

import os
import platform
import shutil
import sys
from typing import TYPE_CHECKING

from tasknest import ToolError

if TYPE_CHECKING:
    from pathlib import Path

_FFI_LIB_STEM = "polylib_ffi"
_BUNDLE_BIN = "bundle"
_RUBY_DIR = "polylib-rb"


def cdylib_filename() -> str:
    """Return the host platform shared-library filename for `polylib-ffi`."""
    if sys.platform == "darwin":
        return f"lib{_FFI_LIB_STEM}.dylib"
    if sys.platform == "win32":
        return f"{_FFI_LIB_STEM}.dll"
    return f"lib{_FFI_LIB_STEM}.so"


def jna_platform_dir() -> str:
    """Return the JNA classpath resource subdirectory for the current host OS/arch."""
    machine = platform.machine().lower()
    arch = "aarch64" if machine in {"arm64", "aarch64"} else "x86-64"
    system = platform.system().lower()
    if system == "darwin":
        return f"darwin-{arch}"
    if system == "windows":
        return f"win32-{arch}"
    return f"linux-{arch}"


def require_tool(binary: str, pixi_env: str) -> None:
    """Raise unless `binary` is on PATH, naming the Pixi environment that ships it."""
    if shutil.which(binary) is None:
        raise ToolError(
            f"Required `{binary}` tool not found on PATH; run via `pixi run -e {pixi_env} ...`."
        )


def isolated_ruby_env(gem_home: Path, rb_root: Path) -> dict[str, str]:
    """Build a `GEM_HOME`/`GEM_PATH` pointing only at the isolated install."""
    iso_env = dict(os.environ)
    iso_env["GEM_HOME"] = str(gem_home)
    paths = [str(gem_home)]
    vendor_ruby = rb_root / "vendor" / _BUNDLE_BIN / "ruby"
    if vendor_ruby.is_dir():
        # Bundler installs into `<BUNDLE_PATH>/ruby/<abi>/`, and that directory
        # is a gem home: it holds `gems/` and `specifications/`. Each entry of
        # GEM_PATH must be such a directory, not one of its children.
        paths.extend(str(p) for p in sorted(vendor_ruby.iterdir()) if p.is_dir())
    iso_env["GEM_PATH"] = os.pathsep.join(paths)
    return iso_env
