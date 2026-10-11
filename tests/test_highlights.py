"""Button highlights: a button's own pixels, a frame or a line, or a shape
drawn in the editor (highlight "drawn" with its highlight_area).

The project fields and their checks, the shapes the menu renderer makes of
them (the same shapes become the DVD subpictures, the Blu-ray button
pictures and the web version's highlights), and the Blu-ray scaling.
"""

import json
import os
import shutil
import tempfile
import unittest

from oncemore import bdmenu, png4, tools
from oncemore.errors import ProjectError
from oncemore.menu import MenuBuilder
from oncemore.project import HighlightArea, build_project
from oncemore.scaffold import sample_project

from .helpers import have
from .test_gui import GuiServer

try:
    from playwright.sync_api import sync_playwright
    PLAYWRIGHT = True
except ImportError:  # pragma: no cover
    PLAYWRIGHT = False

RENDER = have("ffmpeg", "ffprobe") and tools.has_drawtext()


def project(data, base="/virtual"):
    return build_project(data, os.path.join(base, "project.oncemore.json"), check_files=False)


def area(**kw):
    return dict({"x": 100, "y": 100, "w": 200, "h": 80}, **kw)


class TestProjectFields(unittest.TestCase):
    def test_defaults(self):
        d = sample_project()
        d["menus"][0]["buttons"].append({"id": "pic", "image": "media/p.png", "x": 400,
                                         "y": 100, "action": "playall"})
        b = project(d).menus[0].buttons
        self.assertEqual(b[0].highlight, "underline")      # a text button
        self.assertEqual(b[-1].highlight, "frame")         # an image button
        self.assertIsNone(b[0].area)

    def test_drawn(self):
        d = sample_project()
        d["menus"][0]["buttons"][0]["highlight_area"] = area(form="ellipse", filled=False)
        b = project(d).menus[0].buttons[0]
        self.assertEqual(b.highlight, "drawn")              # (implied by the area)
        self.assertEqual(b.area, HighlightArea(100, 100, 200, 80, "ellipse", False))
        d["menus"][0]["buttons"][0]["highlight"] = "drawn"
        self.assertEqual(project(d).menus[0].buttons[0].area.form, "ellipse")

    def test_refused(self):
        cases = (
            ({"highlight": "drawn"}, "needs its highlight_area"),
            ({"highlight": "shape", "highlight_area": area()}, "only for a \"drawn\""),
            ({"highlight_area": area(), "highlight_image": "media/h.png"}, "not both"),
            ({"highlight_area": area(x=600)}, "runs off"),
            ({"highlight_area": area(form="star")}, "must be one of"),
            ({"highlight": "glow"}, "must be one of"),
            ({"image": "media/p.png", "highlight": "underline"}, "for text buttons"),
        )
        for change, message in cases:
            d = sample_project()
            d["menus"][0]["buttons"][0].update(change)
            with self.assertRaises(ProjectError, msg=change) as cm:
                project(d)
            self.assertIn(message, str(cm.exception.issues), change)

    def test_blu_ray_scales_the_area(self):
        d = sample_project()                               # 16:9 NTSC: 1920 / 720 wide
        d["menus"][0]["buttons"][0]["highlight_area"] = area(form="ellipse")
        p = project(d)
        hd = bdmenu.scale_menu(p.menus[0], p.disc, lambda path: {"width": 100, "height": 50})
        a = hd.buttons[0].area
        self.assertEqual((a.x, a.y, a.w, a.h), (267, 225, 533, 180))
        self.assertEqual((a.form, a.filled), ("ellipse", True))


class TestAreaShape(unittest.TestCase):
    def canvas(self, a):
        c = png4.Canvas(720, 480)
        sh = MenuBuilder.area_shape(a)
        if isinstance(sh, png4.Mask):
            c.blit_mask(sh, 1)
        elif sh[0] == "fill":
            c.fill_rect(*sh[1], 1)
        else:
            c.stroke_rect(*sh[1], 1, width=3)
        return c

    def test_rectangles(self):
        self.assertEqual(MenuBuilder.area_shape(HighlightArea(10, 20, 30, 40)),
                         ("fill", (10, 20, 40, 60)))
        self.assertEqual(MenuBuilder.area_shape(HighlightArea(10, 20, 30, 40, filled=False)),
                         ("frame", (10, 20, 40, 60)))

    def test_ellipse(self):
        c = self.canvas(HighlightArea(100, 100, 200, 100, "ellipse"))
        self.assertEqual(c.get(200, 150), 1)                # the centre
        self.assertEqual(c.get(102, 150), 1)                # the ends of its width
        self.assertEqual(c.get(297, 150), 1)
        self.assertEqual(c.get(101, 101), 0)                # not the corners
        self.assertEqual(c.get(298, 198), 0)
        self.assertEqual(c.get(200, 100), 1)                # top and bottom
        self.assertEqual(c.get(200, 199), 1)
        self.assertEqual(c.get(200, 200), 0)                # nothing past it
        self.assertEqual(c.get(99, 150), 0)

    def test_ellipse_outline(self):
        c = self.canvas(HighlightArea(100, 100, 200, 100, "ellipse", filled=False))
        self.assertEqual(c.get(200, 150), 0)                # hollow
        self.assertEqual(c.get(101, 150), 1)                # its line, 3 pixels thick
        self.assertEqual(c.get(103, 150), 0)
        self.assertEqual(c.get(200, 101), 1)
        self.assertEqual(c.get(200, 104), 0)


