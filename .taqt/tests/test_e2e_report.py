import importlib.util
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def load_module(name: str, *parts: str):
    path = ROOT.joinpath(*parts, f"{name}.py")
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


summarize = load_module("summarize", "scripts", "e2e")

REPORT = {
    "stats": {"duration": 1000, "expected": 2, "unexpected": 1},
    "suites": [
        {
            "title": "a.spec.ts",
            "file": "a.spec.ts",
            "specs": [
                {
                    "title": "one",
                    "tests": [{"status": "expected", "results": [{"status": "passed", "duration": 100}]}],
                },
                {
                    "title": "two",
                    "tests": [{"status": "unexpected", "results": [{"status": "failed", "duration": 50}]}],
                },
            ],
            "suites": [],
        },
        {
            "title": "b.spec.ts",
            "file": "b.spec.ts",
            "specs": [
                {
                    "title": "three",
                    "tests": [{"status": "expected", "results": [{"status": "passed", "duration": 300}]}],
                }
            ],
            "suites": [],
        },
    ],
}


def test_summarize_counts_and_orders_files_by_duration() -> None:
    summary = summarize.summarize(REPORT)
    assert summary["total_ms"] == 1000
    assert summary["tests"] == {"total": 3, "passed": 2, "failed": 1, "flaky": 0, "skipped": 0}
    assert [item["file"] for item in summary["files"]] == ["b.spec.ts", "a.spec.ts"]
    assert summary["files"][1]["duration_ms"] == 150


def test_iter_tests_inherits_file_for_nested_suites() -> None:
    report = {
        "suites": [
            {
                "title": "c.spec.ts",
                "file": "c.spec.ts",
                "specs": [],
                "suites": [
                    {
                        "title": "describe",
                        "specs": [
                            {
                                "title": "nested",
                                "tests": [
                                    {"status": "expected", "results": [{"status": "passed", "duration": 7}]}
                                ],
                            }
                        ],
                        "suites": [],
                    }
                ],
            }
        ]
    }
    assert [
        (file, test["results"][0]["duration"])
        for file, test in summarize.iter_tests(report["suites"][0])
    ] == [("c.spec.ts", 7)]


def test_format_summary_reports_total() -> None:
    rendered = summarize.format_summary(summarize.summarize(REPORT))
    assert "1.0s total" in rendered
    assert "3 tests" in rendered
