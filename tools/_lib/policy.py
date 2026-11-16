"""Declarative `alint test` runner plus live real-schema mutation checks."""

from __future__ import annotations

import shutil
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

from tasknest import ToolError

from tools._lib.process import CommandSpec, run_capture, run_checked

if TYPE_CHECKING:
    from collections.abc import Callable

_UTF8 = "utf-8"
_ALINT = "alint"


@dataclass(frozen=True)
class SchemaProbe:
    """One live real-schema negative test executed against `.alint/schemas/`."""

    name: str
    rule_id: str
    target_path: str
    mutate: Callable[[str], str]


_PROBES: tuple[SchemaProbe, ...] = (
    SchemaProbe(
        name="pixi-only-tools-task rejects extra Pixi task",
        rule_id="pixi-only-tools-task",
        target_path="pixi.toml",
        mutate=lambda raw: raw + '\n[tasks.extra]\ncmd = "echo rogue"\n',
    ),
    SchemaProbe(
        name="schema-root-package rejects root npm scripts",
        rule_id="schema-root-package",
        target_path="package.json",
        mutate=lambda raw: raw.replace(
            '"private": true,',
            '"private": true,\n  "scripts": { "build": "echo bad" },',
        ),
    ),
    SchemaProbe(
        name="schema-python-package-pyproject rejects weak requires-python",
        rule_id="schema-python-package-pyproject",
        target_path="packages/polylib-py/pyproject.toml",
        mutate=lambda raw: raw.replace('requires-python = ">=3.10"', 'requires-python = ">=3.6"'),
    ),
    SchemaProbe(
        name="schema-rust-crate-cargo rejects unsafe_code override",
        rule_id="schema-rust-crate-cargo",
        target_path="crates/polylib/Cargo.toml",
        mutate=lambda raw: raw.replace("edition.workspace = true", 'edition = "2018"'),
    ),
    SchemaProbe(
        name="schema-lefthook-config rejects raw non-tools command",
        rule_id="schema-lefthook-config",
        target_path="lefthook.yml",
        mutate=lambda raw: raw.replace("run: pixi run tools", "run: bash -c echo", 1),
    ),
    SchemaProbe(
        name="schema-github-issue-forms rejects missing issue body",
        rule_id="schema-github-issue-forms",
        target_path=".github/ISSUE_TEMPLATE/bug_report.yml",
        mutate=lambda raw: "name: Broken\ndescription: Missing body\n",
    ),
)


def _stage_probe_repo(root: Path, sandbox: Path, target_path: str, mutated: str) -> None:
    shutil.copy2(root / ".alint.yml", sandbox / ".alint.yml")
    shutil.copytree(root / ".alint" / "schemas", sandbox / ".alint" / "schemas")
    dst = sandbox / target_path
    dst.parent.mkdir(parents=True, exist_ok=True)
    dst.write_text(mutated, encoding=_UTF8)


def _run_probe(root: Path, probe: SchemaProbe) -> None:
    original = (root / probe.target_path).read_text(encoding=_UTF8)
    mutated = probe.mutate(original)
    if mutated == original:
        raise ToolError(f"Schema probe {probe.name!r} produced no mutation")
    with tempfile.TemporaryDirectory(prefix="alint-probe-") as tmp:
        sandbox = Path(tmp)
        _stage_probe_repo(root, sandbox, probe.target_path, mutated)
        result = run_capture(
            CommandSpec(argv=(_ALINT, "check", "--only", probe.rule_id), cwd=sandbox)
        )
        if result.returncode == 0:
            raise ToolError(f"Expected {probe.rule_id} to fail on mutated {probe.target_path}")
    print(f"PASS probe: {probe.name}")


def run_policy_tests(root: Path) -> None:
    """Run declarative `.alint/tests/` and live real-schema mutation probes."""
    run_checked((_ALINT, "test", ".alint/tests"), root)
    for probe in _PROBES:
        _run_probe(root, probe)
    print(f"policy-tests: declarative suite + {len(_PROBES)}/{len(_PROBES)} live schema probes OK")
