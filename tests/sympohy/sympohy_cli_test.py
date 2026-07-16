from __future__ import annotations

import io
import json
from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from scripts.sympohy import cli


class SympohyCliTest(unittest.TestCase):
    def test_observe_apply_reviews_candidates_without_executing_by_default(self) -> None:
        captured: dict[str, object] = {}

        class FakeStore:
            def __enter__(self) -> FakeStore:
                return self

            def __exit__(self, _exc_type: object, _exc: object, _tb: object) -> None:
                return None

            def apply_improvements(self, **kwargs: object) -> dict[str, object]:
                captured.update(kwargs)
                return {"schema_version": 1, "execution": {"executed": True}}

        stdout = io.StringIO()
        with (
            patch("scripts.sympohy.cli.load_config", return_value=SimpleNamespace()),
            patch("scripts.sympohy.cli.ObservationStore", return_value=FakeStore()),
            patch("sys.stdout", stdout),
        ):
            exit_code = cli.main(
                [
                    "observe-apply",
                    "--db",
                    "/tmp/observations.sqlite3",
                    "--issue",
                    "126",
                ]
            )

        self.assertEqual(exit_code, 0)
        self.assertFalse(captured["execute"])
        self.assertEqual(captured["issue"], 126)
        self.assertEqual(captured["cwd"], Path.cwd())
        payload = json.loads(stdout.getvalue())
        self.assertEqual(payload["execution"]["executed"], True)

    def test_observe_apply_executes_only_with_explicit_flag(self) -> None:
        captured: dict[str, object] = {}

        class FakeStore:
            def __enter__(self) -> FakeStore:
                return self

            def __exit__(self, _exc_type: object, _exc: object, _tb: object) -> None:
                return None

            def apply_improvements(self, **kwargs: object) -> dict[str, object]:
                captured.update(kwargs)
                return {"schema_version": 1}

        stdout = io.StringIO()
        with (
            patch("scripts.sympohy.cli.load_config", return_value=SimpleNamespace()),
            patch("scripts.sympohy.cli.ObservationStore", return_value=FakeStore()),
            patch("sys.stdout", stdout),
        ):
            exit_code = cli.main(
                [
                    "observe-apply",
                    "--db",
                    "/tmp/observations.sqlite3",
                    "--issue",
                    "126",
                    "--execute",
                ]
            )

        self.assertEqual(exit_code, 0)
        self.assertTrue(captured["execute"])
