"""The executable as the tool host calls it: the handed object answered, and every failure named."""

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def call(entry, arguments, data_root, protocol=1, session=None, env=None):
    handed = {
        "protocol": protocol,
        "kind": "call",
        "entry": entry,
        "arguments": arguments,
        "session": session if session is not None else {"dataRoot": str(data_root)},
    }
    return subprocess.run(
        [sys.executable, "ear-tool.py"],
        cwd=ROOT,
        input=json.dumps(handed),
        capture_output=True,
        text=True,
        timeout=60,
        env=env,
    )


class ToolTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.voice = self.root / "voice.ogg"
        self.voice.write_bytes(b"OggS a room's voice note")

    def tearDown(self):
        self.tmp.cleanup()

    def settings(self):
        folder = self.root / "ear"
        folder.mkdir()
        (folder / "settings.toml").write_text(
            (ROOT / "tests" / "settings-example.toml").read_text(encoding="utf-8"),
            encoding="utf-8",
        )

    def test_a_missing_file_is_an_error_answer(self):
        ran = call("ear/listen", {"path": str(self.root / "missing.ogg")}, self.root)
        self.assertEqual(ran.returncode, 0)
        answer = json.loads(ran.stdout)
        self.assertTrue(answer["isError"])
        self.assertIn("does not stand", answer["content"][0]["text"])

    def test_a_missing_settings_file_is_an_error_answer(self):
        ran = call("ear/listen", {"path": str(self.voice)}, self.root)
        self.assertEqual(ran.returncode, 0)
        answer = json.loads(ran.stdout)
        self.assertTrue(answer["isError"])
        self.assertIn("settings do not read", answer["content"][0]["text"])

    def test_a_node_that_cannot_be_reached_is_named(self):
        self.settings()
        ran = call("ear/listen", {"path": str(self.voice)}, self.root)
        self.assertEqual(ran.returncode, 0)
        answer = json.loads(ran.stdout)
        self.assertTrue(answer["isError"])
        self.assertIn("hub console could not be run", answer["content"][0]["text"])

    def test_the_hosts_data_root_is_read_when_the_call_names_none(self):
        self.settings()
        env = {"BMO_DATA_DIR": str(self.root)}
        ran = call("ear/listen", {"path": str(self.voice)}, self.root, session={}, env=env)
        self.assertEqual(ran.returncode, 0)
        answer = json.loads(ran.stdout)
        self.assertTrue(answer["isError"])
        self.assertIn("hub console could not be run", answer["content"][0]["text"])

    def test_the_default_data_root_is_used_when_none_is_named(self):
        home = self.root / "home"
        settings = home / ".local" / "share" / "bmo" / "data" / "ear"
        settings.mkdir(parents=True)
        (settings / "settings.toml").write_text(
            (ROOT / "tests" / "settings-example.toml").read_text(encoding="utf-8"),
            encoding="utf-8",
        )
        env = {"HOME": str(home)}
        ran = call("ear/listen", {"path": str(self.voice)}, self.root, session={}, env=env)
        self.assertEqual(ran.returncode, 0)
        answer = json.loads(ran.stdout)
        self.assertTrue(answer["isError"])
        self.assertIn("hub console could not be run", answer["content"][0]["text"])

    def test_no_settings_at_the_default_data_root_is_an_error_answer(self):
        home = self.root / "home"
        home.mkdir()
        env = {"HOME": str(home)}
        ran = call("ear/listen", {"path": str(self.voice)}, self.root, session={}, env=env)
        self.assertEqual(ran.returncode, 0)
        answer = json.loads(ran.stdout)
        self.assertTrue(answer["isError"])
        self.assertIn("settings do not read", answer["content"][0]["text"])

    def test_an_unknown_entry_is_an_error_answer(self):
        ran = call("bmo/other", {}, self.root)
        self.assertEqual(ran.returncode, 0)
        answer = json.loads(ran.stdout)
        self.assertTrue(answer["isError"])
        self.assertIn("no entry", answer["content"][0]["text"])

    def test_a_call_of_another_protocol_ends_unclean(self):
        ran = call("ear/listen", {}, self.root, protocol=2)
        self.assertEqual(ran.returncode, 1)
        self.assertIn("does not read", ran.stderr)


if __name__ == "__main__":
    unittest.main()
