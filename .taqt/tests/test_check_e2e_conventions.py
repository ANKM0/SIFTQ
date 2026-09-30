import importlib.util
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts" / "ci"))


def load_module(name: str):
    path = ROOT / "scripts" / "ci" / f"{name}.py"
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


conventions = load_module("check_e2e_conventions")


def empty_allowlist() -> dict[str, list[str]]:
    return {key: [] for key in conventions.ALLOWLIST_KEYS}


def test_allows_clean_spec() -> None:
    text = 'test("works", async ({ page }) => {\n  await expect(page).toHaveTitle(/x/);\n});\n'
    assert conventions.find_spec_violations(text, "tests/e2e/x.spec.ts", empty_allowlist()) == []


def test_flags_networkidle_with_line() -> None:
    text = 'test("x", async ({ page }) => {\n  await page.waitForLoadState("networkidle");\n});\n'
    assert conventions.find_spec_violations(text, "tests/e2e/x.spec.ts", empty_allowlist()) == [
        "tests/e2e/x.spec.ts:2: networkidle wait (use web-first assertions)"
    ]


def test_flags_ui_password_login() -> None:
    text = 'await page.getByLabel("Password").fill("x");\n'
    assert conventions.find_spec_violations(text, "tests/e2e/x.spec.ts", empty_allowlist()) == [
        "tests/e2e/x.spec.ts:1: UI password login (use the auth storageState fixture)"
    ]


def test_flags_serial_mode() -> None:
    text = 'test.describe.configure({ mode: "serial" });\n'
    assert conventions.find_spec_violations(text, "tests/e2e/x.spec.ts", empty_allowlist()) == [
        "tests/e2e/x.spec.ts:1: serial mode (isolate data and run in parallel)"
    ]


def test_flags_oversized_file() -> None:
    text = "".join(f'test("t{i}", async () => {{}});\n' for i in range(21))
    violations = conventions.find_spec_violations(text, "tests/e2e/x.spec.ts", empty_allowlist())
    assert violations == [
        "tests/e2e/x.spec.ts:1: 21 tests exceed the 20-test file limit (split by concern)"
    ]


def test_allowlist_suppresses_known_violations() -> None:
    allowlist = empty_allowlist()
    allowlist["serial"].append("tests/e2e/x.spec.ts")
    text = 'test.describe.configure({ mode: "serial" });\n'
    assert conventions.find_spec_violations(text, "tests/e2e/x.spec.ts", allowlist) == []


def test_flags_trace_without_retries() -> None:
    text = 'retries: 0,\ntrace: "on-first-retry",\n'
    assert conventions.find_config_violations(text, ".config/playwright.config.ts", empty_allowlist()) == [
        ".config/playwright.config.ts:1: trace on-first-retry with retries 0 never records "
        "(use retain-on-failure or set retries)"
    ]


def test_flags_fully_parallel_with_single_worker() -> None:
    text = "fullyParallel: true,\nworkers: 1,\n"
    assert conventions.find_config_violations(text, ".config/playwright.config.ts", empty_allowlist()) == [
        ".config/playwright.config.ts:1: fullyParallel true with workers 1 does not run in "
        "parallel (raise workers or drop fullyParallel)"
    ]
