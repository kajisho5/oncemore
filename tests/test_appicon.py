"""The Mac app's icons: the layered icon of macOS 26 and later
(macos/AppIcon.icon, after Apple's Human Interface Guidelines: square and
unmasked, a solid background and the mark as its foreground layer) and the
legacy one (AppIcon.png -> AppIcon.icns) beside it."""

import json
import os
import plistlib
import re
import shutil
import subprocess
import sys
import tempfile
import unittest

ROOT = os.path.join(os.path.dirname(__file__), "..")
ICON = os.path.join(ROOT, "macos", "AppIcon.icon")


def read(*path):
    with open(os.path.join(ROOT, *path), encoding="utf-8") as f:
        return f.read()


class TestLayeredIcon(unittest.TestCase):
    def test_made_by_the_logo_script(self):
        # make_logo.py --icon writes the same files (the icon is drawn, not hand-made)
        tmp = tempfile.mkdtemp(prefix="oncemore-icon-")
        self.addCleanup(shutil.rmtree, tmp, True)
        logo = os.path.join(tmp, "docs", "images", "logo")
        os.makedirs(logo)
        shutil.copy(os.path.join(ROOT, "docs", "images", "logo", "make_logo.py"), logo)
        subprocess.run([sys.executable, os.path.join(logo, "make_logo.py"), "--icon"], check=True)
        for name in ("icon.json", os.path.join("Assets", "mark.svg")):
            with open(os.path.join(tmp, "macos", "AppIcon.icon", name), encoding="utf-8") as f:
                self.assertEqual(f.read(), read("macos", "AppIcon.icon", name), name)

    def test_square_unmasked_layers(self):
        doc = json.loads(read("macos", "AppIcon.icon", "icon.json"))
        # the background: one solid fill (the system masks the square)
        self.assertEqual(list(doc["fill"]), ["solid"])
        self.assertTrue(doc["fill"]["solid"].startswith("display-p3:"))
        layers = [layer for g in doc["groups"] for layer in g["layers"]]
        self.assertEqual([layer["image-name"] for layer in layers], ["mark.svg"])
        svg = read("macos", "AppIcon.icon", "Assets", "mark.svg")
        self.assertIn('viewBox="0 0 1024 1024"', svg)
        self.assertNotIn("<rect", svg)                   # no tile of its own, no rounded corners
        self.assertNotIn("<text", svg)
        tokens = read("oncemore", "gui", "static", "tokens.css")
        self.assertEqual(set(re.findall(r"#[0-9a-f]{6}", svg)), {"#ffd400"})
        self.assertIn("--brand-highlight: #ffd400", tokens)

    def test_background_is_the_brand_ink(self):
        sys.path.insert(0, os.path.join(ROOT, "docs", "images", "logo"))
        self.addCleanup(sys.path.remove, sys.path[0])
        import make_logo
        doc = json.loads(read("macos", "AppIcon.icon", "icon.json"))
        self.assertEqual(doc["fill"]["solid"], make_logo.p3(make_logo.INK))
        self.assertEqual(make_logo.p3("#ffffff"), "display-p3:1.00000,1.00000,1.00000,1.00000")

    def test_in_the_app(self):
        plist = plistlib.loads(read("macos", "Info.plist").replace("@VERSION@", "0").replace(
            "@BUILD@", "0").encode())
        # macOS 26 and later take the asset catalog's icon, earlier ones the .icns
        self.assertEqual((plist["CFBundleIconName"], plist["CFBundleIconFile"]), ("AppIcon", "AppIcon"))
        script = read("macos", "build_app.sh")
        self.assertIn('actool "$ROOT/macos/AppIcon.icon"', script)
        self.assertIn("--app-icon AppIcon", script)
        self.assertIn("Assets.car", script)


if __name__ == "__main__":
    unittest.main()
