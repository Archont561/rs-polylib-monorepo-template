# Contributing

Thanks for taking the time to contribute. This document covers the workflow, the
commit format that drives releases, and the checks that must pass before a pull
request merges. For the architectural rules that apply to code changes, read
[`AGENTS.md`](AGENTS.md) first; this file doesn't repeat them.

## Where to start

- **Bugs and feature requests:** open an issue using the templates under
  [`.github/ISSUE_TEMPLATE`](.github/ISSUE_TEMPLATE).
- **Security reports:** don't open a public issue. Report the problem privately
  through GitHub's [private vulnerability reporting](https://github.com/Archont561/rs-polylib-monorepo-template/security/advisories/new)
  so a fix can ship before the details are public.
- **Questions about the code:** read [`docs/`](docs/README.md), which builds the
  published documentation site.

## Set up the workspace

This repository pins every tool through [Pixi](https://pixi.sh/) and every
JavaScript dependency through [Bun](https://bun.sh/). Install both, then
bootstrap the locked workspace:

```sh
pixi install -e full --locked
pixi run -e full tools run repo install
pixi run -e full tools run bindings build
pixi run -e full tools run repo hooks
```

The last command installs the Git hooks. Once installed, the `commit-msg` hook
validates every commit message and the `pre-commit` hook runs the policy checks.

## Make a change

1. Branch from `main`.
2. Make the change, updating the Gherkin specs in `conformance/` when public API
   behavior changes.
3. Run the checks for the area you touched:

   ```sh
   pixi run -e full tools run check     # policy, docs, formatting, and linters
   pixi run -e full tools run test      # Rust, Python, TypeScript, and conformance
   ```

   `tools run check` is the same gate CI runs, so a clean local run usually means
   a green pull request. Add `tools run coverage` after `test` to audit the 90%
   per-language threshold.
4. Commit using a Conventional Commit message (see below).
5. Open a pull request and describe the change. CI runs automatically; the
   `CI Required Gate` job is the one that must pass.

## Commit messages

Every commit follows the [Conventional Commits](https://www.conventionalcommits.org/)
format because release notes are generated from them:

```text
<type>(<scope>): <description>

[optional body]

[optional footer]
```

Use the `commit-msg` hook, or run it directly:

```sh
pixi run -e lint tools run repo commit_msg --message-file <path>
```

### Types

The type decides where the commit appears in the changelog, as declared in
[`.convco`](.convco):

| Type | Changelog section | Use for |
| :--- | :--- | :--- |
| `feat` | Features | A new capability |
| `fix` | Bug Fixes | A defect fix |
| `perf` | Performance | A measured speed or memory improvement |
| `refactor` | Refactoring | A change that alters no external behavior |
| `revert` | Reverts | Reverting an earlier commit |
| `docs` | Documentation | Documentation only |
| `build` | Build System | Cargo, Pixi, or Bun changes |
| `ci` | hidden | Workflow and automation changes |
| `test` | hidden | Test-only changes |
| `chore` | hidden | Maintenance that fits nothing else |
| `style` | hidden | Formatting only |

Hidden types still validate, but they stay out of the release notes.

### Scopes

Preferred scopes are enforced by `scopeRegex` in `.convco`:

```text
tools  docs   policy  release  bindings  ci
deps   readme vale    agents   compat    coverage  backlog
```

A scope is optional, but prefer one for anything that touches a single area.

### Breaking changes

Mark a breaking change with a `!` after the type or scope, and explain it in the
footer:

```text
feat(core)!: drop the deprecated summarize() overload

BREAKING CHANGE: callers must pass a score slice instead of varargs.
```

## How releases are generated

Releases are cut from `main` and the GitHub Release body is generated from the
commits since the previous tag. Nothing is written by hand.

```sh
pixi run -e lint tools run release changelog --output RELEASE_NOTES.md --tag v0.2.0
```

That command runs `convco changelog` against the repository history, applies the
types and scopes from `.convco`, and appends the build report when
`--report-md` points at one. `.github/workflows/publish.yml` runs the same
command and blocks the release if convco can't produce a changelog, so a
malformed commit message is caught long before a tag is pushed.

Because the changelog is derived from history, the practical rule is this: a
commit message that doesn't parse is a commit that disappears from the
release notes.

## Continuous integration checks

| Gate | What it covers |
| :--- | :--- |
| Policy, Docs & Static Linters | `alint`, schemas, `docs check`, `rumdl`, `vale`, `ruff`, `mypy`, `rude`, Biome, `actionlint` |
| Rust | Clippy, tests, `cargo-deny`, `.crate` compatibility, MSRV |
| Python & TypeScript | Bindings, tests, coverage, `publint`/`attw`, isolated consumers |
| UniFFI | Kotlin, Swift, and Ruby bindings |
| Compatibility matrices | Python 3.10–3.14, Node 20, 22, and 24, Bun 1.1, 1.4, and latest, JDK 17, 21, and 25, Ruby 3.2, 3.3, and 3.4, Swift |

Pushes to `main` skip the version matrices and run the single-job checks only;
every pull request runs the full set.

## Conventions worth knowing

- **Generated files:** never edit `README.md`, `AGENTS.md`, the issue and pull
  request templates, or `.agents/skills/project-tools/SKILL.md` by hand. Edit
  `templates/` or `tools/` and regenerate with `pixi run tools run docs write`.
  `tools run check` fails when a generated file drifts from its source.
- **One automation entrypoint:** repository automation runs only through
  `pixi run [-e <env>] tools`. Don't add scripts to root `package.json` or tasks
  to `pixi.toml`.
- **Policy as data:** repository rules live in `.alint.yml` with schema tests
  under `.alint/tests/`. Add a rule there rather than hard-coding a check.

## License

By contributing, you agree that your contributions are licensed under the
[MIT License](LICENSE).