@unittest.skipUnless(RENDER, "needs ffmpeg with drawtext")
class TestLayout(unittest.TestCase):
    """The highlight shapes and button areas the layout gives each style."""

    def setUp(self):
        self.dir = tempfile.mkdtemp(prefix="oncemore-hl-")
        self.addCleanup(shutil.rmtree, self.dir, True)
        self.data = sample_project(aspect="4:3")
        m = self.data["menus"][0]
        m.pop("background", None)
        m["background_color"] = "#000000"
        m["texts"] = []
        m["buttons"] = m["buttons"][:1]                     # "PLAY ALL" at 120, 220

    def geom(self, **change):
        self.data["menus"][0]["buttons"][0].update(change)
        p = project(self.data, self.dir)
        return MenuBuilder(p, self.dir).layout(p.menus[0])[0]

    def test_text_styles(self):
        under = self.geom()
        letters = under.shape[0].bbox()
        self.assertEqual(len(under.shape), 2)               # the letters and a line
        self.assertEqual(under.shape[1][0], "fill")
        shape = self.geom(highlight="shape")
        self.assertEqual(len(shape.shape), 1)               # the letters alone
        self.assertEqual(shape.shape[0].bbox(), letters)
        self.assertLess(shape.rect[3], under.rect[3])       # (no line under them)
        frame = self.geom(highlight="frame")
        x0, y0, x1, y1 = letters
        self.assertEqual(frame.shape, [("frame", (x0 - 4, y0 - 4, x1 + 4, y1 + 4))])
        self.assertLessEqual(frame.rect[0], x0 - 4)
        self.assertGreaterEqual(frame.rect[2], x1 + 4)

    def test_thumbnail(self):
        thumb = {"x": 400, "y": 100, "w": 160, "h": 120}
        g = self.geom(action="title:t1", thumbnail=thumb)
        self.assertIn(("frame", (396, 96, 564, 224)), g.shape)
        g = self.geom(highlight="shape")
        self.assertEqual(len(g.shape), 1)                   # the letters, no frame ...
        self.assertGreaterEqual(g.rect[2], 564)             # ... but the area takes it in

    def test_drawn(self):
        g = self.geom(highlight_area=area(y=300))
        self.assertEqual(g.shape, [("fill", (100, 300, 300, 380))])
        self.assertEqual(g.rect, (98, 298, 301, 382))       # the area, not the label
        g = self.geom(highlight_area=area(y=300, form="ellipse"))
        self.assertIsInstance(g.shape[0], png4.Mask)
        self.assertEqual(g.shape[0].bbox(), (100, 300, 300, 380))

    def test_drawn_stays_when_turned(self):
        g = self.geom(highlight_area=area(y=300), rotate=90)
        self.assertEqual(g.shape, [("fill", (100, 300, 300, 380))])

    def test_overlap(self):
        m = self.data["menus"][0]
        m["buttons"].append({"id": "two", "label": "TWO", "x": 500, "y": 400,
                             "action": "playall", "highlight_area": area(x=110, y=200)})
        p = project(self.data, self.dir)
        with self.assertRaises(ProjectError) as cm:
            MenuBuilder(p, self.dir).layout(p.menus[0])
        self.assertIn("overlap", str(cm.exception))

    def test_drawn_on_blu_ray(self):
        # 4:3 on the HD frame: x * 2 + 240 (pillarboxed), y * 2.25
        self.data["menus"][0]["buttons"][0]["highlight_area"] = area(y=300, form="ellipse")
        p = bdmenu.hd_project(project(self.data, self.dir), lambda path: {})
        g = MenuBuilder(p, self.dir).layout(p.menus[0])[0]
        self.assertEqual(g.shape[0].bbox(), (440, 675, 840, 855))

    def test_drawn_on_the_subpicture(self):
        self.data["menus"][0]["buttons"][0]["highlight_area"] = area(y=300, form="ellipse")
        p = project(self.data, self.dir)
        mb = MenuBuilder(p, self.dir)
        geoms = mb.layout(p.menus[0])
        c = mb.highlight_canvas(geoms)
        self.assertEqual(c.get(200, 340), 1)
        self.assertEqual(c.get(101, 301), 0)
        self.assertEqual(c.get(150, 230), 0)                # not the label


