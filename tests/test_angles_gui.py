"""A title's angles in the app's editor: Properties > Angles adds, picks,
orders and removes the videos that are angles 2 and on (the source is
angle 1); a title of joined clips has none."""

import json
import os
import shutil
import tempfile
import unittest

from .test_gui import GuiServer

try:
    from playwright.sync_api import sync_playwright
    PLAYWRIGHT = True
except ImportError:  # pragma: no cover
    PLAYWRIGHT = False


@unittest.skipUnless(PLAYWRIGHT, "needs playwright")
class TestAnglesEditor(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.mkdtemp(prefix="oncemore-angles-gui-")
        self.addCleanup(shutil.rmtree, self.dir, True)
        self.s = GuiServer(self.dir)
        self.addCleanup(self.s.close)
        self.s.call("/api/new", "POST", {"sample": True})
        # a third video, so two angles can differ
        shutil.copy(os.path.join(self.dir, "media", "sample_b.mp4"),
                    os.path.join(self.dir, "media", "sample_c.mp4"))

    def title(self, i=0):
        with open(os.path.join(self.dir, "project.oncemore.json")) as f:
            return json.load(f)["titles"][i]

    def test_angles(self):
        with sync_playwright() as p:
            from .test_gui import TestGuiBrowser
            browser = TestGuiBrowser.launch(self, p)
            page = browser.new_page(viewport={"width": 1400, "height": 900}, locale="en-US")
            errors = []
            page.on("pageerror", lambda e: errors.append(str(e)))
            page.goto(f"{self.s.base}/#token={self.s.app.token}")
            page.click(".nav-item[data-view=title][data-id=t1]", timeout=120000)
            page.locator("#add-angle").wait_for()

            def until(test, what):
                for _ in range(300):
                    t = self.title()
                    if test(t):
                        return t
                    page.wait_for_timeout(100)
                raise AssertionError(f"{what}: {self.title().get('angles')}")
            # the first free video becomes angle 2
            page.click("#add-angle")
            until(lambda t: t.get("angles") == ["media/sample_b.mp4"], "one angle")
            page.click("#add-angle")
            until(lambda t: t.get("angles") == ["media/sample_b.mp4", "media/sample_c.mp4"],
                  "two angles")
            # the source is not offered as an angle
            opts = page.locator("[data-angle='0'] select option").all_inner_texts()
            self.assertNotIn("sample_a.mp4", opts)
            # pick other videos, move one up, remove them
            page.select_option("[data-angle='0'] select", "media/sample_c.mp4")
            until(lambda t: t["angles"][0] == "media/sample_c.mp4", "picked")
            page.select_option("[data-angle='1'] select", "media/sample_b.mp4")
            until(lambda t: t["angles"] == ["media/sample_c.mp4", "media/sample_b.mp4"], "picked")
            page.click("[data-angle-up='1']")
            until(lambda t: t["angles"] == ["media/sample_b.mp4", "media/sample_c.mp4"], "moved")
            page.click("[data-del-angle='1']")
            until(lambda t: t.get("angles") == ["media/sample_b.mp4"], "removed")
            page.click("[data-del-angle='0']")
            until(lambda t: "angles" not in t, "none left")
            browser.close()
        self.assertEqual(errors, [])

    def test_clips_have_none(self):
        with open(os.path.join(self.dir, "project.oncemore.json")) as f:
            data = json.load(f)
        t = data["titles"][0]
        t["clips"] = [{"source": t.pop("source")}, {"source": "media/sample_b.mp4"}]
        self.s.call("/api/project", "PUT", {"project": data})
        with sync_playwright() as p:
            from .test_gui import TestGuiBrowser
            browser = TestGuiBrowser.launch(self, p)
            page = browser.new_page(viewport={"width": 1400, "height": 900}, locale="en-US")
            page.goto(f"{self.s.base}/#token={self.s.app.token}")
            page.click(".nav-item[data-view=title][data-id=t1]", timeout=120000)
            page.locator("#inspector h3", has_text="Angles").wait_for()
            self.assertEqual(page.locator("#add-angle").count(), 0)
            self.assertIn("single video file", page.inner_text("#inspector"))
            browser.close()


if __name__ == "__main__":
    unittest.main()
