"""Cross-platform `file:` dependency references for locally packed tarballs.

npm and Bun both accept a local tarball as a `file:` dependency, but the
spelling of that reference is platform sensitive:

* ``file:/abs/path/pkg.tgz`` and ``file:///abs/path/pkg.tgz`` keep the
  leading slash, so the parser treats the remainder as an absolute path and
  the install fails with ``ENOENT extracting tarball``.
* ``file:C:\\dir\\pkg.tgz`` is parsed as a URL whose host is the drive letter
  ``C:``, so the install never finds the tarball.
* ``file://C:/dir/pkg.tgz`` is likewise read as a URL with a host.

A *relative* reference (``file:../tarballs/pkg.tgz``) is resolved against the
directory that holds the consumer's ``package.json`` by every package manager
and on every operating system, so it is the only spelling that behaves
identically on POSIX and Windows.
"""

from __future__ import annotations

import os
from pathlib import Path

_FILE_PREFIX = "file:"


def tarball_ref(tarball: Path, consumer_dir: Path) -> str:
    """Return a relative `file:` reference to `tarball` from `consumer_dir`.

    The result always uses forward slashes, because `file:` references are
    URL-ish and backslashes are not portable inside them.
    """
    relative = os.path.relpath(tarball, consumer_dir)
    return f"{_FILE_PREFIX}{Path(relative).as_posix()}"
