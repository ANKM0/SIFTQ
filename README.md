# SIFTQ

SIFTQ is a local-first task matrix application. The current MVP is a browser
SPA built with React, TypeScript, Vite, and dnd-kit. Task state is persisted in
browser storage so the matrix can be used in a browser without a native app
shell.

The repository also uses CoDD (Coherence-Driven Development) to keep
requirements, design notes, implementation, and tests traceable.

## Setup

Use the `Yoriwake-base` release as the standard WSL development environment:

- Release: <https://github.com/ANKM0/SIFTQ/releases/tag/Yoriwake-base>
- Template archive: `siftq-base.tar`

On Windows, download `siftq-base.tar` from the release page, then import it
as a WSL2 distribution:

```powershell
wsl --import SIFTQ C:\WSL\SIFTQ C:\Users\<user>\Downloads\siftq-base.tar --version 2
wsl -d SIFTQ
```

Inside the WSL distribution, clone the repository and install project tools and
dependencies:

```bash
git clone git@github.com:ANKM0/SIFTQ.git
cd SIFTQ
aqua install
task setup
```

If you are using an existing Linux or WSL environment instead of the base
template, install the tools managed by `aqua.yaml` first, then run the same
`task setup` command.

## Development

Start the browser development app:

```bash
task frontend:dev
```

Manual Matrix MVP browser smoke check:

- Open the local Vite URL printed by `task frontend:dev`.
- Confirm `Do`, `Schedule`, `Delegate`, `Eliminate`, `Done`, and `Skipped`
  are visible.
- Create cards from multiple matrix area forms and confirm each card appears
  at the bottom of the selected area.
- Confirm blank titles cannot be submitted, duplicate titles are allowed, and
  titles over 256 characters are blocked without truncation.
- Drag cards within an area and between matrix areas, then confirm the visible
  order stays stable after each drop.
- Drop a card on `Done` and `Skipped`, then confirm it disappears from the
  matrix display.
- Confirm a long 256-character title wraps inside the card without overlapping
  nearby controls or changing the page into an unusable layout.
- Reload the browser tab, then confirm the same active task titles, areas,
  statuses, and order are restored from browser storage.

Automated coverage includes browser storage persistence, mutation-time task
refreshes in the React tests, and reload-equivalent remount restoration.

Common frontend checks:

```bash
task ci:typecheck
task ci:lint
task ci:test
task ci:build
```

Common CoDD commands:

```bash
task codd:version
task codd:scan
task codd:validate
task codd:dag
task codd:elicit
```

## sympohy Issue Automation

SIFTQ uses `sympohy` as repository-local development tooling for GitHub
Issue-driven work. It replaces the older TAKT/taqt task workflow; those
references remain only to describe the historical migration.
Generated worktrees and logs stay under `.sympohy/worktrees/` and `.sympohy/runs/`,
which are intentionally ignored by Git.

For sympohy-only setup or revalidation, run:

```bash
task setup:sympohy
task ai:sympohy:doctor
```

Common single-issue workflow commands:

```bash
task ai:sympohy:refine -- '#73'
task ai:sympohy -- '#73'
task ai:sympohy:resume -- '#73'
```

Common migration and watcher commands:

```bash
task ai:sympohy:labels:sync
task ai:sympohy:migrate -- --dry-run '#73'
task ai:sympohy:migrate -- '#73'
task ai:sympohy:migrate -- --all
task ai:sympohy:watch
task ai:sympohy:systemd:install
task ai:sympohy:systemd:status
```

See `docs/contributing/issue-execution.md` for setup requirements, label
semantics, migration notes, and the full task workflow.

## CI Checks

Run the same local checks before opening or updating a pull request:

```bash
task setup:python
task setup:frontend:ci
task ci:sympohy
task ci
```

## Repository Structure

- `src/`: React application source.
- `tests/`: repository-level tests.
- `docs/requirements/`: product and system requirements.
- `docs/design/`: feature-level design documents and design templates.
- `docs/adr/`: accepted architecture decisions.
- `.codd/`: local CoDD configuration.
- `.sympohy/`: sympohy configuration and systemd templates.

## Contributor Docs

- Branch strategy: [docs/contributing/branch-strategy.md](docs/contributing/branch-strategy.md)
- Commit messages: [docs/contributing/commit-message-format.md](docs/contributing/commit-message-format.md)
- Issue execution: [docs/contributing/issue-execution.md](docs/contributing/issue-execution.md)
- MVP spec flow: [docs/contributing/mvp-spec-flow.md](docs/contributing/mvp-spec-flow.md)
