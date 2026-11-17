#!/usr/bin/env python3
"""Build shape-accurate dummy packages, one per ecosystem the real build ships.

The point is to exercise the release path — build, checksum, attach to a GitHub
Release, download — without standing up credentials for crates.io, PyPI, npm,
RubyGems, or Maven Central. Every file here is a dummy: it has the extension,
the internal layout, and the manifest a real package has, so a release asset can
be opened and inspected, but it carries no compiled code and is not publishable
to any registry.

Nothing in this module is imported by the production release tooling.
"""

from __future__ import annotations

import argparse
import gzip
import hashlib
import io
import json
import tarfile
import zipfile
from pathlib import Path

_DESCRIPTION = "Dummy package built by the demo release workflow."
_LICENSE = "MIT"


def _blob(name: str, version: str, repo: str) -> str:
    """Return a small source file that navigates back to the real project."""
    return (
        f"# {name} {version}\n"
        "\n"
        "This is a placeholder produced by the demo release workflow.\n"
        "It exists to prove the release pipeline works end to end; it is not a\n"
        "real package and is not published to any registry.\n"
        "\n"
        f"See https://github.com/{repo} for the actual project.\n"
    )


def _gzip_bytes(payload: bytes) -> bytes:
    """Gzip ``payload`` with a fixed mtime so repeated builds are identical."""
    buffer = io.BytesIO()
    with gzip.GzipFile(filename="", mode="wb", fileobj=buffer, mtime=0) as handle:
        handle.write(payload)
    return buffer.getvalue()


def _tar_bytes(members: list[tuple[str, bytes]]) -> bytes:
    """Build an uncompressed tar from ``(name, payload)`` pairs."""
    buffer = io.BytesIO()
    with tarfile.open(fileobj=buffer, mode="w") as archive:
        for name, payload in members:
            info = tarfile.TarInfo(name)
            info.size = len(payload)
            info.mtime = 0
            info.mode = 0o644
            archive.addfile(info, io.BytesIO(payload))
    return buffer.getvalue()


def _tar_gz_bytes(members: list[tuple[str, bytes]]) -> bytes:
    """Build a gzip-compressed tar from ``(name, payload)`` pairs."""
    return _gzip_bytes(_tar_bytes(members))


def _zip_bytes(members: list[tuple[str, bytes]]) -> bytes:
    """Build a zip from ``(name, payload)`` pairs, with fixed timestamps."""
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as archive:
        for name, payload in members:
            info = zipfile.ZipInfo(name, date_time=(1980, 1, 1, 0, 0, 0))
            info.external_attr = 0o644 << 16
            info.compress_type = zipfile.ZIP_DEFLATED
            archive.writestr(info, payload)
    return buffer.getvalue()


def build_rust_crate(name: str, version: str, repo: str) -> bytes:
    """Return a ``.crate``: a gzipped tar rooted at ``<name>-<version>/``."""
    root = f"{name}-{version}"
    manifest = (
        f'[package]\nname = "{name}"\nversion = "{version}"\n'
        f'edition = "2024"\nlicense = "{_LICENSE}"\n'
        f'description = "{_DESCRIPTION}"\n\n[lib]\npath = "src/lib.rs"\n'
    )
    return _tar_gz_bytes(
        [
            (f"{root}/Cargo.toml", manifest.encode()),
            (f"{root}/README.md", _blob(name, version, repo).encode()),
            (f"{root}/src/lib.rs", b"// placeholder\n"),
        ]
    )


def build_python_wheel(dist: str, version: str, repo: str) -> bytes:
    """Return a ``.whl``: a zip with the dist-info directory a wheel carries."""
    module = dist.replace("-", "_")
    dist_info = f"{module}-{version}.dist-info"
    metadata = (
        "Metadata-Version: 2.1\n"
        f"Name: {dist}\n"
        f"Version: {version}\n"
        f"Summary: {_DESCRIPTION}\n"
        f"License: {_LICENSE}\n"
        f"Home-page: https://github.com/{repo}\n"
    )
    wheel = (
        "Wheel-Version: 1.0\nGenerator: demo-release\nRoot-Is-Purelib: true\nTag: py3-none-any\n"
    )
    record = "\n".join(
        [
            f"{module}/__init__.py,,",
            f"{dist_info}/METADATA,,",
            f"{dist_info}/WHEEL,,",
            f"{dist_info}/RECORD,,",
            "",
        ]
    )
    return _zip_bytes(
        [
            (f"{module}/__init__.py", _blob(dist, version, repo).encode()),
            (f"{dist_info}/METADATA", metadata.encode()),
            (f"{dist_info}/WHEEL", wheel.encode()),
            (f"{dist_info}/RECORD", record.encode()),
        ]
    )


def build_python_sdist(dist: str, version: str, repo: str) -> bytes:
    """Return a ``.tar.gz`` source distribution with a ``PKG-INFO``."""
    root = f"{dist}-{version}"
    pkg_info = (
        "Metadata-Version: 2.1\n"
        f"Name: {dist}\n"
        f"Version: {version}\n"
        f"Summary: {_DESCRIPTION}\n"
        f"License: {_LICENSE}\n"
    )
    return _tar_gz_bytes(
        [
            (f"{root}/PKG-INFO", pkg_info.encode()),
            (f"{root}/README.md", _blob(dist, version, repo).encode()),
            (f"{root}/pyproject.toml", b"[build-system]\nrequires = []\n"),
        ]
    )


