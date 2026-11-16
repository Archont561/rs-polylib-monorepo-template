# `polylib-py`

Thin `PyO3` (`abi3-py310`) native extension crate built by `maturin` for `packages/polylib-py`.

## Responsibilities

- Translates Python inputs and `CoreError` exceptions at the FFI boundary.
- Delegates all domain logic to `polylib-core`.
- Stays `publish = false` on crates.io (distributed as Python wheels on PyPI).

## Allowed Dependencies

- `polylib-core` and `pyo3` only.
- Never imports `wasm-bindgen` or `polylib-wasm`.

## Verification

```sh
pixi run -e full tools run python compat
```