@unittest.skipUnless(PLAYWRIGHT and RENDER, "needs playwright and ffmpeg with drawtext")
class TestEditor(unittest.TestCase):
    """Properties > Highlight, and the drawn highlight on the stage."""

    def setUp(self):
        self.dir = tempfile.mkdtemp(prefix="oncemore-hl-gui-")
        self.addCleanup(shutil.rmtree, self.dir, True)
        self.s = GuiServer(self.dir)
        self.addCleanup(self.s.close)
        self.s.call("/api/new", "POST", {"sample": True})

    def button(self):
        with open(os.path.join(self.dir, "project.oncemore.json")) as f:
            return json.load(f)["menus"][0]["buttons"][0]

    def test_highlight_styles(self):
        with sync_playwright() as p:
            from .test_gui import TestGuiBrowser
            browser = TestGuiBrowser.launch(self, p)
            page = browser.new_page(viewport={"width": 1400, "height": 900}, locale="en-US")
            errors = []
            page.on("pageerror", lambda e: errors.append(str(e)))
            page.goto(f"{self.s.base}/#token={self.s.app.token}")
            page.click(".nav-item[data-view=menu][data-id=main]", timeout=120000)
            page.locator(".stage .el.button").first.click()
            pick = "#inspector select[data-k=highlight]"
            page.locator(pick).wait_for()

            def until(test, what):
                for _ in range(300):
                    if test(self.button()):
                        return self.button()
                    page.wait_for_timeout(100)
                raise AssertionError(what)
            # a text button: a line under it (the default), its letters, a frame
            self.assertEqual(page.input_value(pick), "underline")
            self.assertEqual(page.locator(f"{pick} option").count(), 4)
            page.select_option(pick, "shape")
            until(lambda b: b.get("highlight") == "shape", "shape")
            page.select_option(pick, "underline")
            until(lambda b: "highlight" not in b, "the default again")
            # drawn: a rectangle around the button, on the stage to drag
            page.select_option(pick, "drawn")
            b = until(lambda b: "highlight_area" in b, "an area")
            self.assertNotIn("highlight", b)
            a = b["highlight_area"]
            self.assertLessEqual(a["x"], b["x"])
            self.assertLessEqual(a["y"], b["y"])
            area = page.locator(".stage .hl-area.on")
            area.wait_for()
            stage_w = page.locator("#stage").bounding_box()["width"]
            k = stage_w / 720                                  # (16:9: 1 grid px = k screen px)
            box = page.locator(".hl-grip").bounding_box()
            page.mouse.move(box["x"] + 4, box["y"] + 4)
            page.mouse.down()
            page.mouse.move(box["x"] + 4 + 40 * k, box["y"] + 4, steps=4)
            page.mouse.up()
            b = until(lambda b: b["highlight_area"]["w"] != a["w"], "resized")
            self.assertLess(abs(b["highlight_area"]["w"] - a["w"] - 40), 3)
            self.assertEqual(b["highlight_area"]["x"], a["x"])
            # the form and fill
            page.select_option("#inspector select[data-hla=form]", "ellipse")
            until(lambda b: b["highlight_area"].get("form") == "ellipse", "ellipse")
            page.uncheck("#inspector input[data-hla=filled]")
            until(lambda b: b["highlight_area"].get("filled") is False, "outline")
            page.wait_for_selector(".stage .hl-area.ellipse")
            # moving the button moves its highlight
            before = self.button()["highlight_area"]["x"]
            page.locator(".stage .el.button").first.click()
            page.keyboard.press("Shift+ArrowRight")
            until(lambda b: b["highlight_area"]["x"] == before + 10, "moved along")
            # the exact preview draws it
            page.click("#exact")
            page.wait_for_selector(".stage img.exact", timeout=60000)
            # back to a frame: the area goes
            page.select_option(pick, "frame")
            b = until(lambda b: "highlight_area" not in b, "no area")
            self.assertEqual(b["highlight"], "frame")
            self.assertEqual(page.locator(".stage .hl-area").count(), 0)
            browser.close()
        self.assertEqual(errors, [])


if __name__ == "__main__":
    unittest.main()
