"""Chapter points at scene changes: the cuts ffmpeg's scene score finds,
at least a gap apart, from the command line, the editor's server and
Timeline > Add chapter points at scene changes."""

import json
import os
import shutil
import subprocess
import tempfile
import unittest

from oncemore import scenes, tools

from .helpers import have, json_lines, run_cli
from .test_gui import GuiServer

try:
    from playwright.sync_api import sync_playwright
    PLAYWRIGHT = True
except ImportError:  # pragma: no cover
    PLAYWRIGHT = False


def cuts_video(path):
    """Red for 3 s, a test pattern for 4.5 s, blue for 2.5 s: cuts at 3 and 7.5."""
    subprocess.run([tools.find("ffmpeg"), "-hide_banner", "-v", "error", "-y",
                    "-f", "lavfi", "-i", "color=c=red:s=640x360:d=3,format=yuv420p",
                    "-f", "lavfi", "-i", "testsrc2=s=640x360:d=4.5",
                    "-f", "lavfi", "-i", "color=c=blue:s=640x360:d=2.5",
                    "-filter_complex", "[0][1][2]concat=n=3:v=1:a=0,fps=30000/1001",
                    "-c:v", "libx264", "-preset", "ultrafast", path], check=True)
    return path


@unittest.skipUnless(have("ffmpeg"), "needs ffmpeg")
class TestDetect(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.mkdtemp(prefix="oncemore-scenes-")
        cls.video = cuts_video(os.path.join(cls.tmp, "cuts.mp4"))

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.tmp, ignore_errors=True)

    def test_cuts(self):
        t = scenes.detect(self.video, min_gap=1)
        self.assertEqual(len(t), 2, t)
        self.assertAlmostEqual(t[0], 3.0, delta=0.05)
        self.assertAlmostEqual(t[1], 7.5, delta=0.05)

    def test_gap(self):
        # the second cut is 4.5 s after the first; 5 s apart drops it, and a
        # cut 3 s from the start is dropped with a gap of 4
        self.assertEqual(len(scenes.detect(self.video, min_gap=5)), 1)
        t = scenes.detect(self.video, min_gap=4)
        self.assertEqual(len(t), 1)
        self.assertAlmostEqual(t[0], 7.5, delta=0.05)

    def test_part_of_the_file(self):
        # from 2 s to 6 s: the first cut only, on the file's time line
        t = scenes.detect(self.video, min_gap=0.5, start=2.0, end=6.0)
        self.assertEqual(len(t), 1, t)
        self.assertAlmostEqual(t[0], 3.0, delta=0.05)
        with self.assertRaises(ValueError):
            scenes.detect(self.video, threshold=1.5)

    def test_cli(self):
        rc, out, err = run_cli("--json", "scenes", self.video, "--min-gap", "1")
        self.assertEqual(rc, 0, err)
        self.assertEqual(len(json_lines(out)[-1]["times"]), 2)
        rc, out, err = run_cli("scenes", self.video, "--sensitivity", "low", "--min-gap", "1")
        self.assertIn("2 scene change(s)", out)
        rc, out, err = run_cli("scenes", os.path.join(self.tmp, "none.mp4"))
        self.assertNotEqual(rc, 0)
        self.assertIn("not found", err + out)


@unittest.skipUnless(have("ffmpeg", "ffprobe"), "needs ffmpeg")
class TestEditor(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.mkdtemp(prefix="oncemore-scenes-gui-")
        self.addCleanup(shutil.rmtree, self.dir, True)
        self.s = GuiServer(self.dir)
        self.addCleanup(self.s.close)
        self.s.call("/api/new", "POST", {"sample": True})
        cuts_video(os.path.join(self.dir, "media", "cuts.mp4"))

    def project(self):
        with open(os.path.join(self.dir, "project.oncemore.json")) as f:
            return json.load(f)

    def test_api(self):
        code, r = self.s.call("/api/scenes", "POST", {"path": "media/cuts.mp4", "min_gap": 1})
        self.assertEqual(code, 200)
        self.assertEqual(len(r["times"]), 2)
        self.assertEqual(self.s.call("/api/scenes", "POST", {"path": "../x.mp4"})[0], 403)
        self.assertEqual(self.s.call("/api/scenes", "POST", {"path": "media/cuts.mp4",
                                                             "sensitivity": "max"})[0], 400)

    @staticmethod
    def until(page, expr, seconds=120):
        """Wait for a condition on the page (evaluated, not eval'd: the page's
        content security policy has no unsafe-eval)."""
        for _ in range(seconds * 10):
            if page.evaluate(f"() => !!({expr})"):
                return
            page.wait_for_timeout(100)
        raise AssertionError(f"timed out: {expr}")

    @unittest.skipUnless(PLAYWRIGHT, "needs playwright")
    def test_dialog(self):
        data = self.project()
        data["titles"][1] = {"id": "t2", "name": "Cuts", "source": "media/cuts.mp4"}
        self.s.call("/api/project", "PUT", {"project": data})
        with sync_playwright() as p:
            from .test_gui import TestGuiBrowser
            browser = TestGuiBrowser.launch(self, p)
            page = browser.new_page(viewport={"width": 1400, "height": 900}, locale="en-US")
            errors = []
            page.on("pageerror", lambda e: errors.append(str(e)))
            page.goto(f"{self.s.base}/#token={self.s.app.token}")
            page.click(".nav-item[data-view=title][data-id=t2]", timeout=120000)
            self.until(page, "titleLength(curTitle()) > 9")
            page.evaluate("window.oncemoreCommand('chapters_scenes')")
            page.fill("#sc-gap", "2")
            page.dispatch_event("#sc-gap", "change")
            page.click("#sc-find")
            self.until(page, "!document.querySelector('#sc-ok').disabled")
            self.assertIn("2 scene changes found: 3 chapters", page.inner_text("#sc-preview"))
            page.click("#sc-ok")
            def chapters():
                return self.project()["titles"][1].get("chapters", [])
            for _ in range(100):
                if len(chapters()) == 3:
                    break
                page.wait_for_timeout(100)
            ch = chapters()
            times = [c["time"] if isinstance(c, dict) else c for c in ch]
            self.assertEqual(len(times), 3, ch)
            self.assertTrue(times[1].startswith("00:00:03"), times)
            self.assertTrue(times[2].startswith("00:00:07.5"), times)
            browser.close()
        self.assertEqual(errors, [])


if __name__ == "__main__":
    unittest.main()
