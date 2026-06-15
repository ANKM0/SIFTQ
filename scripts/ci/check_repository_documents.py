#!/usr/bin/env python3
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import re
import subprocess
from typing import Iterable
from urllib.parse import unquote, urlparse

import yaml


ROOT = Path(__file__).resolve().parents[2]
DOCUMENT_PATTERNS = ("*.md", "*.yaml", "*.yml")
YAML_SUFFIXES = {".yaml", ".yml"}
SKILL_NAME = "SKILL.md"
MARKDOWN_LINK_RE = re.compile(
    r"(?<!!)\[[^\]]+\]\(([^)\s]+)(?:\s+\"[^\"]*\")?\)"
)
REFERENCE_LINK_RE = re.compile(r"^\s*\[[^\]]+\]:\s*(\S+)", re.MULTILINE)
IGNORED_SCHEMES = {"http", "https", "mailto", "app"}


@dataclass(frozen=True)
class ValidationIssue:
    path: Path
    message: str
    line: int | None = None

    def format(self) -> str:
        if self.line is None:
            return f"{self.path}: {self.message}"
        return f"{self.path}:{self.line}: {self.message}"


def tracked_document_paths(root: Path = ROOT) -> list[Path]:
    result = subprocess.run(
        ["git", "ls-files", "-z", "--", *DOCUMENT_PATTERNS],
        cwd=root,
        check=True,
        stdout=subprocess.PIPE,
    )
    return sorted(
        Path(item) for item in result.stdout.decode("utf-8").split("\0") if item
    )


def validate_documents(root: Path, paths: Iterable[Path]) -> list[ValidationIssue]:
    issues: list[ValidationIssue] = []
    for relative_path in sorted(paths):
        path = root / relative_path
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError as error:
            issues.append(
                ValidationIssue(
                    relative_path,
                    f"is not readable as UTF-8: {error}",
                )
            )
            continue
        except OSError as error:
            issues.append(ValidationIssue(relative_path, f"cannot be read: {error}"))
            continue

        if path.suffix in YAML_SUFFIXES:
            try:
                list(yaml.safe_load_all(text))
            except yaml.YAMLError as error:
                issues.append(
                    ValidationIssue(relative_path, f"is not readable YAML: {error}")
                )

        if path.name == SKILL_NAME:
            issues.extend(validate_skill_references(root, relative_path, text))

    return issues


def validate_skill_references(
    root: Path, skill_path: Path, text: str
) -> list[ValidationIssue]:
    issues: list[ValidationIssue] = []
    seen: set[tuple[str, int]] = set()
    for target, offset in _reference_targets(text):
        normalized = _normalize_reference_target(target)
        if normalized is None or _is_template_reference(normalized):
            continue
        line = text.count("\n", 0, offset) + 1
        key = (normalized, line)
        if key in seen:
            continue
        seen.add(key)
        if _reference_exists(root, skill_path.parent, normalized):
            continue
        issues.append(
            ValidationIssue(
                skill_path,
                f"reference target does not exist: {target}",
                line,
            )
        )
    return issues


def _reference_targets(text: str) -> list[tuple[str, int]]:
    targets: list[tuple[str, int]] = []
    for regex in (MARKDOWN_LINK_RE, REFERENCE_LINK_RE):
        targets.extend(
            (match.group(1), match.start(1)) for match in regex.finditer(text)
        )
    return targets


def _normalize_reference_target(target: str) -> str | None:
    target = unquote(target.strip().strip("'\""))
    if target.startswith("<") and target.endswith(">"):
        target = target[1:-1]
    if not target or target.startswith("#"):
        return None
    parsed = urlparse(target)
    if parsed.scheme in IGNORED_SCHEMES:
        return None
    if parsed.scheme or parsed.netloc:
        return None
    target = target.split("#", 1)[0].split("?", 1)[0].rstrip()
    if not target:
        return None
    return target.rstrip("/")


def _is_template_reference(target: str) -> bool:
    return any(marker in target for marker in ("<", ">", "*", "{", "}"))


def _reference_exists(root: Path, skill_dir: Path, target: str) -> bool:
    target_path = Path(target)
    if target_path.is_absolute():
        return target_path.exists()
    candidates = (root / skill_dir / target_path, root / target_path)
    return any(candidate.exists() for candidate in candidates)


def main() -> int:
    issues = validate_documents(ROOT, tracked_document_paths(ROOT))
    for issue in issues:
        print(issue.format())
    return 1 if issues else 0


if __name__ == "__main__":
    raise SystemExit(main())
