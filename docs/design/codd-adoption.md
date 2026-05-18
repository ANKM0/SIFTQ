---
codd:
  node_id: design:codd-adoption
  type: design
  status: draft
  depends_on:
    - id: req:yoriwake-system
      relation: depends_on
      semantic: governance
---

# CoDD Adoption Design

Yoriwake uses a project-local `.codd/codd.yaml` file to define the CoDD scan
surface and verification defaults.

## Configuration

- Implementation roots: `src/`
- Test roots: `tests/`
- Documentation roots: `docs/`
- Tooling config: `aqua.yaml`
- Graph output: `.codd/scan`

## Verification

No language-specific typecheck or test command is configured yet because the
repository does not currently contain application source code. Add concrete
commands to `.codd/codd.yaml` when the runtime stack is introduced.

## Dependency Management

Developer tools are installed through aqua. Python packages, including
`codd-dev`, are declared in `pyproject.toml` and installed through uv.
