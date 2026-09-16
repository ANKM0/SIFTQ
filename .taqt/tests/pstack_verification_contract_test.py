import sys
from pathlib import Path

import pytest
import yaml

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

from loop.llm import _build_prompt
from loop.verification import E2E_COMMANDS, FAST_COMMANDS

REPO_ROOT = Path(__file__).resolve().parents[2]
SKILLS_ROOT = REPO_ROOT / ".agents" / "skills"

PSTACK_VERIFICATION_SKILLS = (
    "create-verification-skill",
    "maintain-verification-skill",
    "principle-prove-it-works",
    "principle-fix-root-causes",
    "principle-sequence-verifiable-units",
    "principle-test-behavior-not-implementation",
    "tdd",
)


def _frontmatter(path: Path) -> dict:
    text = path.read_text(encoding="utf-8")
    assert text.startswith("---\n"), f"{path} must start with frontmatter"
    end = text.index("\n---", 4)
    payload = yaml.safe_load(text[4:end])
    assert isinstance(payload, dict), f"{path} frontmatter must be a mapping"
    return payload


@pytest.mark.parametrize("name", PSTACK_VERIFICATION_SKILLS)
def test_pstack_verification_skill_is_discoverable(name: str) -> None:
    skill_path = SKILLS_ROOT / name / "SKILL.md"

    assert skill_path.is_file(), f"missing skill: {name}"
    frontmatter = _frontmatter(skill_path)
    assert frontmatter.get("name") == name
    description = frontmatter.get("description")
    assert isinstance(description, str) and description.strip()


def test_verification_runs_e2e_after_fast_checks() -> None:
    assert "task ci:test:e2e" in E2E_COMMANDS
    assert "task ci:test:e2e" not in FAST_COMMANDS


def _prompt(role: str, *, readonly: bool = False) -> str:
    return _build_prompt(
        task={"id": "TASK-1"},
        step={"id": "step-1"},
        agent={"role": role, "readonly": readonly},
        context={},
    )


@pytest.mark.parametrize(
    ("role", "readonly"),
    [("implementation", False), ("implementation_fixer", False), ("checker", True)],
)
def test_implementation_and_checker_prompts_include_verification_principles(
    role: str, readonly: bool
) -> None:
    prompt = _prompt(role, readonly=readonly)

    assert "principle-prove-it-works" in prompt
    assert "principle-fix-root-causes" in prompt
    assert "principle-test-behavior-not-implementation" in prompt


def test_other_roles_do_not_include_verification_principles() -> None:
    assert "principle-prove-it-works" not in _prompt("design")
    assert "principle-fix-root-causes" not in _prompt("test_author")
    assert "principle-test-behavior-not-implementation" not in _prompt("test_author")
