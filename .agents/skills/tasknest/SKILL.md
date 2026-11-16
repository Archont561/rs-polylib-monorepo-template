---
name: tasknest
description: Author, validate, and maintain nested Python Tasknest (`@tool`) tasks under `tools/{bindings,docs,python,repo,rust,security,ts}/`, package manifest integration, marks, and generated agent skill docs (`project-tools`). Use when adding or updating repository automation in `tools/` or `tasknest.toml`.
---

# Python Tasknest Authoring (`tools/<group>/<task>.py`)

This repository delegates **all** workspace automation to Python **Tasknest `0.4.0`** through the single Pixi task:

```toml
[tasks]
tools = "python -B -m tasknest"
```

## Directory Layout

- Top-level composites & smoke tasks live at `tools/{check,test,hello}.py`.
- Domain tasks are nested in directories so Tasknest exposes natural space-separated and dotted task paths:
  - `tools/bindings/` -> `bindings build`
  - `tools/docs/` -> `docs check`, `docs write`, `docs md`, `docs links`, `docs prose`
  - `tools/python/` -> `python lint`, `python test`, `python compat`
  - `tools/repo/` -> `repo alint`, `repo policy`, `repo format`, `repo gherkin`, `repo actions`, `repo sandbox`, `repo install`, `repo hooks`, `repo commit_msg`
  - `tools/rust/` -> `rust lint`, `rust test`, `rust features`, `rust packages`, `rust msrv`, `rust compat`
  - `tools/security/` -> `security deny_rs`, `security audit_rs`, `security audit_py`, `security audit_js`
  - `tools/ts/` -> `ts lint`, `ts test`, `ts compat`
- Shared non-task helpers live under `tools/_lib/` (ignored by Tasknest discovery and `CC804`).

## Rules

1. **One file = one `@tool` task:** Each `tools/<group>/<task>.py` file must register exactly one `@tool(...)` function. Shared helper code belongs under `tools/_lib/`.
2. **Strict clean code (`CC804`):** Every public function under `tools/` (excluding `tools/_lib/`) must carry `@tool(...)`, a docstring, strict type annotations, and clean-code compliance (`ruff`, `mypy --strict`, `rude check`).
3. **Never add extra tasks to `pixi.toml` or `"scripts"` to root `package.json`:** Both invariants are enforced by `.alint.yml` and `.alint/schemas/`.
4. **Use known marks from `tasknest.toml`:** `fast`, `ci`, `rust`, `python`, `ts`, `compat`, `docs`, `security`, `writes`, `dev`.
5. **Keep the generated skill synchronized:** After adding, renaming, or editing any task or package script, run:

```sh
pixi run tools check
pixi run tools skill --write
pixi run tools skill --check
```

## Example Task

```python
"""Short module summary."""

from __future__ import annotations

from tasknest import ToolContext, tool


@tool(marks=("fast", "ci"), description="Short one-line description shown by `tools ls`.")
def example(ctx: ToolContext, strict: bool = True) -> None:
    """Explain what the task runs."""
    argv = ["alint", "check"]
    if strict:
        argv.append("--strict")
    ctx.run(argv, cwd=ctx.repo_root)
```
