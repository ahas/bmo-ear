"""One call: the file checked, carried, run on the node, and the answer read."""

import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from ear import node
from ear.call import CallError, transcribe
from ear.settings import Engine, Hub, Place, Settings, SettingsError

SETTINGS = Settings(
    agent="example-node",
    hub=Hub(bun="/opt/example/bun", console="/opt/example/console.ts"),
    place=Place(
        root="/home/example/bmo-ear",
        turn="/home/example/bmo-card/turn.py",
        python="/home/example/bmo-ear/.venv/bin/python",
        service="ear",
        uv="/home/example/.local/bin/uv",
    ),
    engine=Engine(model="large-v3-turbo", language="ko", device="cuda", compute="float16"),
)


def completed(code=0, stdout="", stderr=""):
    return subprocess.CompletedProcess(args=[], returncode=code, stdout=stdout, stderr=stderr)


class CallTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.voice = self.root / "voice.ogg"
        self.voice.write_bytes(b"OggS a room's voice note")
        self.patches = [
            mock.patch("ear.call.read", return_value=SETTINGS),
            mock.patch("ear.node.carried_name", return_value="a" * 64 + ".ogg"),
            mock.patch("ear.node.remote_copy", return_value="/home/example/bmo-ear/in/x.ogg"),
            mock.patch("ear.node.make_room"),
            mock.patch("ear.node.upload"),
            mock.patch("ear.node.remove_copy"),
        ]
        self.mocks = [one.start() for one in self.patches]
        self.exec_on_node = mock.patch("ear.node.exec_on_node")
        self.run_mock = self.exec_on_node.start()

    def tearDown(self):
        self.exec_on_node.stop()
        for one in self.patches:
            one.stop()
        self.tmp.cleanup()

    def test_a_path_that_does_not_stand(self):
        with self.assertRaises(CallError) as raised:
            transcribe(str(self.root / "missing.ogg"), self.root)
        self.assertIn("does not stand", str(raised.exception))

    def test_a_relative_path_is_refused(self):
        with self.assertRaises(CallError) as raised:
            transcribe("voice.ogg", self.root)
        self.assertIn("not absolute", str(raised.exception))

    def test_a_directory_is_refused(self):
        with self.assertRaises(CallError) as raised:
            transcribe(str(self.root), self.root)
        self.assertIn("not a file", str(raised.exception))

    def test_settings_that_do_not_read(self):
        with mock.patch("ear.call.read", side_effect=SettingsError("no file")):
            with self.assertRaises(CallError) as raised:
                transcribe(str(self.voice), self.root)
        self.assertIn("settings do not read", str(raised.exception))

    def test_the_transcript_comes_back(self):
        self.run_mock.return_value = completed(
            stdout='{"transcript": "what was said", "language": "ko", "duration": 12.5}\n'
        )
        answer = transcribe(str(self.voice), self.root)
        self.assertEqual(
            answer,
            {"transcript": "what was said", "language": "ko", "duration": 12.5, "device": "cuda"},
        )

    def test_the_run_takes_the_card_through_the_turn_client(self):
        self.run_mock.return_value = completed(stdout='{"transcript": "x"}\n')
        transcribe(str(self.voice), self.root)
        words = self.run_mock.call_args.args[1]
        env = self.run_mock.call_args.kwargs["env"]
        self.assertEqual(env, {"BMO_CARD_SERVICE": "ear"})
        self.assertEqual(words[0], "/home/example/bmo-ear/.venv/bin/python")
        self.assertEqual(words[1], "/home/example/bmo-card/turn.py")
        self.assertEqual(words[2:4], ["--service", "ear"])
        self.assertIn("--", words)
        self.assertIn("/home/example/bmo-ear/ear-transcribe.py", words)
        self.assertIn("--language", words)
        self.assertIn("ko", words)
        self.assertIn("--model", words)
        self.assertIn("large-v3-turbo", words)

    def test_a_cpu_installation_asks_no_card(self):
        cpu = Settings(
            agent=SETTINGS.agent,
            hub=SETTINGS.hub,
            place=SETTINGS.place,
            engine=Engine(model="large-v3-turbo", language="ko", device="cpu", compute="int8"),
        )
        with mock.patch("ear.call.read", return_value=cpu):
            self.run_mock.return_value = completed(stdout='{"transcript": "x"}\n')
            answer = transcribe(str(self.voice), self.root)
        words = self.run_mock.call_args.args[1]
        self.assertIsNone(self.run_mock.call_args.kwargs["env"])
        self.assertNotIn("/home/example/bmo-card/turn.py", words)
        self.assertEqual(answer["device"], "cpu")

    def test_a_node_error_is_the_answer(self):
        self.run_mock.return_value = completed(
            stdout='{"error": "the card is not available"}\n', stderr=""
        )
        with self.assertRaises(CallError) as raised:
            transcribe(str(self.voice), self.root)
        self.assertIn("the card is not available", str(raised.exception))

    def test_no_place_on_the_card_is_named(self):
        self.run_mock.return_value = completed(code=3, stderr="turn: no place on this node\n")
        with self.assertRaises(CallError) as raised:
            transcribe(str(self.voice), self.root)
        self.assertIn("no place", str(raised.exception))
        self.assertIn("no place on this node", str(raised.exception))

    def test_a_failed_run_carries_its_last_lines(self):
        self.run_mock.return_value = completed(code=1, stderr="Traceback\nCUDA out of memory\n")
        with self.assertRaises(CallError) as raised:
            transcribe(str(self.voice), self.root)
        self.assertIn("ended with 1", str(raised.exception))
        self.assertIn("CUDA out of memory", str(raised.exception))

    def test_an_answer_that_does_not_read_is_refused(self):
        self.run_mock.return_value = completed(stdout="Segmentation fault\n")
        with self.assertRaises(CallError) as raised:
            transcribe(str(self.voice), self.root)
        self.assertIn("nothing that reads", str(raised.exception))

    def test_the_copy_is_removed_when_the_run_fails(self):
        self.run_mock.return_value = completed(code=1, stderr="boom\n")
        with self.assertRaises(CallError):
            transcribe(str(self.voice), self.root)
        node.remove_copy.assert_called_once()

    def test_an_unreachable_node_is_the_answer(self):
        node.make_room.side_effect = node.NodeError("the hub console could not be run")
        with self.assertRaises(CallError) as raised:
            transcribe(str(self.voice), self.root)
        self.assertIn("hub console", str(raised.exception))
        self.run_mock.assert_not_called()


if __name__ == "__main__":
    unittest.main()
