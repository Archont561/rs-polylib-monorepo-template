"""Python wheel and sdist compatibility verification for `packages/polylib-py`."""

from __future__ import annotations

import sys
import tempfile
import zipfile
from email.parser import Parser
from pathlib import Path

import tomllib
from tasknest import ToolError

from tools._lib.binary_arch import extension_container, read_payload_arch, tag_wants
from tools._lib.process import run_checked
from tools._lib.status import CheckResult, failed, passed, skipped

_UTF8 = "utf-8"
_PKG_PYPROJECT = (
    "packages",
    "polylib-py",
    "pyproject.toml",
)
_MATURIN = "maturin"
_FLAG_OUT = "--out"


def python_package_identity(root: Path) -> tuple[str, str]:
    """Read the package name and Python floor from `packages/polylib-py/pyproject.toml`.

    The wheel metadata assertion compares against these, so stating them here as
    well would drift the moment either moves. The manifest is the single source.
    """
    manifest = root.joinpath(*_PKG_PYPROJECT)
    data = tomllib.loads(manifest.read_text(encoding=_UTF8))
    project = data.get("project", {})
    name = project.get("name")
    floor = project.get("requires-python")
    if not isinstance(name, str) or not isinstance(floor, str):
        raise ToolError(f"{manifest} must declare [project] name and requires-python.")
    return name, floor


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
    has_native = any(_is_native_member(name) for name in names)
    has_files = has_native and all(req in names for req in _REQUIRED_FILES)
    no_pycache = all("__pycache__" not in name for name in names)
    return meta_path is not None and has_files and no_pycache


def _is_native_member(name: str) -> bool:
    return name.startswith("polylib/_native") and name.endswith((".so", ".pyd", ".dylib"))


def _wheel_platform_tag(wheel_name: str) -> str | None:
    """Extract the platform tag from a wheel filename."""
    parts = wheel_name.removesuffix(".whl").split("-")
    if len(parts) < 5:
        return None
    return parts[-1].split(".")[0]


def _verify_payload_arch(wheel_path: Path, member: str, payload: bytes) -> list[CheckResult]:
    """Check that the extension's container and architecture match the wheel tag."""
    tag = _wheel_platform_tag(wheel_path.name)
    if tag is None:
        return [
            failed(
                "wheel-payload-arch",
                f"could not read a platform tag from {wheel_path.name}",
            )
        ]
    suffix = Path(member).suffix
    expected_container = extension_container(suffix)
    if expected_container is None:
        return [
            failed(
                "wheel-payload-arch",
                f"extension {suffix!r} in {member} belongs to no known container; "
                "a wheel may carry .so or .pyd only",
            )
        ]
    observed = read_payload_arch(payload)
    wanted = tag_wants(tag)
    if wanted is None:
        return [
            skipped(
                "wheel-payload-arch",
                f"platform tag {tag!r} is not one this reader recognises, so the payload "
                f"architecture ({observed.detail}) was not compared against it.",
            )
        ]
    wanted_container, wanted_arch = wanted
    if expected_container != wanted_container:
        return [
            failed(
                "wheel-payload-arch",
                f"{wheel_path.name} is tagged {tag} but carries a {suffix} extension, "
                f"which holds a {expected_container} container; the payload cannot run "
                "on the platform the filename advertises.",
            )
        ]
    if observed.arch != wanted_arch:
        return [
            failed(
                "wheel-payload-arch",
                f"{wheel_path.name} is tagged {tag} ({wanted_arch}) but the extension is "
                f"{observed.detail}; a stale or cross-built library would install and then "
                "fail at import.",
            )
        ]
    return [
        passed(
            "wheel-payload-arch",
            evidence=f"{observed.detail} matches platform tag {tag}",
        )
    ]


def _inspect_wheel(wheel_path: Path) -> tuple[list[str], str | None, bytes | None, str | None]:
    """Return member names, the METADATA path, the extension bytes, and its member name."""
    with zipfile.ZipFile(wheel_path) as archive:
        names = archive.namelist()
        meta_path = next((name for name in names if name.endswith("/METADATA")), None)
        native = next((name for name in names if _is_native_member(name)), None)
        payload = archive.read(native) if native else None
    return names, meta_path, payload, native


def verify_wheel_archive(root: Path, wheel_path: Path) -> list[CheckResult]:
    """Verify wheel structure, metadata, and that the payload matches its platform tag."""
    names, meta_path, payload, native = _inspect_wheel(wheel_path)
    if not _has_valid_structure(names, meta_path) or meta_path is None:
        raise ToolError(f"Wheel archive {wheel_path.name} failed validation: {names}")
    with zipfile.ZipFile(wheel_path) as archive:
        metadata = Parser().parsestr(archive.read(meta_path).decode(_UTF8))
    expected_name, expected_floor = python_package_identity(root)
    if metadata.get("Name") != expected_name or metadata.get("Requires-Python") != expected_floor:
        raise ToolError(f"Unexpected wheel METADATA identity in {wheel_path.name}")
    deps = metadata.get_all("Requires-Dist")
    if deps:
        raise ToolError(f"Core wheel unexpectedly requires runtime deps: {deps}")
    results = [passed("wheel-structure", evidence=f"{wheel_path.name} metadata and layout match")]
    if payload is None or native is None:
        results.append(
            skipped("wheel-payload-arch", f"{wheel_path.name} carries no native extension")
        )
        return results
    results.extend(_verify_payload_arch(wheel_path, native, payload))
    return results


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
        pkg_name, _ = python_package_identity(root)
        wheel = next(tmp_path.glob(f"{pkg_name}-*.whl"))
        dest_root = pkg_dir / "src"
        with zipfile.ZipFile(wheel) as archive:
            for member in archive.namelist():
                if member.startswith("polylib/_native") and member.endswith((".so", ".pyd")):
                    out_file = dest_root / member
                    out_file.write_bytes(archive.read(member))
                    return out_file
    raise ToolError("maturin wheel did not contain compiled polylib._native extension")


def verify_py_compat(root: Path) -> list[CheckResult]:
    """Build `polylib` wheel & sdist with maturin and verify metadata + offline venv install."""
    pkg_dir = root / "packages" / "polylib-py"
    with tempfile.TemporaryDirectory(prefix="polylib-py-compat-") as tmp:
        tmp_path = Path(tmp)
        run_checked((_MATURIN, "build", _FLAG_OUT, str(tmp_path), "--locked"), pkg_dir)
        run_checked((_MATURIN, "sdist", _FLAG_OUT, str(tmp_path)), pkg_dir)
        pkg_name, _ = python_package_identity(root)
        wheel = next(tmp_path.glob(f"{pkg_name}-*.whl"))
        sdist = next(tmp_path.glob(f"{pkg_name}-*.tar.gz"))
        if not sdist.exists():
            raise ToolError("maturin did not emit an sdist archive")
        results = verify_wheel_archive(root, wheel)
        _verify_venv_wheel(wheel, tmp_path)
        results.append(passed("py-venv", evidence="isolated venv install and import smoke passed"))
    return results
