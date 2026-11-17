"""One decorator for the entry points that return verification results.

Seven task entry points ended with the same three lines:

    results = verify_...
    print(render(results))
    if not publish_ready(results):
        raise ToolError("... did not fully pass; see the lanes above.")

The prose differed per site and so did the exit condition, which is how
`ffi test --target kotlin` came to fail its own readiness gate: one site had
appended a skip for a lane the invocation had not asked for. Collapsing the
idiom into one place means the exit condition is written once.

Applied *above* `@tool`, so it wraps the callable tasknest registers rather than
the decorator output.
"""

from __future__ import annotations

import inspect
from functools import wraps
from typing import TYPE_CHECKING, ParamSpec

from tasknest import ToolError

from tools._lib.status import CheckResult, publish_ready, render

if TYPE_CHECKING:
    from collections.abc import Callable

_P = ParamSpec("_P")


def _resolve_annotations(fn: Callable[..., object]) -> dict[str, object]:
    """Evaluate a callable's string annotations against its own module globals."""
    resolved: dict[str, object] = dict(fn.__annotations__)
    globalns = getattr(fn, "__globals__", {})
    for name, value in resolved.items():
        if isinstance(value, str):
            try:
                resolved[name] = eval(value, globalns, {})  # noqa: S307
            except NameError:
                continue
    return resolved


def _signature_with(fn: Callable[..., object], resolved: dict[str, object]) -> inspect.Signature:
    """Return `fn`'s signature with string annotations replaced by resolved types."""
    signature = inspect.signature(fn)
    parameters = [
        parameter.replace(annotation=resolved.get(parameter.name, parameter.annotation))
        for parameter in signature.parameters.values()
    ]
    return signature.replace(
        parameters=parameters,
        return_annotation=resolved.get("return", signature.return_annotation),
    )


def reports_verification(
    subject: str,
) -> Callable[[Callable[_P, CheckResult | list[CheckResult]]], Callable[_P, None]]:
    """Render the returned results and fail the task when any did not pass.

    `subject` completes the failure sentence, so the log says which gate refused
    rather than raising a bare `ToolError`.
    """

    def decorator(
        fn: Callable[_P, CheckResult | list[CheckResult]],
    ) -> Callable[_P, None]:
        @wraps(fn)
        def wrapper(*args: _P.args, **kwargs: _P.kwargs) -> None:
            produced = fn(*args, **kwargs)
            results = produced if isinstance(produced, list) else [produced]
            print(render(results))
            if not publish_ready(results):
                raise ToolError(f"{subject} did not fully pass; see the lanes above.")

        # `@wraps` copies `__annotations__` but not `__globals__`, and
        # `__globals__` cannot be reassigned. tasknest resolves the wrapper's
        # annotations against *this* module, where a task module's `Literal`
        # alias does not exist; `get_type_hints` then raises, tasknest swallows
        # it, and the option degrades to a raw string annotation it rejects
        # ("Unsupported parameter type 'FfiTarget'"). Resolving here, against the
        # task module's own globals, leaves plain types for tasknest to read.
        # `get_type_hints` cannot resolve every name when a dependency (here
        # `CheckResult`) is imported only under `TYPE_CHECKING`; evaluating just
        # the callable's own module globals covers the `Literal` aliases that
        # matter and leaves the rest alone.
        resolved = _resolve_annotations(fn)
        wrapper.__annotations__ = resolved
        # `@wraps` also sets `__wrapped__`, and `inspect.signature` follows it,
        # so tasknest would read the *original* function's string annotations
        # regardless of `__annotations__`. An explicit `__signature__` takes
        # precedence over that lookup and carries the resolved types.
        wrapper.__signature__ = _signature_with(fn, resolved)  # type: ignore[attr-defined]
        return wrapper

    return decorator
