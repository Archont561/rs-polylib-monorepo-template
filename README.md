<!--
  Generated file — do not edit README.md by hand.

  Source template : templates/README.md.j2
  Generator       : Jinja2 via tools/docs/write.py
  Regenerate with : pixi run tools run docs write
  Verify in CI    : pixi run tools run docs check
-->

# Polyglot library monorepo template (`polylib`)

**Write core logic once in Rust—ship idiomatic libraries to crates.io, PyPI, npm, Kotlin, Swift, and Ruby.** Every target shares verified cross-language conformance and offline-ready Pixi environments.

Version: `0.1.0` | Rust MSRV: `1.88` | License: [MIT](LICENSE)

## Architecture

One pure Rust core (`crates/polylib-core`, `#![forbid(unsafe_code)]`) powers six ecosystems. Shared Gherkin [`conformance/*.feature`](conformance/slug.feature) specifications linted with `gherlint` verify every target:

| Ecosystem | Published Artifact | Source Path | Binding / Build Tool | Compatibility Gate |
| :--- | :--- | :--- | :--- | :--- |
| **Rust** | `polylib` (metacrate) + `polylib-core` | [`crates/polylib`](crates/polylib/README.md), [`crates/polylib-core`](crates/polylib-core/README.md) | Cargo (`edition = "2024"`, `resolver = "3"`) | `rust compat` (feature matrix, `cargo package --list`, unpacked `.crate` consumer, MSRV) |
| **Python** | `polylib` (`cp310-abi3` wheels) | [`packages/polylib-py`](packages/polylib-py/README.md) + [`crates/polylib-py`](crates/polylib-py/README.md) | `PyO3` + `maturin` | `python compat` (wheel/sdist, `METADATA`, isolated venv) + `tox` (Python 3.10–3.14) |
| **TypeScript (Facade)** | `@polylib/polylib` (ESM unified facade) | [`packages/polylib-ts`](packages/polylib-ts/README.md) | `bunup` (automatically selects NAPI-RS with WASM fallback + `/native`, `/wasm` subpaths) | `ts compat` (`publint --strict`, `attw`, native & WASM-fallback consumers) |
| **TypeScript (WASM)** | `@polylib/polylib-wasm` (ESM + `.wasm`) | [`packages/polylib-wasm`](packages/polylib-wasm/README.md) + [`crates/polylib-wasm`](crates/polylib-wasm/README.md) | `wasm-bindgen` + `bunup` | `ts compat` (`publint --strict`, `attw`, isolated consumer) + Bun & Node.js matrices |
| **TypeScript (NAPI-RS)** | `@polylib/polylib-js` (ESM + `.node`) | [`packages/polylib-js`](packages/polylib-js/README.md) + [`crates/polylib-js`](crates/polylib-js/README.md) | `napi-rs` + `bunup` | `ts compat` (`publint --strict`, `attw`, isolated consumer) + Bun & Node.js matrices |
| **Kotlin (JVM)** | `dev.polylib:polylib` (JAR + JNA) | [`packages/polylib-kt`](packages/polylib-kt/README.md) + [`crates/polylib-ffi`](crates/polylib-ffi/README.md) | `UniFFI` + Gradle + JNA | `ffi compat --target kotlin` (Gradle `check` + JAR native verification + Cucumber-JVM) |
| **Swift** | `Polylib` (SwiftPM package) | [`packages/polylib-swift`](packages/polylib-swift/README.md) + [`crates/polylib-ffi`](crates/polylib-ffi/README.md) | `UniFFI` + SwiftPM | `ffi compat --target swift` (SwiftPM artifacts + macOS CI `swift test`) |
| **Ruby** | `polylib` (RubyGems `.gem` + `ffi`) | [`packages/polylib-rb`](packages/polylib-rb/README.md) + [`crates/polylib-ffi`](crates/polylib-ffi/README.md) | `UniFFI` + Bundler + Ruby `ffi` | `ffi compat --target ruby` (`gem build` + isolated `GEM_HOME` smoke + Cucumber) |

## Workspace layout

- **Rust crates (6):** `crates/polylib`, `crates/polylib-core`, `crates/polylib-ffi`, `crates/polylib-js`, `crates/polylib-py`, `crates/polylib-wasm` (publishable: `polylib`, `polylib-core`)
- **Python packages (1):** `packages/polylib-py`
- **TypeScript packages (4):** `@polylib/config`, `@polylib/polylib-js`, `@polylib/polylib`, `@polylib/polylib-wasm`
- **UniFFI packages (3):** `packages/polylib-kt`, `packages/polylib-rb`, `packages/polylib-swift`
- **Documentation apps (1):** `apps/docs`
- **Shared contracts and automation:** `conformance/*.feature` specs run across `rstest-bdd`, `pytest-bdd`, `@aboviq/bun-test-cucumber`, Cucumber-JVM, XCTest, and Cucumber Ruby. Nested Tasknest `@tool` tasks live under `tools/` alongside `templates/`, `.alint/`, `.agents/skills/`, and `backlog/`.

