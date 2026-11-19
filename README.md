# Offline sandbox (orphan branch)

Built 2026-11-19T23:34:24Z from commit `fb28215` for platform `linux-64`.
`pixi.lock` sha256 `3a41527e9a9b632865096d675891323d31780d12f71d0c2b40bae9afa54d7e65`.

The verified self-bootstrap binary is stored at `.pixi-sandbox/tools/linux-64/pixi-sandbox`. The branch root intentionally contains documentation only.

| env | platform | packed | unpacked | files |
| --- | --- | ---: | ---: | ---: |
| `default` | linux-64 | 187.7 MiB | 608.7 MiB | 122 |

Cargo dependencies: **268 crates**, 292.9 MiB (loose) from `Cargo.lock` sha256 `b0840313c367…`; restore materialises them to `.pixi-sandbox/vendor/`. Built with cargo 1.99.1 (5f94df478 2026-08-27); rustc 1.99.1 (58cf8f9c3 2026-10-13).


## Restore on the disconnected machine

```bash
./.pixi-sandbox/tools/linux-64/pixi-sandbox doctor --branch-location . --verify
./.pixi-sandbox/tools/linux-64/pixi-sandbox restore --branch-location . --output-path <project> --force
# then, from <project> with no network, use pixi as the sole entrypoint:
pixi install --frozen --offline
pixi run --frozen -- cargo build --offline
```

Every manifest blob is verified before it is written into the working tree.
