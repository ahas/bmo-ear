"""The card master's adapter: the last line it reads, and the answers it gives."""

import json
import os
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def run_adapter(*args, data_root=None):
    env = dict(os.environ)
    if data_root is not None:
        env["BMO_DATA_DIR"] = data_root
    ran = subprocess.run(
        ["python3", "adapter.py", *args],
        cwd=ROOT,
        env=env,
        stdin=subprocess.DEVNULL,
        capture_output=True,
        text=True,
        timeout=60,
    )
    last = ran.stdout.strip().splitlines()[-1]
    return ran.returncode, json.loads(last)


class AdapterTest(unittest.TestCase):
    def test_placed_names_the_placed_nodes(self):
        code, answer = run_adapter("placed", "--placed", "example-node")
        self.assertEqual(code, 0)
        self.assertTrue(answer["ok"])
        self.assertEqual(answer["nodes"], ["example-node"])

    def test_a_missing_settings_file_is_a_failing_answer(self):
        with tempfile.TemporaryDirectory() as empty:
            code, answer = run_adapter("health", "--node", "example-node", "--placed", "example-node",
                                       data_root=empty)
        self.assertEqual(code, 1)
        self.assertFalse(answer["ok"])
        self.assertEqual(answer["state"], "failing")
        self.assertIn("settings", answer["detail"])

    def test_no_node_is_a_failing_answer(self):
        code, answer = run_adapter("health", "--placed", "")
        self.assertEqual(code, 1)
        self.assertFalse(answer["ok"])
        self.assertIn("no node", answer["detail"])

    def test_another_node_is_refused(self):
        with tempfile.TemporaryDirectory() as empty:
            settings = Path(empty) / "ear"
            settings.mkdir()
            (settings / "settings.toml").write_text(
                (ROOT / "tests" / "settings-example.toml").read_text(encoding="utf-8"),
                encoding="utf-8",
            )
            code, answer = run_adapter("health", "--node", "another-node", "--placed", "another-node",
                                       data_root=empty)
        self.assertEqual(code, 1)
        self.assertFalse(answer["ok"])
        self.assertIn("example-node", answer["detail"])
        self.assertIn("another-node", answer["detail"])

    def test_stop_starts_nothing(self):
        with tempfile.TemporaryDirectory() as empty:
            settings = Path(empty) / "ear"
            settings.mkdir()
            (settings / "settings.toml").write_text(
                (ROOT / "tests" / "settings-example.toml").read_text(encoding="utf-8"),
                encoding="utf-8",
            )
            code, answer = run_adapter("stop", "--node", "example-node", "--placed", "example-node",
                                       data_root=empty)
        self.assertEqual(code, 0)
        self.assertTrue(answer["ok"])
        self.assertEqual(answer["state"], "stopped")


if __name__ == "__main__":
    unittest.main()
