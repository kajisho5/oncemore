"""Menu image adjustments in the app: the menu's Properties adjust its
background, a picture's Properties adjust the picture, and the stage shows
them as the disc gets them (the server makes them with the same filters)."""

import json
import os
import shutil
import subprocess
import tempfile
import unittest

from .helpers import have
from .test_gui import GuiServer

try:
    from playwright.sync_api import sync_playwright
    PLAYWRIGHT = True
except ImportError:  # pragma: no cover
    PLAYWRIGHT = False


def pixel(png, x, y):
    raw = subprocess.run(["ffmpeg", "-v", "error", "-i", "pipe:0", "-f", "rawvideo",
                          "-pix_fmt", "rgb24", "-"], input=png, check=True,
                         capture_output=True).stdout
    width = int(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "stream=width",
                                "-of", "csv=p=0", "-i", "pipe:0"], input=png, check=True,
                               capture_output=True).stdout.strip() or 0)
    return tuple(raw[3 * (y * width + x):3 * (y * width + x) + 3]), width


@unittest.skipUnless(have("ffmpeg", "ffprobe"), "needs ffmpeg")
class TestAdjustedPictures(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.mkdtemp(prefix="oncemore-adjust-gui-")
        self.addCleanup(shutil.rmtree, self.dir, True)
        self.s = GuiServer(self.dir)
        self.addCleanup(self.s.close)
        self.s.call("/api/new", "POST", {"sample": True})
        self.path = os.path.join(self.dir, "project.oncemore.json")
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i",
                        "color=c=red:s=64x48,drawbox=x=32:y=0:w=32:h=48:color=blue:t=fill",
                        "-frames:v", "1", os.path.join(self.dir, "media", "halves.png")],
                       check=True)

    def project(self):
        with open(self.path) as f:
            return json.load(f)

    def test_endpoint(self):
        status, png = self.s.call("/api/adjusted?path=media/halves.png&w=64&crop=0.5,0,0.5,1")
        self.assertEqual(status, 200)
        (r, g, b), width = pixel(png, 10, 20)
        self.assertEqual(width, 64)                       # (the right half, at 64 wide)
        self.assertLess(r, 60)
        self.assertGreater(b, 200)
        status, png = self.s.call("/api/adjusted?path=media/halves.png&w=64&s=0")
        (r, g, b), _ = pixel(png, 10, 20)
        self.assertLessEqual(max(r, g, b) - min(r, g, b), 6)                  # (grey)

    @unittest.skipUnless(PLAYWRIGHT, "needs playwright")
    def test_properties(self):
        from .test_gui import TestGuiBrowser
        d = self.project()
        d["menus"][0]["background"] = "media/halves.png"
        d["menus"][0]["images"] = [{"file": "media/halves.png", "x": 400, "y": 300, "w": 64,
                                    "h": 48}]
        with open(self.path, "w") as f:
            json.dump(d, f)

        def until(page, test, what):
            for _ in range(300):
                m = self.project()["menus"][0]
                if test(m):
                    return m
                page.wait_for_timeout(100)
            raise AssertionError(f"{what}: {self.project()['menus'][0]}")
        with sync_playwright() as p:
            browser = TestGuiBrowser.launch(self, p)
            page = browser.new_page(viewport={"width": 1400, "height": 900}, locale="en-US")
            errors = []
            page.on("pageerror", lambda e: errors.append(str(e)))
            page.goto(f"{self.s.base}/#token={self.s.app.token}")
            page.click(".nav-item[data-view=menu][data-id=main]", timeout=120000)
            # the menu's background: the left half, brighter
            box = page.locator("#bg-adjust [data-adjust]")
            box.locator("[data-adj=width]").fill("50")
            box.locator("[data-adj=width]").dispatch_event("change")
            until(page, lambda m: m.get("background_adjust") == {
                "crop": {"x": 0, "y": 0, "w": 0.5, "h": 1}}, "cropped")
            page.locator("#bg-adjust [data-adj=brightness]").evaluate(
                "(e) => { e.value = '30'; e.dispatchEvent(new Event('change')); }")
            until(page, lambda m: m["background_adjust"].get("brightness") == 0.3, "brighter")
            src = page.locator(".stage img.bg").get_attribute("src")
            self.assertIn("/api/adjusted?", src)
            self.assertIn("crop=0%2C0%2C0.5%2C1", src)
            page.locator("#bg-adjust [data-adj-reset]").click()
            until(page, lambda m: "background_adjust" not in m, "reset")
            # a picture: grey
            page.locator(".stage .el.image").click()
            page.locator("[data-adjust] [data-adj=saturation]").evaluate(
                "(e) => { e.value = '0'; e.dispatchEvent(new Event('change')); }")
            until(page, lambda m: m["images"][0].get("adjust") == {"saturation": 0}, "grey")
            page.wait_for_function(
                "document.querySelector('.stage .el.image img').src.includes('/api/adjusted?')")
            browser.close()
        self.assertEqual(errors, [])


if __name__ == "__main__":
    unittest.main()