def build_npm_tarball(name: str, version: str, repo: str) -> bytes:
    """Return a ``.tgz`` with the ``package/`` prefix npm expects."""
    manifest = {
        "name": name,
        "version": version,
        "description": _DESCRIPTION,
        "license": _LICENSE,
        "repository": {"type": "git", "url": f"https://github.com/{repo}.git"},
        "main": "index.js",
        "files": ["index.js"],
    }
    return _tar_gz_bytes(
        [
            ("package/package.json", json.dumps(manifest, indent=2).encode() + b"\n"),
            ("package/index.js", b"module.exports = {};\n"),
            ("package/README.md", _blob(name, version, repo).encode()),
        ]
    )


def build_jvm_jar(name: str, version: str, repo: str) -> bytes:
    """Return a ``.jar`` containing a manifest and a placeholder class entry."""
    manifest = (
        "Manifest-Version: 1.0\n"
        f"Implementation-Title: {name}\n"
        f"Implementation-Version: {version}\n"
        "Created-By: demo-release\n"
    )
    pom = (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<project xmlns="http://maven.apache.org/POM/4.0.0">\n'
        f"  <groupId>dev.polylib</groupId>\n"
        f"  <artifactId>{name}</artifactId>\n"
        f"  <version>{version}</version>\n"
        f"  <description>{_DESCRIPTION}</description>\n"
        "</project>\n"
    )
    return _zip_bytes(
        [
            ("META-INF/MANIFEST.MF", manifest.encode()),
            ("META-INF/maven/dev.polylib/pom.xml", pom.encode()),
            ("README.md", _blob(name, version, repo).encode()),
        ]
    )


def build_ruby_gem(name: str, version: str, repo: str) -> bytes:
    """Return a ``.gem``: a tar of ``metadata.gz``, ``data.tar.gz``, checksums."""
    metadata = (
        "--- !ruby/object:Gem::Specification\n"
        f"name: {name}\n"
        f"version: !ruby/object:Gem::Version\n  version: {version}\n"
        f"summary: {_DESCRIPTION}\n"
        f"homepage: https://github.com/{repo}\n"
        "licenses:\n"
        f"- {_LICENSE}\n"
    ).encode()
    data = _tar_gz_bytes(
        [
            (f"lib/{name.replace('-', '/')}.rb", _blob(name, version, repo).encode()),
            ("README.md", _blob(name, version, repo).encode()),
        ]
    )
    checksums = (
        "---\n"
        f"SHA256:\n  metadata.gz: {hashlib.sha256(metadata).hexdigest()}\n"
        f"  data.tar.gz: {hashlib.sha256(data).hexdigest()}\n"
    ).encode()
    return _tar_bytes(
        [
            ("metadata.gz", _gzip_bytes(metadata)),
            ("data.tar.gz", data),
            ("checksums.yaml.gz", _gzip_bytes(checksums)),
        ]
    )


def build_swift_bundle(name: str, version: str, repo: str) -> bytes:
    """Return a ``.zip`` with the ``Package.swift`` a SwiftPM bundle carries."""
    manifest = (
        "// swift-tools-version:6.0\n"
        "import PackageDescription\n\n"
        f'let package = Package(name: "{name}",\n'
        f"    platforms: [.macOS(.v13)],\n"
        '    targets: [.binaryTarget(name: "Demo", path: "Demo.xcframework")])\n'
    )
    return _zip_bytes(
        [
            ("Package.swift", manifest.encode()),
            ("README.md", _blob(name, version, repo).encode()),
            ("Demo.xcframework/Info.plist", b'<?xml version="1.0"?>\n<plist/>\n'),
        ]
    )


def _artifacts(dist: str, version: str, repo: str) -> list[tuple[str, bytes]]:
    """Return ``(filename, payload)`` for every ecosystem the real build ships."""
    crate = dist.replace("-", "_")
    return [
        (f"{dist}-{version}.crate", build_rust_crate(dist, version, repo)),
        (f"{crate}-{version}-py3-none-any.whl", build_python_wheel(dist, version, repo)),
        (f"{dist}-{version}.tar.gz", build_python_sdist(dist, version, repo)),
        (f"{dist}-{version}.tgz", build_npm_tarball(dist, version, repo)),
        (f"{dist}-{version}.jar", build_jvm_jar(dist, version, repo)),
        (f"{dist}-{version}.gem", build_ruby_gem(dist, version, repo)),
        (f"{dist}-{version}.zip", build_swift_bundle(dist, version, repo)),
    ]


def write_bundle(output_dir: Path, version: str, dist: str, repo: str) -> list[Path]:
    """Write every dummy package plus ``SHA256SUMS.txt`` and return the paths."""
    output_dir.mkdir(parents=True, exist_ok=True)

    written: list[Path] = []
    for filename, payload in _artifacts(dist, version, repo):
        path = output_dir / filename
        path.write_bytes(payload)
        written.append(path)

    lines = [f"{hashlib.sha256(path.read_bytes()).hexdigest()}  {path.name}" for path in written]
    checksums = output_dir / "SHA256SUMS.txt"
    checksums.write_text("\n".join(lines) + "\n", encoding="utf-8")
    written.append(checksums)

    manifest = output_dir / "demo-manifest.json"
    manifest.write_text(
        json.dumps(
            {
                "kind": "demo-release",
                "note": (
                    "Dummy packages used to prove the release pipeline. "
                    "Not published to any registry."
                ),
                "version": version,
                "files": [path.name for path in written],
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    written.append(manifest)
    return written


def main() -> int:
    """Write the dummy release bundle to ``--output-dir``."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", default="demo-dist")
    parser.add_argument("--version", required=True)
    parser.add_argument("--dist", default="polylib-demo")
    parser.add_argument("--repo", default="Archont561/rs-polylib-monorepo-template")
    args = parser.parse_args()

    paths = write_bundle(Path(args.output_dir), args.version, args.dist, args.repo)
    for path in paths:
        print(f"  {path.name}  ({path.stat().st_size} bytes)")
    print(f"wrote {len(paths)} files to {args.output_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
