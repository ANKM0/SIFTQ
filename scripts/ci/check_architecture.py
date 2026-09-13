import json
import re
import sys

from checker import repository_root, source_files


ALLOWLIST_PATH = "scripts/ci/architecture_allowlist.json"
ALLOWED_EXTERNAL = {"hono", "@cloudflare/workers-types"}
DOMAIN_PATH = "src/task.ts"
DOMAIN_SIDE_EFFECT_IMPORTS = {
    "hono",
    "@cloudflare/workers-types",
    "crypto",
    "node:crypto",
}
DOMAIN_CLASS_RE = re.compile(r"\b(?:abstract\s+)?class\b")
DOMAIN_SIDE_EFFECT_APIS = (
    ("Date", re.compile(r"\b(?:new\s+Date|Date\s*(?:\.|\())")),
    ("crypto", re.compile(r"\bcrypto\s*\.")),
    ("Math.random", re.compile(r"\bMath\s*\.\s*random\s*\(")),
    ("fetch", re.compile(r"\bfetch\s*\(")),
    ("database", re.compile(r"\.\s*(?:prepare|batch)\s*\(")),
)
IMPORT_RE = re.compile(r'\bfrom\s+["\']([^"\']+)["\']')


def load_allowlist(root) -> set[tuple[str, str]]:
    path = root / ALLOWLIST_PATH
    if not path.is_file():
        return set()
    data = json.loads(path.read_text(encoding="utf-8"))
    return {(entry["path"], entry["package"]) for entry in data}


def package_name(specifier: str) -> str:
    if specifier.startswith("@"):
        parts = specifier.split("/")
        return "/".join(parts[:2]) if len(parts) >= 2 else specifier
    return specifier.split("/")[0]


def find_domain_violations(text: str, relative_path: str) -> list[str]:
    if relative_path != DOMAIN_PATH:
        return []

    violations: list[str] = []
    for index, line in enumerate(text.splitlines(), start=1):
        if DOMAIN_CLASS_RE.search(line):
            violations.append(f"{relative_path}:{index}: domain class usage")
        for name, pattern in DOMAIN_SIDE_EFFECT_APIS:
            if pattern.search(line):
                violations.append(
                    f"{relative_path}:{index}: domain side-effect API ({name})"
                )
    return violations


def find_violations(
    text: str,
    relative_path: str,
    allowlist: set[tuple[str, str]],
) -> list[str]:
    violations: list[str] = []
    for index, line in enumerate(text.splitlines(), start=1):
        for specifier in IMPORT_RE.findall(line):
            if specifier.startswith("."):
                if "/tests/" in specifier or specifier.endswith("/tests"):
                    violations.append(
                        f"{relative_path}:{index}: tests import ({specifier})"
                    )
                continue
            package = package_name(specifier)
            if relative_path == DOMAIN_PATH and package in DOMAIN_SIDE_EFFECT_IMPORTS:
                violations.append(
                    f"{relative_path}:{index}: domain side-effect import ({specifier})"
                )
                continue
            if package in ALLOWED_EXTERNAL:
                continue
            if (relative_path, package) in allowlist:
                continue
            violations.append(
                f"{relative_path}:{index}: unexpected import ({specifier})"
            )
    return violations + find_domain_violations(text, relative_path)


def main() -> int:
    root = repository_root()
    allowlist = load_allowlist(root)
    failed = False
    for path in source_files(root, "src"):
        relative_path = path.relative_to(root).as_posix()
        text = path.read_text(encoding="utf-8")
        for violation in find_violations(text, relative_path, allowlist):
            print(violation)
            failed = True
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
