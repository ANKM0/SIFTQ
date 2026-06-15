from __future__ import annotations

from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from scripts.ci.check_repository_documents import validate_documents


class RepositoryDocumentsTest(unittest.TestCase):
    def test_reports_unreadable_yaml(self) -> None:
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            path = root / "broken.yaml"
            path.write_text("key: [unterminated\n", encoding="utf-8")

            issues = validate_documents(root, [Path("broken.yaml")])

            self.assertEqual(len(issues), 1)
            self.assertEqual(issues[0].path, Path("broken.yaml"))
            self.assertIn("is not readable YAML", issues[0].message)

    def test_reports_missing_concrete_skill_reference(self) -> None:
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            skill_dir = root / ".agents" / "skills" / "sample"
            skill_dir.mkdir(parents=True)
            skill = skill_dir / "SKILL.md"
            skill.write_text("Use [missing](references/missing.md).\n", encoding="utf-8")

            issues = validate_documents(
                root,
                [Path(".agents/skills/sample/SKILL.md")],
            )

            self.assertEqual(len(issues), 1)
            self.assertEqual(issues[0].path, Path(".agents/skills/sample/SKILL.md"))
            self.assertEqual(issues[0].line, 1)
            self.assertIn("references/missing.md", issues[0].message)

    def test_accepts_existing_skill_relative_reference(self) -> None:
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            skill_dir = root / ".agents" / "skills" / "sample"
            reference_dir = skill_dir / "references"
            reference_dir.mkdir(parents=True)
            (reference_dir / "guide.md").write_text("# Guide\n", encoding="utf-8")
            skill = skill_dir / "SKILL.md"
            skill.write_text("Use [guide](references/guide.md).\n", encoding="utf-8")

            issues = validate_documents(
                root,
                [
                    Path(".agents/skills/sample/SKILL.md"),
                    Path(".agents/skills/sample/references/guide.md"),
                ],
            )

            self.assertEqual(issues, [])


if __name__ == "__main__":
    unittest.main()
