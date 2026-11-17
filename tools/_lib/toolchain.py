"""Report a missing external toolchain as a skip or a failure, once.

Every lane that shells out to `gradle`, `gem`, `swift`, or a C compiler faced the
same six lines: probe `PATH`, compose a message naming the binary and the pixi
environment that provides it, then branch on whether the toolchain was required.
The wording drifted between sites, and a lane that simply returned early left
nothing in the log saying what had not run.

The reason always names the binary and how to obtain it, because the reader of a
skipped lane needs to know what to install, not merely that something happened.
"""

from __future__ import annotations

import shutil
from dataclasses import dataclass
from typing import TYPE_CHECKING

from tools._lib.status import CheckResult, failed, skipped

if TYPE_CHECKING:
    from collections.abc import Sequence

_COMMA_SEP = ", "


@dataclass(frozen=True, slots=True)
class ToolchainAbsence:
    """The result of probing for the executables a lane needs."""

    name: str
    missing: tuple[str, ...]
    hint: str
    required: bool = False

    def as_result(self) -> CheckResult:
        """Render as `failed` when the toolchain was required, `skipped` otherwise.

        A required toolchain that is absent is a failure: the runner promised the
        tool and the run must not look clean. An optional one is a skip, and the
        reason still carries the reason it could not run.
        """
        binary_list = _COMMA_SEP.join(self.missing)
        lookup = binary_list if len(self.missing) > 1 else f"`{binary_list}`"
        reason = f"{lookup} not found on PATH, so {self.name} did not run; {self.hint}."
        return failed(self.name, reason) if self.required else skipped(self.name, reason)


def missing_toolchain(
    name: str,
    binaries: str | Sequence[str],
    *,
    hint: str,
    required: bool = False,
) -> ToolchainAbsence | None:
    """Return an absence when any of `binaries` is not on `PATH`, else `None`.

    `hint` is the sentence fragment telling the reader how to obtain the
    toolchain, for example "run via `pixi run -e kt ...` to build the JAR".
    """
    wanted = (binaries,) if isinstance(binaries, str) else tuple(binaries)
    absent = tuple(binary for binary in wanted if shutil.which(binary) is None)
    if not absent:
        return None
    return ToolchainAbsence(name=name, missing=absent, hint=hint, required=required)
