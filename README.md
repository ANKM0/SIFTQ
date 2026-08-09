# SIFTQ

SIFTQ is a local-first task matrix application. The current MVP is a browser
SPA built with React, TypeScript, Vite, and dnd-kit. Task state is persisted in
browser storage so the matrix can be used in a browser without a native app
shell.

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
refreshes in the React tests, reload-equivalent remount restoration, and the
Playwright terminal-drop regression checks. `task ci:test` and `task ci` install
the required Chromium browser into `tmp/playwright-browsers` automatically
before the E2E suite runs. When the local machine or sandbox does not provide
the Linux shared libraries that Chromium needs, `task ci:test` skips only the
Playwright segment locally and keeps the full E2E enforcement in CI.

Common frontend checks:

```bash
task ci:typecheck
task ci:lint
task ci:test
task ci:build
```

## Loop Engineering

The loop engineering direction is tracked in `docs/design/#134.md`. taqt
is the main task/workflow owner, while GitHub monitoring and other external
integrations are script adapters.

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
- `docs/wireframes/`: UI wireframes and wireframe templates.
- `docs/design/`: PR-scoped design docs.
