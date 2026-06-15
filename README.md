# SIFTQ

SIFTQ is a local-first task matrix application. The v1 MVP is a browser
SPA built with React, TypeScript, Vite, and dnd-kit so the project can validate
the task creation and drag-and-drop matrix workflow before adding the planned
Tauri desktop shell.

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

Start the frontend development server:

```bash
task frontend:dev
```

Manual Matrix MVP smoke check:

- Open the local Vite URL printed by `task frontend:dev`.
- Confirm `Do`, `Schedule`, `Delegate`, `Eliminate`, `Done`, and `Skipped`
  are visible.
- Create cards from multiple matrix area forms and confirm each card appears
  at the bottom of the selected area.
- Confirm blank titles cannot be submitted, duplicate titles are allowed, and
  titles over 256 characters are blocked without truncation.
- Drag cards within an area and between matrix areas, then confirm the visible
  order stays stable in the current browser session.
- Drop a card on `Done` and `Skipped`, then confirm it disappears from the
  matrix display.
- Confirm a long 256-character title wraps inside the card without overlapping
  nearby controls or changing the page into an unusable layout.

Manual v7 settings smoke check:

- Open `Settings`, change all four matrix area labels plus `Done` and
  `Skipped`, click `Save labels`, return to the matrix, and confirm every
  updated label is shown in the matrix and terminal drop areas.
- For restart persistence, run the app in a host that provides the SQLite
  settings connection, change and save the labels, restart the app, and confirm
  the saved labels are restored on the matrix page. The plain Vite development
  server uses the in-memory fallback and cannot prove restart persistence by
  itself.
- Reopen `Settings`, replace one or more labels with only spaces, and confirm
  `Save labels` is disabled with `Area label must not be empty.` Confirm the
  previously saved labels remain unchanged after returning to the matrix.
- Reopen `Settings`, click `Restore defaults`, return to the matrix, and confirm
  the labels return to `Do`, `Schedule`, `Delegate`, `Eliminate`, `Done`, and
  `Skipped`.
- Restart the SQLite-backed app again and confirm the restored default labels
  are still shown.

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

## CI Checks

Run the same local checks before opening or updating a pull request:

```bash
task setup:python
task setup:frontend:ci
task ci
```

## Repository Structure

- `src/`: React application source.
- `tests/`: repository-level tests.
- `docs/requirements/`: product and system requirements.
- `docs/design/`: issue-level design notes.
- `docs/adr/`: accepted architecture decisions.
- `.codd/`: local CoDD configuration.

## Contributor Docs

- Branch strategy: `docs/contributing/branch-strategy.md`
- Commit messages: `docs/contributing/commit-message-format.md`
- Issue execution: `docs/contributing/issue-execution.md`
