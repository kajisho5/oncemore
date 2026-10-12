"""A button thumbnail cut to a shape (`mask`: rounded, ellipse) or to a
picture's opaque pixels (`mask_image`), on the disc and in the app."""

import json
import os
import shutil
import subprocess
import tempfile
import unittest

from oncemore.errors import ProjectError
from oncemore.menu import MenuBuilder, mask_filter
from oncemore.project import build_project
from oncemore.scaffold import sample_project

from .helpers import have
from .test_gui import GuiServer

try:
    from playwright.sync_api import sync_playwright
    PLAYWRIGHT = True
except ImportError:  # pragma: no cover
    PLAYWRIGHT = False

# (on a 16:9 NTSC disc 160 x 107 is a 16:9 rectangle: a 16:9 title fills it)
THUMB = {"x": 200, "y": 100, "w": 160, "h": 107}


def data(thumb, **title):
    d = sample_project()
    b = d["menus"][0]["buttons"][2]                     # SAMPLE TITLE B: title:t2
    b["thumbnail"] = dict(THUMB, **thumb)
    d["titles"][1].update(title)
    return d


def project(d, path="/virtual/project.oncemore.json"):
    return build_project(d, path, check_files=False)


class TestModel(unittest.TestCase):
    def test_loaded(self):
        th = project(data({"mask": "ellipse"})).menus[0].buttons[2].thumb
        self.assertEqual((th.mask, th.mask_image), ("ellipse", None))
        th = project(data({"mask": "rectangle"})).menus[0].buttons[2].thumb
        self.assertIsNone(th.mask)
        th = project(data({"mask_image": "media/heart.png"})).menus[0].buttons[2].thumb
        self.assertTrue(th.mask_image.endswith(os.path.join("media", "heart.png")))

    def test_refused(self):
        with self.assertRaises(ProjectError) as e:
            project(data({"mask_image": "media/heart.png", "animated": True}))
        self.assertIn("a picture mask is for a still thumbnail", str(e.exception.issues))
        with self.assertRaises(ProjectError):
            project(data({"mask": "star"}))                     # (not in the schema)

    def test_filters(self):
        self.assertEqual(mask_filter(None, 10, 10), "")
        self.assertEqual(mask_filter("rectangle", 10, 10), "")
        self.assertIn("pow((X-W/2+0.5)/(W/2),2)", mask_filter("ellipse", 160, 120))
        self.assertIn(",18)", mask_filter("rounded", 160, 120))        # (15 % of 120)


@unittest.skipUnless(have("ffmpeg"), "needs ffmpeg")
class TestRendered(unittest.TestCase):
    """The menu's first frame: black background, a white thumbnail."""

    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="oncemore-thumbmask-")
        self.addCleanup(shutil.rmtree, self.tmp, True)
        self.white = self.make("white.mp4", ["-f", "lavfi", "-i", "color=c=white:s=320x180:d=3",
                                             "-c:v", "mpeg4"])
        # a heart-free shape: opaque only in the picture's right half
        self.half = self.make("half.png", ["-f", "lavfi", "-i",
                                           "color=c=black@0.0:s=20x20,format=rgba[a];"
                                           "color=c=black:s=20x20,format=rgba[b];[a][b]hstack[out0]",
                                           "-frames:v", "1"])
        self.dot = self.make("dot.png", ["-f", "lavfi", "-i", "color=c=black@0.0:s=8x8,format=rgba",
                                         "-frames:v", "1"])

    def make(self, name, args):
        path = os.path.join(self.tmp, name)
        subprocess.run(["ffmpeg", "-v", "error", "-y"] + args + [path], check=True)
        return path

    def render(self, thumb):
        d = data(thumb, source=self.white, chapters=[0])
        d["menus"][0].update(background=None, background_color="#000000", texts=[])
        for b in d["menus"][0]["buttons"]:
            b.pop("label", None)
            b["image"] = self.dot                         # (no text to draw)
        p = project(d, os.path.join(self.tmp, "project.oncemore.json"))
        m = p.menus[0]
        png = MenuBuilder(p, self.tmp).render_base(m)
        raw = subprocess.run(["ffmpeg", "-v", "error", "-i", png, "-f", "rawvideo",
                              "-pix_fmt", "gray", "-"], check=True, capture_output=True).stdout
        width = len(raw) // p.disc.height
        sx = width / 720
        return lambda x, y: raw[y * width + round(x * sx)]

    def test_shapes(self):
        x0, y0, w, h = THUMB["x"], THUMB["y"], THUMB["w"], THUMB["h"]
        corner, centre, top = (x0 + 2, y0 + 2), (x0 + w // 2, y0 + h // 2), (x0 + w // 2, y0 + 2)
        px = self.render({})
        self.assertGreater(px(*corner), 200)              # (a rectangle: its corner too)
        px = self.render({"mask": "ellipse"})
        self.assertLess(px(*corner), 40)
        self.assertGreater(px(*centre), 200)
        self.assertGreater(px(*top), 200)                 # (the top of the ellipse)
        px = self.render({"mask": "rounded"})
        self.assertLess(px(*corner), 40)
        self.assertGreater(px(x0 + 20, y0 + 2), 200)       # (past the corner's curve)
        px = self.render({"mask_image": self.half})
        self.assertLess(px(x0 + w // 4, y0 + h // 2), 40)  # (the picture is clear there)
        self.assertGreater(px(x0 + 3 * w // 4, y0 + h // 2), 200)


@unittest.skipUnless(PLAYWRIGHT, "needs playwright")
class TestApp(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.mkdtemp(prefix="oncemore-thumbmask-gui-")
        self.addCleanup(shutil.rmtree, self.dir, True)
        self.s = GuiServer(self.dir)
        self.addCleanup(self.s.close)
        self.s.call("/api/new", "POST", {"sample": True})
        self.path = os.path.join(self.dir, "project.oncemore.json")
        with open(self.path) as f:
            d = json.load(f)
        d["menus"][0]["buttons"][2]["thumbnail"] = dict(THUMB)
        with open(self.path, "w") as f:
            json.dump(d, f)

    def thumb(self):
        with open(self.path) as f:
            return json.load(f)["menus"][0]["buttons"][2]["thumbnail"]

    def test_shape_chosen(self):
        from .test_gui import TestGuiBrowser
        with sync_playwright() as p:
            browser = TestGuiBrowser.launch(self, p)
            page = browser.new_page(viewport={"width": 1400, "height": 900}, locale="en-US")
            errors = []
            page.on("pageerror", lambda e: errors.append(str(e)))
            page.goto(f"{self.s.base}/#token={self.s.app.token}")
            page.click(".nav-item[data-view=menu][data-id=main]", timeout=120000)
            page.locator(".stage .el.button").nth(2).click()
            page.select_option("#th-mask", "ellipse")
            for _ in range(300):
                if self.thumb().get("mask") == "ellipse":
                    break
                page.wait_for_timeout(100)
            self.assertEqual(self.thumb().get("mask"), "ellipse")
            page.wait_for_function(
                "document.querySelector('.stage .thumb-pv').style.borderRadius === '50%'")
            page.select_option("#th-mask", "picture")             # (the first picture)
            for _ in range(300):
                if self.thumb().get("mask_image"):
                    break
                page.wait_for_timeout(100)
            self.assertNotIn("mask", self.thumb())
            self.assertTrue(self.thumb()["mask_image"].startswith("media/"))
            page.locator("#th-mask-image").wait_for()
            browser.close()
        self.assertEqual(errors, [])


if __name__ == "__main__":
    unittest.main()
