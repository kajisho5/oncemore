"""The vendored libraries: verbatim copies of the packages their UPSTREAM
names, with their licences beside them (DECISIONS §105)."""

import hashlib
import importlib
import importlib.util
import io
import os
import re
import shutil
import tempfile
import unittest
import zipfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
VENDOR_ROOT = os.path.join(ROOT, "oncemore", "_vendor")
VENDOR = os.path.join(VENDOR_ROOT, "vtskit")


def vendored():
    """The libraries oncemore carries a copy of."""
    return sorted(n for n in os.listdir(VENDOR_ROOT) if os.path.isdir(os.path.join(VENDOR_ROOT, n))
                  and not n.startswith("__"))


class TestVendored(unittest.TestCase):
    def test_upstream_names_a_commit_or_a_release(self):
        tool = load_tool()
        for name in vendored():
            vendor = os.path.join(VENDOR_ROOT, name)
            with open(os.path.join(vendor, "UPSTREAM"), encoding="utf-8") as f:
                text = f.read()
            self.assertIn(f"https://github.com/kajisho5/{name}", text)
            self.assertRegex(text, rf"copied from (commit [0-9a-f]{{40}}\b|PyPI {name} (\S+) \({name}-\2-\S+\.whl, "
                                   r"sha256 [0-9a-f]{64}\))")
            for licence in tool.LIBRARIES[name][1]:
                self.assertTrue(os.path.isfile(os.path.join(vendor, licence)), (name, licence))
            m = re.search(rf"PyPI {name} (\S+) ", text)
            if m:                                  # (the copy is that release)
                version = importlib.import_module(f"oncemore._vendor.{name}").__version__
                self.assertEqual(version, m[1], name)

    def test_package_only(self):
        tool = load_tool()
        self.assertIn("vtskit", vendored())
        for lib in vendored():
            vendor = os.path.join(VENDOR_ROOT, lib)
            names = sorted(n for n in os.listdir(vendor) if n != "__pycache__")
            self.assertNotIn("tests", names)
            extra = {"UPSTREAM", *tool.LIBRARIES[lib][1]}
            self.assertTrue(all(n.endswith(".py") or n in extra for n in names), names)
            for name in names:
                if name.endswith(".py"):
                    with open(os.path.join(vendor, name), encoding="utf-8") as f:
                        self.assertNotRegex(f.read(), rf"^\s*(from|import) (oncemore|{lib})\b",
                                            f"{lib}/{name}: imports are relative")

    def test_packaged(self):
        # every copy goes into the package, with its UPSTREAM and licence
        with open(os.path.join(ROOT, "pyproject.toml"), encoding="utf-8") as f:
            toml = f.read()
        for lib in vendored():
            self.assertIn(f'"oncemore._vendor.{lib}"', toml)

    def test_version_module(self):
        for lib in vendored():
            version = importlib.import_module(f"oncemore._vendor.{lib}").__version__
            self.assertRegex(version, r"^\d+\.\d+\.\d+$", lib)


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


class TestUpdates(unittest.TestCase):
    """tools/vendor.py --outdated and the workflow that acts on it."""

    def setUp(self):
        self.tool = load_tool()
        self.root = tempfile.mkdtemp(prefix="oncemore-vendor-")
        self.addCleanup(shutil.rmtree, self.root, True)
        for name, version in (("vtskit", "0.1.0"), ("udfkit", "0.2.0"), ("dvdcc", "0.10.0")):
            os.makedirs(os.path.join(self.root, name))
            with open(os.path.join(self.root, name, "__init__.py"), "w") as f:
                f.write(f'"""{name}."""\n\n__version__ = "{version}"\n')

    def test_newer_releases(self):
        pypi = {"vtskit": "0.1.1", "udfkit": "0.2.0", "dvdcc": "0.9.0", "bdmvkit": "9.9.9"}
        # (bdmvkit is not carried here: nothing to update; 0.10 is newer than 0.9)
        self.assertEqual(self.tool.outdated(pypi.get, self.root), [("vtskit", "0.1.0", "0.1.1")])
        pypi["dvdcc"] = "0.10.1"
        self.assertEqual([r[0] for r in self.tool.outdated(pypi.get, self.root)],
                         ["vtskit", "dvdcc"])

    def test_carried_versions(self):
        for lib in vendored():
            self.assertRegex(self.tool.carried_version(lib), r"^\d+\.\d+\.\d+$")

    def test_workflow(self):
        with open(os.path.join(ROOT, ".github", "workflows", "library-updates.yml"),
                  encoding="utf-8") as f:
            text = f.read()
        self.assertIn("schedule:", text)
        self.assertIn("python tools/vendor.py --outdated", text)
        self.assertIn('python tools/vendor.py "$name" --pypi "$latest"', text)
        self.assertIn("gh pr create --draft", text)
        # (a pull request opened with GITHUB_TOKEN does not start CI: the workflow does)
        self.assertIn('gh workflow run ci.yml --ref "$branch"', text)
        with open(os.path.join(ROOT, ".github", "workflows", "ci.yml"), encoding="utf-8") as f:
            self.assertIn("workflow_dispatch:", f.read())
