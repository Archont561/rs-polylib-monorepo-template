# `polylib`

Public Rust metacrate facade re-exporting `polylib-core` behind additive, opt-in feature flags.

## Features

- `default = []`: zero optional dependencies.
- `serde`: enables `serde::Serialize` and `serde::Deserialize` on core types.
- `json`: enables `serde` plus `summarize_scores_json`.
- `full`: enables all public features.

## Allowed Dependencies

- Depends downward on `polylib-core` and feature-gated registry crates only.
- Never depends on binding crates (`polylib-py`, `polylib-wasm`).

## Verification

```sh
pixi run -e rust tools run rust compat
```
