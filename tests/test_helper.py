"""The tool host's Python helper: the call protocol version this tool answers."""

import io
import json
import unittest

import bmo_tool


class HelperTest(unittest.TestCase):
    def test_the_protocol_is_the_hosts(self):
        self.assertEqual(bmo_tool.PROTOCOL, 1)

    def test_a_failure_is_an_error_answer(self):
        answer = bmo_tool.failure("no such file")
        self.assertTrue(answer["isError"])
        self.assertEqual(answer["content"][0]["text"], "ERROR: no such file")

    def test_a_structured_answer_carries_both_forms(self):
        answer = bmo_tool.structured({"transcript": "hello"})
        self.assertFalse(answer["isError"])
        self.assertEqual(answer["structuredContent"], {"transcript": "hello"})
        self.assertEqual(json.loads(answer["content"][0]["text"]), {"transcript": "hello"})

    def test_a_handed_call_reaches_its_handler(self):
        given = io.BytesIO(
            json.dumps(
                {
                    "protocol": 1,
                    "kind": "call",
                    "entry": "bmo/transcribe",
                    "arguments": {"path": "/tmp/voice.ogg"},
                    "session": {"dataRoot": "/tmp"},
                }
            ).encode()
        )
        said = io.BytesIO()
        bmo_tool.answer(
            {"bmo/transcribe": lambda call: bmo_tool.text(call.arguments["path"])},
            given=given,
            said=said,
        )
        answer = json.loads(said.getvalue())
        self.assertEqual(answer["content"][0]["text"], "/tmp/voice.ogg")
        self.assertFalse(answer["isError"])

    def test_an_unknown_entry_is_an_error_answer(self):
        given = io.BytesIO(
            json.dumps(
                {
                    "protocol": 1,
                    "kind": "call",
                    "entry": "bmo/other",
                    "arguments": {},
                    "session": {"dataRoot": "/tmp"},
                }
            ).encode()
        )
        said = io.BytesIO()
        bmo_tool.answer({}, given=given, said=said)
        answer = json.loads(said.getvalue())
        self.assertTrue(answer["isError"])
        self.assertIn("no entry", answer["content"][0]["text"])

    def test_a_call_of_another_protocol_ends_unclean(self):
        given = io.BytesIO(
            json.dumps(
                {
                    "protocol": 2,
                    "kind": "call",
                    "entry": "bmo/transcribe",
                    "arguments": {},
                    "session": {"dataRoot": "/tmp"},
                }
            ).encode()
        )
        with self.assertRaises(SystemExit) as raised:
            bmo_tool.answer({}, given=given, said=io.BytesIO())
        self.assertEqual(raised.exception.code, 1)


if __name__ == "__main__":
    unittest.main()
