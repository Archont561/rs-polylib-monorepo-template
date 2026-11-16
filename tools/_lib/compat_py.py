"""Python wheel and sdist compatibility verification for `packages/polylib-py`."""

from __future__ import annotations

import sys
import tempfile
import zipfile
from email.parser import Parser
from pathlib import Path

from tasknest import ToolError

from tools._lib.process import run_checked

_PKG_NAME = "polylib"
_UTF8 = "utf-8"
_MATURIN = "maturin"
_FLAG_OUT = "--out"
_REQUIRED_FILES: tuple[str, ...] = (
    "polylib/__init__.py",
    "polylib/_native.pyi",
    "polylib/py.typed",
)
_SMOKE_CODE = (
    "import polylib; "
    "assert polylib.__version__ == polylib.VERSION; "
    "assert polylib.normalize_slug('Hello Wheel!') == 'hello-wheel'; "
    "s = polylib.summarize_scores([10.0, 20.0]); "
    "assert s.count == 2 and s.mean == 15.0"
)


def _has_valid_structure(names: list[str], meta_path: str | None) -> bool:
    has_native = any(
        name.startswith("polylib/_native") and name.endswith((".so", ".pyd")) for name in names
    )
    has_files = has_native and all(req in names for req in _REQUIRED_FILES)
    no_pycache = all("__pycache__" not in name for name in names)
    return meta_path is not None and has_files and no_pycache


def _verify_wheel_archive(wheel_path: Path) -> None:
    with zipfile.ZipFile(wheel_path) as archive:
        names = archive.namelist()
        meta_path = next((name for name in names if name.endswith("/METADATA")), None)
        if not _has_valid_structure(names, meta_path) or meta_path is None:
            raise ToolError(f"Wheel archive {wheel_path.name} failed validation: {names}")
        metadata = Parser().parsestr(archive.read(meta_path).decode(_UTF8))
    if metadata.get("Name") != _PKG_NAME or metadata.get("Requires-Python") != ">=3.10":
        raise ToolError(f"Unexpected wheel METADATA identity in {wheel_path.name}")
    deps = metadata.get_all("Requires-Dist")
    if deps:
        raise ToolError(f"Core wheel unexpectedly requires runtime deps: {deps}")


def _venv_bin(venv_dir: Path, tool: str) -> Path:
    win_bin = venv_dir / "Scripts" / f"{tool}.exe"
    if win_bin.exists():
        return win_bin
    return venv_dir / "bin" / tool


def _verify_venv_wheel(wheel_path: Path, tmp_path: Path) -> None:
    venv_dir = tmp_path / "venv-wheel"
    run_checked((sys.executable, "-m", "virtualenv", str(venv_dir)), tmp_path)
    run_checked(
        (str(_venv_bin(venv_dir, "pip")), "install", "--no-index", "--no-deps", str(wheel_path)),
        tmp_path,
    )
    run_checked((str(_venv_bin(venv_dir, "python")), "-c", _SMOKE_CODE), tmp_path)


def build_editable_extension(root: Path) -> Path:
    """Build the `polylib-py` wheel and extract `_native` into `packages/polylib-py/src`."""
    pkg_dir = root / "packages" / "polylib-py"
    with tempfile.TemporaryDirectory(prefix="polylib-maturin-") as tmp:
        tmp_path = Path(tmp)
        run_checked((_MATURIN, "build", _FLAG_OUT, str(tmp_path), "--locked"), pkg_dir)
        wheel = next(tmp_path.glob(f"{_PKG_NAME}-*.whl"))
        dest_root = pkg_dir / "src"
        with zipfile.ZipFile(wheel) as archive:
            for member in archive.namelist():
                if member.startswith("polylib/_native") and member.endswith((".so", ".pyd")):
                    out_file = dest_root / member
                    out_file.write_bytes(archive.read(member))
                    return out_file
    raise ToolError("maturin wheel did not contain compiled polylib._native extension")


def verify_py_compat(root: Path) -> None:
    """Build `polylib` wheel & sdist with maturin and verify metadata + offline venv install."""
    pkg_dir = root / "packages" / "polylib-py"
    with tempfile.TemporaryDirectory(prefix="polylib-py-compat-") as tmp:
        tmp_path = Path(tmp)
        run_checked((_MATURIN, "build", _FLAG_OUT, str(tmp_path), "--locked"), pkg_dir)
        run_checked((_MATURIN, "sdist", _FLAG_OUT, str(tmp_path)), pkg_dir)
        wheel = next(tmp_path.glob(f"{_PKG_NAME}-*.whl"))
        sdist = next(tmp_path.glob(f"{_PKG_NAME}-*.tar.gz"))
        if not sdist.exists():
            raise ToolError("maturin did not emit an sdist archive")
        _verify_wheel_archive(wheel)
        _verify_venv_wheel(wheel, tmp_path)
    print("py-compat: maturin wheel, sdist, metadata, and isolated venv smoke OK")
