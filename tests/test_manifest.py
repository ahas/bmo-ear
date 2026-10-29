"""The manifest, the schemas and the card declaration, held to their shape."""

import json
import tomllib
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


class ManifestTest(unittest.TestCase):
    def setUp(self):
        self.manifest = tomllib.loads((ROOT / "tool.toml").read_text(encoding="utf-8"))

    def test_the_tool_is_named_by_its_folder(self):
        self.assertEqual(self.manifest["tool"]["name"], ROOT.name)

    def test_the_tool_reads_by_the_hosts_protocol(self):
        tool = self.manifest["tool"]
        self.assertEqual(tool["protocol"], 1)
        self.assertTrue(tool["check"])
        self.assertTrue(tool["build"])
        self.assertTrue(tool["run"])
        self.assertGreater(tool["timeout"], 0)

    def test_the_entry_and_its_schemas(self):
        entries = self.manifest["entry"]
        self.assertEqual(len(entries), 1)
        entry = entries[0]
        self.assertEqual(f"{entry['namespace']}/{entry['name']}", "ear/listen")
        self.assertIn("room.tools", entry["capabilities"])
        self.assertTrue(entry["description"])

        given = json.loads((ROOT / entry["input"]).read_text(encoding="utf-8"))
        self.assertEqual(given["type"], "object")
        self.assertIn("path", given["required"])
        self.assertEqual(given["additionalProperties"], False)

        answered = json.loads((ROOT / entry["output"]).read_text(encoding="utf-8"))
        self.assertEqual(answered["type"], "object")
        self.assertIn("transcript", answered["required"])
        self.assertEqual(answered["additionalProperties"], False)

    def test_the_executable_stands(self):
        self.assertTrue((ROOT / "ear-tool.py").is_file())
        self.assertTrue((ROOT / "bmo_tool.py").is_file())
        self.assertIn("bmo_tool.py", self.manifest["tool"]["build"])

    def test_the_testbed_runs_the_same_suite(self):
        declaration = tomllib.loads((ROOT / "testbed.toml").read_text(encoding="utf-8"))
        self.assertEqual(declaration["name"], ROOT.name)
        self.assertEqual(declaration["test"]["languages"], [])
        self.assertEqual(declaration["check"]["quick"], ["korean"])
        self.assertEqual(declaration["check"]["korean_ledger"], "korean-ledger.json")
        steps = declaration["check"]["step"]
        self.assertEqual(len(steps), 1)
        self.assertEqual(steps[0]["command"], self.manifest["tool"]["check"])

    def test_the_card_declaration(self):
        card = tomllib.loads((ROOT / "ear.card.toml").read_text(encoding="utf-8"))
        self.assertEqual(card["service"], "ear")
        self.assertEqual(card["spread"], "one")
        self.assertFalse(card["alone"])
        self.assertGreater(card["card_mib"], 0)
        self.assertTrue(card["adapter"])
        self.assertLess(card["priority"], 70)

    def test_only_one_declaration_of_the_service(self):
        self.assertNotIn("card", self.manifest)


if __name__ == "__main__":
    unittest.main()