## Quickstart

Install [Pixi](https://pixi.sh/), then bootstrap the locked workspace, native and WASM bindings, and git hooks:

```sh
pixi install -e full --locked
pixi run -e full tools run repo install
pixi run -e full tools run bindings build
pixi run -e full tools run repo hooks
```

All repository and agent automation runs through the single Pixi task `pixi run [-e <env>] tools` (Python Tasknest `0.4.0`):

```sh
pixi run tools ls                           # Discover all nested tasks and package scripts
pixi run -e full tools run check            # Policy, schemas, docs, formatting, and linters
pixi run -e full tools run test             # Rust + Python + TypeScript tests & conformance
pixi run -e full tools run coverage         # Audit coverage/<lang>/ reports against the 90% threshold
pixi run -e full tools run compat           # Rust + Python + TypeScript/npm compatibility gates
pixi run -e full tools run tox              # Unified tox compatibility runner (-m compat/python/npm/rust/ffi/all)
pixi run -e full tools run rust compat      # Feature matrix, cargo package, isolated .crate test
pixi run -e full tools run rust tox         # Tox Rust compatibility envs (features, packages, consumer, compat)
pixi run -e full tools run python compat    # Maturin wheel/sdist, METADATA, offline venv smoke
pixi run -e full tools run python tox       # Tox Python compatibility matrix (py310-py314, wheel/sdist)
pixi run -e full tools run ts compat        # Tarball pack, publint, attw, Bun, Node.js, and tsc
pixi run -e full tools run ts tox           # Tox npm compatibility envs (pack, bun, node, types, compat)
pixi run -e ffi tools run ffi build         # Compile polylib-ffi & generate Kotlin, Swift, Ruby
pixi run -e ffi tools run ffi test          # Run Kotlin (Gradle/Cucumber) & Ruby (Minitest/Cucumber)
pixi run -e ffi tools run ffi compat        # Verify Kotlin JAR (standalone JVM), Swift C-ABI/SwiftPM, Ruby gem
pixi run -e ffi tools run ffi tox           # Tox UniFFI compatibility envs (kotlin-compat, ruby-compat, swift-compat)
```

## Quality and policy guardrails

- **Single automation entrypoint:** `pixi.toml` declares only `[tasks] tools = "python -B -m tasknest"`, root `package.json` forbids `"scripts"`, and `lefthook.yml` delegates every hook through `pixi run [-e <env>] tools`.
- **Clean Code and boundaries:** `rude` + `rude-clean-code` (`CC0`–`CC9`, `CC704`, `CC804`), `ruff`, strict `mypy`, `cargo clippy -- -D warnings`, `cargo-deny`, `biome`, `rumdl`, `vale` (Microsoft preset), `lychee`, `gherlint`, `actionlint`, and `.alint.yml` enforce repository hygiene.
- **Per-language coverage (`coverage/<lang>/`, 90% threshold):** Each language writes its own report (`lcov.info` or `jacoco.xml`) and enforces a 90% line coverage threshold locally and in CI. Workflows upload each language independently to GitHub Actions artifacts (`coverage-<lang>`) and Codecov (`.codecov.yml` flags `rust`, `python`, `ts`, `kotlin`, `ruby`, and `swift`).
- **Offline sandbox:** `pixi-sandbox.toml` packs Linux (`linux-64`) locked environments and vendored Cargo sources (`cargo_vendor = true`) via `scripts/restore.sh`. Optional `kt`, `rb`, and `ffi` environments stay outside the `developer` bundle to preserve transport budgets.
- **Build and release workflows:** `.github/workflows/build.yml` compiles and packs all six ecosystems, generates `report.json`, renders `report.md` with Jinja2 (`templates/build-report.md.j2`), and uploads `SHA256SUMS.txt`. `.github/workflows/publish.yml` publishes via OIDC Trusted Publishing to crates.io, PyPI, npm, and RubyGems, plus Maven Central, GitHub Packages, and GitHub Releases in isolated environments.
- **Documentation site:** `apps/docs` exports a static Fumadocs site (`pixi run -e docs tools run docs build`). `.github/workflows/pages.yml` always validates and builds the site, and automatically deploys only when GitHub Pages uses GitHub Actions (`ENABLE_PAGES=false` opts out).
- **Templated docs and GitHub forms:** Edit `templates/` and run `pixi run tools run docs write`. CI verifies template parity with `docs check`.

See [AGENTS.md](AGENTS.md) for coding-agent instructions and [`.agents/skills/project-tools/SKILL.md`](.agents/skills/project-tools/SKILL.md) for the generated task catalog.

## License

This project uses the [MIT License](LICENSE).
