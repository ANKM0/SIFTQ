# Yoriwake

Yoriwake is a local-first task matrix application. The v1 MVP is a browser
SPA built with React, TypeScript, Vite, and dnd-kit so the project can validate
the task creation and drag-and-drop matrix workflow before adding the planned
Tauri desktop shell.

The repository also uses CoDD (Coherence-Driven Development) to keep
requirements, design notes, implementation, and tests traceable.

## Setup

Use the `Yoriwake-base` release as the standard WSL development environment:

- Release: <https://github.com/ANKM0/Yoriwake/releases/tag/Yoriwake-base>
- Template archive: `Yoriwake-base.tar`

On Windows, download `Yoriwake-base.tar` from the release page, then import it
as a WSL2 distribution:

```powershell
wsl --import Yoriwake C:\WSL\Yoriwake C:\Users\<user>\Downloads\Yoriwake-base.tar --version 2
wsl -d Yoriwake
```

Inside the WSL distribution, clone the repository and install project tools and
dependencies:

```bash
git clone git@github.com:ANKM0/Yoriwake.git
cd Yoriwake
aqua install
uv sync --all-groups
pnpm install
```

If you are using an existing Linux or WSL environment instead of the base
template, install the tools managed by `aqua.yaml` first, then run the same
`uv sync --all-groups` and `pnpm install` commands.

## Development

Start the frontend development server:

```bash
pnpm dev
```

Common frontend checks:

```bash
pnpm typecheck
pnpm lint
pnpm test
pnpm build
```

Common CoDD commands:

```bash
uv run codd version --check
uv run codd scan
uv run codd validate
uv run codd dag verify
```

## CI Checks

Run the same local checks before opening or updating a pull request:

```bash
uv sync --all-groups
pnpm install --frozen-lockfile
uv run python scripts/ci/check_commit_messages.py
uv run python scripts/ci/check_markdown.py
pnpm typecheck
pnpm lint
pnpm test
pnpm build
uv run codd version --check
uv run codd scan
uv run codd validate
uv run codd dag verify
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
