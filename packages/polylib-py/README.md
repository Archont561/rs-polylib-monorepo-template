# `polylib` (Python)

Typed Python library backed by the `polylib-core` Rust engine via `PyO3` (`abi3-py310`) and `maturin`.

## Responsibilities

- Exposes typed Python APIs (`normalize_slug`, `summarize_scores`, `ScoreSummary`, `PolylibError`, `VERSION`).
- Ships PEP 561 type stubs (`_native.pyi`, `py.typed`) with zero runtime Python dependencies.
- Stays verified against shared Gherkin `conformance/*.feature` specs via `pytest`, `pytest-bdd`, and `hypothesis`.

## Verification

```sh
pixi run -e full tools run bindings build
pixi run -e full tools run python test
pixi run -e full tools run python compat
```
