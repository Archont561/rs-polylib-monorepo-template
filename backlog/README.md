# Backlog

Offline-first, Git-native project management powered by **Backlog.md**. Tasks, milestones, specifications, and architectural decisions travel in the same commits and PRs as the library code they govern.

## Directory Layout

- `config.yml` — Local-only configuration (`remote_operations: false`, `filesystem_only: true`, `bypass_git_hooks: false`, `auto_commit: false`).
- `decisions/` — Architectural Decision Records (`ADR-*` / `decision-*`).
- `docs/` — Long-lived library architecture specifications and compatibility runbooks.
- `milestones/` — Milestone records grouping cross-language releases.
- `tasks/` — Work items (`LIB-*`) with YAML frontmatter, Acceptance Criteria, and Definition of Done checklists.
