"""The road to the node: carried names, remote paths and the console's argv."""

import tempfile
import unittest
from pathlib import Path
from unittest import mock

from ear import node
from ear.settings import Engine, Hub, Place, Settings

SETTINGS = Settings(
    agent="example-node",
    hub=Hub(bun="/opt/example/bun", console="/opt/example/console.ts"),
    place=Place(
        root="/home/example/bmo-ear/",
        turn="/home/example/bmo-card/turn.py",
        python="/home/example/bmo-ear/.venv/bin/python",
        service="ear",
        uv="/home/example/.local/bin/uv",
    ),
    engine=Engine(model="large-v3-turbo", language="ko", device="cuda", compute="float16"),
)


class CarriedNameTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def test_name_is_the_content_and_a_safe_extension(self):
        one = self.root / "note.OGG"
        one.write_bytes(b"first voice")
        two = self.root / "again.ogg"
        two.write_bytes(b"first voice")
        other = self.root / "other.wav"
        other.write_bytes(b"other voice")
        self.assertEqual(node.carried_name(one), node.carried_name(two))
        self.assertNotEqual(node.carried_name(one), node.carried_name(other))
        self.assertTrue(node.carried_name(one).endswith(".ogg"))
        self.assertTrue(node.carried_name(other).endswith(".wav"))

    def test_an_unsafe_extension_falls_back(self):
        odd = self.root / "note.weird name"
        odd.write_bytes(b"voice")
        self.assertTrue(node.carried_name(odd).endswith(".ogg"))

    def test_remote_copy_joins_the_root(self):
        name = "a" * 64 + ".ogg"
        self.assertEqual(node.remote_copy(SETTINGS, name), "/home/example/bmo-ear/in/" + name)

    def test_a_name_this_tool_did_not_make_is_refused(self):
        with self.assertRaises(node.NodeError):
            node.remote_copy(SETTINGS, "../../etc/passwd")
        with self.assertRaises(node.NodeError):
            node.remote_copy(SETTINGS, "short.ogg")


class ConsoleTest(unittest.TestCase):
    def test_exec_names_the_agent_and_the_command(self):
        with mock.patch.object(node, "_run") as ran:
            node.exec_on_node(SETTINGS, ["mkdir", "-p", "/tmp/x"], env={"BMO_CARD_SERVICE": "ear"})
        argv = ran.call_args.args[0]
        self.assertEqual(
            argv,
            [
                "/opt/example/bun",
                "/opt/example/console.ts",
                "exec",
                "-a",
                "example-node",
                "--env",
                "BMO_CARD_SERVICE=ear",
                "--",
                "mkdir",
                "-p",
                "/tmp/x",
            ],
        )

    def test_exec_refuses_an_empty_command(self):
        with self.assertRaises(node.NodeError):
            node.exec_on_node(SETTINGS, [])

    def test_upload_names_the_agent(self):
        with mock.patch.object(node, "_run") as ran:
            ran.return_value.returncode = 0
            node.upload(SETTINGS, Path("/tmp/voice.ogg"), "/home/example/bmo-ear/in/x.ogg")
        argv = ran.call_args.args[0]
        self.assertEqual(argv[:2], ["/opt/example/bun", "/opt/example/console.ts"])
        self.assertEqual(argv[2], "upload")
        self.assertEqual(argv[-2:], ["-a", "example-node"])

    def test_a_missing_console_is_named(self):
        with mock.patch.object(node.subprocess, "run", side_effect=FileNotFoundError("nope")):
            with self.assertRaises(node.NodeError) as raised:
                node.exec_on_node(SETTINGS, ["true"])
        self.assertIn("hub console could not be run", str(raised.exception))

    def test_a_failed_upload_carries_the_reason(self):
        with mock.patch.object(node, "_run") as ran:
            ran.return_value.returncode = 1
            ran.return_value.stderr = "refused: no such agent\n"
            ran.return_value.stdout = ""
            with self.assertRaises(node.NodeError) as raised:
                node.upload(SETTINGS, Path("/tmp/voice.ogg"), "/home/example/bmo-ear/in/x.ogg")
        self.assertIn("no such agent", str(raised.exception))

    def test_tail_keeps_the_last_lines(self):
        said = "\n".join(f"line {n}" for n in range(20))
        kept = node.tail(said, 3)
        self.assertEqual(kept.splitlines(), ["line 17", "line 18", "line 19"])


if __name__ == "__main__":
    unittest.main()
