"""The vendored vtskit: a verbatim copy of the package named in UPSTREAM,
with its licence beside it."""

import os
import re
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
VENDOR = os.path.join(ROOT, "oncemore", "_vendor", "vtskit")


class TestVendoredVtskit(unittest.TestCase):
    def test_upstream_names_a_commit(self):
        with open(os.path.join(VENDOR, "UPSTREAM"), encoding="utf-8") as f:
            text = f.read()
        self.assertIn("https://github.com/kajisho5/vtskit", text)
        self.assertRegex(text, r"copied from commit [0-9a-f]{40}\b")
        self.assertTrue(os.path.isfile(os.path.join(VENDOR, "COPYING.LESSER")))

    def test_package_only(self):
        names = sorted(n for n in os.listdir(VENDOR) if n != "__pycache__")
        self.assertNotIn("tests", names)
        self.assertTrue(all(n.endswith(".py") or n in ("UPSTREAM", "COPYING.LESSER") for n in names), names)
        for name in names:
            if name.endswith(".py"):
                with open(os.path.join(VENDOR, name), encoding="utf-8") as f:
                    self.assertNotRegex(f.read(), r"^\s*(from|import) (oncemore|vtskit)\b", f"{name}: imports are relative")

    def test_version_module(self):
        from oncemore._vendor.vtskit import __version__
        self.assertRegex(__version__, r"^\d+\.\d+\.\d+$")
