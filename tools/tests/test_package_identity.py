"""The package name and Python floor have one home: the package manifest.

Both were stated in more than one place. Neither drifted yet, which is exactly
the state the Ruby smoke script was in before it lost an assertion, so the
guard is cheaper than noticing later.
"""

from __future__ import annotations

import re
from pathlib import Path

import tomllib

from tools._lib.compat_py import python_package_identity

_ROOT = Path(__file__).resolve().parents[2]
_PKG_PYPROJECT = _ROOT / "packages" / "polylib-py" / "pyproject.toml"


def test_identity_matches_the_package_manifest() -> None:
    """The helper reads the manifest rather than restating it."""
    data = tomllib.loads(_PKG_PYPROJECT.read_text(encoding="utf-8"))
    name, floor = python_package_identity(_ROOT)
    assert name == data["project"]["name"]
    assert floor == data["project"]["requires-python"]


def test_no_hardcoded_floor_in_the_compat_helper() -> None:
    """The floor must not be restated in the verifier that asserts it."""
    source = (_ROOT / "tools" / "_lib" / "compat_py.py").read_text(encoding="utf-8")
    assert ">=3.10" not in source
    assert ">=3.11" not in source


def test_identity_is_not_repeated_as_a_constant() -> None:
    """A `_PKG_NAME` constant was the duplicate; it must not come back."""
    source = (_ROOT / "tools" / "_lib" / "compat_py.py").read_text(encoding="utf-8")
    assert "_PKG_NAME" not in source


def test_tox_floor_matches_the_manifest() -> None:
    """Tox asserts the distribution's metadata, which must agree with the manifest."""
    floor = tomllib.loads(_PKG_PYPROJECT.read_text(encoding="utf-8"))["project"]["requires-python"]
    tox_text = (_ROOT / "tox.ini").read_text(encoding="utf-8")
    asserted = re.findall(r"dist\.metadata\['Requires-Python'\]\s*==\s*'([^']+)'", tox_text)
    assert asserted, "tox no longer asserts Requires-Python; update this guard"
    for value in asserted:
        assert value == floor, f"tox asserts {value!r} but the manifest declares {floor!r}"


def test_uniffi_contract_version_tracks_the_resolved_dependency() -> None:
    """The C-ABI smoke must not compare against a magic number."""
    from tools._lib.compat_ffi import _c_abi_smoke_source, _uniffi_contract_version

    lock = (_ROOT / "Cargo.lock").read_text(encoding="utf-8")
    match = re.search(r'name = "uniffi"\nversion = "([^"]+)"', lock)
    assert match, "uniffi is not in Cargo.lock"
    expected_minor = int(match.group(1).split(".")[1])
    assert _uniffi_contract_version(_ROOT) == expected_minor
    assert f"v != {expected_minor}" in _c_abi_smoke_source(_ROOT)
    assert "v != __CONTRACT_VERSION__" not in _c_abi_smoke_source(_ROOT)
