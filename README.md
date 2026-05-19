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
