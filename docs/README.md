# `@polylib/app-docs`

Static Fumadocs documentation site for the `polylib` Rust, Python, and TypeScript libraries.

## Responsibilities

- Publishes user guides and API reference pages as a Next.js static export (`docs/out`) to GitHub Pages.
- Requires enabling GitHub Pages once under **Settings -> Pages -> Source: GitHub Actions**.
- Remains isolated from runtime library build artifacts.

## Verification

```sh
pixi run -e docs tools run docs md
pixi run -e docs tools run docs build
```
