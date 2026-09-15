from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SKILL = ROOT / ".agents/skills/issue-creator/SKILL.md"


def test_issue_creator_requires_effect_measurement_for_loop_changes() -> None:
    text = SKILL.read_text(encoding="utf-8").lower()

    required_markers = (
        "`.taqt/loops/`",
        "`.taqt/scripts/loop/`",
        "ac/dod",
        "effect measurement",
        "measurement target",
        "harness",
        "command",
        "observed result",
        "adoption criterion",
        "loop-effect-measurement",
    )
    missing = [marker for marker in required_markers if marker not in text]

    assert missing == []
