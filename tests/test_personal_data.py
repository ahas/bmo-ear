"""No tracked file holds personal data (docs/PERSONAL-DATA.md).

The check keeps the shapes personal data takes, never a list of names or values. A finding names the
path, the line and the shape; it never repeats the value.
"""

import re
import subprocess
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

NEUTRAL_HOME = {"user", "tester", "qa-admin", "placeholder", "example"}
ALLOWED_MAIL = {"dev@ahas.io"}

MAIL = re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z][A-Za-z0-9.-]*\.[A-Za-z]{2,}\b")
HOME = re.compile(r"(?:/home/|/Users/|[A-Za-z]:\\Users\\)([A-Za-z0-9._-]+)")
TELEPHONE = re.compile(
    r"\b01[016789][-. ]?\d{3,4}[-. ]?\d{4}\b"
    r"|\+\d{1,3}[-. ]?\d{2,4}[-. ]?\d{3,4}[-. ]?\d{4}\b"
    r"|\+\d{9,15}\b"
)
TOKEN = re.compile(
    r"gh[pousr]_[A-Za-z0-9]{20,}"
    r"|github_pat_[A-Za-z0-9_]{20,}"
    r"|sk-[A-Za-z0-9_-]{20,}"
    r"|xox[baprs]-[A-Za-z0-9-]{10,}"
    r"|AKIA[0-9A-Z]{16}"
    r"|AIza[0-9A-Za-z_-]{35}"
)
PRIVATE = re.compile(
    r"(?i)\b(?:10\.\d{1,3}\.\d{1,3}\.\d{1,3}"
    r"|192\.168\.\d{1,3}\.\d{1,3}"
    r"|172\.(?:1[6-9]|2\d|3[01])\.\d{1,3}\.\d{1,3})\b"
    r"|\b(?:f[cd][0-9a-f]{2}|fe80):"
)


def tracked_files() -> list[Path]:
    listed = subprocess.run(
        ["git", "ls-files", "--cached", "--others", "--exclude-standard", "-z"],
        cwd=ROOT,
        stdin=subprocess.DEVNULL,
        capture_output=True,
        check=True,
    )
    names = [name for name in listed.stdout.decode().split("\0") if name]
    return [ROOT / name for name in names if (ROOT / name).is_file()]


def is_example_domain(domain: str) -> bool:
    domain = domain.lower()
    return domain in {"example.com", "example.net", "example.org"} or domain.endswith(
        (".example.com", ".example.net", ".example.org", ".example", ".test", ".invalid", ".localhost")
    )


def allowed_mail(address: str) -> bool:
    return address.lower() in ALLOWED_MAIL or (
        "@" in address and is_example_domain(address.rsplit("@", 1)[1])
    )


class PersonalDataTest(unittest.TestCase):
    def test_no_tracked_file_holds_personal_data(self):
        found = []
        for path in tracked_files():
            try:
                text = path.read_text(encoding="utf-8")
            except (UnicodeDecodeError, OSError):
                continue
            name = path.relative_to(ROOT)
            for number, line in enumerate(text.splitlines(), start=1):
                if any(not allowed_mail(one) for one in MAIL.findall(line)):
                    found.append(f"{name}:{number}: mail address")
                if any(folder not in NEUTRAL_HOME for folder in HOME.findall(line)):
                    found.append(f"{name}:{number}: home path")
                if TELEPHONE.search(line):
                    found.append(f"{name}:{number}: telephone number")
                if TOKEN.search(line):
                    found.append(f"{name}:{number}: token")
                if PRIVATE.search(line):
                    found.append(f"{name}:{number}: private address")
        self.assertEqual(found, [], "\n".join(found))


if __name__ == "__main__":
    unittest.main()
