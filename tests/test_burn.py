import json
import os
import shutil
import sys
import tempfile
import unittest
from unittest import mock

from oncemore import burn, tools
from oncemore.errors import MissingToolsError, OncemoreError

from .helpers import json_lines, run_cli


class TestBurnCommand(unittest.TestCase):
    def setUp(self):
        tools.reset_cache()
        self.addCleanup(tools.reset_cache)

    def test_macos(self):
        with mock.patch.object(tools, "is_macos", return_value=True), \
                mock.patch.object(tools, "find", return_value="/usr/bin/hdiutil"):
            self.assertEqual(burn.command("/d/x.iso"),
                             ["/usr/bin/hdiutil", "burn", "/d/x.iso", "-forceclose"])
            self.assertEqual(burn.command("/d/x.iso", "IODVDServices")[-2:],
                             ["-device", "IODVDServices"])

    @unittest.skipIf(sys.platform.startswith("win"), "Linux / BSD rules")
    def test_elsewhere(self):
        with mock.patch.object(tools, "is_macos", return_value=False), \
                mock.patch.object(tools, "find", return_value="/usr/bin/growisofs"):
            self.assertEqual(burn.command("/d/x.iso", "/dev/sr1"),
                             ["/usr/bin/growisofs", "-dvd-compat", "-Z", "/dev/sr1=/d/x.iso"])
            with mock.patch("os.path.exists", side_effect=lambda p: p == "/dev/sr0"):
                self.assertEqual(burn.command("/d/x.iso")[-1], "/dev/sr0=/d/x.iso")
            with mock.patch("os.path.exists", return_value=False), \
                    self.assertRaises(OncemoreError) as cm:
                burn.command("/d/x.iso")
            self.assertIn("no DVD writer found", cm.exception.message)
        with mock.patch.object(tools, "is_macos", return_value=False), \
                mock.patch.object(tools, "find", return_value=None), \
                self.assertRaises(MissingToolsError):
            burn.command("/d/x.iso", "/dev/sr0")


@unittest.skipIf(sys.platform.startswith("win"), "needs a shell script as the fake burner")
class TestBurnCli(unittest.TestCase):
    """`oncemore burn` runs the platform's burner (a fake one here, which
    records its arguments) on the image."""

    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="oncemore-burn-")
        self.addCleanup(shutil.rmtree, self.tmp, True)
        self.bin = os.path.join(self.tmp, "bin")
        os.makedirs(self.bin)
        self.args = os.path.join(self.tmp, "args.json")
        for name in ("hdiutil", "growisofs"):
            path = os.path.join(self.bin, name)
            with open(path, "w") as f:
                f.write(f"#!{sys.executable}\nimport json, sys\n"
                        f"json.dump(sys.argv[1:], open({self.args!r}, 'w'))\n")
            os.chmod(path, 0o755)
        self.iso = os.path.join(self.tmp, "MY_DISC.iso")
        with open(self.iso, "wb") as f:
            f.write(b"\0" * 2048)

    def test_burn(self):
        env = {"PATH": self.bin + os.pathsep + os.environ.get("PATH", "")}
        rc, out, err = run_cli("--json", "burn", self.iso, "--device", "/dev/sr9", env=env)
        self.assertEqual(rc, 0, err + out)
        with open(self.args) as f:
            args = json.load(f)
        if sys.platform == "darwin":
            self.assertEqual(args, ["burn", self.iso, "-forceclose", "-device", "/dev/sr9"])
        else:
            self.assertEqual(args, ["-dvd-compat", "-Z", f"/dev/sr9={self.iso}"])
        events = json_lines(out)
        self.assertEqual(events[0]["step"], "burn")
        self.assertEqual(events[-1]["burned"], self.iso)
        rc, out, err = run_cli("burn", os.path.join(self.tmp, "none.iso"), env=env)
        self.assertNotEqual(rc, 0)
        self.assertIn("no disc image", err)


if __name__ == "__main__":
    unittest.main()
