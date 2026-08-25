from pathlib import Path


EXCLUDED_DIRS = {".git", ".venv", "node_modules", "dist", "coverage"}


def repository_root() -> Path:
    for path in Path(__file__).resolve().parents:
        if (path / "pyproject.toml").is_file() and (path / "package.json").is_file():
            return path
    raise RuntimeError("repository root not found")


def source_files(root: Path, directory: str) -> list[Path]:
    base = root / directory
    if not base.is_dir():
        return []
    return sorted(
        path
        for path in base.rglob("*")
        if path.suffix in {".ts", ".tsx"}
        and not any(part in EXCLUDED_DIRS for part in path.parts)
    )
