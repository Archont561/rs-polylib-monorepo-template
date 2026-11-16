<!--
  Generated file — do not edit PULL_REQUEST_TEMPLATE.md by hand.

  Source template : templates/github/PULL_REQUEST_TEMPLATE.md.j2
  Regenerate with : pixi run tools run docs write
-->

# Pull Request

## Summary

- What changed and why?

## Affected Ecosystems

- [ ] Rust crate `crates/polylib`
- [ ] Rust crate `crates/polylib-core`
- [ ] Rust crate `crates/polylib-ffi`
- [ ] Rust crate `crates/polylib-js`
- [ ] Rust crate `crates/polylib-py`
- [ ] Rust crate `crates/polylib-wasm`
- [ ] Python package `packages/polylib-py`
- [ ] TypeScript package `@polylib/config`
- [ ] TypeScript package `@polylib/polylib-js`
- [ ] TypeScript package `@polylib/polylib`
- [ ] TypeScript package `@polylib/polylib-wasm`
- [ ] Conformance specifications (`conformance/*.feature`)
- [ ] Tooling, policy, CI, or documentation

## Verification Checklist

- [ ] `pixi run -e full tools check` and `pixi run -e full tools skill --check`
- [ ] `pixi run -e full tools run check` (alint, policy tests, docs, formatting, linters)
- [ ] `pixi run -e full tools run test` (Rust, Python, TypeScript, conformance)
- [ ] `pixi run -e full tools run rust compat`, `python compat`, and `ts compat`
- [ ] Updated `templates/` and ran `docs write` if docs or GitHub templates changed
