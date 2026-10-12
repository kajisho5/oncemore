"""Objects coming in on a menu (`animate`): pictures moving, growing and
fading in, texts moving and fading in, over the menu's frames; at rest
where the menu shows them still (previews), and the menu a motion menu."""

import os
import shutil
import subprocess
import tempfile
import unittest

from oncemore import schemalite, tools
from oncemore.errors import ProjectError
from oncemore.menu import MenuBuilder, animated
from oncemore.project import Animate, build_project, load_schema
from oncemore.scaffold import sample_project

from .helpers import have

SMALL = (180, 120)          # frames read back at this size


def data(images=(), texts=(), **menu):
    d = sample_project()
    d["menus"][0].update({"background": None, "background_color": "#000000", "duration": 2,
                          "images": list(images), "texts": list(texts), **menu})
    return d


def project(d, path="/virtual/project.oncemore.json"):
    return build_project(d, path, check_files=False)


class TestModel(unittest.TestCase):
    def test_loaded(self):
        p = project(data(images=[{"file": "a.png", "x": 300, "y": 200, "w": 100, "h": 100,
                                   "animate": {"start": 0.5, "duration": 1, "dx": -300,
                                               "scale": 0.5, "fade": True}}],
                         texts=[{"text": "Hi", "x": 10, "y": 10,
                                 "animate": {"dy": 40, "fade": True}}]))
        m = p.menus[0]
        self.assertEqual(m.images[0].animate, Animate(0.5, 1.0, -300, 0, 0.5, True))
        self.assertEqual(m.images[0].animate.end, 1.5)
        self.assertEqual(m.texts[0].animate, Animate(0.0, 1.0, 0, 40, 1.0, True))
        self.assertTrue(animated(m))
        self.assertFalse(animated(project(data()).menus[0]))

    def test_refused(self):
        cases = [
            (data(texts=[{"text": "Hi", "x": 10, "y": 10, "animate": {"scale": 0.5}}]),
             "only a picture grows"),
        ]
        for d, why in cases:
            with self.assertRaises(ProjectError) as e:
                project(d)
            self.assertIn(why, str(e.exception.issues))
        for bad in ({"duration": 0}, {"scale": 2}):            # (it grows from smaller)
            d = data(images=[{"file": "a.png", "x": 0, "y": 0, "w": 50, "h": 50, "animate": bad}])
            self.assertTrue(schemalite.validate(d, load_schema()))
        # (one that does nothing is no animation)
        p = project(data(images=[{"file": "a.png", "x": 0, "y": 0, "w": 50, "h": 50,
                                  "animate": {"start": 1}}]))
        self.assertIsNone(p.menus[0].images[0].animate)
        self.assertIn("neither moves", " ".join(p.warnings))


@unittest.skipUnless(have("ffmpeg"), "needs ffmpeg")
class TestRendered(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="oncemore-animate-")
        self.addCleanup(shutil.rmtree, self.tmp, True)
        self.white = os.path.join(self.tmp, "white.png")
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i",
                        "color=c=white:s=100x100", "-frames:v", "1", self.white], check=True)

    def builder(self, d):
        p = project(d, os.path.join(self.tmp, "project.oncemore.json"))
        m = p.menus[0]
        m.buttons = []
        return MenuBuilder(p, self.tmp, font=None), m, p

    def frames(self, mb, m):
        """The menu's frames (grey, SMALL), and a function reading one."""
        inputs, graph = mb.compose(m, animate=True)
        graph += f";[out]scale={SMALL[0]}:{SMALL[1]},format=gray[o]"
        raw = subprocess.run([tools.find("ffmpeg"), "-v", "error"] + inputs +
                             ["-filter_complex", graph, "-map", "[o]", "-f", "rawvideo", "-"],
                             cwd=mb.work, check=True, capture_output=True).stdout
        size = SMALL[0] * SMALL[1]
        count = len(raw) // size

        def at(seconds, x, y):
            """Grey at (x, y) of the 720 x 480 grid, `seconds` in."""
            n = min(count - 1, round(seconds * mb.disc.fps[0] / mb.disc.fps[1]))
            return raw[n * size + round(y * SMALL[1] / 480) * SMALL[0] + round(x * SMALL[0] / 720)]
        return at, count

    def test_picture_slides_and_fades_in(self):
        mb, m, p = self.builder(data(images=[{
            "file": self.white, "x": 400, "y": 200, "w": 100, "h": 100,
            "animate": {"start": 0.5, "duration": 1, "dx": -300, "fade": True}}]))
        at, count = self.frames(mb, m)
        self.assertGreaterEqual(count, 55)                 # (two seconds of frames)
        self.assertLess(at(0.2, 450, 250), 20)             # not in yet, and clear
        self.assertLess(at(0.2, 150, 250), 20)
        mid = at(1.0, 300, 250)                            # half way: 150 to the left, half clear
        self.assertGreater(mid, 60)
        self.assertLess(mid, 200)
        self.assertGreater(at(1.9, 450, 250), 230)         # at rest
        self.assertLess(at(1.9, 150, 250), 20)
        # the preview shows it at rest
        base = mb.render_base(m)
        grey = subprocess.run([tools.find("ffmpeg"), "-v", "error", "-i", base, "-vf",
                               "crop=1:1:450:250,format=gray", "-f", "rawvideo", "-"],
                              check=True, capture_output=True).stdout
        self.assertGreater(grey[0], 230)

    def test_picture_grows(self):
        mb, m, p = self.builder(data(images=[{
            "file": self.white, "x": 300, "y": 200, "w": 160, "h": 160,
            "animate": {"start": 0, "duration": 1.5, "scale": 0.25}}]))
        at, _ = self.frames(mb, m)
        self.assertGreater(at(0.05, 380, 280), 230)        # its centre at once
        self.assertLess(at(0.05, 310, 210), 20)            # its corner not yet
        self.assertGreater(at(1.9, 310, 210), 230)         # grown

    def test_loop_point_warning(self):
        anim = {"file": "a.png", "x": 0, "y": 0, "w": 50, "h": 50,
                "animate": {"start": 0.5, "duration": 1, "fade": True}}
        self.assertIn("comes in again each time the menu loops; set its loop point to 1.5 s",
                      " ".join(project(data(images=[anim])).warnings))
        self.assertNotIn("comes in again", " ".join(project(data(images=[anim], loop_point=1.5,
                                                                  duration=3)).warnings))

    @unittest.skipUnless(tools.has_drawtext(), "needs ffmpeg with drawtext")
    def test_dvd_menu_encoded(self):
        from oncemore.menu import find_font
        p = project(data(images=[{"file": self.white, "x": 400, "y": 200, "w": 100, "h": 100,
                                  "animate": {"start": 0.5, "duration": 1, "dx": -300,
                                              "fade": True}}]),
                    os.path.join(self.tmp, "project.oncemore.json"))
        m = p.menus[0]
        mb = MenuBuilder(p, self.tmp, font=find_font(None, "PLAY ALL CHAPTERS"))
        out = mb.encode(m, mb.prepare(m))

        def grey(t):
            return subprocess.run([tools.find("ffmpeg"), "-v", "error", "-ss", str(t), "-i", out,
                                   "-frames:v", "1", "-vf", "scale=720:480,crop=1:1:450:250,format=gray",
                                   "-f", "rawvideo", "-"], check=True, capture_output=True).stdout[0]
        self.assertLess(grey(0.2), 30)                    # (still to come)
        self.assertGreater(grey(1.9), 220)                # (come in)

    @unittest.skipUnless(tools.has_drawtext(), "needs ffmpeg with drawtext")
    def test_text_comes_down_and_fades_in(self):
        from oncemore.menu import find_font
        d = data(texts=[{"text": "████", "x": 300, "y": 300, "size": 60, "color": "#FFFFFF",
                         "animate": {"start": 0, "duration": 1, "dy": -200, "fade": True}}])
        p = project(d, os.path.join(self.tmp, "project.oncemore.json"))
        m = p.menus[0]
        m.buttons = []
        mb = MenuBuilder(p, self.tmp, font=find_font(None, "████"))
        at, _ = self.frames(mb, m)
        self.assertLess(at(0.0, 330, 320), 20)
        self.assertGreater(at(1.9, 330, 320), 200)          # come down to its place
        self.assertLess(at(1.9, 330, 120), 20)


