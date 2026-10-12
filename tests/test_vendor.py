"""The vendored vtskit: a verbatim copy of the package named in UPSTREAM,
with its licence beside it."""

import hashlib
import importlib.util
import io
import os
import re
import shutil
import tempfile
import unittest
import zipfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
VENDOR = os.path.join(ROOT, "oncemore", "_vendor", "vtskit")


class TestVendoredVtskit(unittest.TestCase):
    def test_upstream_names_a_commit_or_a_release(self):
        with open(os.path.join(VENDOR, "UPSTREAM"), encoding="utf-8") as f:
            text = f.read()
        self.assertIn("https://github.com/kajisho5/vtskit", text)
        self.assertRegex(text, r"copied from (commit [0-9a-f]{40}\b|PyPI vtskit (\S+) \(vtskit-\2-\S+\.whl, "
                               r"sha256 [0-9a-f]{64}\))")
        self.assertTrue(os.path.isfile(os.path.join(VENDOR, "COPYING.LESSER")))
        m = re.search(r"PyPI vtskit (\S+) ", text)
        if m:                                  # (the copy is that release)
            from oncemore._vendor.vtskit import __version__
            self.assertEqual(__version__, m[1])

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


def load_tool():
    spec = importlib.util.spec_from_file_location("vendor", os.path.join(ROOT, "tools", "vendor.py"))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def wheel(files):
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as z:
        for name, text in files.items():
            z.writestr(name, text)
    return buf.getvalue()


class TestFromWheel(unittest.TestCase):
    """tools/vendor.py <library> --pypi, on wheels made here (no network)."""

    def setUp(self):
        self.tool = load_tool()
        self.dir = tempfile.mkdtemp(prefix="oncemore-vendor-")
        self.addCleanup(shutil.rmtree, self.dir, True)
        with open(os.path.join(self.dir, "old.py"), "w") as f:
            f.write("# a module the new release no longer has\n")

    def test_copied_with_its_digest(self):
        data = wheel({"vtskit/__init__.py": '__version__ = "9.8.7"\nfrom .ifo import x\n',
                      "vtskit/ifo.py": "x = 1\n", "vtskit/tests/test_x.py": "",
                      "vtskit-9.8.7.dist-info/licenses/COPYING.LESSER": "LGPL\n",
                      "vtskit-9.8.7.dist-info/METADATA": "Name: vtskit\n"})
        self.tool.from_wheel("vtskit", data, "9.8.7", "vtskit-9.8.7-py3-none-any.whl", self.dir)
        self.assertEqual(sorted(os.listdir(self.dir)), ["COPYING.LESSER", "UPSTREAM", "__init__.py", "ifo.py"])
        with open(os.path.join(self.dir, "UPSTREAM")) as f:
            self.assertIn(f"copied from PyPI vtskit 9.8.7 (vtskit-9.8.7-py3-none-any.whl, "
                          f"sha256 {hashlib.sha256(data).hexdigest()})", f.read())

    def test_each_library_with_its_licence(self):
        # (an Apache library brings LICENSE and NOTICE; the LGPL bdmvkit both
        # its licence files)
        data = wheel({"udfkit/__init__.py": '__version__ = "0.1.0"\n', "udfkit/dvd.py": "",
                      "udfkit-0.1.0.dist-info/licenses/LICENSE": "Apache\n",
                      "udfkit-0.1.0.dist-info/licenses/NOTICE": "udfkit\n"})
        self.tool.from_wheel("udfkit", data, "0.1.0", "udfkit-0.1.0-py3-none-any.whl", self.dir)
        self.assertEqual(sorted(os.listdir(self.dir)), ["LICENSE", "NOTICE", "UPSTREAM", "__init__.py", "dvd.py"])
        with open(os.path.join(self.dir, "UPSTREAM")) as f:
            self.assertTrue(f.read().startswith("udfkit, https://github.com/kajisho5/udfkit (Apache-2.0, "
                                                "see LICENSE and NOTICE)\n"))
        with self.assertRaises(SystemExit):          # COPYING missing
            self.tool.from_wheel("bdmvkit", wheel({"bdmvkit/__init__.py": '__version__ = "0.2.0"\n',
                                                   "bdmvkit-0.2.0.dist-info/licenses/COPYING.LESSER": ""}),
                                 "0.2.0", "w.whl", self.dir)
        self.assertEqual(set(self.tool.LIBRARIES), {"vtskit", "udfkit", "bdmvkit", "dvdcc"})

    def test_refused(self):
        good = {"vtskit/__init__.py": '__version__ = "1.0.0"\n',
                "vtskit-1.0.0.dist-info/licenses/COPYING.LESSER": "LGPL\n"}
        with self.assertRaises(SystemExit):          # not the version asked for
            self.tool.from_wheel("vtskit", wheel(good), "1.0.1", "w.whl", self.dir)
        with self.assertRaises(SystemExit):          # no licence
            self.tool.from_wheel("vtskit", wheel({"vtskit/__init__.py": '__version__ = "1.0.0"\n'}), "1.0.0",
                                 "w.whl", self.dir)
        self.assertEqual(os.listdir(self.dir), ["old.py"])   # (nothing touched)

    def test_vtskit_wrapper(self):
        # the name vtskit's README gives still works (it prints its usage)
        import subprocess
        import sys
        p = subprocess.run([sys.executable, os.path.join(ROOT, "tools", "vendor_vtskit.py")],
                           capture_output=True, text=True)
        self.assertEqual(p.returncode, 2)
        self.assertIn("tools/vendor.py udfkit --pypi", p.stderr)
