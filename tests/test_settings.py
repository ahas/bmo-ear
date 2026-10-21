"""The installation's settings file (docs/setup.md)."""

import tempfile
import unittest
from pathlib import Path

from ear.settings import SettingsError, read, settings_path

GOOD = """
[node]
agent = "example-node"

[hub]
bun = "/opt/example/bun"
console = "/opt/example/console.ts"

[place]
root = "/home/example/bmo-ear"
turn = "/home/example/bmo-card/turn.py"
python = "/home/example/bmo-ear/.venv/bin/python"
service = "ear"
uv = "/home/example/.local/bin/uv"

[engine]
model = "large-v3-turbo"
language = "ko"
device = "cuda"
compute = "float16"
"""


class SettingsTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def write(self, text):
        path = settings_path(self.root)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
        return path

    def test_reads_every_table(self):
        self.write(GOOD)
        settings = read(self.root)
        self.assertEqual(settings.agent, "example-node")
        self.assertEqual(settings.hub.console, "/opt/example/console.ts")
        self.assertEqual(settings.place.service, "ear")
        self.assertEqual(settings.engine.model, "large-v3-turbo")
        self.assertEqual(settings.engine.language, "ko")

    def test_missing_file_names_its_path(self):
        with self.assertRaises(SettingsError) as raised:
            read(self.root)
        self.assertIn("does not stand", str(raised.exception))

    def test_missing_key_names_the_table_and_key(self):
        self.write(GOOD.replace('service = "ear"\n', ""))
        with self.assertRaises(SettingsError) as raised:
            read(self.root)
        self.assertIn("[place]", str(raised.exception))
        self.assertIn("service", str(raised.exception))

    def test_missing_table_is_refused(self):
        self.write(GOOD.replace("[engine]\n", "[other]\n"))
        with self.assertRaises(SettingsError) as raised:
            read(self.root)
        self.assertIn("[engine]", str(raised.exception))

    def test_device_is_cuda_or_cpu(self):
        self.write(GOOD.replace('device = "cuda"', 'device = "tpu"'))
        with self.assertRaises(SettingsError) as raised:
            read(self.root)
        self.assertIn("cuda or cpu", str(raised.exception))

    def test_root_is_absolute_on_the_node(self):
        self.write(GOOD.replace('root = "/home/example/bmo-ear"', 'root = "bmo-ear"'))
        with self.assertRaises(SettingsError) as raised:
            read(self.root)
        self.assertIn("absolute", str(raised.exception))

    def test_broken_toml_is_refused(self):
        self.write("[node\nagent = 1")
        with self.assertRaises(SettingsError) as raised:
            read(self.root)
        self.assertIn("does not read", str(raised.exception))


if __name__ == "__main__":
    unittest.main()