try:
    from playwright.sync_api import sync_playwright
    PLAYWRIGHT = True
except ImportError:  # pragma: no cover
    PLAYWRIGHT = False


@unittest.skipUnless(PLAYWRIGHT, "needs playwright")
class TestApp(unittest.TestCase):
    """A text's and a picture's Properties: Comes in."""

    def setUp(self):
        import json
        from .test_gui import GuiServer
        self.dir = tempfile.mkdtemp(prefix="oncemore-animate-gui-")
        self.addCleanup(shutil.rmtree, self.dir, True)
        self.s = GuiServer(self.dir)
        self.addCleanup(self.s.close)
        self.s.call("/api/new", "POST", {"sample": True})
        self.path = os.path.join(self.dir, "project.oncemore.json")
        with open(self.path) as f:
            d = json.load(f)
        d["menus"][0]["images"] = [{"file": "media/menu_bg.png", "x": 500, "y": 300, "w": 120,
                                    "h": 80}]
        with open(self.path, "w") as f:
            json.dump(d, f)

    def menu(self):
        import json
        with open(self.path) as f:
            return json.load(f)["menus"][0]

    def until(self, page, test, what):
        for _ in range(300):
            if test(self.menu()):
                return
            page.wait_for_timeout(100)
        raise AssertionError(f"{what}: {self.menu()}")

    def test_properties(self):
        from .test_gui import TestGuiBrowser
        with sync_playwright() as p:
            browser = TestGuiBrowser.launch(self, p)
            page = browser.new_page(viewport={"width": 1400, "height": 900}, locale="en-US")
            errors = []
            page.on("pageerror", lambda e: errors.append(str(e)))
            page.goto(f"{self.s.base}/#token={self.s.app.token}")
            page.click(".nav-item[data-view=menu][data-id=main]", timeout=120000)
            # the heading: comes down and fades in, from half a second
            page.locator(".stage .el.text").first.click()
            page.locator("[data-anim-on]").check()
            self.until(page, lambda m: m["texts"][0].get("animate") == {
                "start": 0, "duration": 1, "dy": 40, "fade": True}, "on")
            page.locator("[data-anim=start]").fill("0.5")
            page.locator("[data-anim=start]").dispatch_event("change")
            self.until(page, lambda m: m["texts"][0]["animate"]["start"] == 0.5, "start")
            self.assertEqual(page.locator("[data-anim=scale]").count(), 0)   # (texts do not grow)
            page.locator("[data-anim=fade]").uncheck()
            self.until(page, lambda m: "fade" not in m["texts"][0]["animate"], "fade off")
            # the picture: grows from half its size
            page.locator(".stage .el.image").click()
            page.locator("[data-anim-on]").check()
            page.locator("[data-anim=scale]").fill("50")
            page.locator("[data-anim=scale]").dispatch_event("change")
            self.until(page, lambda m: m["images"][0].get("animate", {}).get("scale") == 0.5,
                       "grows")
            page.locator("[data-anim-on]").uncheck()
            self.until(page, lambda m: "animate" not in m["images"][0], "off")
            browser.close()
        self.assertEqual(errors, [])


if __name__ == "__main__":
    unittest.main()
