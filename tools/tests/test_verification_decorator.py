"""The verification decorator, and the annotation trap it has to survive.

The decorator sits between `@tool` and the task body, which means tasknest reads
a wrapper's signature instead of the function the author wrote. `@wraps` sets
`__wrapped__`, and `inspect.signature` follows it, so a `Literal` option
degrades to a bare string annotation unless the signature is supplied directly.
Tasknest then rejects the task outright. These tests pin both facts.
"""

from __future__ import annotations

from typing import Literal

import pytest
from tasknest import ToolContext, ToolError, tool

from tools._lib.status import CheckResult, failed, passed, skipped
from tools._lib.verification import reports_verification

_Target = Literal["all", "kotlin", "swift"]


def test_a_passing_result_returns_normally(capsys: pytest.CaptureFixture[str]) -> None:
    """A pass renders and does not raise."""

    @reports_verification("demo")
    def run() -> list[CheckResult]:
        return [passed("a", evidence="ok")]

    run()
    assert "Verification: passed=1" in capsys.readouterr().out


def test_a_failure_raises_naming_the_subject(capsys: pytest.CaptureFixture[str]) -> None:
    """The failure sentence names the gate, not just "it failed"."""

    @reports_verification("Widget checks")
    def run() -> list[CheckResult]:
        return [failed("a", "broke")]

    with pytest.raises(ToolError, match="Widget checks did not fully pass"):
        run()
    assert "broke" in capsys.readouterr().out


def test_a_bare_result_is_accepted() -> None:
    """A single `CheckResult` needs no list wrapper."""

    @reports_verification("demo")
    def run() -> CheckResult:
        return passed("a")

    run()


def test_a_skip_blocks_the_task() -> None:
    """A skip is not a pass; publication still fails."""

    @reports_verification("demo")
    def run() -> list[CheckResult]:
        return [skipped("a", "no toolchain")]

    with pytest.raises(ToolError):
        run()


def test_literal_options_survive_the_decorator() -> None:
    """`@tool` must still read the `choices` the author declared.

    Exercised against a real task module, not a `Literal` defined here: the alias
    has to live in another module's globals for the trap to reproduce. Removing
    the `__signature__` repair makes importing `tools.ffi.compat` raise
    "Unsupported parameter type 'FfiTarget'".
    """
    from tools.ffi.compat import compat_ffi

    options = {option.cli_name: option for option in compat_ffi.options}
    assert options["target"].choices == ("all", "kotlin", "swift", "ruby")
    assert options["target"].default == "all"


def test_a_plain_str_option_still_works() -> None:
    """The decorator must not disturb an option that carries no `Literal`."""

    @tool(description="demo")
    @reports_verification("demo")
    def run(ctx: ToolContext, name: str = "x") -> list[CheckResult]:
        del ctx, name
        return [passed("a")]

    option = next(option for option in run.options if option.cli_name == "name")
    assert option.base_type is str
    assert option.default == "x"


def test_the_decorator_preserves_the_task_name() -> None:
    """The registry name comes from the function, through both decorators."""

    @tool(description="demo")
    @reports_verification("demo")
    def my_task(ctx: ToolContext) -> list[CheckResult]:
        del ctx
        return [passed("a")]

    assert my_task.name == "my_task"
